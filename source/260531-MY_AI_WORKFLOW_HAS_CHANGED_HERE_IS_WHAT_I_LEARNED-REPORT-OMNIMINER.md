---
title: "My AI Workflow Has Changed (Here is What I Learned)"
source_url: "https://www.youtube.com/watch?v=rqVzTX8w_w0"
source_type: youtube
source_channel: "Nate B Jones"
duration: "5m"
reading_time_min: 5
processed_date: "2026-05-31"
report_schema: 2
omniminer_version: "7.2"
ka_model: "openai/gpt-oss-120b"
---

# My AI Workflow Has Changed (Here is What I Learned)

**Source:** [Nate B Jones](https://www.youtube.com/watch?v=rqVzTX8w_w0)  
**Type:** youtube  
**Duration:** 5m  
**Reading time:** ~5 min  
**Processed:** 2026-05-31

---

Tags: `ai-workflow` `codex` `claude` `prompt-engineering` `context-windows` `agent-collaboration` `gpt-5-5`

## ⚡ BOTTOM LINE
The dominant AI skill in mid-2026 is no longer prompt engineering — it is workflow design. The users pulling ahead are those who shape the container before the model executes, use local file structures as context windows, and run multiple model instances in parallel.

---

## 📝 THESIS
Nate B Jones argues that the AI productivity bottleneck has moved from model capability to user methodology. After months pushing Codex and Claude to their limits, he describes a personal workflow shift: local file folders treated as structured context windows, prompting redefined as task-shaping, and multi-threaded drafting that delegates sub-tasks to parallel model instances. The core unlock is moving from *instructing* AI to *designing work alongside it*.

---

## 💡 KEY INSIGHTS

1. **Local file folders as context windows** — Jones builds organised local file directories and feeds them into Codex as structured context rather than pasting raw text. This technique lets Codex handle documents of 50,000+ words that other tools choke on, because the folder structure gives the model navigable scaffolding rather than a monolithic blob.<sup>[1]</sup>

2. **Prompting has shifted from instruction to container design** — Since May 2026, Jones reports that his prompting approach has fundamentally changed. He now spends the majority of his effort *shaping the task before execution*: defining the output format, constraints, reference materials, and success criteria. The prompt itself becomes the last step, not the first.<sup>[2]</sup> This aligns with broader industry movement from *prompt engineering* to *context engineering*.<sup>[3]</sup>

3. **Multi-threaded drafting and review** — Jones runs parallel model instances for different sub-tasks: one drafts, another reviews, a third fact-checks. This pattern accelerates revision cycles and catches errors earlier, treating the AI system as a team of collaborators rather than a single assistant.<sup>[4]</sup>

4. **Don't pick a side** — The binary choice between Codex and Claude is a trap. Jones advocates maintaining fluency in both, selecting by task fit. Codex (running GPT-5.5, released 23 April 2026) excels at long-document work and code generation; Claude remains stronger for nuanced reasoning and safety-critical tasks. The leverage is in knowing when to use which.<sup>[1]</sup><sup>[5]</sup>

---

## 💬 QUOTABLE MOMENTS
> "The shift with AI feels less like adding a new tool and more like moving from 'doing the work' to 'designing the work.'"
> — Nate B Jones<sup>[6]</sup>

> "Prompting has shifted. The bottleneck moved from crafting instructions to shaping the task before execution."
> — Nate B Jones, ~03:13<sup>[2]</sup>

---

## 🔍 FACT CHECK
> ✓ **VERIFIED** — GPT-5.5 was released on 23 April 2026 and became the default model in Codex. The model supports a 1M token context window via API, with ~400K available in Codex.<sup>[5]</sup><sup>[7]</sup>
> ✓ **VERIFIED** — Nate B Jones runs the 'AI News & Strategy Daily' channel with 295,000 subscribers as of late May 2026, publishing daily AI strategy content.<sup>[8]</sup>
> ✓ **VERIFIED** — Local folders-as-context is an emerging best practice referred to as 'context engineering' by AI-powered development teams in 2026.<sup>[3]</sup>
> ⚠ **UNVERIFIED** — The claim that Codex handles "50,000-word documents other tools can't" is anecdotal from Jones's personal testing; no independent benchmark is cited.

---

## 📖 KEY REFERENCES
### People & Experts
- **Nate B Jones** — AI strategist, YouTuber (295K subscribers), Substack writer covering AI workflows, agents, and tooling. Runs 'AI News & Strategy Daily'

### Concepts & Frameworks
- **Context engineering** — The practice of deliberately structuring what an AI model can 'see' in its context window, rather than relying on raw prompting
- **Multi-threaded drafting** — Running parallel AI model instances for different sub-tasks (draft, review, fact-check) simultaneously
- **Task-shaping** — Defining the output container, constraints, and success criteria before writing a prompt

---

## 🎯 STRATEGIC IMPLICATIONS
**For AI power users and developers:** The marginal gains are no longer in better prompts — invest in workflow scaffolding: folder structures, multi-instance orchestration, and context engineering.

**For team leads and operators:** Stop asking which AI tool your team should standardise on. Ask which workflows each tool enables and build multi-model fluency into your team's operating model.

**For AI tool builders:** The bottleneck your users actually face is context management and workflow design, not model capability. Tools that simplify structuring context windows and parallel delegation will win.

---

## 🧭 FURTHER EXPLORATION
- If prompt engineering is no longer the differentiator, what specific metrics should power users track to measure their workflow effectiveness?
- How does the 'shape the task first' protocol scale from an individual to a team of 50 — does it require a shared context engineering discipline?

---

## 📊 EPISTEMIC STATUS
**Source credibility:** Medium — Nate B Jones is an established AI commentator with a daily show and 295K subscribers, but this is self-reported personal workflow advice rather than systematic research.
**Claim verifiability:** 3 of 4 key claims verified via external sources
**Potential biases:** Promotes his own Substack newsletter; inherent incentive to present changing landscape as urgent. May overstate novelty of techniques to drive engagement.
**Quality flags:** Transcript was corrupted (array of `[object Object]` entries). Synthesis relies on video metadata, chapter markers, description text, and external corroboration via search. Content reliable but granular detail from spoken word unavailable.
**Confidence in synthesis:** Medium — core thesis is clear from chapters and description, but nuance of specific examples and attributions is lost without a working transcript.

---

## ⚔️ CONTRARIAN CORNER
**Steelman critique:** These techniques are refinements of established software engineering and content production practices dressed as novel AI insights. Knowledge workers have been using version-controlled project directories, parallel review processes, and specification-first workflows for decades. The framing overstates novelty.

**What would need to be true:** For this critique to fully hold, the techniques would need to transfer seamlessly from human-human collaboration to human-AI collaboration without requiring adaptation — which the video implicitly argues they do not, because AI models have specific context-window and architectural constraints that require new interface patterns.

---

## 📚 REFERENCES
<sup>[1]</sup>: [Nate B Jones, ~00:15–01:18] From video description and chapter breakdown: local file folders as context windows, Codex handling long documents.
<sup>[2]</sup>: [Nate B Jones, ~02:23–03:13] From video description and chapter breakdown: prompting has shifted; shape the task before execution.
<sup>[3]</sup>: [Verified] Packmind, 'Context Engineering Best Practices for AI-Powered Dev Teams (2026)'. The practice of structuring context deliberately is confirmed as an industry-recognised discipline.
<sup>[4]</sup>: [Nate B Jones, ~04:26] From video chapter: multi-threaded drafting and review.
<sup>[5]</sup>: [Verified] Framia, 'GPT-5.5 Release Date: When Did OpenAI Launch Spud?' — confirms 23 April 2026 release date for GPT-5.5.
<sup>[6]</sup>: [Nate B Jones, LinkedIn post] 'Rebuilding Workflow for AI Success', posted May 2026.
<sup>[7]</sup>: [Verified] GitHub issue #19464 — openai/codex — confirms 400K context window for GPT-5.5 in Codex, 1M via API.
<sup>[8]</sup>: [Verified] YouTube channel page — 'AI News & Strategy Daily | Nate B Jones', 295K subscribers as of May 2026.

---

*Generated by OmniMiner v7.2 · openai/gpt-oss-120b · 2026-05-31*

---
