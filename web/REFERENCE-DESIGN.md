# Visual reference guides

Status: the first format is published. Mitch subsequently rejected its design as too text-heavy and generic. An illustrated replacement is being reviewed separately; technical and editorial passes did not establish visual acceptance. This remains an optional format, not a redesign of every existing report.

## Purpose and composition

Help a phone reader grasp the answer in a few minutes and inspect its basis without leaving the guide. Start with the question and supported conclusions. Use a visual for a comparison, relationship or sequence, not merely to fill space. Keep methods and source detail expandable; keep any qualification that changes the conclusion beside its visual.

Retain OmniMiner attribution and navigation. Choose visual direction for the particular story; do not force every guide into the first example's system font and teal palette. Establish hierarchy with scale, spacing and a deliberate contrast region. Avoid repeated icon-card grids, ornamental charts, fake confidence percentages and motion on every scroll section.

## Reusable components

- Front matter: `report_schema: 3`, `content_kind: reference guide`, `presentation: visual-reference`.
- `web/visual-reference.css`: responsive composition, source disclosures, direct chart labels, motion tokens, print and reduced-motion states.
- `web/visual-reference.js`: source-fed comparison explorer, optional three-question walkthrough, motion preference and deep-link disclosure opening.
- Each `[data-comparison-chart]` carries a `.vr-chart-data` JSON block with labels, exact values, units, baseline, metric scale, sample counts and source metadata. Reject invalid data rather than invent a substitute.
- Keep a complete default chart and a data table in the source HTML. JavaScript enhances a usable reference. Never make source access or core conclusions depend on playback.

The first guide is a worked example. Its metric keys and food categories are content, not hard-coded behaviour in the renderer.

## Selecting approaches and skills

| Need | Preferred route | Why / boundary |
|---|---|---|
| A few comparisons in an existing static library | Semantic HTML + CSS + small native JavaScript | Inspectable, portable, no external runtime; the route used here |
| Dense exploratory data or statistical grammar | Existing ECharts / Vega-Lite route; evaluate Observable Plot where its grammar fits | Do not add a second chart engine for a four-row comparison |
| Interface composition and refinement | Impeccable + existing design system | Layout, hierarchy, interaction and responsive critique |
| Quantitative encoding and uncertainty | Data visualize-data guidance + STD-DATAVIZ | Common baselines, honest samples, readable units and sources; retain the user-selected publishing surface |
| Longer choreographed web sequences | Motion or GSAP when native animation becomes hard to maintain | Introduce a dependency only for a real sequencing need |
| Standalone narrated/video explainer | studio-pipeline motion-design branch | Storyboard, exact script, editable composition, captions, audio and full playback review |
| Research and editorial structure | research-analyst + content-architect | Evidence appraisal and useful reading order precede production |

## Motion contract

Every movement names the change it explains. This guide uses 420 ms chart transitions to connect metric states and an explicitly started, silent 12-second walkthrough. It does not auto-play, hijack scrolling, simulate health outcomes or count up fabricated intermediate facts.

- Default core content is visible. No reveal gate.
- Prefer transform/opacity; avoid reflow on every frame.
- Respect `prefers-reduced-motion` and offer a page control. Cancel running animations when reduction is enabled.
- Keep keyboard/touch operation, visible values and data-table access equivalent.
- Pause timed walkthroughs when the tab is hidden; provide a stop button.
- Verify changed values, units, scales, comparison sentence and accessibility text together.

## Bounded acceptance check

Inspect at 320/390 and desktop widths; test each metric, comparator and source disclosure; check no horizontal overflow; compare source numbers against rendered labels and the table; test playback stop and reduced motion; verify the published index and final page. Do not claim device frame-rate profiling, screen-reader testing or clinical validation from these checks.

## Research informing this format (checked 22 September 2026)

- [W3C: animation from interactions](https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions): disable non-essential motion and respect motion sensitivity.
- [Observable Plot accessibility](https://observablehq.github.io/plot/features/accessibility): mark descriptions, chart labels and hiding redundant decorative geometry.
- [Motion animate](https://motion.dev/docs/animate): native-backed animation, SVG paths and sequences; an option for more elaborate composition.
- [GSAP ScrollTrigger](https://gsap.com/docs/v3/Plugins/ScrollTrigger/): scroll-linked sequencing and pinning capability; not necessary for this concise reference.
- [Flourish scrollytelling examples](https://flourish.studio/blog/scrollytelling-examples/): one idea per step, annotations and reader-paced narrative. Vendor design guidance, not independent evidence that animation improves comprehension.

Decision: use reader-controlled comparison and concise progressive disclosure here. Retain long scrollytelling for a story whose sequence genuinely needs it. No paid tool, new account, plugin or external tracking is required.

## Illustrated-story extension (22 September 2026)

For a substantial redesign, explore visibly different illustrated concepts before implementation. Keep image-generation probes distinct from source-backed graphs: the generated mockup's chart labels and study names are not evidence. Generate the selected production art separately, then author all exact text, numeric marks and source links deterministically.

The next candidate uses a generated dog illustration, study-cohort dot figures, three simultaneously visible environmental comparisons and a question-to-evidence interaction. It replaces the timed highlight overview with a reader-triggered relationship animation. It has not replaced the published page and has not received final user acceptance.

The shared production owner is Content Architect's visual-routing reference, linked to Drive `STD-DATAVIZ §13` and `REF-VISUAL_STORY_PRODUCTION.md`. Those documents connect Impeccable, Image Generator, quantitative visualisation and Studio Pipeline without introducing a second publishing controller. Preserve static equivalence, data tables, reduced motion and primary-source provenance.
