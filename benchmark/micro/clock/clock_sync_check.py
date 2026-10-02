import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

PI3 = "pi3"
PI4 = "pi4"

SAMPLES = 30
INTERVAL_SECONDS = 5


def read_offset(target):
    output = subprocess.check_output(
        ["ssh", target, "chronyc", "tracking"],
        text=True,
    )

    line = next(
        line for line in output.splitlines() if line.strip().startswith("System time")
    )

    parts = line.split()

    offset = float(parts[3])
    direction = parts[5]

    if direction == "slow":
        offset = -offset

    return offset


offsets = []

with ThreadPoolExecutor(max_workers=2) as executor:
    for sample in range(SAMPLES):
        pi3_future = executor.submit(read_offset, PI3)
        pi4_future = executor.submit(read_offset, PI4)

        pi3_offset = pi3_future.result()
        pi4_offset = pi4_future.result()

        relative_offset = abs(pi4_offset - pi3_offset)
        offsets.append(relative_offset)

        if sample < SAMPLES - 1:
            time.sleep(INTERVAL_SECONDS)


mean_offset = sum(offsets) / len(offsets)

print(f"Samples: {SAMPLES}")
print(
    f"Mean absolute Pi-to-Pi clock offset: "
    f"{mean_offset * 1_000_000:.2f} us "
    f"({mean_offset * 1_000:.3f} ms)"
)
