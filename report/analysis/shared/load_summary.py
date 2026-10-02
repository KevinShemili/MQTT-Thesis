import csv
from pathlib import Path

from report.model.benchmark_summary import BenchmarkSummary
from report.model.macro.macro_aggregation import MacroAggregation
from report.model.macro.macro_case import MacroCase
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import THROTTLED as ENERGY_THROTTLED
from report.model.energy.energy_case import EnergyCase, EnergySample
from report.model.memory.memory_aggregation import MemoryAggregation
from report.model.memory.memory_case import PEAK_RSS_BYTES, MemoryCase
from report.model.timing.timing_aggregation import TimingAggregation
from report.model.timing.timing_case import (
    CIPHERTEXT_BYTES,
    MB_PER_SECOND,
    NS_PER_OP,
    RAW_BYTES,
    SERIALIZED_BYTES,
    STORED_KEY_BYTES,
    THROTTLED as TIMING_THROTTLED,
    TOTAL_CIPHERTEXT_BYTES,
    TimingCase,
)


# Load timing, optional memory, and energy CSVs into a BenchmarkSummary
def load_summary(
    timing_filepath: str,
    energy_filepath: str,
    memory_filepath: str | None = None,
) -> BenchmarkSummary:

    summary = BenchmarkSummary()

    _load_timing_results(summary, timing_filepath)

    if memory_filepath is not None:
        _load_memory_results(summary, memory_filepath)

    _load_energy_results(summary, energy_filepath)

    return summary


# Load independent memory runs and runtime baselines
def _load_memory_results(
    summary: BenchmarkSummary,
    filepath: str,
) -> None:

    with Path(filepath).open("r", encoding="utf-8", newline="") as file:

        for row in csv.DictReader(file):

            case = MemoryCase(run=int(row["run"]))
            case.add_measurement(PEAK_RSS_BYTES, float(row["peak_rss_bytes"]))

            if row["row_type"] == "baseline":
                summary.memory_baseline_cases.append(case)
                continue

            algorithm = row["algorithm"]
            operation = row["operation"]
            parameter = row["parameter"]
            parameter_value = int(row["parameter_value"])

            aggregation = summary.find_memory_aggregation(
                algorithm,
                operation,
                parameter,
                parameter_value,
            )

            if aggregation is None:

                aggregation = MemoryAggregation(
                    algorithm,
                    operation,
                    parameter,
                    parameter_value,
                )
                summary.memory_aggregations.append(aggregation)

            aggregation.cases.append(case)


# Load timing runs and their scenario-specific measurements
def _load_timing_results(
    summary: BenchmarkSummary,
    filepath: str,
) -> None:

    with Path(filepath).open("r", encoding="utf-8", newline="") as file:

        for row in csv.DictReader(file):

            algorithm = row["algorithm"]
            operation = row["operation"]
            parameter = row["parameter"]
            parameter_value = int(row["parameter_value"])

            aggregation = summary.find_timing_aggregation(
                algorithm,
                operation,
                parameter,
                parameter_value,
            )

            if aggregation is None:

                aggregation = TimingAggregation(
                    algorithm,
                    operation,
                    parameter,
                    parameter_value,
                )
                summary.timing_aggregations.append(aggregation)

            case = TimingCase(run=int(row["run"]))
            case.add_measurement(NS_PER_OP, float(row["ns_per_op"]))
            case.add_measurement(TIMING_THROTTLED, float(row["throttled"]))

            for column, measurement in (
                ("mb_per_s", MB_PER_SECOND),
                ("serialized_bytes", SERIALIZED_BYTES),
                ("raw_bytes", RAW_BYTES),
                ("ciphertext_bytes", CIPHERTEXT_BYTES),
                ("total_ciphertext_bytes", TOTAL_CIPHERTEXT_BYTES),
                ("stored_key_bytes", STORED_KEY_BYTES),
            ):
                if row.get(column):
                    case.add_measurement(measurement, float(row[column]))

            aggregation.cases.append(case)


# Group measurement-window samples by workload identity and repetition
def _load_energy_results(
    summary: BenchmarkSummary,
    filepath: str,
) -> None:

    with Path(filepath).open("r", encoding="utf-8", newline="") as file:

        for row in csv.DictReader(file):

            run = int(row["run"])
            sample = EnergySample(
                elapsed_s=float(row["elapsed_s"]),
                voltage_v=float(row["voltage_v"]),
                current_a=float(row["current_a"]),
                power_w=float(row["power_w"]),
            )

            if row["row_type"] == "baseline":

                case = next(
                    (case for case in summary.energy_baseline_cases if case.run == run),
                    None,
                )
                if case is None:
                    case = EnergyCase(run)
                    summary.energy_baseline_cases.append(case)

                case.add_sample(sample)
                continue

            algorithm = row["algorithm"]
            operation = row["operation"]
            parameter = row["parameter"]
            parameter_value = int(row["parameter_value"])

            aggregation = summary.find_energy_aggregation(
                algorithm,
                operation,
                parameter,
                parameter_value,
            )

            if aggregation is None:

                aggregation = EnergyAggregation(
                    algorithm,
                    operation,
                    parameter,
                    parameter_value,
                )
                summary.energy_aggregations.append(aggregation)

            case = aggregation.find_case(run)

            if case is None:
                case = EnergyCase(run)
                case.add_measurement(ENERGY_THROTTLED, float(row["throttled"]))
                aggregation.cases.append(case)

            case.add_sample(sample)


# Load the two endpoint CSVs, retaining raw timestamps and workload cycle totals
def load_macro_summary(
    publisher_filepath: str, subscriber_filepath: str, scenario: str
) -> BenchmarkSummary:

    summary = BenchmarkSummary()

    with Path(publisher_filepath).open("r", encoding="utf-8", newline="") as file:

        for row in csv.DictReader(file):

            payload_size = int(row["payload_size"])
            repetition = int(row["repetition"])
            aggregation = summary.find_macro_aggregation(scenario, payload_size)

            if aggregation is None:
                aggregation = MacroAggregation(scenario, payload_size)
                summary.macro_aggregations.append(aggregation)

            case = aggregation.find_case(repetition)

            if case is None:
                case = MacroCase(repetition)
                aggregation.cases.append(case)

            case.publisher_cycles = int(row["publisher_cycles"])
            case.publisher_timestamps[row["message_id"]] = int(
                row["publisher_started_unix_ns"]
            )

    with Path(subscriber_filepath).open("r", encoding="utf-8", newline="") as file:

        for row in csv.DictReader(file):

            payload_size = int(row["payload_size"])
            repetition = int(row["repetition"])

            aggregation = summary.find_macro_aggregation(scenario, payload_size)
            case = aggregation.find_case(repetition)

            case.subscriber_cycles = int(row["subscriber_cycles"])
            case.subscriber_timestamps[row["message_id"]] = int(
                row["subscriber_arrived_unix_ns"]
            )

    return summary
