package benchmark

import (
	"crypto/cipher"
	"fmt"
	"project/cryptography"
	"project/utils"
	"testing"
)

var payloadList []int = []int{16, 64, 256, 1024, 4096, 16384, 65536}

func BenchmarkAESASCONEncrypt(benchmark *testing.B) {

	// Create ciphers
	var aesGcm cipher.AEAD = cryptography.NewAESGCM().AEAD
	var ascon cipher.AEAD = cryptography.NewASCON().AEAD

	// Create nonces
	var aesGcmNonce []byte = utils.GenerateRandomBytes(aesGcm.NonceSize())
	var asconNonce []byte = utils.GenerateRandomBytes(ascon.NonceSize())

	for i := range payloadList {

		var payloadSize int = payloadList[i]

		// Create plaintext based on payload size
		var plaintext []byte = utils.GenerateRandomBytes(payloadSize)

		// Pre-allocate output buffers, to avoid allocation inside loop
		var aesGcmBuffer []byte = make([]byte, 0, payloadSize+aesGcm.Overhead())
		var asconBuffer []byte = make([]byte, 0, payloadSize+ascon.Overhead())

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {
			// Report bytes per operation so the framework can compute MB/s
			b.SetBytes(int64(payloadSize))
			for b.Loop() {
				aesGcm.Seal(aesGcmBuffer[:0], aesGcmNonce, plaintext, nil)
			}

			b.ReportMetric(float64(aesGcm.Overhead()+aesGcm.NonceSize()), "overhead_bytes/op")
		})

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {
			b.SetBytes(int64(payloadSize))

			for b.Loop() {
				ascon.Seal(asconBuffer[:0], asconNonce, plaintext, nil)
			}

			b.ReportMetric(float64(ascon.Overhead()+ascon.NonceSize()), "overhead_bytes/op")
		})
	}
}

func BenchmarkAESASCONDecrypt(benchmark *testing.B) {

	var aesGcm cipher.AEAD = cryptography.NewAESGCM().AEAD
	var ascon cipher.AEAD = cryptography.NewASCON().AEAD

	var aesGcmNonce []byte = utils.GenerateRandomBytes(aesGcm.NonceSize())
	var asconNonce []byte = utils.GenerateRandomBytes(ascon.NonceSize())

	for i := range payloadList {
		var payloadSize int = payloadList[i]

		var plaintext []byte = utils.GenerateRandomBytes(payloadSize)

		// Calculate ciphertext
		var aesGcmCiphertext []byte = aesGcm.Seal(nil, aesGcmNonce, plaintext, nil)
		var asconCiphertext []byte = ascon.Seal(nil, asconNonce, plaintext, nil)

		// Pre-allocate output buffers
		var aesGcmBuffer []byte = make([]byte, 0, payloadSize)
		var asconBuffer []byte = make([]byte, 0, payloadSize)

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {
			b.SetBytes(int64(payloadSize))

			for b.Loop() {
				aesGcm.Open(aesGcmBuffer[:0], aesGcmNonce, aesGcmCiphertext, nil)
			}

			b.ReportMetric(float64(aesGcm.Overhead()+aesGcm.NonceSize()), "overhead_bytes/op")
		})

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {
			b.SetBytes(int64(payloadSize))

			for b.Loop() {
				ascon.Open(asconBuffer[:0], asconNonce, asconCiphertext, nil)
			}

			b.ReportMetric(float64(ascon.Overhead()+ascon.NonceSize()), "overhead_bytes/op")
		})
	}
}
