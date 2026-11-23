from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from beam_calculations import (
    MaterialType,
    PointLoad,
    SupportType,
    UniformLoad,
    analyze_beam,
)


FILE_FORMAT = "beam-designer"
FILE_VERSION = 1


@dataclass(frozen=True)
class BeamDesign:
    span_ft: float
    support_type: SupportType
    material: MaterialType
    section_name: str
    deflection_ratio: int
    point_loads: tuple[PointLoad, ...]
    uniform_loads: tuple[UniformLoad, ...]


def save_design(path: str | Path, design: BeamDesign) -> None:
    validate_design(design)
    data = {
        "format": FILE_FORMAT,
        "version": FILE_VERSION,
        "span_ft": design.span_ft,
        "support_type": design.support_type,
        "material": design.material,
        "section": design.section_name,
        "deflection_limit_ratio": design.deflection_ratio,
        "point_loads": [
            {
                "magnitude_kips": load.magnitude_kips,
                "position_ft": load.position_ft,
            }
            for load in design.point_loads
        ],
        "uniform_loads": [
            {
                "magnitude_kips_per_ft": load.magnitude_kips_per_ft,
                "start_ft": load.start_ft,
                "end_ft": load.end_ft,
            }
            for load in design.uniform_loads
        ],
    }
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def load_design(path: str | Path) -> BeamDesign:
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("Beam design file must contain a JSON object.")
    if data.get("format") != FILE_FORMAT:
        raise ValueError("This file is not a Beam Designer file.")
    if data.get("version") != FILE_VERSION:
        raise ValueError(f"Unsupported Beam Designer file version: {data.get('version')!r}.")

    support_type = data.get("support_type")
    material = data.get("material")
    section_name = data.get("section")
    if not isinstance(support_type, str):
        raise ValueError("Beam design support_type must be text.")
    if not isinstance(material, str):
        raise ValueError("Beam design material must be text.")
    if not isinstance(section_name, str):
        raise ValueError("Beam design section must be text.")

    ratio = data.get("deflection_limit_ratio")
    if isinstance(ratio, bool) or not isinstance(ratio, int):
        raise ValueError("Beam design deflection_limit_ratio must be an integer.")

    points = _load_point_loads(data.get("point_loads"))
    uniforms = _load_uniform_loads(data.get("uniform_loads"))
    design = BeamDesign(
        span_ft=_number(data.get("span_ft"), "span_ft"),
        support_type=support_type,  # validated in validate_design
        material=material,  # validated in validate_design
        section_name=section_name,
        deflection_ratio=ratio,
        point_loads=tuple(points),
        uniform_loads=tuple(uniforms),
    )
    validate_design(design)
    return design


def validate_design(design: BeamDesign) -> None:
    if not math.isfinite(design.span_ft):
        raise ValueError("Beam design span_ft must be finite.")
    analyze_beam(
        design.span_ft,
        design.support_type,
        design.point_loads,
        design.uniform_loads,
        design.material,
        design.section_name,
        design.deflection_ratio,
    )


def _load_point_loads(value: Any) -> list[PointLoad]:
    if not isinstance(value, list):
        raise ValueError("Beam design point_loads must be a list.")
    loads = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"Point load {index + 1} must be a JSON object.")
        loads.append(
            PointLoad(
                magnitude_kips=_number(item.get("magnitude_kips"), f"point_loads[{index}].magnitude_kips"),
                position_ft=_number(item.get("position_ft"), f"point_loads[{index}].position_ft"),
            )
        )
    return loads


def _load_uniform_loads(value: Any) -> list[UniformLoad]:
    if not isinstance(value, list):
        raise ValueError("Beam design uniform_loads must be a list.")
    loads = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"Uniform load {index + 1} must be a JSON object.")
        loads.append(
            UniformLoad(
                magnitude_kips_per_ft=_number(
                    item.get("magnitude_kips_per_ft"),
                    f"uniform_loads[{index}].magnitude_kips_per_ft",
                ),
                start_ft=_number(item.get("start_ft"), f"uniform_loads[{index}].start_ft"),
                end_ft=_number(item.get("end_ft"), f"uniform_loads[{index}].end_ft"),
            )
        )
    return loads


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Beam design {name} must be a number.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Beam design {name} must be finite.")
    return number
