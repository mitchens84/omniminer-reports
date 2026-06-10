#!/usr/bin/env python3
"""Send ONE Telegram message per newly-added report, after a successful Pages deploy.

Identifies the reports added by the triggering push (git diff of source/ between the
push's before/after SHAs), looks each up in the freshly-built manifest by `src_file`,
and posts the live report URL to the HENSPHAM OmniMiner thread. Because this runs as
the final step of the deploy job, the link it sends is already live — fixing the old
race where n8n texted the URL before the page existed.

Usage: notify.py <before_sha> <after_sha>
Env:   TELEGRAM_BOT_TOKEN (GitHub Actions secret)
"""
import json
import os
import pathlib
import subprocess
import sys
import urllib.parse
import urllib.request

CHAT_ID = "-1003961257879"   # HENSPHAM supergroup
THREAD_ID = 157              # OmniMiner reports topic
SITE = "https://mitchens84.github.io/omniminer-reports/"
REPO = pathlib.Path(__file__).resolve().parents[2]


def changed_sources(before: str, after: str) -> list[str]:
    if not before or not after or before.strip("0") == "":
        return []
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=AM", before, after, "--", "source/"],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return []
    return [pathlib.Path(p).name for p in out.split() if p.strip().endswith(".md")]


def send(token: str, text: str) -> bool:
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "message_thread_id": THREAD_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "false",
    }).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r).get("ok", False)
    except Exception as e:  # noqa: BLE001
        print(f"send error: {e}")
        return False


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> int:
    before = sys.argv[1] if len(sys.argv) > 1 else ""
    after = sys.argv[2] if len(sys.argv) > 2 else ""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("no TELEGRAM_BOT_TOKEN; skip")
        return 0
    names = changed_sources(before, after)
    if not names:
        print("no newly-added source reports in this push; nothing to notify")
        return 0
    manifest = json.loads((REPO / "docs" / "manifest.json").read_text())
    by_src = {r.get("src_file"): r for r in manifest.get("reports", [])}
    sent = 0
    for n in names:
        r = by_src.get(n)
        if not r:
            print(f"WARN: {n} absent from manifest (excluded / quality-gated); skip")
            continue
        url = f"{SITE}reports/{r['slug']}.html"
        text = (f"\U0001F4DA <b>{esc(r['title'])}</b>\n\n"
                f"\U0001F310 Read the full report:\n{url}\n\n"
                f"\U0001F50E All reports: {SITE}")
        if send(token, text):
            sent += 1
            print(f"notified: {r['slug']}")
        else:
            print(f"ERROR notifying: {r['slug']}")
    print(f"done; sent={sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
