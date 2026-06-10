---
title: "10 Best CLI Tools for Claude Code"
source_url: "https://youtu.be/uULvhQrKB_c"
author: "Chase Lean (Chase AI)"
duration: "~12:00"
date_published: "2026-03"
date_processed: "260323"
type: video-distillation
format: express-video
lbs: "7A"
goal: "7A-AI_DEV"
---

## 1. BOTTOM LINE

The ecosystem is shifting from MCPs to CLI tools because CLIs share Claude Code's native terminal environment, producing the same capability with dramatically fewer tokens and no context overhead. Knowing which ten tools to install now puts you significantly ahead of the curve for AI-assisted development and content workflows.

---

## 2. RHYTHM MAP

| # | Chapter | Time (approx.) | Duration | Type | Emphasis |
|---|---------|----------------|----------|------|----------|
| 1 | Intro: The CLI shift | 0:00--0:30 | 0:30 | OPINION | High -- "everyone is building CLI tools" |
| 2 | Tool 1: CLI Anything | 0:30--1:45 | 1:15 | EXPLAIN | Medium -- meta-tool framing |
| 3 | Sponsor / CTA | 1:45--2:30 | 0:45 | META | Low |
| 4 | Tool 2: NotebookLM-PI | 2:30--4:30 | 2:00 | EXPLAIN | High -- personal daily use, token savings |
| 5 | Tool 3: Stripe CLI | 4:30--5:15 | 0:45 | EXPLAIN | Medium -- pain-point framing |
| 6 | Tool 4: FFmpeg | 5:15--6:30 | 1:15 | EXPLAIN + DEMO | High -- visual animation example |
| 7 | Tool 5: GitHub CLI | 6:30--7:15 | 0:45 | EXPLAIN | Medium -- "you should already know this" |
| 8 | Tool 6: Vercel CLI | 7:15--8:00 | 0:45 | EXPLAIN | Medium -- free tier + CI/CD framing |
| 9 | Tool 7: Supabase CLI | 8:00--8:30 | 0:30 | EXPLAIN | Low -- brief mention |
| 10 | Tool 8: Playwright CLI | 8:30--10:00 | 1:30 | EXPLAIN + COMPARE | High -- CLI vs MCP benchmark cited |
| 11 | Tool 9: LLM Fit | 10:00--10:45 | 0:45 | EXPLAIN | Medium -- niche but useful |
| 12 | Tool 10: GWS CLI | 10:45--11:30 | 0:45 | EXPLAIN | High -- security caveat + skill selection strategy |
| 13 | Outro: Macro trend | 11:30--12:00 | 0:30 | OPINION | High -- "we're moving away from MCPs" |

**Narrative arc:** Hub-and-spoke. A central thesis (CLIs beat MCPs in the terminal) is stated at the open and close, with each tool as a spoke radiating from that hub. Tools are loosely grouped by domain (multimedia, deployment, backend, browser, AI infra, productivity) but not explicitly signposted.

**Content ratio:** EXPLAIN 65% / OPINION 15% / COMPARE 10% / META (sponsor) 7% / DEMO 3%

---

## 3. KEY INSIGHTS

**1. [0:00--0:30] The CLI-over-MCP paradigm shift** `OPINION`

- **What:** The Claude Code ecosystem is migrating away from MCPs toward CLI tools because both Claude Code and CLIs are native to the terminal, eliminating the protocol overhead MCPs introduce.
- **So what:** This is not a minor preference; Playwright's own benchmark showed CLI execution used ~90,000 fewer tokens than the equivalent MCP for the same task. At scale this is a material cost and latency difference.
- **Now what:** Audit your current MCP stack and identify where a CLI equivalent exists. Prioritise replacing high-frequency MCPs first.

> "Cloud Code lives in the terminal. CLIs live in the terminal. There's no overhead. It's just a straight connection." (Outro)

---

**2. [0:30--1:45] CLI Anything -- a meta-tool that generates CLI tools** `EXPLAIN`

- **What:** CLI Anything (from the makers of LightRAG and RAG Anything) points Claude Code at any open-source project and generates a bespoke CLI tool for it, even when no API exists. Already demonstrated on Blender, Inkscape, OBS, Zoom, NotebookLM.
- **So what:** This dissolves the most common blocker to terminal automation: the absence of an official API. If the project is open source, it is now scriptable.
- **Now what:** Identify any open-source tool you use manually today (video editors, design tools, productivity apps) and test CLI Anything against it as a first integration step.

---

**3. [2:30--4:30] NotebookLM-PI -- bridging Claude Code to video intelligence** `EXPLAIN`

- **What:** No public API exists for NotebookLM, but this CLI tool wraps browser automation to give Claude Code full control: add sources (including YouTube URLs), trigger analysis, and generate all NotebookLM output types (podcasts, slide decks, infographics, quizzes, flashcards).
- **So what:** Claude Code and Sonnet/Opus cannot natively process video. NotebookLM can, and its compute runs on Google's servers at no token cost to the user. This is effectively free video intelligence piped directly into your Claude Code workflow.
- **Now what:** For any video-heavy research workflow (product research, competitor analysis, learning), route YouTube URLs through NotebookLM-PI rather than attempting direct transcript processing. Requires a skill file in addition to the CLI install.

> "These tokens are on Google servers, not ours." (Tool 2 segment)

---

**4. [4:30--5:15] Stripe CLI -- abstracting payment complexity** `EXPLAIN`

- **What:** Stripe's web interface is multi-tab and unintuitive for product configuration. The Stripe CLI exposes all of that through the terminal, letting Claude Code handle product creation and workflow steps that would otherwise require manual navigation across many screens.
- **So what:** The time cost of Stripe configuration is disproportionate to its complexity; it is a UI problem, not a logic problem. A CLI eliminates the UI entirely.
- **Now what:** Still manually verify any transaction-adjacent changes, but delegate all product setup, price creation, and configuration steps to Claude Code via the Stripe CLI.

---

**5. [5:15--6:30] FFmpeg -- multimedia manipulation from the terminal** `EXPLAIN + DEMO`

- **What:** FFmpeg is a library collection for manipulating video, audio, subtitles, and image frames. Demonstrated use case: exploding a keyboard animation video into individual frames to create a scrolling CSS animation; also auto-reversing and stitching video for hero section loops.
- **So what:** Claude Code's out-of-the-box multimedia capability is weak. FFmpeg is the standard tool that closes this gap entirely, covering frame extraction, format conversion, subtitle embedding, and loop generation.
- **Now what:** Any web project with animated assets should default to FFmpeg via Claude Code rather than manual video editing software. A dedicated video breakdown is linked in the original video.

---

**6. [6:30--7:15] GitHub CLI -- the non-negotiable baseline** `EXPLAIN`

- **What:** If you are writing code and pushing to GitHub, the GitHub CLI is mandatory. Claude Code already has strong Git knowledge; adding the CLI makes the full commit/branch/push workflow terminal-native. Installation and authentication are a single guided step.
- **So what:** Switching between terminal and browser for Git operations breaks flow and introduces friction. This tool eliminates that entirely with no meaningful trade-off.
- **Now what:** Install this first if you have not already. It is the foundation all other deployment tools build on.

---

**7. [7:15--8:00] Vercel CLI -- terminal-native CI/CD** `EXPLAIN`

- **What:** Vercel CLI connects to a generous free tier and, combined with GitHub CLI, creates a complete CI/CD pipeline from the terminal. Vercel also publishes a curated skill library covering deployment, browser automation, design, and UI patterns.
- **So what:** The GitHub + Vercel CLI combination replaces the need to touch any web dashboard during a standard deploy cycle.
- **Now what:** Review Vercel's skill library before writing custom deployment skills -- many common patterns are already packaged. Link available in original video description.

---

**8. [8:00--8:30] Supabase CLI -- unified backend from the terminal** `EXPLAIN`

- **What:** Supabase CLI manages both databases and authentication from one terminal interface. As an open-source Firebase alternative, it also supports fully local operation.
- **So what:** Centralising database and auth management in the terminal removes the need to juggle a separate backend dashboard during development.
- **Now what:** Evaluate Supabase as a default backend choice for new projects, particularly if you are already using Vercel on the frontend.

---

**9. [8:30--10:00] Playwright CLI -- browser automation with a benchmark advantage** `EXPLAIN + COMPARE`

- **What:** Playwright CLI lets Claude Code spin up Chrome instances autonomously to test web applications. Playwright's own head-to-head comparison showed the CLI completing equivalent tasks faster and using approximately 90,000 fewer tokens than the Playwright MCP server.
- **So what:** This is the clearest quantitative argument for the CLI-over-MCP thesis. The token saving is not marginal; it is approximately two orders of magnitude in context consumption for browser tasks.
- **Now what:** Replace Playwright MCP with Playwright CLI. Install the companion skill file (one-liner, auto-installs to .claude folder). Explore the full repo if you need advanced automation beyond basic form testing -- the capability depth is significant.

---

**10. [10:00--10:45] LLM Fit -- local model selection made tractable** `EXPLAIN`

- **What:** LLM Fit is a CLI tool that analyses your local hardware and recommends which Ollama models will actually run well on your specific setup. The Ollama model library is enormous and frequently updated, making unaided selection impractical.
- **So what:** Most developers waste time downloading and testing models that are wrong for their hardware. LLM Fit makes local model selection a single command rather than a trial-and-error process.
- **Now what:** Run LLM Fit before any local model experimentation. Referenced in the author's separate "How to run Claude Code locally" video.

---

**11. [10:45--11:30] GWS CLI -- full Google Workspace control with a skills strategy** `EXPLAIN`

- **What:** GWS CLI gives Claude Code access to Gmail, Docs, Sheets, and the broader Google Workspace. Google Workspace Armor provides prompt injection protection. The skill library is extremely large; strategy for selecting which skills to install matters more than the installation itself.
- **So what:** Full Workspace access is genuinely powerful but the skill-selection problem is real: too many skills degrades trigger accuracy. The author's approach -- cloning the repo, letting Claude Code survey it, then discussing which skills match your specific use case -- is the correct way to configure this at scale.
- **Now what:** If security is a concern, use folder filters and email filters to sandbox Claude Code's access scope before granting full Workspace permissions. Do not install all available skills; curate to your actual workflows.

> "Triggering the right one becomes a problem. So this is the kind of repo where... you have a discussion with Claude Code and say: now that you have full visibility into how this works, what would make the most sense for us to install?" (Tool 10 segment)

---

## 4. TECHNICAL REFERENCE

| Item | Detail | Context |
|------|--------|---------|
| CLI Anything | Open-source; from LightRAG/RAG Anything team; two-step install | Tool 1 -- generates CLIs for any open-source project |
| NotebookLM-PI | GitHub CLI tool; browser automation wrapper; requires companion skill file | Tool 2 -- YouTube/video intelligence pipeline |
| Stripe CLI | Official Stripe tooling | Tool 3 -- payment product configuration |
| FFmpeg | Library collection; video/audio/subtitle/frame manipulation | Tool 4 -- multimedia processing |
| GitHub CLI | Official; single-sentence install via Claude Code; OAuth authentication | Tool 5 -- Git workflow terminal-native |
| Vercel CLI | Official; free tier; skill library available at Vercel docs | Tool 6 -- deployment and CI/CD |
| Supabase CLI | Official; open-source; supports local-only operation | Tool 7 -- database + auth backend |
| Playwright CLI | Official; skill one-liner auto-installs to .claude folder | Tool 8 -- browser automation and testing |
| LLM Fit | CLI tool; analyses hardware; recommends compatible Ollama models | Tool 9 -- local model selection |
| GWS CLI | Google Workspace CLI; large skill library; supports access scoping via filters | Tool 10 -- full Google suite control |
| Google Workspace Armor | Google-native prompt injection protection layer | Tool 10 -- security guardrail |

---

## 5. WATCH THESE SEGMENTS

| Timestamp | What happens | Why watch |
|-----------|-------------|-----------|
| ~5:20--6:30 | FFmpeg keyboard animation demo -- video exploded to frames, used as scrolling CSS animation | Only segment with a concrete before/after visual output; shows the real creative application of multimedia CLI tools |
| ~8:30--9:30 | Playwright CLI vs MCP comparison discussion | Clearest articulation of the CLI-over-MCP argument; the 90,000-token benchmark is the key quantitative data point in the entire video |

---

## 6. SKIP THESE

| Timestamp | Content |
|-----------|---------|
| ~1:45--2:30 | Sponsor segment -- Claude Code Masterclass / Chase AI Plus promotion and free community CTA |
| ~11:30--12:00 | Outro -- subscribe prompt and comments CTA (macro trend argument is covered in Insight 1) |

---

## 7. EPISTEMIC STATUS

**Source credibility:** Chase Lean is a practitioner-educator in the Claude Code space with consistent hands-on coverage; not an Anthropic affiliate. Claims are experiential and practical rather than theoretical. The Playwright CLI vs MCP token benchmark is attributed to Playwright's own YouTube channel, which adds credibility but is unverified in this distillation.

**Claim density:** Moderate. Most claims are tool recommendations with light justification. The 90,000-token figure is the only quantitative claim and is second-hand. No academic or technical citations.

**Potential biases:** The author sells a Claude Code course (Chase AI Plus), creating an incentive to keep the content accessible and aspirational rather than deeply technical. Tool selection likely reflects personal workflow rather than systematic evaluation.

**Confidence in synthesis:** High for the tool list and macro trend framing. Medium for the specific token savings figure (needs independent verification against Playwright's benchmark video). Low for the claim that the ecosystem is "moving away from MCPs" wholesale -- this may be overstated; MCPs and CLIs serve different integration patterns.

---

## 8. FURTHER EXPLORATION

1. **CLI vs MCP token economics at scale:** The 90,000-token claim for Playwright is striking. Do other CLI-vs-MCP comparisons show similar ratios? Is this a structural property of the CLI approach or specific to browser automation tasks?

2. **Skill file architecture:** Several tools require companion skill files. What is the optimal structure for managing a large skill file library without degrading trigger accuracy? Is there a principled selection framework beyond "discuss with Claude Code"?

3. **CLI Anything limitations:** The tool is demonstrated on open-source projects. What happens with proprietary desktop software that exposes no API and is not open source? Are there accessibility APIs (macOS Accessibility, Windows UI Automation) that could fill the gap?

4. **Google Workspace Armor in practice:** Prompt injection via email is a realistic attack vector when Claude Code has full Workspace access. What does Armor actually intercept, and what attack patterns does it leave unaddressed? What is the minimum viable scoping strategy for a production workflow?
