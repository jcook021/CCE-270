from __future__ import annotations

from pathlib import Path
import textwrap

from matplotlib.figure import Figure
from matplotlib.patches import Polygon

from beam_calculations import BeamAnalysis
from beam_design_io import BeamDesign, validate_design


def export_calculation_sheet_pdf(
    path: str | Path,
    design: BeamDesign,
    analysis: BeamAnalysis,
) -> None:
    validate_design(design)
    figure = Figure(figsize=(11, 8.5), facecolor="white")
    grid = figure.add_gridspec(
        6,
        1,
        height_ratios=(0.9, 0.8, 1.05, 1.05, 1.05, 0.8),
        hspace=0.36,
    )
    header = figure.add_subplot(grid[0])
    beam_axis = figure.add_subplot(grid[1])
    shear_axis = figure.add_subplot(grid[2], sharex=beam_axis)
    moment_axis = figure.add_subplot(grid[3], sharex=beam_axis)
    deflection_axis = figure.add_subplot(grid[4], sharex=beam_axis)
    checks = figure.add_subplot(grid[5])
    figure.subplots_adjust(left=0.09, right=0.97, top=0.96, bottom=0.06)

    _draw_header(header, design)
    _draw_beam(beam_axis, design, analysis)
    _draw_diagram(
        shear_axis,
        analysis.x_ft,
        analysis.shear_kips,
        "Shear (kips)",
        f"Max |V| = {analysis.max_shear_kips:.2f} k at {analysis.max_shear_x_ft:.2f} ft",
        "#176f86",
        stepped=True,
    )
    _draw_diagram(
        moment_axis,
        analysis.x_ft,
        analysis.moment_kip_ft,
        "Moment (kip-ft)",
        f"Max |M| = {analysis.max_moment_kip_ft:.2f} kip-ft "
        f"at {analysis.max_moment_x_ft:.2f} ft",
        "#27845d",
    )
    _draw_diagram(
        deflection_axis,
        analysis.x_ft,
        analysis.deflection_in,
        "Deflection (in)",
        f"Max |y| = {analysis.max_deflection_in:.3f} in "
        f"at {analysis.max_deflection_x_ft:.2f} ft",
        "#bb7616",
        xlabel="Position along beam (ft)",
    )
    _draw_checks(checks, analysis)
    figure.savefig(path, format="pdf", metadata={"Title": "Beam Calculation Sheet"})


def _draw_header(axis, design: BeamDesign) -> None:
    axis.set_axis_off()
    axis.text(
        0.0,
        1.0,
        "Beam Calculation Sheet",
        transform=axis.transAxes,
        va="top",
        fontsize=16,
        fontweight="bold",
        color="#172635",
    )
    axis.text(
        0.0,
        0.66,
        (
            f"Support: {design.support_type}    Span: {design.span_ft:g} ft    "
            f"Material: {design.material}    Section: {design.section_name}    "
            f"Deflection limit: L/{design.deflection_ratio}"
        ),
        transform=axis.transAxes,
        va="top",
        fontsize=9,
        color="#263746",
    )
    point_text = "; ".join(
        f"P{index} = {load.magnitude_kips:g} k at {load.position_ft:g} ft"
        for index, load in enumerate(design.point_loads, start=1)
    ) or "none"
    uniform_text = "; ".join(
        f"w{index} = {load.magnitude_kips_per_ft:g} k/ft "
        f"from {load.start_ft:g} to {load.end_ft:g} ft"
        for index, load in enumerate(design.uniform_loads, start=1)
    ) or "none"
    loads_text = textwrap.fill(
        f"Point loads: {point_text}    Uniform loads: {uniform_text}",
        width=150,
    )
    axis.text(
        0.0,
        0.30,
        loads_text,
        transform=axis.transAxes,
        va="top",
        fontsize=8,
        color="#263746",
    )


def _draw_beam(axis, design: BeamDesign, analysis: BeamAnalysis) -> None:
    span = design.span_ft
    axis.set_xlim(0, span)
    axis.set_ylim(-0.88, 1.65)
    axis.set_ylabel("Beam and loads")
    axis.set_yticks([])
    axis.grid(axis="x", color="#e8ecef", linewidth=0.6)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.plot([0, span], [0, 0], color="#243b53", linewidth=4, solid_capstyle="round")

    if design.support_type == "Simply supported":
        for x in (0, span):
            axis.add_patch(
                Polygon(
                    [(x, -0.06), (x - span * 0.022, -0.42), (x + span * 0.022, -0.42)],
                    closed=True,
                    facecolor="#8c9aa4",
                    edgecolor="#50616d",
                )
            )
    else:
        axis.axvspan(-span * 0.02, 0, ymin=0.14, ymax=0.66, color="#c5cdd2")
        axis.axvline(0, ymin=0.14, ymax=0.66, color="#50616d", linewidth=2)

    for index, load in enumerate(design.point_loads, start=1):
        axis.annotate(
            "",
            xy=(load.position_ft, 0.04),
            xytext=(load.position_ft, 0.70),
            arrowprops={"arrowstyle": "-|>", "color": "#b33d3d", "lw": 1.4},
        )
        axis.text(
            load.position_ft,
            0.76,
            f"P{index}={load.magnitude_kips:g} k",
            ha="center",
            va="bottom",
            fontsize=7,
            color="#9d3030",
        )

    for index, load in enumerate(design.uniform_loads, start=1):
        start = min(max(load.start_ft, 0.0), span)
        end = min(max(load.end_ft, 0.0), span)
        if end <= start:
            continue
        arrow_count = max(3, min(22, int((end - start) * 1.2)))
        for x in [start + (end - start) * i / (arrow_count - 1) for i in range(arrow_count)]:
            axis.annotate(
                "",
                xy=(x, 0.06),
                xytext=(x, 0.50),
                arrowprops={"arrowstyle": "-|>", "color": "#8f5d16", "lw": 0.8},
            )
        axis.plot([start, end], [0.52, 0.52], color="#8f5d16", linewidth=1)
        axis.text(
            (start + end) / 2,
            0.57,
            f"w{index}={load.magnitude_kips_per_ft:g} k/ft",
            ha="center",
            va="bottom",
            fontsize=7,
            color="#80500f",
        )

    reactions = [(0.0, analysis.left_reaction_kips, "A")]
    if design.support_type == "Simply supported":
        reactions.append((span, analysis.right_reaction_kips, "B"))
    for x, magnitude, label in reactions:
        axis.annotate(
            "",
            xy=(x, -0.03),
            xytext=(x, -0.39),
            arrowprops={"arrowstyle": "-|>", "color": "#28704d", "lw": 1.3},
        )
        axis.text(
            x,
            -0.49,
            f"{label}: {magnitude:.2f} k",
            ha="center",
            va="top",
            fontsize=7,
            color="#28704d",
        )
    if design.support_type == "Cantilever":
        axis.text(
            span * 0.08,
            -0.75,
            f"Fixed-end moment: {abs(analysis.fixed_end_moment_kip_ft):.2f} kip-ft",
            ha="left",
            va="top",
            fontsize=7,
        )


def _draw_diagram(
    axis,
    x_values,
    y_values,
    ylabel: str,
    title: str,
    color: str,
    stepped: bool = False,
    xlabel: str | None = None,
) -> None:
    axis.grid(True, color="#e8ecef", linewidth=0.6)
    axis.spines[["top", "right"]].set_visible(False)
    axis.axhline(0, color="#53636f", linewidth=0.7)
    if stepped:
        axis.fill_between(x_values, 0, y_values, step="post", color=color, alpha=0.2)
        axis.step(x_values, y_values, where="post", color=color, linewidth=1.1)
    else:
        axis.fill_between(x_values, 0, y_values, color=color, alpha=0.2)
        axis.plot(x_values, y_values, color=color, linewidth=1.1)
    axis.set_ylabel(ylabel)
    axis.set_title(title, loc="left", fontsize=8)
    if xlabel:
        axis.set_xlabel(xlabel)


def _draw_checks(axis, analysis: BeamAnalysis) -> None:
    axis.set_axis_off()
    bending_ratio = analysis.bending_stress_ksi / analysis.allowable_bending_stress_ksi
    deflection_ratio = analysis.max_deflection_in / analysis.deflection_limit_in
    _draw_check(
        axis,
        x=0.01,
        passed=analysis.bending_passes,
        ratio=bending_ratio,
        title="Bending",
        detail=(
            f"{analysis.bending_stress_ksi:.3f} ksi / "
            f"{analysis.allowable_bending_stress_ksi:.3f} ksi allowable"
        ),
    )
    _draw_check(
        axis,
        x=0.52,
        passed=analysis.deflection_passes,
        ratio=deflection_ratio,
        title="Deflection",
        detail=(
            f"{analysis.max_deflection_in:.3f} in / "
            f"{analysis.deflection_limit_in:.3f} in allowable"
        ),
    )


def _draw_check(axis, x: float, passed: bool, ratio: float, title: str, detail: str) -> None:
    color = "#24734f" if passed else "#b42318"
    axis.text(
        x,
        0.86,
        f"{title}: {'PASS' if passed else 'FAIL'} ({ratio * 100:.1f}%)",
        transform=axis.transAxes,
        va="top",
        fontsize=10,
        fontweight="bold",
        color=color,
    )
    axis.text(
        x,
        0.42,
        detail,
        transform=axis.transAxes,
        va="top",
        fontsize=8,
        color="#263746",
    )
