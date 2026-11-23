from __future__ import annotations

import csv
from pathlib import Path

from beam_calculations import BeamAnalysis


CSV_HEADERS = ("x (ft)", "V (kips)", "M (kip-ft)", "Deflection (in)")


def export_results_csv(path: str | Path, analysis: BeamAnalysis) -> None:
    with Path(path).open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADERS)
        writer.writerows(
            (
                f"{x_ft:.6f}",
                f"{shear_kips:.6f}",
                f"{moment_kip_ft:.6f}",
                f"{deflection_in:.6f}",
            )
            for x_ft, shear_kips, moment_kip_ft, deflection_in in zip(
                analysis.x_ft,
                analysis.shear_kips,
                analysis.moment_kip_ft,
                analysis.deflection_in,
                strict=True,
            )
        )
