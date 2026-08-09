import importlib.util
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OMQ_PATH = ROOT / "omq.py"


def load_omq():
    spec = importlib.util.spec_from_file_location("omq", OMQ_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def report(title, body, *, source_type="article", topic="general", date="260101"):
    return f"""---
title: "{title}"
source_type: {source_type}
primary_topic: {topic}
processed_date: "{date}"
---

# {title}

## ⚡ BOTTOM LINE
{body}

## 💡 KEY INSIGHTS
{body}
"""


class OmqTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.source = self.base / "source"
        self.source.mkdir()
        self.db = self.base / ".omq.db"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        path = self.source / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_known_topics_rank_expected_report_in_top_three(self):
        expected = {
            "deep sleep": "260620-DEEP-SLEEP.md",
            "ai agents": "260621-AI-AGENTS.md",
            "tipping culture": "260622-TIPPING-CULTURE.md",
        }
        self.write(expected["deep sleep"], report(
            "How diet and meal timing influence deep sleep",
            "Deep sleep improves when meal timing protects circadian rhythm.",
            topic="sleep", date="260620"))
        self.write(expected["ai agents"], report(
            "Building effective AI agents",
            "AI agents need tools, memory, and bounded feedback loops.",
            topic="artificial intelligence", date="260621"))
        self.write(expected["tipping culture"], report(
            "How tipping culture took over the US",
            "Tipping culture shifted wage risk from employers to customers.",
            topic="society", date="260622"))
        for i in range(7):
            self.write(f"26010{i}-DISTRACTOR-{i}.md", report(
                f"Unrelated report {i}",
                "Gardening, architecture, and travel notes with neutral vocabulary.",
                date=f"26010{i}"))

        omq = load_omq()
        omq.sync_index(self.source, self.db)
        for query, filename in expected.items():
            results = omq.search(self.db, query, limit=3)
            self.assertIn(filename, [Path(row["path"]).name for row in results])

    def test_body_only_concept_is_retrievable(self):
        self.write("260701-NEUTRAL-TITLE.md", report(
            "A practical nutrition discussion",
            "The speaker explains glymphatic clearance during the night.",
            topic="health", date="260701"))
        self.write("260702-OTHER.md", report(
            "A second practical discussion",
            "The speaker explains household budgeting.",
            topic="finance", date="260702"))

        omq = load_omq()
        omq.sync_index(self.source, self.db)
        results = omq.search(self.db, "glymphatic clearance")
        self.assertEqual(Path(results[0]["path"]).name, "260701-NEUTRAL-TITLE.md")

    def test_legacy_eight_digit_filename_normalises_to_yymmdd(self):
        path = self.write("20260309-LEGACY.md", report(
            "Legacy report", "body", date=""))
        parsed = load_omq().parse_report(path)
        self.assertEqual(parsed["processed_date"], "260309")

    def test_reindex_twice_is_idempotent_and_reconciles_removed_files(self):
        kept = self.write("260701-KEPT.md", report("Kept", "alpha beta gamma"))
        removed = self.write("260702-REMOVED.md", report("Removed", "delta epsilon zeta"))
        omq = load_omq()

        first = omq.sync_index(self.source, self.db)
        second = omq.sync_index(self.source, self.db)
        self.assertEqual(first, {"indexed": 2, "removed": 0, "unchanged": 0})
        self.assertEqual(second, {"indexed": 0, "removed": 0, "unchanged": 2})
        with sqlite3.connect(self.db) as conn:
            before = conn.execute("SELECT path, mtime_ns, size FROM documents ORDER BY path").fetchall()
        removed.unlink()
        third = omq.sync_index(self.source, self.db)
        with sqlite3.connect(self.db) as conn:
            after = conn.execute("SELECT path, mtime_ns, size FROM documents ORDER BY path").fetchall()
        self.assertEqual(third, {"indexed": 0, "removed": 1, "unchanged": 1})
        self.assertEqual(after, [(str(kept.resolve()), kept.stat().st_mtime_ns, kept.stat().st_size)])

    def test_index_format_change_rebuilds_unchanged_files(self):
        self.write("260701-REPORT.md", report("Report", "alpha beta gamma"))
        omq = load_omq()
        omq.sync_index(self.source, self.db)
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE metadata SET value = 'old' WHERE key = 'index_version'")
        result = omq.sync_index(self.source, self.db)
        self.assertEqual(result, {"indexed": 1, "removed": 0, "unchanged": 0})

    def test_field_filters_and_symlink_exclusion(self):
        self.write("260601-PODCAST.md", report(
            "Sleep interview", "deep sleep circadian rhythm",
            source_type="podcast", topic="sleep", date="260601"))
        self.write("260701-ARTICLE.md", report(
            "Sleep article", "deep sleep circadian rhythm",
            source_type="article", topic="sleep", date="260701"))
        outside = self.base / "outside.md"
        outside.write_text(report("Outside", "deep sleep"), encoding="utf-8")
        (self.source / "260801-LINK.md").symlink_to(outside)

        omq = load_omq()
        omq.sync_index(self.source, self.db)
        results = omq.search(
            self.db, "deep sleep", source_type="article", topic="sleep", since="260650")
        self.assertEqual([Path(row["path"]).name for row in results], ["260701-ARTICLE.md"])

    def test_fresh_session_cli_and_routing_contract(self):
        self.write("260620-DEEP-SLEEP.md", report(
            "How diet and meal timing influence deep sleep",
            "Deep sleep improves when meal timing protects circadian rhythm.",
            topic="sleep", date="260620"))
        env = os.environ.copy()
        env["OMQ_SOURCE_DIR"] = str(self.source)
        env["OMQ_DB_PATH"] = str(self.db)
        run = subprocess.run(
            [sys.executable, str(OMQ_PATH), "deep sleep", "--limit", "3"],
            env=env, text=True, capture_output=True, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("260620-DEEP-SLEEP.md", run.stdout)

        skill_path = Path(os.environ.get(
            "OMQ_PKM_SKILL",
            "/Users/mitchens/Local/00-ENABLEMENT/SKILLS/personal-knowledge-manager/SKILL.md"))
        skill = skill_path.read_text(encoding="utf-8").lower()
        self.assertIn("run `omq` before any web search", skill)


if __name__ == "__main__":
    unittest.main()
