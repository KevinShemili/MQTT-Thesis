import matplotlib
from typing import Callable, Iterable
from .benchmark import BenchmarkSummaryData

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


# Helper that creates a two-panel figure, where each panel represents one operation
# ex. "serialize" and "deserialize", and each panel draws the same set of named series
# ex. JSON, CBOR, and CBOR (int keys)
def draw_two_panel_figure(
    operations: list[str],
    names: list[str],
    collect: Callable[[str, str], BenchmarkSummaryData],
    *,
    title: str,
    x_label: str,
    y_label: str,
    color_for: Callable[[str], str],
    configure_axis: Callable[[Axes], None],
    output_path: str,
    label_for: Callable[[str], str] | None = None,
    legend_kwargs: dict | None = None,
    on_panel: (
        Callable[[Axes, str, list[tuple[str, BenchmarkSummaryData]]], None] | None
    ) = None,
) -> None:

    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)

    for axis, operation in zip(axes, operations):

        drawn: list[tuple[str, BenchmarkSummaryData]] = []

        for name in names:
            series = collect(operation, name)
            label = label_for(name) if label_for is not None else name
            draw_summary(axis, series, label, color_for(name))
            drawn.append((name, series))

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel(x_label)
        axis.set_ylabel(y_label)

        axis.set_ylim(bottom=0)

        configure_axis(axis)
        axis.legend(
            **(legend_kwargs if legend_kwargs is not None else {"fontsize": 10})
        )

        if on_panel is not None:
            on_panel(axis, operation, drawn)

    figure.tight_layout()
    save_figure(figure, output_path)


# Finds the highest visible value across the series, including the top of each confidence interval.
# Used to choose a Y-axis limit that does not cut off any error bars
def calculate_y_axis_overhead(series_list: Iterable[BenchmarkSummaryData]) -> float:

    return max(
        (
            mean_value + ci_half
            for series in series_list
            for mean_value, ci_half in zip(series.means, series.ci_halfs)
        ),
        default=0.0,
    )


# Persists created image
def save_figure(figure: Figure, output_path: str) -> None:
    figure.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved -> {output_path}")
