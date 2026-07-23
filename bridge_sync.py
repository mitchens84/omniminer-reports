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

# --- Self-escalation (FAIL LOUDLY) -------------------------------------------
# The 260620→260624 outages were SILENT: a single file failed to read every 15-min
# cycle for days and nothing raised a hand (the publish-drift watchdog runs in a
# different launchd job that can't see GDrive). The bridge is the ONLY component that
# knows a specific file is stuck, so it escalates directly. Alert keys live in the
# sidecar under reserved __keys__ (never collide with YYMMDD-*.md report filenames).
STUCK_RUNS_ALERT = 3                  # consecutive failed runs before a file is "stuck"
                                      #   (3 × 15-min cycle ≈ 45 min — fast, not flappy)
TELEGRAM_CHAT_ID = "-1003961257879"   # mitch-mai group (matches notify.py / health_check)
TELEGRAM_THREAD_ID = 157              # OmniMiner / INBOX thread
ERR_KEY = "__errors__"                # {filename: consecutive_fail_count}
ALERTED_KEY = "__stuck_alerted__"     # [filename, ...] already escalated (dedup)


def telegram_alert(text: str) -> bool:
    """Best-effort OPS alert; never raises (alerting must not break the sync)."""
    import urllib.request  # local import — keeps the no-token path import-free
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return False
    data = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID, "message_thread_id": TELEGRAM_THREAD_ID,
        "text": text, "parse_mode": "HTML", "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=data,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20):
            return True
    except Exception as e:  # noqa: BLE001
        print(f"[bridge] telegram alert failed: {e}", file=sys.stderr)
        return False


def _strip_transcript(raw: str) -> str:
    lines = raw.splitlines()
    cut = len(lines)
    for i, ln in enumerate(lines):
        if any(ln.strip().startswith(m) for m in MARKERS):
            cut = i
            break
    return "\n".join(lines[:cut]).rstrip() + "\n"


def _copy_rsync(f: pathlib.Path, tmp: pathlib.Path) -> None:
    subprocess.run(["rsync", "-a", "--no-perms", str(f), str(tmp)],
                   check=True, timeout=READ_TIMEOUT_S,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _copy_cat(f: pathlib.Path, tmp: pathlib.Path) -> None:
    with open(tmp, "wb") as out:
        subprocess.run(["cat", str(f)], check=True, timeout=READ_TIMEOUT_S,
                       stdout=out, stderr=subprocess.PIPE)


def _copy_dd(f: pathlib.Path, tmp: pathlib.Path) -> None:
    subprocess.run(["dd", f"if={f}", f"of={tmp}", "bs=1m"],
                   check=True, timeout=READ_TIMEOUT_S,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _copy_python(f: pathlib.Path, tmp: pathlib.Path) -> None:
    """Plain in-process read, NO signal.alarm() (the 260619 EDEADLK cause).

    The subprocess timeout that guards the other methods is absent here, so this
    runs last: if the placeholder is going to hard-hang, one of the bounded
    methods above has already had its turn.
    """
    tmp.write_bytes(f.read_bytes())


# Ordered read strategies, tried in turn on EVERY attempt. Each uses a DIFFERENT
# open/read path in the kernel, which is the whole point: a dehydrated GDrive
# placeholder that raises EDEADLK through one path often succeeds through another.
COPY_METHODS = (
    ("rsync", _copy_rsync),
    ("cat", _copy_cat),
    ("dd", _copy_dd),
    ("python", _copy_python),
)


def _read_via_copy(f: pathlib.Path) -> str:
    """Read f out of FUSE through an escalating list of copy methods.

    History of read strategies (each fix exposed the next bug):
      1. in-process read() + signal.alarm() — SIGALRM mid-read raises EDEADLK (260619).
      2. `cp` subprocess (260620) — fcopyfile/clonefile hard-deadlocks on dehydrated
         GDrive placeholder; 260623 DeepSeek report stuck 4 days.
      3. `cat` subprocess (260624) — plain read()/write(), proven faster than cp on the
         260623 file. REGRESSION 260627: cat also raises EDEADLK on some placeholders.
      4. `rsync` subprocess (260627) — rsync uses its own open/read path, proven to
         succeed on the exact file that cat deadlocked on (260627 AI cognitive report).
      5. FULL CHAIN (260723, current) — the 260627 shape nested cat INSIDE rsync's
         `except`, so (a) an rsync TIMEOUT skipped cat entirely, and (b) once both
         rsync and cat hit EDEADLK there was nothing left to try. That is exactly how
         the 260723 LUCK_ALL_THE_WAY_DOWN report stuck for 79 consecutive runs and
         held the live site 3 days stale. dd and a plain in-process read are now in
         the chain (both were verified by hand to read that same file cleanly), and
         every method is tried independently of how the previous one failed.

    Raises TimeoutError on a hanging read and OSError on a read failure.
    """
    fd, tmp_name = tempfile.mkstemp(prefix="bridge-", suffix=".md")
    os.close(fd)
    tmp = pathlib.Path(tmp_name)
    try:
        last_err = None
        last_timed_out = False
        for attempt in range(COPY_RETRIES):
            for name, method in COPY_METHODS:
                try:
                    method(f, tmp)
                    return tmp.read_text(encoding="utf-8", errors="replace")
                except FileNotFoundError:
                    # Method's binary isn't installed — not a read failure, skip it.
                    continue
                except subprocess.TimeoutExpired:
                    last_err, last_timed_out = f"{name}: read timeout", True
                except (subprocess.CalledProcessError, OSError) as e:
                    stderr = getattr(e, "stderr", None) or b""
                    msg = stderr.decode("utf-8", "replace").strip() or str(e)
                    last_err, last_timed_out = f"{name}: {msg}", False
            if attempt < COPY_RETRIES - 1:
                time.sleep(COPY_RETRY_BACKOFF_S * (attempt + 1))
        if last_timed_out:
            raise TimeoutError(last_err or "read timeout")
        raise OSError(last_err or "read failed")
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

    # --- Per-file failure tracking + stuck-file escalation (FAIL LOUDLY) -------
    # Rebuild the consecutive-failure map each run: a file not attempted this run was,
    # by construction, not failing (a failing file has no target + no matching state
    # entry, so it is never skipped). A file that reads cleanly simply doesn't reappear
    # here → its count resets to 0. When a file crosses STUCK_RUNS_ALERT we escalate to
    # Telegram ONCE (deduped via ALERTED_KEY) and post a recovery when it clears — this
    # is the alarm that was missing while the 260623 report failed silently for 4 days.
    failing = set(timed_out) | set(errored)
    prev_errs = state.get(ERR_KEY) if isinstance(state.get(ERR_KEY), dict) else {}
    err_counts = {name: prev_errs.get(name, 0) + 1 for name in failing}
    stuck = sorted(n for n, c in err_counts.items() if c >= STUCK_RUNS_ALERT)
    already = set(state.get(ALERTED_KEY) or [])
    new_stuck = [n for n in stuck if n not in already]
    recovered = sorted(already - set(stuck))

    if new_stuck:
        body = "\n".join(f"• {n} ({err_counts[n]} consecutive failed runs)" for n in new_stuck)
        telegram_alert(
            "🚨 <b>OmniMiner bridge STUCK</b> — report(s) generated but NOT publishing:\n"
            + body
            + "\n\nFix: <code>cd ~/Local/APPS/omniminer-reports &amp;&amp; bash rebuild_and_push.sh</code>"
              " — or inspect rebuild.log.")
    if recovered:
        telegram_alert("✅ <b>OmniMiner bridge recovered</b>: "
                       + ", ".join(recovered) + " now publishing.")
    for n in stuck:
        print(f"[bridge] STUCK: {n} ({err_counts[n]} consecutive failed runs)", file=sys.stderr)
    state[ERR_KEY] = err_counts
    state[ALERTED_KEY] = stuck

    try:
        state_path.write_text(json.dumps(state, indent=0, sort_keys=True))
    except OSError as e:
        print(f"[bridge] WARN could not write state: {e}", file=sys.stderr)

    print(f"[bridge] changed={changed} removed={removed} skipped={skipped} "
          f"timeouts={len(timed_out)} errors={len(errored)} stuck={len(stuck)} "
          f"elapsed={time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
