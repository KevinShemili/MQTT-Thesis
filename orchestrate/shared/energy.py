import time
from concurrent.futures import ThreadPoolExecutor


def read_um24c(um24c, duration):

    samples = []

    start = time.monotonic()
    deadline = start + duration

    while time.monotonic() < deadline:

        voltage, current, power = um24c.read()

        elapsed = time.monotonic() - start

        samples.append((elapsed, voltage, current, power))

    return samples


def write_to_file(output, samples):

    for elapsed, voltage, current, power in samples:

        output.write(
            f"elapsed_s={elapsed:.6f} "
            f"voltage_v={voltage:.3f} "
            f"current_a={current:.3f} "
            f"power_w={power:.3f}\n"
        )


def collect_energy_runs(process, meter, output, total_workload_duration):

    stress_sample_future = None

    # Main thread: Reads benchmark stdout
    # Worker thread: Reads power samples from the UM24C
    with ThreadPoolExecutor(max_workers=1) as executor:

        for line in process.stdout:

            if "ENRG-START" in line:

                if stress_sample_future is not None:
                    raise RuntimeError(
                        "Received ENRG-START before previous run was completed"
                    )

                stress_sample_future = executor.submit(
                    read_um24c, meter, total_workload_duration
                )

                continue

            if "ns/op" in line:

                if stress_sample_future is None:
                    raise RuntimeError(
                        "Received benchmark result without corresponding power samples"
                    )

                parts = line.split()

                ns_per_op = parts[parts.index("ns/op") - 1]
                throttled = parts[parts.index("throttled") - 1]

                # Obtain the samples belonging to this exact run.
                # If sampling is still finishing, this waits for it.
                stress_samples = stress_sample_future.result()

                output.write("\n[run]\n")
                output.write(f"ns/op={ns_per_op}\n")
                output.write(f"throttled={throttled}\n")

                write_to_file(output, stress_samples)

                stress_sample_future = None
