import os
import re
from pathlib import Path
from statistics import fmean
from typing import cast

from scipy import stats

from report.config import *
from report.model.benchmark_summary import *
from report.model.case_aggregation import *
from report.model.measurement import *
from report.model.populate_model import *
from report.render.chart import *
from report.render.formatting import *
from report.render.html import *

NO_MEASUREMENT = float("nan")

HTML_TEMPLATE_NAME = "aes_ascon_template.html"

DEFAULT_SCENARIO_RESULT_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "results" / "aes-ascon" / "with-acceleration"
)

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"
ENERGY_PLOT = "energy.png"

ENERGY_OUTPUT_NAME = "aes_ascon_energy.txt"

WARMUP_END_NS = 2_000_000_000
MEASUREMENT_END_NS = 12_000_000_000
NS_PER_SECOND = 1_000_000_000
MICROJOULES_PER_JOULE = 1_000_000

BENCHMARK_PREFIX = "BenchmarkAESASCON"

ENERGY_CASE_PATTERN = re.compile(
    r"^\[case algorithm=(\S+) operation=(\S+) payload_size=(\d+)\]$"
)


class EnergyRun:

    def __init__(self, ns_per_op: float) -> None:
        self.ns_per_op = ns_per_op
        self.power_samples: list[tuple[int, float]] = []


def load_energy_results(
    filepath: Path,
) -> tuple[list[float], dict[tuple[str, str, int], list[EnergyRun]]]:
    baseline_power_samples: list[float] = []
    cases: dict[tuple[str, str, int], list[EnergyRun]] = {}

    in_baseline = False
    current_case: tuple[str, str, int] | None = None
    current_run: EnergyRun | None = None

    with filepath.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            if line == "[baseline]":
                in_baseline = True
                current_case = None
                current_run = None
                continue

            case_match = ENERGY_CASE_PATTERN.fullmatch(line)
            if case_match is not None:
                in_baseline = False
                current_case = (
                    case_match.group(1),
                    case_match.group(2),
                    int(case_match.group(3)),
                )
                if current_case in cases:
                    raise ValueError(
                        f"Duplicate energy case at line {line_number}: {line}"
                    )
                cases[current_case] = []
                current_run = None
                continue

            if line == "[run]":
                current_run = None
                continue

            if line.startswith("ns_per_op="):
                if current_case is None:
                    raise ValueError(f"Energy run outside a case at line {line_number}")
                current_run = EnergyRun(float(line.removeprefix("ns_per_op=")))
                cases[current_case].append(current_run)
                continue

            if line.startswith("elapsed_ns="):
                fields = dict(field.split("=", 1) for field in line.split())
                elapsed_ns = int(fields["elapsed_ns"])
                power_w = float(fields["power_w"])

                if in_baseline:
                    baseline_power_samples.append(power_w)
                elif current_run is not None:
                    current_run.power_samples.append((elapsed_ns, power_w))
                else:
                    raise ValueError(
                        f"Power sample outside an energy run at line {line_number}"
                    )
                continue

            raise ValueError(f"Unexpected energy result at line {line_number}: {line}")

    return baseline_power_samples, cases


def calculate_energy_summaries(
    baseline_power_samples: list[float],
    cases: dict[tuple[str, str, int], list[EnergyRun]],
    payload_sizes: list[int],
    runs: int,
) -> dict[tuple[str, str, int], tuple[float, float]]:
    idle_power_w = fmean(baseline_power_samples)
    summaries = {}

    for algorithm in ("AES-GCM", "ASCON"):
        for operation in ("Encrypt", "Decrypt"):
            for payload_size in payload_sizes:
                case_key = (algorithm, operation, payload_size)
                energy_runs = cases[case_key]

                if len(energy_runs) != runs:
                    raise ValueError(
                        f"Expected {runs} energy runs for "
                        f"{algorithm} {operation} {payload_size}B, "
                        f"but observed {len(energy_runs)}"
                    )

                energy_per_operation_joules = []

                for energy_run in energy_runs:
                    steady_state_power_samples = [
                        power_w
                        for elapsed_ns, power_w in energy_run.power_samples
                        if WARMUP_END_NS <= elapsed_ns < MEASUREMENT_END_NS
                    ]
                    load_power_w = fmean(steady_state_power_samples)
                    operation_time_seconds = energy_run.ns_per_op / NS_PER_SECOND
                    energy_per_operation_joules.append(
                        (load_power_w - idle_power_w) * operation_time_seconds
                    )

                mean_joules = fmean(energy_per_operation_joules)
                confidence_interval_joules = float(
                    stats.t.ppf(0.975, runs - 1)
                    * stats.sem(energy_per_operation_joules)
                )
                summaries[case_key] = (mean_joules, confidence_interval_joules)

    return summaries


def collect_energy_series(
    summaries: dict[tuple[str, str, int], tuple[float, float]],
    algorithm: str,
    operation: str,
    payload_sizes: list[int],
) -> tuple[list[float], list[float]]:
    means = [
        summaries[(algorithm, operation, payload_size)][0] * MICROJOULES_PER_JOULE
        for payload_size in payload_sizes
    ]
    confidence_intervals = [
        summaries[(algorithm, operation, payload_size)][1] * MICROJOULES_PER_JOULE
        for payload_size in payload_sizes
    ]
    return means, confidence_intervals


def collect_aggregations(
    results: BenchmarkSummary,
    payload_sizes: list[int],
) -> tuple[
    list[CaseAggregation],
    list[CaseAggregation],
    list[CaseAggregation],
    list[CaseAggregation],
]:
    aes_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Encrypt", "AES-GCM", payload_size),
        )
        for payload_size in payload_sizes
    ]
    aes_decrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Decrypt", "AES-GCM", payload_size),
        )
        for payload_size in payload_sizes
    ]
    ascon_encrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Encrypt", "ASCON", payload_size),
        )
        for payload_size in payload_sizes
    ]
    ascon_decrypt = [
        cast(
            CaseAggregation,
            results.find_aggregation("Decrypt", "ASCON", payload_size),
        )
        for payload_size in payload_sizes
    ]

    return aes_encrypt, aes_decrypt, ascon_encrypt, ascon_decrypt


def analyze_aggregations(
    aes_encrypt: list[CaseAggregation],
    aes_decrypt: list[CaseAggregation],
    ascon_encrypt: list[CaseAggregation],
    ascon_decrypt: list[CaseAggregation],
) -> tuple[
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[int | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[int | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[int | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[int | None],
]:
    aes_encrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in aes_encrypt
    ]
    aes_encrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in aes_encrypt
    ]
    aes_encrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in aes_encrypt
    ]
    aes_encrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in aes_encrypt
    ]
    aes_encrypt_overhead_list = [
        None if aggregation.out_of_memory else aggregation.mean(WIRE_OVERHEAD_BYTES)
        for aggregation in aes_encrypt
    ]
    aes_encrypt_iterations_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in aes_encrypt
    ]

    aes_decrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in aes_decrypt
    ]
    aes_decrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in aes_decrypt
    ]
    aes_decrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in aes_decrypt
    ]
    aes_decrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in aes_decrypt
    ]
    aes_decrypt_overhead_list = [
        None if aggregation.out_of_memory else aggregation.mean(WIRE_OVERHEAD_BYTES)
        for aggregation in aes_decrypt
    ]
    aes_decrypt_iterations_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in aes_decrypt
    ]

    ascon_encrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in ascon_encrypt
    ]
    ascon_encrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in ascon_encrypt
    ]
    ascon_encrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in ascon_encrypt
    ]
    ascon_encrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in ascon_encrypt
    ]
    ascon_encrypt_overhead_list = [
        None if aggregation.out_of_memory else aggregation.mean(WIRE_OVERHEAD_BYTES)
        for aggregation in ascon_encrypt
    ]
    ascon_encrypt_iterations_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in ascon_encrypt
    ]

    ascon_decrypt_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in ascon_decrypt
    ]
    ascon_decrypt_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in ascon_decrypt
    ]
    ascon_decrypt_throughput_list = [
        None if aggregation.out_of_memory else aggregation.mean(MB_PER_SECOND)
        for aggregation in ascon_decrypt
    ]
    ascon_decrypt_throughput_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(MB_PER_SECOND)
        )
        for aggregation in ascon_decrypt
    ]
    ascon_decrypt_overhead_list = [
        None if aggregation.out_of_memory else aggregation.mean(WIRE_OVERHEAD_BYTES)
        for aggregation in ascon_decrypt
    ]
    ascon_decrypt_iterations_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in ascon_decrypt
    ]

    return (
        aes_encrypt_latency_list,
        aes_encrypt_latency_ci_list,
        aes_encrypt_throughput_list,
        aes_encrypt_throughput_ci_list,
        aes_encrypt_overhead_list,
        aes_encrypt_iterations_list,
        aes_decrypt_latency_list,
        aes_decrypt_latency_ci_list,
        aes_decrypt_throughput_list,
        aes_decrypt_throughput_ci_list,
        aes_decrypt_overhead_list,
        aes_decrypt_iterations_list,
        ascon_encrypt_latency_list,
        ascon_encrypt_latency_ci_list,
        ascon_encrypt_throughput_list,
        ascon_encrypt_throughput_ci_list,
        ascon_encrypt_overhead_list,
        ascon_encrypt_iterations_list,
        ascon_decrypt_latency_list,
        ascon_decrypt_latency_ci_list,
        ascon_decrypt_throughput_list,
        ascon_decrypt_throughput_ci_list,
        ascon_decrypt_overhead_list,
        ascon_decrypt_iterations_list,
    )


def main() -> None:
    runs = parse_int_env("AES_ASCON_RUNS")
    payload_sizes = parse_int_list_env("AES_ASCON_PAYLOAD_SIZES")

    result_dir = Path(
        os.environ.get(
            "AES_ASCON_RESULT_DIR",
            str(DEFAULT_SCENARIO_RESULT_DIRECTORY),
        )
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    case_status = result_dir / CASE_STATUS_NAME
    energy_output = result_dir / ENERGY_OUTPUT_NAME
    template_path = Path(TEMPLATE_DIR) / HTML_TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "B")
    load_out_of_memory_status(results, str(case_status))

    baseline_power_samples, energy_cases = load_energy_results(energy_output)
    energy_summaries = calculate_energy_summaries(
        baseline_power_samples,
        energy_cases,
        payload_sizes,
        runs,
    )
    aes_encrypt_energy_list, aes_encrypt_energy_ci_list = collect_energy_series(
        energy_summaries,
        "AES-GCM",
        "Encrypt",
        payload_sizes,
    )
    aes_decrypt_energy_list, aes_decrypt_energy_ci_list = collect_energy_series(
        energy_summaries,
        "AES-GCM",
        "Decrypt",
        payload_sizes,
    )
    ascon_encrypt_energy_list, ascon_encrypt_energy_ci_list = collect_energy_series(
        energy_summaries,
        "ASCON",
        "Encrypt",
        payload_sizes,
    )
    ascon_decrypt_energy_list, ascon_decrypt_energy_ci_list = collect_energy_series(
        energy_summaries,
        "ASCON",
        "Decrypt",
        payload_sizes,
    )

    aes_encrypt, aes_decrypt, ascon_encrypt, ascon_decrypt = collect_aggregations(
        results, payload_sizes
    )

    (
        aes_encrypt_latency_list,
        aes_encrypt_latency_ci_list,
        aes_encrypt_throughput_list,
        aes_encrypt_throughput_ci_list,
        aes_encrypt_overhead_list,
        aes_encrypt_iterations_list,
        aes_decrypt_latency_list,
        aes_decrypt_latency_ci_list,
        aes_decrypt_throughput_list,
        aes_decrypt_throughput_ci_list,
        aes_decrypt_overhead_list,
        aes_decrypt_iterations_list,
        ascon_encrypt_latency_list,
        ascon_encrypt_latency_ci_list,
        ascon_encrypt_throughput_list,
        ascon_encrypt_throughput_ci_list,
        ascon_encrypt_overhead_list,
        ascon_encrypt_iterations_list,
        ascon_decrypt_latency_list,
        ascon_decrypt_latency_ci_list,
        ascon_decrypt_throughput_list,
        ascon_decrypt_throughput_ci_list,
        ascon_decrypt_overhead_list,
        ascon_decrypt_iterations_list,
    ) = analyze_aggregations(
        aes_encrypt,
        aes_decrypt,
        ascon_encrypt,
        ascon_decrypt,
    )

    total_benchmark_iterations = sum(
        aggregation.iterations
        for aggregation in results.aggregations
        if not aggregation.out_of_memory
    )
    out_of_memory_aggregations = [
        aggregation for aggregation in results.aggregations if aggregation.out_of_memory
    ]

    plot_aes_ascon_latency(
        payload_sizes,
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in aes_encrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in aes_encrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in ascon_encrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in ascon_encrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in aes_decrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in aes_decrypt_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in ascon_decrypt_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in ascon_decrypt_latency_ci_list
        ],
        str(result_dir / LATENCY_PLOT),
    )

    plot_aes_ascon_throughput(
        payload_sizes,
        [
            NO_MEASUREMENT if value is None else value
            for value in aes_encrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in aes_encrypt_throughput_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in ascon_encrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in ascon_encrypt_throughput_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in aes_decrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in aes_decrypt_throughput_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in ascon_decrypt_throughput_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in ascon_decrypt_throughput_ci_list
        ],
        str(result_dir / THROUGHPUT_PLOT),
    )

    plot_aes_ascon_energy(
        payload_sizes,
        aes_encrypt_energy_list,
        aes_encrypt_energy_ci_list,
        ascon_encrypt_energy_list,
        ascon_encrypt_energy_ci_list,
        aes_decrypt_energy_list,
        aes_decrypt_energy_ci_list,
        ascon_decrypt_energy_list,
        ascon_decrypt_energy_ci_list,
        str(result_dir / ENERGY_PLOT),
    )

    write_aes_ascon_report(
        runs=runs,
        t_multiplier=float(stats.t.ppf(0.975, runs - 1)),
        total_iterations=total_benchmark_iterations,
        payload_sizes=payload_sizes,
        aes_encrypt_latency_means=aes_encrypt_latency_list,
        aes_encrypt_latency_cis=aes_encrypt_latency_ci_list,
        aes_encrypt_throughput_means=aes_encrypt_throughput_list,
        aes_encrypt_throughput_cis=aes_encrypt_throughput_ci_list,
        aes_encrypt_overhead_bytes=aes_encrypt_overhead_list,
        aes_encrypt_iterations=aes_encrypt_iterations_list,
        aes_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", "AES-GCM", payload_sizes
        ),
        ascon_encrypt_latency_means=ascon_encrypt_latency_list,
        ascon_encrypt_latency_cis=ascon_encrypt_latency_ci_list,
        ascon_encrypt_throughput_means=ascon_encrypt_throughput_list,
        ascon_encrypt_throughput_cis=ascon_encrypt_throughput_ci_list,
        ascon_encrypt_overhead_bytes=ascon_encrypt_overhead_list,
        ascon_encrypt_iterations=ascon_encrypt_iterations_list,
        ascon_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", "ASCON", payload_sizes
        ),
        aes_decrypt_latency_means=aes_decrypt_latency_list,
        aes_decrypt_latency_cis=aes_decrypt_latency_ci_list,
        aes_decrypt_throughput_means=aes_decrypt_throughput_list,
        aes_decrypt_throughput_cis=aes_decrypt_throughput_ci_list,
        aes_decrypt_overhead_bytes=aes_decrypt_overhead_list,
        aes_decrypt_iterations=aes_decrypt_iterations_list,
        aes_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", "AES-GCM", payload_sizes
        ),
        ascon_decrypt_latency_means=ascon_decrypt_latency_list,
        ascon_decrypt_latency_cis=ascon_decrypt_latency_ci_list,
        ascon_decrypt_throughput_means=ascon_decrypt_throughput_list,
        ascon_decrypt_throughput_cis=ascon_decrypt_throughput_ci_list,
        ascon_decrypt_overhead_bytes=ascon_decrypt_overhead_list,
        ascon_decrypt_iterations=ascon_decrypt_iterations_list,
        ascon_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", "ASCON", payload_sizes
        ),
        aes_encrypt_energy_means=aes_encrypt_energy_list,
        aes_encrypt_energy_cis=aes_encrypt_energy_ci_list,
        ascon_encrypt_energy_means=ascon_encrypt_energy_list,
        ascon_encrypt_energy_cis=ascon_encrypt_energy_ci_list,
        aes_decrypt_energy_means=aes_decrypt_energy_list,
        aes_decrypt_energy_cis=aes_decrypt_energy_ci_list,
        ascon_decrypt_energy_means=ascon_decrypt_energy_list,
        ascon_decrypt_energy_cis=ascon_decrypt_energy_ci_list,
        out_of_memory_operations=[
            aggregation.operation for aggregation in out_of_memory_aggregations
        ],
        out_of_memory_cases=[
            f"{aggregation.parameter}/{aggregation.parameter_value}"
            for aggregation in out_of_memory_aggregations
        ],
        latency_plot=LATENCY_PLOT,
        throughput_plot=THROUGHPUT_PLOT,
        energy_plot=ENERGY_PLOT,
        template_path=str(template_path),
        report_path=str(report_path),
    )


if __name__ == "__main__":
    main()
