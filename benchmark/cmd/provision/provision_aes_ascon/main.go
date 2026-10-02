package main

import (
	"fmt"
	"thesis/benchmark/cache"
	cmdshared "thesis/benchmark/cmd/provision/shared"
	"thesis/benchmark/micro/aes_ascon/shared"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
)

func main() {

	config := shared.NewAESASCONConfig()

	dependencies := cmdshared.ProvisionDependencies{
		GenerateRandomBytes: utility.GenerateRandomBytes,
		Store:               cache.Store,
	}

	runProvision(config.PayloadSizes, config.AESKeySize, config.ASCONKeySize, dependencies)
}

func runProvision(payloadSizes []int, aesKeySize int, asconKeySize int, dependencies cmdshared.ProvisionDependencies) {

	aesKey := dependencies.GenerateRandomBytes(aesKeySize)
	dependencies.Store(shared.AESKeyFileName, aesKey)
	aesGCM := aes.NewAES(aesKey)

	asconKey := dependencies.GenerateRandomBytes(asconKeySize)
	dependencies.Store(shared.ASCONKeyFileName, asconKey)
	asconCipher := ascon.NewASCON(asconKey)

	aesNonce := dependencies.GenerateRandomBytes(aesGCM.NonceSize())
	dependencies.Store(shared.AESNonceFileName, aesNonce)

	asconNonce := dependencies.GenerateRandomBytes(asconCipher.NonceSize())
	dependencies.Store(shared.ASCONNonceFileName, asconNonce)

	for _, payloadSize := range payloadSizes {

		plaintext := dependencies.GenerateRandomBytes(payloadSize)

		dependencies.Store(fmt.Sprintf(shared.PlaintextFileNameFormat, payloadSize), plaintext)
		dependencies.Store(fmt.Sprintf(shared.AESCiphertextFileNameFormat, payloadSize), aesGCM.Encrypt(nil, aesNonce, plaintext))
		dependencies.Store(fmt.Sprintf(shared.ASCONCiphertextFileNameFormat, payloadSize), asconCipher.Encrypt(nil, asconNonce, plaintext))
	}
}
