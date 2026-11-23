from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np


SupportType = Literal["Simply supported", "Cantilever"]
MaterialType = Literal["Steel", "Douglas Fir-Larch No. 2"]


@dataclass(frozen=True)
class Section:
    name: str
    ix_in4: float
    sx_in3: float
    weight_lb_ft: float | None = None


@dataclass(frozen=True)
class PointLoad:
    magnitude_kips: float
    position_ft: float


@dataclass(frozen=True)
class UniformLoad:
    magnitude_kips_per_ft: float
    start_ft: float
    end_ft: float


@dataclass(frozen=True)
class BeamAnalysis:
    x_ft: np.ndarray
    shear_kips: np.ndarray
    moment_kip_ft: np.ndarray
    deflection_in: np.ndarray
    left_reaction_kips: float
    right_reaction_kips: float
    fixed_end_moment_kip_ft: float
    max_shear_kips: float
    max_shear_x_ft: float
    max_moment_kip_ft: float
    max_moment_x_ft: float
    max_deflection_in: float
    max_deflection_x_ft: float
    bending_stress_ksi: float
    allowable_bending_stress_ksi: float
    deflection_limit_in: float
    bending_passes: bool
    deflection_passes: bool

    @property
    def passes(self) -> bool:
        return self.bending_passes and self.deflection_passes


MATERIAL_PROPERTIES: dict[MaterialType, tuple[float, float]] = {
    "Steel": (29_000.0, 30.0),
    "Douglas Fir-Larch No. 2": (1_600.0, 0.900),
}

SECTIONS: dict[MaterialType, tuple[Section, ...]] = {
    "Steel": (
        Section("W8x10", 30.8, 7.81, 10),
        Section("W10x12", 53.8, 10.9, 12),
        Section("W12x26", 204, 33.4, 26),
        Section("W14x22", 199, 29.0, 22),
        Section("W16x26", 301, 38.4, 26),
        Section("W18x35", 510, 57.6, 35),
        Section("W21x44", 843, 81.6, 44),
        Section("W24x55", 1350, 114, 55),
    ),
    "Douglas Fir-Larch No. 2": (
        Section("2x8", 47.63, 13.14),
        Section("2x10", 98.93, 21.39),
        Section("2x12", 177.98, 31.64),
    ),
}

DEFLECTION_LIMITS = (240, 360)
MAX_ANALYSIS_STEP_FT = 0.01


def section_by_name(material: MaterialType, section_name: str) -> Section:
    try:
        return next(section for section in SECTIONS[material] if section.name == section_name)
    except (KeyError, StopIteration) as error:
        raise ValueError(f"Unknown section {section_name!r} for {material!r}.") from error


def analyze_beam(
    span_ft: float,
    support_type: SupportType,
    point_loads: tuple[PointLoad, ...] | list[PointLoad],
    uniform_loads: tuple[UniformLoad, ...] | list[UniformLoad],
    material: MaterialType,
    section_name: str,
    deflection_ratio: int,
) -> BeamAnalysis:
    if not math.isfinite(span_ft) or not 4 <= span_ft <= 40:
        raise ValueError("Span must be between 4 and 40 ft.")
    if support_type not in ("Simply supported", "Cantilever"):
        raise ValueError(f"Unsupported support type: {support_type!r}.")
    if material not in MATERIAL_PROPERTIES:
        raise ValueError(f"Unsupported material: {material!r}.")
    if deflection_ratio not in DEFLECTION_LIMITS:
        raise ValueError("Deflection ratio must be 240 or 360.")

    section = section_by_name(material, section_name)
    _validate_loads(span_ft, point_loads, uniform_loads)

    span_in = span_ft * 12.0
    point_data = [(load.magnitude_kips, load.position_ft * 12.0) for load in point_loads]
    uniform_data = []
    for load in uniform_loads:
        start_ft = min(max(load.start_ft, 0.0), span_ft)
        end_ft = min(max(load.end_ft, 0.0), span_ft)
        if end_ft > start_ft:
            uniform_data.append(
                (load.magnitude_kips_per_ft / 12.0, start_ft * 12.0, end_ft * 12.0)
            )

    total_load = sum(magnitude for magnitude, _ in point_data)
    total_load += sum(w * (end - start) for w, start, end in uniform_data)
    moment_about_left = sum(magnitude * position for magnitude, position in point_data)
    moment_about_left += sum(
        w * (end**2 - start**2) / 2.0 for w, start, end in uniform_data
    )

    if support_type == "Simply supported":
        right_reaction = moment_about_left / span_in
        left_reaction = total_load - right_reaction
        fixed_moment = 0.0
    else:
        left_reaction = total_load
        right_reaction = 0.0
        fixed_moment = -moment_about_left

    x_ft = _analysis_grid(span_ft, point_loads, uniform_loads)
    x_in = x_ft * 12.0
    shear = np.full_like(x_in, left_reaction, dtype=float)
    moment = left_reaction * x_in + fixed_moment
    integrated_moment = left_reaction * x_in**3 / 6.0 + fixed_moment * x_in**2 / 2.0

    for magnitude, position in point_data:
        after_load = np.maximum(x_in - position, 0.0)
        shear -= magnitude * (x_in >= position)
        moment -= magnitude * after_load
        integrated_moment -= magnitude * after_load**3 / 6.0

    for w, start, end in uniform_data:
        after_start = np.maximum(x_in - start, 0.0)
        after_end = np.maximum(x_in - end, 0.0)
        shear -= w * np.clip(x_in - start, 0.0, end - start)
        moment += -w * after_start**2 / 2.0 + w * after_end**2 / 2.0
        integrated_moment += -w * after_start**4 / 24.0 + w * after_end**4 / 24.0

    if support_type == "Simply supported":
        slope_constant = -integrated_moment[-1] / span_in
    else:
        slope_constant = 0.0
    elastic_modulus, allowable_stress = MATERIAL_PROPERTIES[material]
    deflection = (integrated_moment + slope_constant * x_in) / (
        elastic_modulus * section.ix_in4
    )
    if support_type == "Cantilever":
        deflection = -deflection

    abs_shear = np.abs(shear)
    abs_moment_ft = np.abs(moment) / 12.0
    abs_deflection = np.abs(deflection)
    shear_index = int(np.argmax(abs_shear))
    moment_index = int(np.argmax(abs_moment_ft))
    deflection_index = int(np.argmax(abs_deflection))
    max_moment = float(abs_moment_ft[moment_index])
    bending_stress = max_moment * 12.0 / section.sx_in3
    deflection_limit = span_in / deflection_ratio

    return BeamAnalysis(
        x_ft=x_ft,
        shear_kips=shear,
        moment_kip_ft=moment / 12.0,
        deflection_in=deflection,
        left_reaction_kips=float(left_reaction),
        right_reaction_kips=float(right_reaction),
        fixed_end_moment_kip_ft=float(fixed_moment / 12.0),
        max_shear_kips=float(abs_shear[shear_index]),
        max_shear_x_ft=float(x_ft[shear_index]),
        max_moment_kip_ft=max_moment,
        max_moment_x_ft=float(x_ft[moment_index]),
        max_deflection_in=float(abs_deflection[deflection_index]),
        max_deflection_x_ft=float(x_ft[deflection_index]),
        bending_stress_ksi=float(bending_stress),
        allowable_bending_stress_ksi=allowable_stress,
        deflection_limit_in=deflection_limit,
        bending_passes=bending_stress <= allowable_stress,
        deflection_passes=float(abs_deflection[deflection_index]) <= deflection_limit,
    )


def lightest_passing_section(
    span_ft: float,
    support_type: SupportType,
    point_loads: tuple[PointLoad, ...] | list[PointLoad],
    uniform_loads: tuple[UniformLoad, ...] | list[UniformLoad],
    material: MaterialType,
    deflection_ratio: int,
) -> Section | None:
    passing: list[Section] = []
    for section in SECTIONS[material]:
        analysis = analyze_beam(
            span_ft,
            support_type,
            point_loads,
            uniform_loads,
            material,
            section.name,
            deflection_ratio,
        )
        if analysis.passes:
            passing.append(section)
    if not passing:
        return None
    if material == "Steel":
        return min(passing, key=lambda section: (section.weight_lb_ft or 0, -section.ix_in4))
    return passing[0]


def _validate_loads(
    span_ft: float,
    point_loads: tuple[PointLoad, ...] | list[PointLoad],
    uniform_loads: tuple[UniformLoad, ...] | list[UniformLoad],
) -> None:
    for load in point_loads:
        if not math.isfinite(load.magnitude_kips) or load.magnitude_kips < 0:
            raise ValueError("Point load magnitudes must be finite and nonnegative.")
        if not math.isfinite(load.position_ft) or not 0 <= load.position_ft <= span_ft:
            raise ValueError("Point load positions must be between zero and the span.")
    for load in uniform_loads:
        values = (
            load.magnitude_kips_per_ft,
            load.start_ft,
            load.end_ft,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Uniform load inputs must be finite numbers.")
        if load.magnitude_kips_per_ft < 0:
            raise ValueError("Uniform load magnitudes must be nonnegative.")
        if not 0 <= load.start_ft <= span_ft:
            raise ValueError("Uniform load starts must be between zero and the span.")
        if load.end_ft <= load.start_ft:
            raise ValueError("Uniform load end must be greater than its start.")


def _analysis_grid(
    span_ft: float,
    point_loads: tuple[PointLoad, ...] | list[PointLoad],
    uniform_loads: tuple[UniformLoad, ...] | list[UniformLoad],
) -> np.ndarray:
    count = max(1, math.ceil(span_ft / MAX_ANALYSIS_STEP_FT))
    points = list(np.linspace(0.0, span_ft, count + 1))
    epsilon = min(1e-6, MAX_ANALYSIS_STEP_FT / 100.0)
    for load in point_loads:
        position = load.position_ft
        points.append(position)
        if position > 0:
            points.append(max(0.0, position - epsilon))
    for load in uniform_loads:
        for position in (load.start_ft, min(load.end_ft, span_ft)):
            if 0 <= position <= span_ft:
                points.append(position)
    return np.unique(np.asarray(points, dtype=float))
