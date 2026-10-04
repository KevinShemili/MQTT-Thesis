import report.analysis.macro_report as sut


def test_main_calls_report_stages_in_expected_order(monkeypatch, tmp_path):

    # Arrange
    calls = []
    charts = []

    class FakeSummary:
        macro_aggregations = ["aggregation"]

    def fake_load_summary(*args, **kwargs):
        if "load summaries" not in calls:
            calls.append("load summaries")

        return FakeSummary()

    def fake_analyze_case(*args):
        if "analyze cases" not in calls:
            calls.append("analyze cases")

        return {
            "payload_sizes": [256],
            "repetition_counts": [1],
            "message_counts": [[1]],
            "latency_means": [1.0],
            "latency_cis": [1.0],
            "cycles": {},
        }

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
    monkeypatch.setenv("MACRO_RESULT_DIR", "results")

    monkeypatch.setattr(sut, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(sut, "load_macro_summary", fake_load_summary)
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
        repetition = 1
        publisher_timestamps = {"message": 1}

    class FakeAggregation:
        payload_size = 256
        cases = [FakeCase()]

    monkeypatch.setattr(
        sut,
        "macro_latency_statistics",
        lambda *args: (
            calls.append("latency statistics"),
            ([1.0], [1.0]),
        )[1],
    )

    monkeypatch.setattr(
        sut,
        "macro_cycle_statistics",
        lambda *args: (
            calls.append("cycle statistics"),
            {},
        )[1],
    )

    monkeypatch.setattr(sut, "to_microseconds", lambda values: values)

    expected = {
        "latency statistics",
        "cycle statistics",
    }

    # Act
    sut.analyze_case([FakeAggregation()])

    # Assert
    assert set(calls) == expected
