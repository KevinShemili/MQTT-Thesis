import report.analysis.full_schema_report as sut


def test_main_calls_report_stages_in_expected_order(monkeypatch, tmp_path):

    # Arrange
    calls = []
    render_calls = []

    class FakeSummary:
        energy_baseline_cases = []
        memory_baseline_cases = []

        def find_timing_aggregation(
            self, configuration, operation, parameter, parameter_value
        ):
            return "timing"

        def find_energy_aggregation(
            self, configuration, operation, parameter, parameter_value
        ):
            return "energy"

        def find_memory_aggregation(
            self, configuration, operation, parameter, parameter_value
        ):
            return "memory"

    def fake_load_summary(*args, **kwargs):
        calls.append("load summary")
        return FakeSummary()

    def fake_analyze_case(*args):
        if "analyze cases" not in calls:
            calls.append("analyze cases")

        return {
            "latency_means": [1.0],
            "latency_cis": [1.0],
            "energy_means": [1.0],
            "energy_cis": [1.0],
            "memory_means": [1.0],
            "memory_cis": [1.0],
            "timing_throttled": [False],
            "energy_throttled": [False],
        }

    def fake_memory_case_statistics(*args):
        calls.append("analyze baseline memory")
        return sut.MEGABYTE, sut.MEGABYTE

    def fake_chart(name):
        def chart(*args):
            if "generate charts" not in calls:
                calls.append("generate charts")

            render_calls.append(name)

        return chart

    def fake_write_report(*args):
        calls.append("write html")
        render_calls.append("html")

    monkeypatch.setattr(sut, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sut, "TEMPLATE_DIR", tmp_path)
    monkeypatch.setenv("FULL_SCHEMA_RESULT_DIR", "results")
    monkeypatch.setattr(sut, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(sut, "parse_int_env", lambda name: 1)
    monkeypatch.setattr(sut, "parse_int_list_env", lambda name: [256])
    monkeypatch.setattr(sut, "load_summary", fake_load_summary)
    monkeypatch.setattr(sut, "analyze_case", fake_analyze_case)
    monkeypatch.setattr(sut, "collect_envelope_sizes", lambda aggregations: [1.0])
    monkeypatch.setattr(sut, "memory_case_statistics", fake_memory_case_statistics)
    monkeypatch.setattr(sut, "plot_full_schema_latency", fake_chart("latency"))
    monkeypatch.setattr(
        sut, "plot_full_schema_latency_overview", fake_chart("latency overview")
    )
    monkeypatch.setattr(
        sut,
        "plot_full_schema_serialized_envelope_size",
        fake_chart("serialized envelope size"),
    )
    monkeypatch.setattr(sut, "plot_full_schema_energy", fake_chart("energy"))
    monkeypatch.setattr(sut, "plot_full_schema_memory", fake_chart("memory"))
    monkeypatch.setattr(sut, "write_full_schema_report", fake_write_report)

    expected_calls = [
        "load summary",
        "analyze cases",
        "analyze baseline memory",
        "generate charts",
        "write html",
    ]

    expected_charts = {
        "latency",
        "latency overview",
        "serialized envelope size",
        "energy",
        "memory",
    }

    # Act
    sut.main()

    # Assert
    assert calls == expected_calls
    assert set(render_calls[:-1]) == expected_charts
    assert render_calls[-1] == "html"


def test_analyze_case_calls_expected_analysis_functions(monkeypatch):

    # Arrange
    calls = []

    def fake_timing_statistics(aggregations, measurement):
        calls.append("timing statistics")
        return [1.0], [1.0]

    def fake_energy_statistics(aggregations, baseline_cases, timing_aggregations):
        calls.append("energy statistics")
        return [1.0], [1.0]

    def fake_memory_statistics(aggregations, measurement):
        calls.append("memory statistics")
        return [1.0], [1.0]

    monkeypatch.setattr(sut, "timing_statistics", fake_timing_statistics)
    monkeypatch.setattr(sut, "energy_statistics", fake_energy_statistics)
    monkeypatch.setattr(sut, "memory_statistics", fake_memory_statistics)
    monkeypatch.setattr(sut, "to_microseconds", lambda values: values)
    monkeypatch.setattr(sut, "to_microjoules", lambda values: values)
    monkeypatch.setattr(sut, "to_megabytes", lambda values: values)
    monkeypatch.setattr(sut, "collect_timing_throttle_flags", lambda values: [])
    monkeypatch.setattr(sut, "collect_energy_throttle_flags", lambda values: [])

    expected_calls = [
        "timing statistics",
        "energy statistics",
        "memory statistics",
    ]

    # Act
    sut.analyze_case(["timing"], ["energy"], ["memory"], ["energy baseline"])

    # Assert
    assert calls == expected_calls
