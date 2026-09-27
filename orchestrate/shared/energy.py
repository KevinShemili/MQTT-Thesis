import time

ENERGY_FIELDS = [
    "scenario",
    "row_type",
    "algorithm",
    "operation",
    "parameter",
    "parameter_value",
    "run",
    "throttled",
    "elapsed_s",
    "voltage_v",
    "current_a",
    "power_w",
]


def read_um24c(um24c, duration):

    samples = []

    start = time.monotonic()
    deadline = start + duration

    while time.monotonic() < deadline:

        voltage, current, power = um24c.read()

        elapsed = time.monotonic() - start

        if elapsed < duration:
            samples.append((elapsed, voltage, current, power))

    return samples


def write_samples(writer, samples, run_data):

    for elapsed, voltage, current, power in samples:

        writer.writerow(
            {
                **run_data,
                "elapsed_s": f"{elapsed:.6f}",
                "voltage_v": f"{voltage:.3f}",
                "current_a": f"{current:.3f}",
                "power_w": f"{power:.3f}",
            }
        )
