# MQTT Security Microbenchmarks

This repository evaluates security and serialization trade-offs for MQTT messaging using two devices: a laptop and a Raspberry Pi. The Raspberry Pi executes the measured Go workloads. The laptop coordinates the Pi over SSH, reads the UM24C power meter, stores the raw results, and runs the Python analysis that produces charts and HTML reports.

## Microbenchmarks

### 1. AES vs. ASCON

Shows how AES-GCM and ASCON authenticated encryption compare as message payloads grow.

- **Sweep:** payload size: 16 B, 64 B, 256 B, 1 KiB, 4 KiB, 16 KiB, 64 KiB, 256 KiB, and 1 MiB.
- **Variables:** AES-GCM or ASCON; Encrypt or Decrypt.
- **Metrics:** latency, throughput, energy per operation, peak RSS, ASCON speedup and energy reduction relative to AES-GCM, timing iterations, 95% confidence intervals, and separate timing/energy throttling observations.

### 2. JSON vs. CBOR

Shows the processing and wire-size cost of serializing the same encrypted envelope in JSON, CBOR with string keys, and CBOR with integer keys.

- **Sweep:** payload size: 16 B, 64 B, 256 B, 1 KiB, 4 KiB, 16 KiB, 64 KiB, 256 KiB, and 1 MiB.
- **Variables:** JSON, CBOR, or CBOR with integer keys; Serialize or Deserialize.
- **Metrics:** latency, encoded envelope size, raw binary size, wire overhead, energy per operation, speedup and energy reduction relative to JSON, timing iterations, 95% confidence intervals, and separate timing/energy throttling observations.

### 3. CP-ABE vs. RSA

Shows how policy-based CP-ABE compares with encrypting a symmetric key separately for every RSA subscriber.

- **Primary sweeps:** CP-ABE policy attributes: 1, 2, 4, 8, 16, and 32; RSA subscribers: 1, 2, 4, 8, 16, 32, and 64.
- **Secondary timing sweep:** RSA key size: 2048, 3072, and 4096 bits.
- **Variables:** CP-ABE or RSA; Encrypt or Decrypt; policy size, subscriber count, and RSA key size as applicable.
- **Metrics:** latency, energy per operation, peak RSS, ciphertext size, CP-ABE stored-key size, total RSA fan-out size, scaling slopes, crossovers, encrypt/decrypt asymmetry, timing iterations, 95% confidence intervals, and separate timing/energy throttling observations.

## Run

On the laptop, create and activate a Python environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Make sure the configured Raspberry Pi is reachable over SSH and the UM24C is available to the laptop. From the repository root, run one scenario at a time:

```sh
python orchestrate/orchestrate_aes_ascon.py
python orchestrate/orchestrate_json_cbor.py
python orchestrate/orchestrate_cpabe_rsa.py
```

Each command runs its complete benchmark and reporting pipeline. Raw measurements, charts, and `report.html` are written under the scenario's directory in `results/`.
