package rsa

import (
	"bytes"
	"testing"
)

const rsaKeyBits = 2048

func TestRSARoundTrip(t *testing.T) {

	// Arrange
	plaintext := []byte("test message")
	cipher := NewRSA(rsaKeyBits)

	// Act
	ciphertext := cipher.Encrypt(plaintext)
	decrypted := cipher.Decrypt(ciphertext)

	// Assert
	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("decrypted plaintext %q does not match original %q", decrypted, plaintext)
	}
}
