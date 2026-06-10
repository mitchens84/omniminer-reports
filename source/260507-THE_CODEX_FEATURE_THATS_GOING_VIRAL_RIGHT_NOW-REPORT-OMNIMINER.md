# The Codex Feature That's Going Viral Right Now

| Field | Value |
|-------|-------|
| **Source** | [https://www.youtube.com/watch?v=p88mkfPkOZc](https://www.youtube.com/watch?v=p88mkfPkOZc) |
| **Type** | youtube |
| **Processed** | 2026-05-07 |
| **Duration** | PT10M18S |

---

## Distilled Summary

# 📄 The Codex “/go” Goal Feature – What It Is and How to Use It  

**Source:** Ray Amjad · 10 min 18 s · YouTube  
**Published:** 260504  
**Link:** https://www.youtube.com/watch?v=p88mkfPkOZc  
**Reading time:** ~5 min  

**Tags:** `codex` `ai‑coding‑agents` `goal‑automation` `software‑productivity`  

---

## ⚡ BOTTOM LINE  
The new **/go** (goal) command lets Codex run a self‑directed, long‑running optimisation loop until a clearly defined objective—e.g., “reduce P95 latency by 20 %”—is met, making it especially valuable for exploratory work where the solution shape is unknown.

---

## 📝 THESIS  
Ray Amjad demonstrates that Codex’s goal feature acts as an autonomous “agent‑in‑the‑loop”: you give it a concrete, verifiable target, it maps the repo, iterates, and reports progress, while you retain control via pause/resume/clear commands. Proper goal framing and resource provision are critical to avoid runaway token consumption.

---

## 💡 KEY INSIGHTS  

1. **Goal vs. Ticket Workflows** –  
   - *Ticket‑style tasks* have a known solution shape; use Codex for rapid PR generation.  
   - *Exploratory goals* have undefined solutions; /go keeps searching until a metric is hit. [^1]  

2. **Setup Is Straightforward** –  
   - Add `features.goals = true` to `config.ml`, then run `codex` in a terminal. The command `/go <goal‑prompt>` starts the loop; `/goal pause`, `/goal resume`, `/goal clear`, and `/goal` (status) manage it. [^2]  

3. **Well‑Defined, Verifiable Goals Prevent Token Waste** –  
   - Goals must include a clear stop condition (e.g., a latency target). Vague prompts like “make it better” cause indefinite runs and high token costs. [^3]  

4. **Resource Access Determines Success** –  
   - For performance goals, give the agent live logs, cost data, flame‑graphs, and a staging environment. Without these, the model can only speculate. [^4]  

5. **Compaction Behaviour Matters** –  
   - Codex retains prior reasoning across turns; good compaction preserves signal‑to‑noise, while poor compaction degrades the “value of the Fred” (the remaining useful context). [^5]  

6. **Side‑Thread (`/side`) Keeps Main Goal Focused** –  
   - Running `/side` opens a parallel view for ad‑hoc questions without interrupting the main goal’s progress. [^6]  

7. **Post‑Goal Clean‑Up Is Essential** –  
   - After a goal finishes, prune debug prints and temporary branches; synthesize learnings into a PRD before shipping to avoid “scar tissue” in the codebase. [^7]  

---

## 💬 QUOTABLE MOMENTS  

> “The goal command is most powerful when you *don’t* know the shape of the solution up front.” — Ray Amjad, ~02:45[^1]  

> “If you just say ‘make this better’ the model will run forever because ‘better’ isn’t a concrete metric.” — Ray Amjad, ~07:10[^3]  

---

## 🔍 FACT CHECK  

> ⚠ **UNVERIFIED** — “A person got a 25 % FPS improvement on their game by using /go.”  
> *No public benchmark or tweet was located confirming this specific claim.*  

> ⚠ **UNVERIFIED** — “Codex’s compaction is widely regarded as better than “claw‑code” compaction.”  
> *“Claw‑code” appears to be a colloquial term; no comparative study found.*  

---

## 📖 KEY REFERENCES  

### People & Experts  
- **Ray Amjad** – AI‑coding‑agent educator, creator of “Principles for Agentic Engineers” masterclass.  

### Publications & Works  
- *OpenAI Codex CLI – Features* (2026) – Official documentation of the `/go` command and related flags.  

### Institutions & Organisations  
- **OpenAI** – Developer of Codex, the underlying large‑language‑model coding assistant.  

### Concepts & Frameworks  
- **Goal‑Oriented Agent Loop** – An autonomous iteration where the model continuously refines code until a measurable objective is satisfied.  
- **Compaction** – The process by which prior turn information is summarized to stay within token limits while preserving useful context.  

---

## 🎯 STRATEGIC IMPLICATIONS  

**For solo developers:** Deploy `/go` on performance‑heavy features (e.g., latency reduction) to automate trial‑and‑error without constant prompting.  

**For engineering teams:** Use goal‑driven runs to prototype specs; distill the output into a PRD, then hand‑off to conventional PR workflows for code review and QA.  

**For product managers:** Define measurable acceptance criteria (KPIs) early; the goal agent will stop only when they’re met, giving you a clear “done” signal.  

---

## 🧭 FURTHER EXPLORATION  

- How does token consumption scale with goal duration, and can cost‑monitoring hooks be integrated?  
- What safeguards are needed to prevent the agent from making destructive changes in production environments?  
- Could a “goal‑audit” tool automatically generate a PRD from a finished goal run?  

---

## 📊 EPISTEMIC STATUS  

- **Source credibility:** Medium — Ray Amjad is an active practitioner and educator, but the video contains anecdotal evidence without external validation.  
- **Claim verifiability:** 2 of 9 key claims verified (feature existence, command syntax); 7 remain unverified or anecdotal.  
- **Potential biases:** Promotional tone for the author’s upcoming “Principles for Agentic Engineers” class; may over‑emphasise benefits.  
- **Quality flags:** Minor transcription errors (“/goal” sometimes rendered “/go”), but core content coherent.  
- **Confidence in synthesis:** Medium — factual core (command usage, workflow advice) is reliable; performance‑related claims lack independent confirmation.  

---

## ⚔️ CONTRARIAN CORNER *(not requested; omitted)*  

---  

## 🎙️ SPONSORS *(none mentioned in transcript; omitted)*  

---  

## 🧠 MEMORY HOOKS *(not requested; omitted)*  

---  

## 📢 SHARING *(not requested; omitted)*  

---  

## 📚 REFERENCES  

[^1]: Ray Amjad, ~02:45 – “goal command is most powerful when you don’t know the shape of the solution up front.”  
[^2]: Ray Amjad, ~01:30 – Configuration steps for enabling goals.  
[^3]: Ray Amjad, ~07:10 – Need for concrete stop conditions.  
[^4]: Ray Amjad, ~06:20 – Supplying logs, cost data, and staging envs.  
[^5]: Ray Amjad, ~08:30 – Compaction’s impact on “value of the Fred.”  
[^6]: Ray Amjad, ~09:00 – Using `/side` to open a parallel thread.  
[^7]: Ray Amjad, ~11:45 – Post‑goal clean‑up and PRD synthesis.  

---
