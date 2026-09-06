import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from report.render import formatting

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from math import isnan
from typing import Any

from .color import *
from .formatting import KILOBYTE, MEGABYTE

FIGURE_DPI = 150
PANEL_FIGURE_SIZE = (13, 5)

# Leaves a little space between the last data point and the right edge of an axis
AXIS_HEADROOM = 1.03
CROSSOVER_FIGURE_SIZE = (8.5, 5.2)
TOTAL_CIPHERTEXT_COLOR = TEAL
AES_ASCON_MAIN_TICK_MIN = 4 * KILOBYTE
AES_ASCON_ZOOM_MAX = KILOBYTE
PAYLOAD_SCALING_ZOOM_MAX = 256 * KILOBYTE
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
    options = {"linewidth": 1.8, "markersize": 5, "capsize": 4, **style}
    axis.errorbar(
        parameter_values,
        means,
        yerr=confidence_intervals if with_ci else None,
        label=label,
        color=color,
        marker="o",
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
        axis.set_ylim(bottom=0)
        rendered_panels.append((axis, parameter_values, series))

        if byte_tick_step is None:
            configure_attribute_axis(parameter_values, axis)
        else:
            configure_byte_axis(axis, parameter_values[-1], byte_tick_step)

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
    with_small_payload_zoom: bool = False,
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
        axis.set_xlabel("Payload size")
        axis.set_ylabel(y_label)
        if baseline_memory_mean is None:
            axis.set_ylim(bottom=0)
        _configure_aes_ascon_main_axis(axis, payload_sizes)
        rendered_panels.append((axis, payload_sizes, series))

        if with_small_payload_zoom:
            _draw_aes_ascon_small_payload_zoom(axis, payload_sizes, series)

    if baseline_memory_mean is not None:
        _configure_peak_rss_axes(rendered_panels, baseline_memory_mean)

    for axis in axes:
        axis.legend(fontsize=10, loc="upper left")

    figure.tight_layout()
    save_figure(figure, output_path)


def _configure_aes_ascon_main_axis(
    axis: Axes,
    payload_sizes: list[int],
) -> None:
    tick_values = [
        payload_size
        for payload_size in payload_sizes
        if payload_size >= AES_ASCON_MAIN_TICK_MIN
    ]

    axis.set_xscale("linear")
    axis.set_yscale("linear")
    axis.set_xticks(tick_values)
    axis.set_xticklabels(
        [
            formatting.format_byte_size(payload_size, compact=True)
            for payload_size in tick_values
        ]
    )
    axis.set_xlim(0, payload_sizes[-1] * AXIS_HEADROOM)
    apply_value_grid(axis)


def _draw_aes_ascon_small_payload_zoom(
    axis: Axes,
    payload_sizes: list[int],
    series: list[tuple[str, list[float], list[float], str]],
) -> None:
    zoom_indexes = [
        index
        for index, payload_size in enumerate(payload_sizes)
        if payload_size <= AES_ASCON_ZOOM_MAX
    ]
    zoom_payload_sizes = [payload_sizes[index] for index in zoom_indexes]
    zoom_axis = axis.inset_axes([0.30, 0.55, 0.46, 0.38])  # type: ignore
    zoom_series = []

    for label, means, confidence_intervals, color in series:
        zoom_means = [means[index] for index in zoom_indexes]
        zoom_confidence_intervals = [
            confidence_intervals[index] for index in zoom_indexes
        ]
        zoom_series.append((label, zoom_means, zoom_confidence_intervals, color))
        draw_summary(
            zoom_axis,
            zoom_payload_sizes,
            zoom_means,
            zoom_confidence_intervals,
            label,
            color,
            with_ci=True,
            linewidth=1.3,
            markersize=3.5,
            capsize=2.5,
        )

    zoom_axis.set_xscale("linear")
    zoom_axis.set_yscale("linear")
    zoom_axis.set_xlim(0, zoom_payload_sizes[-1] * AXIS_HEADROOM)
    zoom_axis.set_ylim(
        0,
        max(
            calculate_axis_top(means, confidence_intervals)
            for _, means, confidence_intervals, _ in zoom_series
        )
        * 1.10,
    )
    zoom_axis.set_xticks(zoom_payload_sizes)
    zoom_axis.set_xticklabels(
        [
            formatting.format_byte_size(payload_size, compact=True)
            for payload_size in zoom_payload_sizes
        ],
        rotation=90,
        ha="center",
    )
    zoom_axis.set_title("Small payloads", fontsize=8)
    zoom_axis.tick_params(axis="both", labelsize=7)
    apply_value_grid(zoom_axis, linewidth=0.4)


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
        with_small_payload_zoom=True,
    )


def plot_aes_ascon_latency_speedup(
    payload_sizes: list[int],
    speedups: dict[str, list[float]],
    output_path: str,
) -> None:
    positions = list(range(len(payload_sizes)))
    payload_labels = [
        formatting.format_byte_size(payload_size, compact=True)
        for payload_size in payload_sizes
    ]
    measured_values = speedups["Encrypt"] + speedups["Decrypt"]
    measured_minimum = min(measured_values)
    measured_maximum = max(measured_values)
    margin = (measured_maximum - measured_minimum) * 0.08
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle("ASCON Relative Speedup vs. AES-GCM", fontsize=13)

    for axis, operation in zip(axes, ("Encrypt", "Decrypt"), strict=True):
        axis.plot(
            positions,
            speedups[operation],
            color=VIOLET,
            marker="o",
            linewidth=1.8,
            markersize=5,
        )
        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Payload Size")
        axis.set_ylabel("Speedup vs AES-GCM (×)")
        axis.set_xticks(positions)
        axis.set_xticklabels(payload_labels)
        axis.set_xlim(-0.5, len(positions) - 0.5)
        axis.set_ylim(measured_minimum - margin, measured_maximum + margin)
        apply_value_grid(axis)

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
        with_small_payload_zoom=True,
    )


def plot_aes_ascon_energy_reduction(
    payload_sizes: list[int],
    reductions: dict[str, list[float]],
    output_path: str,
) -> None:
    positions = list(range(len(payload_sizes)))
    payload_labels = [
        formatting.format_byte_size(payload_size, compact=True)
        for payload_size in payload_sizes
    ]
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle("ASCON Energy Reduction vs. AES-GCM", fontsize=13)

    for axis, operation in zip(axes, ("Encrypt", "Decrypt"), strict=True):
        axis.bar(
            positions,
            reductions[operation],
            width=0.65,
            color=VIOLET,
        )
        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Payload Size")
        axis.set_ylabel("Energy Reduction vs AES-GCM (%)")
        axis.set_xticks(positions)
        axis.set_xticklabels(payload_labels)
        axis.set_xlim(-0.5, len(positions) - 0.5)
        axis.set_ylim(0, 100)
        apply_value_grid(axis)

    figure.tight_layout()
    save_figure(figure, output_path)


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


def _plot_payload_scaling_results(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    title: str,
    y_label: str,
    output_path: str,
    with_small_payload_zoom: bool = False,
    baseline_memory_mean: float | None = None,
) -> None:
    panels = []

    schemes = (
        ("PSK", "PSK", TEAL),
        ("RSA", "RSA", VIOLET),
        ("CPABE", "CP-ABE", CRIMSON),
    )

    for operation in ("Encrypt", "Decrypt"):
        series = []

        for scheme, label, color in schemes:
            means, confidence_intervals = results[(scheme, operation)]
            series.append((label, means, confidence_intervals, color))

        panels.append((operation, series))

    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)
    rendered_panels = []

    for axis, (operation, series) in zip(axes, panels):
        _draw_summaries(axis, payload_sizes, series, with_ci=True)
        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Payload Size")
        axis.set_ylabel(y_label)
        if baseline_memory_mean is None:
            axis.set_ylim(bottom=0)
        _configure_payload_scaling_main_axis(axis, payload_sizes)
        _configure_plain_y_axis(axis)
        rendered_panels.append((axis, payload_sizes, series))

        if with_small_payload_zoom:
            detail_series = series[:2] if operation == "Encrypt" else series
            detail_title = (
                "PSK + RSA detail" if operation == "Encrypt" else "Small-payload detail"
            )
            _draw_payload_scaling_small_payload_zoom(
                axis,
                payload_sizes,
                detail_series,
                detail_title,
            )

    if baseline_memory_mean is not None:
        _configure_peak_rss_axes(rendered_panels, baseline_memory_mean)

    for axis in axes:
        axis.legend(fontsize=10, loc="upper left")

    figure.tight_layout()
    save_figure(figure, output_path)


def _configure_payload_scaling_main_axis(
    axis: Axes,
    payload_sizes: list[int],
) -> None:
    tick_values = [
        payload_size
        for payload_size in payload_sizes
        if payload_size > PAYLOAD_SCALING_ZOOM_MAX
    ]

    axis.set_xscale("linear")
    axis.set_yscale("linear")
    axis.set_xticks(tick_values)
    axis.set_xticklabels(
        [
            formatting.format_byte_size(payload_size, compact=True)
            for payload_size in tick_values
        ]
    )
    axis.set_xlim(0, payload_sizes[-1] * AXIS_HEADROOM)
    apply_value_grid(axis)


def _draw_payload_scaling_small_payload_zoom(
    axis: Axes,
    payload_sizes: list[int],
    series: list[tuple[str, list[float], list[float], str]],
    title: str,
) -> None:
    zoom_indexes = [
        index
        for index, payload_size in enumerate(payload_sizes)
        if payload_size <= PAYLOAD_SCALING_ZOOM_MAX
    ]
    zoom_payload_sizes = [payload_sizes[index] for index in zoom_indexes]
    zoom_axis = axis.inset_axes([0.30, 0.55, 0.46, 0.38])  # type: ignore
    zoom_series = []

    for label, means, confidence_intervals, color in series:
        zoom_means = [means[index] for index in zoom_indexes]
        zoom_confidence_intervals = [
            confidence_intervals[index] for index in zoom_indexes
        ]
        zoom_series.append((label, zoom_means, zoom_confidence_intervals, color))
        draw_summary(
            zoom_axis,
            zoom_payload_sizes,
            zoom_means,
            zoom_confidence_intervals,
            label,
            color,
            with_ci=True,
            linewidth=1.3,
            markersize=3.5,
            capsize=2.5,
        )

    zoom_axis.set_xscale("linear")
    zoom_axis.set_yscale("linear")
    zoom_axis.set_xlim(0, zoom_payload_sizes[-1] * AXIS_HEADROOM)
    zoom_axis.set_ylim(
        0,
        max(
            calculate_axis_top(means, confidence_intervals)
            for _, means, confidence_intervals, _ in zoom_series
        )
        * 1.10,
    )
    visible_tick_values = [
        payload_size
        for payload_size in zoom_payload_sizes
        if payload_size >= 4 * KILOBYTE
    ]
    zoom_axis.set_xticks(visible_tick_values)
    zoom_axis.set_xticklabels(
        [
            formatting.format_byte_size(payload_size, compact=True)
            for payload_size in visible_tick_values
        ],
        rotation=90,
        ha="center",
    )
    zoom_axis.set_title(title, fontsize=8)
    zoom_axis.tick_params(axis="both", labelsize=7)
    _configure_plain_y_axis(zoom_axis)
    apply_value_grid(zoom_axis, linewidth=0.4)


def _configure_plain_y_axis(axis: Axes) -> None:
    axis.yaxis.set_major_formatter(FuncFormatter(_format_plain_number))


def _format_plain_number(value: float, _position: float) -> str:
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def plot_payload_scaling_latency(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_payload_scaling_results(
        payload_sizes,
        results,
        "PSK vs. RSA vs. CP-ABE: Latency vs. Payload Size",
        "Latency (µs/op)",
        output_path,
        with_small_payload_zoom=True,
    )


def plot_payload_scaling_latency_overhead_share(
    payload_sizes: list[int],
    values: dict[tuple[str, str], list[float]],
    output_path: str,
) -> None:
    positions = list(range(len(payload_sizes)))
    payload_labels = [
        formatting.format_byte_size(payload_size) for payload_size in payload_sizes
    ]
    bar_width = 0.38
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle("Latency Overhead Share above PSK", fontsize=13)

    for axis, operation in zip(axes, ("Encrypt", "Decrypt"), strict=True):
        rsa_values = values[("RSA", operation)]
        cpabe_values = values[("CPABE", operation)]
        rsa_bars = axis.bar(
            [position - bar_width / 2 for position in positions],
            rsa_values,
            width=bar_width,
            label="RSA",
            color=VIOLET,
        )
        cpabe_bars = axis.bar(
            [position + bar_width / 2 for position in positions],
            cpabe_values,
            width=bar_width,
            label="CP-ABE",
            color=CRIMSON,
        )

        axis.axhline(
            0.0,
            color=TEAL,
            linestyle="--",
            linewidth=1.8,
            label="PSK reference (0%)",
        )
        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Payload Size")
        axis.set_ylabel("Latency Overhead Share above PSK (%)")
        axis.set_yscale("linear")
        lower_bound = min(0.0, min(rsa_values + cpabe_values))
        upper_bound = max(0.0, max(rsa_values + cpabe_values))
        padding = (upper_bound - lower_bound) * 0.14
        axis.set_ylim(lower_bound - padding, upper_bound + padding)
        axis.set_xticks(positions)
        axis.set_xticklabels(payload_labels)
        axis.set_xlim(-0.6, len(positions) - 0.4)
        for bars, bar_values in (
            (rsa_bars, rsa_values),
            (cpabe_bars, cpabe_values),
        ):
            axis.bar_label(
                bars,
                labels=[
                    "<0.1%" if 0 < value < 0.1 else f"{value:.1f}%"
                    for value in bar_values
                ],
                padding=3,
                fontsize=7,
                rotation=90,
            )
        _configure_plain_y_axis(axis)
        apply_value_grid(axis)

    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        fontsize=10,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.94),
        ncol=3,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.89))
    save_figure(figure, output_path)


def plot_payload_scaling_throughput(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_payload_scaling_results(
        payload_sizes,
        results,
        "PSK vs. RSA vs. CP-ABE: Throughput vs. Payload Size",
        "Throughput (MB/s)",
        output_path,
    )


def plot_payload_scaling_wire_expansion(
    wire_expansions: dict[str, float],
    output_path: str,
) -> None:
    figure, axis = plt.subplots(figsize=(8.5, 5.2))
    schemes = (
        ("PSK", "PSK", TEAL),
        ("RSA", "RSA", VIOLET),
        ("CPABE", "CP-ABE", CRIMSON),
    )
    values = [wire_expansions[scheme] for scheme, _, _ in schemes]
    bars = axis.bar(
        [label for _, label, _ in schemes],
        values,
        color=[color for _, _, color in schemes],
    )

    axis.set_title(
        "PSK vs. RSA vs. CP-ABE: Fixed Wire Expansion per Message",
        fontsize=13,
    )
    axis.set_ylabel("Additional Bytes per Message")
    axis.set_ylim(bottom=0)
    axis.bar_label(
        bars,
        labels=[f"{round(value):,} B" for value in values],
        padding=4,
    )
    _configure_plain_y_axis(axis)
    apply_value_grid(axis)

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_payload_scaling_energy(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_payload_scaling_results(
        payload_sizes,
        results,
        "PSK vs. RSA vs. CP-ABE: Energy per Operation vs. Payload Size",
        "Energy (µJ/op)",
        output_path,
        with_small_payload_zoom=True,
    )


def plot_payload_scaling_additional_energy(
    payload_sizes: list[int],
    values: dict[tuple[str, str], list[float]],
    output_path: str,
) -> None:
    positions = list(range(len(payload_sizes)))
    payload_labels = [
        formatting.format_byte_size(payload_size) for payload_size in payload_sizes
    ]
    bar_width = 0.38
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle("Additional Energy Cost over PSK", fontsize=13)

    for axis, operation in zip(axes, ("Encrypt", "Decrypt"), strict=True):
        rsa_values = values[("RSA", operation)]
        cpabe_values = values[("CPABE", operation)]
        rsa_bars = axis.bar(
            [position - bar_width / 2 for position in positions],
            rsa_values,
            width=bar_width,
            label="RSA",
            color=VIOLET,
        )
        cpabe_bars = axis.bar(
            [position + bar_width / 2 for position in positions],
            cpabe_values,
            width=bar_width,
            label="CP-ABE",
            color=CRIMSON,
        )

        axis.axhline(
            0.0,
            color=TEAL,
            linestyle="--",
            linewidth=1.8,
            label="PSK reference (0 mJ/op)",
        )
        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Payload Size")
        axis.set_ylabel("Additional Energy Cost over PSK (mJ/op)")
        axis.set_yscale("linear")
        lower_bound = min(0.0, min(rsa_values + cpabe_values))
        upper_bound = max(0.0, max(rsa_values + cpabe_values))
        padding = (upper_bound - lower_bound) * 0.14
        axis.set_ylim(lower_bound - padding, upper_bound + padding)
        axis.set_xticks(positions)
        axis.set_xticklabels(payload_labels)
        axis.set_xlim(-0.6, len(positions) - 0.4)
        for bars, bar_values in (
            (rsa_bars, rsa_values),
            (cpabe_bars, cpabe_values),
        ):
            axis.bar_label(
                bars,
                labels=[f"{value:,.1f}" for value in bar_values],
                padding=3,
                fontsize=7,
                rotation=90,
            )
        _configure_plain_y_axis(axis)
        apply_value_grid(axis)

    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        fontsize=10,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.94),
        ncol=3,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.89))
    save_figure(figure, output_path)


def plot_payload_scaling_memory(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    baseline_memory_mean: float,
    output_path: str,
) -> None:
    _plot_payload_scaling_results(
        payload_sizes,
        results,
        "PSK vs. RSA vs. CP-ABE: Peak Process Memory vs. Payload Size",
        "Peak RSS (MB)",
        output_path,
        baseline_memory_mean=baseline_memory_mean,
    )


def configure_attribute_axis(attribute_counts: list[int], axis: Axes) -> None:
    axis.set_xticks(attribute_counts)
    apply_mesh_grid(axis)


def _configure_parameter_axis(
    axis: Axes,
    title: str,
    y_label: str,
    parameter_values: list[int],
    x_label: str,
) -> None:
    axis.set_title(title, fontsize=11)
    axis.set_ylabel(y_label)
    axis.set_ylim(bottom=0)
    axis.set_xticks(parameter_values)
    axis.set_xlabel(x_label)
    apply_value_grid(axis)
    axis.legend(fontsize=10)


def _plot_json_cbor_results(
    attribute_counts: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    title: str,
    y_label: str,
    output_path: str,
) -> None:
    panels = []

    formats = (
        ("JSON", "JSON", AMBER),
        ("CBOR", "CBOR", VIOLET),
        ("CBORKeyAsInt", "CBOR (int keys)", TEAL),
    )

    for operation in ("Serialize", "Deserialize"):
        series = []

        for format_name, label, color in formats:
            means, confidence_intervals = results[(format_name, operation)]
            series.append((label, means, confidence_intervals, color))

        panels.append((operation, series))

    _plot_operation_comparison(
        attribute_counts,
        panels,
        title,
        "Attribute Count",
        y_label,
        output_path,
    )


def _plot_json_cbor_relative_results(
    attribute_counts: list[int],
    results: dict[tuple[str, str], list[float]],
    title: str,
    y_label: str,
    y_limits: dict[str, tuple[float, float]],
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)

    for axis, operation in zip(axes, ("Serialize", "Deserialize"), strict=True):
        for format_name, label, color in (
            ("CBOR", "CBOR", VIOLET),
            ("CBORKeyAsInt", "CBOR-int", TEAL),
        ):
            axis.plot(
                attribute_counts,
                results[(format_name, operation)],
                label=label,
                color=color,
                marker="o",
                linewidth=1.8,
                markersize=5,
            )

        axis.set_title(operation, fontsize=11)
        axis.set_xlabel("Attribute Count")
        axis.set_ylabel(y_label)
        axis.set_ylim(*y_limits[operation])
        configure_attribute_axis(attribute_counts, axis)
        axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_json_cbor_latency(
    attribute_counts: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_json_cbor_results(
        attribute_counts,
        results,
        "JSON vs. CBOR vs. CBOR (Int Keys): Latency vs. Policy Attributes",
        "Latency (µs)",
        output_path,
    )


def plot_json_cbor_latency_speedup(
    attribute_counts: list[int],
    speedups: dict[tuple[str, str], list[float]],
    output_path: str,
) -> None:
    _plot_json_cbor_relative_results(
        attribute_counts,
        speedups,
        "Relative Latency Speedup vs. Policy Attributes",
        "Speedup vs JSON (×)",
        {
            "Serialize": (4.0, 6.5),
            "Deserialize": (18.0, 60.0),
        },
        output_path,
    )


def plot_json_cbor_size(
    attribute_counts: list[int],
    envelope_sizes: dict[str, list[int]],
    output_path: str,
) -> None:
    figure, axis = plt.subplots(figsize=(8.5, 5.2))

    for format_name, label, color in (
        ("JSON", "JSON", AMBER),
        ("CBOR", "CBOR", VIOLET),
        ("CBORKeyAsInt", "CBOR (int keys)", TEAL),
    ):
        axis.plot(
            attribute_counts,
            envelope_sizes[format_name],
            label=label,
            color=color,
            marker="o",
            linewidth=1.8,
            markersize=5,
        )

    axis.set_title(
        "JSON vs. CBOR vs. CBOR (Int Keys): Envelope Size vs. Attribute Count",
        fontsize=13,
    )
    axis.set_xlabel("Attribute Count")
    axis.set_ylabel("Envelope size (bytes)")
    axis.set_ylim(bottom=0)
    configure_attribute_axis(attribute_counts, axis)
    axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_json_cbor_size_reduction(
    attribute_counts: list[int],
    reductions: dict[str, list[float]],
    output_path: str,
) -> None:
    positions = list(range(len(attribute_counts)))
    bar_width = 0.38
    figure, axis = plt.subplots(figsize=(8.5, 5.2))

    axis.bar(
        [position - bar_width / 2 for position in positions],
        reductions["CBOR"],
        width=bar_width,
        label="CBOR",
        color=VIOLET,
    )
    axis.bar(
        [position + bar_width / 2 for position in positions],
        reductions["CBORKeyAsInt"],
        width=bar_width,
        label="CBOR-int",
        color=TEAL,
    )

    axis.set_title("Envelope Size Reduction vs. JSON", fontsize=13)
    axis.set_xlabel("Attribute Count")
    axis.set_ylabel("Size Reduction vs JSON (%)")
    axis.set_yscale("linear")
    axis.set_ylim(0.0, 30.0)
    axis.set_xticks(positions)
    axis.set_xticklabels([str(attribute_count) for attribute_count in attribute_counts])
    axis.set_xlim(-0.6, len(positions) - 0.4)
    apply_mesh_grid(axis)
    axis.legend(fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)


def plot_json_cbor_energy(
    attribute_counts: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_json_cbor_results(
        attribute_counts,
        results,
        "JSON vs. CBOR vs. CBOR (Int Keys): Energy per Operation vs. Policy Attributes",
        "Energy (µJ/op) ± 95% CI",
        output_path,
    )


def plot_json_cbor_energy_reduction(
    attribute_counts: list[int],
    reductions: dict[tuple[str, str], list[float]],
    output_path: str,
) -> None:
    _plot_json_cbor_relative_results(
        attribute_counts,
        reductions,
        "Energy Reduction vs. JSON",
        "Energy Reduction vs JSON (%)",
        {
            "Serialize": (58.0, 70.0),
            "Deserialize": (89.0, 97.0),
        },
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
) -> None:
    figure, (latency_axis, size_axis) = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)
    _draw_summaries(latency_axis, parameter_values, latency_series, with_ci=True)
    if constant is not None:
        value, label, color = constant
        draw_constant(latency_axis, value, parameter_values, label, color)
    _draw_summaries(size_axis, parameter_values, size_series)
    _configure_parameter_axis(
        latency_axis, "Latency", "Latency (µs) ± 95% CI", parameter_values, x_label
    )
    _configure_parameter_axis(
        size_axis,
        "Sizes",
        "Size (bytes)",
        parameter_values,
        x_label,
    )
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
        "CP-ABE Scaling with Policy Attribute Count",
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
        f"RSA Scaling with Subscriber Count (Fixed Key: {fixed_rsa_key_bits} bits)",
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
    )


def plot_rsa_key_size_sensitivity(
    rsa_key_bits: list[int],
    results: dict,
    output_path: str,
) -> None:
    encrypt_latency_means, encrypt_latency_cis = results["encrypt_latency"]
    decrypt_latency_means, decrypt_latency_cis = results["decrypt_latency"]
    ciphertext_means, ciphertext_cis = results["ciphertext"]
    figure, (latency_axis, size_axis) = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle("RSA Key-Size Sensitivity (1 Subscriber)", fontsize=13)

    _draw_summaries(
        latency_axis,
        rsa_key_bits,
        [
            ("Encrypt", encrypt_latency_means, encrypt_latency_cis, AMBER),
            ("Decrypt", decrypt_latency_means, decrypt_latency_cis, VIOLET),
        ],
        with_ci=True,
    )
    _draw_summaries(
        size_axis,
        rsa_key_bits,
        [
            ("Ciphertext", ciphertext_means, ciphertext_cis, AMBER),
        ],
    )

    _configure_parameter_axis(
        latency_axis,
        "Encrypt + Decrypt Latency",
        "Latency (µs) ± 95% CI",
        rsa_key_bits,
        "",
    )
    _configure_parameter_axis(size_axis, "Sizes", "Size (bytes)", rsa_key_bits, "")
    figure.supxlabel("RSA Key Bits", fontsize=10)

    figure.tight_layout(rect=(0.0, 0.04, 1.0, 0.94))
    save_figure(figure, output_path)


def plot_cpabe_rsa_scaling_memory(
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
        axis.set_xticks(parameter_values)
        apply_value_grid(axis)

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


def plot_cpabe_rsa_scaling_energy(
    parameter_values_by_algorithm: dict[str, list[int]],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    fixed_rsa_key_bits: int,
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
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
        axis.set_xticks(values)
        apply_value_grid(axis)
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

    axes[0].set_ylabel("Energy (µJ/op) ± 95% CI")
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
    axis.set_ylabel("Publisher Encrypt Latency (µs)")
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

    largest_value = calculate_axis_top(cpabe_means, cpabe_cis)

    rsa_mean = results["rsa_mean"]
    rsa_ci = results["rsa_ci"]
    if not isnan(rsa_mean) and not isnan(rsa_ci):
        axis.hlines(
            rsa_mean,
            attribute_counts[0],
            attribute_counts[-1],
            color=TOTAL_CIPHERTEXT_COLOR,
            linestyle="--",
            linewidth=1.6,
            label=f'RSA-{results["fixed_rsa_key_bits"]}',
        )
        axis.errorbar(
            [attribute_counts[-1]],
            [rsa_mean],
            yerr=[rsa_ci],
            color=TOTAL_CIPHERTEXT_COLOR,
            fmt="none",
            capsize=4,
        )
        largest_value = max(largest_value, rsa_mean + rsa_ci)

    axis.set_xticks(attribute_counts)
    axis.set_xlim(0.0, float(attribute_counts[-1]) * AXIS_HEADROOM)
    axis.set_ylim(0.0, largest_value * 1.15)
    axis.set_xlabel("Policy Attributes")
    axis.set_ylabel("Decrypt Latency (µs) ± 95% CI")
    apply_value_grid(axis)
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
    axis.set_ylabel("Latency (µs)")
    axis.set_title("Encrypt vs Decrypt Asymmetry", fontsize=12)
    axis.grid(False)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(loc="upper center", ncol=2, frameon=False, fontsize=10)

    figure.tight_layout()
    save_figure(figure, output_path)
