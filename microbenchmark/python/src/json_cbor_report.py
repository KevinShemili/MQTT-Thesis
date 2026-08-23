import os
from typing import cast
from pathlib import Path

from scipy import stats

from template_builder.chart import *
from template_builder.formatting import *
from template_builder.html import *

from model.benchmark_summary import *
from model.measurement import *
from model.populate_model import *

from config.environment import *

SCENARIO = "json-cbor"
HTML_TEMPLATE_NAME = "json_cbor_template.html"

LATENCY_PLOT = "plot.png"
SIZE_PLOT = "size.png"

BENCHMARK_PREFIX = "BenchmarkEnvelope"


def main() -> None:
    runs = parse_int_env("JSON_CBOR_RUNS")
    attribute_counts = parse_int_list_env("JSON_CBOR_ATTRIBUTE_COUNTS")

    result_dir = Path(
        os.environ.get("JSON_CBOR_RESULT_DIR", f"{DEFAULT_RESULT_ROOT}/{SCENARIO}")
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    template_path = Path(TEMPLATE_DIR) / HTML_TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "Attrs")

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

    # JSON Calculations
    # 1. Latency of Serialize and Deserialize
    json_serialize_latency_list = [
        aggregation.mean(NS_PER_OP) for aggregation in json_serialize
    ]
    json_serialize_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in json_serialize
    ]
    json_deserialize_latency_list = [
        aggregation.mean(NS_PER_OP) for aggregation in json_deserialize
    ]
    json_deserialize_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in json_deserialize
    ]
    # 2. Raw and Envelope Sizes of Serialize and Deserialize
    json_serialize_raw_size_list = [
        aggregation.mean(RAW_BYTES) for aggregation in json_serialize
    ]
    json_serialize_envelope_size_list = [
        aggregation.mean(ENVELOPE_BYTES) for aggregation in json_serialize
    ]
    json_serialize_envelope_size_ci_list = [
        aggregation.confidence_interval(ENVELOPE_BYTES)
        for aggregation in json_serialize
    ]
    json_deserialize_raw_size_list = [
        aggregation.mean(RAW_BYTES) for aggregation in json_deserialize
    ]
    json_deserialize_envelope_size_list = [
        aggregation.mean(ENVELOPE_BYTES) for aggregation in json_deserialize
    ]
    # 3. Overhead of Serialize and Deserialize
    # - First calculate the size difference between envelope and raw sizes
    json_size_difference_list = [
        envelope - raw
        for envelope, raw in zip(
            json_serialize_envelope_size_list,
            json_serialize_raw_size_list,
            strict=True,
        )
    ]
    # - Then calculate how much overhead does serialization introduce on top of raw size
    json_serialize_overhead_percent_list = [
        overhead / raw * 100.0
        for overhead, raw in zip(
            json_size_difference_list,
            json_serialize_raw_size_list,
            strict=True,
        )
    ]
    # - Finally calculate how much overhead does deserialization introduce on top of raw size
    json_deserialize_overhead_percent_list = [
        (envelope - raw) / raw * 100.0
        for envelope, raw in zip(
            json_deserialize_envelope_size_list,
            json_deserialize_raw_size_list,
            strict=True,
        )
    ]
    # 4. Iterations of Serialize and Deserialize
    json_serialize_iteration_list = [
        aggregation.iterations for aggregation in json_serialize
    ]
    json_deserialize_iteration_list = [
        aggregation.iterations for aggregation in json_deserialize
    ]
    # 5. Throttle Check of Serialize and Deserialize
    json_serialize_throttled_list = results.get_throttle_flags(
        "Serialize", "JSON", attribute_counts
    )
    json_deserialize_throttled_list = results.get_throttle_flags(
        "Deserialize", "JSON", attribute_counts
    )

    # CBOR Calculations
    # 1. Latency of Serialize and Deserialize
    cbor_serialize_latency_list = [
        aggregation.mean(NS_PER_OP) for aggregation in cbor_serialize
    ]
    cbor_serialize_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in cbor_serialize
    ]
    cbor_deserialize_latency_list = [
        aggregation.mean(NS_PER_OP) for aggregation in cbor_deserialize
    ]
    cbor_deserialize_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in cbor_deserialize
    ]
    # 2. Raw and Envelope Sizes of Serialize and Deserialize
    cbor_serialize_raw_size_list = [
        aggregation.mean(RAW_BYTES) for aggregation in cbor_serialize
    ]
    cbor_serialize_envelope_size_list = [
        aggregation.mean(ENVELOPE_BYTES) for aggregation in cbor_serialize
    ]
    cbor_serialize_envelope_size_ci_list = [
        aggregation.confidence_interval(ENVELOPE_BYTES)
        for aggregation in cbor_serialize
    ]
    cbor_deserialize_raw_size_list = [
        aggregation.mean(RAW_BYTES) for aggregation in cbor_deserialize
    ]
    cbor_deserialize_envelope_size_list = [
        aggregation.mean(ENVELOPE_BYTES) for aggregation in cbor_deserialize
    ]
    # 3. Overhead of Serialize and Deserialize
    cbor_size_difference_list = [
        envelope - raw
        for envelope, raw in zip(
            cbor_serialize_envelope_size_list,
            cbor_serialize_raw_size_list,
            strict=True,
        )
    ]
    cbor_serialize_overhead_percent_list = [
        overhead / raw * 100.0
        for overhead, raw in zip(
            cbor_size_difference_list,
            cbor_serialize_raw_size_list,
            strict=True,
        )
    ]
    cbor_deserialize_overhead_percent_list = [
        (envelope - raw) / raw * 100.0
        for envelope, raw in zip(
            cbor_deserialize_envelope_size_list,
            cbor_deserialize_raw_size_list,
            strict=True,
        )
    ]
    # 4. Iterations of Serialize and Deserialize
    cbor_serialize_iteration_list = [
        aggregation.iterations for aggregation in cbor_serialize
    ]
    cbor_deserialize_iteration_list = [
        aggregation.iterations for aggregation in cbor_deserialize
    ]
    # 5. Throttle Check of Serialize and Deserialize
    cbor_serialize_throttled_list = results.get_throttle_flags(
        "Serialize", "CBOR", attribute_counts
    )
    cbor_deserialize_throttled_list = results.get_throttle_flags(
        "Deserialize", "CBOR", attribute_counts
    )

    # CBOR Calculations - Integer Keys Variant
    cbor_int_serialize_latency_list = [
        aggregation.mean(NS_PER_OP) for aggregation in cbor_int_serialize
    ]
    cbor_int_serialize_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in cbor_int_serialize
    ]
    cbor_int_deserialize_latency_list = [
        aggregation.mean(NS_PER_OP) for aggregation in cbor_int_deserialize
    ]
    cbor_int_deserialize_latency_ci_list = [
        aggregation.confidence_interval(NS_PER_OP)
        for aggregation in cbor_int_deserialize
    ]
    # 2. Raw and Envelope Sizes of Serialize and Deserialize
    cbor_int_serialize_raw_size_list = [
        aggregation.mean(RAW_BYTES) for aggregation in cbor_int_serialize
    ]
    cbor_int_serialize_envelope_size_list = [
        aggregation.mean(ENVELOPE_BYTES) for aggregation in cbor_int_serialize
    ]
    cbor_int_serialize_envelope_size_ci_list = [
        aggregation.confidence_interval(ENVELOPE_BYTES)
        for aggregation in cbor_int_serialize
    ]
    cbor_int_deserialize_raw_size_list = [
        aggregation.mean(RAW_BYTES) for aggregation in cbor_int_deserialize
    ]
    cbor_int_deserialize_envelope_size_list = [
        aggregation.mean(ENVELOPE_BYTES) for aggregation in cbor_int_deserialize
    ]
    # 3. Overhead of Serialize and Deserialize
    cbor_int_size_difference_list = [
        envelope - raw
        for envelope, raw in zip(
            cbor_int_serialize_envelope_size_list,
            cbor_int_serialize_raw_size_list,
            strict=True,
        )
    ]
    cbor_int_serialize_overhead_percent_list = [
        overhead / raw * 100.0
        for overhead, raw in zip(
            cbor_int_size_difference_list,
            cbor_int_serialize_raw_size_list,
            strict=True,
        )
    ]
    cbor_int_deserialize_overhead_percent_list = [
        (envelope - raw) / raw * 100.0
        for envelope, raw in zip(
            cbor_int_deserialize_envelope_size_list,
            cbor_int_deserialize_raw_size_list,
            strict=True,
        )
    ]
    # 4. Iterations of Serialize and Deserialize
    cbor_int_serialize_iteration_list = [
        aggregation.iterations for aggregation in cbor_int_serialize
    ]
    cbor_int_deserialize_iteration_list = [
        aggregation.iterations for aggregation in cbor_int_deserialize
    ]
    # 5. Throttle Check of Serialize and Deserialize
    cbor_int_serialize_throttled_list = results.get_throttle_flags(
        "Serialize", "CBORKeyAsInt", attribute_counts
    )
    cbor_int_deserialize_throttled_list = results.get_throttle_flags(
        "Deserialize", "CBORKeyAsInt", attribute_counts
    )

    total_benchmark_iterations = sum(
        aggregation.iterations for aggregation in results.aggregations
    )

    # Generate the latency graph (Divided by 1000 to convert from ns to us)
    plot_json_cbor_latency(
        attribute_counts,
        [value / NS_PER_MICROSECOND for value in json_serialize_latency_list],
        [value / NS_PER_MICROSECOND for value in json_serialize_latency_ci_list],
        [value / NS_PER_MICROSECOND for value in cbor_serialize_latency_list],
        [value / NS_PER_MICROSECOND for value in cbor_serialize_latency_ci_list],
        [value / NS_PER_MICROSECOND for value in cbor_int_serialize_latency_list],
        [value / NS_PER_MICROSECOND for value in cbor_int_serialize_latency_ci_list],
        [value / NS_PER_MICROSECOND for value in json_deserialize_latency_list],
        [value / NS_PER_MICROSECOND for value in json_deserialize_latency_ci_list],
        [value / NS_PER_MICROSECOND for value in cbor_deserialize_latency_list],
        [value / NS_PER_MICROSECOND for value in cbor_deserialize_latency_ci_list],
        [value / NS_PER_MICROSECOND for value in cbor_int_deserialize_latency_list],
        [value / NS_PER_MICROSECOND for value in cbor_int_deserialize_latency_ci_list],
        str(result_dir / LATENCY_PLOT),
    )

    # Generate the size graph
    plot_json_cbor_size(
        attribute_counts,
        json_serialize_envelope_size_list,
        json_serialize_envelope_size_ci_list,
        json_size_difference_list,
        cbor_serialize_envelope_size_list,
        cbor_serialize_envelope_size_ci_list,
        cbor_size_difference_list,
        cbor_int_serialize_envelope_size_list,
        cbor_int_serialize_envelope_size_ci_list,
        cbor_int_size_difference_list,
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
        json_serialize_throttled=json_serialize_throttled_list,
        cbor_serialize_latency_means=cbor_serialize_latency_list,
        cbor_serialize_latency_cis=cbor_serialize_latency_ci_list,
        cbor_serialize_raw_sizes=cbor_serialize_raw_size_list,
        cbor_serialize_envelope_sizes=cbor_serialize_envelope_size_list,
        cbor_serialize_overhead_percents=cbor_serialize_overhead_percent_list,
        cbor_serialize_iterations=cbor_serialize_iteration_list,
        cbor_serialize_throttled=cbor_serialize_throttled_list,
        cbor_int_serialize_latency_means=cbor_int_serialize_latency_list,
        cbor_int_serialize_latency_cis=cbor_int_serialize_latency_ci_list,
        cbor_int_serialize_raw_sizes=cbor_int_serialize_raw_size_list,
        cbor_int_serialize_envelope_sizes=cbor_int_serialize_envelope_size_list,
        cbor_int_serialize_overhead_percents=cbor_int_serialize_overhead_percent_list,
        cbor_int_serialize_iterations=cbor_int_serialize_iteration_list,
        cbor_int_serialize_throttled=cbor_int_serialize_throttled_list,
        json_deserialize_latency_means=json_deserialize_latency_list,
        json_deserialize_latency_cis=json_deserialize_latency_ci_list,
        json_deserialize_raw_sizes=json_deserialize_raw_size_list,
        json_deserialize_envelope_sizes=json_deserialize_envelope_size_list,
        json_deserialize_overhead_percents=json_deserialize_overhead_percent_list,
        json_deserialize_iterations=json_deserialize_iteration_list,
        json_deserialize_throttled=json_deserialize_throttled_list,
        cbor_deserialize_latency_means=cbor_deserialize_latency_list,
        cbor_deserialize_latency_cis=cbor_deserialize_latency_ci_list,
        cbor_deserialize_raw_sizes=cbor_deserialize_raw_size_list,
        cbor_deserialize_envelope_sizes=cbor_deserialize_envelope_size_list,
        cbor_deserialize_overhead_percents=cbor_deserialize_overhead_percent_list,
        cbor_deserialize_iterations=cbor_deserialize_iteration_list,
        cbor_deserialize_throttled=cbor_deserialize_throttled_list,
        cbor_int_deserialize_latency_means=cbor_int_deserialize_latency_list,
        cbor_int_deserialize_latency_cis=cbor_int_deserialize_latency_ci_list,
        cbor_int_deserialize_raw_sizes=cbor_int_deserialize_raw_size_list,
        cbor_int_deserialize_envelope_sizes=cbor_int_deserialize_envelope_size_list,
        cbor_int_deserialize_overhead_percents=cbor_int_deserialize_overhead_percent_list,
        cbor_int_deserialize_iterations=cbor_int_deserialize_iteration_list,
        cbor_int_deserialize_throttled=cbor_int_deserialize_throttled_list,
        latency_plot=LATENCY_PLOT,
        size_plot=SIZE_PLOT,
        template_path=str(template_path),
        report_path=str(report_path),
    )


if __name__ == "__main__":
    main()
