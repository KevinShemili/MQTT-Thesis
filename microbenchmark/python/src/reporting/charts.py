import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from .benchmark import BenchmarkSummaryData

# Shared colors used across benchmark reports so the same kinds of series remain visually consistent
AMBER = "#d97706"
VIOLET = "#7c3aed"
TEAL = "#0f766e"
CRIMSON = "#c2415d"
BLUE = "#2563eb"

FIGURE_DPI = 150
PANEL_FIGURE_SIZE = (13, 5)


# Draws one summary
def draw_summary(
    axis: Axes,
    summary: BenchmarkSummaryData,
    label: str,
    color: str,
    **overrides,
) -> None:
    axis.errorbar(
        summary.sweep_values,
        summary.means,
        yerr=summary.ci_halfs,
        label=label,
        color=color,
        **(
            {
                "marker": "o",
                "linewidth": 1.8,
                "markersize": 5,
                "capsize": 4,
            }
            | overrides
        ),
    )


# Same as draw_summary() but without CIs
def draw_summary_no_ci(
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
        **(
            {
                "marker": "o",
                "linewidth": 1.8,
                "markersize": 5,
            }
            | overrides
        ),
    )


# Adds horizontal grid lines to allow better interpretability of the vertical axis
# linewidth controls how thick those grid lines are.
def apply_value_grid(axis: Axes, linewidth: float = 0.5) -> None:
    axis.grid(True, axis="y", linestyle="-", linewidth=linewidth, alpha=0.18)


# Adds a grid in both directions
def apply_mesh_grid(axis: Axes) -> None:
    axis.grid(
        True,
        which="both",
        color="#ded9d2",
        linestyle="--",
        linewidth=0.5,
        alpha=0.7,
    )


# Marks the crossover point of two lines on a plot with an X marker and a label
def mark_crossover(axis: Axes, x_value: float, y_value: float, label: str) -> None:
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


# Persists created image
def save_figure(figure: Figure, output_path: str) -> None:
    figure.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved -> {output_path}")
