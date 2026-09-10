"""The bridge and site must withhold every supported raw-source section."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bridge_sync
import build_site


class PublicSourceBoundary(unittest.TestCase):
    def test_purpose_led_topic_and_paragraphs_render_without_changing_lbs(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'260910-REPORT-OMNIMINER.md'
            path.write_text('---\nreport_schema: 3\nlbs: 6I\ntopic_category: Society & Culture\n---\n'
                            '# Critical reading\n\n' + ('An argument can connect evidence\nto a policy conclusion.\n\n' * 12))
            report = build_site.parse_report(path)
            self.assertEqual(report['category'], 'Society & Culture')
            self.assertEqual(report['lbs'], '6I')
            html = build_site.report_page(report)
            self.assertNotIn('evidence<br', html)

    def test_each_supported_source_section_is_removed_by_both_publication_legs(self):
        for heading in ('## Full Source', '## Extracted PDF Text', '## Full Transcript',
                        '## Transcript', '## Raw Transcript'):
            with self.subTest(heading=heading), tempfile.TemporaryDirectory() as temporary:
                body = ('The author describes the proposed mechanism and the limits of its evidence. ' * 8)
                raw = '# A useful report\n\n' + body + '\n\n' + heading + '\n\nRAW_SOURCE_CANARY\n'
                projected = bridge_sync._strip_transcript(raw)
                self.assertNotIn('RAW_SOURCE_CANARY', projected)
                self.assertIn(body.strip(), projected)
                path = Path(temporary)/'260910-REPORT-OMNIMINER.md'
                path.write_text(raw)
                parsed = build_site.parse_report(path)
                self.assertNotIn('_skip', parsed)
                self.assertNotIn('RAW_SOURCE_CANARY', str(parsed))


if __name__ == '__main__': unittest.main()
