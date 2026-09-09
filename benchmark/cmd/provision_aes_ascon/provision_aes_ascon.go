package main

import (
	"benchmark/cache"
	"benchmark/cryptography/aes"
	"benchmark/cryptography/ascon"
	"benchmark/micro/aes_ascon/shared"
	"benchmark/utility"
)

// The point of this program is to provide the fixture data for the AES/ASCON
// memory benchmarks by populating the cache in an earlier process.
func main() {

	config := shared.NewAESASCONConfig()

	aesKey := utility.GenerateRandomBytes(config.AESKeySize)
	cache.StoreFile(cache.CreateAESKeyFileName(config.AESKeySize), aesKey)
	aesGCM := aes.NewAES(aesKey)

	asconKey := utility.GenerateRandomBytes(config.ASCONKeySize)
	cache.StoreFile(cache.CreateASCONKeyFileName(config.ASCONKeySize), asconKey)
	asconCipher := ascon.NewASCON(asconKey)

	aesNonce := utility.GenerateRandomBytes(aesGCM.NonceSize())
	cache.StoreFile(cache.CreateAESGCMNonceFileName(), aesNonce)

	asconNonce := utility.GenerateRandomBytes(asconCipher.NonceSize())
	cache.StoreFile(cache.CreateASCONNonceFileName(), asconNonce)

	for _, payloadSize := range config.PayloadSizes {

		plaintext := utility.GenerateRandomBytes(payloadSize)
		cache.StoreFile(cache.CreateAESASCONPlaintextFileName(payloadSize), plaintext)

		cache.StoreFile(
			cache.CreateAESGCMCiphertextFileName(payloadSize),
			aesGCM.Seal(nil, aesNonce, plaintext, nil),
		)
		cache.StoreFile(
			cache.CreateASCONCiphertextFileName(payloadSize),
			asconCipher.Seal(nil, asconNonce, plaintext, nil),
		)
	}
}
