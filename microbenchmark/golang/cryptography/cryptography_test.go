package cryptography

import (
	"bytes"
	"project/cryptography/aes"
	"project/cryptography/ascon"
	"project/cryptography/cpabe"
	"project/cryptography/rsa"
	"project/utils"
	"testing"
)

var AES_KEY_SIZE = 16
var ASCON_KEY_SIZE = 16
var RSA_KEY_SIZE = 2048

func TestAESRoundTrip(t *testing.T) {

	// Arrange
	key := utils.GenerateRandomBytes(AES_KEY_SIZE)
	plaintext := []byte("test")
	aes := aes.NewAES(key)
	nonce := utils.GenerateRandomBytes(aes.NonceSize())

	// Act
	ciphertext := aes.Seal(nil, nonce, plaintext, nil)
	decrypted, err := aes.Open(nil, nonce, ciphertext, nil)

	// Assert
	if err != nil {
		t.Fatalf("AES: Decrypt Ciphertext: %v", err)
	}

	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("AES: Round trip produced %q, want %q", decrypted, plaintext)
	}
}

func TestASCONRoundTrip(t *testing.T) {

	// Arrange
	key := utils.GenerateRandomBytes(ASCON_KEY_SIZE)
	plaintext := []byte("test")
	ascon := ascon.NewASCON(key)
	nonce := utils.GenerateRandomBytes(ascon.NonceSize())

	// Act
	ciphertext := ascon.Seal(nil, nonce, plaintext, nil)
	decrypted, err := ascon.Open(nil, nonce, ciphertext, nil)

	// Assert
	if err != nil {
		t.Fatalf("ASCON: Decrypt Ciphertext: %v", err)
	}

	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("ASCON: Round trip produced %q, want %q", decrypted, plaintext)
	}
}

func TestRSARoundTrip(t *testing.T) {

	// Arrange
	plaintext := []byte("test")
	rsa := rsa.NewRSA(RSA_KEY_SIZE)

	// Act
	ciphertext := rsa.Encrypt(plaintext)
	decrypted := rsa.Decrypt(ciphertext)

	// Assert
	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("RSA: Round trip produced %q, want %q", decrypted, plaintext)
	}
}

func TestCPABERoundTrip(t *testing.T) {

	// Arrange
	plaintext := []byte("test")
	policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(1)
	authority := cpabe.NewCPABEAuthority()
	subscriberKey := authority.IssuePrivateKey(attributes)

	// Act
	ciphertext := authority.Encrypt(policy, plaintext)
	decrypted := subscriberKey.Decrypt(ciphertext)

	// Assert
	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("CP-ABE: Round trip produced %q, want %q", decrypted, plaintext)
	}
}
