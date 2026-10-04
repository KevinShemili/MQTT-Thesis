package ascon

import (
	"bytes"
	"testing"
	"thesis/utility/golang/generator"
)

const symmetricKeySize = 16

func TestASCONRoundTrip(t *testing.T) {

	// Arrange
	key := generator.GenerateRandomBytes(symmetricKeySize)
	plaintext := []byte("test message")

	cipher := NewASCON(key)
	nonce := generator.GenerateRandomBytes(cipher.NonceSize())

	// Act
	ciphertext := cipher.Encrypt(nil, nonce, plaintext)
	decrypted := cipher.Decrypt(nil, nonce, ciphertext)

	// Assert
	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("round trip produced %q, want %q", decrypted, plaintext)
	}
}
