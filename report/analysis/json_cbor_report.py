import os
from pathlib import Path
from typing import cast

from scipy import stats

from report.config import *
from report.model.benchmark_summary import *
from report.model.case_aggregation import *
from report.model.measurement import *
from report.analysis.shared.load_summary import *
from report.render.chart import *
from report.render.formatting import *
from report.render.html import *

NO_MEASUREMENT = float("nan")

SCENARIO = "json-cbor"
HTML_TEMPLATE_NAME = "json_cbor_template.html"

LATENCY_PLOT = "plot.png"
SIZE_PLOT = "size.png"

BENCHMARK_PREFIX = "BenchmarkEnvelope"


def collect_aggregations(
    results: BenchmarkSummary,
    attribute_counts: list[int],
) -> tuple[
    list[CaseAggregation],
    list[CaseAggregation],
    list[CaseAggregation],
    list[CaseAggregation],
    list[CaseAggregation],
    list[CaseAggregation],
]:
    json_serialize = [
        cast(
            CaseAggregation,
            results.find_aggregation("Serialize", "JSON", attribute_count),
        )
        for attribute_count in attribute_counts
    ]
    json_deserialize = [
        cast(
            CaseAggregation,
            results.find_aggregation("Deserialize", "JSON", attribute_count),
        )
        for attribute_count in attribute_counts
    ]
    cbor_serialize = [
        cast(
            CaseAggregation,
            results.find_aggregation("Serialize", "CBOR", attribute_count),
        )
        for attribute_count in attribute_counts
    ]
    cbor_deserialize = [
        cast(
            CaseAggregation,
            results.find_aggregation("Deserialize", "CBOR", attribute_count),
        )
        for attribute_count in attribute_counts
    ]
    cbor_int_serialize = [
        cast(
            CaseAggregation,
            results.find_aggregation("Serialize", "CBORKeyAsInt", attribute_count),
        )
        for attribute_count in attribute_counts
    ]
    cbor_int_deserialize = [
        cast(
            CaseAggregation,
            results.find_aggregation("Deserialize", "CBORKeyAsInt", attribute_count),
        )
        for attribute_count in attribute_counts
    ]

    return (
        json_serialize,
        json_deserialize,
        cbor_serialize,
        cbor_deserialize,
        cbor_int_serialize,
        cbor_int_deserialize,
    )


def analyze_aggregations(
    json_serialize: list[CaseAggregation],
    json_deserialize: list[CaseAggregation],
    cbor_serialize: list[CaseAggregation],
    cbor_deserialize: list[CaseAggregation],
    cbor_int_serialize: list[CaseAggregation],
    cbor_int_deserialize: list[CaseAggregation],
) -> tuple[list[float | None] | list[int | None], ...]:
    json_serialize_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in json_serialize
    ]
    json_serialize_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in json_serialize
    ]
    json_serialize_raw_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(RAW_BYTES)
        for aggregation in json_serialize
    ]
    json_serialize_envelope_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(ENVELOPE_BYTES)
        for aggregation in json_serialize
    ]
    json_serialize_envelope_size_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(ENVELOPE_BYTES)
        )
        for aggregation in json_serialize
    ]
    json_size_difference_list = [
        None if envelope is None or raw is None else envelope - raw
        for envelope, raw in zip(
            json_serialize_envelope_size_list,
            json_serialize_raw_size_list,
            strict=True,
        )
    ]
    json_serialize_overhead_percent_list = [
        None if overhead is None or raw is None else overhead / raw * 100.0
        for overhead, raw in zip(
            json_size_difference_list,
            json_serialize_raw_size_list,
            strict=True,
        )
    ]
    json_serialize_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in json_serialize
    ]

    json_deserialize_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in json_deserialize
    ]
    json_deserialize_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in json_deserialize
    ]
    json_deserialize_raw_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(RAW_BYTES)
        for aggregation in json_deserialize
    ]
    json_deserialize_envelope_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(ENVELOPE_BYTES)
        for aggregation in json_deserialize
    ]
    json_deserialize_overhead_percent_list = [
        (None if envelope is None or raw is None else (envelope - raw) / raw * 100.0)
        for envelope, raw in zip(
            json_deserialize_envelope_size_list,
            json_deserialize_raw_size_list,
            strict=True,
        )
    ]
    json_deserialize_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in json_deserialize
    ]

    cbor_serialize_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in cbor_serialize
    ]
    cbor_serialize_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in cbor_serialize
    ]
    cbor_serialize_raw_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(RAW_BYTES)
        for aggregation in cbor_serialize
    ]
    cbor_serialize_envelope_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(ENVELOPE_BYTES)
        for aggregation in cbor_serialize
    ]
    cbor_serialize_envelope_size_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(ENVELOPE_BYTES)
        )
        for aggregation in cbor_serialize
    ]
    cbor_size_difference_list = [
        None if envelope is None or raw is None else envelope - raw
        for envelope, raw in zip(
            cbor_serialize_envelope_size_list,
            cbor_serialize_raw_size_list,
            strict=True,
        )
    ]
    cbor_serialize_overhead_percent_list = [
        None if overhead is None or raw is None else overhead / raw * 100.0
        for overhead, raw in zip(
            cbor_size_difference_list,
            cbor_serialize_raw_size_list,
            strict=True,
        )
    ]
    cbor_serialize_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in cbor_serialize
    ]

    cbor_deserialize_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in cbor_deserialize
    ]
    cbor_deserialize_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in cbor_deserialize
    ]
    cbor_deserialize_raw_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(RAW_BYTES)
        for aggregation in cbor_deserialize
    ]
    cbor_deserialize_envelope_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(ENVELOPE_BYTES)
        for aggregation in cbor_deserialize
    ]
    cbor_deserialize_overhead_percent_list = [
        (None if envelope is None or raw is None else (envelope - raw) / raw * 100.0)
        for envelope, raw in zip(
            cbor_deserialize_envelope_size_list,
            cbor_deserialize_raw_size_list,
            strict=True,
        )
    ]
    cbor_deserialize_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in cbor_deserialize
    ]

    cbor_int_serialize_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in cbor_int_serialize
    ]
    cbor_int_serialize_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in cbor_int_serialize
    ]
    cbor_int_serialize_raw_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(RAW_BYTES)
        for aggregation in cbor_int_serialize
    ]
    cbor_int_serialize_envelope_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(ENVELOPE_BYTES)
        for aggregation in cbor_int_serialize
    ]
    cbor_int_serialize_envelope_size_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(ENVELOPE_BYTES)
        )
        for aggregation in cbor_int_serialize
    ]
    cbor_int_size_difference_list = [
        None if envelope is None or raw is None else envelope - raw
        for envelope, raw in zip(
            cbor_int_serialize_envelope_size_list,
            cbor_int_serialize_raw_size_list,
            strict=True,
        )
    ]
    cbor_int_serialize_overhead_percent_list = [
        None if overhead is None or raw is None else overhead / raw * 100.0
        for overhead, raw in zip(
            cbor_int_size_difference_list,
            cbor_int_serialize_raw_size_list,
            strict=True,
        )
    ]
    cbor_int_serialize_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in cbor_int_serialize
    ]

    cbor_int_deserialize_latency_list = [
        None if aggregation.out_of_memory else aggregation.mean(NS_PER_OP)
        for aggregation in cbor_int_deserialize
    ]
    cbor_int_deserialize_latency_ci_list = [
        (
            None
            if aggregation.out_of_memory
            else aggregation.confidence_interval(NS_PER_OP)
        )
        for aggregation in cbor_int_deserialize
    ]
    cbor_int_deserialize_raw_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(RAW_BYTES)
        for aggregation in cbor_int_deserialize
    ]
    cbor_int_deserialize_envelope_size_list = [
        None if aggregation.out_of_memory else aggregation.mean(ENVELOPE_BYTES)
        for aggregation in cbor_int_deserialize
    ]
    cbor_int_deserialize_overhead_percent_list = [
        (None if envelope is None or raw is None else (envelope - raw) / raw * 100.0)
        for envelope, raw in zip(
            cbor_int_deserialize_envelope_size_list,
            cbor_int_deserialize_raw_size_list,
            strict=True,
        )
    ]
    cbor_int_deserialize_iteration_list = [
        None if aggregation.out_of_memory else aggregation.iterations
        for aggregation in cbor_int_deserialize
    ]

    return (
        json_serialize_latency_list,
        json_serialize_latency_ci_list,
        json_serialize_raw_size_list,
        json_serialize_envelope_size_list,
        json_serialize_envelope_size_ci_list,
        json_size_difference_list,
        json_serialize_overhead_percent_list,
        json_serialize_iteration_list,
        json_deserialize_latency_list,
        json_deserialize_latency_ci_list,
        json_deserialize_raw_size_list,
        json_deserialize_envelope_size_list,
        json_deserialize_overhead_percent_list,
        json_deserialize_iteration_list,
        cbor_serialize_latency_list,
        cbor_serialize_latency_ci_list,
        cbor_serialize_raw_size_list,
        cbor_serialize_envelope_size_list,
        cbor_serialize_envelope_size_ci_list,
        cbor_size_difference_list,
        cbor_serialize_overhead_percent_list,
        cbor_serialize_iteration_list,
        cbor_deserialize_latency_list,
        cbor_deserialize_latency_ci_list,
        cbor_deserialize_raw_size_list,
        cbor_deserialize_envelope_size_list,
        cbor_deserialize_overhead_percent_list,
        cbor_deserialize_iteration_list,
        cbor_int_serialize_latency_list,
        cbor_int_serialize_latency_ci_list,
        cbor_int_serialize_raw_size_list,
        cbor_int_serialize_envelope_size_list,
        cbor_int_serialize_envelope_size_ci_list,
        cbor_int_size_difference_list,
        cbor_int_serialize_overhead_percent_list,
        cbor_int_serialize_iteration_list,
        cbor_int_deserialize_latency_list,
        cbor_int_deserialize_latency_ci_list,
        cbor_int_deserialize_raw_size_list,
        cbor_int_deserialize_envelope_size_list,
        cbor_int_deserialize_overhead_percent_list,
        cbor_int_deserialize_iteration_list,
    )


def main() -> None:
    runs = parse_int_env("JSON_CBOR_RUNS")
    attribute_counts = parse_int_list_env("JSON_CBOR_ATTRIBUTE_COUNTS")

    result_dir = Path(
        os.environ.get("JSON_CBOR_RESULT_DIR", f"{DEFAULT_RESULT_ROOT}/{SCENARIO}")
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    case_status = result_dir / CASE_STATUS_NAME
    template_path = Path(TEMPLATE_DIR) / HTML_TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "Attrs")
    load_out_of_memory_status(results, str(case_status))

    (
        json_serialize,
        json_deserialize,
        cbor_serialize,
        cbor_deserialize,
        cbor_int_serialize,
        cbor_int_deserialize,
    ) = collect_aggregations(results, attribute_counts)

    (
        json_serialize_latency_list,
        json_serialize_latency_ci_list,
        json_serialize_raw_size_list,
        json_serialize_envelope_size_list,
        json_serialize_envelope_size_ci_list,
        json_size_difference_list,
        json_serialize_overhead_percent_list,
        json_serialize_iteration_list,
        json_deserialize_latency_list,
        json_deserialize_latency_ci_list,
        json_deserialize_raw_size_list,
        json_deserialize_envelope_size_list,
        json_deserialize_overhead_percent_list,
        json_deserialize_iteration_list,
        cbor_serialize_latency_list,
        cbor_serialize_latency_ci_list,
        cbor_serialize_raw_size_list,
        cbor_serialize_envelope_size_list,
        cbor_serialize_envelope_size_ci_list,
        cbor_size_difference_list,
        cbor_serialize_overhead_percent_list,
        cbor_serialize_iteration_list,
        cbor_deserialize_latency_list,
        cbor_deserialize_latency_ci_list,
        cbor_deserialize_raw_size_list,
        cbor_deserialize_envelope_size_list,
        cbor_deserialize_overhead_percent_list,
        cbor_deserialize_iteration_list,
        cbor_int_serialize_latency_list,
        cbor_int_serialize_latency_ci_list,
        cbor_int_serialize_raw_size_list,
        cbor_int_serialize_envelope_size_list,
        cbor_int_serialize_envelope_size_ci_list,
        cbor_int_size_difference_list,
        cbor_int_serialize_overhead_percent_list,
        cbor_int_serialize_iteration_list,
        cbor_int_deserialize_latency_list,
        cbor_int_deserialize_latency_ci_list,
        cbor_int_deserialize_raw_size_list,
        cbor_int_deserialize_envelope_size_list,
        cbor_int_deserialize_overhead_percent_list,
        cbor_int_deserialize_iteration_list,
    ) = analyze_aggregations(
        json_serialize,
        json_deserialize,
        cbor_serialize,
        cbor_deserialize,
        cbor_int_serialize,
        cbor_int_deserialize,
    )

    total_benchmark_iterations = sum(
        aggregation.iterations
        for aggregation in results.aggregations
        if not aggregation.out_of_memory
    )
    out_of_memory_aggregations = [
        aggregation for aggregation in results.aggregations if aggregation.out_of_memory
    ]

    plot_json_cbor_latency(
        attribute_counts,
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in json_serialize_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in json_serialize_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in cbor_serialize_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in cbor_serialize_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in cbor_int_serialize_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in cbor_int_serialize_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in json_deserialize_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in json_deserialize_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in cbor_deserialize_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in cbor_deserialize_latency_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in cbor_int_deserialize_latency_list
        ],
        [
            NO_MEASUREMENT if value is None else value / NS_PER_MICROSECOND
            for value in cbor_int_deserialize_latency_ci_list
        ],
        str(result_dir / LATENCY_PLOT),
    )

    plot_json_cbor_size(
        attribute_counts,
        [
            NO_MEASUREMENT if value is None else value
            for value in json_serialize_envelope_size_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in json_serialize_envelope_size_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in json_size_difference_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in cbor_serialize_envelope_size_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in cbor_serialize_envelope_size_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in cbor_size_difference_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in cbor_int_serialize_envelope_size_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in cbor_int_serialize_envelope_size_ci_list
        ],
        [
            NO_MEASUREMENT if value is None else value
            for value in cbor_int_size_difference_list
        ],
        str(result_dir / SIZE_PLOT),
    )

    write_json_cbor_report(
        runs=runs,
        t_multiplier=float(stats.t.ppf(0.975, runs - 1)),
        total_iterations=total_benchmark_iterations,
        attribute_counts=attribute_counts,
        json_serialize_latency_means=json_serialize_latency_list,
        json_serialize_latency_cis=json_serialize_latency_ci_list,
        json_serialize_raw_sizes=json_serialize_raw_size_list,
        json_serialize_envelope_sizes=json_serialize_envelope_size_list,
        json_serialize_overhead_percents=json_serialize_overhead_percent_list,
        json_serialize_iterations=json_serialize_iteration_list,
        json_serialize_throttled=results.get_throttle_flags(
            "Serialize", "JSON", attribute_counts
        ),
        cbor_serialize_latency_means=cbor_serialize_latency_list,
        cbor_serialize_latency_cis=cbor_serialize_latency_ci_list,
        cbor_serialize_raw_sizes=cbor_serialize_raw_size_list,
        cbor_serialize_envelope_sizes=cbor_serialize_envelope_size_list,
        cbor_serialize_overhead_percents=cbor_serialize_overhead_percent_list,
        cbor_serialize_iterations=cbor_serialize_iteration_list,
        cbor_serialize_throttled=results.get_throttle_flags(
            "Serialize", "CBOR", attribute_counts
        ),
        cbor_int_serialize_latency_means=cbor_int_serialize_latency_list,
        cbor_int_serialize_latency_cis=cbor_int_serialize_latency_ci_list,
        cbor_int_serialize_raw_sizes=cbor_int_serialize_raw_size_list,
        cbor_int_serialize_envelope_sizes=cbor_int_serialize_envelope_size_list,
        cbor_int_serialize_overhead_percents=cbor_int_serialize_overhead_percent_list,
        cbor_int_serialize_iterations=cbor_int_serialize_iteration_list,
        cbor_int_serialize_throttled=results.get_throttle_flags(
            "Serialize", "CBORKeyAsInt", attribute_counts
        ),
        json_deserialize_latency_means=json_deserialize_latency_list,
        json_deserialize_latency_cis=json_deserialize_latency_ci_list,
        json_deserialize_raw_sizes=json_deserialize_raw_size_list,
        json_deserialize_envelope_sizes=json_deserialize_envelope_size_list,
        json_deserialize_overhead_percents=json_deserialize_overhead_percent_list,
        json_deserialize_iterations=json_deserialize_iteration_list,
        json_deserialize_throttled=results.get_throttle_flags(
            "Deserialize", "JSON", attribute_counts
        ),
        cbor_deserialize_latency_means=cbor_deserialize_latency_list,
        cbor_deserialize_latency_cis=cbor_deserialize_latency_ci_list,
        cbor_deserialize_raw_sizes=cbor_deserialize_raw_size_list,
        cbor_deserialize_envelope_sizes=cbor_deserialize_envelope_size_list,
        cbor_deserialize_overhead_percents=cbor_deserialize_overhead_percent_list,
        cbor_deserialize_iterations=cbor_deserialize_iteration_list,
        cbor_deserialize_throttled=results.get_throttle_flags(
            "Deserialize", "CBOR", attribute_counts
        ),
        cbor_int_deserialize_latency_means=cbor_int_deserialize_latency_list,
        cbor_int_deserialize_latency_cis=cbor_int_deserialize_latency_ci_list,
        cbor_int_deserialize_raw_sizes=cbor_int_deserialize_raw_size_list,
        cbor_int_deserialize_envelope_sizes=cbor_int_deserialize_envelope_size_list,
        cbor_int_deserialize_overhead_percents=cbor_int_deserialize_overhead_percent_list,
        cbor_int_deserialize_iterations=cbor_int_deserialize_iteration_list,
        cbor_int_deserialize_throttled=results.get_throttle_flags(
            "Deserialize", "CBORKeyAsInt", attribute_counts
        ),
        out_of_memory_operations=[
            aggregation.operation for aggregation in out_of_memory_aggregations
        ],
        out_of_memory_cases=[
            f"{aggregation.parameter}/{aggregation.parameter_value}"
            for aggregation in out_of_memory_aggregations
        ],
        latency_plot=LATENCY_PLOT,
        size_plot=SIZE_PLOT,
        template_path=str(template_path),
        report_path=str(report_path),
    )


if __name__ == "__main__":
    main()
