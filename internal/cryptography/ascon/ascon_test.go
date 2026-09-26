package ascon

import (
	"bytes"
	"testing"
	"thesis/benchmark/utility"
)

const symmetricKeySize = 16

func TestASCONRoundTrip(t *testing.T) {
	key := utility.GenerateRandomBytes(symmetricKeySize)
	plaintext := []byte("test message")

	cipher := NewASCON(key)
	nonce := utility.GenerateRandomBytes(cipher.NonceSize())

	ciphertext := cipher.Encrypt(nil, nonce, plaintext)
	decrypted := cipher.Decrypt(nil, nonce, ciphertext)

	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("round trip produced %q, want %q", decrypted, plaintext)
	}
}
