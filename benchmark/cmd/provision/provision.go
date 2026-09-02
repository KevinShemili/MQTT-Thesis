package main

import (
	"benchmark/cache"
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

	aesKeySize := utility.ParseIntFromEnv("ATTRIBUTE_KEY_SCALING_AES_KEY_SIZE")
	aesKey := provisionAESKey(aesKeySize)

	switch algorithm {

	case cpabeAttributesAlgorithm:
		provisionCPABE(parameterValue, aesKeySize, aesKey)

	case rsaSubscribersAlgorithm:
		provisionRSASubscribers(parameterValue)

	case rsaKeyBitsAlgorithm:
		provisionRSAKeyBits(parameterValue, aesKey)

	default:
		panic(fmt.Sprintf("unknown algorithm %q", algorithm))
	}
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

	rsaKeyBits := utility.ParseIntFromEnv("ATTRIBUTE_KEY_SCALING_FIXED_RSA_KEY_SIZE")

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
