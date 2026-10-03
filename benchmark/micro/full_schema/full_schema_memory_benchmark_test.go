package full_schema

import (
	"fmt"
	"runtime"
	"runtime/debug"
	"testing"
	"thesis/benchmark/memory"
	"thesis/benchmark/thermal"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
	"thesis/internal/envelope"
	"thesis/internal/serialization"
	"thesis/utility/golang/cache"
	"thesis/utility/golang/generator"
)

func BenchmarkFullSchemaMemoryEncrypt(benchmark *testing.B) {

	config := NewFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKStandard/%dB", payloadSize), func(b *testing.B) {

			cipher := aes.NewAES(cache.Load(cache.AESKeyFileName))
			plaintext := cache.Load(fmt.Sprintf(cache.PlaintextFileWSizeName, payloadSize))

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				nonce := generator.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Encrypt(nil, nonce, plaintext)

				jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSAStandard/%dB", payloadSize), func(b *testing.B) {

			publicKey := rsa.RSAFromPublicKeyBytes(cache.Load(cache.RSAPublicKeyFileName))
			plaintext := cache.Load(fmt.Sprintf(cache.PlaintextFileWSizeName, payloadSize))
			nonceSize := aes.NewAES(cache.Load(cache.AESKeyFileName)).NonceSize()

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				nonce := generator.GenerateRandomBytes(nonceSize)
				symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				asymmetricCiphertext := publicKey.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(nil, nonce, plaintext)

				jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABEStandard/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.AuthorityFromPublicKeyBytes(cache.Load(cache.CPABEPublicKeyFileName))
			policy := cpabe.ParseCPABEPolicy(
				string(cache.Load(cache.CPABEPolicyFileName)),
			)
			plaintext := cache.Load(fmt.Sprintf(cache.PlaintextFileWSizeName, payloadSize))
			nonceSize := aes.NewAES(cache.Load(cache.AESKeyFileName)).NonceSize()

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				nonce := generator.GenerateRandomBytes(nonceSize)
				symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := aes.NewAES(symmetricKey)

				asymmetricCiphertext := authority.Encrypt(policy, symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(nil, nonce, plaintext)

				jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKLightweight/%dB", payloadSize), func(b *testing.B) {

			cipher := ascon.NewASCON(cache.Load(cache.ASCONKeyFileName))
			plaintext := cache.Load(fmt.Sprintf(cache.PlaintextFileWSizeName, payloadSize))

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				nonce := generator.GenerateRandomBytes(cipher.NonceSize())
				symmetricCiphertext := cipher.Encrypt(nil, nonce, plaintext)

				cborSerializer.Serialize(envelope.AsymmetricEnvelope{
					Nonce:               nonce,
					SymmetricCiphertext: symmetricCiphertext,
				})
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSALightweight/%dB", payloadSize), func(b *testing.B) {

			publicKey := rsa.RSAFromPublicKeyBytes(cache.Load(cache.RSAPublicKeyFileName))
			plaintext := cache.Load(fmt.Sprintf(cache.PlaintextFileWSizeName, payloadSize))
			nonceSize := ascon.NewASCON(cache.Load(cache.ASCONKeyFileName)).NonceSize()

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				nonce := generator.GenerateRandomBytes(nonceSize)
				symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := publicKey.Encrypt(symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(nil, nonce, plaintext)

				cborSerializer.Serialize(envelope.AsymmetricEnvelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABELightweight/%dB", payloadSize), func(b *testing.B) {

			authority := cpabe.AuthorityFromPublicKeyBytes(cache.Load(cache.CPABEPublicKeyFileName))
			policy := cpabe.ParseCPABEPolicy(
				string(cache.Load(cache.CPABEPolicyFileName)),
			)
			plaintext := cache.Load(fmt.Sprintf(cache.PlaintextFileWSizeName, payloadSize))
			nonceSize := ascon.NewASCON(cache.Load(cache.ASCONKeyFileName)).NonceSize()

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				nonce := generator.GenerateRandomBytes(nonceSize)
				symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
				messageCipher := ascon.NewASCON(symmetricKey)

				asymmetricCiphertext := authority.Encrypt(policy, symmetricKey)
				symmetricCiphertext := messageCipher.Encrypt(nil, nonce, plaintext)

				cborSerializer.Serialize(envelope.AsymmetricEnvelope{
					AsymmetricCiphertext: asymmetricCiphertext,
					Nonce:                nonce,
					SymmetricCiphertext:  symmetricCiphertext,
				})
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}
}

func BenchmarkFullSchemaMemoryDecrypt(benchmark *testing.B) {

	config := NewFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}
	cborSerializer := serialization.CBORSerializer{}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKStandard/%dB", payloadSize), func(b *testing.B) {

			cipher := aes.NewAES(cache.Load(cache.AESKeyFileName))
			serializedEnvelope := cache.Load(fmt.Sprintf(cache.PSKStandardEnvelopeWSizeFileName, payloadSize))

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				var env envelope.AsymmetricEnvelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)
				cipher.Decrypt(nil, env.Nonce, env.SymmetricCiphertext)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSAStandard/%dB", payloadSize), func(b *testing.B) {

			privateKey := rsa.RSAFromPrivateKeyBytes(cache.Load(cache.RSAPrivateKeyFileName))
			serializedEnvelope := cache.Load(fmt.Sprintf(cache.RSAStandardEnvelopeWSizeFileName, payloadSize))

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				var env envelope.AsymmetricEnvelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)
				symmetricKey := privateKey.Decrypt(env.AsymmetricCiphertext)
				aes.NewAES(symmetricKey).Decrypt(nil, env.Nonce, env.SymmetricCiphertext)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABEStandard/%dB", payloadSize), func(b *testing.B) {

			privateKey := cpabe.PrivateKeyFromBytes(cache.Load(cache.CPABEPrivateKeyFileName))
			serializedEnvelope := cache.Load(fmt.Sprintf(cache.CPABEStandardEnvelopeWSizeFileName, payloadSize))

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				var env envelope.AsymmetricEnvelope
				jsonSerializer.Deserialize(serializedEnvelope, &env)
				symmetricKey := privateKey.Decrypt(env.AsymmetricCiphertext)
				aes.NewAES(symmetricKey).Decrypt(nil, env.Nonce, env.SymmetricCiphertext)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("PSKLightweight/%dB", payloadSize), func(b *testing.B) {

			cipher := ascon.NewASCON(cache.Load(cache.ASCONKeyFileName))
			serializedEnvelope := cache.Load(fmt.Sprintf(cache.PSKLightEnvelopeWSizeFileName, payloadSize))

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				var env envelope.AsymmetricEnvelope
				cborSerializer.Deserialize(serializedEnvelope, &env)
				cipher.Decrypt(nil, env.Nonce, env.SymmetricCiphertext)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("RSALightweight/%dB", payloadSize), func(b *testing.B) {

			privateKey := rsa.RSAFromPrivateKeyBytes(
				cache.Load(cache.RSAPrivateKeyFileName),
			)
			serializedEnvelope := cache.Load(
				fmt.Sprintf(cache.RSALightEnvelopeWSizeFileName, payloadSize),
			)

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				var env envelope.AsymmetricEnvelope
				cborSerializer.Deserialize(serializedEnvelope, &env)
				symmetricKey := privateKey.Decrypt(env.AsymmetricCiphertext)
				ascon.NewASCON(symmetricKey).Decrypt(nil, env.Nonce, env.SymmetricCiphertext)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}

	for _, payloadSize := range config.PayloadSizes {

		benchmark.Run(fmt.Sprintf("CPABELightweight/%dB", payloadSize), func(b *testing.B) {

			privateKey := cpabe.PrivateKeyFromBytes(cache.Load(cache.CPABEPrivateKeyFileName))
			serializedEnvelope := cache.Load(fmt.Sprintf(cache.CPABELightEnvelopeWSizeFileName, payloadSize))

			thermal.WaitForCooldown()

			isPrepared := prepareFullSchemaPeakMemoryMeasurement()

			for b.Loop() {
				var env envelope.AsymmetricEnvelope
				cborSerializer.Deserialize(serializedEnvelope, &env)
				symmetricKey := privateKey.Decrypt(env.AsymmetricCiphertext)
				ascon.NewASCON(symmetricKey).Decrypt(nil, env.Nonce, env.SymmetricCiphertext)
			}

			if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
				b.ReportMetric(peakBytes, "peak_rss_bytes")
			}
		})
	}
}

func BenchmarkFullSchemaMemoryBaseline(benchmark *testing.B) {

	benchmark.Run("Runtime/0B", func(b *testing.B) {

		thermal.WaitForCooldown()

		isPrepared := prepareFullSchemaPeakMemoryMeasurement()

		for b.Loop() {
		}

		if peakBytes, isAvailable := memory.PeakResidentMemory(); isPrepared && isAvailable {
			b.ReportMetric(peakBytes, "peak_rss_bytes")
		}
	})
}

func prepareFullSchemaPeakMemoryMeasurement() bool {

	runtime.GC()
	debug.FreeOSMemory()

	return memory.ResetPeakResidentMemory()
}
