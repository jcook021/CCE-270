import csv
from pathlib import Path
import tempfile
import unittest

from beam_calculations import UniformLoad, analyze_beam
from beam_results_export import CSV_HEADERS, export_results_csv


class BeamResultsExportTests(unittest.TestCase):
    def test_exports_header_and_all_analysis_samples(self) -> None:
        analysis = analyze_beam(
            4,
            "Simply supported",
            [],
            [UniformLoad(1, 0, 4)],
            "Steel",
            "W12x26",
            360,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "results.csv"
            export_results_csv(path, analysis)

            with path.open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.reader(file))

        self.assertEqual(tuple(rows[0]), CSV_HEADERS)
        self.assertEqual(len(rows), len(analysis.x_ft) + 1)
        self.assertEqual(rows[1], ["0.000000", "2.000000", "0.000000", "0.000000"])
        self.assertEqual(rows[-1][0], "4.000000")


if __name__ == "__main__":
    unittest.main()
