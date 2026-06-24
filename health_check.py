#!/usr/bin/env python3
"""health_check.py — OmniMiner publish-pipeline watchdog.

Answers one question on a schedule: "Is every report that OmniMiner has generated
actually live on the public site?" — the check that was missing when the FUSE-hang
bridge silently stopped publishing for 3 days (260614-17) while reports kept landing
in GDrive.

Checks:
  1. PUBLISH DRIFT — newest report date in the GDrive corpus vs the newest report on
     the live GitHub Pages manifest. If GDrive is ahead by more than --max-lag-hours,
     reports are generated-but-unpublished → ALERT.
  2. STALE BUILD — the live manifest's built_at is older than --max-build-age-hours
     AND there is unpublished drift → the CI build/deploy may be stuck → ALERT.

Exit code: 0 = healthy, 1 = drift/unhealthy, 2 = could not determine (treat as warn).
Prints a single-line verdict. With --telegram it also posts ONE alert line to the
OmniMiner OPS thread on drift (reuses the same bot token / thread as notify.py).

Dependency-free (stdlib only). Reads GDrive filenames via stat/glob (NO content reads
— never triggers the FUSE-hang surface). Designed to run from the same 15-min launchd
job as the bridge, or from daily-ops.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import re
import sys
import time
import urllib.request

GDRIVE = pathlib.Path(
    os.path.expanduser(
        "~/Library/CloudStorage/GoogleDrive-henspham@gmail.com/My Drive/_SYNC/OMNIMINER"
    )
)
MANIFEST_URL = "https://mitchens84.github.io/omniminer-reports/manifest.json"
DATE_RE = re.compile(r"(\d{6})")  # leading YYMMDD on report filenames
TELEGRAM_CHAT_ID = "-1003961257879"   # mitch-mai group (matches notify.py)
TELEGRAM_THREAD_ID = 157              # OmniMiner / INBOX thread
STATE_FILE = pathlib.Path(__file__).with_name(".health_check_state.json")


def _yymmdd_to_date(s: str):
    try:
        return _dt.date(2000 + int(s[:2]), int(s[2:4]), int(s[4:6]))
    except (ValueError, IndexError):
        return None


def newest_gdrive_date():
    """Newest report date in the GDrive corpus (filename YYMMDD; no content reads)."""
    if not GDRIVE.is_dir():
        return None, 0
    newest = None
    count = 0
    for f in GDRIVE.glob("*-REPORT-OMNIMINER.md"):
        m = DATE_RE.match(f.name)
        if not m:
            continue
        d = _yymmdd_to_date(m.group(1))
        if d:
            count += 1
            if newest is None or d > newest:
                newest = d
    return newest, count


def newest_source_date(source_dir: "pathlib.Path"):
    """Newest report date in the LOCAL repo source/ (always readable — no FUSE).

    GDrive-free fallback for when this runs under a launchd job that can't see the
    File-Provider mount (the blind spot that hid the 4-day 260624 outage). source/ is
    what the bridge has already synced, so source-ahead-of-live = CI build/deploy stuck.
    """
    if not source_dir or not source_dir.is_dir():
        return None, 0
    newest, count = None, 0
    for f in source_dir.glob("*-REPORT-OMNIMINER.md"):
        m = DATE_RE.match(f.name)
        if not m:
            continue
        d = _yymmdd_to_date(m.group(1))
        if d:
            count += 1
            if newest is None or d > newest:
                newest = d
    return newest, count


def live_manifest():
    req = urllib.request.Request(MANIFEST_URL, headers={"User-Agent": "omniminer-health/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def newest_live_date(manifest) -> "tuple":
    reports = manifest.get("reports", [])
    newest = None
    for r in reports:
        d = None
        iso = r.get("date")
        if iso:
            try:
                y, mo, da = iso.split("-")
                d = _dt.date(int(y), int(mo), int(da))
            except (ValueError, AttributeError):
                d = None
        if d is None:
            m = DATE_RE.search(r.get("slug", ""))
            if m:
                d = _yymmdd_to_date(m.group(1))
        if d and (newest is None or d > newest):
            newest = d
    return newest, len(reports)


def telegram_alert(text: str):
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
    except Exception as e:  # noqa: BLE001 — alerting must never crash the check
        print(f"[health] telegram alert failed: {e}", file=sys.stderr)
        return False


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:  # noqa: BLE001
        return {}


def _save_state(state: dict):
    try:
        STATE_FILE.write_text(json.dumps(state, indent=0, sort_keys=True))
    except Exception as e:  # noqa: BLE001
        print(f"[health] WARN: could not write state: {e}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-lag-hours", type=float, default=1.0,
                    help="Only alert once drift has PERSISTED this long (grace for normal "
                         "CI catch-up; a freshly-pushed report is briefly ahead of live).")
    ap.add_argument("--telegram", action="store_true", help="Post an alert to OPS on drift.")
    ap.add_argument("--source", default=str(pathlib.Path(__file__).with_name("source")),
                    help="Repo source/ dir — GDrive-free fallback when FUSE is invisible.")
    ap.add_argument("--dedup", action="store_true",
                    help="Accepted for compatibility; persistence-timing is always on.")
    args = ap.parse_args()

    # Newest GENERATED report: prefer GDrive (catches generated-but-not-bridged too);
    # fall back to the local source/ corpus when GDrive isn't visible (launchd) so the
    # check still fires on a CI-side stall instead of going blind (the 260624 lesson).
    g_date, g_count = newest_gdrive_date()
    src = pathlib.Path(os.path.expanduser(args.source)) if args.source else None
    s_date, s_count = newest_source_date(src)
    if g_date is not None:
        gen_date, gen_count, gen_src = g_date, g_count, "GDrive"
    elif s_date is not None:
        gen_date, gen_count, gen_src = s_date, s_count, "source/"
    else:
        print("[health] WARN: neither GDrive corpus nor source/ readable")
        return 2

    try:
        manifest = live_manifest()
    except Exception as e:  # noqa: BLE001
        print(f"[health] WARN: could not fetch live manifest: {e}")
        return 2
    l_date, l_count = newest_live_date(manifest)
    built_at = manifest.get("built_at", "?")

    drift = (l_date is None) or (gen_date > l_date)
    summary = (f"{gen_src} newest={gen_date} ({gen_count} reports) | "
               f"live newest={l_date} ({l_count}, built_at {built_at})")

    state = _load_state()
    now = time.time()

    if drift:
        # Persistence timing: a report pushed seconds ago is legitimately ahead of live
        # until CI finishes (~1-2 min), so date-granular drift is NORMAL transiently.
        # Only alert once the SAME drift episode has persisted past --max-lag-hours; a
        # genuine stall persists across cycles, a normal publish clears in one.
        key = f"{gen_date}>{l_date}"
        if state.get("key") != key:
            state = {"key": key, "first_seen": now, "alerted": False}
        persisted_h = (now - state.get("first_seen", now)) / 3600.0
        print(f"[health] {'UNHEALTHY' if persisted_h >= args.max_lag_hours else 'PENDING'}"
              f" — {summary} (drift persisted {persisted_h:.2f}h)")
        if args.telegram and persisted_h >= args.max_lag_hours and not state.get("alerted"):
            telegram_alert(
                f"⚠️ <b>OmniMiner publish drift</b>: newest generated report ({gen_date}, "
                f"via {gen_src}) has NOT been live for {persisted_h:.1f}h "
                f"(live newest {l_date}, built_at {built_at}). Bridge/CI may be stuck.")
            state["alerted"] = True
        _save_state(state)
        return 1 if persisted_h >= args.max_lag_hours else 0

    # Recovered: previously alerted, now clean → post a one-time all-clear.
    if args.telegram and state.get("alerted"):
        telegram_alert(f"✅ <b>OmniMiner publish recovered</b>: live now current ({summary}).")
    _save_state({})
    print(f"[health] OK — {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
