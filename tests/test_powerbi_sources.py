"""Power BI source contracts and candidate integrity; no Desktop dependency."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_refresh_sources import contracts, inspect
from prepare_page2_candidate import build
from inspect_pbix import DEFAULT_PBIX, read_report


class RefreshSourcesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.first = Path(self.temp.name) / "original data"
        self.second = Path(self.temp.name) / "迁移数据 with spaces"
        for folder in (self.first, self.second):
            folder.mkdir()
            for name, columns in contracts().items():
                with (folder / f"{name}.csv").open("w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    writer.writerow(['São Paulo, 测试'] * len(columns))

    def test_seven_utf8_quoted_csvs_match_across_directories(self):
        first = inspect(self.first)
        self.assertEqual(len(first), 7)
        self.assertEqual(first, inspect(self.second))
        self.assertTrue(all(value["rows"] == 1 for value in first.values()))

    def test_missing_header_fails(self):
        path = self.first / "dim_customer.csv"
        path.write_text("customer_unique_id,customer_city\n1,city\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "expected headers"):
            inspect(self.first)

    def test_different_relocated_files_fail_cli(self):
        path = self.second / "dim_customer.csv"
        with path.open("a", encoding="utf-8") as f:
            f.write("another,city,SP\n")
        result = subprocess.run([sys.executable, str(ROOT / "scripts/check_refresh_sources.py"),
                                 str(self.first), "--compare-with", str(self.second)],
                                cwd=self.temp.name, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Relocated files differ", result.stderr)


class PageCandidateTests(unittest.TestCase):
    def test_candidate_preserves_model_and_corrects_axis_limits(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder) / "candidate.pbix"
            summary = build(DEFAULT_PBIX, candidate)
            self.assertTrue(summary["data_model_unchanged"])
            self.assertEqual(len(summary["changed_visuals"]), 4)
            self.assertEqual(read_report(candidate)["errors"], [])
            with zipfile.ZipFile(candidate) as z:
                prefix = "Report/definition/pages/commercial/visuals/"
                low = json.loads(z.read(prefix + "ff9e459478e8dc0c4493/visual.json"))
                self.assertEqual(low["visual"]["objects"]["valueAxis"][0]["properties"]["end"]["expr"]["Literal"]["Value"], "1D")
                monthly = json.loads(z.read(prefix + "9b140d1b57331f295972/visual.json"))
                self.assertEqual(monthly["visual"]["objects"]["categoryAxis"][0]["properties"]["axisType"]["expr"]["Literal"]["Value"], "'Continuous'")
            with self.assertRaisesRegex(ValueError, "new file"):
                build(DEFAULT_PBIX, candidate)


if __name__ == "__main__":
    unittest.main()
