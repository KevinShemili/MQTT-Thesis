package main

import (
	"flag"
	"os"
	"thesis/benchmark/micro/aes_ascon"
	"thesis/benchmark/thermal"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
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
	case *algorithm == "AES-GCM" && *operation == "Encrypt":
		throttled = encryptAESGCM(*payloadSize, *duration)
	case *algorithm == "ASCON" && *operation == "Encrypt":
		throttled = encryptASCON(*payloadSize, *duration)
	case *algorithm == "AES-GCM" && *operation == "Decrypt":
		throttled = decryptAESGCM(*payloadSize, *duration)
	case *algorithm == "ASCON" && *operation == "Decrypt":
		throttled = decryptASCON(*payloadSize, *duration)
	default:
		panic("Unknown energy case")
	}

	if throttled {
		os.Exit(3)
	}
}

func encryptAESGCM(payloadSize int, duration time.Duration) bool {

	config := aes_ascon.NewAESASCONConfig()

	aes := aes.NewAES(generator.GenerateRandomBytes(config.AESKeySize))
	plaintext := generator.GenerateRandomBytes(payloadSize)
	nonce := generator.GenerateRandomBytes(aes.NonceSize())
	ciphertext := make([]byte, 0, payloadSize+aes.Overhead())

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		aes.Encrypt(ciphertext[:0], nonce, plaintext)
	}

	return throttle.IsThrottled()
}

func encryptASCON(payloadSize int, duration time.Duration) bool {

	config := aes_ascon.NewAESASCONConfig()

	ascon := ascon.NewASCON(generator.GenerateRandomBytes(config.ASCONKeySize))
	plaintext := generator.GenerateRandomBytes(payloadSize)
	nonce := generator.GenerateRandomBytes(ascon.NonceSize())
	ciphertext := make([]byte, 0, payloadSize+ascon.Overhead())

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		ascon.Encrypt(ciphertext[:0], nonce, plaintext)
	}

	return throttle.IsThrottled()
}

func decryptAESGCM(payloadSize int, duration time.Duration) bool {

	config := aes_ascon.NewAESASCONConfig()

	aes := aes.NewAES(generator.GenerateRandomBytes(config.AESKeySize))
	plaintext := generator.GenerateRandomBytes(payloadSize)
	nonce := generator.GenerateRandomBytes(aes.NonceSize())
	ciphertext := aes.Encrypt(nil, nonce, plaintext)
	decryptedPlaintext := make([]byte, 0, payloadSize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		aes.Decrypt(decryptedPlaintext[:0], nonce, ciphertext)
	}

	return throttle.IsThrottled()
}

func decryptASCON(payloadSize int, duration time.Duration) bool {

	config := aes_ascon.NewAESASCONConfig()

	ascon := ascon.NewASCON(generator.GenerateRandomBytes(config.ASCONKeySize))
	plaintext := generator.GenerateRandomBytes(payloadSize)
	nonce := generator.GenerateRandomBytes(ascon.NonceSize())
	ciphertext := ascon.Encrypt(nil, nonce, plaintext)
	decryptedPlaintext := make([]byte, 0, payloadSize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		ascon.Decrypt(decryptedPlaintext[:0], nonce, ciphertext)
	}

	return throttle.IsThrottled()
}
