package cpabe_rsa

import (
	"fmt"
	"runtime"
	"runtime/debug"
	"testing"
	"thesis/benchmark/cache"
	"thesis/benchmark/cryptography/cpabe"
	"thesis/benchmark/cryptography/rsa"
	"thesis/benchmark/memory"
	"thesis/benchmark/micro/cpabe_rsa/shared"
	"thesis/benchmark/thermal"
)

// Peak memory is a property of a whole process rather than of a loop, so these
// cases are driven one sample per process with -test.benchtime=1x
//
// No benchmark fixture is generated, every requisite is restored from the cache that
// CP-ABE/RSA provisioner built in an earlier process
func BenchmarkCPABERSAMemoryEncrypt(benchmark *testing.B) {

	config := shared.NewCPABERSAConfig()

	// Scenario 1: Measure how memory changes as policy grows
	for _, attributeCount := range config.AttributeCounts {

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {

			// Load from cache:
			// 1. Public Key
			// 2. Policy
			// 3. AES Symmetric Key
			asymmetricPublicKey := cpabe.UnmarshalCPABEPublicKey(cache.LoadFile(cache.CPABEPublicKeyFileName))
			abePolicy := cpabe.ParseCPABEPolicy(string(cache.LoadFile(cache.CreateCPABEPolicyFileName(attributeCount))))
			symmetricKey := cache.LoadFile(cache.CreateAESKeyFileName(config.AESKeySize))

			thermal.WaitForCooldown()

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				asymmetricPublicKey.Encrypt(abePolicy, symmetricKey)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	// Scenario 2: Measure how memory changes as one publisher encrypts AES key once for every subscriber
	for _, subscriberCount := range config.SubscriberCounts {

		benchmark.Run(fmt.Sprintf("RSASubscribers/%d", subscriberCount), func(b *testing.B) {

			// Load from cache:
			// 1. Each subscriber's public key
			// 2. AES Symmetric Key
			publicKeySlice := loadIndividualRSAPublicKeys(config.FixedRSAKeyBits, subscriberCount)
			symmetricKey := cache.LoadFile(cache.CreateAESKeyFileName(config.AESKeySize))

			thermal.WaitForCooldown()

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				for index := range subscriberCount {
					publicKeySlice[index].Encrypt(symmetricKey)
				}
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

}

func BenchmarkCPABERSAMemoryDecrypt(benchmark *testing.B) {

	config := shared.NewCPABERSAConfig()

	// Scenario 1: Measure how memory changes as the policy grows
	for _, attributeCount := range config.AttributeCounts {

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {

			// Load from cache:
			// 1. Private key with attributes
			// 2. Ciphertext to decrypt
			asymmetricPrivateKey := cpabe.UnmarshalCPABEPrivateKey(cache.LoadFile(cache.CreateCPABEPrivateKeyFileName(attributeCount)))
			asymmetricCiphertext := cache.LoadFile(cache.CreateCPABECiphertextFileName(attributeCount))

			thermal.WaitForCooldown()

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				asymmetricPrivateKey.Decrypt(asymmetricCiphertext)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	// Fixed RSA-3072 decrypt reference. Subscriber count does not affect this operation.
	rsaKeyBits := config.FixedRSAKeyBits
	benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

		asymmetricPrivateKey := rsa.UnmarshalPrivateKey(
			cache.LoadFile(cache.CreateRSAPrivateKeyFileName(rsaKeyBits, 0)),
		)
		asymmetricCiphertext := cache.LoadFile(
			cache.CreateRSACiphertextFileName(rsaKeyBits, 0),
		)

		thermal.WaitForCooldown()

		isPrepared := preparePeakMemoryMeasurement()

		for b.Loop() {
			asymmetricPrivateKey.Decrypt(asymmetricCiphertext)
		}

		if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
			b.ReportMetric(peakBytes, "peak_rss_bytes")
		}
	})
}

// The resident cost of the runtime alone. Nothing is restored and nothing is performed,
// so what the watermark holds is the floor every case above was measured on top of
//
// The benchmark name retains the standard algorithm/parameter-value shape expected by the loader
func BenchmarkCPABERSAMemoryBaseline(benchmark *testing.B) {

	benchmark.Run("Runtime/0", func(b *testing.B) {

		// Keep cooldown in the baseline so any persistent RSS footprint it introduces is also present in the
		// baseline itself
		thermal.WaitForCooldown()

		// Resetting the watermark leaves it at the current resident size, so the reading
		// below is what the process holds before any fixture or operation touches it
		isPrepared := preparePeakMemoryMeasurement()

		// The measured case is a process that does nothing, so the loop does nothing
		for b.Loop() {
		}

		if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
			b.ReportMetric(peakBytes, "peak_rss_bytes")
		}
	})
}

func preparePeakMemoryMeasurement() bool {

	// Remove unused Go objects left behind by fixture loading
	runtime.GC()

	// Return unused Go memory to Linux so it does not remain part of the process footprint
	debug.FreeOSMemory()

	// Forget the previous process memory peak so the next VmHWM reflects this benchmark case
	flag := memory.ResetPeakResidentMemory()

	return flag
}

// Load the individual public keys of all subscribers
func loadIndividualRSAPublicKeys(rsaKeyBits int, requiredCount int) []rsa.RSA {

	keySlice := make([]rsa.RSA, requiredCount)

	for index := range requiredCount {
		keySlice[index] = rsa.UnmarshalPublicKey(
			cache.LoadFile(cache.CreateRSAPublicKeyFileName(rsaKeyBits, index)),
		)
	}

	return keySlice
}
