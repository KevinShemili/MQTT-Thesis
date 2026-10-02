package main

import (
	"fmt"
	"thesis/benchmark/cache"
	"thesis/benchmark/micro/aes_ascon/shared"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
)

type provisionDependencies struct {
	generateRandomBytes func(int) []byte
	store               func(string, []byte)
}

// The point of this program is to provide the fixture data for the AES/ASCON
// memory benchmarks by populating the cache in an earlier process.
func main() {

	config := shared.NewAESASCONConfig()

	dependencies := provisionDependencies{
		generateRandomBytes: utility.GenerateRandomBytes,
		store:               cache.Store,
	}

	runProvision(config.PayloadSizes, config.AESKeySize, config.ASCONKeySize, dependencies)
}

func runProvision(payloadSizes []int, aesKeySize int, asconKeySize int, dependencies provisionDependencies) {

	aesKey := dependencies.generateRandomBytes(aesKeySize)
	dependencies.store(shared.AESKeyFileName, aesKey)
	aesGCM := aes.NewAES(aesKey)

	asconKey := dependencies.generateRandomBytes(asconKeySize)
	dependencies.store(shared.ASCONKeyFileName, asconKey)
	asconCipher := ascon.NewASCON(asconKey)

	aesNonce := dependencies.generateRandomBytes(aesGCM.NonceSize())
	dependencies.store(shared.AESNonceFileName, aesNonce)

	asconNonce := dependencies.generateRandomBytes(asconCipher.NonceSize())
	dependencies.store(shared.ASCONNonceFileName, asconNonce)

	for _, payloadSize := range payloadSizes {

		plaintext := dependencies.generateRandomBytes(payloadSize)

		dependencies.store(fmt.Sprintf(shared.PlaintextFileNameFormat, payloadSize), plaintext)
		dependencies.store(fmt.Sprintf(shared.AESCiphertextFileNameFormat, payloadSize), aesGCM.Encrypt(nil, aesNonce, plaintext))
		dependencies.store(fmt.Sprintf(shared.ASCONCiphertextFileNameFormat, payloadSize), asconCipher.Encrypt(nil, asconNonce, plaintext))
	}
}
