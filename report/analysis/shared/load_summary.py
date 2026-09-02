from pathlib import Path

from report.model.benchmark_summary import BenchmarkSummary
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import (
    NS_PER_OP,
    THROTTLED,
    EnergyCase,
    EnergySample,
)
from report.model.memory.memory_aggregation import MemoryAggregation
from report.model.memory.memory_case import MemoryCase
from report.model.timing.timing_aggregation import TimingAggregation
from report.model.timing.timing_case import TimingCase


# Load timing, optional memory, and energy results into a BenchmarkSummary
def load_summary(
    timing_filepath: str,
    energy_filepath: str,
    case_prefix: str,
    parameter_by_algorithm: dict[str, str],
    warmup_duration: float,
    measurement_duration: float,
    parameter_suffix: str = "",
    memory_filepath: str | None = None,
) -> BenchmarkSummary:

    summary = BenchmarkSummary()

    _load_timing_results(
        summary,
        timing_filepath,
        case_prefix,
        parameter_by_algorithm,
        parameter_suffix,
    )

    if memory_filepath is not None:
        _load_memory_results(
            summary,
            memory_filepath,
            case_prefix,
            parameter_by_algorithm,
            parameter_suffix,
        )

    _load_energy_results(
        summary,
        energy_filepath,
        parameter_by_algorithm,
        warmup_duration,
        measurement_duration,
    )

    return summary


# Load Go memory benchmark results
def _load_memory_results(
    summary: BenchmarkSummary,
    filepath: str,
    case_prefix: str,
    parameter_by_algorithm: dict[str, str],
    parameter_suffix: str,
) -> None:

    with Path(filepath).open("r", encoding="utf-8") as file:

        for line in file:

            fields = line.split()

            # Ignore non-benchmark output
            if len(fields) < 2 or not fields[0].startswith(case_prefix):
                continue

            algorithm, operation, parameter_value = _parse_timing_case_name(
                fields[0],
                case_prefix,
                parameter_suffix,
            )

            case = MemoryCase(
                iterations=int(fields[1]),
            )

            for index in range(2, len(fields) - 1, 2):

                case.add_measurement(
                    fields[index + 1],
                    float(fields[index]),
                )

            if (
                algorithm == "Runtime"
                and operation == "MemoryBaseline"
                and parameter_value == 0
            ):
                summary.memory_baseline_cases.append(case)
                continue

            parameter = parameter_by_algorithm[algorithm]

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


# Load Go timing benchmark results
def _load_timing_results(
    summary: BenchmarkSummary,
    filepath: str,
    case_prefix: str,
    parameter_by_algorithm: dict[str, str],
    parameter_suffix: str,
) -> None:

    with Path(filepath).open("r", encoding="utf-8") as file:

        for line in file:

            fields = line.split()

            # Ignore non-benchmark output
            if len(fields) < 2 or not fields[0].startswith(case_prefix):
                continue

            algorithm, operation, parameter_value = _parse_timing_case_name(
                fields[0],
                case_prefix,
                parameter_suffix,
            )

            parameter = parameter_by_algorithm[algorithm]

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

            case = TimingCase(
                iterations=int(fields[1]),
            )

            for index in range(2, len(fields) - 1, 2):

                case.add_measurement(
                    fields[index + 1],
                    float(fields[index]),
                )

            aggregation.cases.append(case)


# Extract algorithm, operation and parameter value from a Go benchmark name
def _parse_timing_case_name(
    benchmark_name: str,
    case_prefix: str,
    parameter_suffix: str,
) -> tuple[str, str, int]:

    name_parts = benchmark_name[len(case_prefix) :].split("/")

    if len(name_parts) != 3:
        raise ValueError(f"Invalid timing benchmark name: {benchmark_name}")

    operation, algorithm, parameter_value_string = name_parts

    # Remove Go CPU suffix (-4, -8, etc.) and benchmark value suffix (B, etc.)
    parameter_value_string = parameter_value_string.split("-", 1)[0].removesuffix(
        parameter_suffix
    )

    return algorithm, operation, int(parameter_value_string)


# Load energy benchmark results
def _load_energy_results(
    summary: BenchmarkSummary,
    filepath: str,
    parameter_by_algorithm: dict[str, str],
    warmup_duration: float,
    measurement_duration: float,
) -> None:

    current_aggregation = None
    current_case = None
    reading_baseline = False

    with Path(filepath).open("r", encoding="utf-8") as file:

        for raw_line in file:

            line = raw_line.strip()

            if not line:
                continue

            if line == "[baseline]":

                reading_baseline = True
                current_aggregation = None
                current_case = None

                continue

            if line.startswith("[case "):

                algorithm, operation, parameter_value = _parse_energy_case_header(line)
                parameter = parameter_by_algorithm[algorithm]

                current_aggregation = EnergyAggregation(
                    algorithm=algorithm,
                    operation=operation,
                    parameter=parameter,
                    parameter_value=parameter_value,
                    warmup_duration=warmup_duration,
                    measurement_duration=measurement_duration,
                )

                summary.energy_aggregations.append(current_aggregation)

                reading_baseline = False
                current_case = None

                continue

            if line == "[run]":

                if current_aggregation is None:
                    raise ValueError("Energy run found outside an energy case")

                current_case = EnergyCase()

                current_aggregation.cases.append(current_case)

                continue

            if line.startswith(f"{NS_PER_OP}="):

                if current_case is None:
                    raise ValueError("ns/op found outside an energy run")

                current_case.add_measurement(
                    NS_PER_OP,
                    float(line.removeprefix(f"{NS_PER_OP}=")),
                )

                continue

            if line.startswith(f"{THROTTLED}="):

                if current_case is None:
                    raise ValueError("throttled found outside an energy run")

                current_case.add_measurement(
                    THROTTLED,
                    float(line.removeprefix(f"{THROTTLED}=")),
                )

                continue

            if line.startswith("elapsed_s="):

                sample = _parse_energy_sample(line)

                if reading_baseline:
                    summary.energy_baseline_samples.append(sample)

                elif current_case is not None:
                    current_case.add_sample(sample)

                else:
                    raise ValueError("Energy sample found outside an energy run")

                continue

            raise ValueError(f"Unexpected energy result: {line}")


# Extract algorithm, operation and parameter value from an energy case header
def _parse_energy_case_header(
    line: str,
) -> tuple[str, str, int]:

    fields = dict(
        field.split("=", 1)
        for field in line.removeprefix("[case ").removesuffix("]").split()
    )

    return (
        fields["algorithm"],
        fields["operation"],
        int(fields["parameter_value"]),
    )


# Parse one UM24C sample
def _parse_energy_sample(line: str) -> EnergySample:

    fields = dict(field.split("=", 1) for field in line.split())

    return EnergySample(
        elapsed_s=float(fields["elapsed_s"]),
        voltage_v=float(fields["voltage_v"]),
        current_a=float(fields["current_a"]),
        power_w=float(fields["power_w"]),
    )
