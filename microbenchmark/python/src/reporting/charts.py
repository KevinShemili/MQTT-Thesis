import matplotlib
from math import isnan
from typing import Callable, Iterable

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from .benchmark import BenchmarkSummary, FeatureSweep
from .formatting import format_byte_size

# Shared colors used across benchmark reports so the same kinds of series remain visually consistent
AMBER = "#d97706"
VIOLET = "#7c3aed"
TEAL = "#0f766e"
CRIMSON = "#c2415d"
BLUE = "#2563eb"

FIGURE_DPI = 150
PANEL_FIGURE_SIZE = (13, 5)

# Leaves a little space between the last data point and the right edge of an axis
AXIS_HEADROOM = 1.03


# One named and coloured line of a figure, tied to the operation and the feature it is
# read from, ex. the ciphertext bytes reported by encrypt drawn in amber. Knowing where
# its own numbers come from lets a caller name a line once and draw it against any sweep
class Series:
    def __init__(
        self,
        operation: str,
        unit: str,
        label: str,
        color: str,
        divisor: float = 1.0,
    ) -> None:
        self.operation = operation
        self.unit = unit
        self.label = label
        self.color = color
        self.divisor = divisor

    def sweep(
        self,
        results: BenchmarkSummary,
        group: str,
        sweep_values: list[int],
    ) -> FeatureSweep:

        return results.sweep_features(
            self.operation,
            group,
            sweep_values,
            self.unit,
            self.divisor,
        )

    def draw(
        self,
        axis: Axes,
        results: BenchmarkSummary,
        group: str,
        sweep_values: list[int],
        with_ci: bool = False,
    ) -> None:

        draw_summary(
            axis,
            self.sweep(results, group, sweep_values),
            self.label,
            self.color,
            with_ci=with_ci,
        )


# Draws a sweep as its mean at every point. Error bars are opt-in because a sweep
# always carries its CI, while a size that is fixed by construction ex. a ciphertext
# length has nothing to show for it
def draw_summary(
    axis: Axes,
    summary: FeatureSweep,
    label: str,
    color: str,
    with_ci: bool = False,
    **overrides,
) -> None:
    axis.errorbar(
        summary.sweep_values,
        summary.means,
        yerr=summary.ci if with_ci else None,
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


# Draws a sweep as a distribution rather than as a mean, for a measurement whose
# samples are skewed and where the tail is the point, ex. RSA key generation.
# The median is the line, the box spans the IQR and the thin whiskers reach the
# smallest and largest sample observed
def draw_distribution(
    axis: Axes,
    summary: FeatureSweep,
    label: str,
    color: str,
) -> None:

    medians = summary.medians

    axis.vlines(
        summary.sweep_values,
        summary.minimums,
        summary.maximums,
        color=color,
        linewidth=0.9,
        alpha=0.55,
    )

    axis.errorbar(
        summary.sweep_values,
        medians,
        yerr=[
            [
                median_value - lower
                for median_value, lower in zip(medians, summary.first_quartiles)
            ],
            [
                upper - median_value
                for median_value, upper in zip(medians, summary.third_quartiles)
            ],
        ],
        label=label,
        color=color,
        marker="o",
        linewidth=1.8,
        markersize=5,
        capsize=6,
        elinewidth=4.5,
    )


# Adds horizontal grid lines to allow better interpretability of the vertical axis
# linewidth controls how thick those grid lines are.
def apply_value_grid(axis: Axes, linewidth: float = 0.5) -> None:
    axis.grid(True, axis="y", linestyle="-", linewidth=linewidth, alpha=0.18)


# Configures a horizontal axis that measures payload sizes, labelling the ticks
# in compact byte units ex. "16KB" rather than raw byte counts
def configure_byte_axis(axis: Axes, max_byte_size: int, tick_step: int) -> None:

    tick_values = list(range(0, max_byte_size + tick_step, tick_step))

    axis.set_xticks(tick_values)
    axis.set_xticklabels(
        [
            "0" if tick == 0 else format_byte_size(tick, compact=True)
            for tick in tick_values
        ]
    )
    axis.set_xlim(0, max_byte_size * AXIS_HEADROOM)

    apply_value_grid(axis)


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
    collect: Callable[[str, str], FeatureSweep],
    title: str,
    x_label: str,
    y_label: str,
    colors: dict[str, str],
    configure_axis: Callable[[Axes], None],
    output_path: str,
    labels: dict[str, str] | None = None,
    legend_kwargs: dict | None = None,
    with_ci: bool = True,
    on_panel: Callable[[Axes, str, list[tuple[str, FeatureSweep]]], None] | None = None,
) -> None:

    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)

    for axis, operation in zip(axes, operations):

        drawn: list[tuple[str, FeatureSweep]] = []

        for name in names:
            series = collect(operation, name)
            label = name if labels is None else labels.get(name, name)
            draw_summary(axis, series, label, colors[name], with_ci=with_ci)
            drawn.append((name, series))

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel(x_label)
        axis.set_ylabel(y_label)

        axis.set_ylim(bottom=0)

        configure_axis(axis)
        axis.legend(**(legend_kwargs or {"fontsize": 10}))

        if on_panel is not None:
            on_panel(axis, operation, drawn)

    figure.tight_layout()
    save_figure(figure, output_path)


# Finds the highest visible value across the series, including the top of each confidence interval.
# Used to choose a Y-axis limit that does not cut off any error bars.
# A sweep value whose case never produced a measurement reads as NaN and is skipped,
# since a gap in a line has no height to leave room for
def calculate_axis_top(series_list: Iterable[FeatureSweep]) -> float:

    return max(
        (
            mean_value + ci_half
            for series in series_list
            for mean_value, ci_half in zip(series.means, series.ci)
            if not isnan(mean_value)
        ),
        default=0.0,
    )


# Persists created image
def save_figure(figure: Figure, output_path: str) -> None:
    figure.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved -> {output_path}")
