package benchmark

import (
	"fmt"
	"project/cryptography/aes"
	"project/cryptography/cpabe"
	"project/envelope"
	"project/utils"
	"testing"
)

type JSONCBORConfig struct {
	AttributeSizes []int
	PayloadSize    int
	AESKeySize     int
}

func BenchmarkEnvelopeSerialize(benchmark *testing.B) {

	config := loadJSONCBORConfig()

	// Define key of AES-GCM
	symmetricKey := utils.GenerateRandomBytes(config.AESKeySize)

	// Construct CP-ABE & AES-GCM outside timed benchmarks
	cpAbe := cpabe.NewCPABEAuthority()
	aesGcm := aes.NewAES(symmetricKey)

	plaintext := utils.GenerateRandomBytes(config.PayloadSize)
	nonce := utils.GenerateRandomBytes(aesGcm.NonceSize())
	aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

	for _, attributeCount := range config.AttributeSizes {

		// Stick to synthetic `AND` policies so that ciphertext size grows with every added attribute
		abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

		// Encrypt the session key under policy
		abeCiphertext := cpAbe.Encrypt(abePolicy, symmetricKey)

		// Construct the envelope outside timed benchmarks
		env := envelope.Envelope{
			ABECiphertext: abeCiphertext,
			Nonce:         nonce,
			AESCiphertext: aesCiphertext,
		}

		envKeyAsInt := envelope.EnvelopeIntKeys{
			ABECiphertext: abeCiphertext,
			Nonce:         nonce,
			AESCiphertext: aesCiphertext,
		}

		// Size before JSON / CBOR overhead is added
		rawSize := len(abeCiphertext) + len(nonce) + len(aesCiphertext)

		benchmark.Run(fmt.Sprintf("JSON/%dAttrs", attributeCount), func(b *testing.B) {

			// Size after JSON overhead
			jsonEnvelopeSize := len(envelope.SerializeJSON(env))

			throttle := utils.WatchThrottling()

			for b.Loop() {
				envelope.SerializeJSON(env)
			}

			b.ReportMetric(float64(jsonEnvelopeSize), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})

		benchmark.Run(fmt.Sprintf("CBOR/%dAttrs", attributeCount), func(b *testing.B) {

			cborEnvelopeSize := len(envelope.SerializeCBOR(env))

			throttle := utils.WatchThrottling()

			for b.Loop() {
				envelope.SerializeCBOR(env)
			}

			b.ReportMetric(float64(cborEnvelopeSize), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})

		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dAttrs", attributeCount), func(b *testing.B) {

			cborKeyAsIntEnvelopeSize := len(envelope.SerializeCBORKeyAsInt(envKeyAsInt))

			throttle := utils.WatchThrottling()

			for b.Loop() {
				envelope.SerializeCBORKeyAsInt(envKeyAsInt)
			}

			b.ReportMetric(float64(cborKeyAsIntEnvelopeSize), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}
}

func BenchmarkEnvelopeDeserialize(benchmark *testing.B) {

	config := loadJSONCBORConfig()

	// Define key of AES-GCM
	symmetricKey := utils.GenerateRandomBytes(config.AESKeySize)

	// Construct CP-ABE & AES-GCM outside timed benchmarks
	cpAbe := cpabe.NewCPABEAuthority()
	aesGcm := aes.NewAES(symmetricKey)

	plaintext := utils.GenerateRandomBytes(config.PayloadSize)
	nonce := utils.GenerateRandomBytes(aesGcm.NonceSize())
	aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

	for _, attributeCount := range config.AttributeSizes {

		// Stick to synthetic `AND` policies so that ciphertext size grows with every added attribute
		abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

		// Encrypt the session key under policy
		abeCiphertext := cpAbe.Encrypt(abePolicy, symmetricKey)

		// Construct the envelope outside timed benchmarks
		env := envelope.Envelope{
			ABECiphertext: abeCiphertext,
			Nonce:         nonce,
			AESCiphertext: aesCiphertext,
		}

		envKeyAsInt := envelope.EnvelopeIntKeys{
			ABECiphertext: abeCiphertext,
			Nonce:         nonce,
			AESCiphertext: aesCiphertext,
		}

		// Size before JSON / CBOR overhead is added
		rawSize := len(env.ABECiphertext) + len(env.Nonce) + len(env.AESCiphertext)

		// Serialize the envelope to JSON and CBOR outside timed benchmarks
		jsonSerializedEnvelope := envelope.SerializeJSON(env)
		cborSerializedEnvelope := envelope.SerializeCBOR(env)
		cborKeyAsIntSerializedEnvelope := envelope.SerializeCBORKeyAsInt(envKeyAsInt)

		benchmark.Run(fmt.Sprintf("JSON/%dAttrs", attributeCount), func(b *testing.B) {

			throttle := utils.WatchThrottling()

			for b.Loop() {
				envelope.DeserializeJSON(jsonSerializedEnvelope)
			}

			b.ReportMetric(float64(len(jsonSerializedEnvelope)), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})

		benchmark.Run(fmt.Sprintf("CBOR/%dAttrs", attributeCount), func(b *testing.B) {

			throttle := utils.WatchThrottling()

			for b.Loop() {
				envelope.DeserializeCBOR(cborSerializedEnvelope)
			}

			b.ReportMetric(float64(len(cborSerializedEnvelope)), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})

		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dAttrs", attributeCount), func(b *testing.B) {

			throttle := utils.WatchThrottling()

			for b.Loop() {
				envelope.DeserializeCBORKeyAsInt(cborKeyAsIntSerializedEnvelope)
			}

			b.ReportMetric(float64(len(cborKeyAsIntSerializedEnvelope)), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
			if throttled, available := throttle.Throttled(); available {
				b.ReportMetric(throttled, "throttled")
			}
		})
	}
}

func loadJSONCBORConfig() JSONCBORConfig {

	return JSONCBORConfig{
		AttributeSizes: utils.ParseIntListFromEnv("JSON_CBOR_ATTRIBUTE_COUNTS"),
		PayloadSize:    utils.ParseIntFromEnv("JSON_CBOR_PAYLOAD_SIZE"),
		AESKeySize:     utils.ParseIntFromEnv("AES_ASCON_KEY_SIZE"),
	}
}
