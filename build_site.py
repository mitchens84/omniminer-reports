#!/usr/bin/env python3
"""
build_site.py — OmniMiner Reports static-site generator.

Reads OmniMiner distillation reports (markdown) from the _SYNC/OMNIMINER GDrive
folder, strips the raw transcript, classifies each report into an LBS-aligned
topic bucket, and emits a classified, searchable index plus one rendered HTML
page per report into ./docs (the GitHub Pages source).

Privacy: bodies are truncated at the "## Full Transcript" header so only the
distillation is published. A report is withheld if it contains the literal
marker EXCLUDE_FROM_PUBLIC or its slug is listed in exclude.txt.

Usage:
  python3 build_site.py [--source PATH] [--limit N] [--quiet]

Default source: ~/Library/CloudStorage/GoogleDrive-.../My Drive/_SYNC/OMNIMINER
Idempotent: re-running regenerates docs/ from scratch.
"""
from __future__ import annotations

import argparse
import html
import json
import os
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

# Classification buckets, in priority order (first match wins for primary bucket).
# Each: (bucket label, emoji, LBS tag, keyword list matched against title+tags).
BUCKETS = [
    ("AI & Technology", "\U0001F916", "6I/7A", [
        "ai", "a.i", "llm", "claude", "agent", "agentic", "gpt", "openai", "anthropic",
        "prompt", "codex", "model", "machine learning", "neural", "software", "engineer",
        "coding", "vibe-coding", "automation", "quantum", "robot", "chatbot", "agi",
        "front end", "front-end", "infrastructure", "gpu", "compute",
    ]),
    ("Health & Nutrition", "\U0001FAC0", "4H", [
        "health", "nutrition", "diet", "protein", "creatine", "taurine", "cholesterol",
        "exercise", "muscle", "longevity", "sleep", "dementia", "alzheimer", "thyroid",
        "metabolism", "metabolic", "cardiovascular", "supplement", "fasting", "rucking",
        "vegetable", "atherosclerosis", "endotoxin", "fitness", "training", "vo2",
        "women 40", "medicine", "disease", "mortality", "cook", "food",
    ]),
    ("Money & Economics", "\U0001F4B0", "3P", [
        "finance", "economic", "economy", "market", "invest", "money", "shadow banking",
        "revenue", "business", "sell off", "sell-off", "grifter", "wealth", "valuation",
        "billion", "startup", "vc", "capital",
    ]),
    ("Mind & Philosophy", "\U0001F9D8", "2L", [
        "stoic", "philosophy", "ethic", "psycholog", "attention", "love", "meaning",
        "virtue", "consciousness", "mindful", "happiness", "dating", "relationship",
        "loved", "psychosis", "goldstein", "attention seeking",
    ]),
    ("Productivity & Knowledge", "\U0001F9E0", "0A/6I", [
        "second brain", "pkm", "note-taking", "note taking", "productivity",
        "context engineering", "workflow", "tiago forte", "knowledge management",
        "doable",
    ]),
    ("Society & Culture", "\U0001F30D", "8C/9E", [
        "media", "education", "pedagog", "society", "culture", "documentary",
        "humane education", "animal", "vegan", "epstein", "politic", "democracy",
        "decision making", "decision-making",
    ]),
]
FALLBACK_BUCKET = ("General", "\U0001F4DA", "0A", [])

# LBS-code fallback when keyword classification finds nothing (V7 frontmatter only).
LBS_BUCKET = {
    "4H": "Health & Nutrition", "2L": "Mind & Philosophy", "3P": "Money & Economics",
    "7A": "AI & Technology", "6I": "AI & Technology", "0A": "Productivity & Knowledge",
    "8C": "Society & Culture", "9E": "Society & Culture", "5R": "Society & Culture",
    "1N": "General",
}

CONTENT_TYPES = {
    "video": ("▶️", ["youtube.com", "youtu.be", "vimeo.com", "loom.com"]),
    "podcast": ("\U0001F3A7", ["spotify.com", "acast", "megaphone", "apple.co",
                                "podcast", "substack.com/api/v1/audio", "simplecast",
                                "buzzsprout", "libsyn"]),
}

MD_EXTENSIONS = ["extra", "sane_lists", "nl2br", "smarty"]

# Precompiled word-boundary matchers per bucket (avoids "ai" matching "brain").
_BUCKET_RE = [
    (b, [re.compile(r"\b" + re.escape(kw) + r"\b", re.I) for kw in b[3]])
    for b in BUCKETS
]

INDEX_JS = """
const q=document.getElementById('q'),chips=[...document.querySelectorAll('.chip')],
items=[...document.querySelectorAll('li.item')],secs=[...document.querySelectorAll('section.bucket')],
no=document.getElementById('noresults');let bf='all';
function apply(){const term=q.value.trim().toLowerCase();let shown=0;
items.forEach(li=>{const okB=bf==='all'||li.dataset.b===bf;
const okT=!term||li.dataset.s.includes(term);const v=okB&&okT;
li.style.display=v?'':'none';if(v)shown++;});
secs.forEach(s=>{const any=[...s.querySelectorAll('li.item')].some(li=>li.style.display!=='none');
s.style.display=any?'':'none';});no.style.display=shown?'none':'';}
q.addEventListener('input',apply);
chips.forEach(c=>c.addEventListener('click',()=>{chips.forEach(x=>x.classList.remove('active'));
c.classList.add('active');bf=c.dataset.b;apply();}));
"""

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
META_SOURCE = re.compile(r"\*\*Source:?\*\*[:\s]*\[?([^\]\)\n]+)\]?\(?([^)\n]*)\)?", re.I)
META_PROCESSED = re.compile(r"\*\*Processed:?\*\*[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.I)
META_DURATION = re.compile(r"\*\*Duration:?\*\*[:\s]*([A-Za-z0-9]+)", re.I)
TAG_TOKENS = re.compile(r"`+\s*([a-z0-9][\w\- /]*?)\s*`+", re.I)
FILENAME_DATE8 = re.compile(r"^(\d{4})(\d{2})(\d{2})[_-]")   # YYYYMMDD_  (legacy)
FILENAME_DATE6 = re.compile(r"^(\d{2})(\d{2})(\d{2})[_-]")     # YYMMDD-    (V7)
URL_RE = re.compile(r"https?://[^\s\)\]]+")
YAML_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:80] or "report"


def _date_from_filename(name: str) -> str | None:
    m = FILENAME_DATE8.match(name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = FILENAME_DATE6.match(name)
    if m:
        return f"20{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def _yymmdd_to_iso(v: str) -> str | None:
    v = str(v).strip()
    if re.fullmatch(r"\d{6}", v):
        return f"20{v[:2]}-{v[2:4]}-{v[4:]}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return v
    return None


def parse_report(path: Path) -> dict | None:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if PRIVACY_MARKER in raw:
        return None

    # --- V7 YAML frontmatter path -----------------------------------------
    fm: dict = {}
    fmm = YAML_FM.match(raw)
    if fmm:
        try:
            import yaml
            parsed = yaml.safe_load(fmm.group(1))
            if isinstance(parsed, dict):
                fm = parsed
        except Exception:  # noqa: BLE001
            fm = {}
        body_src = raw[fmm.end():]
    else:
        body_src = raw

    title = (str(fm.get("title")).strip() if fm.get("title") else None)
    source_url = (str(fm.get("source_url")).strip() if fm.get("source_url") else "")
    duration = (str(fm.get("duration")).strip() if fm.get("duration") else "")
    lbs = (str(fm.get("lbs")).strip().upper()[:2] if fm.get("lbs") else "")
    goal = (str(fm.get("goal")).strip() if fm.get("goal") else "")
    tags = []
    if isinstance(fm.get("tags"), list):
        tags = [str(t).lower().strip() for t in fm["tags"] if str(t).strip()]

    lines = body_src.splitlines()

    # Title fallback: first markdown H1 (strip leading emoji), then filename.
    if not title:
        for ln in lines[:40]:
            m = re.match(r"^#\s+(.+)", ln)
            if m:
                title = re.sub(r"^[\U0001F300-\U0001FAFF☀-➿]\s*", "", m.group(1).strip()).strip()
                break
    if not title:
        title = (path.stem.replace("_complete", "")
                 .split("-REPORT-OMNIMINER")[0].replace("_", " ").strip())

    # Date: frontmatter date_processed, else filename, else **Processed**, else epoch.
    date_iso = _yymmdd_to_iso(fm.get("date_processed", "")) if fm else None
    if not date_iso:
        date_iso = _date_from_filename(path.name)
    if not date_iso:
        mp = META_PROCESSED.search(raw)
        date_iso = mp.group(1) if mp else "1970-01-01"

    # Source URL fallback (legacy **Source** line, then first URL).
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

    # Legacy **Tags:** line
    if not tags:
        for ln in lines:
            if re.match(r"\s*\*\*Tags:?\*\*", ln, re.I):
                tags = [t.lower() for t in TAG_TOKENS.findall(ln)
                        if t.lower() not in ("tags",) and len(t) > 1]
                break

    # Body: strip everything from the transcript marker onward.
    cut = len(lines)
    for i, ln in enumerate(lines):
        if any(ln.strip().startswith(m) for m in TRANSCRIPT_MARKERS):
            cut = i
            break
    body_lines = lines[:cut]

    # Legacy double-title cleanup: start body at the emoji distillation title or ⚡.
    start = 0
    if not fm:
        for i, ln in enumerate(body_lines[:30]):
            if re.match(r"^#\s+[\U0001F300-\U0001FAFF]", ln) or ln.strip().startswith("## ⚡"):
                start = i
                break
    body_md = "\n".join(body_lines[start:]).strip()
    body_md = re.sub(r"^##\s+Summary\s*$", "", body_md, flags=re.M)

    # Classify by highest word-boundary keyword-hit score; LBS fallback; General.
    haystack = (title + " " + " ".join(tags) + " " + goal + " " + lbs)
    best_b, best_score = None, 0
    for b, pats in _BUCKET_RE:
        score = sum(1 for pat in pats if pat.search(haystack))
        if score > best_score:
            best_b, best_score = b, score
    bucket = best_b
    if bucket is None and lbs in LBS_BUCKET:
        label = LBS_BUCKET[lbs]
        bucket = next((b for b in BUCKETS + [FALLBACK_BUCKET] if b[0] == label), FALLBACK_BUCKET)
    if bucket is None:
        bucket = FALLBACK_BUCKET

    # Content type
    ctype = "article"
    cicon = "\U0001F4C4"
    for name, (icon, doms) in CONTENT_TYPES.items():
        if any(d in source_url.lower() for d in doms):
            ctype, cicon = name, icon
            break

    stem = (path.stem.replace("_complete", "")
            .split("-REPORT-OMNIMINER")[0])
    stem = re.sub(r"\s*\(\d+\)\s*$", "", stem)  # drop GDrive ' (N)' dup suffix
    return {
        "slug": slugify(stem) or slugify(title),
        "dedup_key": slugify(stem),
        "title": title,
        "date": date_iso,
        "source": source_url,
        "duration": duration,
        "tags": tags,
        "bucket": bucket[0],
        "bucket_icon": bucket[1],
        "bucket_lbs": bucket[2],
        "ctype": ctype,
        "ctype_icon": cicon,
        "body_md": body_md,
        "src_file": path.name,
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_md(body_md: str) -> str:
    return markdown.markdown(body_md, extensions=MD_EXTENSIONS, output_format="html5")


CSS = """
:root{--bg:#f4f5f7;--card:#fff;--ink:#33373d;--ink-strong:#1c1f24;--teal:#2f6f6b;
--teal-bg:#e3efee;--line:#e6e8eb;--muted:#9aa0a6;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);line-height:1.65}
a{color:var(--teal)}
.wrap{max-width:760px;margin:0 auto;padding:24px 16px 64px}
header.site{padding:28px 0 8px}
header.site h1{font-size:26px;margin:0 0 6px;color:var(--ink-strong)}
header.site p{margin:0;color:#5a6068;font-size:14px}
.controls{position:sticky;top:0;background:var(--bg);padding:14px 0 10px;z-index:5;border-bottom:1px solid var(--line);margin-bottom:8px}
#q{width:100%;padding:11px 14px;font-size:15px;border:1px solid var(--line);border-radius:10px;background:#fff;outline:none}
#q:focus{border-color:var(--teal)}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.chip{font-size:12px;padding:5px 11px;border:1px solid var(--line);border-radius:14px;background:#fff;cursor:pointer;color:#566;user-select:none}
.chip.active{background:var(--teal);color:#fff;border-color:var(--teal)}
.count{color:var(--muted);font-size:12px;margin-left:4px}
section.bucket{margin:26px 0 0}
section.bucket > h2{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--teal);border-bottom:1px solid var(--teal-bg);padding-bottom:6px;margin:0 0 4px}
ul.items{list-style:none;margin:0;padding:0}
li.item{padding:12px 2px;border-bottom:1px solid #eef0f2;display:flex;gap:10px;align-items:baseline}
li.item .ico{font-size:14px;flex:0 0 auto}
li.item a.t{font-weight:600;color:var(--ink-strong);text-decoration:none}
li.item a.t:hover{color:var(--teal);text-decoration:underline}
li.item .meta{display:block;font-size:12px;color:var(--muted);margin-top:2px}
li.item .tg{font-size:11px;color:#7a8088}
.empty{color:var(--muted);font-style:italic;padding:18px 0}
footer.site{margin-top:40px;text-align:center;color:var(--muted);font-size:11px}
/* report page */
.report .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:34px 38px}
.report h1{font-size:23px;color:var(--ink-strong);margin:0 0 10px;padding-bottom:12px;border-bottom:1px solid #ececef}
.report h2{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--teal);border-bottom:1px solid var(--teal-bg);padding-bottom:6px;margin:30px 0 12px}
.report h3{font-size:15px;color:var(--ink-strong)}
.report blockquote{border-left:3px solid var(--teal-bg);margin:0 0 14px;padding:2px 16px;color:#4a5057}
.report table{border-collapse:collapse;width:100%;font-size:14px;margin:0 0 16px}
.report th,.report td{border:1px solid var(--line);padding:7px 10px;text-align:left}
.report th{background:#f3f6f6}
.report code{font-size:12px;background:#eef1f3;border:1px solid #e1e5e8;padding:1px 6px;border-radius:10px}
.report img{max-width:100%}
.backlink{display:inline-block;margin:0 0 16px;font-size:13px;text-decoration:none}
.report .submeta{font-size:12px;color:var(--muted);margin:0 0 8px}
@media(max-width:620px){.report .card{padding:22px 18px}.wrap{padding:16px 12px 48px}}
"""


def report_page(r: dict) -> str:
    body = render_md(r["body_md"])
    src = (f'<a href="{html.escape(r["source"])}">source</a>'
           if r["source"] else "source n/a")
    dur = f' &middot; {html.escape(r["duration"])}' if r["duration"] else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(r["title"])} &middot; OmniMiner</title>
<link rel="stylesheet" href="../assets/om.css">
</head><body class="report"><div class="wrap">
<a class="backlink" href="../index.html">&larr; All reports</a>
<div class="card">
<p class="submeta">{r["ctype_icon"]} {html.escape(r["ctype"].title())} &middot; {r["bucket_icon"]} {html.escape(r["bucket"])} &middot; {html.escape(r["date"])}{dur} &middot; {src}</p>
{body}
</div>
<footer class="site">OmniMiner distillation &middot; published from the knowledge queue &middot; transcript withheld</footer>
</div></body></html>"""


def index_page(reports: list[dict], built_at: str) -> str:
    order = [b[0] for b in BUCKETS] + [FALLBACK_BUCKET[0]]
    by_bucket: dict[str, list[dict]] = {b: [] for b in order}
    for r in reports:
        by_bucket.setdefault(r["bucket"], []).append(r)

    chips = ['<span class="chip active" data-b="all">All<span class="count">'
             f'{len(reports)}</span></span>']
    sections = []
    for b in order:
        items = sorted(by_bucket.get(b, []), key=lambda x: x["date"], reverse=True)
        if not items:
            continue
        icon = next((x[1] for x in BUCKETS + [FALLBACK_BUCKET] if x[0] == b), "")
        chips.append(f'<span class="chip" data-b="{html.escape(b)}">{icon} '
                     f'{html.escape(b)}<span class="count">{len(items)}</span></span>')
        lis = []
        for r in items:
            tagstr = " ".join("#" + t for t in r["tags"][:5])
            search = html.escape((r["title"] + " " + " ".join(r["tags"]) + " " + b).lower())
            lis.append(
                f'<li class="item" data-b="{html.escape(b)}" data-s="{search}">'
                f'<span class="ico" title="{html.escape(r["ctype"])}">{r["ctype_icon"]}</span>'
                f'<div><a class="t" href="reports/{r["slug"]}.html">{html.escape(r["title"])}</a>'
                f'<span class="meta">{html.escape(r["date"])} '
                f'<span class="tg">{html.escape(tagstr)}</span></span></div></li>'
            )
        sections.append(
            f'<section class="bucket" data-b="{html.escape(b)}">'
            f'<h2>{icon} {html.escape(b)} <span class="count">{len(items)}</span></h2>'
            f'<ul class="items">{"".join(lis)}</ul></section>'
        )

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OmniMiner Reports</title>
<link rel="stylesheet" href="assets/om.css">
</head><body><div class="wrap">
<header class="site">
<h1>OmniMiner Reports</h1>
<p>Fact-checked distillations of videos, podcasts and articles from the OmniMiner knowledge pipeline. {len(reports)} reports.</p>
</header>
<div class="controls">
<input id="q" type="search" placeholder="Search title or tag&hellip;" autocomplete="off">
<div class="filters">{''.join(chips)}</div>
</div>
<div id="results">{''.join(sections)}</div>
<p class="empty" id="noresults" style="display:none">No reports match.</p>
<footer class="site">Generated {built_at} &middot; distillation only, transcripts withheld &middot;
per-report <code>EXCLUDE_FROM_PUBLIC</code> kill switch</footer>
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

    files = sorted(p for p in src.glob("*.md") if is_report(p))
    if args.limit:
        files = files[-args.limit:]

    parsed, skipped = [], []
    for p in files:
        try:
            r = parse_report(p)
        except Exception as e:  # noqa: BLE001
            skipped.append((p.name, f"parse error: {e}"))
            continue
        if r is None:
            skipped.append((p.name, "EXCLUDE_FROM_PUBLIC marker"))
            continue
        if r["slug"] in excludes or r["dedup_key"] in excludes:
            skipped.append((p.name, "in exclude.txt"))
            continue
        parsed.append((p, r))

    # Dedupe GDrive ' (N)' copies: keep the largest file per dedup_key.
    best: dict[str, tuple[Path, dict]] = {}
    for p, r in parsed:
        key = r["dedup_key"]
        if key not in best or p.stat().st_size > best[key][0].stat().st_size:
            if key in best:
                skipped.append((p.name, f"dup of {best[key][0].name}"))
            best[key] = (p, r)
        else:
            skipped.append((p.name, f"dup of {best[key][0].name}"))
    reports = [r for _, r in best.values()]

    # Ensure slug uniqueness (distinct captures, same title).
    seen: dict[str, int] = {}
    for r in reports:
        s = r["slug"]
        if s in seen:
            seen[s] += 1
            r["slug"] = f"{s}-{r['date'].replace('-', '')}"
        else:
            seen[s] = 1

    # Rebuild docs/ (preserve index.html scaffold backup once).
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
        "reports": [{k: r[k] for k in ("slug", "title", "date", "bucket", "ctype",
                                        "tags", "source", "src_file")} for r in reports],
    }
    (DOCS / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    if not args.quiet:
        from collections import Counter
        dist = Counter(r["bucket"] for r in reports)
        print(f"Built {len(reports)} reports ({len(skipped)} skipped) -> {DOCS}")
        for b, n in dist.most_common():
            print(f"  {n:3d}  {b}")
        if skipped[:5]:
            print("Skipped sample:", skipped[:5])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
