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

// Identifier for file that stores an ASCON key of a specific size
func CreateASCONKeyFileName(asconKeySize int) string {
	return fmt.Sprintf("ascon-key-%d", asconKeySize)
}

// Identifier for file that stores an AES-GCM nonce
func CreateAESGCMNonceFileName() string {
	return "aes-gcm-nonce"
}

// Identifier for file that stores an ASCON nonce
func CreateASCONNonceFileName() string {
	return "ascon-nonce"
}

// Identifier for file that stores an AES/ASCON plaintext of a specific size
func CreateAESASCONPlaintextFileName(payloadSize int) string {
	return fmt.Sprintf("aes-ascon-plaintext-%d", payloadSize)
}

// Identifier for file that stores an AES-GCM ciphertext for a specific payload size
func CreateAESGCMCiphertextFileName(payloadSize int) string {
	return fmt.Sprintf("aes-gcm-ciphertext-%d", payloadSize)
}

// Identifier for file that stores a full-schema plaintext of a specific size
func CreateFullSchemaPlaintextFileName(payloadSize int) string {
	return fmt.Sprintf("full-schema-plaintext-%d", payloadSize)
}

// Identifier for file that stores a full-schema ciphertext of a specific size
func CreateFullSchemaCiphertextFileName(payloadSize int) string {
	return fmt.Sprintf("full-schema-ciphertext-%d", payloadSize)
}

// Identifier for file that stores an ASCON ciphertext for a specific payload size
func CreateASCONCiphertextFileName(payloadSize int) string {
	return fmt.Sprintf("ascon-ciphertext-%d", payloadSize)
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
