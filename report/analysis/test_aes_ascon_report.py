import report.analysis.aes_ascon_report as sut


def test_main_calls_expected_report_stages(monkeypatch, tmp_path):

    # Arrange
    monkeypatch.setenv("AES_ASCON_RUNS", "1")
    monkeypatch.setenv("PAYLOAD_SIZES", "256")
    monkeypatch.setenv("WARMUP_DURATION", "1")
    monkeypatch.setenv("MEASUREMENT_DURATION", "1")
    monkeypatch.setenv("AES_ASCON_RESULT_DIR", "results")

    monkeypatch.setattr(
        sut,
        "ENVIRONMENT_FILE",
        tmp_path / "missing.env",
    )
    monkeypatch.setattr(
        sut,
        "PROJECT_ROOT",
        tmp_path,
    )
    monkeypatch.setattr(
        sut,
        "TEMPLATE_DIR",
        tmp_path / "templates",
    )

    calls = []

    class FakeSummary:

        energy_baseline_cases = []
        memory_baseline_cases = []

        def find_timing_aggregation(
            self,
            algorithm,
            operation,
            parameter,
            parameter_value,
        ):
            return algorithm, operation

        def find_energy_aggregation(
            self,
            algorithm,
            operation,
            parameter,
            parameter_value,
        ):
            return algorithm, operation

        def find_memory_aggregation(
            self,
            algorithm,
            operation,
            parameter,
            parameter_value,
        ):
            return algorithm, operation

    def fake_load_summary(**kwargs):

        calls.append("load summary")

        return FakeSummary()

    def fake_analyze_case(
        timing_aggregations,
        energy_aggregations,
        energy_baseline_cases,
    ):

        algorithm, operation = timing_aggregations[0]

        calls.append(f"analyze {algorithm} {operation}")

        # Only enough data for main() to continue its calculations.
        return {
            "latency_means": [1.0],
            "latency_cis": [0.0],
            "throughput_means": [1.0],
            "throughput_cis": [0.0],
            "energy_means": [1.0],
            "energy_cis": [0.0],
            "timing_throttled": [False],
            "energy_throttled": [False],
        }

    def fake_analyze_memory_case(memory_aggregations):

        algorithm, operation = memory_aggregations[0]

        calls.append(f"analyze memory {algorithm} {operation.removeprefix('Memory')}")

        return {
            "means": [1.0],
            "cis": [0.0],
        }

    monkeypatch.setattr(
        sut,
        "load_summary",
        fake_load_summary,
    )
    monkeypatch.setattr(
        sut,
        "analyze_case",
        fake_analyze_case,
    )
    monkeypatch.setattr(
        sut,
        "analyze_memory_case",
        fake_analyze_memory_case,
    )
    monkeypatch.setattr(
        sut,
        "memory_case_statistics",
        lambda cases, metric: (sut.MEGABYTE, 0.0),
    )

    monkeypatch.setattr(
        sut,
        "plot_aes_ascon_latency",
        lambda *args: calls.append("plot latency"),
    )
    monkeypatch.setattr(
        sut,
        "plot_aes_ascon_latency_speedup",
        lambda *args: calls.append("plot latency speedup"),
    )
    monkeypatch.setattr(
        sut,
        "plot_aes_ascon_throughput",
        lambda *args: calls.append("plot throughput"),
    )
    monkeypatch.setattr(
        sut,
        "plot_aes_ascon_energy",
        lambda *args: calls.append("plot energy"),
    )
    monkeypatch.setattr(
        sut,
        "plot_aes_ascon_energy_reduction",
        lambda *args: calls.append("plot energy reduction"),
    )
    monkeypatch.setattr(
        sut,
        "plot_aes_ascon_memory",
        lambda *args: calls.append("plot memory"),
    )
    monkeypatch.setattr(
        sut,
        "write_aes_ascon_report",
        lambda *args: calls.append("write html"),
    )

    expected_before_charts = [
        "load summary",
        "analyze AES-GCM Encrypt",
        "analyze memory AES-GCM Encrypt",
        "analyze AES-GCM Decrypt",
        "analyze memory AES-GCM Decrypt",
        "analyze ASCON Encrypt",
        "analyze memory ASCON Encrypt",
        "analyze ASCON Decrypt",
        "analyze memory ASCON Decrypt",
    ]

    expected_charts = {
        "plot latency",
        "plot latency speedup",
        "plot throughput",
        "plot energy",
        "plot energy reduction",
        "plot memory",
    }

    # Act
    sut.main()

    # Assert
    assert calls[: len(expected_before_charts)] == expected_before_charts

    assert set(calls[len(expected_before_charts) : -1]) == expected_charts

    assert calls[-1] == "write html"
