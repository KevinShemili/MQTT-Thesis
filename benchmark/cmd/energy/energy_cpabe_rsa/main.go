package main

import (
	"flag"
	"fmt"
	"os"
	"thesis/benchmark/cache"
	"thesis/benchmark/micro/cpabe_rsa/shared"
	"thesis/benchmark/thermal"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
	"time"
)

func main() {

	algorithm := flag.String("algorithm", "", "")
	operation := flag.String("operation", "", "")
	duration := flag.Duration("duration", 0, "")
	attributeCount := flag.Int("attribute-count", 0, "")
	subscriberCount := flag.Int("subscriber-count", 0, "")
	flag.Parse()

	var throttled bool

	switch {
	case *algorithm == "CPABEAttributes" && *operation == "Encrypt":
		throttled = encryptCPABEAttributes(*attributeCount, *duration)
	case *algorithm == "RSASubscribers" && *operation == "Encrypt":
		throttled = encryptRSASubscribers(*subscriberCount, *duration)
	case *algorithm == "CPABEAttributes" && *operation == "Decrypt":
		throttled = decryptCPABEAttributes(*attributeCount, *duration)
	case *algorithm == "RSAKeyBits" && *operation == "Decrypt":
		throttled = decryptRSAKeyBits(*duration)
	default:
		panic("Unknown energy case")
	}

	if throttled {
		os.Exit(3)
	}
}

func encryptCPABEAttributes(attributeCount int, duration time.Duration) bool {

	config := shared.NewCPABERSAConfig()

	authority := cpabe.NewAuthority()
	abePolicy, _ := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)
	symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		authority.Encrypt(abePolicy, symmetricKey)
	}

	return throttle.IsThrottled()
}

func encryptRSASubscribers(subscriberCount int, duration time.Duration) bool {

	config := shared.NewCPABERSAConfig()

	publicKeySlice := make([]rsa.RSA, subscriberCount)
	for index := range subscriberCount {
		publicKeySlice[index] = rsa.RSAFromPublicKeyBytes(cache.Load(fmt.Sprintf(shared.RSAPublicKeyFileNameFormat, index)))
	}

	symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		for index := range subscriberCount {
			publicKeySlice[index].Encrypt(symmetricKey)
		}
	}

	return throttle.IsThrottled()
}

func decryptCPABEAttributes(attributeCount int, duration time.Duration) bool {

	config := shared.NewCPABERSAConfig()

	authority := cpabe.NewAuthority()
	abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)
	privateKey := authority.IssuePrivateKey(abeAttributes)
	symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
	asymmetricCiphertext := authority.Encrypt(abePolicy, symmetricKey)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		privateKey.Decrypt(asymmetricCiphertext)
	}

	return throttle.IsThrottled()
}

func decryptRSAKeyBits(duration time.Duration) bool {

	config := shared.NewCPABERSAConfig()

	privateKey := rsa.NewRSA(config.FixedRSAKeyBits)
	symmetricKey := utility.GenerateRandomBytes(config.AESKeySize)
	asymmetricCiphertext := privateKey.Encrypt(symmetricKey)

	throttle := thermal.NewThrottleWatch()

	deadline := time.Now().Add(duration)
	for time.Now().Before(deadline) {
		privateKey.Decrypt(asymmetricCiphertext)
	}

	return throttle.IsThrottled()
}
