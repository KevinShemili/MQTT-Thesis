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
)

func BenchmarkFullSchemaEncrypt(benchmark *testing.B) {

	config := shared.LoadFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	// PSK + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKStandard/%dB", payloadSize), func(b *testing.B) {

			cipher := aes.NewAES(utility.GenerateRandomBytes(config.SymmetricKeySize))

			plaintext := utility.GenerateRandomBytes(payloadSize)

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			serializedEnvelope, _ := jsonSerializer.Serialize(
				envelope.AsymmetricEnvelope{
					Nonce:               make([]byte, cipher.NonceSize()),
					SymmetricCiphertext: make([]byte, payloadSize+cipher.Overhead()),
				})
			serializedSize := len(serializedEnvelope)

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Encrypt(ciphertext[:0], nonce, plaintext)

				jsonSerializer.Serialize(
					envelope.AsymmetricEnvelope{
						Nonce:               nonce,
						SymmetricCiphertext: symmetricCiphertext,
					})
			}

			b.ReportMetric(float64(serializedSize), "serialized_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// RSA + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSAStandard/%dB", payloadSize), func(b *testing.B) {

			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			cipher := aes.NewAES(utility.GenerateRandomBytes(config.SymmetricKeySize))

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			asymmetricCiphertextSize := len(rsaScheme.Encrypt(
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			))

			serializedEnvelope, _ := jsonSerializer.Serialize(
				envelope.AsymmetricEnvelope{
					AsymmetricCiphertext: make([]byte, asymmetricCiphertextSize),
					Nonce:                make([]byte, cipher.NonceSize()),
					SymmetricCiphertext:  make([]byte, payloadSize+cipher.Overhead()),
				})
			serializedSize := len(serializedEnvelope)

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(serializedSize), "serialized_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// CP-ABE + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABEStandard/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewAuthority()

			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			cipher := aes.NewAES(utility.GenerateRandomBytes(config.SymmetricKeySize))

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			asymmetricCiphertextSize := len(authority.Encrypt(
				abePolicy,
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			))

			serializedEnvelope, _ := jsonSerializer.Serialize(
				envelope.AsymmetricEnvelope{
					AsymmetricCiphertext: make([]byte, asymmetricCiphertextSize),
					Nonce:                make([]byte, cipher.NonceSize()),
					SymmetricCiphertext:  make([]byte, payloadSize+cipher.Overhead()),
				})
			serializedSize := len(serializedEnvelope)

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(serializedSize), "serialized_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// PSK + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKLightweight/%dB", payloadSize), func(b *testing.B) {

			cipher := ascon.NewASCON(utility.GenerateRandomBytes(config.SymmetricKeySize))

			plaintext := utility.GenerateRandomBytes(payloadSize)

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			serializedEnvelope, _ := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
				Nonce:               make([]byte, cipher.NonceSize()),
				SymmetricCiphertext: make([]byte, payloadSize+cipher.Overhead()),
			})
			serializedSize := len(serializedEnvelope)

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Encrypt(ciphertext[:0], nonce, plaintext)

				cborSerializer.Serialize(envelope.AsymmetricEnvelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(serializedSize), "serialized_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// RSA + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSALightweight/%dB", payloadSize), func(b *testing.B) {

			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			cipher := ascon.NewASCON(utility.GenerateRandomBytes(config.SymmetricKeySize))

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			asymmetricCiphertextSize := len(rsaScheme.Encrypt(
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			))

			serializedEnvelope, _ := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
				AsymmetricCiphertext: make([]byte, asymmetricCiphertextSize),
				Nonce:                make([]byte, cipher.NonceSize()),
				SymmetricCiphertext:  make([]byte, payloadSize+cipher.Overhead()),
			})
			serializedSize := len(serializedEnvelope)

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				cborSerializer.Serialize(envelope.AsymmetricEnvelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(serializedSize), "serialized_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// CP-ABE + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABELightweight/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewAuthority()

			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			cipher := ascon.NewASCON(utility.GenerateRandomBytes(config.SymmetricKeySize))

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			asymmetricCiphertextSize := len(authority.Encrypt(
				abePolicy,
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			))

			serializedEnvelope, _ := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
				AsymmetricCiphertext: make([]byte, asymmetricCiphertextSize),
				Nonce:                make([]byte, cipher.NonceSize()),
				SymmetricCiphertext:  make([]byte, payloadSize+cipher.Overhead()),
			})
			serializedSize := len(serializedEnvelope)

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			// A realistic implementation of CP-ABE + ASCON necessitates a fresh session key & nonce per message
			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

				cborSerializer.Serialize(envelope.AsymmetricEnvelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(serializedSize), "serialized_bytes")

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}
}

func BenchmarkFullSchemaDecrypt(benchmark *testing.B) {

	config := shared.LoadFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	// PSK + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKStandard/%dB", payloadSize), func(b *testing.B) {

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := aes.NewAES(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
				Nonce:               nonce,
				SymmetricCiphertext: cipher.Encrypt(nil, nonce, plaintext),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var env envelope.AsymmetricEnvelope
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

	// RSA + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSAStandard/%dB", payloadSize), func(b *testing.B) {

			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := aes.NewAES(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
				AsymmetricCiphertext: rsaScheme.Encrypt(symmetricKey),
				Nonce:                nonce,
				SymmetricCiphertext:  cipher.Encrypt(nil, nonce, plaintext),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var env envelope.AsymmetricEnvelope
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

	// CP-ABE + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABEStandard/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewAuthority()

			abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)

			subscriberKey := authority.IssuePrivateKey(abeAttributes)

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := aes.NewAES(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
				AsymmetricCiphertext: authority.Encrypt(abePolicy, symmetricKey),
				Nonce:                nonce,
				SymmetricCiphertext:  cipher.Encrypt(nil, nonce, plaintext),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var env envelope.AsymmetricEnvelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := subscriberKey.Decrypt(
					env.AsymmetricCiphertext,
				)

				aes.NewAES(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
			}

			if throttle.IsThrottled() {
				b.ReportMetric(1, "throttled")
			} else {
				b.ReportMetric(0, "throttled")
			}
		})
	}

	// PSK + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKLightweight/%dB", payloadSize), func(b *testing.B) {

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := ascon.NewASCON(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
				Nonce:               nonce,
				SymmetricCiphertext: cipher.Encrypt(nil, nonce, plaintext),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var env envelope.AsymmetricEnvelope
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

	// RSA + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSALightweight/%dB", payloadSize), func(b *testing.B) {

			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := ascon.NewASCON(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
				AsymmetricCiphertext: rsaScheme.Encrypt(symmetricKey),
				Nonce:                nonce,
				SymmetricCiphertext:  cipher.Encrypt(nil, nonce, plaintext),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var env envelope.AsymmetricEnvelope
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

	// CP-ABE + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABELightweight/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewAuthority()

			abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)

			subscriberKey := authority.IssuePrivateKey(abeAttributes)

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := ascon.NewASCON(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
				AsymmetricCiphertext: authority.Encrypt(abePolicy, symmetricKey),
				Nonce:                nonce,
				SymmetricCiphertext:  cipher.Encrypt(nil, nonce, plaintext),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var env envelope.AsymmetricEnvelope
				cborSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := subscriberKey.Decrypt(
					env.AsymmetricCiphertext,
				)

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
