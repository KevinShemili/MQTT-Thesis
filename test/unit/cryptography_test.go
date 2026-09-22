package unit

import (
	"bytes"
	"testing"

	"thesis/benchmark/utility"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
)

const (
	symmetricKeySize = 16
	rsaKeyBits       = 2048
)

func TestAESRoundTrip(t *testing.T) {

	key := utility.GenerateRandomBytes(symmetricKeySize)
	plaintext := []byte("test message")

	cipher := aes.NewAES(key)
	nonce := utility.GenerateRandomBytes(cipher.NonceSize())

	ciphertext := cipher.Encrypt(nil, nonce, plaintext)
	decrypted := cipher.Decrypt(nil, nonce, ciphertext)

	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("round trip produced %q, want %q", decrypted, plaintext)
	}
}

func TestASCONRoundTrip(t *testing.T) {
	key := utility.GenerateRandomBytes(symmetricKeySize)
	plaintext := []byte("test message")

	cipher := ascon.NewASCON(key)
	nonce := utility.GenerateRandomBytes(cipher.NonceSize())

	ciphertext := cipher.Encrypt(nil, nonce, plaintext)
	decrypted := cipher.Decrypt(nil, nonce, ciphertext)

	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("round trip produced %q, want %q", decrypted, plaintext)
	}
}

func TestRSARoundTrip(t *testing.T) {

	plaintext := []byte("test message")
	cipher := rsa.NewRSA(rsaKeyBits)

	ciphertext := cipher.Encrypt(plaintext)
	decrypted := cipher.Decrypt(ciphertext)

	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("decrypted plaintext %q does not match original %q", decrypted, plaintext)
	}
}

func TestBuildSyntheticPolicyAndAttributes(t *testing.T) {

	plaintext := []byte("test message")

	for _, attributeCount := range []int{1, 3, 8} {

		policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(attributeCount)

		authority := cpabe.NewAuthority()
		subscriber := authority.IssuePrivateKey(attributes)

		ciphertext := authority.Encrypt(policy, plaintext)
		decrypted := subscriber.Decrypt(ciphertext)

		if !bytes.Equal(decrypted, plaintext) {
			t.Fatalf(
				"generated policy and attributes failed for %d attributes",
				attributeCount,
			)
		}
	}
}

func TestCPABERoundTrip(t *testing.T) {

	plaintext := []byte("test message")

	policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(3)

	authority := cpabe.NewAuthority()
	subscriber := authority.IssuePrivateKey(attributes)

	ciphertext := authority.Encrypt(policy, plaintext)
	decrypted := subscriber.Decrypt(ciphertext)

	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("decrypted plaintext %q does not match original %q", decrypted, plaintext)
	}
}
