# Two Fixes To Improve Opus 4.6 Performance

| Field | Value |
|-------|-------|
| **Source** | [https://www.youtube.com/watch?v=L1CH00T3FeA](https://www.youtube.com/watch?v=L1CH00T3FeA) |
| **Type** | youtube |
| **Processed** | 2026-04-13 |
| **Duration** | PT1M15S |

---

## Distilled Summary

# 📄 Two Fixes To Improve Opus 4.6 Performance

**Source:** YouTube Channel · 1:15 · YouTube  
**Published:** 260412  
**Link:** https://www.youtube.com/watch?v=L1CH00T3FeA  
**Reading time:** ~2 min

**Tags:** `claude code` `ai coding` `performance tuning` `adaptive thinking`

---

## ⚡ BOTTOM LINE

Two specific configuration changes—setting effort to max and disabling adaptive thinking—can restore Claude Code's performance to pre-February 2026 levels, as confirmed by the tool's creator.

---

## 📝 THESIS

Claude Code users experiencing degraded performance with Opus 4.6 can fix it by overriding two default settings: manually setting effort to max (which no longer defaults to high) and disabling adaptive thinking, forcing the model to always use maximum reasoning capacity regardless of perceived task complexity.[^1]

---

## 💡 KEY INSIGHTS

1. **Effort levels no longer default to high** — Since February 2026, Claude Code defaults to medium effort instead of high or max, requiring explicit `/effort max` commands for optimal performance.[^2]

2. **Adaptive thinking under-allocates reasoning** — The creator, Boris Cherny, acknowledged that the adaptive thinking feature causes the model to "sometimes think less on simpler questions," leading to inconsistent performance.[^3] [✓]

3. **Settings work best together** — Setting `/effort max` alone doesn't fully solve the problem because adaptive thinking can still override effort settings, making both configuration changes necessary for consistent maximum performance.[^4] [✓]

4. **Session vs. permanent settings** — The `/effort max` command is session-only, requiring users to either reapply it each session or modify their settings folder defaults for persistent changes.[^5]

---

## 💬 QUOTABLE MOMENTS

> "This is literally a suggestion from Churnney himself. He actually posted about this on hacker news because someone was bringing up how they did all these tests and it looked like Opus wasn't performing as well."
> — [YouTube Channel, ~0:40][^3]

---

## 🔍 FACT CHECK

> ✓ **VERIFIED** — Boris Cherny is the actual creator and head of Claude Code at Anthropic, confirming his authority on these recommendations.[^6]

> ✓ **VERIFIED** — The adaptive thinking feature was introduced in Opus 4.6 and allows Claude to dynamically decide thinking allocation based on perceived task complexity, sometimes reducing reasoning for simpler tasks.[^7]

> ✓ **VERIFIED** — The recommended settings (`/effort max` plus `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1`) were indeed confirmed by Cherny as restoring "pre-February behavior where Claude always thought deeply."[^8]

---

## 📖 KEY REFERENCES

### People & Experts
- **Boris Cherny** — Creator and Head of Claude Code at Anthropic, principal authority on Claude Code configuration and performance tuning

### Institutions & Organisations
- **Anthropic** — Creator of Claude AI models and Claude Code, developer of the Opus 4.6 model architecture

### Concepts & Frameworks
- **Adaptive Thinking** — Feature introduced in Claude Opus 4.6 that allows the model to dynamically allocate thinking tokens based on perceived task complexity, replacing fixed thinking budgets
- **Effort Parameter** — Setting controlling how much computational effort Claude applies to tasks, ranging from low to max, with significant performance implications

---

## 🎯 STRATEGIC IMPLICATIONS

**For AI developers:** Performance tuning requires understanding that default settings may prioritize efficiency over maximum capability, necessitating manual optimization for demanding tasks.

**For Claude Code power users:** Documenting and sharing optimal configuration patterns becomes essential as AI tools evolve rapidly, with community-sourced knowledge often preceding official documentation.

**For AI tool designers:** The tension between adaptive efficiency (conserving resources) and consistent high performance represents a fundamental trade-off in AI interface design, with user-controllable overrides as a necessary compromise.

---

## 🧭 FURTHER EXPLORATION

- What are the computational cost implications of running Claude Code with adaptive thinking disabled versus enabled for different types of coding tasks?
- How might the "under-allocating reasoning" problem with adaptive thinking affect different user skill levels differently?
- What other performance tuning parameters beyond effort and adaptive thinking might significantly impact Claude Code's effectiveness?

---

## 📊 EPISTEMIC STATUS

**Source credibility:** Medium — While the speaker is not identified, the recommendations trace back to Boris Cherny, the actual Claude Code creator, giving them strong authority despite secondhand transmission.  
**Claim verifiability:** 3 of 3 key claims verified — All main technical claims about settings and their effects were confirmed through documentation and creator statements.  
**Potential biases:** The source presents these as definitive fixes without discussing potential trade-offs (like increased computational cost or the intended benefits of adaptive thinking).  
**Quality flags:** Speaker unidentified, minimal technical detail, secondhand information (though traceable to authoritative source).  
**Confidence in synthesis:** High — Core recommendations are well-documented and traceable to authoritative source, though implementation details are minimal.

---

## 📚 REFERENCES

[^1]: [YouTube Channel, ~0:15] "If you feel like claude code in Opus 4.6 just hasn't been performing as well lately, then here are two settings you can change."
[^2]: [YouTube Channel, ~0:25] "The first setting you need to change is the effort because it doesn't default to high or max anymore."
[^3]: [YouTube Channel, ~0:40] "The second setting you want to change is claude code disable adaptive thinking one. This is literally a suggestion from Churnney himself."
[^4]: [Verified] Documentation confirms `/effort max` without disabling adaptive thinking doesn't completely solve performance issues because the model might still decide not to think on certain turns.
[^5]: [YouTube Channel, ~0:30] "This is session only. So you will need to do this each time or change the default setting in your settings folder."
[^6]: [Verified] LinkedIn profile confirms Boris Cherny as "Creator & Head of Claude Code @Anthropic."
[^7]: [Verified] Amazon Bedrock documentation describes adaptive thinking as "letting Claude dynamically decide when and how much to think based on the complexity of each request."
[^8]: [Verified] Technical guide confirms these settings "restore the pre-February behavior where Claude always thought deeply."

---
