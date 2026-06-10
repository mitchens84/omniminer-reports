#!/bin/bash
# rebuild_and_push.sh — SOURCE BRIDGE (260610 rewrite).
#
# Build, deploy, and Telegram notification now run in GitHub Actions
# (.github/workflows/build.yml). This script's ONLY remaining job is to keep the
# repo's source/ corpus in sync with the private GDrive corpus and push:
#
#   GDrive _SYNC/OMNIMINER/*.md  --(strip transcript)-->  repo source/*.md  --> git push
#       ... GitHub Actions then builds (build_site.py), deploys Pages, and sends ONE
#       Telegram message per new report AFTER the page is live.
#
# Privacy: only the distillation is committed — bodies are cut at "## Full Transcript"
# and EXCLUDE_FROM_PUBLIC reports are withheld (and removed from source/ if previously synced).
#
# INTERIM: the durable end-state is n8n committing source/ directly (no Mac in the loop).
# That is blocked on a Contents:write GitHub PAT — the current bws GITHUB_PERSONAL_ACCESS_TOKEN
# is read-only. Once a write-scoped token exists, wire n8n GITHUB_COMMIT -> source/ and retire
# this launchd job (com.mitchens.omniminer-reports-rebuild). See CHANGELOG 260610.
set -uo pipefail

REPO="$HOME/Local/APPS/omniminer-reports"
SRC="$HOME/Library/CloudStorage/GoogleDrive-henspham@gmail.com/My Drive/_SYNC/OMNIMINER"
LOG="$REPO/rebuild.log"
PY="$REPO/.venv/bin/python"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

cd "$REPO" || { log "ERROR: repo dir missing"; exit 1; }
[ -x "$PY" ] || PY="python3"
[ -d "$SRC" ] || { log "GDrive source not mounted; skip"; exit 0; }

"$PY" - "$SRC" "$REPO/source" <<'PY'
import sys, pathlib
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)
MARKERS = ("## Full Transcript", "## Transcript", "## Raw Transcript")
for f in sorted(src.glob("*.md")):
    raw = f.read_text(encoding="utf-8", errors="replace")
    target = dst / f.name
    if "EXCLUDE_FROM_PUBLIC" in raw:
        if target.exists():
            target.unlink()          # withdraw a previously-synced excluded report
        continue
    lines = raw.splitlines()
    cut = len(lines)
    for i, ln in enumerate(lines):
        if any(ln.strip().startswith(m) for m in MARKERS):
            cut = i
            break
    target.write_text("\n".join(lines[:cut]).rstrip() + "\n", encoding="utf-8")
PY

if [ -n "$(git status --porcelain source)" ]; then
  git add source
  git commit -q -m "Sync source corpus from GDrive" \
    -m "Auto-bridge; build + deploy + Telegram notify run in GitHub Actions." \
    -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  if git push -q origin main >> "$LOG" 2>&1; then
    log "Pushed source/ changes (GitHub Actions will build, deploy, and notify)."
  else
    log "ERROR: git push failed."
    exit 1
  fi
else
  log "source/ unchanged; nothing to push."
fi
