package main

import (
	"thesis/benchmark/cache"
	"thesis/benchmark/micro/aes_ascon/shared"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
)

// The point of this program is to provide the fixture data for the AES/ASCON
// memory benchmarks by populating the cache in an earlier process.
func main() {

	config := shared.NewAESASCONConfig()

	aesKey := utility.GenerateRandomBytes(config.AESKeySize)
	cache.Store(cache.AESKeyFileName, aesKey)
	aesGCM := aes.NewAES(aesKey)

	asconKey := utility.GenerateRandomBytes(config.ASCONKeySize)
	cache.Store(cache.ASCONKeyFileName, asconKey)
	asconCipher := ascon.NewASCON(asconKey)

	aesNonce := utility.GenerateRandomBytes(aesGCM.NonceSize())
	cache.Store(cache.AESGCMNonceFileName, aesNonce)

	asconNonce := utility.GenerateRandomBytes(asconCipher.NonceSize())
	cache.Store(cache.ASCONNonceFileName, asconNonce)

	for _, payloadSize := range config.PayloadSizes {

		plaintext := utility.GenerateRandomBytes(payloadSize)
		cache.Store(cache.CreateAESASCONPlaintextFileName(payloadSize), plaintext)

		cache.Store(
			cache.CreateAESGCMCiphertextFileName(payloadSize),
			aesGCM.Encrypt(nil, aesNonce, plaintext),
		)
		cache.Store(
			cache.CreateASCONCiphertextFileName(payloadSize),
			asconCipher.Encrypt(nil, asconNonce, plaintext),
		)
	}
}
