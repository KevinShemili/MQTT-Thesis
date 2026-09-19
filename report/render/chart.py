import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from report.render import formatting

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import (
    FixedLocator,
    FuncFormatter,
    LogLocator,
    NullFormatter,
)
from math import ceil, floor, isclose, isnan, log10
from typing import Any, Callable

from .color import *
from .formatting import MEGABYTE

FIGURE_DPI = 150
PANEL_FIGURE_SIZE = (13, 5)

# Leaves a little space between the last data point and the right edge of an axis
AXIS_HEADROOM = 1.03
CROSSOVER_FIGURE_SIZE = (8.5, 5.2)
TOTAL_CIPHERTEXT_COLOR = TEAL
PEAK_RSS_AXIS_PADDING = 0.08
PEAK_RSS_FALLBACK_PADDING = 0.01


def draw_summary(
    axis: Axes,
    parameter_values: list[int],
    means: list[float],
    confidence_intervals: list[float],
    label: str,
    color: str,
    with_ci: bool = False,
    **style: Any,
) -> None:
    options = {
        "linewidth": 1.8,
        "markersize": 5,
        "capsize": 4,
        "marker": "o",
        **style,
    }
    axis.errorbar(
        parameter_values,
        means,
        yerr=confidence_intervals if with_ci else None,
        label=label,
        color=color,
        **options,
    )


def draw_constant(
    axis: Axes,
    value: float,
    parameter_values: list[int],
    label: str,
    color: str,
) -> None:
    axis.hlines(
        value,
        parameter_values[0],
        parameter_values[-1],
        color=color,
        linestyle="--",
        linewidth=1.8,
        label=label,
    )


def apply_value_grid(axis: Axes, linewidth: float = 0.5) -> None:
    axis.grid(True, axis="y", linestyle="-", linewidth=linewidth, alpha=0.18)


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


def apply_mesh_grid(axis: Axes) -> None:
    axis.grid(
        True,
        which="both",
        color="#ded9d2",
        linestyle="--",
        linewidth=0.5,
        alpha=0.7,
    )


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


def calculate_axis_top(means: list[float], confidence_intervals: list[float]) -> float:
    return max(
        (
            mean_value + ci_half
            for mean_value, ci_half in zip(means, confidence_intervals)
            if not isnan(mean_value)
        ),
        default=0.0,
    )


def _configure_peak_rss_axes(
    panels: list[
        tuple[
            Axes,
            list[int],
            list[tuple[str, list[float], list[float], str]],
        ]
    ],
    baseline_memory_mean: float,
) -> None:
    bounds = [baseline_memory_mean]

    for _, _, series in panels:
        for _, means, confidence_intervals, _ in series:
            for mean, confidence_interval in zip(means, confidence_intervals):
                if not isnan(mean) and not isnan(confidence_interval):
                    bounds.extend(
                        [mean - confidence_interval, mean + confidence_interval]
                    )

    lower_bound = min(bounds)
    upper_bound = max(bounds)
    value_range = upper_bound - lower_bound
    padding = value_range * PEAK_RSS_AXIS_PADDING

    if padding == 0:
        padding = (
            max(abs(lower_bound), abs(upper_bound), 1.0) * PEAK_RSS_FALLBACK_PADDING
        )

    for axis, _, _ in panels:
        axis.axhline(
            baseline_memory_mean,
            color=TEAL,
            linestyle="--",
            linewidth=1.8,
            label="Runtime baseline",
        )
        axis.set_yscale("linear")
        axis.set_ylim(lower_bound - padding, upper_bound + padding)


def save_figure(figure: Figure, output_path: str) -> None:
    figure.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved -> {output_path}")


def _draw_summaries(
    axis: Axes,
    parameter_values: list[int],
    series: list[tuple[str, list[float], list[float], str]],
    with_ci: bool = False,
) -> None:
    for label, means, confidence_intervals, color in series:
        draw_summary(
            axis,
            parameter_values,
            means,
            confidence_intervals,
            label,
            color,
            with_ci=with_ci,
        )


def _plot_operation_comparison(
    parameter_values: list[int],
    panels: list[tuple[str, list[tuple[str, list[float], list[float], str]]]],
    title: str,
    x_label: str,
    y_label: str,
    output_path: str,
    byte_tick_step: int | None = None,
    with_log2_payload_axis: bool = False,
    with_logarithmic_y_axis: bool = False,
    legend_location: str | None = None,
    baseline_memory_mean: float | None = None,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)
    rendered_panels = []

    for axis, (operation, series) in zip(axes, panels):
        _draw_summaries(axis, parameter_values, series, with_ci=True)
        axis.set_title(operation, fontsize=11)
        axis.set_xlabel(x_label)
        axis.set_ylabel(y_label)
        if not with_logarithmic_y_axis:
            axis.set_ylim(bottom=0)
        rendered_panels.append((axis, parameter_values, series))

        if with_log2_payload_axis:
            _configure_log2_payload_axis(axis, parameter_values)
        elif byte_tick_step is None:
            configure_attribute_axis(parameter_values, axis)
        else:
            configure_byte_axis(axis, parameter_values[-1], byte_tick_step)

        if with_logarithmic_y_axis:
            _configure_compact_logarithmic_y_axis(axis)

        legend_options = {"fontsize": 10}
        if legend_location is not None:
            legend_options["loc"] = legend_location
        axis.legend(**legend_options)

    if baseline_memory_mean is not None:
        _configure_peak_rss_axes(rendered_panels, baseline_memory_mean)
        for axis in axes:
            legend_options = {"fontsize": 10}
            if legend_location is not None:
                legend_options["loc"] = legend_location
            axis.legend(**legend_options)

    figure.tight_layout()
    save_figure(figure, output_path)


def _plot_prefixed_operation_comparison(
    parameter_values: list[int],
    scope: dict[str, Any],
    series: list[tuple[str, str, str]],
    operations: list[tuple[str, str]],
    title: str,
    x_label: str,
    y_label: str,
    output_path: str,
    **options: Any,
) -> None:
    panels = [
        (
            operation_label,
            [
                (
                    label,
                    scope[f"{prefix}_{operation}_means"],
                    scope[f"{prefix}_{operation}_cis"],
                    color,
                )
                for label, prefix, color in series
            ],
        )
        for operation_label, operation in operations
    ]
    _plot_operation_comparison(
        parameter_values, panels, title, x_label, y_label, output_path, **options
    )


def _plot_aes_ascon_results(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    title: str,
    y_label: str,
    output_path: str,
    with_logarithmic_y_axis: bool = False,
    baseline_memory_mean: float | None = None,
) -> None:
    panels = []

    for operation in ("Encrypt", "Decrypt"):
        series = []

        for algorithm, color in (("AES-GCM", AMBER), ("ASCON", VIOLET)):
            means, confidence_intervals = results[(algorithm, operation)]
            series.append((algorithm, means, confidence_intervals, color))

        panels.append((operation, series))

    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)
    rendered_panels = []

    for axis, (operation, series) in zip(axes, panels):
        _draw_summaries(axis, payload_sizes, series, with_ci=True)
        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Payload Size")
        axis.set_ylabel(y_label)
        if baseline_memory_mean is None and not with_logarithmic_y_axis:
            axis.set_ylim(bottom=0)

        _configure_log2_payload_axis(axis, payload_sizes)

        if with_logarithmic_y_axis:
            _configure_compact_logarithmic_y_axis(axis)

        rendered_panels.append((axis, payload_sizes, series))

    if baseline_memory_mean is not None:
        _configure_peak_rss_axes(rendered_panels, baseline_memory_mean)

    for axis in axes:
        axis.legend(fontsize=10, loc="upper left")

    figure.tight_layout()
    save_figure(figure, output_path)


def _configure_log2_payload_axis(
    axis: Axes,
    payload_sizes: list[int],
) -> None:
    _configure_log2_parameter_axis(
        axis,
        payload_sizes,
        [
            formatting.format_byte_size(payload_size, compact=True)
            for payload_size in payload_sizes
        ],
    )


def _configure_log2_count_axis(
    axis: Axes,
    parameter_values: list[int],
) -> None:
    _configure_log2_parameter_axis(
        axis,
        parameter_values,
        [str(parameter_value) for parameter_value in parameter_values],
    )


def _configure_log2_parameter_axis(
    axis: Axes,
    parameter_values: list[int],
    tick_labels: list[str],
) -> None:
    axis.set_xscale("log", base=2)
    axis.set_xticks(parameter_values)
    axis.set_xticklabels(tick_labels)
    axis.set_xlim(parameter_values[0] / 2, parameter_values[-1] * 2)
    axis.grid(
        True,
        axis="x",
        linestyle="--",
        linewidth=0.5,
        alpha=0.25,
    )
    apply_value_grid(axis)


def plot_aes_ascon_latency(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_aes_ascon_results(
        payload_sizes,
        results,
        "AES-GCM vs. ASCON: Latency vs. Payload Size",
        "Latency (µs/op)",
        output_path,
        with_logarithmic_y_axis=True,
    )


def plot_aes_ascon_latency_speedup(
    payload_sizes: list[int],
    speedups: dict[str, list[float]],
    output_path: str,
) -> None:
    _plot_payload_effect_points(
        payload_sizes,
        [
            (operation, [(None, speedups[operation], VIOLET)])
            for operation in ("Encrypt", "Decrypt")
        ],
        "ASCON Relative Speedup vs. AES-GCM",
        "ASCON Speedup over AES-GCM (×)",
        1.0,
        "Equal performance (1×)",
        output_path,
    )


def _plot_payload_effect_points(
    payload_sizes: list[int],
    panels: list[
        tuple[
            str,
            list[tuple[str | None, list[float], str]],
        ]
    ],
    title: str,
    x_label: str,
    reference_value: float,
    reference_label: str,
    output_path: str,
) -> None:
    positions = list(range(len(payload_sizes)))
    payload_labels = [
        formatting.format_byte_size(payload_size, compact=True)
        for payload_size in payload_sizes
    ]
    measured_values = [
        value for _, series in panels for _, values, _ in series for value in values
    ]
    lower_bound = min(measured_values + [reference_value])
    upper_bound = max(measured_values + [reference_value])
    value_range = upper_bound - lower_bound
    margin = value_range * 0.08

    if margin == 0:
        margin = max(abs(reference_value), 1.0) * 0.08

    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)

    for axis, (operation, series) in zip(axes, panels, strict=True):
        offsets = [
            (index - (len(series) - 1) / 2) * 0.22 for index in range(len(series))
        ]

        for offset, (label, values, color) in zip(offsets, series, strict=True):
            axis.scatter(
                values,
                [position + offset for position in positions],
                color=color,
                s=38,
                label=label,
                zorder=3,
            )
        axis.axvline(
            reference_value,
            color=TEAL,
            linestyle="--",
            linewidth=1.8,
            label=reference_label,
        )
        axis.set_title(operation, fontsize=11)
        axis.set_xlabel(x_label)
        axis.set_ylabel("Payload Size")
        axis.set_yticks(positions)
        axis.set_yticklabels(payload_labels)
        axis.set_ylim(len(positions) - 0.5, -0.5)
        axis.set_xlim(lower_bound - margin, upper_bound + margin)
        axis.grid(
            True,
            axis="x",
            linestyle="-",
            linewidth=0.5,
            alpha=0.18,
        )
        axis.legend(fontsize=9, loc="best")

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_aes_ascon_throughput(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_aes_ascon_results(
        payload_sizes,
        results,
        "AES-GCM vs. ASCON: Throughput vs. Payload Size",
        "Throughput (MB/s)",
        output_path,
    )


def plot_aes_ascon_energy(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_aes_ascon_results(
        payload_sizes,
        results,
        "AES-GCM vs. ASCON: Energy per Operation vs. Payload Size",
        "Energy (µJ/op)",
        output_path,
        with_logarithmic_y_axis=True,
    )


def plot_aes_ascon_energy_reduction(
    payload_sizes: list[int],
    reductions: dict[str, list[float]],
    output_path: str,
) -> None:
    _plot_payload_effect_points(
        payload_sizes,
        [
            (operation, [("Estimate from means", reductions[operation], VIOLET)])
            for operation in ("Encrypt", "Decrypt")
        ],
        "ASCON Energy Reduction vs. AES-GCM",
        "ASCON Energy Reduction vs. AES-GCM (%)",
        0.0,
        "No reduction (0%)",
        output_path,
    )


def plot_aes_ascon_memory(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    baseline_memory_mean: float,
    output_path: str,
) -> None:
    _plot_aes_ascon_results(
        payload_sizes,
        results,
        "AES-GCM vs. ASCON: Peak Process Memory vs. Payload Size",
        "Peak RSS (MB)",
        output_path,
        baseline_memory_mean=baseline_memory_mean,
    )


FULL_SCHEMA_DETAIL_FIGURE_SIZE = (15, 9.2)
FULL_SCHEMA_TICK_LABEL_SPACING = 1.35
FULL_SCHEMA_LINEAR_STEP_MANTISSAS = (1.0, 2.0, 2.5, 5.0, 10.0)
FULL_SCHEMA_LOGARITHMIC_MANTISSA_TIERS = (
    (1.0,),
    (1.0, 3.0),
    (1.0, 2.0, 5.0),
    (1.0, 1.5, 2.0, 3.0, 5.0, 7.0),
    (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0),
    (
        1.0,
        1.25,
        1.5,
        2.0,
        2.5,
        3.0,
        3.5,
        4.0,
        4.5,
        5.0,
        5.5,
        6.0,
        6.5,
        7.0,
        7.5,
        8.0,
    ),
    (
        1.0,
        1.25,
        1.5,
        2.0,
        2.5,
        3.0,
        3.5,
        4.0,
        4.5,
        5.0,
        5.5,
        6.0,
        6.5,
        7.0,
        7.5,
        8.0,
        8.5,
        9.0,
        9.5,
    ),
)
FULL_SCHEMA_FAMILIES = (
    ("PSK", "PSK", TEAL),
    ("RSA", "RSA", VIOLET),
    ("CPABE", "CP-ABE", CRIMSON),
)
FULL_SCHEMA_PROFILES = (
    ("Standard", "Standard", "-", "o", ""),
    ("Lightweight", "Lightweight", "--", "s", "//"),
)


def _full_schema_series(
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    operation: str,
) -> list[tuple[str, list[float], list[float], str, str, str]]:
    series = []

    for family, family_label, color in FULL_SCHEMA_FAMILIES:
        for profile, profile_label, linestyle, marker, _ in FULL_SCHEMA_PROFILES:
            configuration = f"{family}{profile}"
            means, confidence_intervals = results[(configuration, operation)]
            series.append(
                (
                    f"{family_label} — {profile_label}",
                    means,
                    confidence_intervals,
                    color,
                    linestyle,
                    marker,
                )
            )

    return series


def _draw_full_schema_series(
    axis: Axes,
    payload_sizes: list[int],
    series: list[tuple[str, list[float], list[float], str, str, str]],
) -> None:
    for label, means, confidence_intervals, color, linestyle, marker in series:
        draw_summary(
            axis,
            payload_sizes,
            means,
            confidence_intervals,
            label,
            color,
            with_ci=True,
            linestyle=linestyle,
            marker=marker,
        )


def _configure_full_schema_payload_axis(
    axis: Axes,
    payload_sizes: list[int],
) -> None:
    _configure_log2_parameter_axis(
        axis,
        payload_sizes,
        [formatting.format_byte_size(payload_size) for payload_size in payload_sizes],
    )


def _format_full_schema_number(value: float, _position: float) -> str:
    nearest_integer = round(value)
    tolerance = max(1e-9, abs(value) * 1e-12)

    if isclose(value, nearest_integer, rel_tol=0.0, abs_tol=tolerance):
        return f"{nearest_integer:,}"

    return f"{value:,.6f}".rstrip("0").rstrip(".")


def _full_schema_minimum_tick_spacing(axis: Axes) -> float:
    label_size = axis.yaxis.get_major_ticks()[0].label1.get_fontsize()
    label_height = label_size * axis.figure.dpi / 72
    return label_height * FULL_SCHEMA_TICK_LABEL_SPACING


def _full_schema_ticks_are_readable(axis: Axes, ticks: list[float]) -> bool:
    if len(ticks) < 2:
        return True

    x_position = axis.get_xlim()[0]
    display_positions = [
        axis.transData.transform((x_position, tick))[1] for tick in ticks
    ]
    minimum_spacing = min(
        second - first
        for first, second in zip(display_positions, display_positions[1:])
    )
    return minimum_spacing >= _full_schema_minimum_tick_spacing(axis)


def _full_schema_nice_linear_step(minimum_step: float) -> float:
    magnitude = 10 ** floor(log10(minimum_step))
    normalized_step = minimum_step / magnitude

    for mantissa in FULL_SCHEMA_LINEAR_STEP_MANTISSAS:
        if mantissa >= normalized_step:
            return mantissa * magnitude

    raise ValueError(f"Unable to calculate a linear tick step for {minimum_step}")


def _full_schema_linear_ticks(
    axis: Axes,
    lower_bound: float,
    upper_bound: float,
) -> list[float]:
    axis_height = axis.get_window_extent().height
    visible_range = upper_bound - lower_bound
    minimum_step = visible_range * _full_schema_minimum_tick_spacing(axis) / axis_height
    step = _full_schema_nice_linear_step(minimum_step)
    first_multiple = ceil(lower_bound / step)
    last_multiple = floor(upper_bound / step)

    return [multiple * step for multiple in range(first_multiple, last_multiple + 1)]


def _full_schema_logarithmic_candidates(
    lower_bound: float,
    upper_bound: float,
    mantissas: tuple[float, ...],
) -> list[float]:
    first_exponent = floor(log10(lower_bound)) - 1
    last_exponent = ceil(log10(upper_bound)) + 1

    return sorted(
        {
            mantissa * 10**exponent
            for exponent in range(first_exponent, last_exponent + 1)
            for mantissa in mantissas
            if lower_bound <= mantissa * 10**exponent <= upper_bound
        }
    )


def _full_schema_logarithmic_ticks(
    axis: Axes,
    lower_bound: float,
    upper_bound: float,
) -> list[float]:
    for mantissas in reversed(FULL_SCHEMA_LOGARITHMIC_MANTISSA_TIERS):
        ticks = _full_schema_logarithmic_candidates(
            lower_bound,
            upper_bound,
            mantissas,
        )

        if ticks and _full_schema_ticks_are_readable(axis, ticks):
            return ticks

    return _full_schema_logarithmic_candidates(
        lower_bound,
        upper_bound,
        FULL_SCHEMA_LOGARITHMIC_MANTISSA_TIERS[0],
    )


def _configure_full_schema_logarithmic_y_axis(axis: Axes) -> None:
    axis.set_yscale("log", base=10)
    y_limits = axis.get_ylim()
    lower_bound, upper_bound = y_limits
    ticks = _full_schema_logarithmic_ticks(axis, lower_bound, upper_bound)
    axis.yaxis.set_major_locator(FixedLocator(ticks))
    axis.yaxis.set_major_formatter(FuncFormatter(_format_full_schema_number))
    axis.yaxis.set_minor_formatter(NullFormatter())
    axis.tick_params(axis="y", labelleft=True)
    apply_value_grid(axis)
    assert axis.get_ylim() == y_limits


def _configure_full_schema_linear_y_axis(axis: Axes) -> None:
    y_limits = axis.get_ylim()
    ticks = _full_schema_linear_ticks(axis, *y_limits)
    axis.yaxis.set_major_locator(FixedLocator(ticks))
    axis.yaxis.set_major_formatter(FuncFormatter(_format_full_schema_number))
    axis.tick_params(axis="y", labelleft=True)
    apply_value_grid(axis)
    assert axis.get_ylim() == y_limits


def _plot_full_schema_overview(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    title: str,
    y_label: str,
    output_path: str,
    with_logarithmic_y_axis: bool = False,
    baseline_memory_mean: float | None = None,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.8), sharey=True)
    figure.suptitle(title, fontsize=13)
    rendered_panels = []

    for axis, operation in zip(axes, ("Encrypt", "Decrypt"), strict=True):
        series = _full_schema_series(results, operation)
        _draw_full_schema_series(axis, payload_sizes, series)
        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Payload Size")
        axis.set_ylabel(y_label)
        _configure_full_schema_payload_axis(axis, payload_sizes)
        if with_logarithmic_y_axis:
            axis.set_yscale("log", base=10)
        rendered_panels.append(
            (
                axis,
                payload_sizes,
                [
                    (label, means, confidence_intervals, color)
                    for label, means, confidence_intervals, color, _, _ in series
                ],
            )
        )

    if baseline_memory_mean is not None:
        _configure_peak_rss_axes(rendered_panels, baseline_memory_mean)
    elif not with_logarithmic_y_axis:
        for axis in axes:
            axis.set_ylim(bottom=0)

    handles, labels = axes[0].get_legend_handles_labels()

    if baseline_memory_mean is not None:
        baseline_index = labels.index("Runtime baseline")
        baseline_handle = handles.pop(baseline_index)
        labels.pop(baseline_index)
        axes[0].legend(
            [baseline_handle],
            ["Runtime baseline"],
            fontsize=9,
            loc="upper left",
        )

    figure.legend(
        handles,
        labels,
        fontsize=9,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.94),
        ncol=3,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.82))

    for axis in axes:
        if with_logarithmic_y_axis:
            _configure_full_schema_logarithmic_y_axis(axis)
        else:
            _configure_full_schema_linear_y_axis(axis)

    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.82))
    save_figure(figure, output_path)


def plot_full_schema_latency_overview(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_full_schema_overview(
        payload_sizes,
        results,
        "Full Schema Latency Overview",
        "Latency (µs/op)",
        output_path,
        with_logarithmic_y_axis=True,
    )


def plot_full_schema_latency(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    figure, axes = plt.subplots(2, 3, figsize=FULL_SCHEMA_DETAIL_FIGURE_SIZE)
    figure.suptitle("Full Schema Latency Detail by Key Management", fontsize=13)

    for row_index, operation in enumerate(("Encrypt", "Decrypt")):
        for column_index, (family, family_label, color) in enumerate(
            FULL_SCHEMA_FAMILIES
        ):
            axis = axes[row_index][column_index]

            for profile, profile_label, linestyle, marker, _ in FULL_SCHEMA_PROFILES:
                means, confidence_intervals = results[(f"{family}{profile}", operation)]
                draw_summary(
                    axis,
                    payload_sizes,
                    means,
                    confidence_intervals,
                    profile_label,
                    color,
                    with_ci=True,
                    linestyle=linestyle,
                    marker=marker,
                )

            axis.set_title(f"{family_label} — {operation}", fontsize=11)
            axis.set_xlabel("Payload Size")
            axis.set_ylabel("Latency (µs/op)")
            _configure_full_schema_payload_axis(axis, payload_sizes)
            axis.set_yscale("log", base=10)

    handles, labels = axes[0][0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        fontsize=10,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.95),
        ncol=2,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.91))

    for axis in axes.flat:
        _configure_full_schema_logarithmic_y_axis(axis)

    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.91))
    save_figure(figure, output_path)


def plot_full_schema_serialized_envelope_size(
    payload_sizes: list[int],
    envelope_sizes: dict[str, list[float]],
    output_path: str,
) -> None:
    positions = list(range(len(payload_sizes)))
    bar_width = 0.13
    figure, axis = plt.subplots(figsize=(11, 5.8))

    series_index = 0
    for family, family_label, color in FULL_SCHEMA_FAMILIES:
        for profile, profile_label, _, _, hatch in FULL_SCHEMA_PROFILES:
            offset = (series_index - 2.5) * bar_width
            axis.bar(
                [position + offset for position in positions],
                envelope_sizes[f"{family}{profile}"],
                width=bar_width,
                label=f"{family_label} — {profile_label}",
                color=color,
                edgecolor="black",
                linewidth=0.4,
                hatch=hatch,
            )
            series_index += 1

    axis.set_title("Serialized Envelope Size", fontsize=13)
    axis.set_xlabel("Payload Size")
    axis.set_ylabel("Serialized Envelope Size (bytes)")
    axis.set_xticks(positions)
    axis.set_xticklabels(
        [formatting.format_byte_size(payload_size) for payload_size in payload_sizes]
    )
    axis.set_xlim(-0.65, len(positions) - 0.35)
    axis.set_yscale("log", base=10)
    axis.legend(
        fontsize=10,
        loc="upper left",
        ncol=3,
    )

    figure.tight_layout()
    _configure_full_schema_logarithmic_y_axis(axis)
    figure.tight_layout()
    save_figure(figure, output_path)


def plot_full_schema_energy(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_full_schema_overview(
        payload_sizes,
        results,
        "Full Schema Energy per Operation",
        "Energy (µJ/op)",
        output_path,
        with_logarithmic_y_axis=True,
    )


def plot_full_schema_memory(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    baseline_memory_mean: float,
    output_path: str,
) -> None:
    _plot_full_schema_overview(
        payload_sizes,
        results,
        "Full Schema Peak Process Memory",
        "Peak RSS (MB)",
        output_path,
        baseline_memory_mean=baseline_memory_mean,
    )


def _configure_compact_linear_y_axis(axis: Axes) -> None:
    axis.yaxis.set_major_formatter(FuncFormatter(_format_compact_number))


def _configure_compact_logarithmic_y_axis(axis: Axes) -> None:
    _configure_logarithmic_y_axis(axis, _format_compact_number)


def _configure_byte_logarithmic_y_axis(axis: Axes) -> None:
    _configure_logarithmic_y_axis(axis, _format_byte_logarithmic_tick)


def _configure_logarithmic_y_axis(
    axis: Axes,
    formatter: Callable[[float, float], str],
) -> None:
    axis.set_yscale("log", base=10)
    axis.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0,)))
    axis.yaxis.set_major_formatter(FuncFormatter(formatter))
    axis.yaxis.set_minor_formatter(NullFormatter())
    apply_value_grid(axis)


def _format_compact_number(value: float, _position: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:g}M"

    if value >= 1_000:
        return f"{value / 1_000:g}k"

    return f"{value:g}"


def _format_byte_logarithmic_tick(value: float, _position: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:g} MB"

    if value >= 1_000:
        return f"{value / 1_000:g} KB"

    return f"{value:g} B"


def configure_attribute_axis(attribute_counts: list[int], axis: Axes) -> None:
    axis.set_xticks(attribute_counts)
    apply_mesh_grid(axis)


def _configure_parameter_axis(
    axis: Axes,
    title: str,
    y_label: str,
    parameter_values: list[int],
    x_label: str,
    with_logarithmic_y_axis: bool = False,
) -> None:
    axis.set_title(title, fontsize=11)
    axis.set_ylabel(y_label)
    if with_logarithmic_y_axis:
        _configure_compact_logarithmic_y_axis(axis)
    else:
        axis.set_ylim(bottom=0)
    axis.set_xticks(parameter_values)
    axis.set_xlabel(x_label)
    apply_value_grid(axis)
    axis.legend(fontsize=10)


def _plot_json_cbor_results(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    title: str,
    y_label: str,
    output_path: str,
    with_logarithmic_y_axis: bool = False,
) -> None:
    panels = []

    formats = (
        ("JSON", "JSON", AMBER),
        ("CBOR", "CBOR", VIOLET),
        ("CBORKeyAsInt", "CBOR (Int Keys)", TEAL),
    )

    for operation in ("Serialize", "Deserialize"):
        series = []

        for format_name, label, color in formats:
            means, confidence_intervals = results[(format_name, operation)]
            series.append((label, means, confidence_intervals, color))

        panels.append((operation, series))

    _plot_operation_comparison(
        payload_sizes,
        panels,
        title,
        "Payload Size (bytes)",
        y_label,
        output_path,
        with_log2_payload_axis=True,
        with_logarithmic_y_axis=with_logarithmic_y_axis,
    )


def plot_json_cbor_latency(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_json_cbor_results(
        payload_sizes,
        results,
        "JSON vs. CBOR vs. CBOR (Int Keys): Latency vs. Payload Size",
        "Latency (µs/op)",
        output_path,
        with_logarithmic_y_axis=True,
    )


def plot_json_cbor_latency_speedup(
    payload_sizes: list[int],
    speedups: dict[tuple[str, str], list[float]],
    output_path: str,
) -> None:
    _plot_payload_effect_points(
        payload_sizes,
        [
            (
                operation,
                [
                    ("CBOR", speedups[("CBOR", operation)], VIOLET),
                    (
                        "CBOR (Int Keys)",
                        speedups[("CBORKeyAsInt", operation)],
                        TEAL,
                    ),
                ],
            )
            for operation in ("Serialize", "Deserialize")
        ],
        "CBOR Relative Latency Speedup vs. JSON",
        "Speedup vs JSON (×)",
        1.0,
        "Equal performance (1×)",
        output_path,
    )


def plot_json_cbor_size(
    payload_sizes: list[int],
    message_sizes: dict[str, list[int]],
    output_path: str,
) -> None:
    figure, axis = plt.subplots(figsize=(8.5, 5.2))

    for format_name, label, color in (
        ("JSON", "JSON", AMBER),
        ("CBOR", "CBOR", VIOLET),
        ("CBORKeyAsInt", "CBOR (Int Keys)", TEAL),
    ):
        axis.plot(
            payload_sizes,
            message_sizes[format_name],
            label=label,
            color=color,
            marker="o",
            linewidth=1.8,
            markersize=5,
        )

    axis.set_title(
        "JSON vs. CBOR vs. CBOR (Int Keys): Message Size vs. Payload Size",
        fontsize=13,
    )
    axis.set_xlabel("Payload Size (bytes)")
    axis.set_ylabel("Message size (bytes)")
    _configure_log2_payload_axis(axis, payload_sizes)
    _configure_byte_logarithmic_y_axis(axis)
    axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_json_cbor_wire_overhead(
    payload_sizes: list[int],
    wire_overheads: dict[str, list[int]],
    output_path: str,
) -> None:
    positions = list(range(len(payload_sizes)))
    bar_width = 0.25
    figure, axis = plt.subplots(figsize=(8.5, 5.2))

    for series_index, (format_name, label, color) in enumerate(
        (
            ("JSON", "JSON", AMBER),
            ("CBOR", "CBOR", VIOLET),
            ("CBORKeyAsInt", "CBOR (Int Keys)", TEAL),
        )
    ):
        offset = (series_index - 1) * bar_width
        axis.bar(
            [position + offset for position in positions],
            wire_overheads[format_name],
            width=bar_width,
            label=label,
            color=color,
        )

    axis.set_title("Wire Overhead above Raw Message Data", fontsize=13)
    axis.set_xlabel("Payload Size")
    axis.set_ylabel("Wire overhead (bytes, log scale)")
    _configure_byte_logarithmic_y_axis(axis)
    axis.set_ylim(bottom=1)
    axis.set_xticks(positions)
    axis.set_xticklabels(
        [
            formatting.format_byte_size(payload_size, compact=True)
            for payload_size in payload_sizes
        ]
    )
    axis.set_xlim(-0.6, len(positions) - 0.4)
    axis.grid(
        True,
        axis="y",
        which="both",
        linestyle="-",
        linewidth=0.5,
        alpha=0.18,
    )
    axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_json_cbor_energy(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_json_cbor_results(
        payload_sizes,
        results,
        "JSON vs. CBOR vs. CBOR (Int Keys): Energy per Operation vs. Payload Size",
        "Energy (µJ/op)",
        output_path,
        with_logarithmic_y_axis=True,
    )


def plot_json_cbor_energy_reduction(
    payload_sizes: list[int],
    reductions: dict[tuple[str, str], list[float]],
    output_path: str,
) -> None:
    _plot_payload_effect_points(
        payload_sizes,
        [
            (
                operation,
                [
                    ("CBOR", reductions[("CBOR", operation)], VIOLET),
                    (
                        "CBOR (Int Keys)",
                        reductions[("CBORKeyAsInt", operation)],
                        TEAL,
                    ),
                ],
            )
            for operation in ("Serialize", "Deserialize")
        ],
        "CBOR Energy Reduction vs. JSON",
        "Energy Reduction vs JSON (%)",
        0.0,
        "No reduction (0%)",
        output_path,
    )


def _plot_latency_and_size(
    parameter_values: list[int],
    title: str,
    x_label: str,
    latency_series: list[tuple[str, list[float], list[float], str]],
    size_series: list[tuple[str, list[float], list[float], str]],
    output_path: str,
    constant: tuple[float, str, str] | None = None,
    with_logarithmic_size_axis: bool = False,
    with_log2_count_axis: bool = True,
    latency_y_ticks: list[int] | None = None,
) -> None:
    figure, (latency_axis, size_axis) = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)
    _draw_summaries(latency_axis, parameter_values, latency_series, with_ci=True)
    if constant is not None:
        value, label, color = constant
        draw_constant(latency_axis, value, parameter_values, label, color)
    _draw_summaries(size_axis, parameter_values, size_series)
    latency_axis.set_title("Latency", fontsize=11)
    latency_axis.set_xlabel(x_label)
    latency_axis.set_ylabel("Latency (µs/op)")
    if with_log2_count_axis:
        _configure_log2_count_axis(latency_axis, parameter_values)
    else:
        configure_attribute_axis(parameter_values, latency_axis)
    _configure_compact_logarithmic_y_axis(latency_axis)
    if latency_y_ticks is not None:
        latency_axis.set_yticks(latency_y_ticks)
    latency_axis.legend(fontsize=10)

    size_axis.set_title("Sizes", fontsize=11)
    size_axis.set_xlabel(x_label)
    size_axis.set_ylabel("Size (bytes)")
    if with_log2_count_axis:
        _configure_log2_count_axis(size_axis, parameter_values)
    else:
        configure_attribute_axis(parameter_values, size_axis)
    if with_logarithmic_size_axis:
        _configure_byte_logarithmic_y_axis(size_axis)
    else:
        size_axis.set_ylim(bottom=0)
    size_axis.legend(fontsize=10)
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    save_figure(figure, output_path)


def plot_cpabe_attributes(
    attribute_counts: list[int],
    results: dict[str, tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    encrypt_latency_means, encrypt_latency_cis = results["encrypt_latency"]
    decrypt_latency_means, decrypt_latency_cis = results["decrypt_latency"]
    ciphertext_means, ciphertext_cis = results["ciphertext"]
    stored_key_means, stored_key_cis = results["stored_key"]
    _plot_latency_and_size(
        attribute_counts,
        "CP-ABE Scaling with Policy Attributes",
        "Policy Attributes",
        [
            ("Encrypt", encrypt_latency_means, encrypt_latency_cis, AMBER),
            ("Decrypt", decrypt_latency_means, decrypt_latency_cis, VIOLET),
        ],
        [
            ("Ciphertext", ciphertext_means, ciphertext_cis, AMBER),
            ("Private Key", stored_key_means, stored_key_cis, CRIMSON),
        ],
        output_path,
        with_log2_count_axis=False,
        latency_y_ticks=[200_000, 500_000, 1_000_000, 2_000_000, 5_000_000],
    )


def plot_rsa_subscribers(
    subscriber_counts: list[int],
    results: dict,
    fixed_rsa_key_bits: int,
    output_path: str,
) -> None:
    encrypt_latency_means, encrypt_latency_cis = results["encrypt_latency"]
    ciphertext_means, ciphertext_cis = results["ciphertext"]
    total_ciphertext_means, total_ciphertext_cis = results["total_ciphertext"]
    constant = (
        results["decrypt_latency"],
        f"Decrypt (RSA-{fixed_rsa_key_bits}, Constant)",
        VIOLET,
    )
    _plot_latency_and_size(
        subscriber_counts,
        f"RSA Scaling with Subscribers (Fixed Key: {fixed_rsa_key_bits} bits)",
        "Subscribers",
        [("Encrypt", encrypt_latency_means, encrypt_latency_cis, AMBER)],
        [
            ("Ciphertext", ciphertext_means, ciphertext_cis, AMBER),
            (
                "Ciphertext (TOTAL)",
                total_ciphertext_means,
                total_ciphertext_cis,
                TOTAL_CIPHERTEXT_COLOR,
            ),
        ],
        output_path,
        constant,
        with_logarithmic_size_axis=True,
    )


def plot_rsa_key_size_sensitivity(
    rsa_key_bits: list[int],
    results: dict,
    output_path: str,
) -> None:
    encrypt_latency_means, encrypt_latency_cis = results["encrypt_latency"]
    decrypt_latency_means, decrypt_latency_cis = results["decrypt_latency"]
    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    _draw_summaries(
        axis,
        rsa_key_bits,
        [
            ("Encrypt", encrypt_latency_means, encrypt_latency_cis, AMBER),
            ("Decrypt", decrypt_latency_means, decrypt_latency_cis, VIOLET),
        ],
        with_ci=True,
    )

    _configure_parameter_axis(
        axis,
        "RSA Key-Size Sensitivity (1 Subscriber)",
        "Latency (µs/op)",
        rsa_key_bits,
        "RSA Key Bits",
        with_logarithmic_y_axis=True,
    )

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_cpabe_rsa_memory(
    parameter_values_by_algorithm: dict[str, list[int]],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    baseline_memory_mean: float,
    output_path: str,
) -> None:
    attribute_counts = parameter_values_by_algorithm["CPABEAttributes"]
    subscriber_counts = parameter_values_by_algorithm["RSASubscribers"]
    cpabe_encrypt_means, cpabe_encrypt_cis = results[("CPABEAttributes", "Encrypt")]
    cpabe_decrypt_means, cpabe_decrypt_cis = results[("CPABEAttributes", "Decrypt")]
    subscriber_encrypt_means, subscriber_encrypt_cis = results[
        ("RSASubscribers", "Encrypt")
    ]
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE, sharey=True)
    figure.suptitle("Peak Process Memory of a Single Operation", fontsize=13)

    panels = [
        (
            axes[0],
            attribute_counts,
            "CP-ABE",
            "Policy Attributes",
            [
                ("Encrypt", cpabe_encrypt_means, cpabe_encrypt_cis, AMBER),
                ("Decrypt", cpabe_decrypt_means, cpabe_decrypt_cis, VIOLET),
            ],
        ),
        (
            axes[1],
            subscriber_counts,
            "RSA Subscribers",
            "Subscribers",
            [("Encrypt", subscriber_encrypt_means, subscriber_encrypt_cis, AMBER)],
        ),
    ]
    for axis, parameter_values, title, x_label, series in panels:
        _draw_summaries(axis, parameter_values, series, with_ci=True)
        axis.set_title(title, fontsize=11)
        axis.set_xlabel(x_label)
        _configure_log2_count_axis(axis, parameter_values)

    _configure_peak_rss_axes(
        [
            (axis, parameter_values, series)
            for axis, parameter_values, _, _, series in panels
        ],
        baseline_memory_mean,
    )

    for axis in axes:
        axis.legend(fontsize=9)

    axes[0].set_ylabel("Peak RSS (MB)")

    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    save_figure(figure, output_path)


def plot_cpabe_rsa_energy(
    parameter_values_by_algorithm: dict[str, list[int]],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    fixed_rsa_key_bits: int,
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE, sharey=True)
    figure.suptitle(
        "Energy per Operation under Policy and Subscriber Scaling",
        fontsize=13,
    )

    panels = (
        (
            axes[0],
            parameter_values_by_algorithm["CPABEAttributes"],
            "CP-ABE",
            "Policy Attributes",
            (
                ("Encrypt", "CPABEAttributes", "Encrypt", AMBER),
                ("Decrypt", "CPABEAttributes", "Decrypt", VIOLET),
            ),
        ),
        (
            axes[1],
            parameter_values_by_algorithm["RSASubscribers"],
            "RSA Subscribers",
            "Subscribers",
            (("Encrypt", "RSASubscribers", "Encrypt", AMBER),),
        ),
    )

    for axis, values, title, x_label, specifications in panels:
        series = []
        for label, algorithm, operation, color in specifications:
            means, confidence_intervals = results[(algorithm, operation)]
            series.append((label, means, confidence_intervals, color))
        _draw_summaries(axis, values, series, with_ci=True)
        axis.set_title(title, fontsize=11)
        axis.set_xlabel(x_label)
        _configure_log2_count_axis(axis, values)
        _configure_compact_logarithmic_y_axis(axis)
        axis.legend(fontsize=9)

    rsa_decrypt_means, _ = results[("RSAKeyBits", "Decrypt")]
    draw_constant(
        axes[1],
        rsa_decrypt_means[0],
        parameter_values_by_algorithm["RSASubscribers"],
        f"Decrypt (RSA-{fixed_rsa_key_bits}, Fixed Reference)",
        VIOLET,
    )
    axes[1].legend(fontsize=9)

    axes[0].set_ylabel("Energy (µJ/op)")
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    save_figure(figure, output_path)


def plot_ciphertext_size_crossover(
    subscriber_counts: list[int],
    results: dict,
    output_path: str,
) -> None:
    rsa_means = results["rsa_means"]
    rsa_cis = results["rsa_cis"]
    x_limit = subscriber_counts[-1]
    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    draw_summary(
        axis,
        subscriber_counts,
        rsa_means,
        rsa_cis,
        "RSA Scaling Subs",
        TOTAL_CIPHERTEXT_COLOR,
    )

    for attribute_count, level, crossover, color in (
        (
            results["low_attribute_count"],
            results["low_cpabe_level"],
            results["low_crossover"],
            AMBER,
        ),
        (
            results["high_attribute_count"],
            results["high_cpabe_level"],
            results["high_crossover"],
            CRIMSON,
        ),
    ):
        axis.hlines(
            level,
            1,
            x_limit,
            color=color,
            linewidth=1.8,
            label=(f"CP-ABE, {formatting.format_attribute_label(attribute_count)}"),
        )
        mark_crossover(axis, crossover, level, f"≈{crossover:,.1f}")

    linear_tick_values = [subscriber_counts[0]] + [
        count for count in subscriber_counts if count >= 8
    ]
    axis.set_xticks(linear_tick_values)
    axis.set_xlim(0.0, float(x_limit) * AXIS_HEADROOM)
    axis.set_xlabel("Subscribers")
    axis.set_ylabel("Ciphertext Bytes")
    axis.set_ylim(bottom=0.0)
    apply_value_grid(axis)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_encrypt_latency_crossover(
    subscriber_counts: list[int],
    results: dict,
    output_path: str,
) -> None:
    x_limit = results["projection_end_subscribers"]
    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    axis.plot(
        [results["projection_start_subscribers"], x_limit],
        [results["projection_start_micros"], results["projection_end_micros"]],
        color=TOTAL_CIPHERTEXT_COLOR,
        linewidth=1.8,
        linestyle=":",
        label="RSA Linear Fit (Projected Beyond Sample)",
    )

    draw_summary(
        axis,
        subscriber_counts,
        results["rsa_means"],
        results["rsa_cis"],
        "RSA Scaling Subs (Measured)",
        TOTAL_CIPHERTEXT_COLOR,
        linewidth=2.6,
    )

    largest_value = results["projection_end_micros"]

    for attribute_count, level, crossover, color in (
        (
            results["low_attribute_count"],
            results["low_cpabe_level"],
            results["low_crossover"],
            AMBER,
        ),
        (
            results["high_attribute_count"],
            results["high_cpabe_level"],
            results["high_crossover"],
            CRIMSON,
        ),
    ):
        axis.hlines(
            level,
            0.0,
            x_limit,
            color=color,
            linewidth=1.8,
            label=(f"CP-ABE, {formatting.format_attribute_label(attribute_count)}"),
        )
        mark_crossover(axis, crossover, level, f"≈{crossover:,.0f}")
        largest_value = max(largest_value, level)

    axis.set_xlim(0.0, x_limit)
    axis.set_ylim(0.0, largest_value * 1.12)
    axis.set_xlabel("Subscribers")
    axis.set_ylabel("Publisher Encrypt Latency (µs/op)")
    _configure_compact_linear_y_axis(axis)
    apply_value_grid(axis)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_decrypt_latency_comparison(
    attribute_counts: list[int],
    results: dict,
    output_path: str,
) -> None:
    cpabe_means = results["cpabe_means"]
    cpabe_cis = results["cpabe_cis"]
    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)
    draw_summary(
        axis,
        attribute_counts,
        cpabe_means,
        cpabe_cis,
        "CP-ABE",
        VIOLET,
        with_ci=True,
        linewidth=2.0,
    )
    draw_summary(
        axis,
        results["rsa_attribute_counts"],
        results["rsa_means"],
        results["rsa_cis"],
        f'RSA-{results["fixed_rsa_key_bits"]}',
        TOTAL_CIPHERTEXT_COLOR,
        with_ci=True,
        linewidth=2.0,
    )

    largest_value = max(
        calculate_axis_top(cpabe_means, cpabe_cis),
        calculate_axis_top(results["rsa_means"], results["rsa_cis"]),
    )

    _configure_log2_count_axis(axis, attribute_counts)
    axis.set_ylim(0.0, largest_value * 1.15)
    axis.set_xlabel("Policy Attributes")
    axis.set_ylabel("Decrypt Latency (µs/op)")
    _configure_compact_linear_y_axis(axis)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_encrypt_decrypt_asymmetry(
    results: dict,
    output_path: str,
) -> None:
    encrypt_values = [results["rsa_encrypt_micros"], results["cpabe_encrypt_micros"]]
    decrypt_values = [results["rsa_decrypt_micros"], results["cpabe_decrypt_micros"]]
    scheme_labels = [
        f'RSA-{results["fixed_rsa_key_bits"]}',
        f'CP-ABE ({formatting.format_attribute_label(results["min_attribute_count"])})',
    ]
    slower_operations = [
        results["rsa_slower_operation"],
        results["cpabe_slower_operation"],
    ]
    ratios = [results["rsa_ratio"], results["cpabe_ratio"]]

    figure, axis = plt.subplots(figsize=(9, 5.5))
    positions = [0.0, 1.25]
    bar_width = 0.34
    encrypt_positions = [position - bar_width / 2.0 for position in positions]
    decrypt_positions = [position + bar_width / 2.0 for position in positions]

    axis.bar(
        encrypt_positions, encrypt_values, width=bar_width, color=AMBER, label="Encrypt"
    )
    axis.bar(
        decrypt_positions,
        decrypt_values,
        width=bar_width,
        color=VIOLET,
        label="Decrypt",
    )

    largest_value = max(max(encrypt_values), max(decrypt_values))

    for index, position in enumerate(positions):
        for bar_position, value in (
            (encrypt_positions[index], encrypt_values[index]),
            (decrypt_positions[index], decrypt_values[index]),
        ):
            axis.annotate(
                f"{value:,.1f} µs",
                (bar_position, value),
                textcoords="offset points",
                xytext=(0, 5),
                ha="center",
                fontsize=9,
            )

        ratio_text = f"{slower_operations[index]} is {ratios[index]:.0f}× Slower"

        tallest_value = max(encrypt_values[index], decrypt_values[index])
        axis.text(
            position,
            tallest_value + largest_value * 0.10,
            ratio_text,
            ha="center",
            fontsize=10,
            fontweight="bold",
        )

    axis.set_ylim(0.0, largest_value * 1.24)
    axis.set_xticks(positions)
    axis.set_xticklabels(scheme_labels)
    axis.set_ylabel("Latency (µs/op)")
    axis.set_title("Encrypt vs Decrypt Asymmetry", fontsize=12)
    _configure_compact_linear_y_axis(axis)
    axis.grid(False)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(loc="upper center", ncol=2, frameon=False, fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)
