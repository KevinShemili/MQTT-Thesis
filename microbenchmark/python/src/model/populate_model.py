from model.benchmark_summary import BenchmarkSummary
from model.case_aggregation import CaseAggregation
from model.case import Case
from model.measurement import Measurement


# Populate a BenchmarkSummary from a Go benchmark output file
def load_results(
    summary: BenchmarkSummary,
    filepath: str,
    case_prefix: str,
    suffix_to_delete: str = "",
) -> None:

    with open(filepath, "r", encoding="utf-8") as file:

        # Read file row by row, skipping any rows that dont match the expected format
        for line in file:

            # Split row by whitespace
            fields = line.split()

            # Skip rows that don't have enough fields or don't start with the expected prefix
            if len(fields) < 2 or not fields[0].startswith(case_prefix):
                continue

            # Split the first field into operation, parameter & parameter value
            name_parts = fields[0][len(case_prefix) :].split("/")

            # An OOM kill can leave an incomplete benchmark row
            if len(name_parts) < 3 or not fields[1].isdigit():
                continue

            operation, parameter, parameter_value_string = name_parts[:3]
            parameter_value_string = parameter_value_string.split("-")[0].removesuffix(
                suffix_to_delete
            )

            if not parameter_value_string.isdigit():
                continue

            parameter_value = int(parameter_value_string)

            # Check if an aggregation already exists for this operation, parameter & parameter value
            aggregation = summary.find_aggregation(
                operation, parameter, parameter_value
            )

            # If not create it
            if aggregation is None:
                aggregation = CaseAggregation(operation, parameter, parameter_value)
                summary.aggregations.append(aggregation)

            # Create a list of Measurement objects from the remaining fields in the row
            measurements = [
                Measurement(fields[index + 1], float(fields[index]))
                for index in range(2, len(fields) - 1, 2)
            ]

            # Create full object graph
            aggregation.cases.append(
                Case(
                    iterations=int(fields[1]),
                    measurements=measurements,
                )
            )


# Load OOM status from a separate file and update the BenchmarkSummary accordingly
def load_out_of_memory_status(summary: BenchmarkSummary, filepath: str) -> None:

    with open(filepath, "r", encoding="utf-8") as file:
        for line in file:
            fields = line.split()

            if not fields or fields[0].startswith("#") or len(fields) != 4:
                continue

            operation, parameter, parameter_value_string, is_out_of_memory = fields
            parameter_value = int(parameter_value_string)

            if is_out_of_memory != "true":
                continue

            aggregation = summary.find_aggregation(
                operation, parameter, parameter_value
            )

            if aggregation is None:
                aggregation = CaseAggregation(operation, parameter, parameter_value)
                summary.aggregations.append(aggregation)

            aggregation.out_of_memory = True
