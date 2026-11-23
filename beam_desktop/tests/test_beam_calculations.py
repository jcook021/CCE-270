import unittest

from beam_calculations import (
    PointLoad,
    UniformLoad,
    analyze_beam,
    lightest_passing_section,
)


class BeamCalculationTests(unittest.TestCase):
    def test_simply_supported_uniform_load(self) -> None:
        result = analyze_beam(
            20,
            "Simply supported",
            [],
            [UniformLoad(1, 0, 20)],
            "Steel",
            "W12x26",
            360,
        )
        self.assertAlmostEqual(result.left_reaction_kips, 10)
        self.assertAlmostEqual(result.right_reaction_kips, 10)
        self.assertAlmostEqual(result.max_shear_kips, 10)
        self.assertAlmostEqual(result.max_moment_kip_ft, 50)
        self.assertAlmostEqual(result.max_moment_x_ft, 10)
        self.assertAlmostEqual(result.bending_stress_ksi, 17.96, places=2)
        self.assertAlmostEqual(result.max_deflection_in, 0.609, places=3)
        self.assertAlmostEqual(result.deflection_limit_in, 0.667, places=3)
        self.assertTrue(result.passes)

    def test_simply_supported_point_load(self) -> None:
        result = analyze_beam(
            20,
            "Simply supported",
            [PointLoad(10, 5)],
            [],
            "Steel",
            "W12x26",
            360,
        )
        self.assertAlmostEqual(result.left_reaction_kips, 7.5)
        self.assertAlmostEqual(result.right_reaction_kips, 2.5)
        self.assertAlmostEqual(result.max_moment_kip_ft, 37.5)
        self.assertAlmostEqual(result.max_moment_x_ft, 5)
        self.assertAlmostEqual(result.bending_stress_ksi, 13.47, places=2)
        self.assertAlmostEqual(result.max_deflection_in, 0.340, places=3)
        self.assertAlmostEqual(result.max_deflection_x_ft, 8.82, places=2)

    def test_cantilever_end_point_load(self) -> None:
        result = analyze_beam(
            10,
            "Cantilever",
            [PointLoad(5, 10)],
            [],
            "Steel",
            "W12x26",
            360,
        )
        self.assertAlmostEqual(result.left_reaction_kips, 5)
        self.assertAlmostEqual(result.fixed_end_moment_kip_ft, -50)
        self.assertAlmostEqual(result.max_deflection_in, 0.487, places=3)
        self.assertGreater(result.deflection_in[-1], 0)
        self.assertAlmostEqual(result.deflection_limit_in, 0.333, places=3)
        self.assertFalse(result.deflection_passes)

    def test_lumber_uniform_load(self) -> None:
        result = analyze_beam(
            12,
            "Simply supported",
            [],
            [UniformLoad(0.05, 0, 12)],
            "Douglas Fir-Larch No. 2",
            "2x10",
            360,
        )
        self.assertAlmostEqual(result.max_moment_kip_ft, 0.9)
        self.assertAlmostEqual(result.bending_stress_ksi, 0.505, places=3)
        self.assertAlmostEqual(result.max_deflection_in, 0.147, places=3)
        self.assertTrue(result.passes)

    def test_partial_uniform_load_reactions_and_maximum_moment(self) -> None:
        result = analyze_beam(
            30,
            "Simply supported",
            [],
            [UniformLoad(2, 0, 15)],
            "Steel",
            "W18x35",
            360,
        )
        self.assertAlmostEqual(result.left_reaction_kips, 22.5)
        self.assertAlmostEqual(result.right_reaction_kips, 7.5)
        self.assertAlmostEqual(result.max_moment_kip_ft, 126.5625)
        self.assertAlmostEqual(result.max_moment_x_ft, 11.25)

    def test_uniform_load_beyond_beam_is_clipped(self) -> None:
        result = analyze_beam(
            12,
            "Simply supported",
            [],
            [UniformLoad(1, 4, 20)],
            "Steel",
            "W12x26",
            360,
        )
        self.assertAlmostEqual(result.left_reaction_kips, 8 / 3)
        self.assertAlmostEqual(result.right_reaction_kips, 16 / 3)
        self.assertIn(12, result.x_ft)

    def test_lightest_passing_steel_section_is_from_catalog(self) -> None:
        section = lightest_passing_section(
            20,
            "Simply supported",
            [],
            [UniformLoad(1, 0, 20)],
            "Steel",
            360,
        )
        self.assertIsNotNone(section)
        self.assertEqual(section.name, "W14x22")

    def test_invalid_loads_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            analyze_beam(
                20,
                "Simply supported",
                [PointLoad(-1, 10)],
                [],
                "Steel",
                "W12x26",
                360,
            )
        with self.assertRaises(ValueError):
            analyze_beam(
                20,
                "Simply supported",
                [],
                [UniformLoad(1, 5, 4)],
                "Steel",
                "W12x26",
                360,
            )


if __name__ == "__main__":
    unittest.main()
