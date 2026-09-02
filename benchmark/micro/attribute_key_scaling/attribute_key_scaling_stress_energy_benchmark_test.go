package attribute_key_scaling

import (
	"benchmark/cryptography/cpabe"
	"benchmark/cryptography/rsa"
	"benchmark/micro/attribute_key_scaling/shared"
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

func BenchmarkAttributeKeyScalingEnergyEncrypt(benchmark *testing.B) {

	config := shared.NewAttributeKeyScalingConfig()

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

	// Scenario 3: Scaling key size in RSA
	for _, rsaKeyBits := range config.RSAKeyBits {

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			publicKey := shared.LoadRSAKeysFromInMemoryCache(rsaKeyBits, 1)[0]

			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				publicKey.Encrypt(symmetricKey)
			}

			// Actually measure this region
			for b.Loop() {
				publicKey.Encrypt(symmetricKey)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				publicKey.Encrypt(symmetricKey)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func BenchmarkAttributeKeyScalingEnergyDecrypt(benchmark *testing.B) {

	config := shared.NewAttributeKeyScalingConfig()

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

	// Scenario 2: Scaling key size in RSA
	for _, rsaKeyBits := range config.RSAKeyBits {

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			privateKey := shared.LoadRSAKeysFromInMemoryCache(rsaKeyBits, 1)[0]

			symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

			asymmetricCiphertext := privateKey.Encrypt(symmetricKey)

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
}

func BenchmarkAttributeKeyScalingEnergyKeyGen(benchmark *testing.B) {

	config := shared.NewAttributeKeyScalingConfig()

	// RSA key generation only
	for _, rsaKeyBits := range config.RSAKeyBits {

		benchmark.Run(fmt.Sprintf("RSAKeyBits/%d", rsaKeyBits), func(b *testing.B) {

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				_ = rsa.NewRSA(rsaKeyBits)
			}

			// Actually measure this region
			for b.Loop() {
				_ = rsa.NewRSA(rsaKeyBits)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				_ = rsa.NewRSA(rsaKeyBits)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}
