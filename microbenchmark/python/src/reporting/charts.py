import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .benchmark import Series

AMBER = "#d97706"
VIOLET = "#7c3aed"
TEAL = "#0f766e"
CRIMSON = "#c2415d"
BLUE = "#2563eb"

ERROR_SERIES_STYLE = {
    "marker": "o",
    "linewidth": 1.8,
    "markersize": 5,
    "capsize": 4,
}
LINE_SERIES_STYLE = {
    "marker": "o",
    "linewidth": 1.8,
    "markersize": 5,
}

FIGURE_DPI = 150
PANEL_FIGURE_SIZE = (13, 5)


def draw_error_series(
    axis: Axes,
    series: Series,
    label: str,
    color: str,
    **overrides,
) -> None:
    axis.errorbar(
        series.x,
        series.means,
        yerr=series.ci_halfs,
        label=label,
        color=color,
        **(ERROR_SERIES_STYLE | overrides),
    )


def draw_line_series(
    axis: Axes,
    x_values: list[float],
    y_values: list[float],
    label: str,
    color: str,
    **overrides,
) -> None:
    axis.plot(
        x_values,
        y_values,
        label=label,
        color=color,
        **(LINE_SERIES_STYLE | overrides),
    )


def apply_value_grid(axis: Axes, linewidth: float = 0.5) -> None:
    axis.grid(True, axis="y", linestyle="-", linewidth=linewidth, alpha=0.18)


def apply_mesh_grid(axis: Axes) -> None:
    axis.grid(
        True,
        which="both",
        color="#ded9d2",
        linestyle="--",
        linewidth=0.5,
        alpha=0.7,
    )


def annotate_crossover(axis: Axes, x_value: float, y_value: float, label: str) -> None:
    axis.plot(
        [x_value],
        [y_value],
        marker="X",
        color="black",
        markersize=9,
        linestyle="none",
        zorder=5,
    )
    axis.annotate(
        label,
        (x_value, y_value),
        textcoords="offset points",
        xytext=(6, 8),
        fontsize=9,
        fontweight="bold",
    )


def save_figure(figure: Figure, output_path: str) -> None:
    figure.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved -> {output_path}")
