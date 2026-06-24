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
  * SUBPROCESS READ-OUT — each new/changed file is read out of the GDrive FUSE
    mount via a `cat` SUBPROCESS bounded by a timeout, then read from the local copy.
    History of this line (each fix exposed the next bug):
      1. in-process read() wrapped in signal.alarm() — on macOS File Provider a signal
         delivered mid-read() makes the kernel raise EDEADLK ("Resource deadlock
         avoided"); the SIGALRM "timeout" was ITSELF the failure (260619 stuck).
      2. `cp` SUBPROCESS (260620) — macOS `cp` uses fcopyfile/clonefile, which ALSO
         hard-deadlocks on a DEHYDRATED GDrive placeholder; the 260623 DeepSeek report
         stuck for 4 days on exactly this (260624 diagnosis), silently blocking publish.
      3. `cat` SUBPROCESS (260624, current) — cat uses plain read()/write(), NOT
         fcopyfile, forcing normal on-read materialisation. PROVEN 260624: the file
         `cp` deadlocked on read cleanly via cat/dd/plain read().
    A subprocess can be killed on timeout without signalling this thread mid-syscall,
    so a genuinely-hanging read is dropped + retried next run instead of poisoning the
    file forever.
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
import os
import pathlib
import subprocess
import sys
import tempfile
import time

MARKERS = ("## Full Transcript", "## Transcript", "## Raw Transcript")
READ_TIMEOUT_S = 90  # per-file hard cap on the read-out-of-FUSE subprocess (allows
                     # first-fetch of a dehydrated placeholder; GDrive throttles ~<1KB/s)
COPY_RETRIES = 4            # in-run retries on a slow/transient FUSE materialisation
COPY_RETRY_BACKOFF_S = 1.5  # base backoff between retries (×attempt: 1.5s, 3s, 4.5s)


def _strip_transcript(raw: str) -> str:
    lines = raw.splitlines()
    cut = len(lines)
    for i, ln in enumerate(lines):
        if any(ln.strip().startswith(m) for m in MARKERS):
            cut = i
            break
    return "\n".join(lines[:cut]).rstrip() + "\n"


def _read_via_copy(f: pathlib.Path) -> str:
    """Read f out of FUSE in a `cat` subprocess (timeout-bounded), then read locally.

    Raises TimeoutError on a hanging read and OSError on a read failure — both are
    handled by the caller as skip-and-retry-next-run, never a hang of this process.
    """
    fd, tmp_name = tempfile.mkstemp(prefix="bridge-", suffix=".md")
    os.close(fd)
    tmp = pathlib.Path(tmp_name)
    try:
        # Read via `cat` (plain read()/write()), NOT `cp`. macOS `cp` uses
        # fcopyfile/clonefile, which HARD-DEADLOCKS on a DEHYDRATED GDrive
        # File-Provider placeholder — not a transient EDEADLK that retries away: the
        # 260623 DeepSeek report hung `cp` on every 15-min cycle for 4 days (260624
        # diagnosis). `cat` issues ordinary read() syscalls, which trigger normal
        # on-read materialisation of the placeholder and succeed (PROVEN 260624: the
        # exact file `cp` deadlocked on read cleanly via cat/dd/plain read()). The
        # subprocess stays killable on a genuine hang via the per-attempt timeout, so
        # a truly-stuck read is dropped + retried next run instead of poisoning the
        # process. Retry in-run with backoff to absorb a slow first-fetch.
        last_err = None
        for attempt in range(COPY_RETRIES):
            try:
                with open(tmp, "wb") as out:
                    subprocess.run(
                        ["cat", str(f)],
                        check=True,
                        timeout=READ_TIMEOUT_S,
                        stdout=out,
                        stderr=subprocess.PIPE,
                    )
                return tmp.read_text(encoding="utf-8", errors="replace")
            except subprocess.TimeoutExpired as e:
                if attempt == COPY_RETRIES - 1:
                    raise TimeoutError(str(e)) from e
                last_err = "read timeout"
                time.sleep(COPY_RETRY_BACKOFF_S * (attempt + 1))
            except subprocess.CalledProcessError as e:
                msg = (e.stderr or b"").decode("utf-8", "replace").strip()
                last_err = msg or f"cat exited {e.returncode}"
                if attempt == COPY_RETRIES - 1:
                    raise OSError(last_err) from e
                time.sleep(COPY_RETRY_BACKOFF_S * (attempt + 1))
        raise OSError(last_err or "cat failed")
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


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
    errored: list[str] = []
    t0 = time.time()

    for f, mtime, size in entries:
        target = dst / f.name
        prev = state.get(f.name)
        if prev and prev.get("mtime") == mtime and prev.get("size") == size \
                and (target.exists() or prev.get("excluded")):
            skipped += 1
            continue

        try:
            raw = _read_via_copy(f)
        except TimeoutError:
            timed_out.append(f.name)
            print(f"[bridge] copy timeout (retry next run): {f.name}", file=sys.stderr)
            continue
        except OSError as e:
            errored.append(f.name)
            print(f"[bridge] copy error {f.name}: {e}", file=sys.stderr)
            continue

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
          f"timeouts={len(timed_out)} errors={len(errored)} elapsed={time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
