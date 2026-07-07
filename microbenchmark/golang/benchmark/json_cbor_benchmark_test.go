package benchmark

import (
	"fmt"
	"project/cryptography"
	"project/envelope"
	"project/utils"
	"testing"
)

var attributeCountList []int = utils.ParseIntListFromEnv("JSON_CBOR_ATTRIBUTE_COUNTS")
var fixedPayloadSize int = utils.ParseIntFromEnv("JSON_CBOR_PAYLOAD_SIZE")

func BenchmarkEnvelopeSerialize(benchmark *testing.B) {

	// Define key of AES-GCM
	sessionKey := utils.GenerateRandomBytes(utils.ParseIntFromEnv("AES_ASCON_KEY_SIZE"))

	// Construct CP-ABE & AES-GCM outside timed benchmarks
	cpAbe := cryptography.NewCPABE()
	aesGcm := cryptography.NewAESGCM(sessionKey)

	plaintext := utils.GenerateRandomBytes(fixedPayloadSize)
	nonce := utils.GenerateRandomBytes(aesGcm.NonceSize())
	aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

	for index := range attributeCountList {

		attributeCount := attributeCountList[index]

		// Stick to synthetic `AND` policies so that ciphertext size grows with every added attribute
		abePolicy := cryptography.BuildSyntheticConjunctivePolicy(attributeCount)

		// Encrypt the session key under policy
		abeCiphertext := cpAbe.Encrypt(abePolicy, sessionKey)

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

			for b.Loop() {
				envelope.SerializeJSON(env)
			}

			b.ReportMetric(float64(jsonEnvelopeSize), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
		})

		benchmark.Run(fmt.Sprintf("CBOR/%dAttrs", attributeCount), func(b *testing.B) {

			cborEnvelopeSize := len(envelope.SerializeCBOR(env))

			for b.Loop() {
				envelope.SerializeCBOR(env)
			}

			b.ReportMetric(float64(cborEnvelopeSize), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
		})

		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dAttrs", attributeCount), func(b *testing.B) {

			cborKeyAsIntEnvelopeSize := len(envelope.SerializeCBORKeyAsInt(envKeyAsInt))

			for b.Loop() {
				envelope.SerializeCBORKeyAsInt(envKeyAsInt)
			}

			b.ReportMetric(float64(cborKeyAsIntEnvelopeSize), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
		})
	}
}

func BenchmarkEnvelopeDeserialize(benchmark *testing.B) {

	// Define key of AES-GCM
	sessionKey := utils.GenerateRandomBytes(utils.ParseIntFromEnv("AES_ASCON_KEY_SIZE"))

	// Construct CP-ABE & AES-GCM outside timed benchmarks
	cpAbe := cryptography.NewCPABE()
	aesGcm := cryptography.NewAESGCM(sessionKey)

	plaintext := utils.GenerateRandomBytes(fixedPayloadSize)
	nonce := utils.GenerateRandomBytes(aesGcm.NonceSize())
	aesCiphertext := aesGcm.Seal(nil, nonce, plaintext, nil)

	for index := range attributeCountList {

		attributeCount := attributeCountList[index]

		// Stick to synthetic `AND` policies so that ciphertext size grows with every added attribute
		abePolicy := cryptography.BuildSyntheticConjunctivePolicy(attributeCount)

		// Encrypt the session key under policy
		abeCiphertext := cpAbe.Encrypt(abePolicy, sessionKey)

		// Construct the envelope outside timed benchmarks
		var env envelope.Envelope = envelope.Envelope{
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

			for b.Loop() {
				envelope.DeserializeJSON(jsonSerializedEnvelope)
			}

			b.ReportMetric(float64(len(jsonSerializedEnvelope)), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
		})

		benchmark.Run(fmt.Sprintf("CBOR/%dAttrs", attributeCount), func(b *testing.B) {

			for b.Loop() {
				envelope.DeserializeCBOR(cborSerializedEnvelope)
			}

			b.ReportMetric(float64(len(cborSerializedEnvelope)), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
		})

		benchmark.Run(fmt.Sprintf("CBORKeyAsInt/%dAttrs", attributeCount), func(b *testing.B) {

			for b.Loop() {
				envelope.DeserializeCBORKeyAsInt(cborKeyAsIntSerializedEnvelope)
			}

			b.ReportMetric(float64(len(cborKeyAsIntSerializedEnvelope)), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
		})
	}
}
