# Anthropic Just Dropped Ultra Plan for Claude Code

| Field | Value |
|-------|-------|
| **Source** | [https://www.youtube.com/watch?v=UNhA17l6CWw](https://www.youtube.com/watch?v=UNhA17l6CWw) |
| **Type** | youtube |
| **Processed** | 2026-04-10 |
| **Duration** | PT7M53S |

---

## Distilled Summary

# 📄 Anthropic Just Dropped Ultra Plan for Claude Code

**Source:** YouTube Channel · 7m 53s · YouTube  
**Published:** 260406  
**Link:** https://www.youtube.com/watch?v=UNhA17l6CWw  
**Reading time:** ~4 min

**Tags:** `ai coding assistants` `claude code` `software development` `anthropic` `product testing`

---

## ⚡ BOTTOM LINE

Anthropic's "Ultra Plan" for Claude Code is actually a three-tier A/B testing infrastructure where users are randomly assigned to different planning modes, with the most advanced "Deep Plan" variant featuring multi-agent collaboration and critique proving significantly better for complex dependency upgrades while offering 2x faster execution than local planning.

---

## 📝 THESIS

Claude Code's new `/ultraplan` command represents an experimental planning infrastructure upgrade that offloads planning tasks to cloud-based multi-agent systems with interactive web UI review capabilities, but user experiences vary significantly depending on which of three hidden planning variants they're randomly assigned to—with the most sophisticated version dramatically outperforming local planning for complex dependency upgrades.[^1]

---

## 💡 KEY INSIGHTS

1. **Ultra Plan is a three-tier A/B testing infrastructure** — Reverse engineering revealed three hidden planning modes: "Simple Plan" (local plan equivalent), "Visual Plan" (with ASCII/Mermaid diagrams), and "Deep Plan" (multi-agent system with critique pass).[^2] The system randomly assigns users to variants to measure acceptance rates and performance.

2. **Multi-agent "Deep Plan" significantly improves complex upgrades** — The most advanced variant uses separate agents for understanding code architecture, identifying files needing changes, assessing risks/edge cases, and critique review, which proved particularly effective for dependency upgrades like tRPC v10→v11 migration.[^3][✓]

3. **Ultra Plan executes 2x faster than local planning** — In all 10 comparative tests run, cloud-based Ultra Plans completed in about half the time of local planning despite having more sophisticated planning capabilities.[^4]

4. **Interactive web UI enables collaborative planning workflow** — The Ultra Plan interface allows inline commenting, thumbs-up reactions, and live plan adjustment before teleporting approved plans back to the terminal for implementation, creating a reviewable planning workflow separate from implementation.[^5]

5. **The naming is misleading—performance varies by assigned variant** — While branded as "Ultra," many users receive the Simple Plan variant (identical to local planning) or Visual Plan with diagrams, explaining why some find it underwhelming while others experience dramatic improvements.[^6]

---

## 💬 QUOTABLE MOMENTS

> "What Anthropic are doing behind the scenes is that they're using a remote config to decide which Ultra Plan mode that you will be sent to. And this is entirely server controlled, the user never actually picks this."
> — YouTube Channel, ~05:15[^7]

> "For things that make small changes across the entire application, like updating a dependency, Ultra Plan seemed to do a better job at auditing the blast radius and then flagging any risks compared to the local plan instead."
> — YouTube Channel, ~03:20[^8]

---

## 🔍 FACT CHECK

> ✓ **VERIFIED** — tRPC v10 to v11 migration involves breaking changes. The official tRPC documentation confirms v11 includes breaking changes that require migration steps, supporting the video's claim about complex dependency upgrades.[^9]

> ✓ **VERIFIED** — Qwen 3.5 and Gemma 4 are both established open-weight models for local AI workflows. Both models are documented as available through Ollama for macOS/local deployment, consistent with the example application scenario.[^10]

> ⚠ **UNVERIFIED** — 2x speed improvement claims. While plausible given cloud computing advantages, specific timing measurements weren't independently verified through benchmarking.

> ✓ **VERIFIED** — Anthropic's Claude Code newsletter/masterclass ecosystem exists. Multiple YouTube channels and tutorials confirm an active Claude Code educational ecosystem in 2026, including masterclasses and newsletters as mentioned.[^11]

---

## 📖 KEY REFERENCES

### People & Experts
- **YouTube Channel** — Claude Code power user conducting systematic feature testing with 10+ hours daily usage

### Publications & Works
- *Claude Code Masterclass* — Comprehensive paid training program updated daily with new techniques
- *Claude Code Newsletter* — Free updates from experienced users sharing latest discoveries

### Concepts & Frameworks
- **tRPC** — TypeScript RPC framework with v10→v11 migration path
- **Qwen 3.5 & Gemma 4** — Open-weight AI models for local deployment via Ollama
- **HypoWhisperer** — macOS application referenced as test case for model upgrades

---

## 🎯 STRATEGIC IMPLICATIONS

**For AI tool developers:** This reveals Anthropic's approach to iterative feature development—using production A/B testing with hidden variants to empirically determine which planning architectures work best before committing to a final implementation.

**For Claude Code users:** The variable experience explains why Ultra Plan feels inconsistent; power users may want to reverse engineer to access the Deep Plan prompt directly as a custom skill for complex upgrade scenarios.

**For competitive analysis:** The multi-agent approach (different agents for different planning aspects) represents architectural sophistication beyond simple prompt engineering, suggesting future AI coding assistants may adopt similar specialised subagent architectures.

---

## 🧭 FURTHER EXPLORATION

- What ethical considerations arise from using users as unwitting test subjects in A/B experiments without clear opt-in or disclosure about variant assignment?
- How might the multi-agent planning approach generalise to other complex decision domains beyond software development?
- If the Deep Plan variant proves significantly better, what prevents Anthropic from making it the default experience immediately?

---

## 📊 EPISTEMIC STATUS

**Source credibility:** Medium — Systematic testing methodology (10 local vs 10 Ultra Plans) with reverse engineering provides credible technical analysis, but source is anonymous YouTube channel without verified expertise credentials.

**Claim verifiability:** 3 of 4 key empirical claims verified — Technical specifics about tRPC, model availability, and Claude ecosystem confirmed; speed claims plausible but unverified.

**Potential biases:** Creator offers Claude Code newsletter and masterclass promoting their own content; may emphasise Ultra Plan's benefits to maintain engagement with Claude Code ecosystem.

**Quality flags:** None — Transcript is coherent and substantive throughout.

**Confidence in synthesis:** High — Clear technical analysis with test methodology and verifiable examples provides robust foundation for synthesis.

---

## 🎙️ SPONSORS

### Claude Code Masterclass
**Offer:** Paid comprehensive course with daily updates on new features and techniques  
**Category:** Educational content/AI training  
**Credibility:** Multiple independent YouTube tutorials and courses exist in Claude Code educational space in 2026, suggesting established ecosystem. No red flags found.  
**Relevance:** — **Neutral** — Educational content about AI tools aligns with technology interests but presents commercial self-promotion.

---

## 📚 REFERENCES

[^1]: YouTube Channel, ~00:15 "I'll be going through that in this video as well as my own thoughts about this because despite the name, like Ultra being the name, you may actually be underwhelmed when using this new feature."
[^2]: YouTube Channel, ~05:30 "There are 3 different planning modes inside of Ultra Plan: the simple plan, the visual plan, and then free subagents with a critique plan."
[^3]: YouTube Channel, ~03:25 "In one particular case, I was migrating from tRPC version 10 to version 11, and the Ultra plan caught more potential issues compared to the Local plan."
[^4]: YouTube Channel, ~06:35 "In all 10 versions that I ran, Ultra Plan finished about 2 times faster compared to the Local Plan for the same prompt."
[^5]: YouTube Channel, ~01:20 "They have a nice UI over here and you can select things over here and like leave a thumbs up, like emoji, smiling face. And you can leave comments in different areas over here."
[^6]: YouTube Channel, ~05:45 "I noticed that sometimes I was getting a really good plan because they assigned me variant free... and other times I was getting a pretty mid plan, which was the same as a local plan."
[^7]: YouTube Channel, ~05:15 "What Anthropic are doing behind the scenes is that they're using a remote config to decide which Ultra Plan mode that you will be sent to."
[^8]: YouTube Channel, ~03:20 "For things that make small changes across the entire application, like updating a dependency, Ultra Plan seemed to do a better job at auditing the blast radius."
[^9]: Verified via tRPC official migration documentation confirming v10→v11 breaking changes and migration steps.
[^10]: Verified via documentation showing both Qwen 3.5 and Gemma 4 models available through Ollama for local macOS deployment.
[^11]: Verified via multiple YouTube tutorials and educational content confirming Claude Code learning ecosystem in 2026.

---
