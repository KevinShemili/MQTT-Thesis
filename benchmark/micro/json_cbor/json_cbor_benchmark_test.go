package json_cbor

import (
	"benchmark/cryptography/aes"
	"benchmark/cryptography/cpabe"
	"benchmark/envelope"
	"benchmark/system/thermal"
	"benchmark/utility"
	"fmt"
	"testing"
)

type JSONCBORConfig struct {
	AttributeSizes []int
	PayloadSize    int
	AESKeySize     int
}

func BenchmarkEnvelopeSerialize(benchmark *testing.B) {

	config := loadJSONCBORConfig()

	// Scenario 1: JSON Scaling Attribute Count
	for _, attributeCount := range config.AttributeSizes {

		benchmark.Run(fmt.Sprintf("JSON/%dAttrs", attributeCount), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aes := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(config.PayloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aes.NonceSize())

			// Encrypt payload
			aesCiphertext := aes.Seal(nil, nonce, plaintext, nil)

			// Build policy for given attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				ABECiphertext: abeCiphertext,
				Nonce:         nonce,
				AESCiphertext: aesCiphertext,
			}

			// Size before serialization overhead is added
			rawSize := len(abeCiphertext) + len(nonce) + len(aesCiphertext)

			// Serialized size is fixed for this benchmark case, so measure once
			// outside the timed loop
			jsonEnvelopeSize := len(envelope.SerializeJSON(env))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.WatchThrottling()

			for b.Loop() {
				envelope.SerializeJSON(env)
			}

			b.ReportMetric(float64(jsonEnvelopeSize), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")

			if throttled, isAvailable := throttle.Throttled(); isAvailable {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}

	// Scenario 2: CBOR Scaling Attribute Count
	for _, attributeCount := range config.AttributeSizes {

		benchmark.Run(fmt.Sprintf("CBOR/%dAttrs", attributeCount), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(config.PayloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			// Encrypt payload
			aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Build policy for given attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				ABECiphertext: abeCiphertext,
				Nonce:         nonce,
				AESCiphertext: aesCiphertext,
			}

			// Size before serialization overhead is added
			rawSize := len(abeCiphertext) + len(nonce) + len(aesCiphertext)

			// Serialized size is fixed for this benchmark case, so measure once
			// outside the timed loop
			cborEnvelopeSize := len(envelope.SerializeCBOR(env))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.WatchThrottling()

			for b.Loop() {
				envelope.SerializeCBOR(env)
			}

			b.ReportMetric(float64(cborEnvelopeSize), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")

			if throttled, isAvailable := throttle.Throttled(); isAvailable {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}

	// Scenario 3: CBOR With Integer Keys Scaling Attribute Count
	for _, attributeCount := range config.AttributeSizes {

		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dAttrs", attributeCount), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(config.PayloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			// Encrypt payload
			aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Build policy for given attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope using integer keys
			env := envelope.EnvelopeIntKeys{
				ABECiphertext: abeCiphertext,
				Nonce:         nonce,
				AESCiphertext: aesCiphertext,
			}

			// Size before serialization overhead is added
			rawSize := len(abeCiphertext) + len(nonce) + len(aesCiphertext)

			// Serialized size is fixed for this benchmark case, so measure once
			// outside the timed loop
			cborEnvelopeSize := len(envelope.SerializeCBORKeyAsInt(env))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.WatchThrottling()

			for b.Loop() {
				envelope.SerializeCBORKeyAsInt(env)
			}

			b.ReportMetric(float64(cborEnvelopeSize), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")

			if throttled, isAvailable := throttle.Throttled(); isAvailable {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}
}

func BenchmarkEnvelopeDeserialize(benchmark *testing.B) {

	config := loadJSONCBORConfig()

	// Scenario 1: JSON Scaling Attribute Count
	for _, attributeCount := range config.AttributeSizes {

		benchmark.Run(fmt.Sprintf("JSON/%dAttrs", attributeCount), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(config.PayloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			// Encrypt payload
			aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Build policy for given attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				ABECiphertext: abeCiphertext,
				Nonce:         nonce,
				AESCiphertext: aesCiphertext,
			}

			// Size before serialization overhead is added
			rawSize := len(abeCiphertext) + len(nonce) + len(aesCiphertext)

			// Serialize outside timed loop so only deserialization is measured
			serializedEnvelope := envelope.SerializeJSON(env)

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.WatchThrottling()

			for b.Loop() {
				envelope.DeserializeJSON(serializedEnvelope)
			}

			b.ReportMetric(float64(len(serializedEnvelope)), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")

			if throttled, isAvailable := throttle.Throttled(); isAvailable {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}

	// Scenario 2: CBOR Scaling Attribute Count
	for _, attributeCount := range config.AttributeSizes {

		benchmark.Run(fmt.Sprintf("CBOR/%dAttrs", attributeCount), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(config.PayloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			// Encrypt payload
			aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Build policy for given attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope
			env := envelope.Envelope{
				ABECiphertext: abeCiphertext,
				Nonce:         nonce,
				AESCiphertext: aesCiphertext,
			}

			// Size before serialization overhead is added
			rawSize := len(abeCiphertext) + len(nonce) + len(aesCiphertext)

			// Serialize outside timed loop so only deserialization is measured
			serializedEnvelope := envelope.SerializeCBOR(env)

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.WatchThrottling()

			for b.Loop() {
				envelope.DeserializeCBOR(serializedEnvelope)
			}

			b.ReportMetric(float64(len(serializedEnvelope)), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")

			if throttled, isAvailable := throttle.Throttled(); isAvailable {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}

	// Scenario 3: CBOR With Integer Keys Scaling Attribute Count
	for _, attributeCount := range config.AttributeSizes {

		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dAttrs", attributeCount), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Instantiate AES-GCM cipher
			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
			aesGcm := aes.NewAES(symmetricKey)

			// Construct plaintext
			plaintext := utility.GenerateRandomBytes(config.PayloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(aesGcm.NonceSize())

			// Encrypt payload
			aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

			// Build policy for given attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			// Encrypt symmetric key under policy
			abeCiphertext := authority.Encrypt(abePolicy, symmetricKey)

			// Construct envelope using integer keys
			env := envelope.EnvelopeIntKeys{
				ABECiphertext: abeCiphertext,
				Nonce:         nonce,
				AESCiphertext: aesCiphertext,
			}

			// Size before serialization overhead is added
			rawSize := len(abeCiphertext) + len(nonce) + len(aesCiphertext)

			// Serialize outside timed loop so only deserialization is measured
			serializedEnvelope := envelope.SerializeCBORKeyAsInt(env)

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			waitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.WatchThrottling()

			for b.Loop() {
				envelope.DeserializeCBORKeyAsInt(serializedEnvelope)
			}

			b.ReportMetric(float64(len(serializedEnvelope)), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")

			if throttled, isAvailable := throttle.Throttled(); isAvailable {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}
}

func loadJSONCBORConfig() JSONCBORConfig {

	return JSONCBORConfig{
		AttributeSizes: utility.ParseIntListFromEnv("JSON_CBOR_ATTRIBUTE_COUNTS"),
		PayloadSize:    utility.ParseIntFromEnv("JSON_CBOR_PAYLOAD_SIZE"),
		AESKeySize:     utility.ParseIntFromEnv("AES_ASCON_KEY_SIZE"),
	}
}

func waitForCooldown() {
	thermal.WaitForCooldown(
		utility.ParseIntFromEnv("THERMAL_COOLDOWN_CELSIUS"),
		thermal.CooldownTimeout,
	)
}
