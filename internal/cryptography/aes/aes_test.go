package aes

import (
	"bytes"
	"testing"
	generator "thesis/utility/golang/generator"
)

const symmetricKeySize = 16

func TestAESRoundTrip(t *testing.T) {
	// Arrange
	key := generator.GenerateRandomBytes(symmetricKeySize)
	plaintext := []byte("test message")

	cipher := NewAES(key)
	nonce := generator.GenerateRandomBytes(cipher.NonceSize())

	// Act
	ciphertext := cipher.Encrypt(nil, nonce, plaintext)
	decrypted := cipher.Decrypt(nil, nonce, ciphertext)

	// Assert
	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("round trip produced %q, want %q", decrypted, plaintext)
	}
}
