package benchmark

import (
	"fmt"
	"project/cache"
	"project/cryptography/cpabe"
	"project/cryptography/rsa"
	"project/utils"
	"runtime"
	"runtime/debug"
	"testing"
)

// Peak memory is a property of a whole process rather than of a loop, so these
// cases are driven one sample per process with -test.benchtime=1x
//
// No benchmark fixture is generated, every requisite is restored from the cache that
// cmd/provision built in an earlier process
func BenchmarkAttributeKeyScalingMemoryEncrypt(benchmark *testing.B) {

	config := loadAttributeKeyScalingConfig()

	// Scenario 1: Measure how memory changes as policy grows
	for _, attributeCount := range config.AttributeCountList {

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {

			// Load from cache:
			// 1. Public Key
			// 2. Policy
			// 3. AES Symmetric Key
			asymmetricPublicKey := cpabe.UnmarshalCPABEPublicKey(cache.LoadFile(cache.CPABEPublicKeyFileName))
			abePolicy := cpabe.ParseCPABEPolicy(string(cache.LoadFile(cache.CreateCPABEPolicyFileName(attributeCount))))
			symmetricKey := cache.LoadFile(cache.CreateAESKeyFileName(config.AESKeySize))

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				asymmetricPublicKey.Encrypt(abePolicy, symmetricKey)
			}

			if peakBytes, isAvailable := utils.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	// Scenario 2: Measure how memory changes as one publisher encrypts AES key once for every subscriber
	for _, subscriberCount := range config.SubscriberCountList {

		benchmark.Run(fmt.Sprintf("RSASubscribers/%d", subscriberCount), func(b *testing.B) {

			// Load from cache:
			// 1. Each subscriber's public key
			// 2. AES Symmetric Key
			publicKeySlice := loadIndividualRSAPublicKeys(config.FixedRSAKeyBits, subscriberCount)
			symmetricKey := cache.LoadFile(cache.CreateAESKeyFileName(config.AESKeySize))

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				for index := range subscriberCount {
					publicKeySlice[index].Encrypt(symmetricKey)
				}
			}

			if peakBytes, isAvailable := utils.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	// Scenario 3: Measure how memory changes as key size is varied
	for _, rsaKeyBits := range config.RSAKeySizeList {

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			// Load from cache:
			// 1. Load one RSA key with specified size, take index 0 from slice
			// 2. AES Symmetric Key
			asymmetricPublicKey := loadIndividualRSAPublicKeys(rsaKeyBits, 1)[0]
			symmetricKey := cache.LoadFile(cache.CreateAESKeyFileName(config.AESKeySize))

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				asymmetricPublicKey.Encrypt(symmetricKey)
			}

			if peakBytes, isAvailable := utils.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}
}

func BenchmarkAttributeKeyScalingMemoryDecrypt(benchmark *testing.B) {

	config := loadAttributeKeyScalingConfig()

	// Scenario 1: Measure how memory changes as as policy grows
	for _, attributeCount := range config.AttributeCountList {

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {

			// Load from cache:
			// 1. Private key with attributes
			// 2. Ciphertext to decrypt
			asymmetricPrivateKey := cpabe.UnmarshalCPABEPrivateKey(cache.LoadFile(cache.CreateCPABEPrivateKeyFileName(attributeCount)))
			asymmetricCiphertext := cache.LoadFile(cache.CreateCPABECiphertextFileName(attributeCount))

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				asymmetricPrivateKey.Decrypt(asymmetricCiphertext)
			}

			if peakBytes, isAvailable := utils.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	// Scenario 2: Measure how memory changes as key size is varied
	for _, rsaKeyBits := range config.RSAKeySizeList {

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			// Load from cache:
			// 1. Private key
			// 2. Ciphertext to decrypt
			asymmetricPrivateKey := rsa.UnmarshalPrivateKey(cache.LoadFile(cache.CreateRSAPrivateKeyFileName(rsaKeyBits, 0)))
			asymmetricCiphertext := cache.LoadFile(cache.CreateRSACiphertextFileName(rsaKeyBits, 0))

			isPrepared := preparePeakMemoryMeasurement()

			for b.Loop() {
				asymmetricPrivateKey.Decrypt(asymmetricCiphertext)
			}

			if peakBytes, isAvailable := utils.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}
}

func preparePeakMemoryMeasurement() bool {

	// Remove unused Go objects left behind by fixture loading
	runtime.GC()

	// Return unused Go memory to Linux so it does not remain part of the process footprint
	debug.FreeOSMemory()

	// Forget the previous process memory peak so the next VmHWM reflects this benchmark case
	flag := utils.ResetPeakResidentMemory()

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
