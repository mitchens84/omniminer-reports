#!/usr/bin/env python3
"""
build_site.py — OmniMiner Reports static-site generator.

Reads OmniMiner distillation reports (markdown) from the _SYNC/OMNIMINER GDrive
folder, strips the raw transcript, classifies each report into a general-audience
topic category, and emits a classified, searchable index plus one rendered HTML
page per report into ./docs (the GitHub Pages source).

Privacy: bodies are truncated at the "## Full Transcript" header so only the
distillation is published. A report is withheld if it contains EXCLUDE_FROM_PUBLIC,
is listed in exclude.txt, or fails the quality gate (empty / raw tool-call output).

Categories are general-audience plain English (NOT the internal LBS codes); each
report's LBS code is still carried in manifest.json for downstream (website) use.

Usage: python3 build_site.py [--source PATH] [--limit N] [--quiet]
Idempotent: re-running regenerates docs/ from scratch.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import markdown

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent
DOCS = REPO / "docs"
REPORTS_DIR = DOCS / "reports"
ASSETS = DOCS / "assets"
EXCLUDE_FILE = REPO / "exclude.txt"

DEFAULT_SOURCE = (
    Path.home()
    / "Library/CloudStorage/GoogleDrive-henspham@gmail.com/My Drive/_SYNC/OMNIMINER"
)

TRANSCRIPT_MARKERS = ("## Full Transcript", "## Transcript", "## Raw Transcript")
PRIVACY_MARKER = "EXCLUDE_FROM_PUBLIC"

# Quality gate: a distillation that contains a raw unexecuted tool-call, or is
# effectively empty, is a failed generation and must not be published.
QUALITY_TOOLCALL = re.compile(
    r"function_calls|<invoke\b|</invoke|antml:|name=\"(PERPLEXITY|TAVILY|WIKIPEDIA|CALCULATOR)\""
    r"|call_[A-Za-z0-9]{16,}", re.I)
QUALITY_UNPROC = re.compile(r"unprocessable|unparseable|unparsable", re.I)
QUALITY_MIN_BODY = 350  # chars of real distillation prose

# Display categories — general-audience labels in a fixed, predictable order.
# Each: (label, lbs_code_for_manifest, keyword list matched on title+tags+goal).
CATEGORIES = [
    ("AI & Technology", "6I", [
        "ai", "a.i", "llm", "claude", "anthropic", "openai", "gpt", "agent", "agentic",
        "agi", "prompt", "codex", "model", "machine learning", "neural", "software",
        "engineer", "coding", "vibe-coding", "quantum", "robot", "chatbot", "mcp",
        "front end", "front-end", "gpu", "compute", "nvidia", "antigravity", "automation",
    ]),
    ("Health & Nutrition", "4H", [
        "health", "nutrition", "diet", "protein", "creatine", "taurine", "cholesterol",
        "exercise", "muscle", "longevity", "sleep", "dementia", "alzheimer", "thyroid",
        "metabolism", "metabolic", "cardiovascular", "supplement", "fasting", "rucking",
        "vegetable", "atherosclerosis", "endotoxin", "fitness", "training", "vo2",
        "women 40", "medicine", "disease", "cook", "food", "vegan", "cancer", "heart",
    ]),
    ("Mind & Philosophy", "2L", [
        "stoic", "stoics", "philosophy", "ethic", "psycholog", "attention", "love",
        "meaning", "virtue", "consciousness", "mindful", "happiness", "dating",
        "relationship", "loved", "psychosis", "goldstein", "peterson", "mattering",
    ]),
    ("Money & Business", "3P", [
        "finance", "economic", "economy", "market", "invest", "money", "shadow banking",
        "revenue", "business", "sell off", "sell-off", "grifter", "wealth", "valuation",
        "billion", "startup", "founders", "enterprise", "ipo", "capital", "tipping",
    ]),
    ("Society & Culture", "8C", [
        "media", "education", "pedagog", "society", "culture", "documentary", "politic",
        "democrat", "democracy", "iran", "gaza", "history", "ufo", "smart home", "matter",
        "humane education",
    ]),
    ("Productivity & Learning", "0A", [
        "second brain", "pkm", "note-taking", "note taking", "productivity", "to do list",
        "to-do", "context engineering", "workflow", "tiago forte", "knowledge management",
        "learning", "study",
    ]),
]
FALLBACK_CATEGORY = ("General", "0A", [])
CATEGORY_ORDER = [c[0] for c in CATEGORIES] + [FALLBACK_CATEGORY[0]]
LBS_OF = {c[0]: c[1] for c in CATEGORIES + [FALLBACK_CATEGORY]}

_CAT_RE = [
    (c, [re.compile(r"\b" + re.escape(kw) + r"\b", re.I) for kw in c[2]])
    for c in CATEGORIES
]

# Content type by source domain.
CTYPES = {
    "video": ["youtube.com", "youtu.be", "vimeo.com", "loom.com"],
    "podcast": ["spotify.com", "acast", "megaphone", "apple.co", "podcast",
                "simplecast", "buzzsprout", "libsyn", "substack.com/api/v1/audio",
                "transistor", "pdst.fm", "redcircle", "snipd"],
}
# Pretty platform names for the SOURCE line when no author is available.
PLATFORM = {
    "youtube.com": "YouTube", "youtu.be": "YouTube", "vimeo.com": "Vimeo",
    "loom.com": "Loom", "acast.com": "Acast", "open.spotify.com": "Spotify",
    "spotify.com": "Spotify", "substack.com": "Substack", "megaphone.fm": "Megaphone",
    "apple.co": "Apple Podcasts", "podcasts.apple.com": "Apple Podcasts",
    "simplecast.com": "Simplecast",
}

MD_EXTENSIONS = ["extra", "sane_lists", "nl2br"]

INDEX_JS = """
const q=document.getElementById('q'),chips=[...document.querySelectorAll('.chip')],
items=[...document.querySelectorAll('li.item')],
count=document.getElementById('count'),no=document.getElementById('noresults');
let bf='all';
function apply(){const term=q.value.trim().toLowerCase();let shown=0;
items.forEach(li=>{const okB=bf==='all'||li.dataset.b===bf;
const okT=!term||li.dataset.s.includes(term);const v=okB&&okT;
li.style.display=v?'':'none';if(v)shown++;});
no.style.display=shown?'none':'';
count.textContent=shown+(shown===1?' report':' reports');}
q.addEventListener('input',apply);
chips.forEach(c=>c.addEventListener('click',()=>{chips.forEach(x=>x.classList.remove('active'));
c.classList.add('active');bf=c.dataset.b;apply();}));
"""

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
YAML_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
FILENAME_DATE8 = re.compile(r"^(\d{4})(\d{2})(\d{2})[_-]")
FILENAME_DATE6 = re.compile(r"^(\d{2})(\d{2})(\d{2})[_-]")
URL_RE = re.compile(r"https?://[^\s\)\]]+")
META_SOURCE = re.compile(r"\*\*Source:?\*\*[:\s]*\[?([^\]\)\n]+)\]?\(?([^)\n]*)\)?", re.I)
META_PROCESSED = re.compile(r"\*\*Processed:?\*\*[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.I)
META_DURATION = re.compile(r"\*\*Duration:?\*\*[:\s|]*([A-Za-z0-9:]+)", re.I)
TAG_TOKENS = re.compile(r"`+\s*([a-z0-9][\w\- /]*?)\s*`+", re.I)
MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower())
    return s.strip("-")[:80] or "report"


def friendly_date(iso: str) -> str:
    try:
        y, m, d = iso.split("-")
        return f"{int(d)} {MONTHS[int(m)]} {y}"
    except Exception:
        return iso


def friendly_duration(v: str) -> str:
    v = (v or "").strip()
    if not v:
        return ""
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", v, re.I)
    if m:
        h, mi, s = (int(x) if x else 0 for x in m.groups())
    else:
        parts = v.split(":")
        if all(p.isdigit() for p in parts) and 2 <= len(parts) <= 3:
            nums = [int(p) for p in parts]
            h, mi, s = ([0] + nums)[-3:] if len(nums) == 2 else nums
        else:
            return ""
    if h:
        return f"{h}h {mi}m" if mi else f"{h}h"
    if mi:
        return f"{mi}m"
    return f"{s}s" if s else ""


def source_label(author: str, url: str) -> str:
    """A short uppercase SOURCE name: prefer author/channel, else platform."""
    if author:
        a = re.sub(r"\s*\([^)]*\)\s*$", "", author).strip()  # drop "(...)" suffix
        return a.upper()[:48]
    if not url:
        return ""
    if "doi.org" in url:
        return "RESEARCH"
    if "snipd" in url:
        return "SNIPD"
    m = re.search(r"https?://([^/]+)", url)
    host = (m.group(1) if m else "").lower().lstrip("www.")
    for dom, name in PLATFORM.items():
        if dom in host:
            return name.upper()
    root = host.split(".")[-2] if host.count(".") >= 1 else host
    return root.upper() if root else ""


def content_type(url: str) -> str:
    u = url.lower()
    for t, doms in CTYPES.items():
        if any(d in u for d in doms):
            return t
    return "article"


def strip_leading_meta(body_md: str) -> str:
    """Remove the report's own metadata block (Source/Processed/Duration/Type,
    a Field|Value table, a leading duplicate H1, and empty Summary headers) so
    only the distillation prose renders under our own header."""
    lines = body_md.splitlines()
    out, in_table = [], False
    started = False
    for ln in lines:
        s = ln.strip()
        if not started:
            if re.match(r"^#\s+", s):                       # leading duplicate title
                continue
            if re.match(r"^\*\*(Source|Processed|Duration|Link|Published|Type|Reading time|Tags)\b", s, re.I):
                continue
            if re.match(r"^\|.*\|$", s):                    # Field|Value metadata table
                in_table = True
                continue
            if in_table and re.match(r"^\|[\s:|-]+\|$", s):
                continue
            if in_table and re.match(r"^\|.*\|$", s):
                continue
            in_table = False
            if s in ("---", "") or re.match(r"^##\s+(Summary|Distilled Summary)\s*$", s, re.I):
                continue
            started = True
        out.append(ln)
    return "\n".join(out).strip()


def quality_fail(body_md: str) -> str | None:
    if QUALITY_TOOLCALL.search(body_md):
        return "raw tool-call output"
    prose = re.sub(r"^#.*$|^\s*\|.*\|\s*$|^\*\*[^*]+\*\*.*$|^---+$|^\{.*\}$", "",
                   body_md, flags=re.M).strip()
    if len(prose) < QUALITY_MIN_BODY:
        return f"empty distillation ({len(prose)}c)"
    return None


def parse_report(path: Path) -> dict | None:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if PRIVACY_MARKER in raw:
        return {"_skip": "EXCLUDE_FROM_PUBLIC"}
    if QUALITY_UNPROC.search(raw[:400]):
        return {"_skip": "unprocessable transcript"}

    fm: dict = {}
    fmm = YAML_FM.match(raw)
    if fmm:
        try:
            import yaml
            p = yaml.safe_load(fmm.group(1))
            if isinstance(p, dict):
                fm = p
        except Exception:
            fm = {}
        body_src = raw[fmm.end():]
    else:
        body_src = raw

    def fv(k):
        return str(fm.get(k)).strip() if fm.get(k) else ""

    title = fv("title")
    source_url = fv("source_url")
    duration = fv("duration")
    # `author` is the clean channel/podcast/publication name (with spaces) that
    # drives the TYPE · SOURCE line. OmniMiner frontmatter historically wrote this
    # as `source_channel`; read either so the whole existing corpus gets a clean
    # source line without re-firing. (PROC-OMNIMINER_TRIGGER §10a)
    author = fv("author") or fv("source_channel")
    if not author:
        # Fallback: recover the channel/show/publication from the body's
        # "**Source:** [Channel Name](url)" link text when frontmatter omitted it
        # (older v7.2 reports wrote the channel only in the body). Ignore the case
        # where the link text is the bare URL or an em-dash placeholder.
        ms_a = META_SOURCE.search(raw)
        if ms_a:
            cand = ms_a.group(1).strip().strip("[]")
            if cand and not cand.lower().startswith("http") and cand not in ("—", "-", ""):
                author = cand
    lbs_fm = fv("lbs").upper()[:2]
    goal = fv("goal")
    tags = [str(t).lower().strip() for t in fm["tags"]] if isinstance(fm.get("tags"), list) else []

    lines = body_src.splitlines()
    if not title:
        for ln in lines[:40]:
            m = re.match(r"^#\s+(.+)", ln)
            if m:
                title = re.sub(r"^[\U0001F300-\U0001FAFF☀-➿]\s*", "", m.group(1).strip()).strip()
                break
    if not title:
        title = (path.stem.replace("_complete", "").split("-REPORT-OMNIMINER")[0]
                 .replace("_", " ").strip())

    # Date
    date_iso = None
    if fv("date_processed") or fv("processed_date"):
        dp = fv("date_processed") or fv("processed_date")
        if re.fullmatch(r"\d{6}", dp):
            date_iso = f"20{dp[:2]}-{dp[2:4]}-{dp[4:]}"
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", dp):
            date_iso = dp
    if not date_iso:
        m8 = FILENAME_DATE8.match(path.name)
        m6 = FILENAME_DATE6.match(path.name)
        if m8:
            date_iso = f"{m8.group(1)}-{m8.group(2)}-{m8.group(3)}"
        elif m6:
            date_iso = f"20{m6.group(1)}-{m6.group(2)}-{m6.group(3)}"
    if not date_iso:
        mp = META_PROCESSED.search(raw)
        date_iso = mp.group(1) if mp else "1970-01-01"

    if not source_url:
        ms = META_SOURCE.search(raw)
        if ms and ms.group(2).strip().startswith("http"):
            source_url = ms.group(2).strip()
        else:
            mu = URL_RE.search(raw[:800])
            source_url = mu.group(0) if mu else ""
    if not duration:
        md = META_DURATION.search(raw)
        duration = md.group(1) if md else ""
    if not tags:
        for ln in lines:
            if re.match(r"\s*\*\*Tags:?\*\*", ln, re.I):
                tags = [t.lower() for t in TAG_TOKENS.findall(ln)
                        if t.lower() != "tags" and len(t) > 1]
                break

    # Body up to transcript
    cut = len(lines)
    for i, ln in enumerate(lines):
        if any(ln.strip().startswith(m) for m in TRANSCRIPT_MARKERS):
            cut = i
            break
    raw_body = "\n".join(lines[:cut]).strip()

    qf = quality_fail(raw_body)
    if qf:
        return {"_skip": qf}

    body_md = strip_leading_meta(raw_body)

    # Classify
    haystack = (title + " " + " ".join(tags) + " " + goal + " " + lbs_fm)
    best, best_score = None, 0
    for c, pats in _CAT_RE:
        score = sum(1 for p in pats if p.search(haystack))
        if score > best_score:
            best, best_score = c, score
    if best is None:
        label = next((lab for lab, code in LBS_OF.items() if code == lbs_fm), None)
        category = (next((c for c in CATEGORIES if c[0] == label), FALLBACK_CATEGORY)
                    if label else FALLBACK_CATEGORY)
    else:
        category = best

    ctype = content_type(source_url)
    src = source_label(author, source_url)

    stem = path.stem.replace("_complete", "").split("-REPORT-OMNIMINER")[0]
    stem = re.sub(r"\s*\(\d+\)\s*$", "", stem)
    return {
        "slug": slugify(stem) or slugify(title),
        "dedup_key": slugify(stem),
        "title": title,
        "date": date_iso,
        "source_url": source_url,
        "source_label": src,
        "duration": friendly_duration(duration),
        "tags": tags,
        "category": category[0],
        "lbs": LBS_OF[category[0]],
        "ctype": ctype,
        "body_md": body_md,
        "src_file": path.name,
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
# Autolink bare URLs that markdown leaves as plain text (e.g. KA footnotes
# "Link: https://…"). The lookbehind skips URLs already inside an attribute
# (href="…") or as anchor text (>…<), so existing [title](url) links are untouched.
_BARE_URL = re.compile(r"""(?<![">='])(https?://[^\s<>"')]+)""")


def linkify(html_str: str) -> str:
    return _BARE_URL.sub(lambda m: f'<a href="{m.group(1)}">{m.group(1)}</a>', html_str)


def render_md(body_md: str) -> str:
    return linkify(markdown.markdown(body_md, extensions=MD_EXTENSIONS, output_format="html5"))


CSS = """
:root{--bg:#f4f5f7;--card:#fff;--ink:#33373d;--ink-strong:#1c1f24;--teal:#2f6f6b;
--teal-bg:#e3efee;--line:#e6e8eb;--muted:#9aa0a6;--src:#b07a2f;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);line-height:1.6}
a{color:var(--teal)}
.wrap{max-width:760px;margin:0 auto;padding:24px 16px 64px}
header.site{padding:26px 0 6px}
header.site h1{font-size:26px;margin:0 0 6px;color:var(--ink-strong)}
header.site p{margin:0;color:#5a6068;font-size:14px}
.controls{position:sticky;top:0;background:var(--bg);padding:14px 0 12px;z-index:5;border-bottom:1px solid var(--line);margin-bottom:6px}
#q{width:100%;padding:11px 14px;font-size:15px;border:1px solid var(--line);border-radius:10px;background:#fff;outline:none}
#q:focus{border-color:var(--teal)}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.chip{font-size:12.5px;padding:5px 12px;border:1px solid var(--line);border-radius:14px;background:#fff;cursor:pointer;color:#566;user-select:none}
.chip.active{background:var(--teal);color:#fff;border-color:var(--teal)}
#count{color:var(--muted);font-size:12px;margin:10px 2px 0;display:block}
section.cat{margin:22px 0 0}
section.cat > h2{font-size:12px;letter-spacing:.07em;text-transform:uppercase;color:var(--teal);border-bottom:1px solid var(--teal-bg);padding-bottom:6px;margin:0 0 2px}
ul.items{list-style:none;margin:0;padding:0}
li.item{padding:13px 2px;border-bottom:1px solid #eef0f2}
li.item a.t{font-weight:600;font-size:15px;color:var(--ink-strong);text-decoration:none}
li.item a.t:hover{color:var(--teal);text-decoration:underline}
li.item .src{display:block;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--src);margin:3px 0 2px;font-weight:600}
li.item .meta{display:block;font-size:12px;color:var(--muted)}
li.item .tg{color:#aeb4ba}
.empty{color:var(--muted);font-style:italic;padding:18px 0}
footer.site{margin-top:40px;text-align:center;color:var(--muted);font-size:11px;line-height:1.7}
/* report page */
.report .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:34px 38px}
.report .src{font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--src);font-weight:600;margin:0 0 4px}
.report h1{font-size:23px;color:var(--ink-strong);margin:0 0 8px;line-height:1.3}
.report .submeta{font-size:12px;color:var(--muted);margin:0 0 4px;padding-bottom:14px;border-bottom:1px solid #ececef}
.report h2{font-size:13px;letter-spacing:.05em;text-transform:uppercase;color:var(--teal);border-bottom:1px solid var(--teal-bg);padding-bottom:6px;margin:28px 0 12px}
.report h3{font-size:15px;color:var(--ink-strong)}
.report blockquote{border-left:3px solid var(--teal-bg);margin:0 0 14px;padding:2px 16px;color:#4a5057}
.report table{border-collapse:collapse;width:100%;font-size:14px;margin:0 0 16px}
.report th,.report td{border:1px solid var(--line);padding:7px 10px;text-align:left}
.report th{background:#f3f6f6}
.report code{font-size:12px;background:#eef1f3;border:1px solid #e1e5e8;padding:1px 6px;border-radius:10px}
.report img{max-width:100%}
.backlink{display:inline-block;margin:0 0 16px;font-size:13px;text-decoration:none}
@media(max-width:620px){.report .card{padding:22px 18px}.wrap{padding:16px 12px 48px}}
"""


def submeta_line(r: dict, with_category: bool) -> str:
    bits = [r["ctype"].title()]
    if with_category:
        bits.append(r["category"])
    bits.append(friendly_date(r["date"]))
    if r["duration"]:
        bits.append(r["duration"])
    line = " &middot; ".join(html.escape(b) for b in bits)
    if r["source_url"]:
        line += f' &middot; <a href="{html.escape(r["source_url"])}">source</a>'
    return line


def report_page(r: dict) -> str:
    body = render_md(r["body_md"])
    src = f'<p class="src">{html.escape(r["source_label"])}</p>' if r["source_label"] else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(r["title"])} &middot; OmniMiner</title>
<link rel="stylesheet" href="../assets/om.css">
</head><body class="report"><div class="wrap">
<a class="backlink" href="../index.html">&larr; All reports</a>
<div class="card">
{src}<h1>{html.escape(r["title"])}</h1>
<p class="submeta">{submeta_line(r, with_category=True)}</p>
{body}
</div>
<footer class="site">OmniMiner distillation &middot; transcript withheld</footer>
</div></body></html>"""


def index_page(reports: list[dict], built_at: str) -> str:
    from collections import Counter
    counts = Counter(r["category"] for r in reports)

    chips = [f'<span class="chip active" data-b="all">All ({len(reports)})</span>']
    for c in CATEGORY_ORDER:
        if counts.get(c):
            chips.append(f'<span class="chip" data-b="{html.escape(c)}">{html.escape(c)} ({counts[c]})</span>')

    # Single flat list, newest first; chips filter it (no category section headers).
    lis = []
    for r in sorted(reports, key=lambda x: x["date"], reverse=True):
        srcline = f'<span class="src">{r["ctype"].upper()}'
        if r["source_label"]:
            srcline += f' &middot; {html.escape(r["source_label"])}'
        srcline += "</span>"
        tagstr = " ".join("#" + t for t in r["tags"][:4])
        search = html.escape((r["title"] + " " + " ".join(r["tags"]) + " "
                              + r["source_label"] + " " + r["category"]).lower())
        lis.append(
            f'<li class="item" data-b="{html.escape(r["category"])}" data-s="{search}">'
            f'<a class="t" href="reports/{r["slug"]}.html">{html.escape(r["title"])}</a>'
            f'{srcline}'
            f'<span class="meta">{html.escape(friendly_date(r["date"]))}'
            f'{(" &middot; " + r["duration"]) if r["duration"] else ""} '
            f'<span class="tg">{html.escape(tagstr)}</span></span></li>'
        )
    sections = [f'<ul class="items">{"".join(lis)}</ul>']

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OmniMiner Reports</title>
<link rel="stylesheet" href="assets/om.css">
</head><body><div class="wrap">
<header class="site">
<h1>OmniMiner Reports</h1>
<p>Fact-checked distillations of the videos, podcasts and articles I work through &mdash; the key points of each, without the transcript.</p>
</header>
<div class="controls">
<input id="q" type="search" placeholder="Search title, source or tag&hellip;" autocomplete="off">
<div class="filters">{''.join(chips)}</div>
<span id="count">{len(reports)} reports</span>
</div>
<div id="results">{''.join(sections)}</div>
<p class="empty" id="noresults" style="display:none">No reports match.</p>
<footer class="site">Generated {built_at} &middot; distillation only, transcripts withheld</footer>
</div>
<script>{INDEX_JS}</script>
</body></html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.is_dir():
        print(f"ERROR: source not found: {src}", file=sys.stderr)
        return 1

    excludes = set()
    if EXCLUDE_FILE.exists():
        excludes = {ln.strip() for ln in EXCLUDE_FILE.read_text().splitlines()
                    if ln.strip() and not ln.startswith("#")}

    def is_report(p: Path) -> bool:
        if p.name.startswith(".") or p.stat().st_size < 400:
            return False
        return p.stem.endswith("_complete") or "REPORT-OMNIMINER" in p.name

    all_md_files = list(src.glob("*.md"))
    files = sorted(p for p in all_md_files if is_report(p))
    if args.limit:
        files = files[-args.limit:]

    parsed, skipped = [], []
    for p in files:
        try:
            r = parse_report(p)
        except Exception as e:  # noqa: BLE001
            skipped.append((p.name, f"parse error: {e}"))
            continue
        if r is None or "_skip" in r:
            skipped.append((p.name, r.get("_skip", "skip") if r else "skip"))
            continue
        if r["slug"] in excludes or r["dedup_key"] in excludes:
            skipped.append((p.name, "exclude.txt"))
            continue
        parsed.append((p, r))

    # Dedupe GDrive ' (N)' copies: keep the largest source file per dedup_key.
    best: dict[str, tuple[Path, dict]] = {}
    for p, r in parsed:
        k = r["dedup_key"]
        if k not in best or p.stat().st_size > best[k][0].stat().st_size:
            if k in best:
                skipped.append((p.name, f"dup of {best[k][0].name}"))
            best[k] = (p, r)
        else:
            skipped.append((p.name, f"dup of {best[k][0].name}"))
    reports = [r for _, r in best.values()]

    seen: dict[str, int] = {}
    for r in reports:
        if r["slug"] in seen:
            seen[r["slug"]] += 1
            r["slug"] = f"{r['slug']}-{r['date'].replace('-', '')}"
        else:
            seen[r["slug"]] = 1

    if REPORTS_DIR.exists():
        shutil.rmtree(REPORTS_DIR)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "om.css").write_text(CSS, encoding="utf-8")

    for r in reports:
        (REPORTS_DIR / f"{r['slug']}.html").write_text(report_page(r), encoding="utf-8")

    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    (DOCS / "index.html").write_text(index_page(reports, built_at), encoding="utf-8")

    manifest = {
        "built_at": built_at,
        "count": len(reports),
        "source_count": len(all_md_files),
        "categories": CATEGORY_ORDER,
        "reports": [{k: r[k] for k in ("slug", "title", "date", "category", "lbs",
                                        "ctype", "source_label", "source_url", "tags",
                                        "duration", "src_file")} for r in
                    sorted(reports, key=lambda x: x["date"], reverse=True)],
    }
    (DOCS / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    if not args.quiet:
        from collections import Counter
        dist = Counter(r["category"] for r in reports)
        qskip = [s for s in skipped if s[1] in ("raw tool-call output", "unprocessable transcript")
                 or "empty distillation" in s[1]]
        print(f"Built {len(reports)} reports ({len(skipped)} skipped) -> {DOCS}")
        for c in CATEGORY_ORDER:
            if dist.get(c):
                print(f"  {dist[c]:3d}  {c}")
        print(f"Quality-gate skips: {len(qskip)}", qskip[:6] if qskip else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
