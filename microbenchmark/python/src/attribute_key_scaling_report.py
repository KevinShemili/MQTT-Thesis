import sys
from dataclasses import dataclass, field

from reporting.benchmark import (
    CIPHERTEXT_BYTES,
    NS_PER_MICROSECOND,
    NS_PER_OP,
    STORED_KEY_BYTES,
    TOTAL_CIPHERTEXT_BYTES,
    BenchmarkMetrics,
    BenchmarkSpec,
    case_id,
    collect_means,
    collect_series,
    load_results,
    require_mean,
    require_mean_micros,
    sum_iterations,
    total_iterations,
)
from reporting.charts import (
    AMBER,
    BLUE,
    CRIMSON,
    TEAL,
    VIOLET,
    annotate_crossover,
    apply_value_grid,
    draw_error_series,
    draw_line_series,
    plt,
    save_figure,
)
from reporting.environment import (
    ScenarioPaths,
    parse_int_env,
    parse_int_list_env,
    resolve_paths,
)
from reporting.formatting import (
    format_attribute_label,
    format_byte_size,
    format_mean_with_ci,
)
from reporting.html import common_placeholders, render_report, render_table
from reporting.panels import series_maximum
from reporting.statistics import (
    LinearFit,
    fit_linear_regression,
    mean,
    mean_and_confidence_interval,
    student_t_critical_95,
)

SLUG = "attribute-key-scaling"
RESULT_DIR_VAR = "ATTRIBUTE_KEY_SCALING_RESULT_DIR"
TEMPLATE_NAME = "attribute_key_scaling_template.html"

CPABE_PLOT = "cpabe_attributes.png"
RSA_SUBSCRIBERS_PLOT = "rsa_subscribers.png"
RSA_KEY_BITS_PLOT = "rsa_key_bits.png"
BANDWIDTH_CROSSOVER_PLOT = "bandwidth_crossover.png"
ASYMMETRY_PLOT = "encrypt_decrypt_asymmetry.png"
ENCRYPT_CPU_CROSSOVER_PLOT = "encrypt_cpu_crossover.png"
DECRYPT_CPU_CROSSOVER_PLOT = "decrypt_cpu_crossover.png"

CPABE_ATTRIBUTES = "CPABEAttributes"
RSA_SUBSCRIBERS = "RSASubscribers"
RSA_KEY_BITS = "RSAKeyBits"
RSA_SUBSCRIBER_FIXED_KEY = "RSASubscriberFixedKey"

OPERATIONS = ["encrypt", "decrypt", "keygen"]
ENCRYPT_DECRYPT = ["encrypt", "decrypt"]

OPERATION_COLORS = {"encrypt": AMBER, "decrypt": VIOLET, "keygen": CRIMSON}
FALLBACK_COLOR = CRIMSON
TOTAL_CIPHERTEXT_COLOR = TEAL

RSA_KEY_BITS_COLORS = [TOTAL_CIPHERTEXT_COLOR, BLUE, AMBER, CRIMSON]

FANOUT_LARGEST_DIAMETER_PX = 168.0
FANOUT_SMALLEST_DIAMETER_PX = 22.0

CROSSOVER_FIGURE_SIZE = (8.5, 5.2)
ASYMMETRY_FIGURE_SIZE = (9, 5.5)

AXIS_HEADROOM = 1.03

SIZE_SERIES = (
    ("encrypt", CIPHERTEXT_BYTES, "Ciphertext", AMBER, True),
    (
        "encrypt",
        TOTAL_CIPHERTEXT_BYTES,
        "Ciphertext (TOTAL)",
        TOTAL_CIPHERTEXT_COLOR,
        False,
    ),
    ("keygen", STORED_KEY_BYTES, "Private Key", CRIMSON, False),
)

CIPHERTEXT_COLUMN = ("CIPHERTEXT", CIPHERTEXT_BYTES)
TOTAL_CIPHERTEXT_COLUMN = ("CIPHERTEXT (TOTAL)", TOTAL_CIPHERTEXT_BYTES)
STORED_KEY_COLUMN = ("STORED KEY", STORED_KEY_BYTES)

SPEC = BenchmarkSpec(
    prefix="BenchmarkAttributeKeyScaling",
    required_units=(NS_PER_OP,),
    optional_units=(CIPHERTEXT_BYTES, TOTAL_CIPHERTEXT_BYTES, STORED_KEY_BYTES),
)


@dataclass(frozen=True)
class Config:
    runs: int
    t_critical: float
    attribute_counts: list[int]
    subscriber_counts: list[int]
    rsa_key_bits: list[int]
    fixed_rsa_key_bits: int
    paths: ScenarioPaths

    @property
    def min_attributes(self) -> int:
        return self.attribute_counts[0]

    @property
    def max_attributes(self) -> int:
        return self.attribute_counts[-1]

    @property
    def max_subscribers(self) -> int:
        return self.subscriber_counts[-1]

    @property
    def fixed_key_decrypt_case(self) -> str:
        return case_id("decrypt", RSA_SUBSCRIBER_FIXED_KEY, self.fixed_rsa_key_bits)


def load_config() -> Config:
    runs = parse_int_env("ATTRIBUTE_KEY_SCALING_RUNS")

    return Config(
        runs=runs,
        t_critical=student_t_critical_95(runs - 1),
        attribute_counts=parse_int_list_env("ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT"),
        subscriber_counts=parse_int_list_env("ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT"),
        rsa_key_bits=parse_int_list_env("ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES"),
        fixed_rsa_key_bits=parse_int_env("ATTRIBUTE_KEY_SCALING_FIXED_RSA_KEY_BITS"),
        paths=resolve_paths(SLUG, RESULT_DIR_VAR, TEMPLATE_NAME),
    )


def operation_color(operation: str) -> str:
    return OPERATION_COLORS.get(operation, FALLBACK_COLOR)


def sweep_cases(operation: str, sweep_name: str, sweep_values: list[int]):
    return [(value, case_id(operation, sweep_name, value)) for value in sweep_values]


@dataclass
class CrossoverSummary:
    """Where RSA's per-subscriber bytes overtake one CP-ABE ciphertext."""

    measured_total_bytes: list[float] = field(default_factory=list)

    cpabe_bytes_min: float = 0.0
    cpabe_bytes_max: float = 0.0

    bytes_crossover_min: float = 0.0
    bytes_crossover_max: float = 0.0


@dataclass
class CpuCrossoverSummary:

    measured_encrypt_micros: list[float] = field(default_factory=list)

    rsa_encrypt_slope_micros_per_subscriber: float = 0.0
    rsa_encrypt_intercept_micros: float = 0.0

    rsa_decrypt_micros: float = 0.0

    cpabe_encrypt_micros_min: float = 0.0
    cpabe_encrypt_micros_max: float = 0.0
    cpabe_decrypt_micros_min: float = 0.0
    cpabe_decrypt_micros_max: float = 0.0

    encrypt_crossover_min: float = 0.0
    encrypt_crossover_max: float = 0.0

    decrypt_penalty_min: float = 0.0
    decrypt_penalty_max: float = 0.0


@dataclass(frozen=True)
class CpabeMarginalSlopes:

    encrypt: LinearFit
    decrypt: LinearFit
    key_issuance: LinearFit
    ciphertext: LinearFit
    stored_key: LinearFit


@dataclass(frozen=True)
class RsaSubscriberSlopes:

    encrypt: LinearFit

    total_ciphertext_slope_bytes: float


def compute_crossover_summary(
    results: dict[str, BenchmarkMetrics],
    config: Config,
) -> CrossoverSummary:

    summary = CrossoverSummary()

    for subscriber_count in config.subscriber_counts:

        metrics = results.get(case_id("encrypt", RSA_SUBSCRIBERS, subscriber_count))
        if metrics is None or len(metrics.samples(TOTAL_CIPHERTEXT_BYTES)) == 0:
            sys.exit(
                "[error] missing RSA subscriber sweep data for crossover synthesis"
            )

        summary.measured_total_bytes.append(
            mean(metrics.samples(TOTAL_CIPHERTEXT_BYTES))
        )

    rsa_single_bytes = require_mean(
        results,
        case_id("encrypt", RSA_SUBSCRIBERS, config.subscriber_counts[0]),
        CIPHERTEXT_BYTES,
        config.paths.bench_output,
        "ciphertext bytes for",
    )

    summary.cpabe_bytes_min = cpabe_ciphertext_bytes(
        results, config, config.min_attributes
    )
    summary.cpabe_bytes_max = cpabe_ciphertext_bytes(
        results, config, config.max_attributes
    )

    summary.bytes_crossover_min = summary.cpabe_bytes_min / rsa_single_bytes
    summary.bytes_crossover_max = summary.cpabe_bytes_max / rsa_single_bytes

    return summary


def cpabe_ciphertext_bytes(
    results: dict[str, BenchmarkMetrics],
    config: Config,
    attribute_count: int,
) -> float:
    return require_mean(
        results,
        case_id("encrypt", CPABE_ATTRIBUTES, attribute_count),
        CIPHERTEXT_BYTES,
        config.paths.bench_output,
        "ciphertext bytes for",
    )


def compute_cpu_crossover_summary(
    results: dict[str, BenchmarkMetrics],
    config: Config,
) -> CpuCrossoverSummary:

    summary = CpuCrossoverSummary()

    subscriber_values = [float(count) for count in config.subscriber_counts]
    summary.measured_encrypt_micros = [
        require_mean_micros(
            results,
            case_id("encrypt", RSA_SUBSCRIBERS, count),
            config.paths.bench_output,
        )
        for count in config.subscriber_counts
    ]

    summary.rsa_encrypt_slope_micros_per_subscriber = fit_linear_regression(
        subscriber_values, summary.measured_encrypt_micros
    ).slope

    summary.rsa_encrypt_intercept_micros = mean(
        summary.measured_encrypt_micros
    ) - summary.rsa_encrypt_slope_micros_per_subscriber * mean(subscriber_values)

    summary.rsa_decrypt_micros = require_mean_micros(
        results,
        case_id("decrypt", RSA_KEY_BITS, config.fixed_rsa_key_bits),
        config.paths.bench_output,
    )

    def cpabe_micros(operation: str, attribute_count: int) -> float:
        return require_mean_micros(
            results,
            case_id(operation, CPABE_ATTRIBUTES, attribute_count),
            config.paths.bench_output,
        )

    summary.cpabe_encrypt_micros_min = cpabe_micros("encrypt", config.min_attributes)
    summary.cpabe_encrypt_micros_max = cpabe_micros("encrypt", config.max_attributes)
    summary.cpabe_decrypt_micros_min = cpabe_micros("decrypt", config.min_attributes)
    summary.cpabe_decrypt_micros_max = cpabe_micros("decrypt", config.max_attributes)

    summary.encrypt_crossover_min = (
        summary.cpabe_encrypt_micros_min - summary.rsa_encrypt_intercept_micros
    ) / summary.rsa_encrypt_slope_micros_per_subscriber

    summary.encrypt_crossover_max = (
        summary.cpabe_encrypt_micros_max - summary.rsa_encrypt_intercept_micros
    ) / summary.rsa_encrypt_slope_micros_per_subscriber

    summary.decrypt_penalty_min = (
        summary.cpabe_decrypt_micros_min / summary.rsa_decrypt_micros
    )
    summary.decrypt_penalty_max = (
        summary.cpabe_decrypt_micros_max / summary.rsa_decrypt_micros
    )

    return summary


def compute_cpabe_marginal_slopes(
    results: dict[str, BenchmarkMetrics],
    config: Config,
) -> CpabeMarginalSlopes:

    def fit(operation: str, unit: str, divisor: float = 1.0) -> LinearFit:
        cases = sweep_cases(operation, CPABE_ATTRIBUTES, config.attribute_counts)
        return fit_linear_regression(*collect_means(results, cases, unit, divisor))

    return CpabeMarginalSlopes(
        encrypt=fit("encrypt", NS_PER_OP, NS_PER_MICROSECOND),
        decrypt=fit("decrypt", NS_PER_OP, NS_PER_MICROSECOND),
        key_issuance=fit("keygen", NS_PER_OP, NS_PER_MICROSECOND),
        ciphertext=fit("encrypt", CIPHERTEXT_BYTES),
        stored_key=fit("keygen", STORED_KEY_BYTES),
    )


def compute_rsa_subscriber_slopes(
    results: dict[str, BenchmarkMetrics],
    config: Config,
) -> RsaSubscriberSlopes:

    cases = sweep_cases("encrypt", RSA_SUBSCRIBERS, config.subscriber_counts)

    return RsaSubscriberSlopes(
        encrypt=fit_linear_regression(
            *collect_means(results, cases, NS_PER_OP, NS_PER_MICROSECOND)
        ),
        total_ciphertext_slope_bytes=require_mean(
            results,
            case_id("encrypt", RSA_SUBSCRIBERS, config.subscriber_counts[0]),
            CIPHERTEXT_BYTES,
            config.paths.bench_output,
            "ciphertext bytes for",
        ),
    )

def plot_sweep(
    results: dict[str, BenchmarkMetrics],
    config: Config,
    sweep_name: str,
    sweep_values: list[int],
    sweep_operations: list[str],
    x_label: str,
    figure_title: str,
    output_path: str,
    fixed_decrypt_case_id: str | None = None,
    split_keygen_latency: bool = False,
) -> None:

    if split_keygen_latency:
        figure = plt.figure(figsize=(13, 7))

        grid_spec = figure.add_gridspec(
            2,
            2,
            width_ratios=[1.0, 1.0],
            height_ratios=[1.0, 1.0],
            hspace=0.34,
        )

        keygen_latency_axis = figure.add_subplot(grid_spec[0, 0])
        latency_axis = figure.add_subplot(grid_spec[1, 0], sharex=keygen_latency_axis)
        size_axis = figure.add_subplot(grid_spec[:, 1])
    else:
        figure = plt.figure(figsize=(13, 5))
        grid_spec = figure.add_gridspec(1, 2)

        latency_axis = figure.add_subplot(grid_spec[0, 0])
        keygen_latency_axis = latency_axis
        size_axis = figure.add_subplot(grid_spec[0, 1])

    figure.suptitle(figure_title, fontsize=13)

    for operation in sweep_operations:

        cases = sweep_cases(operation, sweep_name, sweep_values)

        if operation == "decrypt" and fixed_decrypt_case_id is not None:
            cases = [(value, fixed_decrypt_case_id) for value, _ in cases]

        series = collect_series(
            results, cases, NS_PER_OP, config.t_critical, NS_PER_MICROSECOND
        )

        operation_axis = (
            keygen_latency_axis
            if split_keygen_latency and operation == "keygen"
            else latency_axis
        )

        draw_error_series(
            operation_axis, series, operation.capitalize(), operation_color(operation)
        )

    if split_keygen_latency:
        keygen_latency_axis.set_title("Key Generation Latency", fontsize=11)
        keygen_latency_axis.set_ylabel("Latency (µs) ± 95% CI")
        keygen_latency_axis.set_ylim(bottom=0)
        keygen_latency_axis.set_xticks(sweep_values)

        keygen_latency_axis.tick_params(axis="x", labelbottom=True)
        keygen_latency_axis.set_xlabel(x_label)

        apply_value_grid(keygen_latency_axis)
        keygen_latency_axis.legend(fontsize=10)

        latency_axis.set_title("Encrypt + Decrypt Latency", fontsize=11)
    else:
        latency_axis.set_title("Latency", fontsize=11)

    latency_axis.set_ylabel("Latency (µs) ± 95% CI")
    latency_axis.set_ylim(bottom=0)

    latency_axis.set_xticks(sweep_values)
    latency_axis.set_xlabel(x_label)
    apply_value_grid(latency_axis)
    latency_axis.legend(fontsize=10)

    for operation, unit, label, color, always_draw in SIZE_SERIES:

        x_values, sizes = collect_means(
            results, sweep_cases(operation, sweep_name, sweep_values), unit
        )

        if always_draw or len(x_values) > 0:
            draw_line_series(size_axis, x_values, sizes, label, color)

    size_axis.set_title("Sizes", fontsize=11)
    size_axis.set_ylabel("Size (bytes)")
    size_axis.set_xticks(sweep_values)
    size_axis.set_xlabel(x_label)
    apply_value_grid(size_axis)
    size_axis.legend(fontsize=10)
    size_axis.set_ylim(bottom=0)

    if split_keygen_latency:
        figure.subplots_adjust(top=0.92)
    else:
        figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))

    save_figure(figure, output_path)


def plot_bandwidth_crossover(
    summary: CrossoverSummary,
    config: Config,
) -> None:

    x_limit = config.max_subscribers

    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    draw_line_series(
        axis,
        config.subscriber_counts,  # type: ignore
        summary.measured_total_bytes,
        "RSA Scaling Subs",
        TOTAL_CIPHERTEXT_COLOR,
    )

    for level, attribute_count, color in (
        (summary.cpabe_bytes_min, config.min_attributes, AMBER),
        (summary.cpabe_bytes_max, config.max_attributes, CRIMSON),
    ):
        axis.hlines(
            level,
            1,
            x_limit,
            color=color,
            linewidth=1.8,
            label=f"CP-ABE, {format_attribute_label(attribute_count)}",
        )

    for crossover_value, level_value in (
        (summary.bytes_crossover_min, summary.cpabe_bytes_min),
        (summary.bytes_crossover_max, summary.cpabe_bytes_max),
    ):
        annotate_crossover(
            axis, crossover_value, level_value, f"≈{crossover_value:,.1f}"
        )

    linear_tick_values = [config.subscriber_counts[0]] + [
        count for count in config.subscriber_counts if count >= 8
    ]

    axis.set_xticks(linear_tick_values)
    axis.set_xlim(0.0, float(x_limit) * AXIS_HEADROOM)
    axis.set_xlabel("Subscribers")
    axis.set_ylabel("Ciphertext Bytes")
    axis.set_ylim(bottom=0.0)
    apply_value_grid(axis)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    save_figure(figure, config.paths.figure(BANDWIDTH_CROSSOVER_PLOT))


def plot_encrypt_cpu_crossover(
    summary: CpuCrossoverSummary,
    config: Config,
) -> None:

    x_limit = summary.encrypt_crossover_max * 1.15

    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    def projected_micros(subscribers: float) -> float:
        return (
            summary.rsa_encrypt_intercept_micros
            + summary.rsa_encrypt_slope_micros_per_subscriber * subscribers
        )

    projection_start_subscribers = float(config.max_subscribers)
    projection_end_micros = projected_micros(x_limit)

    axis.plot(
        [projection_start_subscribers, x_limit],
        [projected_micros(projection_start_subscribers), projection_end_micros],
        color=TOTAL_CIPHERTEXT_COLOR,
        linewidth=1.8,
        linestyle=":",
        label="RSA Linear Fit (Projected Beyond Sample)",
    )

    axis.plot(
        config.subscriber_counts,
        summary.measured_encrypt_micros,
        color=TOTAL_CIPHERTEXT_COLOR,
        marker="o",
        linewidth=2.6,
        markersize=5,
        label="RSA Scaling Subs (Measured)",
    )

    for level, attribute_count, color in (
        (summary.cpabe_encrypt_micros_min, config.min_attributes, AMBER),
        (summary.cpabe_encrypt_micros_max, config.max_attributes, CRIMSON),
    ):
        axis.hlines(
            level,
            0.0,
            x_limit,
            color=color,
            linewidth=1.8,
            label=f"CP-ABE, {format_attribute_label(attribute_count)}",
        )

    for crossover_value, level_value in (
        (summary.encrypt_crossover_min, summary.cpabe_encrypt_micros_min),
        (summary.encrypt_crossover_max, summary.cpabe_encrypt_micros_max),
    ):
        annotate_crossover(
            axis, crossover_value, level_value, f"≈{crossover_value:,.0f}"
        )

    largest_value = max(summary.cpabe_encrypt_micros_max, projection_end_micros)

    axis.set_xlim(0.0, x_limit)
    axis.set_ylim(0.0, largest_value * 1.12)
    axis.set_xlabel("Subscribers")
    axis.set_ylabel("Publisher Encrypt Latency (µs)")
    apply_value_grid(axis)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    save_figure(figure, config.paths.figure(ENCRYPT_CPU_CROSSOVER_PLOT))


def plot_decrypt_cpu_crossover(
    results: dict[str, BenchmarkMetrics],
    config: Config,
) -> None:

    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    cpabe_cases = sweep_cases("decrypt", CPABE_ATTRIBUTES, config.attribute_counts)

    for _, benchmark_case_id in cpabe_cases:
        if benchmark_case_id not in results:
            sys.exit(
                f"[error] missing benchmark case "
                f"'{benchmark_case_id}' in {config.paths.bench_output}"
            )

    cpabe_series = collect_series(
        results, cpabe_cases, NS_PER_OP, config.t_critical, NS_PER_MICROSECOND
    )

    draw_error_series(axis, cpabe_series, "CP-ABE", VIOLET, linewidth=2.0)

    largest_value = series_maximum([cpabe_series])

    for index, rsa_key_bits in enumerate(config.rsa_key_bits):

        benchmark_case_id = case_id("decrypt", RSA_KEY_BITS, rsa_key_bits)
        metrics = results.get(benchmark_case_id)

        if metrics is None:
            sys.exit(
                f"[error] missing benchmark case "
                f"'{benchmark_case_id}' in {config.paths.bench_output}"
            )

        latency_mean, latency_ci = mean_and_confidence_interval(
            metrics.ns_per_op, config.t_critical
        )

        rsa_mean_micros = latency_mean / NS_PER_MICROSECOND
        rsa_ci_micros = latency_ci / NS_PER_MICROSECOND
        rsa_color = RSA_KEY_BITS_COLORS[index % len(RSA_KEY_BITS_COLORS)]

        axis.hlines(
            rsa_mean_micros,
            config.min_attributes,
            config.max_attributes,
            color=rsa_color,
            linestyle="--",
            linewidth=1.6,
            label=f"RSA-{rsa_key_bits}",
        )

        axis.errorbar(
            [config.max_attributes],
            [rsa_mean_micros],
            yerr=[rsa_ci_micros],
            color=rsa_color,
            fmt="none",
            capsize=4,
        )

        largest_value = max(largest_value, rsa_mean_micros + rsa_ci_micros)

    axis.set_xticks(config.attribute_counts)
    axis.set_xlim(0.0, float(config.max_attributes) * AXIS_HEADROOM)
    axis.set_ylim(0.0, largest_value * 1.15)
    axis.set_xlabel("Policy Attributes")
    axis.set_ylabel("Decrypt Latency (µs) ± 95% CI")
    apply_value_grid(axis)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    save_figure(figure, config.paths.figure(DECRYPT_CPU_CROSSOVER_PLOT))


def plot_encrypt_decrypt_asymmetry(
    results: dict[str, BenchmarkMetrics],
    config: Config,
) -> None:

    def micros(operation: str, sweep_name: str, sweep_value: int) -> float:
        return require_mean_micros(
            results,
            case_id(operation, sweep_name, sweep_value),
            config.paths.bench_output,
        )

    scheme_labels = [
        f"RSA-{config.fixed_rsa_key_bits}",
        f"CP-ABE ({format_attribute_label(config.min_attributes)})",
    ]
    encrypt_values = [
        micros("encrypt", RSA_KEY_BITS, config.fixed_rsa_key_bits),
        micros("encrypt", CPABE_ATTRIBUTES, config.min_attributes),
    ]
    decrypt_values = [
        micros("decrypt", RSA_KEY_BITS, config.fixed_rsa_key_bits),
        micros("decrypt", CPABE_ATTRIBUTES, config.min_attributes),
    ]

    figure, axis = plt.subplots(figsize=ASYMMETRY_FIGURE_SIZE)

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

        if encrypt_values[index] >= decrypt_values[index]:
            ratio_text = f"Encrypt is {encrypt_values[index] / decrypt_values[index]:.0f}× Slower"
        else:
            ratio_text = f"Decrypt is {decrypt_values[index] / encrypt_values[index]:.0f}× Slower"

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
    save_figure(figure, config.paths.figure(ASYMMETRY_PLOT))


def build_sweep_table(
    results: dict[str, BenchmarkMetrics],
    config: Config,
    sweep_name: str,
    sweep_values: list[int],
    operation: str,
    value_header: str,
    size_columns: tuple[tuple[str, str], ...] = (),
    fixed_benchmark_case_id: str | None = None,
) -> str:

    rows = []

    for sweep_value in sweep_values:

        # Display one measured fixed-key result for every subscriber count.
        benchmark_case_id = fixed_benchmark_case_id or case_id(
            operation, sweep_name, sweep_value
        )

        metrics = results.get(benchmark_case_id)
        if metrics is None:
            continue

        latency_mean, latency_ci = mean_and_confidence_interval(
            metrics.ns_per_op, config.t_critical
        )

        size_cells = [
            (
                format_byte_size(int(round(mean(metrics.samples(unit)))))
                if len(metrics.samples(unit)) > 0
                else "—"
            )
            for _, unit in size_columns
        ]

        rows.append(
            [
                str(sweep_value),
                format_mean_with_ci(
                    latency_mean / NS_PER_MICROSECOND, latency_ci / NS_PER_MICROSECOND
                ),
                *size_cells,
                f"{sum_iterations(metrics):,}",
            ]
        )

    return render_table(
        [
            value_header.upper(),
            "LATENCY (µs/op)",
            *[header for header, _ in size_columns],
            f"ITERS (Σ{config.runs} RUNS)",
        ],
        rows,
    )


def build_fanout_placeholders(
    results: dict[str, BenchmarkMetrics],
    config: Config,
) -> dict[str, str]:

    fanout_case_id = case_id("encrypt", RSA_SUBSCRIBERS, config.max_subscribers)

    single_bytes = require_mean(
        results,
        fanout_case_id,
        CIPHERTEXT_BYTES,
        config.paths.bench_output,
        "ciphertext bytes for",
    )
    total_bytes = require_mean(
        results,
        fanout_case_id,
        TOTAL_CIPHERTEXT_BYTES,
        config.paths.bench_output,
        "total ciphertext bytes for",
    )

    single_diameter_px = max(
        FANOUT_SMALLEST_DIAMETER_PX,
        FANOUT_LARGEST_DIAMETER_PX * (single_bytes / total_bytes) ** 0.5,
    )

    def circle_style(diameter_px: float) -> str:
        return f'style="width:{diameter_px:.0f}px;height:{diameter_px:.0f}px;"'

    return {
        "FanoutSingleBytes": format_byte_size(int(round(single_bytes))),
        "FanoutTotalBytes": format_byte_size(int(round(total_bytes))),
        "FanoutMultiplier": f"{total_bytes / single_bytes:.0f}",
        "FanoutSingleStyle": circle_style(single_diameter_px),
        "FanoutTotalStyle": circle_style(FANOUT_LARGEST_DIAMETER_PX),
    }


def write_html_report(
    results: dict[str, BenchmarkMetrics],
    config: Config,
    crossover_summary: CrossoverSummary,
    cpu_crossover_summary: CpuCrossoverSummary,
) -> None:

    cpabe = compute_cpabe_marginal_slopes(results, config)
    rsa = compute_rsa_subscriber_slopes(results, config)

    def micros_slope(fit: LinearFit) -> str:
        return f"+{format_mean_with_ci(fit.slope, fit.slope_ci, decimals=0)} µs"

    def bytes_slope(fit: LinearFit) -> str:
        return f"+{format_mean_with_ci(fit.slope, fit.slope_ci, decimals=0, thousands=False)} B"

    def table(
        sweep_name, sweep_values, operation, value_header, *size_columns, fixed=None
    ):
        return build_sweep_table(
            results,
            config,
            sweep_name,
            sweep_values,
            operation,
            value_header,
            size_columns,
            fixed,
        )

    placeholders = {
        **common_placeholders(
            config.runs, config.t_critical, total_iterations(results)
        ),
        **build_fanout_placeholders(results, config),
        "CpabeEncryptTable": table(
            CPABE_ATTRIBUTES,
            config.attribute_counts,
            "encrypt",
            "Attributes",
            CIPHERTEXT_COLUMN,
        ),
        "CpabeDecryptTable": table(
            CPABE_ATTRIBUTES,
            config.attribute_counts,
            "decrypt",
            "Attributes",
        ),
        "CpabeKeygenTable": table(
            CPABE_ATTRIBUTES,
            config.attribute_counts,
            "keygen",
            "Attributes",
            STORED_KEY_COLUMN,
        ),
        "RsaSubscribersEncryptTable": table(
            RSA_SUBSCRIBERS,
            config.subscriber_counts,
            "encrypt",
            "Subscribers",
            CIPHERTEXT_COLUMN,
            TOTAL_CIPHERTEXT_COLUMN,
        ),
        "RsaSubscribersDecryptTable": table(
            RSA_SUBSCRIBERS,
            config.subscriber_counts,
            "decrypt",
            "Subscribers",
            fixed=config.fixed_key_decrypt_case,
        ),
        "RsaKeyBitsEncryptTable": table(
            RSA_KEY_BITS,
            config.rsa_key_bits,
            "encrypt",
            "Key Bits",
            CIPHERTEXT_COLUMN,
        ),
        "RsaKeyBitsDecryptTable": table(
            RSA_KEY_BITS,
            config.rsa_key_bits,
            "decrypt",
            "Key Bits",
        ),
        "RsaKeyBitsKeygenTable": table(
            RSA_KEY_BITS,
            config.rsa_key_bits,
            "keygen",
            "Key Bits",
            STORED_KEY_COLUMN,
        ),
        "MinAttributeLabel": format_attribute_label(config.min_attributes),
        "MaxAttributeLabel": format_attribute_label(config.max_attributes),
        "MaxSubscriberCount": str(config.max_subscribers),
        "FixedRsaKeyBits": str(config.fixed_rsa_key_bits),
        "CpabePlot": CPABE_PLOT,
        "RsaSubscribersPlot": RSA_SUBSCRIBERS_PLOT,
        "RsaKeyBitsPlot": RSA_KEY_BITS_PLOT,
        "BandwidthCrossoverPlot": BANDWIDTH_CROSSOVER_PLOT,
        "AsymmetryPlot": ASYMMETRY_PLOT,
        "EncryptCpuCrossoverPlot": ENCRYPT_CPU_CROSSOVER_PLOT,
        "DecryptCpuCrossoverPlot": DECRYPT_CPU_CROSSOVER_PLOT,
        "CpabeEncryptSlope": micros_slope(cpabe.encrypt),
        "CpabeDecryptSlope": micros_slope(cpabe.decrypt),
        "CpabeKeyIssuanceSlope": micros_slope(cpabe.key_issuance),
        "CpabeCiphertextSlope": bytes_slope(cpabe.ciphertext),
        "CpabeStoredKeySlope": bytes_slope(cpabe.stored_key),
        "CpabeEncryptRSquared": f"{cpabe.encrypt.r_squared:.6f}",
        "CpabeDecryptRSquared": f"{cpabe.decrypt.r_squared:.6f}",
        "CpabeKeyIssuanceRSquared": f"{cpabe.key_issuance.r_squared:.6f}",
        "CpabeCiphertextRSquared": f"{cpabe.ciphertext.r_squared:.6f}",
        "CpabeStoredKeyRSquared": f"{cpabe.stored_key.r_squared:.6f}",
        "RsaSubscriberEncryptSlope": (
            f"+{format_mean_with_ci(rsa.encrypt.slope, rsa.encrypt.slope_ci)} µs"
        ),
        "RsaSubscriberTotalCiphertextSlope": (
            f"+{rsa.total_ciphertext_slope_bytes:.0f} B"
        ),
        "RsaSubscriberEncryptRSquared": f"{rsa.encrypt.r_squared:.6f}",

        "BytesCrossoverLow": f"{crossover_summary.bytes_crossover_min:,.1f}",
        "BytesCrossoverHigh": f"{crossover_summary.bytes_crossover_max:,.1f}",
        "BytesRsaThroughMin": f"{int(crossover_summary.bytes_crossover_min):,}",
        "BytesRsaThroughMax": f"{int(crossover_summary.bytes_crossover_max):,}",
        "EncryptCpuCrossoverLow": f"{cpu_crossover_summary.encrypt_crossover_min:,.0f}",
        "EncryptCpuCrossoverHigh": f"{cpu_crossover_summary.encrypt_crossover_max:,.0f}",
        "CpuRsaThroughMin": f"{int(cpu_crossover_summary.encrypt_crossover_min):,}",
        "CpuRsaThroughMax": f"{int(cpu_crossover_summary.encrypt_crossover_max):,}",
        "DecryptPenaltyMin": f"{cpu_crossover_summary.decrypt_penalty_min:,.1f}",
        "DecryptPenaltyMax": f"{cpu_crossover_summary.decrypt_penalty_max:,.1f}",
    }

    render_report(config.paths.template, config.paths.report, placeholders)


def main() -> None:
    config = load_config()
    results = load_results(config.paths.bench_output, SPEC)

    plot_sweep(
        results,
        config,
        CPABE_ATTRIBUTES,
        config.attribute_counts,
        OPERATIONS,
        "Policy Attributes",
        "CP-ABE Scaling with Policy Attribute Count",
        config.paths.figure(CPABE_PLOT),
    )

    plot_sweep(
        results,
        config,
        RSA_SUBSCRIBERS,
        config.subscriber_counts,
        ENCRYPT_DECRYPT,
        "Subscribers",
        f"RSA Scaling with Subscriber Count (Fixed Key: {config.fixed_rsa_key_bits} bits)",
        config.paths.figure(RSA_SUBSCRIBERS_PLOT),
        fixed_decrypt_case_id=config.fixed_key_decrypt_case,
    )

    plot_sweep(
        results,
        config,
        RSA_KEY_BITS,
        config.rsa_key_bits,
        OPERATIONS,
        "RSA Key Bits",
        "RSA Scaling with Key Size (1 Subscriber)",
        config.paths.figure(RSA_KEY_BITS_PLOT),
        split_keygen_latency=True,
    )

    crossover_summary = compute_crossover_summary(results, config)

    cpu_crossover_summary = compute_cpu_crossover_summary(results, config)

    plot_bandwidth_crossover(crossover_summary, config)
    plot_encrypt_cpu_crossover(cpu_crossover_summary, config)
    plot_decrypt_cpu_crossover(results, config)
    plot_encrypt_decrypt_asymmetry(results, config)

    write_html_report(results, config, crossover_summary, cpu_crossover_summary)


if __name__ == "__main__":
    main()
