package fixture

import (
	"fmt"
	"os"
	"path/filepath"
	"project/utils"
)

const fixtureDirectoryName = "fixtures"
const fixtureExtension = ".bin"
const CPABEPublicKey = "cpabe-public-key"
const CPABEMasterSecret = "cpabe-master-secret"

var cacheDirectory = utils.ParseStringFromEnv("CACHE_DIRECTORY")
var fixtureDirectory = filepath.Join(cacheDirectory, fixtureDirectoryName)

// Names the stored policy for one exact CP-ABE attribute-count case
func NameCPABEPolicy(attributeCount int) string {
	return fmt.Sprintf("cpabe-policy-a%d", attributeCount)
}

// Names the subscriber key belonging to one exact CP-ABE attribute-count case
func NameCPABEAttributeKey(attributeCount int) string {
	return fmt.Sprintf("cpabe-attribute-key-a%d", attributeCount)
}

// Includes every parameter that changes the ciphertext so a case can only load
// the ciphertext that was provisioned for that exact configuration
func NameCPABECiphertext(attributeCount int, aesKeySize int) string {
	return fmt.Sprintf("cpabe-ciphertext-a%d-aes%d", attributeCount, aesKeySize)
}

// Keeps AES keys of different configured sizes separate in the fixture cache
func NameAESKey(aesKeySize int) string {
	return fmt.Sprintf("aes-key-%d", aesKeySize)
}

// Identifies the ciphertext of one exact RSA subscriber and configuration
func NameRSACiphertext(rsaKeyBits int, index int, aesKeySize int) string {
	return fmt.Sprintf("rsa-ciphertext-%d-i%d-aes%d", rsaKeyBits, index, aesKeySize)
}

// Each RSA key size gets its own directory
func RSAKeyDirectory(rsaKeyBits int) string {
	return filepath.Join(cacheDirectory, fmt.Sprintf("rsa-%d", rsaKeyBits))
}

// Caches the fixture in the fixture directory, creating it if it does not exist yet
func Store(name string, content []byte) {

	if err := os.MkdirAll(fixtureDirectory, utils.DirectoryPermissions); err != nil {
		panic(err)
	}

	if err := os.WriteFile(fixturePath(name), content, utils.FilePermissions); err != nil {
		panic(err)
	}
}

// Whether a fixture has already been built, so provisioning skips what is there,
// used specifically by the provisioning process
func Find(name string) ([]byte, bool) {

	content, err := os.ReadFile(fixturePath(name))
	if err != nil {
		return nil, false
	}

	return content, true
}

// Loads a fixture required by a benchmark,
// here a miss is fatal as a memory benchmark must never generate its own fixtures,
// which would distort the memory measurement
func Load(name string) []byte {

	content, found := Find(name)
	if !found {
		panic(fmt.Sprintf("fixture %q was never provisioned", name))
	}

	return content
}

func fixturePath(name string) string {
	return filepath.Join(fixtureDirectory, name+fixtureExtension)
}
