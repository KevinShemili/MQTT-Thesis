#!/bin/sh
# run-aes-ascon.sh
mkdir -p /results/aes-ascon
echo 'Running AES vs ASCON benchmark...'
./benchmark-binary \
  -test.run=^$ \
  -test.bench=^BenchmarkAESASCON \
  -test.benchtime=5s \
  -test.benchmem \
  -test.count=4 \
  -test.cpu=1 \
  > /results/aes-ascon/bench_output.txt
echo 'Generating AES vs ASCON HTML report...'
python3 src/aes_ascon_report.py