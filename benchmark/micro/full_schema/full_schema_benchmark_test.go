package full_schema

import (
	"fmt"
	"testing"
	"thesis/benchmark/cryptography/aes"
	"thesis/benchmark/cryptography/ascon"
	"thesis/benchmark/cryptography/cpabe"
	"thesis/benchmark/cryptography/rsa"
	"thesis/benchmark/micro/full_schema/shared"
	"thesis/benchmark/thermal"
	"thesis/benchmark/utility"
	"thesis/internal/envelope"
	"thesis/internal/serialization"
)

func BenchmarkFullSchemaEncrypt(benchmark *testing.B) {

	config := shared.LoadFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	// Standard package: PSK + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKStandard/%dB", payloadSize), func(b *testing.B) {

			cipher := aes.NewAES(
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			serializedEnvelope, _ := jsonSerializer.Serialize(envelope.Envelope{
				Nonce:               make([]byte, cipher.NonceSize()),
				SymmetricCiphertext: make([]byte, payloadSize+cipher.Overhead()),
			})
			envelopeSize := len(serializedEnvelope)

			b.SetBytes(int64(payloadSize))

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				jsonSerializer.Serialize(envelope.Envelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(envelopeSize), "serialized_bytes")

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

			cipher := aes.NewAES(
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			)

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			asymmetricCiphertextSize := len(
				rsaScheme.Encrypt(
					utility.GenerateRandomBytes(config.SymmetricKeySize),
				),
			)

			serializedEnvelope, _ := jsonSerializer.Serialize(envelope.Envelope{
				AsymmetricCiphertext: make([]byte, asymmetricCiphertextSize),
				Nonce:                make([]byte, cipher.NonceSize()),
				SymmetricCiphertext:  make([]byte, payloadSize+cipher.Overhead()),
			})
			envelopeSize := len(serializedEnvelope)

			b.SetBytes(int64(payloadSize))

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				jsonSerializer.Serialize(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(envelopeSize), "serialized_bytes")

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

			authority := cpabe.NewCPABEAuthority()

			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(
				config.AttributeCount,
			)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			cipher := aes.NewAES(
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			)

			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			asymmetricCiphertextSize := len(
				authority.Encrypt(
					abePolicy,
					utility.GenerateRandomBytes(config.SymmetricKeySize),
				),
			)

			serializedEnvelope, _ := jsonSerializer.Serialize(envelope.Envelope{
				AsymmetricCiphertext: make([]byte, asymmetricCiphertextSize),
				Nonce:                make([]byte, cipher.NonceSize()),
				SymmetricCiphertext:  make([]byte, payloadSize+cipher.Overhead()),
			})
			envelopeSize := len(serializedEnvelope)

			b.SetBytes(int64(payloadSize))

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)
				symmetricCiphertext := messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				jsonSerializer.Serialize(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(envelopeSize), "serialized_bytes")

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

			// Instantiate ASCON cipher with the pre-shared key
			cipher := ascon.NewASCON(
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			)

			// Construct plaintext for given payload size
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			// Serialized size is fixed for this benchmark case, so measure once
			// outside the timed loop
			serializedEnvelope, _ := cborSerializer.Serialize(envelope.Envelope{
				Nonce:               make([]byte, cipher.NonceSize()),
				SymmetricCiphertext: make([]byte, payloadSize+cipher.Overhead()),
			})
			envelopeSize := len(serializedEnvelope)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			// A realistic implementation of PSK necessitates a fresh nonce per message
			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				cborSerializer.Serialize(envelope.Envelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(envelopeSize), "serialized_bytes")

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

			// Instantiate RSA cipher
			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			// Construct plaintext for given payload size
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Instantiate ASCON once outside timed loop to obtain its fixed sizes
			cipher := ascon.NewASCON(
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			// Calculate fixed RSA wrapped-key size
			asymmetricCiphertextSize := len(
				rsaScheme.Encrypt(
					utility.GenerateRandomBytes(config.SymmetricKeySize),
				),
			)

			// Serialized size is fixed for this benchmark case, so measure once
			// outside the timed loop
			serializedEnvelope, _ := cborSerializer.Serialize(envelope.Envelope{
				AsymmetricCiphertext: make([]byte, asymmetricCiphertextSize),
				Nonce:                make([]byte, cipher.NonceSize()),
				SymmetricCiphertext:  make([]byte, payloadSize+cipher.Overhead()),
			})
			envelopeSize := len(serializedEnvelope)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			// A realistic implementation of RSA + ASCON necessitates a fresh session key & nonce per message
			for b.Loop() {
				nonce := utility.GenerateRandomBytes(cipher.NonceSize())
				symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				cborSerializer.Serialize(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(envelopeSize), "serialized_bytes")

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

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Build policy for configured attribute count
			abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(
				config.AttributeCount,
			)

			// Construct plaintext for given payload size
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Instantiate ASCON once outside timed loop to obtain its fixed sizes
			cipher := ascon.NewASCON(
				utility.GenerateRandomBytes(config.SymmetricKeySize),
			)

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

			// Calculate fixed CP-ABE wrapped-key size
			asymmetricCiphertextSize := len(
				authority.Encrypt(
					abePolicy,
					utility.GenerateRandomBytes(config.SymmetricKeySize),
				),
			)

			// Serialized size is fixed for this benchmark case, so measure once
			// outside the timed loop
			serializedEnvelope, _ := cborSerializer.Serialize(envelope.Envelope{
				AsymmetricCiphertext: make([]byte, asymmetricCiphertextSize),
				Nonce:                make([]byte, cipher.NonceSize()),
				SymmetricCiphertext:  make([]byte, payloadSize+cipher.Overhead()),
			})
			envelopeSize := len(serializedEnvelope)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

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
				symmetricCiphertext := messageCipher.Seal(ciphertext[:0], nonce, plaintext, nil)

				cborSerializer.Serialize(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(envelopeSize), "serialized_bytes")

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

	// Standard package: PSK + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKStandard/%dB", payloadSize), func(b *testing.B) {

			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			cipher := aes.NewAES(symmetricKey)

			plaintext := utility.GenerateRandomBytes(payloadSize)

			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			serializedEnvelope, _ := jsonSerializer.Serialize(envelope.Envelope{
				Nonce:               nonce,
				SymmetricCiphertext: cipher.Seal(nil, nonce, plaintext, nil),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			b.SetBytes(int64(payloadSize))

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var env envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)

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
				SymmetricCiphertext:  cipher.Seal(nil, nonce, plaintext, nil),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			b.SetBytes(int64(payloadSize))

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var env envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := rsaScheme.Decrypt(env.AsymmetricCiphertext)

				if _, err := aes.NewAES(recoveredSymmetricKey).Open(
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

	// Standard package: CP-ABE + AES-GCM + JSON
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABEStandard/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.NewCPABEAuthority()

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
				SymmetricCiphertext:  cipher.Seal(nil, nonce, plaintext, nil),
			})

			decryptedPlaintext := make([]byte, 0, payloadSize)

			b.SetBytes(int64(payloadSize))

			thermal.WaitForCooldown()

			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var env envelope.Envelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)
				recoveredSymmetricKey := subscriberKey.Decrypt(
					env.AsymmetricCiphertext,
				)

				if _, err := aes.NewAES(recoveredSymmetricKey).Open(
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

	// Lightweight package: PSK + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKLightweight/%dB", payloadSize), func(b *testing.B) {

			// Generate pre-shared key
			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			// Instantiate ASCON cipher
			cipher := ascon.NewASCON(symmetricKey)

			// Construct plaintext for given payload size
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			// Create serialized envelope to measure the complete decryption pipeline
			serializedEnvelope, _ := cborSerializer.Serialize(envelope.Envelope{
				Nonce:               nonce,
				SymmetricCiphertext: cipher.Seal(nil, nonce, plaintext, nil),
			})

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			decryptedPlaintext := make([]byte, 0, payloadSize)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var env envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &env)

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

	// Lightweight package: RSA + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSALightweight/%dB", payloadSize), func(b *testing.B) {

			// Instantiate RSA cipher
			rsaScheme := rsa.NewRSA(config.RSAKeyBits)

			// Generate symmetric key
			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			// Instantiate ASCON cipher
			cipher := ascon.NewASCON(symmetricKey)

			// Construct plaintext for given payload size
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			// Create serialized envelope to measure the complete decryption pipeline
			serializedEnvelope, _ := cborSerializer.Serialize(envelope.Envelope{
				AsymmetricCiphertext: rsaScheme.Encrypt(symmetricKey),
				Nonce:                nonce,
				SymmetricCiphertext:  cipher.Seal(nil, nonce, plaintext, nil),
			})

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			decryptedPlaintext := make([]byte, 0, payloadSize)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var env envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &env)
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

	// Lightweight package: CP-ABE + ASCON + CBOR
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABELightweight/%dB", payloadSize), func(b *testing.B) {

			// Instantiate CP-ABE authority
			authority := cpabe.NewCPABEAuthority()

			// Build policy and attributes
			abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(
				config.AttributeCount,
			)

			// Issue subscriber private key
			subscriberKey := authority.IssuePrivateKey(abeAttributes)

			// Generate symmetric key
			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			// Instantiate ASCON cipher
			cipher := ascon.NewASCON(symmetricKey)

			// Construct plaintext for given payload size
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			// Create serialized envelope to measure the complete decryption pipeline
			serializedEnvelope, _ := cborSerializer.Serialize(envelope.Envelope{
				AsymmetricCiphertext: authority.Encrypt(abePolicy, symmetricKey),
				Nonce:                nonce,
				SymmetricCiphertext:  cipher.Seal(nil, nonce, plaintext, nil),
			})

			// Pre-allocate output destination buffer to avoid allocation inside timed loop
			decryptedPlaintext := make([]byte, 0, payloadSize)

			// Records the number of bytes processed in a single operation
			b.SetBytes(int64(payloadSize))

			// Let device cool off before starting timed loop, to avoid thermal throttling affecting results
			thermal.WaitForCooldown()

			// Start watching for thermal throttling, so it can be reported as a metric
			throttle := thermal.NewThrottleWatch()

			for b.Loop() {
				var env envelope.Envelope
				cborSerializer.Deserialize(serializedEnvelope, &env)
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
