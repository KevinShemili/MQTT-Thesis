package benchmark

import (
	"fmt"
	"project/cryptography"
	"project/envelope"
	"project/utils"
	"testing"

	"github.com/cloudflare/circl/abe/cpabe/tkn20"
)

// AttributeCountList is the set of CP-ABE policy sizes this benchmark sweeps over.
var AttributeCountList []int = []int{1, 2, 5, 10, 20, 50}

// FixedPayloadSize is the AES-GCM plaintext size held constant while attribute count varies.
var FixedPayloadSize int = 256

func BenchmarkEnvelopeSerialize(benchmark *testing.B) {

	// AES-GCM side is fixed for this benchmark, so build it once.
	var aesGcm cryptography.AESGCM = cryptography.NewAESGCM()
	var plaintext []byte = utils.GenerateRandomBytes(FixedPayloadSize)
	var nonce []byte = utils.GenerateRandomBytes(aesGcm.NonceSize())
	var ciphertext []byte = aesGcm.Seal(nil, nonce, plaintext, nil)

	// CP-ABE Setup is expensive and independent of attribute count, so it runs once.
	var cpAbe cryptography.CPABE = cryptography.NewCPABE()

	// The CP-ABE plaintext stands in for the AES-GCM session key that would really be protected.
	var sessionKey []byte = utils.GenerateRandomBytes(16)

	var index int
	for index = 0; index < len(AttributeCountList); index++ {

		var attributeCount int = AttributeCountList[index]

		// Real CP-ABE encryption happens once per attribute count, outside every timed loop below.
		var policy tkn20.Policy = cryptography.BuildConjunctivePolicy(attributeCount)
		var cpAbeCiphertext []byte = cpAbe.Encrypt(policy, sessionKey)

		var env envelope.Envelope = envelope.Envelope{
			CpAbeCiphertext: cpAbeCiphertext,
			Nonce:           nonce,
			Ciphertext:      ciphertext,
		}

		var rawSize int = len(cpAbeCiphertext) + len(nonce) + len(ciphertext)

		benchmark.Run(fmt.Sprintf("JSON/%dAttrs", attributeCount), func(b *testing.B) {

			var envelopeSize int = len(envelope.SerializeJson(env))

			for b.Loop() {
				envelope.SerializeJson(env)
			}

			b.ReportMetric(float64(envelopeSize), "envelope_bytes/op")
			// Reports the pre-serialization size so the report script can compute format overhead.
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
		})

		benchmark.Run(fmt.Sprintf("CBOR/%dAttrs", attributeCount), func(b *testing.B) {

			var envelopeSize int = len(envelope.SerializeCbor(env))

			for b.Loop() {
				envelope.SerializeCbor(env)
			}

			b.ReportMetric(float64(envelopeSize), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
		})
	}
}

func BenchmarkEnvelopeDeserialize(benchmark *testing.B) {

	var aesGcm cryptography.AESGCM = cryptography.NewAESGCM()
	var plaintext []byte = utils.GenerateRandomBytes(FixedPayloadSize)
	var nonce []byte = utils.GenerateRandomBytes(aesGcm.NonceSize())
	var ciphertext []byte = aesGcm.Seal(nil, nonce, plaintext, nil)

	var cpAbe cryptography.CPABE = cryptography.NewCPABE()
	var sessionKey []byte = utils.GenerateRandomBytes(16)

	var index int
	for index = 0; index < len(AttributeCountList); index++ {

		var attributeCount int = AttributeCountList[index]

		var policy tkn20.Policy = cryptography.BuildConjunctivePolicy(attributeCount)
		var cpAbeCiphertext []byte = cpAbe.Encrypt(policy, sessionKey)

		var env envelope.Envelope = envelope.Envelope{
			CpAbeCiphertext: cpAbeCiphertext,
			Nonce:           nonce,
			Ciphertext:      ciphertext,
		}

		var rawSize int = len(cpAbeCiphertext) + len(nonce) + len(ciphertext)

		var jsonBytes []byte = envelope.SerializeJson(env)
		var cborBytes []byte = envelope.SerializeCbor(env)

		benchmark.Run(fmt.Sprintf("JSON/%dAttrs", attributeCount), func(b *testing.B) {
			for b.Loop() {
				envelope.DeserializeJson(jsonBytes)
			}
			b.ReportMetric(float64(len(jsonBytes)), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
		})

		benchmark.Run(fmt.Sprintf("CBOR/%dAttrs", attributeCount), func(b *testing.B) {
			for b.Loop() {
				envelope.DeserializeCbor(cborBytes)
			}
			b.ReportMetric(float64(len(cborBytes)), "envelope_bytes/op")
			b.ReportMetric(float64(rawSize), "raw_bytes/op")
		})
	}
}
