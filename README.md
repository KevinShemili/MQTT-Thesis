[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-highlight.svg)](https://sonarcloud.io/summary/new_code?id=KevinShemili_MQTT-Thesis)
[![Lines of Code](https://sonarcloud.io/api/project_badges/measure?project=KevinShemili_MQTT-Thesis&metric=ncloc)](https://sonarcloud.io/summary/new_code?id=KevinShemili_MQTT-Thesis)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=KevinShemili_MQTT-Thesis&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=KevinShemili_MQTT-Thesis)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=KevinShemili_MQTT-Thesis&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=KevinShemili_MQTT-Thesis)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=KevinShemili_MQTT-Thesis&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=KevinShemili_MQTT-Thesis)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=KevinShemili_MQTT-Thesis&metric=coverage)](https://sonarcloud.io/summary/new_code?id=KevinShemili_MQTT-Thesis)

# MQTT Security Benchmarks

## Microbenchmarks

### AES vs. ASCON

Compares AES-GCM and ASCON encryption and decryption across payload sizes.

Metrics: operation latency, throughput, energy per operation, and peak resident memory (RSS). Reports also compare speed and energy consumption.

### JSON vs. CBOR

Compares serialization and deserialization using JSON, CBOR with string keys, and CBOR with integer keys across payload sizes.

Metrics: operation latency, energy per operation, raw and serialized message sizes, and wire overhead. Reports also compare speed and energy consumption.

### CP-ABE vs. RSA

Compares CP-ABE and RSA for encrypting and decrypting a symmetric key. Varies CP-ABE policy attribute counts and RSA subscriber counts, with a separate RSA key-size timing sweep.

Metrics: operation latency, energy per operation, peak RSS, ciphertext size, CP-ABE private-key size, and total RSA ciphertext size across subscribers. Reports also compare scaling, crossover points, and encryption/decryption cost.

### Full schema

Compares six combinations of key handling, payload encryption, and serialization: pre-shared keys (PSK), RSA, or CP-ABE, each paired with either AES-GCM and JSON or ASCON and CBOR. Measures encryption plus serialization and deserialization plus decryption across payload sizes.

Metrics: combined operation latency, energy per operation, peak RSS, and serialized envelope size.

All four microbenchmarks record timing iteration counts and separate timing/energy throttling observations. Reports include 95% confidence intervals for repeated measurements.

## Macrobenchmark: MQTT-over-TLS baseline

Measures JSON messages sent from a publisher through a broker to a subscriber over MQTT 3.1.1, QoS 0, and TLS 1.3, across payload sizes. Payloads have no additional application-level encryption.

Metrics: one-way end-to-end latency, from before publisher serialization to after subscriber deserialization, and separate publisher/subscriber CPU cycle totals per repetition. Reports include means and 95% confidence intervals.

## Run benchmarks

Run from the repository root on the laptop, with the benchmark environment configured in `environment/benchmark.env`. Choose the corresponding orchestrator:

```bash
python orchestrate/orchestrate_aes_ascon.py
python orchestrate/orchestrate_json_cbor.py
python orchestrate/orchestrate_cpabe_rsa.py
python orchestrate/orchestrate_full_schema.py
go run ./orchestrate/orchestrate_macro.go
```

Each orchestrator runs the benchmark and generates its report.

## Generate reports from existing results

With the result CSVs present in the directories configured in `environment/benchmark.env`, run the corresponding command from the repository root:

```bash
python -m report.analysis.aes_ascon_report
python -m report.analysis.json_cbor_report
python -m report.analysis.cpabe_rsa_report
python -m report.analysis.full_schema_report
python -m report.analysis.macro_report
```

Charts and `report.html` are written alongside the results.
