# MQTT Security Microbenchmarks

This repository contains the microbenchmark and reporting pipeline used to study cryptographic and serialization trade-offs for secure MQTT messaging on a Raspberry Pi.

Go implements the benchmark workloads. Python on the laptop builds and executes those benchmarks remotely over SSH, records power samples from a UM24C meter, loads the raw results, performs the statistical analysis, and generates charts and HTML reports.

## Scenarios

| Scenario | Varied parameter | Compared cases | Reported results |
| --- | --- | --- | --- |
| AES vs. ASCON | Payload size | AES-GCM and ASCON Encrypt/Decrypt | Latency, throughput, wire overhead, energy/op, iterations, thermal state |
| JSON vs. CBOR | Payload size | JSON, CBOR, and CBOR with integer keys Serialize/Deserialize | Latency, encoded size, format overhead, energy/op, iterations, thermal state |
| Full Schema | Payload size | PSK, RSA, and CP-ABE Encrypt/Decrypt | Latency, throughput chart, wire size, energy/op, peak RSS, and thermal state |
| CP-ABE vs. RSA | CP-ABE policy attributes and RSA subscribers; RSA key size is a secondary timing sensitivity | CP-ABE and RSA Encrypt/Decrypt | Latency, wrapped-key sizes, energy/op, peak RSS, slopes, crossovers, asymmetry, and comparisons |

## How the pipeline works

```text
Laptop Python orchestrator
    ├── SSH → build and run Go benchmarks on the Raspberry Pi
    ├── serial/Bluetooth → collect UM24C power samples
    └── write raw result files
            ↓
      BenchmarkSummary loader
            ↓
       shared statistics
            ↓
    scenario-specific analysis
            ↓
       PNG charts + report.html
```

Timing benchmarks measure only the operation under study. Energy benchmarks execute the same operation during warmup, the Go benchmark measurement region, and the tail. `ENRG-START` coordinates the beginning of UM24C collection with the remote workload.

For each energy repetition, the report uses the load samples and `ns/op` from that same run. Mean load power is taken from the configured steady-state interval:

```text
[WARMUP_DURATION, WARMUP_DURATION + MEASUREMENT_DURATION)
```

Energy per operation is calculated as:

```text
(mean load power - mean idle power) × operation time
```

The CP-ABE/RSA scenario also measures peak resident memory. Each memory repetition runs in its own process because Linux `VmHWM` is process-wide. A separate runtime baseline is recorded using the same independent-process method.

## Requirements

### Laptop

- Python 3.12 or newer
- Python packages from `requirements.txt`
- SSH access to the Raspberry Pi through the target name `pi`
- A paired UM24C exposed as a serial port

The current orchestrators use explicit constants for the SSH target, Raspberry Pi paths, and UM24C port. The checked-in values expect:

```text
SSH target:          pi
Remote repository:  /home/thesis/MQTT-Thesis
UM24C serial port:   COM11
```

Update those constants near the top of each orchestrator if the local setup differs.

### Raspberry Pi

- The repository at `/home/thesis/MQTT-Thesis`, or matching updated orchestrator paths
- Go 1.25 available as `/usr/local/go/bin/go`
- `environment/benchmark.env` present in the remote repository
- Linux `/proc` support for peak-RSS measurements
- Raspberry Pi thermal information under `/sys/class/thermal`
- `vcgencmd` for throttling observations

## Laptop setup

From the repository root:

```sh
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Activate the virtual environment using the command appropriate for the laptop shell, or invoke its Python executable directly.

The Go module dependencies can be prepared on the Raspberry Pi with:

```sh
cd /home/thesis/MQTT-Thesis/benchmark
/usr/local/go/bin/go mod download
```

## Configuration

Experiment settings live in [`environment/benchmark.env`](environment/benchmark.env). It contains:

- general cache and thermal settings;
- timing duration;
- idle-baseline, warmup, measurement, and tail durations;
- repetition counts;
- the shared payload-size sweep and scenario-specific attribute counts;
- subscriber counts, fixed RSA configuration, and RSA timing-sensitivity key sizes;
- fixed comparison values and result directories.

The laptop and Raspberry Pi copies of this file must agree. The orchestrators load the local file for orchestration/reporting and source the remote file before executing the Go benchmark binary.

## Running a scenario

Run one orchestrator from the repository root:

```sh
python orchestrate/orchestrate_aes_ascon.py
python orchestrate/orchestrate_json_cbor.py
python orchestrate/orchestrate_full_schema.py
python orchestrate/orchestrate_cpabe_rsa.py
```

Each orchestrator performs the complete scenario and replaces its result files. The common sequence is:

1. load the environment;
2. create the local result directory;
3. build the Go benchmark binary on the Raspberry Pi;
4. allow the device to stabilize;
5. record one idle power baseline and run all energy cases;
6. run all timing cases;
7. generate the HTML report and charts.

Scenarios that report peak RSS additionally clear and provision their fixture cache, record independent memory cases, and then continue with energy and timing.

Run scenarios sequentially. Concurrent experiments would compete for Raspberry Pi CPU, memory, temperature, and power.

## Regenerating reports

If the raw files already exist, regenerate a report without rerunning the hardware benchmarks:

```sh
python -m report.analysis.aes_ascon_report
python -m report.analysis.json_cbor_report
python -m report.analysis.full_schema_report
python -m report.analysis.cpabe_rsa_report
```

Each report module loads `environment/benchmark.env` and reads from its configured result directory.

## Results

Generated results live under `results/` and are intentionally ignored by Git.

| Directory | Raw files | Charts |
| --- | --- | --- |
| `results/aes_ascon/` | `timing.txt`, `energy.txt` | `latency.png`, `throughput.png`, `energy.png` |
| `results/json_cbor/` | `timing.txt`, `energy.txt` | `latency.png`, `size.png`, `energy.png` |
| `results/full_schema/` | `timing.txt`, `memory.txt`, `energy.txt` | `latency.png`, `latency_overhead_share.png`, `throughput.png`, `wire_expansion.png`, `energy.png`, `additional_energy.png`, `memory.png` |
| `results/cpabe_rsa/` | `timing.txt`, `memory.txt`, `energy.txt` | `cpabe_attributes.png`, `rsa_subscribers.png`, `rsa_key_size_sensitivity.png`, `energy.png`, `peak_memory.png`, and four comparison charts |

Every directory also receives `report.html`. Timing and energy thermal observations are reported separately.

The raw energy format contains one scenario-level `[baseline]`, followed by parameterized `[case ...]` sections containing independent `[run]` sections. Each run stores its own `ns/op`, throttling flag, and UM24C samples.

## Repository structure

```text
.
├── benchmark/
│   ├── cache/                    # Provisioned benchmark fixtures
│   ├── cmd/provision/            # Benchmark fixture provisioning binary
│   ├── cryptography/             # AES-GCM, ASCON, RSA, and CP-ABE adapters
│   ├── envelope/                 # JSON and CBOR envelope representations
│   ├── micro/                    # Timing, energy, and memory benchmarks
│   ├── thermal/                  # Cooldown and throttling observation
│   └── utility/                  # Environment, memory, and byte helpers
├── environment/benchmark.env     # Shared experiment configuration
├── orchestrate/                  # Supported laptop-side scenario entry points
├── report/
│   ├── analysis/                 # Scenario analysis and shared statistics/loading
│   ├── model/                    # Slim benchmark object graph
│   ├── render/                   # Chart and HTML rendering
│   └── template/                 # Scenario HTML templates
├── results/                      # Generated raw results, charts, and reports
├── um24c/                        # UM24C serial protocol integration
├── requirements.txt              # Python dependencies
└── AGENTS.md                     # Repository guidance for coding agents
```

## Validation

Export the variables from `environment/benchmark.env` before running the Go test suite. On a POSIX shell:

```sh
cd benchmark
set -a
. ../environment/benchmark.env
set +a
go test ./...
cd ..
```

Python and formatting checks can be run from the repository root:

```sh
python -m compileall -q orchestrate report um24c
python -c "import report.analysis.aes_ascon_report; import report.analysis.json_cbor_report; import report.analysis.full_schema_report; import report.analysis.cpabe_rsa_report"
python -m black --check orchestrate report um24c
gofmt -d $(git ls-files '*.go')
git diff --check
```

The `gofmt` command uses POSIX command substitution; use the equivalent file-list expansion in PowerShell if needed.

## Docker status

The Python orchestrators above are the current supported execution path. Files under `orchestrate/docker/` and the present CI workflow still contain stale paths from an older layout and should not be used as execution documentation until they are updated.
