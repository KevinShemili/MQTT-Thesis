package main

import (
	"fmt"
	"os"
	"project/cryptography"
	"project/fixture"
	"project/utils"
	"strconv"
)

const cpabeAttributesGroup = "CPABEAttributes"
const rsaSubscribersGroup = "RSASubscribers"
const rsaKeyBitsGroup = "RSAKeyBits"

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
		panic("usage: provision <group> <sweep value>")
	}

	group := os.Args[1]

	sweepValue, err := strconv.Atoi(os.Args[2])
	if err != nil {
		panic(err)
	}

	aesKeySize := utils.ParseIntFromEnv("ATTRIBUTE_KEY_SCALING_AES_KEY_SIZE")
	aesKey := provisionAESKey(aesKeySize)

	switch group {

	case cpabeAttributesGroup:
		provisionCPABE(sweepValue, aesKeySize, aesKey)

	case rsaSubscribersGroup:
		provisionRSASubscribers(sweepValue, aesKeySize, aesKey)

	case rsaKeyBitsGroup:
		provisionRSAKeyBits(sweepValue, aesKeySize, aesKey)

	default:
		panic(fmt.Sprintf("unknown group %q", group))
	}
}

func provisionAESKey(aesKeySize int) []byte {

	if aesKey, found := fixture.Find(fixture.NameAESKey(aesKeySize)); found {
		return aesKey
	}

	aesKey := utils.GenerateRandomBytes(aesKeySize)
	fixture.Store(fixture.NameAESKey(aesKeySize), aesKey)

	return aesKey
}

func provisionCPABEAuthority() cryptography.CPABEAuthority {

	publicKeyBytes, publicKeyFound := fixture.Find(fixture.CPABEPublicKey)
	masterSecretBytes, masterSecretFound := fixture.Find(fixture.CPABEMasterSecret)

	if publicKeyFound && masterSecretFound {
		return cryptography.UnmarshalCPABEAuthority(publicKeyBytes, masterSecretBytes)
	}

	authority := cryptography.NewCPABEAuthority()

	fixture.Store(
		fixture.CPABEPublicKey,
		cryptography.MarshalCPABEPublicKey(authority.PublisherKey()),
	)
	fixture.Store(
		fixture.CPABEMasterSecret,
		cryptography.MarshalCPABEMasterSecret(authority),
	)

	return authority
}

func provisionCPABE(attributeCount int, aesKeySize int, aesKey []byte) {

	authority := provisionCPABEAuthority()

	abePolicy, abeAttributes := cryptography.BuildSyntheticPolicyAndAttributes(attributeCount)

	fixture.Store(
		fixture.NameCPABEPolicy(attributeCount),
		[]byte(cryptography.BuildSyntheticPolicyString(attributeCount)),
	)
	fixture.Store(
		fixture.NameCPABEAttributeKey(attributeCount),
		cryptography.MarshalCPABESubscriberKey(authority.IssueSubscriberKey(abeAttributes)),
	)
	fixture.Store(
		fixture.NameCPABECiphertext(attributeCount, aesKeySize),
		authority.Encrypt(abePolicy, aesKey),
	)
}

func provisionRSASubscribers(subscriberCount int, aesKeySize int, aesKey []byte) {

	rsaKeyBits := utils.ParseIntFromEnv("ATTRIBUTE_KEY_SCALING_FIXED_RSA_KEY_BITS")

	var subscriberKey cryptography.RSA

	for index := range subscriberCount {
		subscriberKey = provisionRSAKey(rsaKeyBits, index)
	}

	decryptingIndex := subscriberCount - 1

	fixture.Store(
		fixture.NameRSACiphertext(rsaKeyBits, decryptingIndex, aesKeySize),
		subscriberKey.Encrypt(aesKey),
	)
}

func provisionRSAKeyBits(rsaKeyBits int, aesKeySize int, aesKey []byte) {

	subscriberKey := provisionRSAKey(rsaKeyBits, 0)

	fixture.Store(
		fixture.NameRSACiphertext(rsaKeyBits, 0, aesKeySize),
		subscriberKey.Encrypt(aesKey),
	)
}

func provisionRSAKey(rsaKeyBits int, index int) cryptography.RSA {

	directory := fixture.RSAKeyDirectory(rsaKeyBits)

	key, stored := cryptography.LoadRSAKey(directory, index)
	if !stored {
		key = cryptography.NewRSA(rsaKeyBits)
		cryptography.StoreRSAKey(key, directory, index)
	}

	if _, stored := cryptography.LoadRSAPublicKey(directory, index); !stored {
		cryptography.StoreRSAPublicKey(key, directory, index)
	}

	return key
}
