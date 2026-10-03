package main

import (
	"flag"
	"os"
	"thesis/benchmark/micro/full_schema"
	"thesis/benchmark/thermal"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
	"thesis/internal/envelope"
	"thesis/internal/serialization"
	"thesis/utility/golang/generator"
	"time"
)

func main() {

	algorithm := flag.String("algorithm", "", "")
	operation := flag.String("operation", "", "")
	duration := flag.Duration("duration", 0, "")
	payloadSize := flag.Int("payload-size", 0, "")

	flag.Parse()

	var throttled bool

	switch {
	case *algorithm == "PSKStandard" && *operation == "Encrypt":
		throttled = encryptPSKStandard(*payloadSize, *duration)
	case *algorithm == "RSAStandard" && *operation == "Encrypt":
		throttled = encryptRSAStandard(*payloadSize, *duration)
	case *algorithm == "CPABEStandard" && *operation == "Encrypt":
		throttled = encryptCPABEStandard(*payloadSize, *duration)
	case *algorithm == "PSKLightweight" && *operation == "Encrypt":
		throttled = encryptPSKLightweight(*payloadSize, *duration)
	case *algorithm == "RSALightweight" && *operation == "Encrypt":
		throttled = encryptRSALightweight(*payloadSize, *duration)
	case *algorithm == "CPABELightweight" && *operation == "Encrypt":
		throttled = encryptCPABELightweight(*payloadSize, *duration)
	case *algorithm == "PSKStandard" && *operation == "Decrypt":
		throttled = decryptPSKStandard(*payloadSize, *duration)
	case *algorithm == "RSAStandard" && *operation == "Decrypt":
		throttled = decryptRSAStandard(*payloadSize, *duration)
	case *algorithm == "CPABEStandard" && *operation == "Decrypt":
		throttled = decryptCPABEStandard(*payloadSize, *duration)
	case *algorithm == "PSKLightweight" && *operation == "Decrypt":
		throttled = decryptPSKLightweight(*payloadSize, *duration)
	case *algorithm == "RSALightweight" && *operation == "Decrypt":
		throttled = decryptRSALightweight(*payloadSize, *duration)
	case *algorithm == "CPABELightweight" && *operation == "Decrypt":
		throttled = decryptCPABELightweight(*payloadSize, *duration)
	default:
		panic("Unknown energy case")
	}

	if throttled {
		os.Exit(3)
	}
}

func encryptPSKStandard(payloadSize int, duration time.Duration) bool {

	config := full_schema.NewFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}

	cipher := aes.NewAES(generator.GenerateRandomBytes(config.SymmetricKeySize))

	plaintext := generator.GenerateRandomBytes(payloadSize)

	ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		nonce := generator.GenerateRandomBytes(cipher.NonceSize())
		symmetricCiphertext := cipher.Encrypt(ciphertext[:0], nonce, plaintext)

		jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
			Nonce:               nonce,
			SymmetricCiphertext: symmetricCiphertext,
		})
	}

	return throttle.IsThrottled()
}

func encryptRSAStandard(payloadSize int, duration time.Duration) bool {

	config := full_schema.NewFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}

	rsaScheme := rsa.NewRSA(config.RSAKeyBits)

	plaintext := generator.GenerateRandomBytes(payloadSize)

	cipher := aes.NewAES(generator.GenerateRandomBytes(config.SymmetricKeySize))

	ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		nonce := generator.GenerateRandomBytes(cipher.NonceSize())
		symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
		messageCipher := aes.NewAES(symmetricKey)

		asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)
		symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

		jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
			AsymmetricCiphertext: asymmetricCiphertext,
			Nonce:                nonce,
			SymmetricCiphertext:  symmetricCiphertext,
		})
	}

	return throttle.IsThrottled()
}

func encryptCPABEStandard(payloadSize int, duration time.Duration) bool {

	config := full_schema.NewFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}

	authority := cpabe.NewAuthority()

	abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)

	plaintext := generator.GenerateRandomBytes(payloadSize)

	cipher := aes.NewAES(generator.GenerateRandomBytes(config.SymmetricKeySize))

	ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		nonce := generator.GenerateRandomBytes(cipher.NonceSize())
		symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
		messageCipher := aes.NewAES(symmetricKey)

		asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)
		symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

		jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
			AsymmetricCiphertext: asymmetricCiphertext,
			Nonce:                nonce,
			SymmetricCiphertext:  symmetricCiphertext,
		})
	}

	return throttle.IsThrottled()
}

func encryptPSKLightweight(payloadSize int, duration time.Duration) bool {

	config := full_schema.NewFullSchemaConfig()
	cborSerializer := serialization.CBORSerializer{}

	cipher := ascon.NewASCON(generator.GenerateRandomBytes(config.SymmetricKeySize))

	plaintext := generator.GenerateRandomBytes(payloadSize)

	ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		nonce := generator.GenerateRandomBytes(cipher.NonceSize())
		symmetricCiphertext := cipher.Encrypt(ciphertext[:0], nonce, plaintext)

		cborSerializer.Serialize(envelope.AsymmetricEnvelope{
			Nonce:               nonce,
			SymmetricCiphertext: symmetricCiphertext,
		})
	}

	return throttle.IsThrottled()
}

func encryptRSALightweight(payloadSize int, duration time.Duration) bool {

	config := full_schema.NewFullSchemaConfig()
	cborSerializer := serialization.CBORSerializer{}

	rsaScheme := rsa.NewRSA(config.RSAKeyBits)

	plaintext := generator.GenerateRandomBytes(payloadSize)

	cipher := ascon.NewASCON(generator.GenerateRandomBytes(config.SymmetricKeySize))

	ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		nonce := generator.GenerateRandomBytes(cipher.NonceSize())
		symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
		messageCipher := ascon.NewASCON(symmetricKey)

		asymmetricCiphertext := rsaScheme.Encrypt(symmetricKey)
		symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

		cborSerializer.Serialize(envelope.AsymmetricEnvelope{
			AsymmetricCiphertext: asymmetricCiphertext,
			Nonce:                nonce,
			SymmetricCiphertext:  symmetricCiphertext,
		})
	}

	return throttle.IsThrottled()
}

func encryptCPABELightweight(payloadSize int, duration time.Duration) bool {

	config := full_schema.NewFullSchemaConfig()
	cborSerializer := serialization.CBORSerializer{}

	authority := cpabe.NewAuthority()

	abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)

	plaintext := generator.GenerateRandomBytes(payloadSize)

	cipher := ascon.NewASCON(generator.GenerateRandomBytes(config.SymmetricKeySize))

	ciphertext := make([]byte, 0, payloadSize+cipher.Overhead())

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		nonce := generator.GenerateRandomBytes(cipher.NonceSize())
		symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
		messageCipher := ascon.NewASCON(symmetricKey)

		asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)
		symmetricCiphertext := messageCipher.Encrypt(ciphertext[:0], nonce, plaintext)

		cborSerializer.Serialize(envelope.AsymmetricEnvelope{
			AsymmetricCiphertext: asymmetricCiphertext,
			Nonce:                nonce,
			SymmetricCiphertext:  symmetricCiphertext,
		})
	}

	return throttle.IsThrottled()
}

func decryptPSKStandard(payloadSize int, duration time.Duration) bool {

	config := full_schema.NewFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}

	symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
	cipher := aes.NewAES(symmetricKey)

	plaintext := generator.GenerateRandomBytes(payloadSize)
	nonce := generator.GenerateRandomBytes(cipher.NonceSize())

	serializedEnvelope, _ := jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
		Nonce:               nonce,
		SymmetricCiphertext: cipher.Encrypt(nil, nonce, plaintext),
	})

	decryptedPlaintext := make([]byte, 0, payloadSize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		var env envelope.AsymmetricEnvelope
		jsonSerializer.Deserialize(serializedEnvelope, &env)

		cipher.Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
	}

	return throttle.IsThrottled()
}

func decryptRSAStandard(payloadSize int, duration time.Duration) bool {

	config := full_schema.NewFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}

	rsaScheme := rsa.NewRSA(config.RSAKeyBits)

	symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
	cipher := aes.NewAES(symmetricKey)

	plaintext := generator.GenerateRandomBytes(payloadSize)
	nonce := generator.GenerateRandomBytes(cipher.NonceSize())

	serializedEnvelope, _ := jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
		AsymmetricCiphertext: rsaScheme.Encrypt(symmetricKey),
		Nonce:                nonce,
		SymmetricCiphertext:  cipher.Encrypt(nil, nonce, plaintext),
	})

	decryptedPlaintext := make([]byte, 0, payloadSize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		var env envelope.AsymmetricEnvelope
		jsonSerializer.Deserialize(serializedEnvelope, &env)
		recoveredSymmetricKey := rsaScheme.Decrypt(env.AsymmetricCiphertext)

		aes.NewAES(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
	}

	return throttle.IsThrottled()
}

func decryptCPABEStandard(payloadSize int, duration time.Duration) bool {

	config := full_schema.NewFullSchemaConfig()
	jsonSerializer := serialization.JSONSerializer{}

	authority := cpabe.NewAuthority()
	abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)
	subscriberKey := authority.IssuePrivateKey(abeAttributes)

	symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
	cipher := aes.NewAES(symmetricKey)

	plaintext := generator.GenerateRandomBytes(payloadSize)
	nonce := generator.GenerateRandomBytes(cipher.NonceSize())

	serializedEnvelope, _ := jsonSerializer.Serialize(envelope.AsymmetricEnvelope{
		AsymmetricCiphertext: authority.Encrypt(abePolicy, symmetricKey),
		Nonce:                nonce,
		SymmetricCiphertext:  cipher.Encrypt(nil, nonce, plaintext),
	})

	decryptedPlaintext := make([]byte, 0, payloadSize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		var env envelope.AsymmetricEnvelope
		jsonSerializer.Deserialize(serializedEnvelope, &env)
		recoveredSymmetricKey := subscriberKey.Decrypt(env.AsymmetricCiphertext)

		aes.NewAES(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
	}

	return throttle.IsThrottled()
}

func decryptPSKLightweight(payloadSize int, duration time.Duration) bool {

	config := full_schema.NewFullSchemaConfig()
	cborSerializer := serialization.CBORSerializer{}

	symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
	cipher := ascon.NewASCON(symmetricKey)

	plaintext := generator.GenerateRandomBytes(payloadSize)
	nonce := generator.GenerateRandomBytes(cipher.NonceSize())

	serializedEnvelope, _ := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
		Nonce:               nonce,
		SymmetricCiphertext: cipher.Encrypt(nil, nonce, plaintext),
	})

	decryptedPlaintext := make([]byte, 0, payloadSize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		var env envelope.AsymmetricEnvelope
		cborSerializer.Deserialize(serializedEnvelope, &env)

		cipher.Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
	}

	return throttle.IsThrottled()
}

func decryptRSALightweight(payloadSize int, duration time.Duration) bool {

	config := full_schema.NewFullSchemaConfig()
	cborSerializer := serialization.CBORSerializer{}

	rsaScheme := rsa.NewRSA(config.RSAKeyBits)

	symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
	cipher := ascon.NewASCON(symmetricKey)

	plaintext := generator.GenerateRandomBytes(payloadSize)
	nonce := generator.GenerateRandomBytes(cipher.NonceSize())

	serializedEnvelope, _ := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
		AsymmetricCiphertext: rsaScheme.Encrypt(symmetricKey),
		Nonce:                nonce,
		SymmetricCiphertext:  cipher.Encrypt(nil, nonce, plaintext),
	})

	decryptedPlaintext := make([]byte, 0, payloadSize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		var env envelope.AsymmetricEnvelope
		cborSerializer.Deserialize(serializedEnvelope, &env)
		recoveredSymmetricKey := rsaScheme.Decrypt(env.AsymmetricCiphertext)

		ascon.NewASCON(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
	}

	return throttle.IsThrottled()
}

func decryptCPABELightweight(payloadSize int, duration time.Duration) bool {

	config := full_schema.NewFullSchemaConfig()
	cborSerializer := serialization.CBORSerializer{}

	authority := cpabe.NewAuthority()
	abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(config.AttributeCount)
	subscriberKey := authority.IssuePrivateKey(abeAttributes)

	symmetricKey := generator.GenerateRandomBytes(config.SymmetricKeySize)
	cipher := ascon.NewASCON(symmetricKey)

	plaintext := generator.GenerateRandomBytes(payloadSize)
	nonce := generator.GenerateRandomBytes(cipher.NonceSize())

	serializedEnvelope, _ := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
		AsymmetricCiphertext: authority.Encrypt(abePolicy, symmetricKey),
		Nonce:                nonce,
		SymmetricCiphertext:  cipher.Encrypt(nil, nonce, plaintext),
	})

	decryptedPlaintext := make([]byte, 0, payloadSize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		var env envelope.AsymmetricEnvelope
		cborSerializer.Deserialize(serializedEnvelope, &env)
		recoveredSymmetricKey := subscriberKey.Decrypt(env.AsymmetricCiphertext)

		ascon.NewASCON(recoveredSymmetricKey).Decrypt(decryptedPlaintext[:0], env.Nonce, env.SymmetricCiphertext)
	}

	return throttle.IsThrottled()
}
