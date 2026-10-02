import csv

from report.analysis.macro_report import SCENARIOS, generate_report


def test_generate_report_compares_all_scenario_directories(tmp_path):
    for scenario, _, _, _ in SCENARIOS:
        scenario_directory = tmp_path / scenario
        scenario_directory.mkdir()

        with (scenario_directory / "publisher.csv").open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "payload_size", "repetition", "message_id",
                "publisher_started_unix_ns", "publisher_cycles",
            ])
            for payload_size in (256, 512):
                for repetition in (1, 2):
                    writer.writerow([
                        payload_size, repetition,
                        f"{scenario}-{payload_size}-{repetition}", 100, 1000,
                    ])

        with (scenario_directory / "subscriber.csv").open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.writer(file)
            writer.writerow([
                "payload_size", "repetition", "message_id",
                "subscriber_arrived_unix_ns", "subscriber_cycles",
            ])
            for payload_size in (256, 512):
                for repetition in (1, 2):
                    writer.writerow([
                        payload_size, repetition,
                        f"{scenario}-{payload_size}-{repetition}", 200, 2000,
                    ])

    generate_report(tmp_path)

    report = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert (tmp_path / "latency.png").is_file()
    assert (tmp_path / "cpu_cycles.png").is_file()
    assert report.count('class="reference-row"') == 6
    for _, label, _, _ in SCENARIOS:
        assert label in report
    assert "256 B" in report
    assert "512 B" in report
