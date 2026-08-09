#!/usr/bin/env python3
"""omq — ranked local search over the OmniMiner source mirror."""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT / "source"
DEFAULT_DB = ROOT / ".omq.db"
INDEX_VERSION = "1"
SECTION_RE = re.compile(r"^##\s+.*?KEY INSIGHTS\s*$", re.IGNORECASE | re.MULTILINE)
NEXT_SECTION_RE = re.compile(r"^##\s+", re.MULTILINE)


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    fields = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip().strip('"').strip("'")
    return fields


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip().lstrip("📄 ")
    return "Untitled"


def _tags(text: str) -> list[str]:
    for line in text.splitlines():
        if line.lower().startswith("**tags:**") or (
                line.strip().startswith("`") and line.count("`") >= 2):
            return [tag.strip() for tag in re.findall(r"`([^`]+)`", line) if tag.strip()]
    return []


def _processed_date(path: Path, fields: dict[str, str]) -> str:
    match = re.match(r"(\d{8}|\d{6})", path.name)
    raw = fields.get("processed_date", "")
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 8:
        return digits[2:]
    if len(digits) == 6:
        return digits
    if match:
        prefix = match.group(1)
        return prefix[2:] if len(prefix) == 8 else prefix
    return ""


def _source_type(text: str, fields: dict[str, str]) -> str:
    declared = fields.get("source_type", "").lower()
    if declared in {"youtube", "podcast", "article"}:
        return declared
    lowered = text[:2500].lower()
    if "youtube.com" in lowered or "youtu.be" in lowered:
        return "youtube"
    if ".mp3" in lowered or "· podcast" in lowered or "**type:** podcast" in lowered:
        return "podcast"
    return "article"


def _section(text: str, heading_re: re.Pattern[str]) -> str:
    match = heading_re.search(text)
    if not match:
        return ""
    start = match.end()
    end_match = NEXT_SECTION_RE.search(text, start)
    return text[start:end_match.start() if end_match else len(text)].strip()


def parse_report(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    fields = _frontmatter(text)
    tags = _tags(text)
    topic = fields.get("primary_topic") or " ".join(tags)
    return {
        "path": str(path.resolve()),
        "title": fields.get("title") or _first_heading(text),
        "source_type": _source_type(text, fields),
        "primary_topic": topic,
        "processed_date": _processed_date(path, fields),
        "body": text,
        "key_insights": _section(text, SECTION_RE),
    }


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            mtime_ns INTEGER NOT NULL,
            size INTEGER NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS reports USING fts5(
            path UNINDEXED,
            title,
            source_type,
            primary_topic,
            processed_date UNINDEXED,
            body,
            key_insights,
            tokenize='unicode61'
        );
    """)
    return conn


def _source_files(source_dir: Path) -> list[Path]:
    root = source_dir.resolve(strict=True)
    files = []
    for path in root.iterdir():
        if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".md":
            continue
        if path.name in {"FEATURES_LOG.md", "_INDEX.md"}:
            continue
        files.append(path)
    return sorted(files)


def sync_index(source_dir: Path, db_path: Path) -> dict[str, int]:
    source_dir = Path(source_dir)
    db_path = Path(db_path)
    files = _source_files(source_dir)
    current_paths = {str(path.resolve()) for path in files}
    counts = {"indexed": 0, "removed": 0, "unchanged": 0}

    with _connect(db_path) as conn:
        version_row = conn.execute(
            "SELECT value FROM metadata WHERE key = 'index_version'").fetchone()
        if not version_row or version_row["value"] != INDEX_VERSION:
            conn.execute("DELETE FROM reports")
            conn.execute("DELETE FROM documents")
            conn.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES ('index_version', ?)",
                (INDEX_VERSION,))
        existing = {
            row["path"]: row
            for row in conn.execute("SELECT id, path, mtime_ns, size FROM documents")
        }
        for stale_path in sorted(set(existing) - current_paths):
            row_id = existing[stale_path]["id"]
            conn.execute("DELETE FROM reports WHERE rowid = ?", (row_id,))
            conn.execute("DELETE FROM documents WHERE id = ?", (row_id,))
            counts["removed"] += 1

        for path in files:
            resolved = str(path.resolve())
            stat = path.stat()
            old = existing.get(resolved)
            if old and old["mtime_ns"] == stat.st_mtime_ns and old["size"] == stat.st_size:
                counts["unchanged"] += 1
                continue

            report = parse_report(path)
            if old:
                row_id = old["id"]
                conn.execute("DELETE FROM reports WHERE rowid = ?", (row_id,))
                conn.execute(
                    "UPDATE documents SET mtime_ns = ?, size = ? WHERE id = ?",
                    (stat.st_mtime_ns, stat.st_size, row_id))
            else:
                cursor = conn.execute(
                    "INSERT INTO documents(path, mtime_ns, size) VALUES (?, ?, ?)",
                    (resolved, stat.st_mtime_ns, stat.st_size))
                row_id = cursor.lastrowid
            conn.execute(
                """INSERT INTO reports(
                       rowid, path, title, source_type, primary_topic,
                       processed_date, body, key_insights
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (row_id, report["path"], report["title"], report["source_type"],
                 report["primary_topic"], report["processed_date"], report["body"],
                 report["key_insights"]))
            counts["indexed"] += 1
    return counts


def _match_query(query: str) -> str:
    terms = re.findall(r"\w+", query, flags=re.UNICODE)
    if not terms:
        raise ValueError("query must contain at least one word")
    return " ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)


def _like_value(value: str) -> str:
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def search(
    db_path: Path,
    query: str,
    *,
    source_type: str | None = None,
    topic: str | None = None,
    since: str | None = None,
    limit: int = 10,
) -> list[dict[str, object]]:
    clauses = ["reports MATCH ?"]
    params: list[object] = [_match_query(query)]
    if source_type:
        clauses.append("lower(source_type) = lower(?)")
        params.append(source_type)
    if topic:
        clauses.append("lower(primary_topic) LIKE lower(?) ESCAPE '\\'")
        params.append(_like_value(topic))
    if since:
        if not re.fullmatch(r"\d{6}", since):
            raise ValueError("--since must be YYMMDD")
        clauses.append("processed_date >= ?")
        params.append(since)
    if limit < 1:
        raise ValueError("--limit must be at least 1")
    params.append(limit)
    sql = f"""
        SELECT path, title, source_type, primary_topic, processed_date,
               snippet(reports, 5, '<<', '>>', '…', 28) AS snippet,
               bm25(reports, 0.0, 8.0, 2.0, 4.0, 0.0, 1.0, 5.0) AS rank
          FROM reports
         WHERE {' AND '.join(clauses)}
         ORDER BY rank ASC, processed_date DESC, path ASC
         LIMIT ?
    """
    with _connect(Path(db_path)) as conn:
        return [dict(row) for row in conn.execute(sql, params)]


def _print_results(results: list[dict[str, object]]) -> None:
    for index, row in enumerate(results, 1):
        metadata = " · ".join(filter(None, (
            str(row["source_type"]), str(row["processed_date"]), str(row["primary_topic"]))))
        print(f"[{index}] {row['title']} ({metadata})")
        print(row["path"])
        print(str(row["snippet"]).replace("\n", " ").strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the local OmniMiner mirror with FTS5 BM25")
    parser.add_argument("query")
    parser.add_argument("--type", dest="source_type", choices=["youtube", "podcast", "article"])
    parser.add_argument("--topic")
    parser.add_argument("--since", metavar="YYMMDD")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    source_dir = Path(os.environ.get("OMQ_SOURCE_DIR", DEFAULT_SOURCE))
    db_path = Path(os.environ.get("OMQ_DB_PATH", DEFAULT_DB))
    try:
        sync_index(source_dir, db_path)
        _print_results(search(
            db_path, args.query, source_type=args.source_type, topic=args.topic,
            since=args.since, limit=args.limit))
    except (OSError, sqlite3.Error, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
