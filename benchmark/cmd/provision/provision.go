package main

import (
	"benchmark/cache"
	"benchmark/cryptography/aes"
	"benchmark/cryptography/ascon"
	"benchmark/cryptography/cpabe"
	"benchmark/cryptography/rsa"
	"benchmark/utility"
	"fmt"
	"os"
	"strconv"
)

const cpabeAttributesAlgorithm = "CPABEAttributes"
const rsaSubscribersAlgorithm = "RSASubscribers"
const rsaKeyBitsAlgorithm = "RSAKeyBits"
const aesGCMAlgorithm = "AES-GCM"
const asconAlgorithm = "ASCON"
const payloadScalingAlgorithm = "PayloadScaling"

// The point of this program is to provide the fixture data for one benchmark case
// It does so by populating the cache, allowing the benchmark processes to just load it
//
// This is especially important for the peak memory usage, because if the bench process
// generates the fixture needed indicated memory could be misleading as it has been polluted
// by fixture concerns
//
// While not really needed for the macrobenchmark, for the microbenchmark where realistic deployment
// requirements can be sidelined in favor of isolation of the operation, it allows us to
// obtain a more accurate measurement of the desired operation
func main() {

	if len(os.Args) != 3 {
		panic("usage: provision <algorithm> <parameter value>")
	}

	algorithm := os.Args[1]

	parameterValue, err := strconv.Atoi(os.Args[2])
	if err != nil {
		panic(err)
	}

	switch algorithm {

	case cpabeAttributesAlgorithm:
		aesKeySize := utility.ParseIntFromEnv("CPABE_RSA_SCALING_AES_KEY_SIZE")
		aesKey := provisionAESKey(aesKeySize)
		provisionCPABE(parameterValue, aesKeySize, aesKey)

	case rsaSubscribersAlgorithm:
		provisionRSASubscribers(parameterValue)

	case rsaKeyBitsAlgorithm:
		aesKeySize := utility.ParseIntFromEnv("CPABE_RSA_SCALING_AES_KEY_SIZE")
		aesKey := provisionAESKey(aesKeySize)
		provisionRSAKeyBits(parameterValue, aesKey)

	case aesGCMAlgorithm:
		provisionAESGCM(parameterValue)

	case asconAlgorithm:
		provisionASCON(parameterValue)

	case payloadScalingAlgorithm:
		provisionPayloadScaling(parameterValue)

	default:
		panic(fmt.Sprintf("unknown algorithm %q", algorithm))
	}
}

func provisionPayloadScaling(payloadSize int) {

	aesKeySize := utility.ParseIntFromEnv("PAYLOAD_SCALING_AES_KEY_SIZE")
	attributeCount := utility.ParseIntFromEnv("PAYLOAD_SCALING_ATTRIBUTE_COUNT")
	rsaKeyBits := utility.ParseIntFromEnv("PAYLOAD_SCALING_RSA_KEY_BITS")

	aesKey := provisionAESKey(aesKeySize)
	cipher := aes.NewAES(aesKey)
	plaintext := utility.GenerateRandomBytes(payloadSize)
	nonce := provisionAESGCMNonce(cipher.NonceSize())

	cache.StoreFile(
		cache.CreatePayloadScalingPlaintextFileName(payloadSize),
		plaintext,
	)
	cache.StoreFile(
		cache.CreatePayloadScalingCiphertextFileName(payloadSize),
		cipher.Seal(nil, nonce, plaintext, nil),
	)

	if _, found := cache.FindFile(cache.CreateCPABECiphertextFileName(attributeCount)); !found {
		provisionCPABE(attributeCount, aesKeySize, aesKey)
	}

	if _, found := cache.FindFile(cache.CreateRSACiphertextFileName(rsaKeyBits, 0)); !found {
		provisionRSAKeyBits(rsaKeyBits, aesKey)
	}
}

func provisionAESGCM(payloadSize int) {

	keySize := utility.ParseIntFromEnv("AES_ASCON_KEY_SIZE")
	key := provisionAESKey(keySize)
	cipher := aes.NewAES(key)
	plaintext := provisionAESASCONPlaintext(payloadSize)
	nonce := provisionAESGCMNonce(cipher.NonceSize())

	cache.StoreFile(
		cache.CreateAESGCMCiphertextFileName(payloadSize),
		cipher.Seal(nil, nonce, plaintext, nil),
	)
}

func provisionASCON(payloadSize int) {

	keySize := utility.ParseIntFromEnv("AES_ASCON_KEY_SIZE")
	key := provisionASCONKey(keySize)
	cipher := ascon.NewASCON(key)
	plaintext := provisionAESASCONPlaintext(payloadSize)
	nonce := provisionASCONNonce(cipher.NonceSize())

	cache.StoreFile(
		cache.CreateASCONCiphertextFileName(payloadSize),
		cipher.Seal(nil, nonce, plaintext, nil),
	)
}

func provisionAESASCONPlaintext(payloadSize int) []byte {

	fileName := cache.CreateAESASCONPlaintextFileName(payloadSize)
	if plaintext, found := cache.FindFile(fileName); found {
		return plaintext
	}

	plaintext := utility.GenerateRandomBytes(payloadSize)
	cache.StoreFile(fileName, plaintext)

	return plaintext
}

func provisionAESGCMNonce(nonceSize int) []byte {

	fileName := cache.CreateAESGCMNonceFileName()
	if nonce, found := cache.FindFile(fileName); found {
		return nonce
	}

	nonce := utility.GenerateRandomBytes(nonceSize)
	cache.StoreFile(fileName, nonce)

	return nonce
}

func provisionASCONKey(keySize int) []byte {

	fileName := cache.CreateASCONKeyFileName(keySize)
	if key, found := cache.FindFile(fileName); found {
		return key
	}

	key := utility.GenerateRandomBytes(keySize)
	cache.StoreFile(fileName, key)

	return key
}

func provisionASCONNonce(nonceSize int) []byte {

	fileName := cache.CreateASCONNonceFileName()
	if nonce, found := cache.FindFile(fileName); found {
		return nonce
	}

	nonce := utility.GenerateRandomBytes(nonceSize)
	cache.StoreFile(fileName, nonce)

	return nonce
}

func provisionAESKey(aesKeySize int) []byte {

	if aesKey, found := cache.FindFile(cache.CreateAESKeyFileName(aesKeySize)); found {
		return aesKey
	}

	aesKey := utility.GenerateRandomBytes(aesKeySize)
	cache.StoreFile(cache.CreateAESKeyFileName(aesKeySize), aesKey)

	return aesKey
}

func provisionCPABE(attributeCount int, aesKeySize int, aesKey []byte) {

	authority := provisionCPABEAuthority()

	abePolicy, abeAttributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

	cache.StoreFile(
		cache.CreateCPABEPolicyFileName(attributeCount),
		[]byte(abePolicy.String()),
	)

	cache.StoreFile(
		cache.CreateCPABEPrivateKeyFileName(attributeCount),
		cpabe.MarshalCPABEPrivateKey(authority.IssuePrivateKey(abeAttributes).PrivateKey),
	)

	cache.StoreFile(
		cache.CreateCPABECiphertextFileName(attributeCount),
		authority.Encrypt(abePolicy, aesKey),
	)
}

func provisionCPABEAuthority() cpabe.CPABEAuthority {

	// Check if the authority is already provisioned
	// - If so -> return it
	publicKeyBytes, isPublicKeyFound := cache.FindFile(cache.CPABEPublicKeyFileName)
	masterSecretBytes, isMasterSecretFound := cache.FindFile(cache.CPABEMasterSecretFileName)

	if isPublicKeyFound && isMasterSecretFound {
		return cpabe.UnmarshalCPABEAuthority(publicKeyBytes, masterSecretBytes)
	}

	// If not -> Create it
	authority := cpabe.NewCPABEAuthority()

	cache.StoreFile(
		cache.CPABEPublicKeyFileName,
		cpabe.MarshalCPABEPublicKey(authority.PublicKey),
	)

	cache.StoreFile(
		cache.CPABEMasterSecretFileName,
		cpabe.MarshalCPABEMasterSecret(authority.SystemSecretKey),
	)

	return authority
}

func provisionRSASubscribers(subscriberCount int) {

	rsaKeyBits := utility.ParseIntFromEnv("CPABE_RSA_SCALING_FIXED_RSA_KEY_SIZE")

	for index := range subscriberCount {
		provisionRSAKey(rsaKeyBits, index)
	}
}

func provisionRSAKeyBits(rsaKeyBits int, aesKey []byte) {

	subscriberKey := provisionRSAKey(rsaKeyBits, 0)

	cache.StoreFile(
		cache.CreateRSACiphertextFileName(rsaKeyBits, 0),
		subscriberKey.Encrypt(aesKey),
	)
}

func provisionRSAKey(rsaKeyBits int, index int) rsa.RSA {

	if keyBytes, found := cache.FindFile(cache.CreateRSAPrivateKeyFileName(rsaKeyBits, index)); found {
		return rsa.UnmarshalPrivateKey(keyBytes)
	}

	key := rsa.NewRSA(rsaKeyBits)

	// A key is cached whole, so a private half that is there means the public half is too
	cache.StoreFile(
		cache.CreateRSAPrivateKeyFileName(rsaKeyBits, index),
		rsa.MarshalPrivateKey(key.PrivateKey),
	)
	cache.StoreFile(
		cache.CreateRSAPublicKeyFileName(rsaKeyBits, index),
		rsa.MarshalPublicKey(key.PublicKey),
	)

	return key
}
