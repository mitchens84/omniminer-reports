import importlib.util
import hashlib
import json
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
        self.base = Path(self.tmp.name).resolve()
        self.source = self.base / "source"
        self.source.mkdir()
        self.db = self.base / ".omq.db"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        path = self.source / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_verified_private_report_searches_without_copying_to_public_source(self):
        self.write("public.md", report("Public", "public fixture"))
        runs = self.base / "private-runs"
        run = runs / "record-one"
        run.mkdir(parents=True)
        path = run / "report.md"
        body = report("Private podcast", "unique private insight", source_type="podcast")
        path.write_text(body)
        state = {"drive_verified": True, "identity": {"work_id": "podcast:one"},
                 "report_sha256": hashlib.sha256(body.encode()).hexdigest()}
        (run / "state.json").write_text(json.dumps(state))
        omq = load_omq()
        counts = omq.sync_index(self.source, self.db, private_runs=runs)
        self.assertEqual(counts["indexed"], 2)
        self.assertEqual(omq.search(self.db, "unique private")[0]["path"], str(path.resolve()))
        self.assertEqual(list(self.source.iterdir()), [self.source / "public.md"])
        self.assertEqual(self.db.stat().st_mode & 0o777, 0o600)
        self.assertEqual(omq.sync_index(self.source, self.db, private_runs=runs)["unchanged"], 2)
        path.write_text(body + "changed after verification")
        self.assertEqual(omq.sync_index(self.source, self.db, private_runs=runs)["removed"], 1)
        self.assertEqual(omq.search(self.db, "unique private"), [])
        self.assertEqual(len(omq.search(self.db, "public fixture")), 1)

    def test_private_search_rejects_symlink_and_unverified_report(self):
        runs = self.base / "runs"
        runs.mkdir()
        external = self.base / "external"
        external.mkdir()
        (runs / "linked-run").symlink_to(external, target_is_directory=True)
        run = runs / "unverified"
        run.mkdir()
        (run / "report.md").write_text("# Not accepted")
        (run / "state.json").write_text(json.dumps({"drive_verified": False}))
        self.assertEqual(load_omq()._private_report_files(runs), [])
        alias = self.base / "alias"
        alias.symlink_to(runs, target_is_directory=True)
        with self.assertRaises(ValueError):
            load_omq()._private_report_files(alias)

    def test_source_bound_knowledge_note_retrieval_and_tamper_withdrawal(self):
        run=self.base/'runs'/'one';run.mkdir(parents=True)
        body=report('Source report','source fixture');(run/'report.md').write_text(body)
        (run/'state.json').write_text(json.dumps({'drive_verified':True,'identity':{'work_id':'one'},'source_sha256':'source-hash','report_sha256':hashlib.sha256(body.encode()).hexdigest()}))
        note=run/'knowledge.md';note.write_text(report('Application','distinct actionable answer'))
        assets={'work_id':'one','source_sha256':'source-hash','artifacts':[{'format':'knowledge-note','path':str(note),'sha256':hashlib.sha256(note.read_bytes()).hexdigest()}]}
        manifest=run/'derived-artifacts.json';manifest.write_text(json.dumps(assets))
        omq=load_omq();omq.sync_index(self.source,self.db,private_runs=run.parent)
        self.assertEqual(omq.search(self.db,'distinct actionable')[0]['path'],str(note))
        note.write_text('tampered')
        omq.sync_index(self.source,self.db,private_runs=run.parent)
        self.assertEqual(omq.search(self.db,'distinct actionable'),[])
        outside=self.base/'outside.md';outside.write_text(report('Wrong home','outside content'))
        assets['artifacts'][0].update(path=str(outside),sha256=hashlib.sha256(outside.read_bytes()).hexdigest())
        manifest.write_text(json.dumps(assets))
        self.assertEqual(omq._private_report_files(run.parent),[run/'report.md'])

    def test_json_cli_preserves_structured_identity(self):
        p=self.write('one.md',report('Structured match','distinct structured query'))
        result=subprocess.run([sys.executable,str(OMQ_PATH),'distinct structured','--json'],capture_output=True,text=True,env=dict(os.environ,OMQ_SOURCE_DIR=str(self.source),OMQ_DB_PATH=str(self.db)),check=True)
        value=json.loads(result.stdout)
        self.assertEqual(value['results'][0]['path'],str(p))
        self.assertIn('inspect source lineage',value['evidence_class'])

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
