package full_schema

import (
	"benchmark/cache"
	"benchmark/cryptography/ascon"
	"benchmark/cryptography/cpabe"
	"benchmark/cryptography/rsa"
	"benchmark/envelope"
	"benchmark/memory"
	"benchmark/micro/full_schema/shared"
	"benchmark/thermal"
	"benchmark/utility"
	"fmt"
	"runtime"
	"runtime/debug"
	"testing"
)

// Peak memory is a property of a whole process rather than of a loop, so these
// cases are driven one sample per process with -test.benchtime=1x.
//
// Every fixture is restored from the cache populated by the Full Schema provisioner in an
// earlier process so fixture generation does not pollute the measured peak.
func BenchmarkFullSchemaMemoryEncrypt(benchmark *testing.B) {

	config := shared.LoadFullSchemaConfig()

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

			cipher := ascon.NewASCON(
				cache.LoadFile(cache.CreateASCONKeyFileName(config.SymmetricKeySize)),
			)
			plaintext := cache.LoadFile(cache.CreateFullSchemaPlaintextFileName(payloadSize))

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Seal(nil, nonce, plaintext, nil)

				envelope.SerializeCBOR(envelope.Envelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSA/%dB", payloadSize), func(b *testing.B) {

			publicKey := rsa.UnmarshalPublicKey(
				cache.LoadFile(cache.CreateRSAPublicKeyFileName(config.RSAKeyBits, 0)),
			)
			plaintext := cache.LoadFile(cache.CreateFullSchemaPlaintextFileName(payloadSize))
			nonceSize := ascon.NewASCON(
				cache.LoadFile(cache.CreateASCONKeyFileName(config.SymmetricKeySize)),
			).NonceSize()

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(nonceSize)
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := publicKey.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Seal(nil, nonce, plaintext, nil)

				envelope.SerializeCBOR(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABE/%dB", payloadSize), func(b *testing.B) {

			publicKey := cpabe.UnmarshalCPABEPublicKey(cache.LoadFile(cache.CPABEPublicKeyFileName))
			policy := cpabe.ParseCPABEPolicy(
				string(cache.LoadFile(cache.CreateCPABEPolicyFileName(config.AttributeCount))),
			)
			plaintext := cache.LoadFile(cache.CreateFullSchemaPlaintextFileName(payloadSize))
			nonceSize := ascon.NewASCON(
				cache.LoadFile(cache.CreateASCONKeyFileName(config.SymmetricKeySize)),
			).NonceSize()

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(nonceSize)
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := publicKey.Encrypt(policy, symmetricKey)
				symmetricCiphertext := messageCipher.Seal(nil, nonce, plaintext, nil)

				envelope.SerializeCBOR(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}
}

func BenchmarkFullSchemaMemoryDecrypt(benchmark *testing.B) {

	config := shared.LoadFullSchemaConfig()

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

			cipher := ascon.NewASCON(
				cache.LoadFile(cache.CreateASCONKeyFileName(config.SymmetricKeySize)),
			)
			serializedEnvelope := cache.LoadFile(
				cache.CreateFullSchemaEnvelopeFileName("psk", payloadSize),
			)

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				env := envelope.DeserializeCBOR(serializedEnvelope)
				if _, err := cipher.Open(nil, env.Nonce, env.SymmetricCiphertext, nil); err != nil {
					panic(err)
				}
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSA/%dB", payloadSize), func(b *testing.B) {

			privateKey := rsa.UnmarshalPrivateKey(
				cache.LoadFile(cache.CreateRSAPrivateKeyFileName(config.RSAKeyBits, 0)),
			)
			serializedEnvelope := cache.LoadFile(
				cache.CreateFullSchemaEnvelopeFileName("rsa", payloadSize),
			)

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				env := envelope.DeserializeCBOR(serializedEnvelope)
				symmetricKey := privateKey.Decrypt(env.AsymmetricCiphertext)
				if _, err := ascon.NewASCON(symmetricKey).Open(
					nil,
					env.Nonce,
					env.SymmetricCiphertext,
					nil,
				); err != nil {
					panic(err)
				}
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABE/%dB", payloadSize), func(b *testing.B) {

			privateKey := cpabe.UnmarshalCPABEPrivateKey(
				cache.LoadFile(cache.CreateCPABEPrivateKeyFileName(config.AttributeCount)),
			)
			serializedEnvelope := cache.LoadFile(
				cache.CreateFullSchemaEnvelopeFileName("cpabe", payloadSize),
			)

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				env := envelope.DeserializeCBOR(serializedEnvelope)
				symmetricKey := privateKey.Decrypt(env.AsymmetricCiphertext)
				if _, err := ascon.NewASCON(symmetricKey).Open(
					nil,
					env.Nonce,
					env.SymmetricCiphertext,
					nil,
				); err != nil {
					panic(err)
				}
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}
}

func BenchmarkFullSchemaMemoryBaseline(benchmark *testing.B) {

	benchmark.Run("Runtime/0B", func(b *testing.B) {

		thermal.WaitForCooldown()

		isPrepared := prepareFullSchemaPeakMemoryMeasurement()

		for b.Loop() {
		}

		if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
			b.ReportMetric(peakBytes, "peak_rss_bytes")
		}
	})
}

func prepareFullSchemaPeakMemoryMeasurement() bool {

	runtime.GC()
	debug.FreeOSMemory()

	return memory.ResetPeakResidentMemory()
}
