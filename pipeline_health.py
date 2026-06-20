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

Exit: 0 = healthy, 1 = unhealthy (errors / path-down / canary fail), 2 = could not run.
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
    lines, error_records, path_down = scan()
    state = load_state()
    known = set(state.get("known_error_ids", []))
    cur_err_ids = {rid for (_, rid, _, _) in error_records}
    new_errors = [e for e in error_records if e[1] not in known]
    new_path_down = [t for t in path_down if t not in set(state.get("path_down", []))]

    print("[pipeline] per-type health:")
    for ln in lines:
        print(ln)

    unhealthy = bool(error_records) or bool(path_down)
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

    save_state({"known_error_ids": sorted(cur_err_ids), "path_down": path_down})

    if path_down:
        print(f"[pipeline] UNHEALTHY — path-down: {path_down}")
        return 1
    if error_records:
        print(f"[pipeline] WARN — {len(error_records)} error record(s) standing "
              f"({len(new_errors)} new)")
        return 1
    print("[pipeline] OK — all content types healthy")
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
    if not _api_key():
        return 2
    return run_e2e(args.telegram) if args.e2e else run_scan(args.telegram)


if __name__ == "__main__":
    sys.exit(main())
