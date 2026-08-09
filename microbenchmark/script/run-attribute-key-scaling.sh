#!/bin/sh
set -eu

ResultDirectory=/results/attribute-key-scaling
OutputFile="${ResultDirectory}/bench_output.txt"
ExitCodeFile="${ResultDirectory}/case_exit_codes.txt"

mkdir -p "${ResultDirectory}"
: > "${OutputFile}"
printf '# case exit_code (0 = ok, 2 = panic, 137 = OOM-killed)\n' > "${ExitCodeFile}"
rm -rf key-cache # ensure old keys are not used in PI

echo 'Phase 1 of 3 - CP-ABE attribute scaling'

for AttributeCount in $(echo "${ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT}" | tr ',' ' '); do
  Label="CPABEAttributes/${AttributeCount}"

  echo "  ${Label}"

  set +e
  ./benchmark-binary \
    -test.run='^$' \
    -test.bench="^BenchmarkAttributeKeyScaling(Encrypt|Decrypt)\$/^CPABEAttributes/${AttributeCount}\$" \
    -test.benchtime='5s' \
    -test.count="${ATTRIBUTE_KEY_SCALING_RUNS}" \
    -test.timeout=0 \
    >> "${OutputFile}"
  ExitCode=$?
  set -e

    printf '%-40s %d\n' "${Label}" "${ExitCode}" >> "${ExitCodeFile}"
done

echo 'Phase 2 of 3 - RSA subscriber and key-size scaling'

for SubscriberCount in $(echo "${ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT}" | tr ',' ' '); do
  Label="RSASubscribers/${SubscriberCount}"

  echo "  ${Label}"

  set +e
  ./benchmark-binary \
    -test.run='^$' \
    -test.bench="^BenchmarkAttributeKeyScaling(Encrypt|Decrypt)\$/^RSASubscribers/${SubscriberCount}\$" \
    -test.benchtime='5s' \
    -test.count="${ATTRIBUTE_KEY_SCALING_RUNS}" \
    -test.timeout=0 \
    >> "${OutputFile}"
  ExitCode=$?
  set -e

    printf '%-40s %d\n' "${Label}" "${ExitCode}" >> "${ExitCodeFile}"
done

for RSAKeyBits in $(echo "${ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES}" | tr ',' ' '); do
  Label="RSAKeyBits/${RSAKeyBits}"

  echo "  ${Label}"

  set +e
  ./benchmark-binary \
    -test.run='^$' \
    -test.bench="^BenchmarkAttributeKeyScaling(Encrypt|Decrypt)\$/^RSAKeyBits/${RSAKeyBits}\$" \
    -test.benchtime='5s' \
    -test.count="${ATTRIBUTE_KEY_SCALING_RUNS}" \
    -test.timeout=0 \
    >> "${OutputFile}"
  ExitCode=$?
  set -e

    printf '%-40s %d\n' "${Label}" "${ExitCode}" >> "${ExitCodeFile}"
done

echo 'Phase 3 of 3 - RSA key generation'

for RSAKeyBits in $(echo "${ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES}" | tr ',' ' '); do
  Label="KeyGen/RSAKeyBits/${RSAKeyBits}"

  echo "  ${Label}"

  set +e
  ./benchmark-binary \
    -test.run='^$' \
    -test.bench="^BenchmarkAttributeKeyScalingKeyGen\$/^RSAKeyBits/${RSAKeyBits}\$" \
    -test.benchtime='1x' \
    -test.count="${ATTRIBUTE_KEY_SCALING_KEYGEN_RUNS}" \
    -test.timeout=0 \
    >> "${OutputFile}"
  ExitCode=$?
  set -e

    printf '%-40s %d\n' "${Label}" "${ExitCode}" >> "${ExitCodeFile}"
done

echo 'Generating Attribute & Key Scaling HTML report...'

python3 src/attribute_key_scaling_report.py