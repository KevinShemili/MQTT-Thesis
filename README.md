# MQTT Security Microbenchmarks

This repository contains the reproducible microbenchmark suite used to study cryptographic and serialization trade-offs for secure MQTT messaging. The benchmarks are implemented in Go, executed in Docker, and converted into HTML reports and charts by Python.

The suite currently covers four questions:

| Scenario | What it measures | Compared approaches |
| --- | --- | --- |
| Payload-size scaling | Encryption/decryption latency, throughput, wire overhead, asymmetry, and additivity as payloads grow | Pre-shared AES-GCM, RSA + AES-GCM, and CP-ABE + AES-GCM |
| Attribute and key scaling | The cost of growing access policies, subscriber sets, and RSA keys | CP-ABE attribute counts, RSA subscriber counts, and RSA modulus sizes |
| Envelope serialization | Serialization/deserialization latency and encoded envelope size | JSON, CBOR with string keys, and CBOR with integer keys |
| Symmetric cipher comparison | Encryption/decryption latency, throughput, and wire overhead across payload sizes | AES-GCM and ASCON using the host's default CPU features, then with AES acceleration disabled |

## Requirements

- Docker Engine or Docker Desktop
- Docker Compose v2 (`docker compose`)
- A POSIX-compatible shell for the orchestration script (Linux/macOS shell, WSL, or Git Bash)

Go and Python do not need to be installed on the host. The Docker image contains the pinned toolchain and reporting dependencies.

## Run the benchmark suite

From the repository root:

```sh
cd microbenchmark
sh script/run-sequentially.sh
```

This is the recommended workflow. It builds and runs every scenario **sequentially**, preventing concurrently running benchmarks from competing for CPU and memory. Docker's build cache is reused between scenarios.

The full matrix is intentionally thorough and can take a while. To shorten or change an experiment, edit [`microbenchmark/config/benchmark.env`](microbenchmark/config/benchmark.env) before starting the run.

### Run a selected scenario

Use the same generic Compose pattern with one of the service names from the table below:

```sh
docker compose build <service>
docker compose run --rm <service>
```

| Service | Result directory |
| --- | --- |
| `payload-scaling` | `results/payload-scaling/` |
| `attribute-key-scaling` | `results/attribute-key-scaling/` |
| `json-cbor` | `results/json-cbor/` |
| `aes-ascon-with-acceleration` | `results/aes-ascon/with-acceleration/` |
| `aes-ascon-without-acceleration` | `results/aes-ascon/without-acceleration/` |

Avoid using `docker compose up` for performance measurements: it starts independent services concurrently and can introduce resource contention.

## Configuration

All experiment inputs are centralized in [`benchmark.env`](microbenchmark/config/benchmark.env). They are grouped by scenario and control:

- the number of repeated benchmark runs;
- payload sizes in bytes;
- CP-ABE attribute counts;
- RSA subscriber counts and modulus sizes;
- AES key size and fixed comparison parameters.


## Results

Each run writes directly to [`microbenchmark/results/`](microbenchmark/results) through a Docker volume and replaces the files for the corresponding scenario:

- `bench_output.txt` — raw Go benchmark output;
- `report.html` — tables, summary statistics, methodology notes, and embedded chart references;
- `*.png` — generated comparison charts.

The repository includes the latest generated result set:

- [Payload-size scaling report](microbenchmark/results/payload-scaling/report.html)
- [Attribute and key scaling report](microbenchmark/results/attribute-key-scaling/report.html)
- [JSON/CBOR report](microbenchmark/results/json-cbor/report.html)
- [AES/ASCON report with acceleration](microbenchmark/results/aes-ascon/with-acceleration/report.html)
- [AES/ASCON report without acceleration](microbenchmark/results/aes-ascon/without-acceleration/report.html)

Because benchmark results depend on the host CPU, system load, Docker runtime, and hardware acceleration support, comparisons should be made from reports produced on the same machine under similar conditions.

## Repository structure

```text
.
├── .github/workflows/ci.yml        # Compose, build, static, and test validation
├── docs/
│   ├── Benchmark Matrix.pdf        # Experiment design and benchmark matrix
│   └── Thesis Proposal.pdf         # Thesis proposal
└── microbenchmark/
    ├── config/benchmark.env        # Complete experiment configuration
    ├── docker-compose.yml          # One service per benchmark scenario/variant
    ├── Dockerfile                  # Reproducible Go + Python benchmark image
    ├── golang/
    │   ├── benchmark/              # Go benchmark implementations
    │   ├── cryptography/           # AES-GCM, ASCON, RSA, and CP-ABE adapters
    │   ├── envelope/               # JSON and CBOR envelope representations
    │   └── utils/                  # Environment parsing and test-data helpers
    ├── python/
    │   ├── src/                    # Scenario report generators
    │   │   └── reporting/          # Shared parsing, statistics, chart, and HTML code
    │   └── template/               # HTML report templates
    ├── results/                    # Raw outputs, HTML reports, and charts
    └── script/
        ├── run-sequentially.sh     # Recommended full-suite entry point
        └── run-*.sh                # Per-scenario container entry points
```