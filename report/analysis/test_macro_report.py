import report.analysis.macro_report as sut


def test_main_calls_report_stages_in_expected_order(monkeypatch, tmp_path):

    # Arrange
    calls = []
    charts = []

    class FakeSummary:
        macro_aggregations = []

    def fake_load_macro_summary(publisher_filepath, subscriber_filepath, scenario):
        if "load summaries" not in calls:
            calls.append("load summaries")

        return FakeSummary()

    def fake_analyze_case(aggregations):
        if "analyze cases" not in calls:
            calls.append("analyze cases")

        return {
            "payload_sizes": [256],
            "repetition_counts": [1],
            "message_counts": [[1]],
            "latency_means": [1.0],
            "latency_cis": [0.1],
            "cycles": {},
        }

    def fake_chart(name):
        def chart(case_results, output_path):
            if "generate charts" not in calls:
                calls.append("generate charts")

            charts.append(name)

        return chart

    def fake_write_report(report_data, template_path, report_path):
        calls.append("write html")

    monkeypatch.setattr(sut, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sut, "TEMPLATE_DIR", tmp_path)
    monkeypatch.setenv("MACRO_RESULT_DIR", "results")
    monkeypatch.setattr(sut, "load_dotenv", lambda environment_file, override: None)
    monkeypatch.setattr(sut, "load_macro_summary", fake_load_macro_summary)
    monkeypatch.setattr(sut, "analyze_case", fake_analyze_case)
    monkeypatch.setattr(sut, "plot_macro_latency", fake_chart("latency"))
    monkeypatch.setattr(sut, "plot_macro_cpu_cycles", fake_chart("cpu cycles"))
    monkeypatch.setattr(sut, "write_macro_report", fake_write_report)

    expected_calls = [
        "load summaries",
        "analyze cases",
        "generate charts",
        "write html",
    ]

    expected_charts = {
        "latency",
        "cpu cycles",
    }

    # Act
    sut.main()

    # Assert
    assert calls == expected_calls
    assert set(charts) == expected_charts


def test_analyze_case_calls_expected_analysis_functions(monkeypatch):

    # Arrange
    calls = []

    class FakeCase:
        repetition = 0
        publisher_timestamps = [1]

    class FakeAggregation:
        payload_size = 256
        cases = [FakeCase()]

    def fake_macro_latency_statistics(aggregations):
        calls.append("latency statistics")
        return [1.0], [0.1]

    def fake_macro_cycle_statistics(aggregations):
        calls.append("cycle statistics")
        return {}

    monkeypatch.setattr(sut, "macro_latency_statistics", fake_macro_latency_statistics)
    monkeypatch.setattr(sut, "macro_cycle_statistics", fake_macro_cycle_statistics)
    monkeypatch.setattr(sut, "to_microseconds", lambda values: values)

    expected_calls = [
        "latency statistics",
        "cycle statistics",
    ]

    # Act
    sut.analyze_case([FakeAggregation()])

    # Assert
    assert calls == expected_calls
