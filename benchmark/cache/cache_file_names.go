package cache

import "fmt"

const AESKeyFileName = "aes-key"
const ASCONKeyFileName = "ascon-key"
const AESGCMNonceFileName = "aes-gcm-nonce"
const ASCONNonceFileName = "ascon-nonce"
const CPABEPublicKeyFileName = "cpabe-public-key"
const CPABEPolicyFileName = "cpabe-policy"
const CPABEPrivateKeyFileName = "cpabe-private-key"
const RSACiphertextFileName = "rsa-ciphertext"
const RSAPrivateKeyFileName = "rsa-private-key"
const RSAPublicKeyFileName = "rsa-public-key"

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

// Identifier for file that stores a serialized full-schema envelope of a specific key-management family, profile and size
func CreateFullSchemaEnvelopeFileName(keyManagement string, profile string, payloadSize int) string {
	return fmt.Sprintf("full-schema-%s-%s-envelope-%d", keyManagement, profile, payloadSize)
}

// Identifier for file that stores an ASCON ciphertext for a specific payload size
func CreateASCONCiphertextFileName(payloadSize int) string {
	return fmt.Sprintf("ascon-ciphertext-%d", payloadSize)
}

// Identifier for file that stores the RSA public key for a specific subscriber
func CreateRSAPublicKeyFileName(subscriberIndex int) string {
	return fmt.Sprintf("rsa-public-key-i%d", subscriberIndex)
}
