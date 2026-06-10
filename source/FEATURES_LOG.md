---
title: OmniMiner Features Log
type: LOG
status: ACTIVE
provenance: "Created by Codex after 260608 GitHub Pages + Thai derivative publishing incident."
canonicality: "DERIVED_OPERATIONAL_LOG"
tags:
  - omniminer
  - features
  - multilingual
  - publishing
last_reviewed: 260608
---

# OmniMiner Features Log

Append-only log for user-facing OmniMiner capabilities, workflow affordances, and lessons learned from feature work. `_INDEX.md` remains the processing/routing audit; this file tracks product and publishing behaviour.

## 260608 - Multilingual Reader Derivatives

**Feature:** OmniMiner reports can have language-specific reader derivatives, starting with Thai.

**User value:** A public or shareable OmniMiner report can be converted into a target-language reader version while preserving the source report's structure, caveats, references, and visual treatment.

**Current implementation:** Manual Codex-assisted derivative next to the source report:

- Source report: `260608-THE_FUTURE_OF_FOOD_WITH_BRUCE_FRIEDRICH-REPORT-OMNIMINER.md`
- Thai markdown source: `260608-THE_FUTURE_OF_FOOD_WITH_BRUCE_FRIEDRICH-THAI.md`
- Thai HTML: `260608-THE_FUTURE_OF_FOOD_WITH_BRUCE_FRIEDRICH-THAI.html`
- Thai PDF: `260608-THE_FUTURE_OF_FOOD_WITH_BRUCE_FRIEDRICH-THAI.pdf`
- Public temporary/permanent web sharing path: here.now via `~/Local/AUTOMATION/here-now/here_publish.py`
- Published verified Thai page: `https://spruce-mullet-7wff.here.now/`

**Design contract:**

- Treat translations as derivative reader artifacts, not as canonical source reports.
- Preserve the English report's public-safe structure where possible: source line, tags, report card, key sections, fact-check, references, epistemic status, and contrarian corner.
- Keep source-quality caveats visible in the target language. If the source report says transcript quality was degraded, the translated derivative must not imply direct transcript fidelity.
- Use `lang="<code>"` on HTML output and language-aware font fallback. For Thai and other non-Latin scripts, use Playwright/Chromium-family rendering for PDF; avoid WeasyPrint because it can corrupt Thai/non-Latin text layers.
- When publishing a single-file Here page, inline the report CSS or publish an asset directory. A standalone file cannot rely on `../assets/om.css`.

**Verification checklist:**

- Target-language readability: register is appropriate, technical terms are either standard local usage or intentionally left in English where domain readers expect that.
- Fidelity: section intent matches the English report; no new uncited claims are introduced.
- Rendering: HTML opens cleanly; Thai glyphs render; no tofu boxes; PDF text remains selectable where possible.
- Public link: live URL returns HTTP 200 with a browser-like user agent.

**Lessons learned:**

- The first Thai version was content-readable but visually separate from the English OmniMiner page because it used a PDF-oriented stylesheet. Multilingual derivatives should start from the public report shell, not from a standalone document template.
- The publishing incident was two-layered: the public page URL was announced before the GitHub Pages repo contained the regenerated `docs/` output, and the scheduled rebuild failed because `markdown` was missing from the active Python environment. The reports publisher now creates/uses a repo `.venv` with tracked dependencies.
- The 15-minute launchd watcher should remain enabled so new public report links resolve soon after a report lands, not only after the daily maintenance bundle.
- The quality caveat matters more in translation because target-language readers cannot easily inspect the English source. Put the caveat in the translated epistemic-status block, not only in English metadata.

**Next implementation candidates:**

- Add first-class language variants to `omniminer-reports/build_site.py`, e.g. `docs/reports/<slug>/th.html` plus language switch links.
- Add a translation manifest per source report with `source_slug`, `language`, `status`, `verified_at`, `public_url`, and `source_quality`.
- Move repeated derivative rendering into a script so Thai/Vietnamese/Croatian variants use the same shell and checks.
- Add a TickTick/PPM task template for "verify translated derivative" when a translated report is published externally.
