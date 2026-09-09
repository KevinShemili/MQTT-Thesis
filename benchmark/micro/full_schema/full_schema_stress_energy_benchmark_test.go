package full_schema

import (
	"benchmark/cryptography/ascon"
	"benchmark/cryptography/cpabe"
	"benchmark/cryptography/rsa"
	"benchmark/envelope"
	"benchmark/micro/full_schema/shared"
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

func BenchmarkFullSchemaEnergyEncrypt(benchmark *testing.B) {

	config := shared.LoadFullSchemaConfig()

	// Scenario 1: PSK Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

			cipher := ascon.NewASCON(
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				envelope.SerializeCBOR(envelope.Envelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			// Actually measure this region
			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				envelope.SerializeCBOR(envelope.Envelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				envelope.SerializeCBOR(envelope.Envelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: RSA + ASCON Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSA/%dB", payloadSize), func(b *testing.B) {

			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			cipher := ascon.NewASCON(
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			)

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				envelope.SerializeCBOR(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			// Actually measure this region
			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				envelope.SerializeCBOR(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				envelope.SerializeCBOR(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 3: CP-ABE + ASCON Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABE/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewCPABEAuthority()

			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(
				config.AttributeCount,
			)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			cipher := ascon.NewASCON(
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			)

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)
				symmetricCiphertext := messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				envelope.SerializeCBOR(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			// Actually measure this region
			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)
				symmetricCiphertext := messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				envelope.SerializeCBOR(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)
				symmetricCiphertext := messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				envelope.SerializeCBOR(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func BenchmarkFullSchemaEnergyDecrypt(benchmark *testing.B) {

	config := shared.LoadFullSchemaConfig()

	// Scenario 1: PSK Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := ascon.NewASCON(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope := envelope.SerializeCBOR(envelope.Envelope{
				Nonce:               nonce,
				SymmetricCiphertext: cipher.Seal(nil, nonce, plaintext, nil),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				env := envelope.DeserializeCBOR(serializedEnvelope)

				if _, err := cipher.Open(
					decryptedPlaintext[:0],
					env.Nonce,
					env.SymmetricCiphertext,
					nil,
				); err != nil {
					panic(err)
				}
			}

			// Actually measure this region
			for b.Loop() {
				env := envelope.DeserializeCBOR(serializedEnvelope)

				if _, err := cipher.Open(
					decryptedPlaintext[:0],
					env.Nonce,
					env.SymmetricCiphertext,
					nil,
				); err != nil {
					panic(err)
				}
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				env := envelope.DeserializeCBOR(serializedEnvelope)

				if _, err := cipher.Open(
					decryptedPlaintext[:0],
					env.Nonce,
					env.SymmetricCiphertext,
					nil,
				); err != nil {
					panic(err)
				}
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 2: RSA + ASCON Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSA/%dB", payloadSize), func(b *testing.B) {

			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := ascon.NewASCON(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope := envelope.SerializeCBOR(envelope.Envelope{
				AsymmetricCiphertext: rsaScheme.Encrypt(symmetricKey),
				Nonce:                nonce,
				SymmetricCiphertext:  cipher.Seal(nil, nonce, plaintext, nil),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				env := envelope.DeserializeCBOR(serializedEnvelope)
				recoveredSymmetricKey := rsaScheme.Decrypt(env.AsymmetricCiphertext)

				if _, err := ascon.NewASCON(recoveredSymmetricKey).Open(
					decryptedPlaintext[:0],
					env.Nonce,
					env.SymmetricCiphertext,
					nil,
				); err != nil {
					panic(err)
				}
			}

			// Actually measure this region
			for b.Loop() {
				env := envelope.DeserializeCBOR(serializedEnvelope)
				recoveredSymmetricKey := rsaScheme.Decrypt(env.AsymmetricCiphertext)

				if _, err := ascon.NewASCON(recoveredSymmetricKey).Open(
					decryptedPlaintext[:0],
					env.Nonce,
					env.SymmetricCiphertext,
					nil,
				); err != nil {
					panic(err)
				}
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				env := envelope.DeserializeCBOR(serializedEnvelope)
				recoveredSymmetricKey := rsaScheme.Decrypt(env.AsymmetricCiphertext)

				if _, err := ascon.NewASCON(recoveredSymmetricKey).Open(
					decryptedPlaintext[:0],
					env.Nonce,
					env.SymmetricCiphertext,
					nil,
				); err != nil {
					panic(err)
				}
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Scenario 3: CP-ABE + ASCON Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABE/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewCPABEAuthority()

			abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(
				config.AttributeCount,
			)

			subscriberKey := authority.IssuePrivateKey(abeAttributes)

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := ascon.NewASCON(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope := envelope.SerializeCBOR(envelope.Envelope{
				AsymmetricCiphertext: authority.Encrypt(abePolicy, symmetricKey),
				Nonce:                nonce,
				SymmetricCiphertext:  cipher.Seal(nil, nonce, plaintext, nil),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				env := envelope.DeserializeCBOR(serializedEnvelope)
				recoveredSymmetricKey := subscriberKey.Decrypt(
					env.AsymmetricCiphertext,
				)

				if _, err := ascon.NewASCON(recoveredSymmetricKey).Open(
					decryptedPlaintext[:0],
					env.Nonce,
					env.SymmetricCiphertext,
					nil,
				); err != nil {
					panic(err)
				}
			}

			// Actually measure this region
			for b.Loop() {
				env := envelope.DeserializeCBOR(serializedEnvelope)
				recoveredSymmetricKey := subscriberKey.Decrypt(
					env.AsymmetricCiphertext,
				)

				if _, err := ascon.NewASCON(recoveredSymmetricKey).Open(
					decryptedPlaintext[:0],
					env.Nonce,
					env.SymmetricCiphertext,
					nil,
				); err != nil {
					panic(err)
				}
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				env := envelope.DeserializeCBOR(serializedEnvelope)
				recoveredSymmetricKey := subscriberKey.Decrypt(
					env.AsymmetricCiphertext,
				)

				if _, err := ascon.NewASCON(recoveredSymmetricKey).Open(
					decryptedPlaintext[:0],
					env.Nonce,
					env.SymmetricCiphertext,
					nil,
				); err != nil {
					panic(err)
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
