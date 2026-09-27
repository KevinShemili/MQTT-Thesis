import os
from pathlib import Path

from dotenv import load_dotenv

from report.analysis.shared.load_summary import load_summary
from report.analysis.shared.parser import parse_int_env, parse_int_list_env
from report.analysis.shared.paths import REPORT_NAME, TEMPLATE_DIR
from report.analysis.shared.statistics import (
    energy_statistics,
    timing_statistics,
)
from report.analysis.shared.metrics import (
    collect_energy_throttle_flags,
    collect_timing_throttle_flags,
    to_microjoules,
    to_microseconds,
)
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import EnergyCase
from report.model.timing.timing_aggregation import TimingAggregation
from report.model.timing.timing_case import (
    NS_PER_OP,
    RAW_BYTES,
    SERIALIZED_BYTES,
)
from report.render.chart import (
    plot_json_cbor_energy,
    plot_json_cbor_energy_reduction,
    plot_json_cbor_latency,
    plot_json_cbor_latency_speedup,
    plot_json_cbor_size,
    plot_json_cbor_wire_overhead,
)
from report.render.html import write_json_cbor_report

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_FILE = PROJECT_ROOT / "environment" / "benchmark.env"

PARAMETER = "payload_size"

TIMING_RESULT_NAME = "timing.csv"
ENERGY_RESULT_NAME = "energy.csv"
REPORT_TEMPLATE_NAME = "json_cbor_template.html"

LATENCY_PLOT = "latency.png"
LATENCY_SPEEDUP_PLOT = "latency_speedup.png"
SIZE_PLOT = "size.png"
WIRE_OVERHEAD_PLOT = "wire_overhead.png"
ENERGY_PLOT = "energy.png"
ENERGY_REDUCTION_PLOT = "energy_reduction.png"


def analyze_case(
    timing_aggregations: list[TimingAggregation],
    energy_aggregations: list[EnergyAggregation],
    energy_baseline_cases: list[EnergyCase],
):

    latency_means, latency_cis = timing_statistics(
        timing_aggregations,
        NS_PER_OP,
    )

    energy_means, energy_cis = energy_statistics(
        energy_aggregations,
        energy_baseline_cases,
        timing_aggregations,
    )

    return {
        "latency_means": to_microseconds(latency_means),
        "latency_cis": to_microseconds(latency_cis),
        "energy_means": to_microjoules(energy_means),
        "energy_cis": to_microjoules(energy_cis),
        "timing_throttled": collect_timing_throttle_flags(timing_aggregations),
        "energy_throttled": collect_energy_throttle_flags(energy_aggregations),
    }


def main() -> None:

    load_dotenv(
        ENVIRONMENT_FILE,
        override=True,
    )

    runs = parse_int_env("JSON_CBOR_RUNS")
    payload_sizes = parse_int_list_env("PAYLOAD_SIZES")
    warmup_duration = parse_int_env("WARMUP_DURATION")
    measurement_duration = parse_int_env("MEASUREMENT_DURATION")

    result_directory = PROJECT_ROOT / os.environ["JSON_CBOR_RESULT_DIR"]
    timing_result_file = result_directory / TIMING_RESULT_NAME
    energy_result_file = result_directory / ENERGY_RESULT_NAME
    template_path = TEMPLATE_DIR / REPORT_TEMPLATE_NAME
    report_path = result_directory / REPORT_NAME

    summary = load_summary(
        timing_filepath=str(timing_result_file),
        energy_filepath=str(energy_result_file),
    )

    case_results = {}
    size_results = {}

    for format_name in ("JSON", "CBOR", "CBORKeyAsInt"):
        for operation in ("Serialize", "Deserialize"):

            timing_aggregations = [
                summary.find_timing_aggregation(
                    format_name,
                    operation,
                    PARAMETER,
                    payload_size,
                )
                for payload_size in payload_sizes
            ]

            energy_aggregations = [
                summary.find_energy_aggregation(
                    format_name,
                    operation,
                    PARAMETER,
                    payload_size,
                )
                for payload_size in payload_sizes
            ]

            case_results[(format_name, operation)] = analyze_case(
                timing_aggregations,
                energy_aggregations,
                summary.energy_baseline_cases,
            )

            if operation == "Serialize":
                size_results[format_name] = [
                    int(aggregation.cases[0].measurements[SERIALIZED_BYTES])
                    for aggregation in timing_aggregations
                ]
                if format_name == "JSON":
                    raw_sizes = [
                        int(aggregation.cases[0].measurements[RAW_BYTES])
                        for aggregation in timing_aggregations
                    ]

    latency_results = {
        case: (
            values["latency_means"],
            values["latency_cis"],
        )
        for case, values in case_results.items()
    }

    wire_overheads = {
        format_name: [
            message_size - raw_size
            for message_size, raw_size in zip(
                message_sizes,
                raw_sizes,
                strict=True,
            )
        ]
        for format_name, message_sizes in size_results.items()
    }

    energy_results = {
        case: (
            values["energy_means"],
            values["energy_cis"],
        )
        for case, values in case_results.items()
    }

    latency_speedups = {
        (format_name, operation): [
            json_latency / alternative_latency
            for json_latency, alternative_latency in zip(
                case_results[("JSON", operation)]["latency_means"],
                case_results[(format_name, operation)]["latency_means"],
                strict=True,
            )
        ]
        for format_name in ("CBOR", "CBORKeyAsInt")
        for operation in ("Serialize", "Deserialize")
    }

    energy_reductions = {
        (format_name, operation): [
            (json_energy - alternative_energy) / json_energy * 100.0
            for json_energy, alternative_energy in zip(
                case_results[("JSON", operation)]["energy_means"],
                case_results[(format_name, operation)]["energy_means"],
                strict=True,
            )
        ]
        for format_name in ("CBOR", "CBORKeyAsInt")
        for operation in ("Serialize", "Deserialize")
    }

    interpretations = {
        "latency_speedup": {
            "serialize_cbor_min": min(latency_speedups[("CBOR", "Serialize")]),
            "serialize_cbor_max": max(latency_speedups[("CBOR", "Serialize")]),
            "serialize_cbor_int_min": min(
                latency_speedups[("CBORKeyAsInt", "Serialize")]
            ),
            "serialize_cbor_int_max": max(
                latency_speedups[("CBORKeyAsInt", "Serialize")]
            ),
            "deserialize_cbor_min": min(latency_speedups[("CBOR", "Deserialize")]),
            "deserialize_cbor_max": max(latency_speedups[("CBOR", "Deserialize")]),
            "deserialize_cbor_int_min": min(
                latency_speedups[("CBORKeyAsInt", "Deserialize")]
            ),
            "deserialize_cbor_int_max": max(
                latency_speedups[("CBORKeyAsInt", "Deserialize")]
            ),
        },
        "wire_overhead": {
            "json_first": wire_overheads["JSON"][0],
            "json_last": wire_overheads["JSON"][-1],
            "cbor_min": min(wire_overheads["CBOR"]),
            "cbor_max": max(wire_overheads["CBOR"]),
            "cbor_int_min": min(wire_overheads["CBORKeyAsInt"]),
            "cbor_int_max": max(wire_overheads["CBORKeyAsInt"]),
        },
        "energy_reduction": {
            "serialize_cbor_min": min(energy_reductions[("CBOR", "Serialize")]),
            "serialize_cbor_max": max(energy_reductions[("CBOR", "Serialize")]),
            "serialize_cbor_int_min": min(
                energy_reductions[("CBORKeyAsInt", "Serialize")]
            ),
            "serialize_cbor_int_max": max(
                energy_reductions[("CBORKeyAsInt", "Serialize")]
            ),
            "deserialize_cbor_min": min(energy_reductions[("CBOR", "Deserialize")]),
            "deserialize_cbor_max": max(energy_reductions[("CBOR", "Deserialize")]),
            "deserialize_cbor_int_min": min(
                energy_reductions[("CBORKeyAsInt", "Deserialize")]
            ),
            "deserialize_cbor_int_max": max(
                energy_reductions[("CBORKeyAsInt", "Deserialize")]
            ),
        },
    }

    plot_json_cbor_latency(
        payload_sizes,
        latency_results,
        str(result_directory / LATENCY_PLOT),
    )

    plot_json_cbor_latency_speedup(
        payload_sizes,
        latency_speedups,
        str(result_directory / LATENCY_SPEEDUP_PLOT),
    )

    plot_json_cbor_size(
        payload_sizes,
        size_results,
        str(result_directory / SIZE_PLOT),
    )

    plot_json_cbor_wire_overhead(
        payload_sizes,
        wire_overheads,
        str(result_directory / WIRE_OVERHEAD_PLOT),
    )

    plot_json_cbor_energy(
        payload_sizes,
        energy_results,
        str(result_directory / ENERGY_PLOT),
    )

    plot_json_cbor_energy_reduction(
        payload_sizes,
        energy_reductions,
        str(result_directory / ENERGY_REDUCTION_PLOT),
    )

    report_data = {
        "runs": runs,
        "payload_sizes": payload_sizes,
        "raw_sizes": raw_sizes,
        "sizes": size_results,
        "energy_window_start": warmup_duration,
        "energy_window_end": warmup_duration + measurement_duration,
        "cases": case_results,
        "interpretations": interpretations,
        "plots": {
            "latency": LATENCY_PLOT,
            "latency_speedup": LATENCY_SPEEDUP_PLOT,
            "size": SIZE_PLOT,
            "wire_overhead": WIRE_OVERHEAD_PLOT,
            "energy": ENERGY_PLOT,
            "energy_reduction": ENERGY_REDUCTION_PLOT,
        },
    }

    write_json_cbor_report(
        report_data,
        str(template_path),
        str(report_path),
    )


if __name__ == "__main__":
    main()
