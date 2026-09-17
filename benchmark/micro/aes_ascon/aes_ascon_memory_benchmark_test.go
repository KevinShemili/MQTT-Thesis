package aes_ascon

import (
	"fmt"
	"runtime"
	"runtime/debug"
	"testing"
	"thesis/benchmark/cache"
	"thesis/benchmark/cryptography/aes"
	"thesis/benchmark/cryptography/ascon"
	"thesis/benchmark/memory"
	"thesis/benchmark/micro/aes_ascon/shared"
	"thesis/benchmark/thermal"
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

			cipher := aes.NewAES(cache.LoadFile(cache.CreateAESKeyFileName(config.AESKeySize)))
			plaintext := cache.LoadFile(cache.CreateAESASCONPlaintextFileName(payloadSize))
			nonce := cache.LoadFile(cache.CreateAESGCMNonceFileName())

			thermal.WaitForCooldown()

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				cipher.Seal(nil, nonce, plaintext, nil)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {

			cipher := ascon.NewASCON(cache.LoadFile(cache.CreateASCONKeyFileName(config.ASCONKeySize)))
			plaintext := cache.LoadFile(cache.CreateAESASCONPlaintextFileName(payloadSize))
			nonce := cache.LoadFile(cache.CreateASCONNonceFileName())

			thermal.WaitForCooldown()

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				cipher.Seal(nil, nonce, plaintext, nil)
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

			cipher := aes.NewAES(cache.LoadFile(cache.CreateAESKeyFileName(config.AESKeySize)))
			ciphertext := cache.LoadFile(cache.CreateAESGCMCiphertextFileName(payloadSize))
			nonce := cache.LoadFile(cache.CreateAESGCMNonceFileName())

			thermal.WaitForCooldown()

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				cipher.Open(nil, nonce, ciphertext, nil)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("ASCON/%dB", payloadSize), func(b *testing.B) {

			cipher := ascon.NewASCON(cache.LoadFile(cache.CreateASCONKeyFileName(config.ASCONKeySize)))
			ciphertext := cache.LoadFile(cache.CreateASCONCiphertextFileName(payloadSize))
			nonce := cache.LoadFile(cache.CreateASCONNonceFileName())

			thermal.WaitForCooldown()

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				cipher.Open(nil, nonce, ciphertext, nil)
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
