#!/usr/bin/env python3
"""pipeline_health.py — OmniMiner PROCESSING-side observability.

Sibling to health_check.py (which watches the PUBLISH side: generated-vs-live).
This watches the PROCESSING side — the gap that let the YouTube path stay silently
broken for days (260618-20): a per-content-type pipeline regression with no canary
and no per-item error surfacing.

Two modes:

  (default) SCAN — read the three OmniMiner content tables in Airtable and surface
      per-item failures + per-type path-down regressions. Cheap (Airtable REST only),
      daily-safe. State-deduped so it only Telegram-pings on NEW errors / new path-down,
      not on the standing backlog.

  --e2e     CANARY — actively drive ONE item per content type through the LIVE pipeline
      via the dispatch CLI and confirm each reaches STATUS=Completed. Expensive
      (real LLM calls + AssemblyAI for the podcast) → run weekly or after any workflow
      edit, NOT daily. This is the active per-path proof that catches a regression
      regardless of how the workflow was changed (the n8n API key isn't available to a
      headless script, so a version-drift watch isn't possible here; E2E covers it).

Exit: 0 = healthy, 1 = unhealthy (errors / path-down / ingestion stale / canary fail),
2 = could not run (no API key, or corpus freshness could not be determined).
Alerts (best-effort, never crash the check) go to the same OPS thread as health_check.py
when TELEGRAM_BOT_TOKEN is set. Stdlib only.

Contract sources: STD-TOOL_OMNIMINER.md, CHANGELOG.md (260620 YouTube fix entry).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import subprocess
import sys
import urllib.parse
import urllib.request

BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "appnXs8cMG8FXpIes")  # 6I-LEARNING
TABLES = {
    "youtube": "tblJQWaCHHgFHM6Lo",  # YOUTUBE_VIDEOS
    "podcast": "tbll8rChOHLtiJJ9Q",  # PODCASTS_EPISODES
    "article": "tblu49WpeYPbhfp8e",  # ARTICLES
}
TELEGRAM_CHAT_ID = "-1003961257879"  # mitch-mai group (matches notify.py / health_check.py)
TELEGRAM_THREAD_ID = 157             # OmniMiner / INBOX thread
STATE_FILE = pathlib.Path(__file__).with_name(".pipeline_health_state.json")
DISPATCH_CLI = pathlib.Path(
    os.path.expanduser(
        "~/Local/AUTOMATION/N8N-WORKFLOWS/0A-PKM-OMNIMINER/bin/omniminer_dispatch.py"
    )
)
# Stable canary records (one per type) used by --e2e. Force-refired so they never
# create new rows. Chosen 260620: short, on-interest, known-good content.
CANARY = {
    "youtube": ("rec59jcfdbGbVrtyU", TABLES["youtube"]),   # Huberman deep-sleep (260620 fix proof)
    "article": ("rectXQo2wep3QHgLN", TABLES["article"]),   # Anthropic "Building Effective Agents"
    "podcast": ("recFVd93lP2LGBwkj", TABLES["podcast"]),   # Ep802 AI-news (short → fast AssemblyAI)
}
RECENT_WINDOW = 8   # of the last N records per type, used for path-down detection
PROCESSING_STATES = {"Processing", "Requested", "In Progress"}

# --- Ingestion staleness (added 260910) -------------------------------------
# The scan above scores only records that ALREADY EXIST, so a TOTAL ingestion outage
# produces no Error rows and no path-down, and this check printed "OK" for 15 straight
# days while nothing whatsoever was produced (observability.log 260910 08:40; newest
# report 2026-08-26; the n8n producer had no executor at all). A probe that scores only
# history cannot see an outage — it needs an absolute freshness term.
#
# Age is measured from the report FILENAME date (YYMMDD), never from mtime: source/
# mtimes are MIRROR-COPY times (newest mtime 2026-09-02 for the 2026-08-26 report), so
# an mtime-based age would have understated this stall by 7 days.
#
# 10 days ~= 2x the observed pre-stall cadence (Aug 5 -> 12 -> 22 -> 26, i.e. 4-10 day
# gaps), so an ordinary drought does not trip it but a dead producer does.
MAX_REPORT_AGE_DAYS = 10


def _api_key() -> str:
    k = os.environ.get("AIRTABLE_API_KEY", "")
    if not k:
        print("[pipeline] WARN: AIRTABLE_API_KEY not set", file=sys.stderr)
    return k


def _at_get(table_id: str, params: dict) -> dict:
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table_id}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {_api_key()}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_records(table_id: str, max_records: int = 100) -> list:
    """Most-recent records (by createdTime desc), capped."""
    out = []
    params = {"pageSize": "100", "sort[0][field]": "CREATED", "sort[0][direction]": "desc",
              "maxRecords": str(max_records)}
    try:
        data = _at_get(table_id, params)
    except Exception:
        # CREATED field may not exist on every table — fall back to default order.
        try:
            data = _at_get(table_id, {"pageSize": "100", "maxRecords": str(max_records)})
        except Exception as e:  # noqa: BLE001
            print(f"[pipeline] WARN: fetch failed for {table_id}: {e}", file=sys.stderr)
            return out
    for r in data.get("records", []):
        f = r.get("fields", {})
        title = f.get("TITLE") or f.get("Title") or f.get("Name") or "(untitled)"
        # Skip quarantine-tagged rows (CP10 🗑️ DELETE_ prefix) — marked-for-removal
        # test/invalid artifacts, not real pipeline failures.
        if str(title).lstrip().startswith("🗑️ DELETE_") or "DELETE_" in str(title)[:20]:
            continue
        out.append({
            "id": r["id"],
            "status": (f.get("STATUS") or "").strip(),
            "title": str(title)[:60],
            "link": f.get("LINK") or f.get("URL") or f.get("AUDIO_URL") or "",
            "created": r.get("createdTime", ""),
        })
    return out


def scan() -> tuple:
    """Returns (verdict_lines, error_records, path_down_types)."""
    error_records = []   # list of (type, id, title, link)
    path_down = []       # types whose recent window is all-error / no-completed
    lines = []
    for ctype, tid in TABLES.items():
        recs = fetch_records(tid)
        if not recs:
            lines.append(f"  {ctype:8s}: no records / fetch failed")
            continue
        errs = [r for r in recs if r["status"] == "Error"]
        for r in errs:
            error_records.append((ctype, r["id"], r["title"], r["link"]))
        recent = recs[:RECENT_WINDOW]
        recent_done = sum(1 for r in recent if r["status"] == "Completed")
        recent_err = sum(1 for r in recent if r["status"] == "Error")
        # Path-down: recent activity shows errors but nothing completing.
        if recent_err >= 3 and recent_done == 0:
            path_down.append(ctype)
        lines.append(
            f"  {ctype:8s}: {len(errs)} Error (all-time recent), "
            f"last{len(recent)}: {recent_done}✓ {recent_err}✗"
            + ("  ⚠️ PATH-DOWN" if ctype in path_down else "")
        )
    return lines, error_records, path_down


def check_ingestion_staleness(telegram: bool) -> tuple:
    """Absolute freshness of the watched report corpus. Returns (exit_code, note).

    0 = fresh, 1 = STALE, 2 = UNKNOWN. NEVER returns 0 for a corpus it could not read:
    an unreadable corpus cannot prove freshness, and "could not prove" must not be
    reported as health. Reuses health_check.py's readers (sibling module, same dir) so
    the date parsing has exactly one implementation.

    Corpus preference matches health_check.py: GDrive first (sees generated-but-not-
    bridged reports too), local source/ as the fallback for launchd runs where the
    File-Provider mount is invisible.
    """
    try:
        from health_check import newest_gdrive_date, newest_source_date
    except Exception as e:  # noqa: BLE001
        return 2, f"UNKNOWN — cannot load corpus readers ({e})"

    newest = count = None
    corpus = ""
    try:
        g_date, g_count = newest_gdrive_date()
        if g_date is not None:
            newest, count, corpus = g_date, g_count, "GDrive"
        else:
            s_date, s_count = newest_source_date(pathlib.Path(__file__).with_name("source"))
            if s_date is not None:
                newest, count, corpus = s_date, s_count, "source/"
    except Exception as e:  # noqa: BLE001
        return 2, f"UNKNOWN — corpus read failed ({e})"

    if newest is None:
        return 2, "UNKNOWN — neither GDrive corpus nor source/ readable (freshness unprovable)"

    age = (_dt.date.today() - newest).days
    if age <= MAX_REPORT_AGE_DAYS:
        return 0, f"fresh — newest={newest} age={age}d (via {corpus}, {count} reports)"

    note = (f"STALE — newest={newest} age={age}d "
            f"(> {MAX_REPORT_AGE_DAYS}d, via {corpus}, {count} reports)")
    # Alert once per stalled newest-date, not once per day (matches the error-dedup
    # discipline above). Persisted here; run_scan merges rather than overwrites.
    if telegram:
        st = load_state()
        if st.get("stale_alerted_for") != str(newest):
            if telegram_alert(
                    f"⚠️ <b>OmniMiner ingestion STALE</b> — newest report {newest} is "
                    f"{age}d old (> {MAX_REPORT_AGE_DAYS}d). Nothing new has entered the "
                    f"corpus; the producer may have no executor."):
                st["stale_alerted_for"] = str(newest)
                save_state(st)
    return 1, note


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"known_error_ids": [], "path_down": []}


def save_state(state: dict):
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:  # noqa: BLE001
        print(f"[pipeline] WARN: could not write state: {e}", file=sys.stderr)


def telegram_alert(text: str) -> bool:
    # OPERATOR MUTE (260808): shared kill-switch with persist_notify.classify().
    # This emitter bypasses the tg-send.sh/tg-alert.sh classifier, so it honours the
    # mute file directly. Restore by deleting ~/.claude/channels/telegram/ALERTS-MUTED
    import pathlib as _pl
    if (_pl.Path.home() / ".claude/channels/telegram/ALERTS-MUTED").exists():
        return False
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
        print(f"[pipeline] telegram alert failed: {e}", file=sys.stderr)
        return False


def run_scan(telegram: bool) -> int:
    # Ingestion freshness FIRST, and INDEPENDENT of Airtable: a dead producer must stay
    # visible even when the content-type scan cannot run at all (260908: no API key ->
    # exit 2, and not one word about the ingestion outage already in progress).
    stale_rc, stale_note = check_ingestion_staleness(telegram)
    print(f"[ingestion] {stale_note}")

    if not _api_key():
        print("[pipeline] SCAN SKIPPED — AIRTABLE_API_KEY not set "
              f"(content-type scan did not run; ingestion: {stale_note})")
        return 2

    lines, error_records, path_down = scan()
    state = load_state()
    known = set(state.get("known_error_ids", []))
    cur_err_ids = {rid for (_, rid, _, _) in error_records}
    new_errors = [e for e in error_records if e[1] not in known]
    new_path_down = [t for t in path_down if t not in set(state.get("path_down", []))]

    print("[pipeline] per-type health:")
    for ln in lines:
        print(ln)

    # Only PING on something new (avoid daily spam on a standing backlog).
    if telegram and (new_errors or new_path_down):
        parts = ["⚠️ <b>OmniMiner pipeline</b>"]
        if new_path_down:
            parts.append("PATH-DOWN: " + ", ".join(new_path_down))
        if new_errors:
            parts.append(f"{len(new_errors)} new error(s):")
            for ctype, rid, title, _ in new_errors[:8]:
                parts.append(f"• [{ctype}] {title}")
        telegram_alert("\n".join(parts))

    # Merge, don't overwrite: preserves stale_alerted_for written above.
    state.update({"known_error_ids": sorted(cur_err_ids), "path_down": path_down})
    if stale_rc == 0:
        state.pop("stale_alerted_for", None)   # recovered — re-arm the alert
    save_state(state)

    if path_down:
        print(f"[pipeline] UNHEALTHY — path-down: {path_down}")
        return 1
    if error_records:
        print(f"[pipeline] WARN — {len(error_records)} error record(s) standing "
              f"({len(new_errors)} new)")
        return 1
    # A clean content-type scan is NOT health if nothing is arriving. This branch is the
    # whole point of the 260910 patch: the scan below it can only ever score history.
    if stale_rc == 1:
        print(f"[pipeline] UNHEALTHY — ingestion {stale_note}; content-type scan is clean "
              f"but no new content is arriving")
        return 1
    if stale_rc == 2:
        print("[pipeline] UNKNOWN — content-type scan clean, but corpus freshness could "
              "not be proved (see the [ingestion] line above)")
        return 2
    # The OK line can never be printed without naming the freshness it is asserting.
    print(f"[pipeline] OK — all content types healthy; ingestion {stale_note}")
    return 0


def run_e2e(telegram: bool) -> int:
    """Fire one canary per configured type via the dispatch CLI; verify Completed."""
    if not DISPATCH_CLI.is_file():
        print(f"[pipeline] E2E: dispatch CLI not found at {DISPATCH_CLI}")
        return 2
    results = {}
    for ctype, spec in CANARY.items():
        if not spec:
            results[ctype] = "skipped (no canary record pinned)"
            continue
        rec, tbl = spec
        cmd = ["python3", str(DISPATCH_CLI), "--record", rec, "--table", tbl,
               "--force-refire", "--priority"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=1000)
            tail = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ""
            ok = '"status": "completed"' in p.stdout or "Completed" in p.stdout
            results[ctype] = ("PASS " if ok else "FAIL ") + tail[:120]
        except subprocess.TimeoutExpired:
            results[ctype] = "FAIL timeout (>1000s)"
        except Exception as e:  # noqa: BLE001
            results[ctype] = f"FAIL {e}"
    print("[pipeline] E2E canary results:")
    failed = [t for t, r in results.items() if r.startswith("FAIL")]
    for t, r in results.items():
        print(f"  {t:8s}: {r}")
    if telegram and failed:
        telegram_alert("⚠️ <b>OmniMiner E2E canary FAILED</b>: " + ", ".join(failed))
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="OmniMiner processing-side health check.")
    ap.add_argument("--e2e", action="store_true",
                    help="Run the active per-type canary (expensive; weekly/post-edit).")
    ap.add_argument("--telegram", action="store_true", help="Alert to OPS on regression.")
    args = ap.parse_args()
    if args.e2e:
        # E2E genuinely cannot run without Airtable; the scan path now degrades instead
        # (it still reports ingestion freshness, which needs no API key).
        if not _api_key():
            return 2
        return run_e2e(args.telegram)
    return run_scan(args.telegram)


if __name__ == "__main__":
    sys.exit(main())
