import csv
from pathlib import Path

RESULT_FIELDS = [
    "scenario",
    "row_type",
    "algorithm",
    "operation",
    "parameter",
    "parameter_value",
    "run",
]


# Extract independent repetitions from the current Go benchmark output.
def _read_benchmark_results(txt_filepath, scenario):

    if scenario == "aes_ascon":
        case_prefix = "BenchmarkAESASCON"
    elif scenario == "json_cbor":
        case_prefix = "BenchmarkMessage"
    elif scenario == "cpabe_rsa":
        case_prefix = "BenchmarkCPABERSA"
    elif scenario == "full_schema":
        case_prefix = "BenchmarkFullSchema"
    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    runs = {}

    with txt_filepath.open("r", encoding="utf-8") as file:

        for line in file:

            fields = line.split()

            if not fields or not fields[0].startswith(case_prefix):
                continue

            operation, algorithm, parameter_value = fields[0][len(case_prefix) :].split(
                "/"
            )
            parameter_value = int(parameter_value.split("-", 1)[0].removesuffix("B"))

            baseline = algorithm == "Runtime" and operation == "MemoryBaseline"

            if operation == "MemoryEncrypt":
                operation = "Encrypt"
            elif operation == "MemoryDecrypt":
                operation = "Decrypt"

            if baseline:
                parameter = ""
            elif scenario == "cpabe_rsa":
                if algorithm == "CPABEAttributes":
                    parameter = "attribute_count"
                elif algorithm == "RSASubscribers":
                    parameter = "subscriber_count"
                else:
                    parameter = "rsa_key_bits"
            else:
                parameter = "payload_size"

            identity = (algorithm, operation, parameter, parameter_value)
            runs[identity] = runs.get(identity, 0) + 1

            row = {
                "scenario": scenario,
                "row_type": "baseline" if baseline else "workload",
                "algorithm": "" if baseline else algorithm,
                "operation": "" if baseline else operation,
                "parameter": parameter,
                "parameter_value": "" if baseline else parameter_value,
                "run": runs[identity],
            }
            measurements = {
                fields[index + 1]: float(fields[index])
                for index in range(2, len(fields), 2)
            }

            yield row, measurements


# Retain only timing measurements consumed by the scenario reports.
def convert_timing_results(txt_filepath, scenario):

    txt_filepath = Path(txt_filepath)
    csv_filepath = txt_filepath.with_suffix(".csv")
    fieldnames = RESULT_FIELDS + ["ns_per_op", "throttled"]

    if scenario == "aes_ascon":
        fieldnames += ["mb_per_s"]
    elif scenario == "json_cbor":
        fieldnames += ["serialized_bytes", "raw_bytes"]
    elif scenario == "cpabe_rsa":
        fieldnames += ["ciphertext_bytes", "total_ciphertext_bytes", "stored_key_bytes"]
    elif scenario == "full_schema":
        fieldnames += ["serialized_bytes"]

    with csv_filepath.open("w", encoding="utf-8", newline="") as output:

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for row, measurements in _read_benchmark_results(txt_filepath, scenario):

            row["ns_per_op"] = measurements["ns/op"]
            row["throttled"] = int(measurements["throttled"])

            if scenario == "aes_ascon":
                row["mb_per_s"] = measurements["MB/s"]

            elif scenario == "json_cbor" and row["operation"] == "Serialize":
                row["serialized_bytes"] = int(measurements["serialized_bytes"])
                if row["algorithm"] == "JSON":
                    row["raw_bytes"] = int(measurements["raw_bytes"])

            elif scenario == "cpabe_rsa":
                if row["operation"] == "Encrypt":
                    row["ciphertext_bytes"] = int(measurements["ciphertext_bytes"])
                    if row["algorithm"] == "RSASubscribers":
                        row["total_ciphertext_bytes"] = int(
                            measurements["total_ciphertext_bytes"]
                        )
                elif row["algorithm"] == "CPABEAttributes":
                    row["stored_key_bytes"] = int(measurements["stored_key_bytes"])

            elif scenario == "full_schema" and row["operation"] == "Encrypt":
                row["serialized_bytes"] = int(measurements["serialized_bytes"])

            writer.writerow(row)

    txt_filepath.unlink()

    return csv_filepath


# Memory results contain peak RSS and independent baseline repetitions only.
def convert_memory_results(txt_filepath, scenario):

    txt_filepath = Path(txt_filepath)
    csv_filepath = txt_filepath.with_suffix(".csv")

    with csv_filepath.open("w", encoding="utf-8", newline="") as output:

        writer = csv.DictWriter(output, fieldnames=RESULT_FIELDS + ["peak_rss_bytes"])
        writer.writeheader()

        for row, measurements in _read_benchmark_results(txt_filepath, scenario):
            row["peak_rss_bytes"] = int(measurements["peak_rss_bytes"])
            writer.writerow(row)

    txt_filepath.unlink()

    return csv_filepath
