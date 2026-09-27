import report.analysis.cpabe_rsa_report as sut


def test_main_calls_report_stages_in_expected_order(monkeypatch, tmp_path):

    # Arrange
    calls = []
    charts = []

    class FakeSummary:
        energy_baseline_cases = []
        memory_baseline_cases = []

        def find_timing_aggregation(
            self, algorithm, operation, parameter, parameter_value
        ):
            return algorithm, operation

        def find_energy_aggregation(
            self, algorithm, operation, parameter, parameter_value
        ):
            return algorithm, operation

        def find_memory_aggregation(
            self, algorithm, operation, parameter, parameter_value
        ):
            return algorithm, operation

    def fake_load_summary(*args, **kwargs):
        calls.append("load summary")
        return FakeSummary()

    def fake_analyze_case(
        timing_aggregations,
        energy_aggregations,
        memory_aggregations,
        energy_baseline_cases,
    ):
        if "analyze cases" not in calls:
            calls.append("analyze cases")

        return {
            "latency_means": [2.0],
            "latency_cis": [0.1],
            "timing_throttled": [False],
            "energy_means": [2.0],
            "energy_cis": [0.1],
            "energy_throttled": [False],
            "memory_means": [2.0],
            "memory_cis": [0.1],
        }

    def fake_add_timing_measurement(result, aggregations, measurement, name):
        result[f"{name}_means"] = [2.0]
        result[f"{name}_cis"] = [0.1]

    def fake_memory_case_statistics(*args):
        calls.append("analyze baseline memory")
        return sut.MEGABYTE, sut.MEGABYTE

    def fake_linear_regression_statistics(*args):
        if "run regressions" not in calls:
            calls.append("run regressions")

        return 1.0, 1.0, 1.0, 1.0

    def fake_chart(name):
        def chart(*args):
            if "generate charts" not in calls:
                calls.append("generate charts")

            charts.append(name)

        return chart

    def fake_write_report(*args):
        calls.append("write html")

    monkeypatch.setattr(sut, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sut, "TEMPLATE_DIR", tmp_path)
    monkeypatch.setenv("CPABE_RSA_RESULT_DIR", "results")

    monkeypatch.setattr(sut, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        sut,
        "parse_int_env",
        lambda name: {
            "CPABE_RSA_RUNS": 1,
            "CPABE_RSA_FIXED_RSA_KEY_SIZE": 1,
            "WARMUP_DURATION": 1,
            "MEASUREMENT_DURATION": 1,
        }[name],
    )
    monkeypatch.setattr(
        sut,
        "parse_int_list_env",
        lambda name: [1],
    )

    monkeypatch.setattr(sut, "load_summary", fake_load_summary)
    monkeypatch.setattr(sut, "analyze_case", fake_analyze_case)
    monkeypatch.setattr(
        sut,
        "add_timing_measurement",
        fake_add_timing_measurement,
    )
    monkeypatch.setattr(
        sut,
        "memory_case_statistics",
        fake_memory_case_statistics,
    )
    monkeypatch.setattr(
        sut,
        "linear_regression_statistics",
        fake_linear_regression_statistics,
    )

    monkeypatch.setattr(
        sut,
        "plot_cpabe_attributes",
        fake_chart("cpabe attributes"),
    )
    monkeypatch.setattr(
        sut,
        "plot_rsa_subscribers",
        fake_chart("rsa subscribers"),
    )
    monkeypatch.setattr(
        sut,
        "plot_rsa_key_size_sensitivity",
        fake_chart("rsa key size sensitivity"),
    )
    monkeypatch.setattr(
        sut,
        "plot_cpabe_rsa_energy",
        fake_chart("energy"),
    )
    monkeypatch.setattr(
        sut,
        "plot_cpabe_rsa_memory",
        fake_chart("memory"),
    )
    monkeypatch.setattr(
        sut,
        "plot_ciphertext_size_crossover",
        fake_chart("ciphertext crossover"),
    )
    monkeypatch.setattr(
        sut,
        "plot_encrypt_latency_crossover",
        fake_chart("encrypt crossover"),
    )
    monkeypatch.setattr(
        sut,
        "plot_decrypt_latency_comparison",
        fake_chart("decrypt comparison"),
    )
    monkeypatch.setattr(
        sut,
        "plot_encrypt_decrypt_asymmetry",
        fake_chart("asymmetry"),
    )
    monkeypatch.setattr(
        sut,
        "write_cpabe_rsa_report",
        fake_write_report,
    )

    expected_calls = [
        "load summary",
        "analyze cases",
        "analyze baseline memory",
        "run regressions",
        "generate charts",
        "write html",
    ]

    expected_charts = {
        "cpabe attributes",
        "rsa subscribers",
        "rsa key size sensitivity",
        "energy",
        "memory",
        "ciphertext crossover",
        "encrypt crossover",
        "decrypt comparison",
        "asymmetry",
    }

    # Act
    sut.main()

    # Assert
    assert calls == expected_calls
    assert set(charts) == expected_charts


def test_analyze_case_calls_expected_analysis_functions(monkeypatch):

    # Arrange
    calls = []

    monkeypatch.setattr(
        sut,
        "timing_statistics",
        lambda *args: (
            calls.append("timing statistics"),
            ([1.0], [1.0]),
        )[1],
    )
    monkeypatch.setattr(
        sut,
        "energy_statistics",
        lambda *args: (
            calls.append("energy statistics"),
            ([1.0], [1.0]),
        )[1],
    )
    monkeypatch.setattr(
        sut,
        "memory_statistics",
        lambda *args: (
            calls.append("memory statistics"),
            ([1.0], [1.0]),
        )[1],
    )

    monkeypatch.setattr(sut, "to_microseconds", lambda values: values)
    monkeypatch.setattr(sut, "to_microjoules", lambda values: values)
    monkeypatch.setattr(sut, "to_megabytes", lambda values: values)
    monkeypatch.setattr(sut, "collect_timing_throttle_flags", lambda values: [])
    monkeypatch.setattr(sut, "collect_energy_throttle_flags", lambda values: [])

    expected = {
        "timing statistics",
        "energy statistics",
        "memory statistics",
    }

    # Act
    sut.analyze_case(
        ["timing"],
        ["energy"],
        ["memory"],
        ["energy baseline"],
    )

    # Assert
    assert set(calls) == expected
