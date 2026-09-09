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
)

func BenchmarkFullSchemaEncrypt(benchmark *testing.B) {

	config := shared.LoadFullSchemaConfig()

	// Scenario 1: PSK Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

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
			envelopeSize := len(envelope.SerializeCBOR(envelope.Envelope{
				Nonce:               make([]byte, cipher.NonceSize()),
				SymmetricCiphertext: make([]byte, payloadSize+cipher.Overhead()),
			}))

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

				envelope.SerializeCBOR(envelope.Envelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(envelopeSize), "envelope_bytes")

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
			envelopeSize := len(envelope.SerializeCBOR(envelope.Envelope{
				AsymmetricCiphertext: make([]byte, asymmetricCiphertextSize),
				Nonce:                make([]byte, cipher.NonceSize()),
				SymmetricCiphertext:  make([]byte, payloadSize+cipher.Overhead()),
			}))

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

				envelope.SerializeCBOR(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(envelopeSize), "envelope_bytes")

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
			envelopeSize := len(envelope.SerializeCBOR(envelope.Envelope{
				AsymmetricCiphertext: make([]byte, asymmetricCiphertextSize),
				Nonce:                make([]byte, cipher.NonceSize()),
				SymmetricCiphertext:  make([]byte, payloadSize+cipher.Overhead()),
			}))

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

				envelope.SerializeCBOR(envelope.Envelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			b.ReportMetric(float64(envelopeSize), "envelope_bytes")

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

	// Scenario 1: PSK Scaling Payload Size
	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSK/%dB", payloadSize), func(b *testing.B) {

			// Generate pre-shared key
			symmetricKey := utility.GenerateRandomBytes(config.SymmetricKeySize)

			// Instantiate ASCON cipher
			cipher := ascon.NewASCON(symmetricKey)

			// Construct plaintext for given payload size
			plaintext := utility.GenerateRandomBytes(payloadSize)

			// Create nonce
			nonce := utility.GenerateRandomBytes(cipher.NonceSize())

			// Create serialized envelope to measure the complete decryption pipeline
			serializedEnvelope := envelope.SerializeCBOR(envelope.Envelope{
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
			serializedEnvelope := envelope.SerializeCBOR(envelope.Envelope{
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
			serializedEnvelope := envelope.SerializeCBOR(envelope.Envelope{
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
