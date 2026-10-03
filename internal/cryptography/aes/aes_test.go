package aes

import (
	"bytes"
	"testing"
	generator "thesis/utility/golang/generator"
)

const symmetricKeySize = 16

func TestAESRoundTrip(t *testing.T) {

	key := generator.GenerateRandomBytes(symmetricKeySize)
	plaintext := []byte("test message")

	cipher := NewAES(key)
	nonce := generator.GenerateRandomBytes(cipher.NonceSize())

	ciphertext := cipher.Encrypt(nil, nonce, plaintext)
	decrypted := cipher.Decrypt(nil, nonce, ciphertext)

	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("round trip produced %q, want %q", decrypted, plaintext)
	}
}
