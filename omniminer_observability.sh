#!/bin/zsh
# omniminer_observability.sh — daily OmniMiner health run (both sides).
#
# Wrapped by with-secrets.sh under launchd (com.mitchens.omniminer-observability),
# so AIRTABLE_API_KEY (+ other bws keys) are materialised in env before this runs.
# The Telegram bot token lives in the channels .env (not bws), so source it here.
#
# Runs:
#   1. health_check.py     — PUBLISH side: generated-vs-live drift (was the 260614-17 gap)
#   2. pipeline_health.py  — PROCESSING side: per-item errors + per-type path-down
# Both alert (best-effort) to the OmniMiner OPS thread on regression; both always log a
# one-line verdict. Neither aborts the other (so one failing check never masks the other).
set -u
APP="$HOME/Local/APPS/omniminer-reports"
LOG="$APP/observability.log"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Telegram token for alerts (channels .env; matches notify.py target chat/thread).
if [ -f "$HOME/.claude/channels/telegram/.env" ]; then
  export TELEGRAM_BOT_TOKEN="$(grep -E '^TELEGRAM_BOT_TOKEN=' "$HOME/.claude/channels/telegram/.env" | head -1 | cut -d= -f2- | tr -d '"'"'"' ')"
fi

{
  echo "===== omniminer observability $TS ====="
  echo "--- publish drift (health_check.py) ---"
  python3 "$APP/health_check.py" --telegram 2>&1
  echo "publish_exit=$?"
  echo "--- processing health (pipeline_health.py) ---"
  python3 "$APP/pipeline_health.py" --telegram 2>&1
  echo "processing_exit=$?"
  echo ""
} >> "$LOG" 2>&1
