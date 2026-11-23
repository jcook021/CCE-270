import json
from pathlib import Path
import tempfile
import unittest

from beam_calculations import PointLoad, UniformLoad
from beam_design_io import BeamDesign, load_design, save_design


class BeamDesignFileTests(unittest.TestCase):
    def test_round_trip_preserves_all_beam_information(self) -> None:
        design = BeamDesign(
            span_ft=30,
            support_type="Simply supported",
            material="Steel",
            section_name="W18x35",
            deflection_ratio=240,
            point_loads=(PointLoad(2.5, 12.25),),
            uniform_loads=(UniformLoad(0.75, 4, 35),),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "design.json"
            save_design(path, design)
            self.assertEqual(load_design(path), design)

    def test_rejects_unknown_file_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.json"
            path.write_text(
                json.dumps({"format": "beam-designer", "version": 999}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "version"):
                load_design(path)

    def test_rejects_invalid_load_data(self) -> None:
        design = BeamDesign(
            span_ft=20,
            support_type="Simply supported",
            material="Steel",
            section_name="W12x26",
            deflection_ratio=360,
            point_loads=(PointLoad(-1, 10),),
            uniform_loads=(),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.json"
            with self.assertRaisesRegex(ValueError, "nonnegative"):
                save_design(path, design)


if __name__ == "__main__":
    unittest.main()
