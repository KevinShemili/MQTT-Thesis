package benchmark

import (
	"fmt"
	"project/cryptography"
	"project/fixture"
	"project/utils"
	"runtime"
	"runtime/debug"
	"testing"
)

// Peak resident memory is a property of a whole process rather than of a loop, so these
// cases are driven one sample per process with -test.benchtime=1x, and their output is
// kept in a file of its own because they are a different experiment from the timing one.
//
// Nothing here is generated. Every prerequisite is restored from the fixture cache that
// cmd/provision built in an earlier process, and a fixture that is missing panics: VmHWM
// is an absolute figure, not a delta, so a process that had generated a key would keep a
// larger resident baseline afterwards even once the heap had been handed back, and that
// baseline would be counted as part of the operation.
//
// Each closure restores only what the role it stands for would actually hold. A publisher
// holds public material, a subscriber holds its own private key. Holding anything else
// would measure what we chose to keep resident instead of what the operation costs

func BenchmarkAttributeKeyScalingMemoryEncrypt(benchmark *testing.B) {

	config := loadAttributeKeyScalingConfig()

	// Scenario 1: CP-ABE scaling attribute count
	for _, attributeCount := range config.AttributeCountList {

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {

			// Restored inside the closure so a filtered run loads only its own case, and
			// the master secret a publisher never holds stays out of the process
			publisherKey := cryptography.UnmarshalCPABEPublicKey(
				fixture.Load(fixture.CPABEPublicKey),
			)
			abePolicy := cryptography.ParseCPABEPolicy(
				string(fixture.Load(fixture.NameCPABEPolicy(attributeCount))),
			)
			aesKey := fixture.Load(fixture.NameAESKey(config.AESKeySize))

			// Restoring the fixtures dirtied a heap that is now garbage, and clear_refs
			// sets the watermark to the resident size of the moment, so those pages go
			// back to the kernel first or they are counted as part of the operation
			runtime.GC()
			debug.FreeOSMemory()

			reset := utils.ResetPeakResidentMemory()

			for b.Loop() {
				publisherKey.Encrypt(abePolicy, aesKey)
			}

			if peakBytes, available := utils.PeakResidentMemory(); reset && available {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	// Scenario 2: RSA scaling subscriber count
	for _, subscriberCount := range config.SubscriberCountList {

		benchmark.Run(fmt.Sprintf("RSASubscribers/%d", subscriberCount), func(b *testing.B) {

			// A publisher holds one public key per subscriber and no private key at all
			rsaSubscribers := rsaPublisherKeys(config.FixedRSAKeyBits, subscriberCount)
			aesKey := fixture.Load(fixture.NameAESKey(config.AESKeySize))

			runtime.GC()
			debug.FreeOSMemory()

			reset := utils.ResetPeakResidentMemory()

			// One publish is one operation, the same unit the timing benchmark measures
			for b.Loop() {
				for index := range subscriberCount {
					rsaSubscribers[index].Encrypt(aesKey)
				}
			}

			if peakBytes, available := utils.PeakResidentMemory(); reset && available {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	// Scenario 3: RSA scaling key size
	for _, rsaKeyBits := range config.RSAKeySizeList {

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			rsaScheme := rsaPublisherKeys(rsaKeyBits, 1)[0]
			aesKey := fixture.Load(fixture.NameAESKey(config.AESKeySize))

			runtime.GC()
			debug.FreeOSMemory()

			reset := utils.ResetPeakResidentMemory()

			for b.Loop() {
				rsaScheme.Encrypt(aesKey)
			}

			if peakBytes, available := utils.PeakResidentMemory(); reset && available {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}
}

func BenchmarkAttributeKeyScalingMemoryDecrypt(benchmark *testing.B) {

	config := loadAttributeKeyScalingConfig()

	// Scenario 1: CP-ABE scaling attribute count
	for _, attributeCount := range config.AttributeCountList {

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {

			subscriberKey := cryptography.UnmarshalCPABESubscriberKey(
				fixture.Load(fixture.NameCPABEAttributeKey(attributeCount)),
			)
			abeCiphertext := fixture.Load(
				fixture.NameCPABECiphertext(attributeCount, config.AESKeySize),
			)

			runtime.GC()
			debug.FreeOSMemory()

			reset := utils.ResetPeakResidentMemory()

			for b.Loop() {
				subscriberKey.Decrypt(abeCiphertext)
			}

			if peakBytes, available := utils.PeakResidentMemory(); reset && available {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	// Scenario 2: RSA scaling subscriber count
	// A subscriber holds its own key and unwraps its own copy, so the sweep point loads
	// exactly one key. Loading the publisher's whole pool here would draw a rising curve
	// caused by the fixture rather than by decryption
	for _, subscriberCount := range config.SubscriberCountList {

		benchmark.Run(fmt.Sprintf("RSASubscribers/%d", subscriberCount), func(b *testing.B) {

			decryptingIndex := subscriberCount - 1

			subscriber := rsaSubscriberKey(config.FixedRSAKeyBits, decryptingIndex)
			subscriberCiphertext := fixture.Load(
				fixture.NameRSACiphertext(config.FixedRSAKeyBits, decryptingIndex, config.AESKeySize),
			)

			runtime.GC()
			debug.FreeOSMemory()

			reset := utils.ResetPeakResidentMemory()

			for b.Loop() {
				subscriber.Decrypt(subscriberCiphertext)
			}

			if peakBytes, available := utils.PeakResidentMemory(); reset && available {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	// Scenario 3: RSA scaling key size
	for _, rsaKeyBits := range config.RSAKeySizeList {

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			rsa := rsaSubscriberKey(rsaKeyBits, 0)
			rsaCiphertext := fixture.Load(
				fixture.NameRSACiphertext(rsaKeyBits, 0, config.AESKeySize),
			)

			runtime.GC()
			debug.FreeOSMemory()

			reset := utils.ResetPeakResidentMemory()

			for b.Loop() {
				rsa.Decrypt(rsaCiphertext)
			}

			if peakBytes, available := utils.PeakResidentMemory(); reset && available {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}
}

// A measuring process never generates. A key that is not there means the provisioning
// step never ran, and a measurement taken anyway would be meaningless
func rsaPublisherKeys(rsaKeyBits int, requiredCount int) []cryptography.RSA {

	directory := fixture.RSAKeyDirectory(rsaKeyBits)
	keys := make([]cryptography.RSA, requiredCount)

	for index := range requiredCount {

		key, provisioned := cryptography.LoadRSAPublicKey(directory, index)
		if !provisioned {
			panic(fmt.Sprintf("rsa-%d public key %d was never provisioned", rsaKeyBits, index))
		}

		keys[index] = key
	}

	return keys
}

func rsaSubscriberKey(rsaKeyBits int, index int) cryptography.RSA {

	key, provisioned := cryptography.LoadRSAKey(fixture.RSAKeyDirectory(rsaKeyBits), index)
	if !provisioned {
		panic(fmt.Sprintf("rsa-%d private key %d was never provisioned", rsaKeyBits, index))
	}

	return key
}
