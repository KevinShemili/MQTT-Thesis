import matplotlib
import matplotlib.pyplot as plt
import formatting

matplotlib.use("Agg")

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from math import isnan

FIGURE_DPI = 150
PANEL_FIGURE_SIZE = (13, 5)

# Leaves a little space between the last data point and the right edge of an axis
AXIS_HEADROOM = 1.03


# Draws a sweep as its mean at every point. Error bars are opt-in because a size fixed
# by construction, such as a ciphertext length, has no meaningful spread to present.
def draw_summary(
    axis: Axes,
    sweep_values: list[int],
    means: list[float],
    confidence_intervals: list[float],
    label: str,
    color: str,
    with_ci: bool = False,
    **overrides,
) -> None:
    axis.errorbar(
        sweep_values,
        means,
        yerr=confidence_intervals if with_ci else None,
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


# A measurement that does not depend on the swept variable, drawn as the flat line it is.
# Spans the whole sweep rather than carrying a point at every value, since it was measured
# once and repeating it at each tick would read as a sweep that had been performed
def draw_constant(
    axis: Axes,
    value: float,
    sweep_values: list[int],
    label: str,
    color: str,
) -> None:

    axis.hlines(
        value,
        sweep_values[0],
        sweep_values[-1],
        color=color,
        linestyle="--",
        linewidth=1.8,
        label=label,
    )


# Draws a sweep as a distribution rather than as a mean, for a measurement whose
# samples are skewed and where the tail is the point, ex. RSA key generation.
# The median is the line, the box spans the IQR and the thin whiskers reach the
# smallest and largest sample observed
def draw_distribution(
    axis: Axes,
    sweep_values: list[int],
    medians: list[float],
    minimums: list[float],
    maximums: list[float],
    first_quartiles: list[float],
    third_quartiles: list[float],
    label: str,
    color: str,
) -> None:
    axis.vlines(
        sweep_values,
        minimums,
        maximums,
        color=color,
        linewidth=0.9,
        alpha=0.55,
    )

    axis.errorbar(
        sweep_values,
        medians,
        yerr=[
            [
                median_value - lower
                for median_value, lower in zip(medians, first_quartiles)
            ],
            [
                upper - median_value
                for median_value, upper in zip(medians, third_quartiles)
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
            "0" if tick == 0 else formatting.format_byte_size(tick, compact=True)
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


# Finds the highest visible mean plus CI without introducing a plot-data object.
def calculate_axis_top(means: list[float], confidence_intervals: list[float]) -> float:
    return max(
        (
            mean_value + ci_half
            for mean_value, ci_half in zip(means, confidence_intervals)
            if not isnan(mean_value)
        ),
        default=0.0,
    )


# Persists created image
def save_figure(figure: Figure, output_path: str) -> None:
    figure.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved -> {output_path}")
