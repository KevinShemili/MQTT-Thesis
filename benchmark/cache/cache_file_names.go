package cache

import "fmt"

// Identifier for file that stores the CP-ABE policy for a specific attribute count
func CreateCPABEPolicyFileName(attributeCount int) string {
	return fmt.Sprintf("cpabe-policy-a%d", attributeCount)
}

// Identifier for file that stores the CP-ABE private key with a specific attribute count
func CreateCPABEPrivateKeyFileName(attributeCount int) string {
	return fmt.Sprintf("cpabe-private-key-a%d", attributeCount)
}

// Identifier for file that stores the CP-ABE ciphertext for a specific attribute count
func CreateCPABECiphertextFileName(attributeCount int) string {
	return fmt.Sprintf("cpabe-ciphertext-a%d", attributeCount)
}

// Identifier for file that stores the AES key for a specific key size
func CreateAESKeyFileName(aesKeySize int) string {
	return fmt.Sprintf("aes-key-%d", aesKeySize)
}

// Identifier for file that stores the RSA ciphertext for a specific key size & subscriber
func CreateRSACiphertextFileName(rsaKeyBits int, subscriberIndex int) string {
	return fmt.Sprintf("rsa-ciphertext-%d-i%d", rsaKeyBits, subscriberIndex)
}

// Identifier for file that stores the RSA private key for a specific key size & subscriber
func CreateRSAPrivateKeyFileName(rsaKeyBits int, subscriberIndex int) string {
	return fmt.Sprintf("rsa-private-key-%d-i%d", rsaKeyBits, subscriberIndex)
}

// Identifier for file that stores the RSA public key for a specific key size & subscriber
func CreateRSAPublicKeyFileName(rsaKeyBits int, subscriberIndex int) string {
	return fmt.Sprintf("rsa-public-key-%d-i%d", rsaKeyBits, subscriberIndex)
}
