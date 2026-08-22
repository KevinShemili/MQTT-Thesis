import os
from pathlib import Path

from template_builder.chart import *
from template_builder.formatting import *
from template_builder.html import *

from model.benchmark_summary import *
from model.measurement import *
from model.populate_model import *

from config.environment import *
from statistics_tbd.summary import *

SCENARIO = "aes-ascon"
HTML_TEMPLATE_NAME = "aes_ascon_template.html"

LATENCY_PLOT = "plot.png"
THROUGHPUT_PLOT = "throughput.png"

BENCHMARK_PREFIX = "BenchmarkAESASCON"


def main() -> None:
    runs = parse_int_env("AES_ASCON_RUNS")
    payload_sizes = parse_int_list_env("AES_ASCON_PAYLOAD_SIZES")

    result_dir = Path(
        os.environ.get("AES_ASCON_RESULT_DIR", f"{DEFAULT_RESULT_ROOT}/{SCENARIO}")
    )
    bench_output = result_dir / BENCH_OUTPUT_NAME
    template_path = Path(TEMPLATE_DIR) / HTML_TEMPLATE_NAME
    report_path = result_dir / REPORT_NAME

    # Create object and load benchmark results into it
    results = BenchmarkSummary()
    load_results(results, str(bench_output), BENCHMARK_PREFIX, "B")

    aes_encrypt = [
        results.find_aggregation("Encrypt", "AES-GCM", payload_size)
        for payload_size in payload_sizes
    ]
    ascon_encrypt = [
        results.find_aggregation("Encrypt", "ASCON", payload_size)
        for payload_size in payload_sizes
    ]
    aes_decrypt = [
        results.find_aggregation("Decrypt", "AES-GCM", payload_size)
        for payload_size in payload_sizes
    ]
    ascon_decrypt = [
        results.find_aggregation("Decrypt", "ASCON", payload_size)
        for payload_size in payload_sizes
    ]
    assert all(aggregation is not None for aggregation in aes_encrypt)
    assert all(aggregation is not None for aggregation in ascon_encrypt)
    assert all(aggregation is not None for aggregation in aes_decrypt)
    assert all(aggregation is not None for aggregation in ascon_decrypt)

    aes_encrypt = [
        aggregation for aggregation in aes_encrypt if aggregation is not None
    ]
    ascon_encrypt = [
        aggregation for aggregation in ascon_encrypt if aggregation is not None
    ]
    aes_decrypt = [
        aggregation for aggregation in aes_decrypt if aggregation is not None
    ]
    ascon_decrypt = [
        aggregation for aggregation in ascon_decrypt if aggregation is not None
    ]

    aes_encrypt_latency_ns = [
        aggregation.mean(NS_PER_OP) for aggregation in aes_encrypt
    ]
    aes_encrypt_latency_cis_ns = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in aes_encrypt
    ]
    ascon_encrypt_latency_ns = [
        aggregation.mean(NS_PER_OP) for aggregation in ascon_encrypt
    ]
    ascon_encrypt_latency_cis_ns = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in ascon_encrypt
    ]
    aes_decrypt_latency_ns = [
        aggregation.mean(NS_PER_OP) for aggregation in aes_decrypt
    ]
    aes_decrypt_latency_cis_ns = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in aes_decrypt
    ]
    ascon_decrypt_latency_ns = [
        aggregation.mean(NS_PER_OP) for aggregation in ascon_decrypt
    ]
    ascon_decrypt_latency_cis_ns = [
        aggregation.confidence_interval(NS_PER_OP) for aggregation in ascon_decrypt
    ]

    aes_encrypt_throughput = [
        aggregation.mean(MB_PER_SECOND) for aggregation in aes_encrypt
    ]
    aes_encrypt_throughput_cis = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in aes_encrypt
    ]
    ascon_encrypt_throughput = [
        aggregation.mean(MB_PER_SECOND) for aggregation in ascon_encrypt
    ]
    ascon_encrypt_throughput_cis = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in ascon_encrypt
    ]
    aes_decrypt_throughput = [
        aggregation.mean(MB_PER_SECOND) for aggregation in aes_decrypt
    ]
    aes_decrypt_throughput_cis = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in aes_decrypt
    ]
    ascon_decrypt_throughput = [
        aggregation.mean(MB_PER_SECOND) for aggregation in ascon_decrypt
    ]
    ascon_decrypt_throughput_cis = [
        aggregation.confidence_interval(MB_PER_SECOND) for aggregation in ascon_decrypt
    ]

    plot_aes_ascon_latency(
        payload_sizes,
        [value / NS_PER_MICROSECOND for value in aes_encrypt_latency_ns],
        [value / NS_PER_MICROSECOND for value in aes_encrypt_latency_cis_ns],
        [value / NS_PER_MICROSECOND for value in ascon_encrypt_latency_ns],
        [value / NS_PER_MICROSECOND for value in ascon_encrypt_latency_cis_ns],
        [value / NS_PER_MICROSECOND for value in aes_decrypt_latency_ns],
        [value / NS_PER_MICROSECOND for value in aes_decrypt_latency_cis_ns],
        [value / NS_PER_MICROSECOND for value in ascon_decrypt_latency_ns],
        [value / NS_PER_MICROSECOND for value in ascon_decrypt_latency_cis_ns],
        str(result_dir / LATENCY_PLOT),
    )
    plot_aes_ascon_throughput(
        payload_sizes,
        aes_encrypt_throughput,
        aes_encrypt_throughput_cis,
        ascon_encrypt_throughput,
        ascon_encrypt_throughput_cis,
        aes_decrypt_throughput,
        aes_decrypt_throughput_cis,
        ascon_decrypt_throughput,
        ascon_decrypt_throughput_cis,
        str(result_dir / THROUGHPUT_PLOT),
    )

    write_aes_ascon_report(
        runs=runs,
        t_multiplier=get_student_t_critical_95(runs - 1),
        total_iterations=sum(
            aggregation.iterations for aggregation in results.aggregations
        ),
        payload_sizes=payload_sizes,
        aes_encrypt_latency_means=aes_encrypt_latency_ns,
        aes_encrypt_latency_cis=aes_encrypt_latency_cis_ns,
        aes_encrypt_throughput_means=aes_encrypt_throughput,
        aes_encrypt_throughput_cis=aes_encrypt_throughput_cis,
        aes_encrypt_overhead_bytes=[
            aggregation.mean(WIRE_OVERHEAD_BYTES) for aggregation in aes_encrypt
        ],
        aes_encrypt_iterations=[aggregation.iterations for aggregation in aes_encrypt],
        aes_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", "AES-GCM", payload_sizes
        ),
        ascon_encrypt_latency_means=ascon_encrypt_latency_ns,
        ascon_encrypt_latency_cis=ascon_encrypt_latency_cis_ns,
        ascon_encrypt_throughput_means=ascon_encrypt_throughput,
        ascon_encrypt_throughput_cis=ascon_encrypt_throughput_cis,
        ascon_encrypt_overhead_bytes=[
            aggregation.mean(WIRE_OVERHEAD_BYTES) for aggregation in ascon_encrypt
        ],
        ascon_encrypt_iterations=[
            aggregation.iterations for aggregation in ascon_encrypt
        ],
        ascon_encrypt_throttled=results.get_throttle_flags(
            "Encrypt", "ASCON", payload_sizes
        ),
        aes_decrypt_latency_means=aes_decrypt_latency_ns,
        aes_decrypt_latency_cis=aes_decrypt_latency_cis_ns,
        aes_decrypt_throughput_means=aes_decrypt_throughput,
        aes_decrypt_throughput_cis=aes_decrypt_throughput_cis,
        aes_decrypt_overhead_bytes=[
            aggregation.mean(WIRE_OVERHEAD_BYTES) for aggregation in aes_decrypt
        ],
        aes_decrypt_iterations=[aggregation.iterations for aggregation in aes_decrypt],
        aes_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", "AES-GCM", payload_sizes
        ),
        ascon_decrypt_latency_means=ascon_decrypt_latency_ns,
        ascon_decrypt_latency_cis=ascon_decrypt_latency_cis_ns,
        ascon_decrypt_throughput_means=ascon_decrypt_throughput,
        ascon_decrypt_throughput_cis=ascon_decrypt_throughput_cis,
        ascon_decrypt_overhead_bytes=[
            aggregation.mean(WIRE_OVERHEAD_BYTES) for aggregation in ascon_decrypt
        ],
        ascon_decrypt_iterations=[
            aggregation.iterations for aggregation in ascon_decrypt
        ],
        ascon_decrypt_throttled=results.get_throttle_flags(
            "Decrypt", "ASCON", payload_sizes
        ),
        latency_plot=LATENCY_PLOT,
        throughput_plot=THROUGHPUT_PLOT,
        template_path=str(template_path),
        report_path=str(report_path),
    )


if __name__ == "__main__":
    main()
