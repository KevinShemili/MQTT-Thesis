#!/bin/sh
mkdir -p /results/json-cbor
echo 'Running JSON/CBOR Serialization benchmark...'
./benchmark-binary \
  -test.run=^$ \
  -test.bench=^BenchmarkEnvelope \
  -test.benchtime=5s \
  -test.benchmem \
  -test.count=4 \
  -test.cpu=1 \
  > /results/json-cbor/bench_output.txt
echo 'Generating JSON/CBOR Serialization HTML report...'
python3 src/json_cbor_report.py