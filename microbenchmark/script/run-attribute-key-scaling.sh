#!/bin/sh

mkdir -p /results/attribute-key-scaling

echo 'Running Attribute & Key Scaling benchmark...'

AttributeCountCount=$(echo "${ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT}" | tr ',' '\n' | wc -l)
RecipientCountCount=$(echo "${ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT}" | tr ',' '\n' | wc -l)
RSAKeyBitsCount=$(echo "${ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES}" | tr ',' '\n' | wc -l)

# Encrypt & Decrypt cover every sweep value; KeyGen skips the recipient sweep, since key size is fixed there
EncryptDecryptCases=$((2 * (AttributeCountCount + RecipientCountCount + RSAKeyBitsCount)))
KeyGenCases=$((AttributeCountCount + RSAKeyBitsCount))

EncryptDecryptLines=$((EncryptDecryptCases * ATTRIBUTE_KEY_SCALING_RUNS))
KeyGenLines=$((KeyGenCases * ATTRIBUTE_KEY_SCALING_RUNS))

# Per-message operations: time-budgeted, like every other scenario
./benchmark-binary \
  -test.run=^$ \
  -test.bench='^BenchmarkAttributeKeyScaling(Encrypt|Decrypt)$' \
  -test.benchtime=5s \
  -test.count=${ATTRIBUTE_KEY_SCALING_RUNS} \
  -test.cpu=1 \
  | pv \
      --force \
      --wait \
      --line-mode \
      --size "${EncryptDecryptLines}" \
      --interval 5 \
      --format "Attribute & Key Scaling (Encrypt/Decrypt): %p %e" \
      > /results/attribute-key-scaling/bench_output.txt

# Key generation: iteration-budgeted, so slow RSA-4096 draws still get a real average
# instead of the 1-3 iterations a time budget would allow them
./benchmark-binary \
  -test.run=^$ \
  -test.bench=^BenchmarkAttributeKeyScalingKeyGen$ \
  -test.benchtime=20x \
  -test.count=${ATTRIBUTE_KEY_SCALING_RUNS} \
  -test.cpu=1 \
  | pv \
      --force \
      --wait \
      --line-mode \
      --size "${KeyGenLines}" \
      --interval 5 \
      --format "Attribute & Key Scaling (KeyGen): %p %e" \
      >> /results/attribute-key-scaling/bench_output.txt

echo 'Generating Attribute & Key Scaling HTML report...'

python3 src/attribute_key_scaling_report.py