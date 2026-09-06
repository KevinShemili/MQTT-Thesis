package full_schema

import (
	"benchmark/cache"
	"benchmark/cryptography/aes"
	"benchmark/cryptography/cpabe"
	"benchmark/cryptography/rsa"
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
// Every fixture is restored from the cache populated by cmd/provision in an
// earlier process so fixture generation does not pollute the measured peak.
func BenchmarkFullSchemaMemoryEncrypt(benchmark *testing.B) {

	config := shared.LoadFullSchemaConfig()

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

			cipher := aes.NewAES(cache.LoadFile(cache.CreateAESKeyFileName(config.AESKeySize)))
			plaintext := cache.LoadFile(cache.CreateFullSchemaPlaintextFileName(payloadSize))

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				cipher.Seal(nil, nonce, plaintext, nil)
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
			nonceSize := aes.NewAES(
				cache.LoadFile(cache.CreateAESKeyFileName(config.AESKeySize)),
			).NonceSize()

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(nonceSize)
				symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				publicKey.Encrypt(symmetricKey)
				messageCipher.Seal(nil, nonce, plaintext, nil)
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
			nonceSize := aes.NewAES(
				cache.LoadFile(cache.CreateAESKeyFileName(config.AESKeySize)),
			).NonceSize()

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(nonceSize)
				symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				publicKey.Encrypt(policy, symmetricKey)
				messageCipher.Seal(nil, nonce, plaintext, nil)
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

			cipher := aes.NewAES(cache.LoadFile(cache.CreateAESKeyFileName(config.AESKeySize)))
			ciphertext := cache.LoadFile(cache.CreateFullSchemaCiphertextFileName(payloadSize))
			nonce := cache.LoadFile(cache.CreateAESGCMNonceFileName())

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				cipher.Open(nil, nonce, ciphertext, nil)
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
			encryptedSymmetricKey := cache.LoadFile(
				cache.CreateRSACiphertextFileName(config.RSAKeyBits, 0),
			)
			ciphertext := cache.LoadFile(cache.CreateFullSchemaCiphertextFileName(payloadSize))
			nonce := cache.LoadFile(cache.CreateAESGCMNonceFileName())

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				symmetricKey := privateKey.Decrypt(encryptedSymmetricKey)
				aes.NewAES(symmetricKey).Open(nil, nonce, ciphertext, nil)
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
			encryptedSymmetricKey := cache.LoadFile(
				cache.CreateCPABECiphertextFileName(config.AttributeCount),
			)
			ciphertext := cache.LoadFile(cache.CreateFullSchemaCiphertextFileName(payloadSize))
			nonce := cache.LoadFile(cache.CreateAESGCMNonceFileName())

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				symmetricKey := privateKey.Decrypt(encryptedSymmetricKey)
				aes.NewAES(symmetricKey).Open(nil, nonce, ciphertext, nil)
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
