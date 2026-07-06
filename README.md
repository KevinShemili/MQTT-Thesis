# MQTT Thesis Benchmarks

## Structure

```text
microbenchmark/
  docker-compose.yml
  Dockerfile
  golang/
    benchmark/        # Go benchmark suites
    cryptography/     # AES, ASCON, CP-ABE helpers
    envelope/         # JSON/CBOR envelope model
  python/
    src/              # Report generators
    template/         # HTML report templates
  script/             # Docker benchmark entrypoints
  results/            # Generated benchmark outputs
```

## Commands

Run from the benchmark directory:

```sh
cd microbenchmark
```

Build images:

```sh
docker compose build
```

Run all benchmarks:

```sh
docker compose up --build
```

Run AES vs ASCON benchmark:

```sh
docker compose run --rm aes-ascon
```

Run JSON vs CBOR benchmark:

```sh
docker compose run --rm json-cbor
```

Clean stopped benchmark containers:

```sh
docker compose down
```

## Services

| Service     | Container             | Output                              |
| ----------- | --------------------- | ----------------------------------- |
| `aes-ascon` | `aes-ascon-benchmark` | `microbenchmark/results/aes-ascon/` |
| `json-cbor` | `json-cbor-benchmark` | `microbenchmark/results/json-cbor/` |

## Output Files

Each benchmark writes:

- `bench_output.txt`
- `report.html`
- generated `.png` charts
