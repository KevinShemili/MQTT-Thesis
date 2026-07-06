package benchmark

import (
	"crypto/cipher"
	"fmt"
	"project/cryptography"
	"project/utils"
	"testing"
)

var payloadList []int = utils.ParseIntListFromEnv("AES_ASCON_PAYLOAD_SIZES")

func BenchmarkAESASCONEncrypt(benchmark *testing.B) {

	// Construct ciphers outside timed benchmarks
	var aesGcm cipher.AEAD = cryptography.NewAESGCM(utils.GenerateRandomBytes(utils.ParseIntFromEnv("AES_ASCON_KEY_SIZE"))).AEAD
	var ascon cipher.AEAD = cryptography.NewASCON(utils.GenerateRandomBytes(utils.ParseIntFromEnv("AES_ASCON_KEY_SIZE"))).AEAD

	// Construct nonces outside timed benchmarks
	// Normally reusing nonce is insecure, but acceptable here because ciphertexts are discarded benchmark artifacts
	var aesGcmNonce []byte = utils.GenerateRandomBytes(aesGcm.NonceSize())
	var asconNonce []byte = utils.GenerateRandomBytes(ascon.NonceSize())

	for index := range payloadList {

		var payloadSize int = payloadList[index]

		// Construct plaintext outside timed benchmarks
		var plaintext []byte = utils.GenerateRandomBytes(payloadSize)

		// Pre-allocate output destination buffers, to avoid allocation inside loop
		var aesGcmCiphertext []byte = make([]byte, 0, payloadSize+aesGcm.Overhead())
		var asconCiphertext []byte = make([]byte, 0, payloadSize+ascon.Overhead())

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {
			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			for b.Loop() {
				aesGcm.Seal(aesGcmCiphertext[:0], aesGcmNonce, plaintext, nil)
			}

			// Wire overhead = authentication tag size + nonce size
			b.ReportMetric(float64(aesGcm.Overhead()+aesGcm.NonceSize()), "wire_overhead_bytes/op")

			// Verify that benchmark measures cipher work, not any hidden memory allocations
			b.ReportAllocs()
		})

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {
			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			for b.Loop() {
				ascon.Seal(asconCiphertext[:0], asconNonce, plaintext, nil)
			}

			// Wire overhead = authentication tag size + nonce size
			b.ReportMetric(float64(ascon.Overhead()+ascon.NonceSize()), "wire_overhead_bytes/op")

			// Verify that benchmark measures cipher work, not any hidden memory allocations
			b.ReportAllocs()
		})
	}
}

func BenchmarkAESASCONDecrypt(benchmark *testing.B) {

	// Construct ciphers outside timed benchmarks
	var aesGcm cipher.AEAD = cryptography.NewAESGCM(utils.GenerateRandomBytes(utils.ParseIntFromEnv("AES_ASCON_KEY_SIZE"))).AEAD
	var ascon cipher.AEAD = cryptography.NewASCON(utils.GenerateRandomBytes(utils.ParseIntFromEnv("AES_ASCON_KEY_SIZE"))).AEAD

	// Construct nonces outside timed benchmarks
	var aesGcmNonce []byte = utils.GenerateRandomBytes(aesGcm.NonceSize())
	var asconNonce []byte = utils.GenerateRandomBytes(ascon.NonceSize())

	for i := range payloadList {
		var payloadSize int = payloadList[i]

		var plaintext []byte = utils.GenerateRandomBytes(payloadSize)

		// Calculate ciphertext
		var aesGcmCiphertext []byte = aesGcm.Seal(nil, aesGcmNonce, plaintext, nil)
		var asconCiphertext []byte = ascon.Seal(nil, asconNonce, plaintext, nil)

		// Pre-allocate output decryption buffers, to avoid allocation inside loop
		var aesGcmPlaintext []byte = make([]byte, 0, payloadSize)
		var asconPlaintext []byte = make([]byte, 0, payloadSize)

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {
			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			for b.Loop() {
				aesGcm.Open(aesGcmPlaintext[:0], aesGcmNonce, aesGcmCiphertext, nil)
			}

			// Wire overhead = authentication tag size + nonce size
			b.ReportMetric(float64(aesGcm.Overhead()+aesGcm.NonceSize()), "wire_overhead_bytes/op")

			// Verify that benchmark measures cipher work, not any hidden memory allocations
			b.ReportAllocs()
		})

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {
			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			for b.Loop() {
				ascon.Open(asconPlaintext[:0], asconNonce, asconCiphertext, nil)
			}

			// Wire overhead = authentication tag size + nonce size
			b.ReportMetric(float64(ascon.Overhead()+ascon.NonceSize()), "wire_overhead_bytes/op")

			// Verify that benchmark measures cipher work, not any hidden memory allocations
			b.ReportAllocs()
		})
	}
}
