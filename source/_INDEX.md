# OMNIMINER Processing Log

> Lean derived audit for `_SYNC/OMNIMINER/`. Records actions taken on files (route / quarantine / add-to-notebook / skip). The **filesystem** is primary state — a file present here that is NOT in the action log below = extracted but not yet routed.
>
> Counts block is updated by maintenance task B5 (weekly) or on-demand. Action table is append-only; each row represents one per-file or per-batch action.

---

## Counts (as of 260422, post-Plan-A execution)

| Field | Value |
|---|---|
| Total files | 207 (211 pre-plan; 4 quarantined) |
| Markdown reports (`*.md`) | 196 |
| Audio files (`*.mp3`) | 11 |
| Filename duplicates remaining (`(n)` suffix) | 20 (non-AI-cluster; pending future B5) |
| Files routed to notebooks (this pass) | 66 (63 → FRONTIER_OPS, 3 → TECH_FOUNDATIONS) |
| Files quarantined (this pass) | 4 (AI-cluster duplicates) |
| Files logged as archive-read-only (this pass) | 3 (AI industry/economy tangent) |
| Pending routing (non-AI, not yet clustered) | 129 + 20 dups = 149 |
| Last B5 scan | 260422 |

---

## Action Log

_Append-only. One row per file action. Batch actions may use a summary row (see Phase 5 demo entries)._

| Date | Filename | Action | Target | Notes |
|------|----------|--------|--------|-------|
| 260422 | — | BASELINE | — | Created; 211 files enumerated; action log empty |
| 260422 | AI-cluster batch (63 files) | ADD_TO_NOTEBOOK | `6I-CYBORG-AI_FRONTIER_OPERATIONS` | Clusters A-D of AI-competence routing proposal (pilot 3 + batch1 30 + batch2 30); no cap-exceed. Per-file source IDs captured in governance 260422-G response. |
| 260422 | 260418-THE_BRAND_NEW_CLAUDE_DESIGN_EXPLAINED_IN_30_SECONDS-REPORT-OMNIMINER.md | ADD_TO_NOTEBOOK | `6I-CYBORG-TECHNICAL_FOUNDATIONS` | Cluster F |
| 260422 | 260420-THE_CLAUDE_DESIGN_MASTERCLASS_WHAT_NOBODY_IS_TELLING_YOU-REPORT-OMNIMINER.md | ADD_TO_NOTEBOOK | `6I-CYBORG-TECHNICAL_FOUNDATIONS` | Cluster F |
| 260422 | 260421-CLAUDE_DESIGN_SEEDANCE_20_INSANE_ANIMATED_WEBSITES-REPORT-OMNIMINER.md | ADD_TO_NOTEBOOK | `6I-CYBORG-TECHNICAL_FOUNDATIONS` | Cluster F |
| 260422 | 260328-THE_AI_DEMAND_SHOCK-REPORT-OMNIMINER.md | ARCHIVE_READ_ONLY | (stays in `_SYNC/OMNIMINER/`) | Cluster E — AI industry tangent; no notebook route |
| 260422 | 260405-WALL_STREET-REPORT-OMNIMINER.md | ARCHIVE_READ_ONLY | (stays in `_SYNC/OMNIMINER/`) | Cluster E |
| 260422 | 260419-EVERY_TECH_GIANT_IS_BUILDING-REPORT-OMNIMINER.md | ARCHIVE_READ_ONLY | (stays in `_SYNC/OMNIMINER/`) | Cluster E |
| 260422 | 260410-ANTHROPIC_FEATURE_NOBODY_KNEW (1).md | QUARANTINE | `_QUARANTINE/260422-OMNIMINER-DUP-ANTHROPIC_FEATURE_NOBODY_KNEW (1).md` | Filename-dup of canonical |
| 260422 | 260410-EP_752_MYTHOS (1).md | QUARANTINE | `_QUARANTINE/260422-OMNIMINER-DUP-EP_752_MYTHOS (1).md` | Filename-dup |
| 260422 | 260410-EP_752_MYTHOS (2).md | QUARANTINE | `_QUARANTINE/260422-OMNIMINER-DUP-EP_752_MYTHOS (2).md` | Filename-dup |
| 260422 | 260411-CLAUDE_CODE_SKILLS_20 (1).md | QUARANTINE | `_QUARANTINE/260422-OMNIMINER-DUP-CLAUDE_CODE_SKILLS_20 (1).md` | Filename-dup |

---

## Scan recipes

**Find unrouted files older than N days**:
```bash
find _SYNC/OMNIMINER/ -name "*.md" -not -name "_INDEX.md" -mtime +N
```
Then cross-check against this log — anything matched by find but not in the action log = unrouted.

**List duplicates**:
```bash
ls _SYNC/OMNIMINER/ | grep " (1)"
```

**Count by YYMMDD prefix** (oldest first):
```bash
ls _SYNC/OMNIMINER/ | grep -oE "^[0-9]{6,8}" | sort | uniq -c | sort -n
```

---

## Routing targets

For AI-competence content (test-case in Plan A Phase 4):
- **Existing notebook candidates**: `6I-CYBORG-AI_FRONTIER_OPERATIONS` (currently 20 sources)
- **New notebook proposal** (pending Phase 4 analysis): `6I-CYBORG-AI_COMPETENCE` or similar
- **Archive route**: `00-AREA/6I-CYBORG/00-RESOURCES/` sub-folder

For non-AI content: per topic cluster → appropriate LBS area `00-RESOURCES/` or matching NotebookLM notebook.

---

## Related

- Feature log: `_SYNC/OMNIMINER/FEATURES_LOG.md`
- Plan: `99-PLANS/260422-0A-SYS-SYNC_TRACKING_NOTEBOOKLM_ROUTING-PLAN.md`
- Standard: `00-MASTER/03-STANDARDS/STD-TOOL_NOTEBOOKLM.md §4.2` (tier model)
- Maintenance: `00-MASTER/02-AUTOMATION/MAINTENANCE_CHECKLIST.md` B5
- Quarantine protocol: `00-MASTER/03-STANDARDS/STD-FILE_HYGIENE.md §1`
- Registry: `00-MASTER/00-INDEXES/INDEX_SYNC.md`

---

## ⚠️ V7 hallucination period (260513–260519) — quarantine action 260520

**13 YouTube-source reports from this window were largely hallucinated** and have been quarantined to `~/Local/QUARANTINE/260520/omniminer-v7-hallucinated-youtube/` (with NOTES.md explaining). Root cause: V7's KNOWLEDGE_ARCHITECT prompt expression treated Supadata's transcript content array as a string → AI received `[object Object],...` garbage → confabulated reports from title + Airtable DESCRIPTION field only. The Antigravity report (260518) admitted this explicitly in its Epistemic Status: *"Quality flags: Transcript unavailable; analysis based on video description and presenter summary."*

**Bug fixed 260520** — KA prompt updated to convert content array to flat text. Future YouTube reports use real transcripts. Verified end-to-end on Caitlin Kalinowski / Lenny's Newsletter (exec #6389, 3m 25s, 2810 transcript segments processed) and Paul Graham / "How to Start Google" via Mode C article path (exec #6396, 74s).

**Unaffected by the bug** (KEPT in this folder):
- Podcast reports from the same period (AssemblyAI returns flat string, different code path)
- Article reports from the same period (Jina Reader returns flat text, different code path)
- All pre-260513 reports (V6 era, different workflow)
- Post-260520 reports (post-fix)

Full diagnostic detail: `_MEMORY/system_omniminer_v7_1.md` and `00-MASTER/00-KERNEL/PROC-OMNIMINER_TRIGGER.md` v2.0+.

---

*File version: 1.1 | Created: 260422 | Updated: 260520 (V7 hallucination quarantine notice)*
