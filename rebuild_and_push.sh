#!/bin/bash
# rebuild_and_push.sh — regenerate the OmniMiner reports site and publish if changed.
#
# Trigger: invoked (backgrounded) by the daily-maintenance job
# (~/Local/AUTOMATION/CHANNELS/telegram/bin/daily-maintenance.sh, com.mitchens.daily-maintenance,
# daily 08:00 ICT) — bundled there rather than a standalone daemon. Replaces the retired
# in-workflow GITHUB_COMMIT push node (PROC-OMNIMINER_TRIGGER §9). Idempotent: build_site.py
# rebuilds docs/ from scratch and clears orphan pages; the mtime guard below makes this a
# cheap no-op unless a source .md is newer than the last build.
#
# Publishes to the PUBLIC repo mitchens84/omniminer-reports (privacy gates: transcript
# truncation + quality gate + EXCLUDE_FROM_PUBLIC). Operator-authorised 260606. Safe to run by hand.
set -euo pipefail

REPO="$HOME/Local/APPS/omniminer-reports"
SRC="$HOME/Library/CloudStorage/GoogleDrive-henspham@gmail.com/My Drive/_SYNC/OMNIMINER"
LOG="$REPO/rebuild.log"
MANIFEST="$REPO/docs/manifest.json"
PYTHON_BIN="$REPO/.venv/bin/python"
REQ="$REPO/requirements.txt"
DEPS_STAMP="$REPO/.venv/.deps-ok"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

cd "$REPO"

if [ ! -x "$PYTHON_BIN" ]; then
  log "Creating Python virtualenv."
  python3 -m venv "$REPO/.venv" >> "$LOG" 2>&1
fi

if [ ! -f "$DEPS_STAMP" ] || [ "$REQ" -nt "$DEPS_STAMP" ]; then
  log "Installing Python dependencies."
  "$PYTHON_BIN" -m pip install -q -r "$REQ" >> "$LOG" 2>&1
  touch "$DEPS_STAMP"
fi

# Cheap guard: skip the rebuild entirely if no source .md is newer than the last build.
if [ -f "$MANIFEST" ] && [ -d "$SRC" ]; then
  newer=$(find "$SRC" -name '*.md' -newer "$MANIFEST" -print -quit 2>/dev/null || true)
  if [ -z "$newer" ]; then
    exit 0
  fi
fi

log "Source change detected; rebuilding."
if ! "$PYTHON_BIN" build_site.py --quiet >> "$LOG" 2>&1; then
  log "ERROR: build_site.py failed; aborting (no push)."
  exit 1
fi

# Publish only on a real content change.
if [ -n "$(git status --porcelain docs)" ]; then
  n=$("$PYTHON_BIN" -c "import json;print(json.load(open('$MANIFEST'))['count'])" 2>/dev/null || echo '?')
  git add docs
  git commit -q -m "Rebuild reports site (${n} reports)" \
    -m "Automated rebuild via launchd watcher; supersedes in-workflow GITHUB_COMMIT push." \
    -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  if git push -q origin main >> "$LOG" 2>&1; then
    log "Pushed: ${n} reports."
  else
    log "ERROR: git push failed."
    exit 1
  fi
else
  log "Rebuilt; docs/ unchanged; nothing to push."
fi
