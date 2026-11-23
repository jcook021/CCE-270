from pathlib import Path
import tempfile
import unittest

from beam_calculations import UniformLoad, analyze_beam
from beam_calculation_sheet import export_calculation_sheet_pdf
from beam_design_io import BeamDesign


class BeamCalculationSheetTests(unittest.TestCase):
    def test_exports_pdf_with_inputs_diagrams_and_checks(self) -> None:
        design = BeamDesign(
            span_ft=20,
            support_type="Simply supported",
            material="Steel",
            section_name="W12x26",
            deflection_ratio=360,
            point_loads=(),
            uniform_loads=(UniformLoad(1, 0, 20),),
        )
        analysis = analyze_beam(
            design.span_ft,
            design.support_type,
            design.point_loads,
            design.uniform_loads,
            design.material,
            design.section_name,
            design.deflection_ratio,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calculation-sheet.pdf"
            export_calculation_sheet_pdf(path, design, analysis)
            content = path.read_bytes()

        self.assertTrue(content.startswith(b"%PDF-"))
        self.assertGreater(len(content), 10_000)


if __name__ == "__main__":
    unittest.main()
