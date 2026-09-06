package cpabe_rsa

import (
	"benchmark/cryptography/cpabe"
	"benchmark/micro/cpabe_rsa/shared"
	"benchmark/thermal"
	"benchmark/utility"
	"fmt"
	"testing"
	"time"
)

var (
	warmupDuration = time.Duration(utility.ParseIntFromEnv("WARMUP_DURATION")) * time.Second
	tailDuration   = time.Duration(utility.ParseIntFromEnv("TAIL_DURATION")) * time.Second
)

func BenchmarkCPABERSAEnergyEncrypt(benchmark *testing.B) {

	config := shared.NewCPABERSAConfig()

	// Scenario 1: Scaling attribute count in CP-ABE
	for _, attributeCount := range config.AttributeCounts {

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {

			authority := cpabe.NewCPABEAuthority()

			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				authority.Encrypt(abePolicy, symmetricKey)
			}

			// Actually measure this region
			for b.Loop() {
				authority.Encrypt(abePolicy, symmetricKey)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				authority.Encrypt(abePolicy, symmetricKey)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: Scaling subscriber count in RSA
	for _, subscriberCount := range config.SubscriberCounts {

		benchmark.Run(fmt.Sprintf("RSASubscribers/%d", subscriberCount), func(b *testing.B) {

			publicKeySlice := shared.LoadRSAKeysFromInMemoryCache(
				config.FixedRSAKeyBits,
				subscriberCount,
			)

			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				for index := range subscriberCount {
					publicKeySlice[index].Encrypt(symmetricKey)
				}
			}

			// Actually measure this region
			for b.Loop() {
				for index := range subscriberCount {
					publicKeySlice[index].Encrypt(symmetricKey)
				}
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				for index := range subscriberCount {
					publicKeySlice[index].Encrypt(symmetricKey)
				}
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

}

func BenchmarkCPABERSAEnergyDecrypt(benchmark *testing.B) {

	config := shared.NewCPABERSAConfig()

	// Scenario 1: Scaling attribute count in CP-ABE
	for _, attributeCount := range config.AttributeCounts {

		benchmark.Run(fmt.Sprintf("CPABEAttributes/%d", attributeCount), func(b *testing.B) {

			authority := cpabe.NewCPABEAuthority()

			abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(
				attributeCount,
			)

			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			privateKey := authority.IssuePrivateKey(abeAttributes)

			asymmetricCiphertext := authority.Encrypt(
				abePolicy,
				symmetricKey,
			)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				privateKey.Decrypt(asymmetricCiphertext)
			}

			// Actually measure this region
			for b.Loop() {
				privateKey.Decrypt(asymmetricCiphertext)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				privateKey.Decrypt(asymmetricCiphertext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Fixed RSA-3072 decrypt reference. Subscriber count does not affect this operation.
	rsaKeyBits := config.FixedRSAKeyBits
	benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

		privateKey := shared.LoadRSAKeysFromInMemoryCache(rsaKeyBits, 1)[0]
		symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
		asymmetricCiphertext := privateKey.Encrypt(symmetricKey)

		thermal.WaitForCooldown()
		throttle := thermal.NewThrottleWatch()

		fmt.Println("ENRG-START")

		warmupDeadline := time.Now().Add(warmupDuration)
		for time.Now().Before(warmupDeadline) {
			privateKey.Decrypt(asymmetricCiphertext)
		}

		for b.Loop() {
			privateKey.Decrypt(asymmetricCiphertext)
		}

		tailDeadline := time.Now().Add(tailDuration)
		for time.Now().Before(tailDeadline) {
			privateKey.Decrypt(asymmetricCiphertext)
		}

		if throttle.IsThrottled() {
			b.ReportMetric(1, "throttled")
		} else {
			b.ReportMetric(0, "throttled")
		}
	})
}
