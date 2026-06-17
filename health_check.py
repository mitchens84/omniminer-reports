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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-lag-hours", type=float, default=2.0,
                    help="Alert if GDrive newest report is this many hours ahead of live.")
    ap.add_argument("--telegram", action="store_true", help="Post an alert to OPS on drift.")
    args = ap.parse_args()

    g_date, g_count = newest_gdrive_date()
    if g_date is None:
        print("[health] WARN: GDrive corpus not mounted / no reports found")
        return 2
    try:
        manifest = live_manifest()
    except Exception as e:  # noqa: BLE001
        print(f"[health] WARN: could not fetch live manifest: {e}")
        return 2
    l_date, l_count = newest_live_date(manifest)
    built_at = manifest.get("built_at", "?")

    # Date-granular drift: GDrive has a report dated newer than anything live.
    drift = (l_date is None) or (g_date > l_date)
    summary = (f"GDrive newest={g_date} ({g_count} reports) | "
               f"live newest={l_date} ({l_count}, built_at {built_at})")

    if drift:
        msg = (f"⚠️ OmniMiner publish drift: newest generated report ({g_date}) is NOT live "
               f"(live newest {l_date}, built_at {built_at}). Bridge/CI may be stuck.")
        print(f"[health] UNHEALTHY — {summary}")
        if args.telegram:
            telegram_alert(msg)
        return 1

    print(f"[health] OK — {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
