#!/usr/bin/env python3
"""bridge_sync.py — hang-proof GDrive -> repo source/ transcript-stripping sync.

Replaces the naive "read every GDrive .md every run" loop in rebuild_and_push.sh,
which stalled on per-file FUSE reads (~file 90 of 300+) and silently failed to
publish new reports (root cause of the 260614-260617 "generates but never reaches
Pages" incident — see source/FEATURES_LOG.md).

Robustness properties:
  * INCREMENTAL — a local sidecar (.bridge_state.json) records each GDrive file's
    (mtime, size). Unchanged files are skipped with a cheap stat() and are NEVER
    content-read, so the FUSE-read hang surface shrinks to genuinely new/changed
    files only.
  * NEWEST-FIRST — files are processed by descending mtime, so a freshly generated
    report publishes even if an older file stalls.
  * PER-FILE TIMEOUT — each content read is bounded by SIGALRM (default 30s). A
    hanging dataless FUSE read is skipped (logged) and retried next run instead of
    blocking the whole sync.
  * AUTO-SEED — on first run (empty sidecar) any file that already has a stripped
    target in source/ is recorded as synced via stat() alone (no content read), so
    the first run only reads genuinely-new files instead of re-reading the corpus.

Privacy contract (unchanged): bodies are cut at the first transcript marker and
EXCLUDE_FROM_PUBLIC reports are withheld (and withdrawn from source/ if previously
synced).

Exit code is always 0 unless arguments are wrong — a per-file timeout is normal
operation, not a failure. Prints a one-line summary the shell logs.
"""
from __future__ import annotations

import json
import pathlib
import signal
import sys
import time

MARKERS = ("## Full Transcript", "## Transcript", "## Raw Transcript")
READ_TIMEOUT_S = 30  # per-file hard cap on a FUSE content read


class _ReadTimeout(Exception):
    pass


def _on_alarm(_sig, _frame):
    raise _ReadTimeout()


def _strip_transcript(raw: str) -> str:
    lines = raw.splitlines()
    cut = len(lines)
    for i, ln in enumerate(lines):
        if any(ln.strip().startswith(m) for m in MARKERS):
            cut = i
            break
    return "\n".join(lines[:cut]).rstrip() + "\n"


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: bridge_sync.py <gdrive_src_dir> <repo_source_dir> [state_json]",
              file=sys.stderr)
        return 2

    src = pathlib.Path(sys.argv[1])
    dst = pathlib.Path(sys.argv[2])
    state_path = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else dst.parent / ".bridge_state.json"
    dst.mkdir(parents=True, exist_ok=True)

    try:
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
    except (ValueError, OSError):
        state = {}
    seeded_empty = not state

    signal.signal(signal.SIGALRM, _on_alarm)

    # Cheap metadata pass (stat() does NOT materialise dataless FUSE files).
    entries = []
    for f in src.glob("*.md"):
        if f.name in ("FEATURES_LOG.md", "_INDEX.md"):
            continue  # operational logs, never published reports
        try:
            st = f.stat()
        except OSError as e:
            print(f"[bridge] stat failed {f.name}: {e}", file=sys.stderr)
            continue
        entries.append((f, int(st.st_mtime), int(st.st_size)))
    entries.sort(key=lambda x: x[1], reverse=True)  # newest first

    # Auto-seed: trust existing stripped targets as already-synced (stat only).
    if seeded_empty:
        seeded = 0
        for f, mtime, size in entries:
            if (dst / f.name).exists():
                state[f.name] = {"mtime": mtime, "size": size, "excluded": False}
                seeded += 1
        if seeded:
            print(f"[bridge] seeded {seeded} already-synced files (no content read)")

    changed = removed = skipped = 0
    timed_out: list[str] = []
    t0 = time.time()

    for f, mtime, size in entries:
        target = dst / f.name
        prev = state.get(f.name)
        if prev and prev.get("mtime") == mtime and prev.get("size") == size \
                and (target.exists() or prev.get("excluded")):
            skipped += 1
            continue

        signal.alarm(READ_TIMEOUT_S)
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except _ReadTimeout:
            timed_out.append(f.name)
            print(f"[bridge] read timeout (retry next run): {f.name}", file=sys.stderr)
            continue
        except OSError as e:
            print(f"[bridge] read error {f.name}: {e}", file=sys.stderr)
            continue
        finally:
            signal.alarm(0)

        excluded = "EXCLUDE_FROM_PUBLIC" in raw
        if excluded:
            if target.exists():
                target.unlink()
                removed += 1
        else:
            new_body = _strip_transcript(raw)
            if not (target.exists() and target.read_text(encoding="utf-8") == new_body):
                target.write_text(new_body, encoding="utf-8")
                changed += 1
        state[f.name] = {"mtime": mtime, "size": size, "excluded": excluded}

    try:
        state_path.write_text(json.dumps(state, indent=0, sort_keys=True))
    except OSError as e:
        print(f"[bridge] WARN could not write state: {e}", file=sys.stderr)

    print(f"[bridge] changed={changed} removed={removed} skipped={skipped} "
          f"timeouts={len(timed_out)} elapsed={time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
