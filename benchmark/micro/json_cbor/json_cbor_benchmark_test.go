package json_cbor

import (
	"fmt"
	"testing"
	"thesis/benchmark/cryptography/aes"
	"thesis/benchmark/cryptography/cpabe"
	"thesis/benchmark/micro/json_cbor/shared"
	"thesis/benchmark/thermal"
	"thesis/benchmark/utility"
	"thesis/internal/envelope"
	"thesis/internal/serialization"
)

func BenchmarkEnvelopeSerialize(benchmark *testing.B) {

	config := shared.NewJSONCBORConfig()

	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	// Scenario 1: JSON Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("JSON/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build the fixed CP-ABE policy used by every payload-size case
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.CPABEAttributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				AsymmetricCiphertext: abeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  aesCiphertext,
			}

			// Size of the three binary fields before serialization overhead is added
			rawSize := len(abeCiphertext) + len(nonce) + len(aesCiphertext)

			// Serialized size is fixed for this benchmark case, so measure once
			// outside the timed loop
			serializedEnvelope, _ := jsonSerializer.Serialize(env)
			jsonEnvelopeSize := len(serializedEnvelope)

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				jsonSerializer.Serialize(env)
			}

			b.ReportMetric(float64(jsonEnvelopeSize), "envelope_bytes")
			b.ReportMetric(float64(rawSize), "raw_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: CBOR Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CBOR/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			// Encrypt payload
			aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Build the fixed CP-ABE policy used by every payload-size case
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.CPABEAttributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				AsymmetricCiphertext: abeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  aesCiphertext,
			}

			// Size of the three binary fields before serialization overhead is added
			rawSize := len(abeCiphertext) + len(nonce) + len(aesCiphertext)

			// Serialized size is fixed for this benchmark case, so measure once
			// outside the timed loop
			serializedEnvelope, _ := cborSerializer.Serialize(env)
			cborEnvelopeSize := len(serializedEnvelope)

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				cborSerializer.Serialize(env)
			}

			b.ReportMetric(float64(cborEnvelopeSize), "envelope_bytes")
			b.ReportMetric(float64(rawSize), "raw_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 3: CBOR With Integer Keys Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			// Encrypt payload
			aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Build the fixed CP-ABE policy used by every payload-size case
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.CPABEAttributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope using integer keys
			env := envelope.EnvelopeIntKeys{
				AsymmetricCiphertext: abeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  aesCiphertext,
			}

			// Size of the three binary fields before serialization overhead is added
			rawSize := len(abeCiphertext) + len(nonce) + len(aesCiphertext)

			// Serialized size is fixed for this benchmark case, so measure once
			// outside the timed loop
			serializedEnvelope, _ := cborSerializer.Serialize(env)
			cborEnvelopeSize := len(serializedEnvelope)

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				cborSerializer.Serialize(env)
			}

			b.ReportMetric(float64(cborEnvelopeSize), "envelope_bytes")
			b.ReportMetric(float64(rawSize), "raw_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func BenchmarkEnvelopeDeserialize(benchmark *testing.B) {

	config := shared.NewJSONCBORConfig()

	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	// Scenario 1: JSON Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("JSON/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			// Encrypt payload
			aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Build the fixed CP-ABE policy used by every payload-size case
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.CPABEAttributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				AsymmetricCiphertext: abeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  aesCiphertext,
			}

			// Serialize outside timed loop so only deserialization is measured
			serializedEnvelope, _ := jsonSerializer.Serialize(env)

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var decoded envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &decoded)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: CBOR Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CBOR/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			// Encrypt payload
			aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Build the fixed CP-ABE policy used by every payload-size case
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.CPABEAttributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				AsymmetricCiphertext: abeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  aesCiphertext,
			}

			// Serialize outside timed loop so only deserialization is measured
			serializedEnvelope, _ := cborSerializer.Serialize(env)

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var decoded envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &decoded)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 3: CBOR With Integer Keys Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			// Encrypt payload
			aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Build the fixed CP-ABE policy used by every payload-size case
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.CPABEAttributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope using integer keys
			env := envelope.EnvelopeIntKeys{
				AsymmetricCiphertext: abeCiphertext,
				Nonce:                nonce,
				SymmetricCiphertext:  aesCiphertext,
			}

			// Serialize outside timed loop so only deserialization is measured
			serializedEnvelope, _ := cborSerializer.Serialize(env)

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var decoded envelope.EnvelopeIntKeys
				cborSerializer.Deserialize(serializedEnvelope, &decoded)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}
