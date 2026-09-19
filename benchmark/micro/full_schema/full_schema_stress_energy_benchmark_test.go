package full_schema

import (
	"fmt"
	"testing"
	"thesis/benchmark/micro/full_schema/shared"
	"thesis/benchmark/thermal"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
	"thesis/internal/envelope"
	"thesis/internal/serialization"
	"time"
)

var (
	warmupDuration = time.Duration(utility.ParseIntFromEnv("WARMUP_DURATION")) * time.Second
	tailDuration   = time.Duration(utility.ParseIntFromEnv("TAIL_DURATION")) * time.Second
)

func BenchmarkFullSchemaEnergyEncrypt(benchmark *testing.B) {

	config := shared.LoadFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	// Standard package: PSK + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKStandard/%dB", payloadSize), func(b *testing.B) {

			cipher := aes.NewAES(utility.GenerateRandomBytes(config.SymmetricKeySize))

			plaintext := utility.GenerateRandomBytes(payloadSize)

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Encrypt(ciphertext[:0], nonce, plaintext)

				jsonSerializer.Serialize(envelope.Envelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Encrypt(ciphertext[:0], nonce, plaintext)

				jsonSerializer.Serialize(envelope.Envelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Encrypt(ciphertext[:0], nonce, plaintext)

				jsonSerializer.Serialize(envelope.Envelope{
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

	// Standard package: RSA + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSAStandard/%dB", payloadSize), func(b *testing.B) {

			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			cipher := aes.NewAES(utility.GenerateRandomBytes(config.SymmetricKeySize))

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				jsonSerializer.Serialize(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				jsonSerializer.Serialize(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				jsonSerializer.Serialize(envelope.Envelope{
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

	// Standard package: CP-ABE + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABEStandard/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewAuthority()

			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			cipher := aes.NewAES(utility.GenerateRandomBytes(config.SymmetricKeySize))

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				jsonSerializer.Serialize(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				jsonSerializer.Serialize(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				jsonSerializer.Serialize(envelope.Envelope{
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

	// Lightweight package: PSK + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKLightweight/%dB", payloadSize), func(b *testing.B) {

			cipher := ascon.NewASCON(utility.GenerateRandomBytes(config.SymmetricKeySize))

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
				symmetricCiphertext := cipher.Encrypt(ciphertext[:0], nonce, plaintext)

				cborSerializer.Serialize(envelope.Envelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			// Actually measure this region
			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Encrypt(ciphertext[:0], nonce, plaintext)

				cborSerializer.Serialize(envelope.Envelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Encrypt(ciphertext[:0], nonce, plaintext)

				cborSerializer.Serialize(envelope.Envelope{
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

	// Lightweight package: RSA + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSALightweight/%dB", payloadSize), func(b *testing.B) {

			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			cipher := ascon.NewASCON(utility.GenerateRandomBytes(config.SymmetricKeySize))

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
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				cborSerializer.Serialize(envelope.Envelope{
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
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				cborSerializer.Serialize(envelope.Envelope{
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
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				cborSerializer.Serialize(envelope.Envelope{
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

	// Lightweight package: CP-ABE + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABELightweight/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewAuthority()

			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			cipher := ascon.NewASCON(utility.GenerateRandomBytes(config.SymmetricKeySize))

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
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				cborSerializer.Serialize(envelope.Envelope{
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
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				cborSerializer.Serialize(envelope.Envelope{
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
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				cborSerializer.Serialize(envelope.Envelope{
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
	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	// Standard package: PSK + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKStandard/%dB", payloadSize), func(b *testing.B) {

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := aes.NewAES(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := jsonSerializer.Serialize(envelope.Envelope{
				Nonce:               nonce,
				SymmetricCiphertext: cipher.Encrypt(nil, nonce, plaintext),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				var env envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)

				cipher.Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			for b.Loop() {
				var env envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)

				cipher.Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				var env envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)

				cipher.Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Standard package: RSA + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSAStandard/%dB", payloadSize), func(b *testing.B) {

			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := aes.NewAES(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := jsonSerializer.Serialize(envelope.Envelope{
				AsymmetricCiphertext: rsaScheme.Encrypt(symmetricKey),
				Nonce:                nonce,
				SymmetricCiphertext:  cipher.Encrypt(nil, nonce, plaintext),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				var env envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := rsaScheme.Decrypt(env.AsymmetricCiphertext)

				aes.NewAES(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			for b.Loop() {
				var env envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := rsaScheme.Decrypt(env.AsymmetricCiphertext)

				aes.NewAES(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				var env envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := rsaScheme.Decrypt(env.AsymmetricCiphertext)

				aes.NewAES(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Standard package: CP-ABE + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABEStandard/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewAuthority()

			abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(
				config.AttributeCount,
			)

			subscriberKey := authority.IssuePrivateKey(abeAttributes)

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := aes.NewAES(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := jsonSerializer.Serialize(envelope.Envelope{
				AsymmetricCiphertext: authority.Encrypt(abePolicy, symmetricKey),
				Nonce:                nonce,
				SymmetricCiphertext:  cipher.Encrypt(nil, nonce, plaintext),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				var env envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := subscriberKey.Decrypt(env.AsymmetricCiphertext)

				aes.NewAES(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			for b.Loop() {
				var env envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := subscriberKey.Decrypt(env.AsymmetricCiphertext)

				aes.NewAES(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				var env envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := subscriberKey.Decrypt(env.AsymmetricCiphertext)

				aes.NewAES(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Lightweight package: PSK + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKLightweight/%dB", payloadSize), func(b *testing.B) {

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := ascon.NewASCON(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := cborSerializer.Serialize(envelope.Envelope{
				Nonce:               nonce,
				SymmetricCiphertext: cipher.Encrypt(nil, nonce, plaintext),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				var env envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &env)

				cipher.Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			// Actually measure this region
			for b.Loop() {
				var env envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &env)

				cipher.Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				var env envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &env)

				cipher.Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Lightweight package: RSA + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSALightweight/%dB", payloadSize), func(b *testing.B) {

			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := ascon.NewASCON(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := cborSerializer.Serialize(envelope.Envelope{
				AsymmetricCiphertext: rsaScheme.Encrypt(symmetricKey),
				Nonce:                nonce,
				SymmetricCiphertext:  cipher.Encrypt(nil, nonce, plaintext),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			fmt.Println("ENRG-START")

			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				var env envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := rsaScheme.Decrypt(env.AsymmetricCiphertext)

				ascon.NewASCON(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			// Actually measure this region
			for b.Loop() {
				var env envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := rsaScheme.Decrypt(env.AsymmetricCiphertext)

				ascon.NewASCON(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				var env envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := rsaScheme.Decrypt(env.AsymmetricCiphertext)

				ascon.NewASCON(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// Lightweight package: CP-ABE + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABELightweight/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewAuthority()

			abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(
				config.AttributeCount,
			)

			subscriberKey := authority.IssuePrivateKey(abeAttributes)

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := ascon.NewASCON(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := cborSerializer.Serialize(envelope.Envelope{
				AsymmetricCiphertext: authority.Encrypt(abePolicy, symmetricKey),
				Nonce:                nonce,
				SymmetricCiphertext:  cipher.Encrypt(nil, nonce, plaintext),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()
			throttle := thermal.NewThrottleWatch()

			// Let orchestrator know that the workload has started
			fmt.Println("ENRG-START")

			// Warm up in plain loop as we do not want results recorded
			warmupDeadline := time.Now().Add(warmupDuration)
			for time.Now().Before(warmupDeadline) {
				var env envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := subscriberKey.Decrypt(env.AsymmetricCiphertext)

				ascon.NewASCON(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			// Actually measure this region
			for b.Loop() {
				var env envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := subscriberKey.Decrypt(env.AsymmetricCiphertext)

				ascon.NewASCON(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			// Keep same workload running after measured region
			tailDeadline := time.Now().Add(tailDuration)
			for time.Now().Before(tailDeadline) {
				var env envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := subscriberKey.Decrypt(env.AsymmetricCiphertext)

				ascon.NewASCON(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}
