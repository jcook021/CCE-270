from __future__ import annotations

from dataclasses import dataclass
import math
import tkinter as tk
from tkinter import ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon

from beam_calculations import (
    DEFLECTION_LIMITS,
    MATERIAL_PROPERTIES,
    SECTIONS,
    BeamAnalysis,
    MaterialType,
    PointLoad,
    SupportType,
    UniformLoad,
    analyze_beam,
    lightest_passing_section,
)


@dataclass
class LoadRow:
    kind: str
    frame: ttk.Frame
    magnitude_var: tk.StringVar
    position_var: tk.StringVar
    end_var: tk.StringVar | None = None


class BeamDesignerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Beam Designer")
        self.root.geometry("1450x980")
        self.root.minsize(1120, 760)

        self.support_var = tk.StringVar(value="Simply supported")
        self.span_var = tk.DoubleVar(value=20.0)
        self.span_entry_var = tk.StringVar(value="20")
        self.material_var = tk.StringVar(value="Steel")
        self.section_var = tk.StringVar(value="W12x26")
        self.deflection_ratio_var = tk.StringVar(value="L/360")
        self.error_var = tk.StringVar()
        self.rows: list[LoadRow] = []
        self._busy = False
        self._update_after: str | None = None
        self._point_drag_index: int | None = None
        self._point_positions: list[float] = []
        self._crosshair_lines = []
        self._crosshair_texts = []
        self._analysis: BeamAnalysis | None = None
        self._analysis_inputs: tuple | None = None
        self._suggested_section = None

        self._configure_styles()
        self._build_layout()
        self._add_uniform_load(default=True)
        self._schedule_recalculate()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.configure("AppTitle.TLabel", font=("TkDefaultFont", 20, "bold"))
        style.configure("Card.TLabelframe", padding=12)
        style.configure("Card.TLabelframe.Label", font=("TkDefaultFont", 11, "bold"))
        style.configure("Status.TLabel", font=("TkDefaultFont", 11, "bold"))
        style.configure(
            "Pass.Horizontal.TProgressbar",
            troughcolor="#e8edf0",
            background="#27845d",
        )
        style.configure(
            "Warn.Horizontal.TProgressbar",
            troughcolor="#e8edf0",
            background="#d2932a",
        )
        style.configure(
            "Fail.Horizontal.TProgressbar",
            troughcolor="#e8edf0",
            background="#c74343",
        )

    def _build_layout(self) -> None:
        shell = ttk.Frame(self.root, padding=14)
        shell.pack(fill=tk.BOTH, expand=True)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        left = ttk.Frame(shell, width=370)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.grid_propagate(False)
        left.rowconfigure(1, weight=1)

        ttk.Label(left, text="Beam Designer", style="AppTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        controls_canvas = tk.Canvas(left, highlightthickness=0, width=350)
        controls_scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=controls_canvas.yview)
        controls_canvas.configure(yscrollcommand=controls_scroll.set)
        controls_canvas.grid(row=1, column=0, sticky="nsew")
        controls_scroll.grid(row=1, column=1, sticky="ns")
        self.controls = ttk.Frame(controls_canvas, padding=(2, 2, 8, 8))
        self._controls_window = controls_canvas.create_window(
            (0, 0), window=self.controls, anchor="nw"
        )
        self.controls.bind(
            "<Configure>",
            lambda _event: controls_canvas.configure(
                scrollregion=controls_canvas.bbox("all")
            ),
        )
        controls_canvas.bind(
            "<Configure>",
            lambda event: controls_canvas.itemconfigure(
                self._controls_window, width=event.width
            ),
        )
        controls_canvas.bind_all(
            "<MouseWheel>",
            lambda event: controls_canvas.yview_scroll(
                int(-event.delta / 120), "units"
            ),
        )

        self._build_controls()

        right = ttk.Frame(shell)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)
        self._build_results(right)
        self._build_figure(right)

    def _build_controls(self) -> None:
        beam_card = ttk.LabelFrame(self.controls, text="Beam", style="Card.TLabelframe")
        beam_card.pack(fill=tk.X, pady=(0, 10))
        beam_card.columnconfigure(1, weight=1)

        ttk.Label(beam_card, text="Support").grid(row=0, column=0, sticky="w", pady=4)
        support = ttk.Combobox(
            beam_card,
            textvariable=self.support_var,
            values=("Simply supported", "Cantilever"),
            state="readonly",
        )
        support.grid(row=0, column=1, sticky="ew", pady=4)
        support.bind("<<ComboboxSelected>>", lambda _event: self._schedule_recalculate())

        ttk.Label(beam_card, text="Span (ft)").grid(row=1, column=0, sticky="w", pady=4)
        self.span_scale = ttk.Scale(
            beam_card,
            from_=4,
            to=40,
            variable=self.span_var,
            command=self._span_slider_changed,
        )
        self.span_scale.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(3, 0))
        span_entry = ttk.Entry(beam_card, textvariable=self.span_entry_var, width=9)
        span_entry.grid(row=1, column=1, sticky="e", pady=4)
        self.span_entry_var.trace_add("write", self._span_entry_changed)

        material_card = ttk.LabelFrame(
            self.controls, text="Material and section", style="Card.TLabelframe"
        )
        material_card.pack(fill=tk.X, pady=(0, 10))
        material_card.columnconfigure(1, weight=1)
        ttk.Label(material_card, text="Material").grid(row=0, column=0, sticky="w", pady=4)
        material = ttk.Combobox(
            material_card,
            textvariable=self.material_var,
            values=tuple(MATERIAL_PROPERTIES),
            state="readonly",
        )
        material.grid(row=0, column=1, sticky="ew", pady=4)
        material.bind("<<ComboboxSelected>>", self._material_changed)

        ttk.Label(material_card, text="Section").grid(row=1, column=0, sticky="w", pady=4)
        self.section_combo = ttk.Combobox(
            material_card,
            textvariable=self.section_var,
            state="readonly",
        )
        self.section_combo.grid(row=1, column=1, sticky="ew", pady=4)
        self.section_combo.bind("<<ComboboxSelected>>", lambda _event: self._schedule_recalculate())
        self._refresh_section_choices()

        ttk.Label(material_card, text="Deflection limit").grid(
            row=2, column=0, sticky="w", pady=4
        )
        limit = ttk.Combobox(
            material_card,
            textvariable=self.deflection_ratio_var,
            values=("L/240", "L/360"),
            state="readonly",
            width=10,
        )
        limit.grid(row=2, column=1, sticky="ew", pady=4)
        limit.bind("<<ComboboxSelected>>", lambda _event: self._schedule_recalculate())

        loads_card = ttk.LabelFrame(
            self.controls, text="Loads (downward)", style="Card.TLabelframe"
        )
        loads_card.pack(fill=tk.X, pady=(0, 10))
        buttons = ttk.Frame(loads_card)
        buttons.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(buttons, text="Add point load", command=self._add_point_load).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4)
        )
        ttk.Button(buttons, text="Add uniform load", command=self._add_uniform_load).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0)
        )
        self.loads_container = ttk.Frame(loads_card)
        self.loads_container.pack(fill=tk.X)

        ttk.Label(
            self.controls,
            textvariable=self.error_var,
            foreground="#b42318",
            wraplength=330,
        ).pack(fill=tk.X, pady=(2, 8))

    def _build_results(self, parent: ttk.Frame) -> None:
        cards = ttk.Frame(parent)
        cards.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        cards.columnconfigure((0, 1), weight=1)
        self.bending_card = self._make_check_card(
            cards,
            0,
            "Bending",
            "Bending stress: |Mmax| × 12 / Sx.",
        )
        self.deflection_card = self._make_check_card(
            cards,
            1,
            "Deflection",
            "Compare maximum absolute deflection with the selected L/240 or L/360 limit.",
        )

        suggestion = ttk.Frame(parent)
        suggestion.grid(row=0, column=1, sticky="e", padx=(12, 0), pady=(4, 10))
        self.suggestion_var = tk.StringVar(value="Lightest passing section: —")
        ttk.Label(suggestion, textvariable=self.suggestion_var, style="Status.TLabel").pack(
            side=tk.LEFT, padx=(0, 8)
        )
        self.use_section_button = ttk.Button(
            suggestion,
            text="Use section",
            command=self._use_suggested_section,
            state=tk.DISABLED,
        )
        self.use_section_button.pack(side=tk.LEFT)

        reaction_card = ttk.LabelFrame(
            parent,
            text="Support reactions",
            style="Card.TLabelframe",
        )
        reaction_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.reaction_var = tk.StringVar(value="Reactions: —")
        ttk.Label(
            reaction_card,
            textvariable=self.reaction_var,
            style="Status.TLabel",
        ).pack(anchor="w")

    def _make_check_card(
        self,
        parent: ttk.Frame,
        column: int,
        title: str,
        tooltip: str,
    ) -> dict[str, object]:
        card = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
        card.grid(row=0, column=column, sticky="ew")
        card.columnconfigure(0, weight=1)
        status = ttk.Label(card, text="—", style="Status.TLabel")
        status.grid(row=0, column=0, sticky="w")
        ratio = ttk.Label(card, text="—")
        ratio.grid(row=0, column=1, sticky="e")
        bar = ttk.Progressbar(card, maximum=100, mode="determinate")
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 3))
        detail = ttk.Label(card, text="—", foreground="#5d6871")
        detail.grid(row=2, column=0, columnspan=2, sticky="w")
        for widget in (card, status, ratio, bar, detail):
            self._add_tooltip(widget, tooltip)
        return {
            "status": status,
            "ratio": ratio,
            "bar": bar,
            "detail": detail,
        }

    def _build_figure(self, parent: ttk.Frame) -> None:
        figure = Figure(figsize=(10.5, 7.5), dpi=100, facecolor="white")
        axes = figure.subplots(
            4,
            1,
            sharex=True,
            gridspec_kw={"height_ratios": (1.0, 1.05, 1.05, 1.05)},
        )
        self.ax_beam, self.ax_shear, self.ax_moment, self.ax_deflection = axes
        figure.subplots_adjust(left=0.09, right=0.97, top=0.96, bottom=0.09, hspace=0.23)
        self.figure = figure
        self.figure_canvas = FigureCanvasTkAgg(figure, master=parent)
        self.figure_canvas.get_tk_widget().grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.figure_canvas.mpl_connect("button_press_event", self._on_plot_press)
        self.figure_canvas.mpl_connect("button_release_event", self._on_plot_release)
        self.figure_canvas.mpl_connect("motion_notify_event", self._on_plot_motion)

    def _add_point_load(self, default: bool = False) -> None:
        span = self.span_var.get()
        position = span if self.support_var.get() == "Cantilever" else span / 2.0
        self._add_load_row("point", "1", f"{position:g}")
        if not default:
            self._schedule_recalculate()

    def _add_uniform_load(self, default: bool = False) -> None:
        self._add_load_row("uniform", "1", "0", f"{self.span_var.get():g}")
        if not default:
            self._schedule_recalculate()

    def _add_load_row(
        self,
        kind: str,
        magnitude: str,
        position: str,
        end: str | None = None,
    ) -> None:
        frame = ttk.Frame(self.loads_container, padding=(0, 5))
        frame.pack(fill=tk.X, expand=True)
        frame.columnconfigure(1, weight=1)
        magnitude_var = tk.StringVar(value=magnitude)
        position_var = tk.StringVar(value=position)
        end_var = tk.StringVar(value=end) if end is not None else None
        row = LoadRow(kind, frame, magnitude_var, position_var, end_var)
        self.rows.append(row)

        heading = "Point load" if kind == "point" else "Uniform load"
        ttk.Label(frame, text=heading, font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(
            frame,
            text="Remove",
            width=8,
            command=lambda load_row=row: self._remove_load_row(load_row),
        ).grid(row=0, column=2, sticky="e")
        ttk.Label(frame, text="Magnitude (k)" if kind == "point" else "Load (k/ft)").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Entry(frame, textvariable=magnitude_var, width=9).grid(
            row=1, column=1, sticky="ew", padx=(6, 0), pady=(4, 0)
        )
        if kind == "point":
            ttk.Label(frame, text="Position (ft)").grid(
                row=2, column=0, sticky="w", pady=(4, 0)
            )
            ttk.Entry(frame, textvariable=position_var, width=9).grid(
                row=2, column=1, sticky="ew", padx=(6, 0), pady=(4, 0)
            )
        else:
            ttk.Label(frame, text="Start (ft)").grid(row=2, column=0, sticky="w", pady=(4, 0))
            ttk.Entry(frame, textvariable=position_var, width=9).grid(
                row=2, column=1, sticky="ew", padx=(6, 0), pady=(4, 0)
            )
            ttk.Label(frame, text="End (ft)").grid(row=3, column=0, sticky="w", pady=(4, 0))
            ttk.Entry(frame, textvariable=end_var, width=9).grid(
                row=3, column=1, sticky="ew", padx=(6, 0), pady=(4, 0)
            )
        ttk.Separator(frame).grid(
            row=4 if kind == "uniform" else 3,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(8, 0),
        )

        for variable in (magnitude_var, position_var, end_var):
            if variable is not None:
                variable.trace_add("write", lambda *_: self._schedule_recalculate())

    def _remove_load_row(self, row: LoadRow) -> None:
        if row in self.rows:
            self.rows.remove(row)
            row.frame.destroy()
            self._schedule_recalculate()

    def _span_slider_changed(self, value: str) -> None:
        if self._busy:
            return
        self._busy = True
        self.span_entry_var.set(f"{float(value):g}")
        self._busy = False
        self._schedule_recalculate()

    def _span_entry_changed(self, *_args) -> None:
        if self._busy:
            return
        text = self.span_entry_var.get().strip()
        try:
            value = float(text)
        except ValueError:
            self.error_var.set("Enter a span between 4 and 40 ft.")
            self._schedule_recalculate()
            return
        if not math.isfinite(value) or not 4 <= value <= 40:
            self.error_var.set("Span must be between 4 and 40 ft.")
            self._schedule_recalculate()
            return
        self._busy = True
        self.span_var.set(value)
        self._busy = False
        self.error_var.set("")
        self._schedule_recalculate()

    def _material_changed(self, _event=None) -> None:
        self._refresh_section_choices()
        self._schedule_recalculate()

    def _refresh_section_choices(self) -> None:
        material = self.material_var.get()
        names = [section.name for section in SECTIONS[material]]
        self.section_combo.configure(values=names)
        if self.section_var.get() not in names:
            self.section_var.set(names[0] if material != "Steel" else "W12x26")

    def _schedule_recalculate(self) -> None:
        if self._update_after is not None:
            self.root.after_cancel(self._update_after)
        self._update_after = self.root.after(35, self._recalculate)

    def _recalculate(self) -> None:
        self._update_after = None
        try:
            span = float(self.span_entry_var.get())
            if not math.isfinite(span) or not 4 <= span <= 40:
                raise ValueError("Span must be between 4 and 40 ft.")
            point_loads: list[PointLoad] = []
            uniform_loads: list[UniformLoad] = []
            for row in self.rows:
                magnitude = float(row.magnitude_var.get())
                position = float(row.position_var.get())
                if row.kind == "point":
                    point_loads.append(PointLoad(magnitude, position))
                else:
                    if row.end_var is None:
                        raise ValueError("Uniform load end position is missing.")
                    uniform_loads.append(
                        UniformLoad(magnitude, position, float(row.end_var.get()))
                    )

            ratio = {"L/240": 240, "L/360": 360}.get(self.deflection_ratio_var.get())
            if ratio is None:
                raise ValueError("Select a deflection limit of L/240 or L/360.")
            material = self.material_var.get()
            section_name = self.section_var.get()
            analysis = analyze_beam(
                span,
                self.support_var.get(),  # type: ignore[arg-type]
                point_loads,
                uniform_loads,
                material,  # type: ignore[arg-type]
                section_name,
                ratio,
            )
        except ValueError as error:
            self.error_var.set(str(error))
            self._analysis = None
            self._suggested_section = None
            self.reaction_var.set("Reactions: —")
            self.suggestion_var.set("Lightest passing section: —")
            self.use_section_button.configure(state=tk.DISABLED)
            self._clear_check_card(self.bending_card)
            self._clear_check_card(self.deflection_card)
            self._draw_empty_plot()
            return

        self.error_var.set("")
        self._analysis = analysis
        if self.support_var.get() == "Cantilever":
            self.reaction_var.set(
                f"Fixed support A: {analysis.left_reaction_kips:.2f} kips upward"
                f"    Fixed-end moment: {abs(analysis.fixed_end_moment_kip_ft):.2f} kip-ft"
            )
        else:
            self.reaction_var.set(
                f"A (left): {analysis.left_reaction_kips:.2f} kips upward"
                f"    B (right): {analysis.right_reaction_kips:.2f} kips upward"
            )
        self._analysis_inputs = (
            span,
            self.support_var.get(),
            point_loads,
            uniform_loads,
            material,
            ratio,
        )
        self._update_check_card(
            self.bending_card,
            analysis.bending_passes,
            analysis.bending_stress_ksi,
            analysis.allowable_bending_stress_ksi,
            "ksi",
        )
        self._update_check_card(
            self.deflection_card,
            analysis.deflection_passes,
            analysis.max_deflection_in,
            analysis.deflection_limit_in,
            "in",
        )
        self._suggested_section = lightest_passing_section(
            span,
            self.support_var.get(),  # type: ignore[arg-type]
            point_loads,
            uniform_loads,
            material,  # type: ignore[arg-type]
            ratio,
        )
        if self._suggested_section is None:
            self.suggestion_var.set("Lightest passing section: none")
            self.use_section_button.configure(state=tk.DISABLED)
        else:
            section = self._suggested_section
            weight = (
                f", {section.weight_lb_ft:g} lb/ft"
                if section.weight_lb_ft is not None
                else ""
            )
            self.suggestion_var.set(f"Lightest passing section: {section.name}{weight}")
            self.use_section_button.configure(state=tk.NORMAL)
        self._draw_analysis(analysis, span, point_loads, uniform_loads)

    def _update_check_card(
        self,
        card: dict[str, object],
        passed: bool,
        actual: float,
        allowable: float,
        unit: str,
    ) -> None:
        ratio = actual / allowable if allowable else math.inf
        status = card["status"]
        ratio_label = card["ratio"]
        bar = card["bar"]
        detail = card["detail"]
        assert isinstance(status, ttk.Label)
        assert isinstance(ratio_label, ttk.Label)
        assert isinstance(bar, ttk.Progressbar)
        assert isinstance(detail, ttk.Label)
        status.configure(
            text="PASS" if passed else "FAIL",
            foreground="#24734f" if passed else "#b42318",
        )
        ratio_label.configure(text=f"{ratio * 100:.1f}%")
        style = (
            "Pass.Horizontal.TProgressbar"
            if ratio < 0.7
            else "Warn.Horizontal.TProgressbar"
            if ratio <= 1.0
            else "Fail.Horizontal.TProgressbar"
        )
        bar.configure(value=min(100.0, ratio * 100), style=style)
        detail.configure(text=f"{actual:.3f} {unit} / {allowable:.3f} {unit} allowable")

    def _clear_check_card(self, card: dict[str, object]) -> None:
        status = card["status"]
        ratio = card["ratio"]
        bar = card["bar"]
        detail = card["detail"]
        assert isinstance(status, ttk.Label)
        assert isinstance(ratio, ttk.Label)
        assert isinstance(bar, ttk.Progressbar)
        assert isinstance(detail, ttk.Label)
        status.configure(text="—", foreground="#5d6871")
        ratio.configure(text="—")
        bar.configure(value=0)
        detail.configure(text="—")

    def _use_suggested_section(self) -> None:
        if self._suggested_section is not None:
            self.section_var.set(self._suggested_section.name)
            self._schedule_recalculate()

    def _add_tooltip(self, widget: tk.Widget, text: str) -> None:
        popup: tk.Toplevel | None = None

        def show(_event=None) -> None:
            nonlocal popup
            if popup is not None:
                return
            popup = tk.Toplevel(self.root)
            popup.wm_overrideredirect(True)
            popup.wm_geometry(f"+{self.root.winfo_pointerx() + 12}+{self.root.winfo_pointery() + 12}")
            ttk.Label(popup, text=text, padding=8, relief=tk.SOLID, wraplength=300).pack()

        def hide(_event=None) -> None:
            nonlocal popup
            if popup is not None:
                popup.destroy()
                popup = None

        widget.bind("<Enter>", show, add="+")
        widget.bind("<Leave>", hide, add="+")

    def _draw_empty_plot(self) -> None:
        for axis in (self.ax_beam, self.ax_shear, self.ax_moment, self.ax_deflection):
            axis.clear()
        self.ax_beam.text(0.5, 0.5, "Correct the inputs to show beam analysis", ha="center")
        self.ax_beam.set_axis_off()
        self.ax_shear.set_ylabel("Shear (k)")
        self.ax_moment.set_ylabel("Moment (kip-ft)")
        self.ax_deflection.set_ylabel("Deflection (in)")
        self.ax_deflection.set_xlabel("Position along beam (ft)")
        self.figure_canvas.draw_idle()

    def _draw_analysis(
        self,
        result: BeamAnalysis,
        span: float,
        point_loads: list[PointLoad],
        uniform_loads: list[UniformLoad],
    ) -> None:
        for axis in (self.ax_beam, self.ax_shear, self.ax_moment, self.ax_deflection):
            axis.clear()
            axis.grid(True, color="#e8ecef", linewidth=0.7)
            axis.spines[["top", "right"]].set_visible(False)

        self.ax_beam.set_ylabel("Beam and loads")
        self.ax_beam.set_ylim(-0.9, 2.0)
        self.ax_beam.set_xlim(0, span)
        self.ax_beam.set_yticks([])
        self.ax_beam.plot([0, span], [0, 0], color="#243b53", linewidth=5, solid_capstyle="round")
        self._draw_supports(span)
        self._draw_loads(span, point_loads, uniform_loads)
        self._draw_reactions(result, span)

        self.ax_shear.fill_between(
            result.x_ft, 0, result.shear_kips, step="post", color="#3f88a8", alpha=0.24
        )
        self.ax_shear.step(result.x_ft, result.shear_kips, where="post", color="#176f86")
        self.ax_shear.axhline(0, color="#53636f", linewidth=0.8)
        self.ax_shear.set_ylabel("Shear (k)")
        self.ax_shear.set_title(
            f"Max |V| = {result.max_shear_kips:.2f} k at {result.max_shear_x_ft:.2f} ft",
            loc="left",
            fontsize=9,
        )

        self.ax_moment.fill_between(
            result.x_ft, 0, result.moment_kip_ft, color="#5b9e72", alpha=0.24
        )
        self.ax_moment.plot(result.x_ft, result.moment_kip_ft, color="#27845d")
        self.ax_moment.axhline(0, color="#53636f", linewidth=0.8)
        self.ax_moment.set_ylabel("Moment\n(kip-ft)")
        self.ax_moment.set_title(
            f"Max |M| = {result.max_moment_kip_ft:.2f} kip-ft "
            f"at {result.max_moment_x_ft:.2f} ft",
            loc="left",
            fontsize=9,
        )

        self.ax_deflection.fill_between(
            result.x_ft, 0, result.deflection_in, color="#d89a39", alpha=0.24
        )
        self.ax_deflection.plot(result.x_ft, result.deflection_in, color="#bb7616")
        self.ax_deflection.axhline(0, color="#53636f", linewidth=0.8)
        self.ax_deflection.set_ylabel("Deflection\n(in)")
        self.ax_deflection.set_xlabel("Position along beam (ft)")
        self.ax_deflection.set_title(
            f"Max |y| = {result.max_deflection_in:.3f} in "
            f"at {result.max_deflection_x_ft:.2f} ft",
            loc="left",
            fontsize=9,
        )

        self._crosshair_lines = []
        self._crosshair_texts = []
        for axis in (self.ax_shear, self.ax_moment, self.ax_deflection):
            line = axis.axvline(0, color="#263746", linewidth=0.9, alpha=0.8, visible=False)
            text = axis.text(
                0.99,
                0.9,
                "",
                transform=axis.transAxes,
                ha="right",
                va="top",
                fontsize=8,
                bbox={"facecolor": "white", "edgecolor": "#cbd5dc", "alpha": 0.9},
            )
            self._crosshair_lines.append(line)
            self._crosshair_texts.append(text)

        self.figure_canvas.draw_idle()

    def _draw_supports(self, span: float) -> None:
        if self.support_var.get() == "Simply supported":
            for x in (0, span):
                triangle = Polygon(
                    [(x, -0.08), (x - span * 0.025, -0.52), (x + span * 0.025, -0.52)],
                    closed=True,
                    facecolor="#8c9aa4",
                    edgecolor="#50616d",
                )
                self.ax_beam.add_patch(triangle)
                self.ax_beam.plot(
                    [x - span * 0.035, x + span * 0.035],
                    [-0.57, -0.57],
                    color="#50616d",
                    linewidth=1.5,
                )
        else:
            self.ax_beam.axvspan(-span * 0.025, 0, ymin=0.13, ymax=0.7, color="#c5cdd2")
            self.ax_beam.axvline(0, ymin=0.13, ymax=0.7, color="#50616d", linewidth=2)
            for y in np.linspace(-0.5, 0.3, 7):
                self.ax_beam.plot([-span * 0.025, 0], [y, y + 0.14], color="#8797a1", linewidth=0.8)
        self.ax_beam.text(0, -0.72, "A", ha="center", fontsize=8)
        self.ax_beam.text(span, -0.72, "B" if self.support_var.get() == "Simply supported" else "Free", ha="center", fontsize=8)

    def _draw_loads(
        self,
        span: float,
        point_loads: list[PointLoad],
        uniform_loads: list[UniformLoad],
    ) -> None:
        self._point_positions = []
        for index, load in enumerate(point_loads):
            x = load.position_ft
            self._point_positions.append(x)
            self.ax_beam.annotate(
                "",
                xy=(x, 0.06),
                xytext=(x, 0.83),
                arrowprops={"arrowstyle": "-|>", "color": "#b33d3d", "lw": 1.6},
            )
            self.ax_beam.text(
                x,
                0.91,
                f"P{index + 1}={load.magnitude_kips:g} k",
                ha="center",
                va="bottom",
                color="#9d3030",
                fontsize=8,
            )

        for index, load in enumerate(uniform_loads):
            start = min(max(load.start_ft, 0), span)
            end = min(max(load.end_ft, 0), span)
            if end <= start:
                continue
            count = max(3, min(25, int((end - start) * 1.3)))
            for x in np.linspace(start, end, count):
                self.ax_beam.annotate(
                    "",
                    xy=(x, 0.08),
                    xytext=(x, 0.62),
                    arrowprops={"arrowstyle": "-|>", "color": "#8f5d16", "lw": 0.9},
                )
            self.ax_beam.plot([start, end], [0.64, 0.64], color="#8f5d16", linewidth=1.2)
            self.ax_beam.text(
                (start + end) / 2,
                0.72,
                f"w{index + 1}={load.magnitude_kips_per_ft:g} k/ft",
                ha="center",
                va="bottom",
                color="#80500f",
                fontsize=8,
            )

    def _draw_reactions(self, result: BeamAnalysis, span: float) -> None:
        positions = [0]
        magnitudes = [result.left_reaction_kips]
        if self.support_var.get() == "Simply supported":
            positions.append(span)
            magnitudes.append(result.right_reaction_kips)
        for index, (x, magnitude) in enumerate(zip(positions, magnitudes)):
            self.ax_beam.annotate(
                "",
                xy=(x, -0.05),
                xytext=(x, -0.5),
                arrowprops={"arrowstyle": "-|>", "color": "#28704d", "lw": 1.5},
            )
            offset = 0.25 if index == 0 else -0.25
            self.ax_beam.text(
                x + offset,
                -0.29,
                f"R={magnitude:.2f} k",
                ha="center",
                color="#28704d",
                fontsize=8,
            )
        if self.support_var.get() == "Cantilever":
            self.ax_beam.text(
                span * 0.08,
                -0.82,
                f"Fixed-end moment = {abs(result.fixed_end_moment_kip_ft):.2f} kip-ft",
                ha="left",
                fontsize=8,
            )

    def _on_plot_press(self, event) -> None:
        if event.inaxes is not self.ax_beam or event.xdata is None or event.button != 1:
            return
        if not self._point_positions:
            return
        distances = [abs(position - event.xdata) for position in self._point_positions]
        nearest = int(np.argmin(distances))
        if distances[nearest] <= max(0.3, self.span_var.get() * 0.02):
            self._point_drag_index = nearest

    def _on_plot_release(self, _event) -> None:
        self._point_drag_index = None

    def _on_plot_motion(self, event) -> None:
        if self._point_drag_index is not None and event.inaxes is self.ax_beam and event.xdata is not None:
            index = self._point_drag_index
            rows = [row for row in self.rows if row.kind == "point"]
            if index < len(rows):
                span = self.span_var.get()
                snapped = round(min(max(event.xdata, 0), span) * 4) / 4
                rows[index].position_var.set(f"{snapped:g}")
            return

        axes = (self.ax_shear, self.ax_moment, self.ax_deflection)
        if event.inaxes not in axes or event.xdata is None or self._analysis is None:
            for line in self._crosshair_lines:
                line.set_visible(False)
            self.figure_canvas.draw_idle()
            return

        result = self._analysis
        index = int(np.argmin(np.abs(result.x_ft - event.xdata)))
        values = (
            f"V = {result.shear_kips[index]:.3f} k",
            f"M = {result.moment_kip_ft[index]:.3f} kip-ft",
            f"y = {result.deflection_in[index]:.4f} in",
        )
        for line, label, value in zip(self._crosshair_lines, self._crosshair_texts, values):
            line.set_xdata([result.x_ft[index], result.x_ft[index]])
            line.set_visible(True)
            label.set_text(value)
        self.figure_canvas.draw_idle()


def main() -> None:
    root = tk.Tk()
    BeamDesignerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
