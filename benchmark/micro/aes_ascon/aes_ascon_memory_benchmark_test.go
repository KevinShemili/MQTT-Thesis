package aes_ascon

import (
	"fmt"
	"runtime"
	"runtime/debug"
	"testing"
	"thesis/benchmark/cache"
	"thesis/benchmark/memory"
	"thesis/benchmark/micro/aes_ascon/shared"
	"thesis/benchmark/thermal"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
)

// Peak memory is a property of a whole process rather than of a loop, so these
// cases are driven one sample per process with -test.benchtime=1x.
//
// Every fixture is restored from the cache populated by the AES/ASCON provisioner in an
// earlier process so fixture generation does not pollute the measured peak.
func BenchmarkAESASCONMemoryEncrypt(benchmark *testing.B) {

	config := shared.NewAESASCONConfig()

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {

			cipher := aes.NewAES(cache.Load(cache.AESKeyFileName))
			plaintext := cache.Load(cache.CreateAESASCONPlaintextFileName(payloadSize))
			nonce := cache.Load(cache.AESGCMNonceFileName)

			thermal.WaitForCooldown()

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				cipher.Encrypt(nil, nonce, plaintext)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {

			cipher := ascon.NewASCON(cache.Load(cache.ASCONKeyFileName))
			plaintext := cache.Load(cache.CreateAESASCONPlaintextFileName(payloadSize))
			nonce := cache.Load(cache.ASCONNonceFileName)

			thermal.WaitForCooldown()

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				cipher.Encrypt(nil, nonce, plaintext)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}
}

func BenchmarkAESASCONMemoryDecrypt(benchmark *testing.B) {

	config := shared.NewAESASCONConfig()

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("AES-GCM/%dB", payloadSize), func(b *testing.B) {

			cipher := aes.NewAES(cache.Load(cache.AESKeyFileName))
			ciphertext := cache.Load(cache.CreateAESGCMCiphertextFileName(payloadSize))
			nonce := cache.Load(cache.AESGCMNonceFileName)

			thermal.WaitForCooldown()

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				cipher.Decrypt(nil, nonce, ciphertext)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {

			cipher := ascon.NewASCON(cache.Load(cache.ASCONKeyFileName))
			ciphertext := cache.Load(cache.CreateASCONCiphertextFileName(payloadSize))
			nonce := cache.Load(cache.ASCONNonceFileName)

			thermal.WaitForCooldown()

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				cipher.Decrypt(nil, nonce, ciphertext)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}
}

// The runtime-only process establishes the floor that all memory cases include.
func BenchmarkAESASCONMemoryBaseline(benchmark *testing.B) {

	benchmark.Run("Runtime/0B", func(b *testing.B) {

		thermal.WaitForCooldown()

		isPrepared := preparePeakMemoryMeasurement()

		for b.Loop() {
		}

		if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
			b.ReportMetric(peakBytes, "peak_rss_bytes")
		}
	})
}

func preparePeakMemoryMeasurement() bool {

	runtime.GC()
	debug.FreeOSMemory()

	return memory.ResetPeakResidentMemory()
}
