#!/usr/bin/env python3
"""Create four supplementary calibration and decision-curve figures.

The script uses the already generated calibration-bin and DCA result tables. It
does not refit models, regenerate patient-level predictions, recalibrate models,
or select configurations based on the appearance of the resulting curves.

The default outputs are four task-specific figures for survival,
clinical-efficacy, polymyxin-resistance, and MIMIC-IV CRAB analyses. Editable
SVG, PDF, and high-resolution PNG previews are exported. A combined 2 x 2
version remains available as an optional output.
"""

import argparse
import os
from collections import OrderedDict
from pathlib import Path
from string import ascii_lowercase


SCRIPT_DIR = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(SCRIPT_DIR / ".mplconfig"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FormatStrFormatter
import numpy as np
import pandas as pd


# Editable text in SVG/PDF is mandatory for manuscript figures.
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
FONT_SCALE = 1.25


def fs(value):
    """Scale all text consistently without enlarging the output canvas."""
    return value * FONT_SCALE


plt.rcParams["font.size"] = fs(8.5)
plt.rcParams["axes.linewidth"] = 1.0
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["legend.frameon"] = False
plt.rcParams["xtick.major.width"] = 1.0
plt.rcParams["ytick.major.width"] = 1.0
plt.rcParams["xtick.major.size"] = 3.5
plt.rcParams["ytick.major.size"] = 3.5
plt.rcParams["savefig.facecolor"] = "white"


MODEL_ORDER = OrderedDict(
    [
        ("RandomForest", "Random forest"),
        ("SVM", "Support vector machine"),
    ]
)

FEATURE_COLORS = {
    "FFM": "#6F6F6F",
    "Set A": "#0F4D92",
    "Set B": "#E28E2C",
    "Set C": "#42949E",
    "Set D": "#9A4D8E",
    "Set E": "#B64342",
}

FEATURE_LINESTYLES = {
    "FFM": (0, (5, 2)),
    "Set A": "-",
    "Set B": (0, (3, 1.5)),
    "Set C": (0, (5, 1.5, 1, 1.5)),
    "Set D": (0, (1, 1.5)),
    "Set E": (0, (7, 1.5, 2, 1.5)),
}

FEATURE_MARKERS = {
    "FFM": "o",
    "Set A": "s",
    "Set B": "^",
    "Set C": "D",
    "Set D": "v",
    "Set E": "P",
}

REFERENCE_COLORS = {
    "ideal": "#272727",
    "all": "#8C8C8C",
    "none": "#272727",
}


FIGURE_SPECS = OrderedDict(
    [
        (
            1,
            {
                "output_name": "Supplementary_Figure_1_survival_calibration_DCA",
                "task": "Survival",
                "cohorts": OrderedDict(
                    [
                        ("Development_OOF", "Development cohort"),
                        ("External_1", "Temporal validation cohort"),
                    ]
                ),
                "feature_sets": OrderedDict(
                    [
                        ("FullFeature", "FFM"),
                        ("cand_16", "Set A"),
                        ("cand_37", "Set B"),
                    ]
                ),
                "calibration_xlabel": "Predicted mortality risk",
                "calibration_ylabel": "Observed mortality rate",
            },
        ),
        (
            2,
            {
                "output_name": "Supplementary_Figure_2_clinical_efficacy_calibration_DCA",
                "task": "Clinical efficacy",
                "cohorts": OrderedDict(
                    [
                        ("Development_OOF", "Development cohort"),
                        ("External_1", "Temporal validation cohort"),
                    ]
                ),
                "feature_sets": OrderedDict(
                    [
                        ("FullFeature", "FFM"),
                        ("cand_21", "Set A"),
                        ("cand_38", "Set B"),
                        ("cand_39", "Set C"),
                        ("cand_40", "Set D"),
                    ]
                ),
                "calibration_xlabel": "Predicted probability of clinical improvement",
                "calibration_ylabel": "Observed clinical-improvement rate",
            },
        ),
        (
            3,
            {
                "output_name": "Supplementary_Figure_3_polymyxin_resistance_calibration_DCA",
                "task": "Polymyxin resistance",
                "cohorts": OrderedDict(
                    [
                        ("Development_OOF", "Development cohort"),
                        ("External_1", "Temporal validation cohort"),
                    ]
                ),
                "feature_sets": OrderedDict(
                    [
                        ("FullFeature", "FFM"),
                        ("cand_04", "Set A"),
                        ("cand_05", "Set B"),
                        ("cand_11", "Set C"),
                        ("cand_27", "Set D"),
                        ("cand_40", "Set E"),
                    ]
                ),
                "calibration_xlabel": "Predicted probability of polymyxin resistance",
                "calibration_ylabel": "Observed resistance rate",
            },
        ),
        (
            4,
            {
                "output_name": "Supplementary_Figure_4_MIMIC_CRAB_calibration_DCA",
                "task": "Survival",
                "cohorts": OrderedDict(
                    [("MIMIC_CRAB_LOOCV", "MIMIC-IV CRAB cohort")]
                ),
                "feature_sets": OrderedDict(
                    [
                        ("feature-setA", "Set A"),
                        ("feature-setB", "Set B"),
                    ]
                ),
                "calibration_xlabel": "Predicted mortality risk",
                "calibration_ylabel": "Observed mortality rate",
            },
        ),
    ]
)

COMPOSITE_PANEL_TITLES = {
    1: "Survival prediction",
    2: "Clinical-efficacy prediction",
    3: "Polymyxin-resistance prediction",
    4: "MIMIC-IV CRAB survival prediction",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Draw Supplementary Figures 1-4 from existing calibration and DCA tables."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=SCRIPT_DIR.parent / "results",
        help="Directory containing calibration/ and dca/ result tables.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SCRIPT_DIR / "output",
        help="Directory for final figures and the source manifest.",
    )
    parser.add_argument(
        "--figures",
        type=int,
        nargs="+",
        choices=tuple(FIGURE_SPECS),
        default=list(FIGURE_SPECS),
        help="Task-specific figures to draw (default: 1 2 3 4).",
    )
    parser.add_argument(
        "--composite",
        action="store_true",
        help="Also export the optional 2 x 2 combined figure.",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=("svg", "pdf", "png", "tiff"),
        default=("svg", "pdf", "png"),
        help="Output formats. SVG keeps manuscript text editable.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=600,
        help="Resolution for raster outputs (PNG/TIFF).",
    )
    return parser.parse_args()


def load_source_tables(results_dir):
    calibration_path = results_dir / "calibration" / "calibration_bins_all_configs.csv"
    dca_path = results_dir / "dca" / "dca_results_all_configs.csv"
    missing = [path for path in (calibration_path, dca_path) if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing source table(s): " + ", ".join(str(path) for path in missing)
        )
    calibration = pd.read_csv(calibration_path)
    dca = pd.read_csv(dca_path)
    return calibration, dca


def _select(
    data,
    task,
    cohort,
    feature_set,
    model,
):
    return data.loc[
        (data["task"] == task)
        & (data["cohort"] == cohort)
        & (data["feature_set"] == feature_set)
        & (data["model"] == model)
    ].copy()


def validate_figure_sources(
    calibration,
    dca,
    spec,
):
    errors = []
    for cohort in spec["cohorts"]:
        for feature_set in spec["feature_sets"]:
            for model in MODEL_ORDER:
                calibration_rows = _select(
                    calibration, spec["task"], cohort, feature_set, model
                )
                dca_rows = _select(dca, spec["task"], cohort, feature_set, model)
                key = f"{spec['task']} | {cohort} | {feature_set} | {model}"
                if calibration_rows.empty:
                    errors.append(f"No calibration rows for {key}")
                if dca_rows.empty:
                    errors.append(f"No DCA rows for {key}")
                else:
                    thresholds = np.sort(dca_rows["threshold"].unique())
                    expected = np.round(np.arange(0.01, 1.00, 0.01), 2)
                    if len(thresholds) != 99 or not np.allclose(thresholds, expected):
                        errors.append(
                            f"Unexpected DCA thresholds for {key}: expected 0.01-0.99 by 0.01"
                        )
    if errors:
        raise ValueError("Source validation failed:\n- " + "\n- ".join(errors))


def add_panel_label(ax, label):
    ax.text(
        -0.18,
        1.08,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=fs(10),
        fontweight="bold",
    )


def style_axis(ax):
    ax.grid(True, color="#D9D9D9", linewidth=0.45, alpha=0.55)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=fs(7.5))


def plot_calibration_panel(
    ax,
    calibration,
    spec,
    cohort,
    model,
):
    ax.plot(
        [0, 1],
        [0, 1],
        color=REFERENCE_COLORS["ideal"],
        linestyle=(0, (4, 2)),
        linewidth=1.35,
        zorder=1,
    )
    for feature_set, display_label in spec["feature_sets"].items():
        rows = _select(calibration, spec["task"], cohort, feature_set, model).sort_values(
            "mean_predicted_probability"
        )
        ax.plot(
            rows["mean_predicted_probability"],
            rows["observed_event_rate"],
            color=FEATURE_COLORS[display_label],
            linestyle=FEATURE_LINESTYLES[display_label],
            linewidth=1.65,
            marker=FEATURE_MARKERS[display_label],
            markersize=3.8,
            markeredgewidth=0.45,
            markeredgecolor="white",
            zorder=2,
        )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks(np.arange(0, 1.01, 0.2))
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    ax.set_xlabel(spec["calibration_xlabel"], fontsize=fs(8))
    ax.set_ylabel(spec["calibration_ylabel"], fontsize=fs(8))
    style_axis(ax)


def dca_display_limits(
    dca,
    spec,
    cohort,
):
    selected = dca.loc[
        (dca["task"] == spec["task"])
        & (dca["cohort"] == cohort)
        & dca["feature_set"].isin(spec["feature_sets"])
        & dca["model"].isin(MODEL_ORDER)
    ]
    values = selected["net_benefit_model"].to_numpy(dtype=float)
    if not np.isfinite(values).all() or values.size == 0:
        raise ValueError(f"Invalid or empty DCA values for {spec['task']} | {cohort}")
    low = min(0.0, float(values.min()))
    high = max(0.0, float(values.max()))
    span = max(high - low, 0.05)
    padding = span * 0.07
    return low - padding, high + padding


def plot_dca_panel(
    ax,
    dca,
    spec,
    cohort,
    model,
    y_limits,
):
    first_feature_set = next(iter(spec["feature_sets"]))
    reference = _select(dca, spec["task"], cohort, first_feature_set, model).sort_values(
        "threshold"
    )
    ax.plot(
        reference["threshold"],
        reference["net_benefit_all"],
        color=REFERENCE_COLORS["all"],
        linestyle=(0, (4, 2)),
        linewidth=1.25,
        zorder=1,
        clip_on=True,
    )
    ax.plot(
        reference["threshold"],
        reference["net_benefit_none"],
        color=REFERENCE_COLORS["none"],
        linestyle=(0, (1, 2)),
        linewidth=1.25,
        zorder=1,
    )
    for feature_set, display_label in spec["feature_sets"].items():
        rows = _select(dca, spec["task"], cohort, feature_set, model).sort_values(
            "threshold"
        )
        ax.plot(
            rows["threshold"],
            rows["net_benefit_model"],
            color=FEATURE_COLORS[display_label],
            linestyle=FEATURE_LINESTYLES[display_label],
            linewidth=1.65,
            zorder=2,
        )
    ax.set_xlim(0.01, 0.99)
    ax.set_ylim(*y_limits)
    ax.set_xticks([0.01, 0.20, 0.40, 0.60, 0.80, 0.99])
    ax.set_xticklabels(["0.01", "0.20", "0.40", "0.60", "0.80", "0.99"])
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    ax.set_xlabel("Threshold probability", fontsize=fs(8))
    ax.set_ylabel("Net benefit", fontsize=fs(8))
    style_axis(ax)


def make_legend_handles(spec):
    handles = [
        Line2D(
            [0],
            [0],
            color=FEATURE_COLORS[label],
            linestyle=FEATURE_LINESTYLES[label],
            marker=FEATURE_MARKERS[label],
            markersize=4.4,
            linewidth=1.65,
            label=label,
        )
        for label in spec["feature_sets"].values()
    ]
    handles.extend(
        [
            Line2D(
                [0],
                [0],
                color=REFERENCE_COLORS["ideal"],
                linestyle=(0, (4, 2)),
                linewidth=1.25,
                label="Ideal calibration",
            ),
            Line2D(
                [0],
                [0],
                color=REFERENCE_COLORS["all"],
                linestyle=(0, (4, 2)),
                linewidth=1.25,
                label="Treat all",
            ),
            Line2D(
                [0],
                [0],
                color=REFERENCE_COLORS["none"],
                linestyle=(0, (1, 2)),
                linewidth=1.25,
                label="Treat none",
            ),
        ]
    )
    return handles


def draw_main_figure(
    calibration,
    dca,
    spec,
):
    fig, axes = plt.subplots(2, 4, figsize=(13.0, 6.25), squeeze=False)
    panel_index = 0
    cohorts = list(spec["cohorts"].items())
    for row, (model, model_display) in enumerate(MODEL_ORDER.items()):
        for cohort_index, (cohort, cohort_display) in enumerate(cohorts):
            cal_col = cohort_index * 2
            dca_col = cal_col + 1
            cal_ax = axes[row, cal_col]
            dca_ax = axes[row, dca_col]
            plot_calibration_panel(cal_ax, calibration, spec, cohort, model)
            limits = dca_display_limits(dca, spec, cohort)
            plot_dca_panel(dca_ax, dca, spec, cohort, model, limits)
            add_panel_label(cal_ax, ascii_lowercase[panel_index])
            panel_index += 1
            add_panel_label(dca_ax, ascii_lowercase[panel_index])
            panel_index += 1
            if row == 0:
                cal_ax.set_title(f"{cohort_display}\nCalibration", fontsize=fs(9), pad=7)
                dca_ax.set_title(f"{cohort_display}\nDecision curve", fontsize=fs(9), pad=7)
        axes[row, 0].annotate(
            model_display,
            xy=(-0.35, 0.5),
            xycoords="axes fraction",
            rotation=90,
            ha="center",
            va="center",
            fontsize=fs(9),
            fontweight="bold",
        )

    handles = make_legend_handles(spec)
    fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.53, 0.985),
        ncol=min(len(handles), 9),
        columnspacing=1.3,
        handlelength=2.6,
        fontsize=fs(7.5),
    )
    fig.subplots_adjust(
        left=0.075,
        right=0.995,
        bottom=0.09,
        top=0.84,
        wspace=0.34,
        hspace=0.42,
    )
    return fig


def draw_crab_figure(
    calibration,
    dca,
    spec,
):
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.2), squeeze=False)
    cohort, cohort_display = next(iter(spec["cohorts"].items()))
    limits = dca_display_limits(dca, spec, cohort)
    panel_index = 0
    for row, (model, model_display) in enumerate(MODEL_ORDER.items()):
        cal_ax, dca_ax = axes[row]
        plot_calibration_panel(cal_ax, calibration, spec, cohort, model)
        plot_dca_panel(dca_ax, dca, spec, cohort, model, limits)
        add_panel_label(cal_ax, ascii_lowercase[panel_index])
        panel_index += 1
        add_panel_label(dca_ax, ascii_lowercase[panel_index])
        panel_index += 1
        if row == 0:
            cal_ax.set_title(f"{cohort_display}\nCalibration", fontsize=fs(9), pad=7)
            dca_ax.set_title(f"{cohort_display}\nDecision curve", fontsize=fs(9), pad=7)
        cal_ax.annotate(
            model_display,
            xy=(-0.31, 0.5),
            xycoords="axes fraction",
            rotation=90,
            ha="center",
            va="center",
            fontsize=fs(9),
            fontweight="bold",
        )

    handles = make_legend_handles(spec)
    fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.54, 0.985),
        ncol=len(handles),
        columnspacing=1.25,
        handlelength=2.6,
        fontsize=fs(7.5),
    )
    fig.subplots_adjust(
        left=0.13,
        right=0.99,
        bottom=0.09,
        top=0.84,
        wspace=0.33,
        hspace=0.42,
    )
    return fig


def populate_main_composite_panel(
    subfigure,
    calibration,
    dca,
    spec,
    panel_label,
    panel_title,
):
    """Populate one main composite panel with the original 2 x 4 task grid."""
    axes = subfigure.subplots(2, 4, squeeze=False)
    cohorts = list(spec["cohorts"].items())
    for row, (model, model_display) in enumerate(MODEL_ORDER.items()):
        for cohort_index, (cohort, cohort_display) in enumerate(cohorts):
            cal_col = cohort_index * 2
            dca_col = cal_col + 1
            cal_ax = axes[row, cal_col]
            dca_ax = axes[row, dca_col]
            plot_calibration_panel(cal_ax, calibration, spec, cohort, model)
            limits = dca_display_limits(dca, spec, cohort)
            plot_dca_panel(dca_ax, dca, spec, cohort, model, limits)
            if row == 0:
                cal_ax.set_title(f"{cohort_display}\nCalibration", fontsize=fs(8.2), pad=5)
                dca_ax.set_title(f"{cohort_display}\nDecision curve", fontsize=fs(8.2), pad=5)
        axes[row, 0].annotate(
            model_display,
            xy=(-0.38, 0.5),
            xycoords="axes fraction",
            rotation=90,
            ha="center",
            va="center",
            fontsize=fs(8.2),
            fontweight="bold",
        )

    subfigure.suptitle(
        f"{panel_label}   {panel_title}",
        x=0.006,
        y=0.995,
        ha="left",
        va="top",
        fontsize=fs(12),
        fontweight="bold",
    )
    handles = make_legend_handles(spec)
    subfigure.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.57, 0.993),
        ncol=min(len(handles), 9),
        columnspacing=0.95,
        handlelength=2.2,
        fontsize=fs(6.7),
    )
    subfigure.subplots_adjust(
        left=0.09,
        right=0.995,
        bottom=0.09,
        top=0.82,
        wspace=0.38,
        hspace=0.45,
    )


def populate_crab_composite_panel(
    subfigure,
    calibration,
    dca,
    spec,
    panel_label,
    panel_title,
):
    """Populate the CRAB composite panel with the original 2 x 2 task grid."""
    axes = subfigure.subplots(2, 2, squeeze=False)
    cohort, _ = next(iter(spec["cohorts"].items()))
    limits = dca_display_limits(dca, spec, cohort)
    for row, (model, model_display) in enumerate(MODEL_ORDER.items()):
        cal_ax, dca_ax = axes[row]
        plot_calibration_panel(cal_ax, calibration, spec, cohort, model)
        plot_dca_panel(dca_ax, dca, spec, cohort, model, limits)
        if row == 0:
            cal_ax.set_title("Calibration", fontsize=fs(8.2), pad=5)
            dca_ax.set_title("Decision curve", fontsize=fs(8.2), pad=5)
        cal_ax.annotate(
            model_display,
            xy=(-0.29, 0.5),
            xycoords="axes fraction",
            rotation=90,
            ha="center",
            va="center",
            fontsize=fs(8.2),
            fontweight="bold",
        )

    subfigure.suptitle(
        f"{panel_label}   {panel_title}",
        x=0.006,
        y=0.995,
        ha="left",
        va="top",
        fontsize=fs(12),
        fontweight="bold",
    )
    handles = make_legend_handles(spec)
    subfigure.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.58, 0.993),
        ncol=len(handles),
        columnspacing=1.05,
        handlelength=2.3,
        fontsize=fs(7.0),
    )
    subfigure.subplots_adjust(
        left=0.12,
        right=0.985,
        bottom=0.09,
        top=0.82,
        wspace=0.31,
        hspace=0.45,
    )


def draw_composite_figure(
    calibration,
    dca,
):
    """Draw all four task figures as top-level panels a-d in one canvas."""
    figure = plt.figure(figsize=(24.0, 16.5), facecolor="white")
    subfigures = figure.subfigures(2, 2, wspace=0.025, hspace=0.045)
    for figure_number, subfigure, panel_label in zip(
        FIGURE_SPECS,
        subfigures.flat,
        ascii_lowercase,
    ):
        spec = FIGURE_SPECS[figure_number]
        if figure_number == 4:
            populate_crab_composite_panel(
                subfigure,
                calibration,
                dca,
                spec,
                panel_label,
                COMPOSITE_PANEL_TITLES[figure_number],
            )
        else:
            populate_main_composite_panel(
                subfigure,
                calibration,
                dca,
                spec,
                panel_label,
                COMPOSITE_PANEL_TITLES[figure_number],
            )
    return figure


def save_figure(
    fig,
    output_base,
    formats,
    dpi,
):
    output_base.parent.mkdir(parents=True, exist_ok=True)
    saved = []
    for output_format in formats:
        path = output_base.with_suffix(f".{output_format}")
        save_kwargs = {"bbox_inches": "tight", "facecolor": "white"}
        if output_format in {"png", "tiff"}:
            save_kwargs["dpi"] = dpi
        fig.savefig(path, **save_kwargs)
        saved.append(path)
    plt.close(fig)
    return saved


def make_source_manifest(figure_numbers, output_dir):
    rows = []
    for figure_number in figure_numbers:
        spec = FIGURE_SPECS[figure_number]
        for model in MODEL_ORDER:
            for cohort in spec["cohorts"]:
                for analysis_type in ("calibration", "DCA"):
                    rows.append(
                        {
                            "supplementary_figure": figure_number,
                            "composite_panel": ascii_lowercase[figure_number - 1],
                            "task": spec["task"],
                            "cohort": cohort,
                            "model": model,
                            "analysis": analysis_type,
                            "feature_set_filters": ";".join(spec["feature_sets"].keys()),
                            "display_labels": ";".join(spec["feature_sets"].values()),
                            "source_table": (
                                "calibration/calibration_bins_all_configs.csv"
                                if analysis_type == "calibration"
                                else "dca/dca_results_all_configs.csv"
                            ),
                        }
                    )
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "supplementary_figure_source_manifest.csv"
    pd.DataFrame(rows).to_csv(manifest_path, index=False)
    return manifest_path


def main():
    args = parse_args()
    calibration, dca = load_source_tables(args.results_dir.resolve())
    output_dir = args.output_dir.resolve()
    generated = []

    for figure_number in args.figures:
        spec = FIGURE_SPECS[figure_number]
        validate_figure_sources(calibration, dca, spec)
        if figure_number == 4:
            figure = draw_crab_figure(calibration, dca, spec)
        else:
            figure = draw_main_figure(calibration, dca, spec)
        generated.extend(
            save_figure(
                figure,
                output_dir / spec["output_name"],
                args.formats,
                args.dpi,
            )
        )

    if args.composite:
        for spec in FIGURE_SPECS.values():
            validate_figure_sources(calibration, dca, spec)
        composite = draw_composite_figure(calibration, dca)
        generated.extend(
            save_figure(
                composite,
                output_dir / "Supplementary_Figure_calibration_DCA_combined",
                args.formats,
                args.dpi,
            )
        )

    manifest_figures = list(FIGURE_SPECS) if args.composite else args.figures
    manifest_path = make_source_manifest(manifest_figures, output_dir)
    print("Generated files:")
    for path in generated:
        print(f"  {path}")
    print(f"  {manifest_path}")


if __name__ == "__main__":
    main()
