package main

import (
	"fmt"
	"thesis/benchmark/cmd/provision"
	"thesis/benchmark/micro/aes_ascon"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
	"thesis/utility/golang/cache"
	"thesis/utility/golang/generator"
)

func main() {

	config := aes_ascon.NewAESASCONConfig()

	dependencies := provision.Dependency{
		Store: cache.Store,
	}

	runProvision(config.PayloadSizes, config.AESKeySize, config.ASCONKeySize, dependencies)
}

func runProvision(payloadSizes []int, aesKeySize int, asconKeySize int, dependencies provision.Dependency) {

	aesKey := generator.GenerateRandomBytes(aesKeySize)
	dependencies.Store(cache.AESKeyFileName, aesKey)
	aesGCM := aes.NewAES(aesKey)

	asconKey := generator.GenerateRandomBytes(asconKeySize)
	dependencies.Store(cache.ASCONKeyFileName, asconKey)
	asconCipher := ascon.NewASCON(asconKey)

	aesNonce := generator.GenerateRandomBytes(aesGCM.NonceSize())
	dependencies.Store(cache.AESNonceFileName, aesNonce)

	asconNonce := generator.GenerateRandomBytes(asconCipher.NonceSize())
	dependencies.Store(cache.ASCONNonceFileName, asconNonce)

	for _, payloadSize := range payloadSizes {

		plaintext := generator.GenerateRandomBytes(payloadSize)

		dependencies.Store(fmt.Sprintf(cache.PlaintextFileWSizeName, payloadSize), plaintext)
		dependencies.Store(fmt.Sprintf(cache.AESCiphertextWSizeFileName, payloadSize), aesGCM.Encrypt(nil, aesNonce, plaintext))
		dependencies.Store(fmt.Sprintf(cache.ASCONCiphertextWSizeFileName, payloadSize), asconCipher.Encrypt(nil, asconNonce, plaintext))
	}
}
