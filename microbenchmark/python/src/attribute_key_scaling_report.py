from dataclasses import dataclass

from reporting.benchmark import (
    CIPHERTEXT_BYTES,
    NS_PER_MICROSECOND,
    NS_PER_OP,
    STORED_KEY_BYTES,
    TOTAL_CIPHERTEXT_BYTES,
    BenchmarkSummary,
    FeatureSweep,
    load_results,
)
from reporting.charts import (
    AMBER,
    AXIS_HEADROOM,
    BLUE,
    CRIMSON,
    TEAL,
    VIOLET,
    mark_crossover,
    apply_value_grid,
    draw_summary,
    plt,
    save_figure,
    calculate_axis_top,
)
from reporting.environment import (
    FilePaths,
    parse_int_env,
    parse_int_list_env,
    resolve_paths,
)
from reporting.formatting import (
    format_byte_size,
    format_mean_with_ci,
)
from reporting.html import build_html_generic_data, build_html_report, build_html_table
from reporting.statistics import (
    LinearFit,
    fit_linear_regression,
    get_student_t_critical_95,
)

SCENARIO = "attribute-key-scaling"
BENCHMARK_PREFIX = "BenchmarkAttributeKeyScaling"
TEMPLATE_NAME = "attribute_key_scaling_template.html"

CPABE_PLOT = "cpabe_attributes.png"
RSA_SUBSCRIBERS_PLOT = "rsa_subscribers.png"
RSA_KEY_BITS_PLOT = "rsa_key_bits.png"
CIPHERTEXT_SIZE_CROSSOVER_PLOT = "ciphertext_size_crossover.png"
ASYMMETRY_PLOT = "encrypt_decrypt_asymmetry.png"
ENCRYPT_LATENCY_CROSSOVER_PLOT = "encrypt_latency_crossover.png"
DECRYPT_LATENCY_CROSSOVER_PLOT = "decrypt_latency_crossover.png"

CPABE_ATTRIBUTES = "CPABEAttributes"
RSA_SUBSCRIBERS = "RSASubscribers"
RSA_KEY_BITS = "RSAKeyBits"

OPERATIONS = ["encrypt", "decrypt", "keygen"]
ENCRYPT_DECRYPT = ["encrypt", "decrypt"]

OPERATION_COLORS = {"encrypt": AMBER, "decrypt": VIOLET, "keygen": CRIMSON}
TOTAL_CIPHERTEXT_COLOR = TEAL

RSA_KEY_BITS_COLORS = [TOTAL_CIPHERTEXT_COLOR, BLUE, AMBER, CRIMSON]

FANOUT_LARGEST_DIAMETER_PX = 168.0
FANOUT_SMALLEST_DIAMETER_PX = 22.0

CROSSOVER_FIGURE_SIZE = (8.5, 5.2)
ASYMMETRY_FIGURE_SIZE = (9, 5.5)


# One size metric drawn on the "Sizes" panel of a sweep figure
@dataclass(frozen=True)
class SizeSeries:
    operation: str
    unit: str
    label: str
    color: str


CIPHERTEXT_SERIES = SizeSeries("encrypt", CIPHERTEXT_BYTES, "Ciphertext", AMBER)
TOTAL_CIPHERTEXT_SERIES = SizeSeries(
    "encrypt", TOTAL_CIPHERTEXT_BYTES, "Ciphertext (TOTAL)", TOTAL_CIPHERTEXT_COLOR
)
STORED_KEY_SERIES = SizeSeries("keygen", STORED_KEY_BYTES, "Private Key", CRIMSON)

CIPHERTEXT_COLUMN = ("CIPHERTEXT", CIPHERTEXT_BYTES)
TOTAL_CIPHERTEXT_COLUMN = ("CIPHERTEXT (TOTAL)", TOTAL_CIPHERTEXT_BYTES)
STORED_KEY_COLUMN = ("STORED KEY", STORED_KEY_BYTES)


# Stores all configuration needed to process attribute key scaling benchmark
@dataclass(frozen=True)
class Config:
    runs: int
    t_critical: float
    attribute_counts: list[int]
    subscriber_counts: list[int]
    rsa_key_bits: list[int]
    fixed_rsa_key_bits: int
    paths: FilePaths

    @property
    def min_attributes(self) -> int:
        return self.attribute_counts[0]

    @property
    def max_attributes(self) -> int:
        return self.attribute_counts[-1]

    @property
    def max_subscribers(self) -> int:
        return self.subscriber_counts[-1]


def load_config() -> Config:
    runs = parse_int_env("ATTRIBUTE_KEY_SCALING_RUNS")

    return Config(
        runs=runs,
        t_critical=get_student_t_critical_95(runs - 1),
        attribute_counts=parse_int_list_env("ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT"),
        subscriber_counts=parse_int_list_env("ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT"),
        rsa_key_bits=parse_int_list_env("ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES"),
        fixed_rsa_key_bits=parse_int_env("ATTRIBUTE_KEY_SCALING_FIXED_RSA_KEY_BITS"),
        paths=resolve_paths(SCENARIO, TEMPLATE_NAME),
    )


def format_attribute_label(attribute_count: int) -> str:
    if attribute_count == 1:
        return "1 ATTRIBUTE"

    return f"{attribute_count} ATTRIBUTES"


# CP-ABE's cost as a straight line in the policy attribute count
@dataclass(frozen=True)
class CPABEFittedSlopes:
    encrypt: LinearFit
    decrypt: LinearFit
    key_issuance: LinearFit
    ciphertext: LinearFit
    stored_key: LinearFit


# Where RSA's per-subscriber ciphertext growth overtakes CP-ABE's fixed ciphertext
@dataclass(frozen=True)
class CiphertextSizeCrossover:
    rsa_total_bytes: FeatureSweep
    cpabe_bytes_min: float
    cpabe_bytes_max: float
    crossover_min: float
    crossover_max: float


# Where RSA's per-subscriber encrypt cost overtakes CP-ABE's fixed encrypt cost,
# plus the decrypt cost CP-ABE pays in exchange
@dataclass(frozen=True)
class LatencyCrossover:
    rsa_encrypt_micros: FeatureSweep
    rsa_encrypt_fit: LinearFit
    cpabe_encrypt_micros_min: float
    cpabe_encrypt_micros_max: float
    crossover_min: float
    crossover_max: float
    decrypt_penalty_min: float
    decrypt_penalty_max: float


# Everything derived from the parsed benchmark output, computed once and shared
# by the figures and the HTML report
@dataclass(frozen=True)
class Analysis:
    cpabe: CPABEFittedSlopes
    ciphertext_crossover: CiphertextSizeCrossover
    latency_crossover: LatencyCrossover
    # Size of one wrapped session key, so also the total ciphertext growth per subscriber
    rsa_ciphertext_bytes_per_subscriber: float


def fit_cpabe_slopes(
    results: BenchmarkSummary,
    config: Config,
) -> CPABEFittedSlopes:

    def fit(operation: str, unit: str, divisor: float = 1.0) -> LinearFit:
        series = results.sweep_features(
            operation, CPABE_ATTRIBUTES, config.attribute_counts, unit, divisor
        )
        return fit_linear_regression(series.sweep_values, series.means)

    return CPABEFittedSlopes(
        encrypt=fit("encrypt", NS_PER_OP, NS_PER_MICROSECOND),
        decrypt=fit("decrypt", NS_PER_OP, NS_PER_MICROSECOND),
        key_issuance=fit("keygen", NS_PER_OP, NS_PER_MICROSECOND),
        ciphertext=fit("encrypt", CIPHERTEXT_BYTES),
        stored_key=fit("keygen", STORED_KEY_BYTES),
    )


def build_ciphertext_size_crossover(
    results: BenchmarkSummary,
    config: Config,
    rsa_bytes_per_subscriber: float,
) -> CiphertextSizeCrossover:

    def cpabe_bytes(attribute_count: int) -> float:
        return (
            results.get_case_summary("encrypt", CPABE_ATTRIBUTES, attribute_count)
            .get_feature(CIPHERTEXT_BYTES)
            .mean
        )

    cpabe_bytes_min = cpabe_bytes(config.min_attributes)
    cpabe_bytes_max = cpabe_bytes(config.max_attributes)

    return CiphertextSizeCrossover(
        rsa_total_bytes=results.sweep_features(
            "encrypt",
            RSA_SUBSCRIBERS,
            config.subscriber_counts,
            TOTAL_CIPHERTEXT_BYTES,
        ),
        cpabe_bytes_min=cpabe_bytes_min,
        cpabe_bytes_max=cpabe_bytes_max,
        # Subscriber count at which RSA's wrapped keys add up to CP-ABE's one ciphertext
        crossover_min=cpabe_bytes_min / rsa_bytes_per_subscriber,
        crossover_max=cpabe_bytes_max / rsa_bytes_per_subscriber,
    )


def build_latency_crossover(
    results: BenchmarkSummary,
    config: Config,
    rsa_encrypt_micros: FeatureSweep,
    rsa_encrypt_fit: LinearFit,
) -> LatencyCrossover:

    def cpabe_micros(operation: str, attribute_count: int) -> float:
        return results.get_case_summary(
            operation, CPABE_ATTRIBUTES, attribute_count
        ).get_latency_in_micros.mean

    cpabe_encrypt_micros_min = cpabe_micros("encrypt", config.min_attributes)
    cpabe_encrypt_micros_max = cpabe_micros("encrypt", config.max_attributes)

    rsa_decrypt_micros = results.get_case_summary(
        "decrypt", RSA_KEY_BITS, config.fixed_rsa_key_bits
    ).get_latency_in_micros.mean

    # Subscriber count at which RSA's fitted encrypt line reaches CP-ABE's fixed cost
    def crossover_at(cpabe_micros_level: float) -> float:
        return (cpabe_micros_level - rsa_encrypt_fit.intercept) / rsa_encrypt_fit.slope

    return LatencyCrossover(
        rsa_encrypt_micros=rsa_encrypt_micros,
        rsa_encrypt_fit=rsa_encrypt_fit,
        cpabe_encrypt_micros_min=cpabe_encrypt_micros_min,
        cpabe_encrypt_micros_max=cpabe_encrypt_micros_max,
        crossover_min=crossover_at(cpabe_encrypt_micros_min),
        crossover_max=crossover_at(cpabe_encrypt_micros_max),
        decrypt_penalty_min=cpabe_micros("decrypt", config.min_attributes)
        / rsa_decrypt_micros,
        decrypt_penalty_max=cpabe_micros("decrypt", config.max_attributes)
        / rsa_decrypt_micros,
    )


def analyse(results: BenchmarkSummary, config: Config) -> Analysis:

    # One wrapped session key is the same size at every subscriber count, and RSA's total
    # ciphertext grows by exactly that much per additional subscriber
    rsa_ciphertext_bytes_per_subscriber = (
        results.get_case_summary(
            "encrypt", RSA_SUBSCRIBERS, config.subscriber_counts[0]
        )
        .get_feature(CIPHERTEXT_BYTES)
        .mean
    )

    rsa_encrypt_micros = results.sweep_features(
        "encrypt",
        RSA_SUBSCRIBERS,
        config.subscriber_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
    )
    rsa_encrypt_fit = fit_linear_regression(
        rsa_encrypt_micros.sweep_values, rsa_encrypt_micros.means
    )

    return Analysis(
        cpabe=fit_cpabe_slopes(results, config),
        ciphertext_crossover=build_ciphertext_size_crossover(
            results, config, rsa_ciphertext_bytes_per_subscriber
        ),
        latency_crossover=build_latency_crossover(
            results, config, rsa_encrypt_micros, rsa_encrypt_fit
        ),
        rsa_ciphertext_bytes_per_subscriber=rsa_ciphertext_bytes_per_subscriber,
    )


def plot_sweep(
    results: BenchmarkSummary,
    sweep_name: str,
    sweep_values: list[int],
    sweep_operations: list[str],
    size_series: tuple[SizeSeries, ...],
    x_label: str,
    figure_title: str,
    output_path: str,
) -> None:

    # Key generation is orders of magnitude slower than encrypt and decrypt, so it gets
    # its own panel wherever the sweep measures it
    keygen_on_own_axis = "keygen" in sweep_operations

    if keygen_on_own_axis:
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

        series = results.sweep_features(
            operation,
            sweep_name,
            sweep_values,
            NS_PER_OP,
            NS_PER_MICROSECOND,
            with_ci=True,
        )

        draw_summary(
            keygen_latency_axis if operation == "keygen" else latency_axis,
            series,
            operation.capitalize(),
            OPERATION_COLORS[operation],
        )

    if keygen_on_own_axis:
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

    for size in size_series:
        draw_summary(
            size_axis,
            results.sweep_features(size.operation, sweep_name, sweep_values, size.unit),
            size.label,
            size.color,
        )

    size_axis.set_title("Sizes", fontsize=11)
    size_axis.set_ylabel("Size (bytes)")
    size_axis.set_xticks(sweep_values)
    size_axis.set_xlabel(x_label)
    apply_value_grid(size_axis)
    size_axis.legend(fontsize=10)
    size_axis.set_ylim(bottom=0)

    if keygen_on_own_axis:
        figure.subplots_adjust(top=0.92)
    else:
        figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))

    save_figure(figure, output_path)


def plot_ciphertext_size_crossover(
    crossover: CiphertextSizeCrossover,
    config: Config,
) -> None:

    x_limit = config.max_subscribers

    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    draw_summary(
        axis,
        crossover.rsa_total_bytes,
        "RSA Scaling Subs",
        TOTAL_CIPHERTEXT_COLOR,
    )

    for level, attribute_count, color in (
        (crossover.cpabe_bytes_min, config.min_attributes, AMBER),
        (crossover.cpabe_bytes_max, config.max_attributes, CRIMSON),
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
        (crossover.crossover_min, crossover.cpabe_bytes_min),
        (crossover.crossover_max, crossover.cpabe_bytes_max),
    ):
        mark_crossover(axis, crossover_value, level_value, f"≈{crossover_value:,.1f}")

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
    save_figure(figure, config.paths.figure(CIPHERTEXT_SIZE_CROSSOVER_PLOT))


def plot_encrypt_latency_crossover(
    crossover: LatencyCrossover,
    config: Config,
) -> None:

    x_limit = crossover.crossover_max * 1.15

    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    projection_start_subscribers = float(config.max_subscribers)
    projection_end_micros = crossover.rsa_encrypt_fit.calculate_y_based_on_x(x_limit)

    axis.plot(
        [projection_start_subscribers, x_limit],
        [
            crossover.rsa_encrypt_fit.calculate_y_based_on_x(
                projection_start_subscribers
            ),
            projection_end_micros,
        ],
        color=TOTAL_CIPHERTEXT_COLOR,
        linewidth=1.8,
        linestyle=":",
        label="RSA Linear Fit (Projected Beyond Sample)",
    )

    draw_summary(
        axis,
        crossover.rsa_encrypt_micros,
        "RSA Scaling Subs (Measured)",
        TOTAL_CIPHERTEXT_COLOR,
        linewidth=2.6,
    )

    for level, attribute_count, color in (
        (crossover.cpabe_encrypt_micros_min, config.min_attributes, AMBER),
        (crossover.cpabe_encrypt_micros_max, config.max_attributes, CRIMSON),
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
        (crossover.crossover_min, crossover.cpabe_encrypt_micros_min),
        (crossover.crossover_max, crossover.cpabe_encrypt_micros_max),
    ):
        mark_crossover(axis, crossover_value, level_value, f"≈{crossover_value:,.0f}")

    largest_value = max(crossover.cpabe_encrypt_micros_max, projection_end_micros)

    axis.set_xlim(0.0, x_limit)
    axis.set_ylim(0.0, largest_value * 1.12)
    axis.set_xlabel("Subscribers")
    axis.set_ylabel("Publisher Encrypt Latency (µs)")
    apply_value_grid(axis)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    save_figure(figure, config.paths.figure(ENCRYPT_LATENCY_CROSSOVER_PLOT))


def plot_decrypt_latency_crossover(
    results: BenchmarkSummary,
    config: Config,
) -> None:

    figure, axis = plt.subplots(figsize=CROSSOVER_FIGURE_SIZE)

    cpabe_series = results.sweep_features(
        "decrypt",
        CPABE_ATTRIBUTES,
        config.attribute_counts,
        NS_PER_OP,
        NS_PER_MICROSECOND,
        with_ci=True,
    )

    draw_summary(axis, cpabe_series, "CP-ABE", VIOLET, linewidth=2.0)

    largest_value = calculate_axis_top([cpabe_series])

    for index, rsa_key_bits in enumerate(config.rsa_key_bits):

        rsa_latency = results.get_case_summary(
            "decrypt", RSA_KEY_BITS, rsa_key_bits
        ).get_latency_in_micros

        rsa_color = RSA_KEY_BITS_COLORS[index % len(RSA_KEY_BITS_COLORS)]

        axis.hlines(
            rsa_latency.mean,
            config.min_attributes,
            config.max_attributes,
            color=rsa_color,
            linestyle="--",
            linewidth=1.6,
            label=f"RSA-{rsa_key_bits}",
        )

        axis.errorbar(
            [config.max_attributes],
            [rsa_latency.mean],
            yerr=[rsa_latency.ci],
            color=rsa_color,
            fmt="none",
            capsize=4,
        )

        largest_value = max(largest_value, rsa_latency.mean + rsa_latency.ci)

    axis.set_xticks(config.attribute_counts)
    axis.set_xlim(0.0, float(config.max_attributes) * AXIS_HEADROOM)
    axis.set_ylim(0.0, largest_value * 1.15)
    axis.set_xlabel("Policy Attributes")
    axis.set_ylabel("Decrypt Latency (µs) ± 95% CI")
    apply_value_grid(axis)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    save_figure(figure, config.paths.figure(DECRYPT_LATENCY_CROSSOVER_PLOT))


def plot_encrypt_decrypt_asymmetry(
    results: BenchmarkSummary,
    config: Config,
) -> None:

    def micros(operation: str, sweep_name: str, sweep_value: int) -> float:
        return results.get_case_summary(
            operation, sweep_name, sweep_value
        ).get_latency_in_micros.mean

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


def build_table(
    results: BenchmarkSummary,
    config: Config,
    sweep_name: str,
    sweep_values: list[int],
    operation: str,
    value_header: str,
    size_columns: tuple[tuple[str, str], ...] = (),
) -> str:

    rows = []

    for sweep_value in sweep_values:

        case = results.get_case_summary(operation, sweep_name, sweep_value)

        latency = case.get_latency_in_micros

        rows.append(
            [
                str(sweep_value),
                format_mean_with_ci(latency.mean, latency.ci),
                *[
                    format_byte_size(round(case.get_feature(unit).mean))
                    for _, unit in size_columns
                ],
                f"{case.iterations:,}",
            ]
        )

    return build_html_table(
        [
            value_header.upper(),
            "LATENCY (µs/op)",
            *[header for header, _ in size_columns],
            f"ITERS (Σ{config.runs} RUNS)",
        ],
        rows,
    )


def build_rsa_circle_visualization(
    results: BenchmarkSummary,
    analysis: Analysis,
    config: Config,
) -> dict[str, str]:

    single_bytes = analysis.rsa_ciphertext_bytes_per_subscriber
    total_bytes = (
        results.get_case_summary("encrypt", RSA_SUBSCRIBERS, config.max_subscribers)
        .get_feature(TOTAL_CIPHERTEXT_BYTES)
        .mean
    )

    single_diameter_px = max(
        FANOUT_SMALLEST_DIAMETER_PX,
        FANOUT_LARGEST_DIAMETER_PX * (single_bytes / total_bytes) ** 0.5,
    )

    def circle_style(diameter_px: float) -> str:
        return f'style="width:{diameter_px:.0f}px;height:{diameter_px:.0f}px;"'

    return {
        "FanoutSingleBytes": format_byte_size(round(single_bytes)),
        "FanoutTotalBytes": format_byte_size(round(total_bytes)),
        "FanoutMultiplier": f"{total_bytes / single_bytes:.0f}",
        "FanoutSingleStyle": circle_style(single_diameter_px),
        "FanoutTotalStyle": circle_style(FANOUT_LARGEST_DIAMETER_PX),
    }


def write_html_report(
    results: BenchmarkSummary,
    config: Config,
    analysis: Analysis,
) -> None:

    cpabe = analysis.cpabe
    ciphertext = analysis.ciphertext_crossover
    latency = analysis.latency_crossover

    def micros_slope(fit: LinearFit) -> str:
        return f"+{format_mean_with_ci(fit.slope, fit.slope_ci, decimals=0)} µs"

    def bytes_slope(fit: LinearFit) -> str:
        return f"+{format_mean_with_ci(fit.slope, fit.slope_ci, decimals=0, thousands=False)} B"

    def table(sweep_name, sweep_values, operation, value_header, *size_columns) -> str:
        return build_table(
            results,
            config,
            sweep_name,
            sweep_values,
            operation,
            value_header,
            size_columns,
        )

    placeholders = {
        **build_html_generic_data(
            config.runs, config.t_critical, results.get_total_iterations
        ),
        **build_rsa_circle_visualization(results, analysis, config),
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
        "BandwidthCrossoverPlot": CIPHERTEXT_SIZE_CROSSOVER_PLOT,
        "AsymmetryPlot": ASYMMETRY_PLOT,
        "EncryptCpuCrossoverPlot": ENCRYPT_LATENCY_CROSSOVER_PLOT,
        "DecryptCpuCrossoverPlot": DECRYPT_LATENCY_CROSSOVER_PLOT,
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
            f"+{format_mean_with_ci(latency.rsa_encrypt_fit.slope, latency.rsa_encrypt_fit.slope_ci)} µs"
        ),
        "RsaSubscriberEncryptRSquared": f"{latency.rsa_encrypt_fit.r_squared:.6f}",
        "RsaSubscriberTotalCiphertextSlope": (
            f"+{analysis.rsa_ciphertext_bytes_per_subscriber:.0f} B"
        ),
        "BytesCrossoverLow": f"{ciphertext.crossover_min:,.1f}",
        "BytesCrossoverHigh": f"{ciphertext.crossover_max:,.1f}",
        "BytesRsaThroughMin": f"{int(ciphertext.crossover_min):,}",
        "BytesRsaThroughMax": f"{int(ciphertext.crossover_max):,}",
        "EncryptCpuCrossoverLow": f"{latency.crossover_min:,.0f}",
        "EncryptCpuCrossoverHigh": f"{latency.crossover_max:,.0f}",
        "CpuRsaThroughMin": f"{int(latency.crossover_min):,}",
        "CpuRsaThroughMax": f"{int(latency.crossover_max):,}",
        "DecryptPenaltyMin": f"{latency.decrypt_penalty_min:,.1f}",
        "DecryptPenaltyMax": f"{latency.decrypt_penalty_max:,.1f}",
    }

    build_html_report(config.paths.template, config.paths.report, placeholders)


def main() -> None:
    config = load_config()
    results = load_results(
        config.paths.bench_output, BENCHMARK_PREFIX, config.t_critical
    )
    analysis = analyse(results, config)

    plot_sweep(
        results,
        CPABE_ATTRIBUTES,
        config.attribute_counts,
        OPERATIONS,
        (CIPHERTEXT_SERIES, STORED_KEY_SERIES),
        "Policy Attributes",
        "CP-ABE Scaling with Policy Attribute Count",
        config.paths.figure(CPABE_PLOT),
    )

    plot_sweep(
        results,
        RSA_SUBSCRIBERS,
        config.subscriber_counts,
        ENCRYPT_DECRYPT,
        (CIPHERTEXT_SERIES, TOTAL_CIPHERTEXT_SERIES),
        "Subscribers",
        f"RSA Scaling with Subscriber Count (Fixed Key: {config.fixed_rsa_key_bits} bits)",
        config.paths.figure(RSA_SUBSCRIBERS_PLOT),
    )

    plot_sweep(
        results,
        RSA_KEY_BITS,
        config.rsa_key_bits,
        OPERATIONS,
        (CIPHERTEXT_SERIES, STORED_KEY_SERIES),
        "RSA Key Bits",
        "RSA Scaling with Key Size (1 Subscriber)",
        config.paths.figure(RSA_KEY_BITS_PLOT),
    )

    plot_ciphertext_size_crossover(analysis.ciphertext_crossover, config)
    plot_encrypt_latency_crossover(analysis.latency_crossover, config)
    plot_decrypt_latency_crossover(results, config)
    plot_encrypt_decrypt_asymmetry(results, config)

    write_html_report(results, config, analysis)


if __name__ == "__main__":
    main()
