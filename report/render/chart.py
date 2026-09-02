import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from report.render import formatting

from matplotlib.axes import Axes
from matplotlib.figure import Figure
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
RSA_KEY_BITS_COLORS = [TOTAL_CIPHERTEXT_COLOR, BLUE, AMBER, CRIMSON]


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


def draw_distribution(
    axis: Axes,
    parameter_values: list[int],
    medians: list[float],
    minimums: list[float],
    maximums: list[float],
    first_quartiles: list[float],
    third_quartiles: list[float],
    label: str,
    color: str,
) -> None:
    quartile_errors = [
        [median - lower for median, lower in zip(medians, first_quartiles)],
        [upper - median for median, upper in zip(medians, third_quartiles)],
    ]
    axis.vlines(
        parameter_values,
        minimums,
        maximums,
        color=color,
        linewidth=0.9,
        alpha=0.55,
    )

    axis.errorbar(
        parameter_values,
        medians,
        yerr=quartile_errors,
        label=label,
        color=color,
        marker="o",
        linewidth=1.8,
        markersize=5,
        capsize=6,
        elinewidth=4.5,
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


def _draw_zoom(
    axis: Axes,
    parameter_values: list[int],
    series: list[tuple[str, list[float], list[float], str]],
) -> None:
    zoom_axis = axis.inset_axes([0.08, 0.08, 0.47, 0.32])  # type: ignore
    for label, means, confidence_intervals, color in series:
        draw_summary(
            zoom_axis,
            parameter_values,
            means,
            confidence_intervals,
            label,
            color,
            linewidth=1.6,
            markersize=4,
            capsize=3,
        )

    zoom_axis.set_ylim(
        0.0,
        max(
            calculate_axis_top(means, confidence_intervals)
            for _, means, confidence_intervals, _ in series
        )
        * 1.10,
    )
    zoom_axis.set_xlim(0, parameter_values[-1] * AXIS_HEADROOM)
    zoom_axis.set_xticks([])
    zoom_axis.set_title("PSK + RSA Zoom", fontsize=9)
    zoom_axis.set_ylabel("µs", fontsize=8)
    zoom_axis.tick_params(axis="both", labelsize=8)
    apply_value_grid(zoom_axis, linewidth=0.4)
    zoom_axis.legend(fontsize=8, loc="upper left")


def _plot_operation_comparison(
    parameter_values: list[int],
    panels: list[tuple[str, list[tuple[str, list[float], list[float], str]]]],
    title: str,
    x_label: str,
    y_label: str,
    output_path: str,
    byte_tick_step: int | None = None,
    legend_location: str | None = None,
    zoom_first_panel: bool = False,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(title, fontsize=13)

    for index, (axis, (operation, series)) in enumerate(zip(axes, panels)):
        _draw_summaries(axis, parameter_values, series, with_ci=True)
        axis.set_title(operation, fontsize=11)
        axis.set_xlabel(x_label)
        axis.set_ylabel(y_label)
        axis.set_ylim(bottom=0)

        if byte_tick_step is None:
            configure_attribute_axis(parameter_values, axis)
        else:
            configure_byte_axis(axis, parameter_values[-1], byte_tick_step)

        legend_options = {"fontsize": 10}
        if legend_location is not None:
            legend_options["loc"] = legend_location
        axis.legend(**legend_options)

        if zoom_first_panel and index == 0:
            _draw_zoom(axis, parameter_values, series[:2])

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
) -> None:
    panels = []

    for operation in ("Encrypt", "Decrypt"):
        series = []

        for algorithm, color in (("AES-GCM", AMBER), ("ASCON", VIOLET)):
            means, confidence_intervals = results[(algorithm, operation)]
            series.append((algorithm, means, confidence_intervals, color))

        panels.append((operation, series))

    _plot_operation_comparison(
        payload_sizes,
        panels,
        title,
        "Payload size",
        y_label,
        output_path,
        byte_tick_step=16 * KILOBYTE,
    )


def plot_aes_ascon_latency(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_aes_ascon_results(
        payload_sizes,
        results,
        "AES-GCM vs. ASCON: Latency vs. Payload Size",
        "Latency (µs) ± 95% CI",
        output_path,
    )


def plot_aes_ascon_throughput(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_aes_ascon_results(
        payload_sizes,
        results,
        "AES-GCM vs. ASCON: Throughput vs. Payload Size",
        "Throughput (MB/s) ± 95% CI",
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
        "Energy (µJ/op) ± 95% CI",
        output_path,
    )


def _plot_payload_scaling_results(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    title: str,
    y_label: str,
    output_path: str,
    zoom_first_panel: bool = False,
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

    _plot_operation_comparison(
        payload_sizes,
        panels,
        title,
        "Payload Size",
        y_label,
        output_path,
        byte_tick_step=4 * MEGABYTE,
        legend_location="upper left",
        zoom_first_panel=zoom_first_panel,
    )


def plot_payload_scaling_latency(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_payload_scaling_results(
        payload_sizes,
        results,
        "PSK vs. RSA vs. CP-ABE: Latency vs. Payload Size",
        "Latency (µs) ± 95% CI",
        output_path,
        zoom_first_panel=True,
    )


def plot_payload_scaling_throughput(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_payload_scaling_results(
        payload_sizes,
        results,
        "PSK vs. RSA vs. CP-ABE: Throughput vs. Payload Size",
        "Throughput (MB/s) ± 95% CI",
        output_path,
    )


def plot_payload_scaling_energy(
    payload_sizes: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_payload_scaling_results(
        payload_sizes,
        results,
        "PSK vs. RSA vs. CP-ABE: Energy per Operation vs. Payload Size",
        "Energy (µJ/op) ± 95% CI",
        output_path,
        zoom_first_panel=True,
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


def plot_json_cbor_latency(
    attribute_counts: list[int],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    _plot_json_cbor_results(
        attribute_counts,
        results,
        "JSON vs. CBOR vs. CBOR (Int Keys): Latency vs. Policy Attributes",
        "Latency (µs) ± 95% CI",
        output_path,
    )


def plot_json_cbor_size(
    attribute_counts: list[int],
    results: dict[str, tuple[list[float], list[float], list[float]]],
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=PANEL_FIGURE_SIZE)
    figure.suptitle(
        "JSON vs. CBOR vs. CBOR (Int Keys): Envelope Size vs. Attribute Count",
        fontsize=13,
    )

    for format_name, label, color in (
        ("JSON", "JSON", AMBER),
        ("CBOR", "CBOR", VIOLET),
        ("CBORKeyAsInt", "CBOR (int keys)", TEAL),
    ):
        envelope_means, envelope_cis, overhead_bytes = results[format_name]

        draw_summary(
            axes[0],
            attribute_counts,
            envelope_means,
            envelope_cis,
            label,
            color,
            with_ci=True,
        )

        axes[1].plot(
            attribute_counts,
            overhead_bytes,
            label=label,
            color=color,
            marker="o",
            linewidth=1.8,
            markersize=5,
        )

    for axis, title, y_label in (
        (axes[0], "Absolute Size", "Envelope size (bytes)"),
        (axes[1], "Format Tax", "Bytes added over raw payload"),
    ):
        axis.set_title(title, fontsize=11)
        axis.set_xlabel("Attribute Count")
        axis.set_ylabel(y_label)
        axis.set_ylim(bottom=0)
        configure_attribute_axis(attribute_counts, axis)
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


def plot_rsa_key_bits(
    rsa_key_bits: list[int],
    results: dict,
    output_path: str,
) -> None:
    keygen = results["keygen"]
    encrypt_latency_means, encrypt_latency_cis = results["encrypt_latency"]
    decrypt_latency_means, decrypt_latency_cis = results["decrypt_latency"]
    ciphertext_means, ciphertext_cis = results["ciphertext"]
    stored_key_means, stored_key_cis = results["stored_key"]
    figure = plt.figure(figsize=(13, 7))
    grid_spec = figure.add_gridspec(2, 2, hspace=0.34)
    keygen_latency_axis = figure.add_subplot(grid_spec[0, 0])
    latency_axis = figure.add_subplot(grid_spec[1, 0], sharex=keygen_latency_axis)
    size_axis = figure.add_subplot(grid_spec[:, 1])
    figure.suptitle("RSA Scaling with Key Size (1 Subscriber)", fontsize=13)

    draw_distribution(
        keygen_latency_axis,
        rsa_key_bits,
        keygen["medians"],
        keygen["minimums"],
        keygen["maximums"],
        keygen["first_quartiles"],
        keygen["third_quartiles"],
        "Keygen",
        CRIMSON,
    )

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
            ("Private Key", stored_key_means, stored_key_cis, CRIMSON),
        ],
    )

    keygen_latency_axis.set_title("Key Generation Latency", fontsize=11)
    keygen_latency_axis.set_ylabel("Latency (ms), Median + IQR + Min-Max")
    keygen_latency_axis.set_ylim(bottom=0)
    keygen_latency_axis.set_xticks(rsa_key_bits)
    keygen_latency_axis.tick_params(axis="x", labelbottom=True)
    keygen_latency_axis.set_xlabel("RSA Key Bits")
    apply_value_grid(keygen_latency_axis)
    keygen_latency_axis.legend(fontsize=10)

    _configure_parameter_axis(
        latency_axis,
        "Encrypt + Decrypt Latency",
        "Latency (µs) ± 95% CI",
        rsa_key_bits,
        "RSA Key Bits",
    )
    _configure_parameter_axis(
        size_axis, "Sizes", "Size (bytes)", rsa_key_bits, "RSA Key Bits"
    )

    figure.subplots_adjust(top=0.92)
    save_figure(figure, output_path)


def plot_attribute_key_scaling_memory(
    parameter_values_by_algorithm: dict[str, list[int]],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    fixed_rsa_key_bits: int,
    subscriber_decrypt_reference: float,
    output_path: str,
) -> None:
    attribute_counts = parameter_values_by_algorithm["CPABEAttributes"]
    subscriber_counts = parameter_values_by_algorithm["RSASubscribers"]
    rsa_key_bits = parameter_values_by_algorithm["RSAKeyBits"]
    cpabe_encrypt_means, cpabe_encrypt_cis = results[("CPABEAttributes", "Encrypt")]
    cpabe_decrypt_means, cpabe_decrypt_cis = results[("CPABEAttributes", "Decrypt")]
    subscriber_encrypt_means, subscriber_encrypt_cis = results[
        ("RSASubscribers", "Encrypt")
    ]
    rsa_encrypt_means, rsa_encrypt_cis = results[("RSAKeyBits", "Encrypt")]
    rsa_decrypt_means, rsa_decrypt_cis = results[("RSAKeyBits", "Decrypt")]
    figure, axes = plt.subplots(1, 3, figsize=(14, 4.6), sharey=True)
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
        (
            axes[2],
            rsa_key_bits,
            "RSA Key Size",
            "RSA Key Bits",
            [
                ("Encrypt", rsa_encrypt_means, rsa_encrypt_cis, AMBER),
                ("Decrypt", rsa_decrypt_means, rsa_decrypt_cis, VIOLET),
            ],
        ),
    ]
    for axis, parameter_values, title, x_label, series in panels:
        _draw_summaries(axis, parameter_values, series, with_ci=True)
        if axis is axes[1]:
            draw_constant(
                axis,
                subscriber_decrypt_reference,
                subscriber_counts,
                f"Decrypt (RSA-{fixed_rsa_key_bits})",
                VIOLET,
            )
        axis.set_title(title, fontsize=11)
        axis.set_xlabel(x_label)
        axis.set_xticks(parameter_values)
        apply_value_grid(axis)
        axis.legend(fontsize=9)

    axes[0].set_ylabel("Peak RSS (MB) ± 95% CI")

    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    save_figure(figure, output_path)


def plot_attribute_key_scaling_energy(
    parameter_values_by_algorithm: dict[str, list[int]],
    results: dict[tuple[str, str], tuple[list[float], list[float]]],
    output_path: str,
) -> None:
    figure, axes = plt.subplots(1, 3, figsize=(14, 4.6))
    figure.suptitle(
        "Energy per Operation by Attribute Count, Subscriber Count, and RSA Key Bits",
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
        (
            axes[2],
            parameter_values_by_algorithm["RSAKeyBits"],
            "RSA Key Size",
            "RSA Key Bits",
            (
                ("Encrypt", "RSAKeyBits", "Encrypt", AMBER),
                ("Decrypt", "RSAKeyBits", "Decrypt", VIOLET),
                ("Key Generation", "RSAKeyBits", "KeyGen", CRIMSON),
            ),
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

    for index, (rsa_key_bits, rsa_mean, rsa_ci) in enumerate(
        zip(
            results["rsa_key_bits"],
            results["rsa_means"],
            results["rsa_cis"],
            strict=True,
        )
    ):
        if isnan(rsa_mean) or isnan(rsa_ci):
            continue

        rsa_color = RSA_KEY_BITS_COLORS[index % len(RSA_KEY_BITS_COLORS)]

        axis.hlines(
            rsa_mean,
            attribute_counts[0],
            attribute_counts[-1],
            color=rsa_color,
            linestyle="--",
            linewidth=1.6,
            label=f"RSA-{rsa_key_bits}",
        )
        axis.errorbar(
            [attribute_counts[-1]],
            [rsa_mean],
            yerr=[rsa_ci],
            color=rsa_color,
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
