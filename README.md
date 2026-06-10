# OmniMiner Reports

Auto-published rendered HTML distillations from the OmniMiner pipeline.
Published site: https://mitchens84.github.io/omniminer-reports/

- Source for Pages: **GitHub Actions** (`.github/workflows/build.yml` builds `docs/` from `source/` and deploys)
- Publish model: publish-all by default; per-report `EXCLUDE_FROM_PUBLIC` kill switch + `exclude.txt`
- Report bodies are the distillation only (no raw transcript, no private notes/metadata)

## Build

```bash
python3 build_site.py            # reads _SYNC/OMNIMINER, rebuilds ./docs
python3 build_site.py --limit 20 # quick test on the 20 newest reports
python3 build_site.py --source /path/to/reports
```

`build_site.py`:
- reads OmniMiner reports from the `_SYNC/OMNIMINER` GDrive folder (both the legacy
  `*_complete.md` and the V7 `*-REPORT-OMNIMINER.md` YAML-frontmatter formats);
- **strips everything from `## Full Transcript` onward** so only the distillation is published;
- classifies each report into an LBS-aligned topic bucket (AI & Technology, Health &
  Nutrition, Money & Economics, Mind & Philosophy, Productivity & Knowledge, Society &
  Culture, General) by keyword score, falling back to the report's `lbs` frontmatter;
- dedupes GDrive ` (N)` copies (keeps the largest);
- emits `docs/index.html` (search + topic filter), one `docs/reports/<slug>.html` per
  report, `docs/assets/om.css`, and `docs/manifest.json`.

Idempotent — re-run to rebuild from scratch.

## Privacy & quality gates

1. Transcript truncation at `## Full Transcript` (automatic).
2. `EXCLUDE_FROM_PUBLIC` marker anywhere in a report's source `.md`.
3. `exclude.txt` — one report slug per line.
4. **Quality gate** — a report is skipped if its distillation is a failed generation:
   raw unexecuted tool-call output (`<function_calls>…`), an "unprocessable/unparseable
   transcript", or an effectively empty body (<350 chars of prose). Such source files
   should be quarantined and re-fired via the Airtable `TRANSCRIBE` button.

Categories shown to readers are general-audience plain English (AI & Technology,
Health & Nutrition, Mind & Philosophy, Money & Business, Society & Culture,
Productivity & Learning, General) — **not** the internal LBS codes. Each report's
LBS code is still emitted in `manifest.json` for downstream use (e.g. the website).

**This repo is public.** Publishing is a deliberate act: rebuild, review, then
`git push`. See `00-MASTER/00-KERNEL/PROC-OMNIMINER_TRIGGER.md` §9.

## Publish (automated, 260610)

Publishing is now a CI pipeline — no manual rebuild, and the Telegram link is only
sent **after** the page is live (fixing the old premature-URL race):

```
report processed (n8n)
  -> archive .md uploaded to GDrive _SYNC/OMNIMINER
  -> rebuild_and_push.sh (launchd bridge): strip transcript -> source/<name>.md -> git push
  -> GitHub Actions (.github/workflows/build.yml):
       build_site.py --source source -> deploy Pages -> ONE Telegram message per new report
```

- `source/` holds the **transcript-free** distillation `.md` corpus (the only thing the
  public repo ever contains — transcripts stay in the private GDrive archive).
- `.github/scripts/notify.py` posts the live report link to the HENSPHAM OmniMiner
  thread (157) using the `TELEGRAM_BOT_TOKEN` Actions secret, diffing the push for new
  `source/` files.

Manual rebuild still works for testing: `python3 build_site.py --source source`.

**Interim note:** the `rebuild_and_push.sh` bridge runs on the Mac (launchd
`com.mitchens.omniminer-reports-rebuild`). The durable end-state is n8n committing
`source/` directly (no Mac in the loop) — blocked on a Contents:write GitHub PAT
(the current bws token is read-only). See OmniMiner `CHANGELOG.md` 260610.
