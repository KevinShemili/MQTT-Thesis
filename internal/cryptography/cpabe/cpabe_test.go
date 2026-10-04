package cpabe

import (
	"bytes"
	"testing"
)

func TestBuildSyntheticPolicyAndAttributes(t *testing.T) {

	// Arrange
	plaintext := []byte("test message")

	for _, attributeCount := range []int{1, 3, 8} {

		// Act
		policy, attributes := BuildSyntheticPolicyAndAttributes(attributeCount)

		authority := NewAuthority()
		subscriber := authority.IssuePrivateKey(attributes)

		// Act
		ciphertext := authority.Encrypt(policy, plaintext)
		decrypted := subscriber.Decrypt(ciphertext)

		// Assert
		if !bytes.Equal(decrypted, plaintext) {
			t.Fatalf("generated policy and attributes failed for %d attributes", attributeCount)
		}
	}
}

func TestCPABERoundTrip(t *testing.T) {

	// Arrange
	plaintext := []byte("test message")

	policy, attributes := BuildSyntheticPolicyAndAttributes(3)

	authority := NewAuthority()
	subscriber := authority.IssuePrivateKey(attributes)

	// Act
	ciphertext := authority.Encrypt(policy, plaintext)
	decrypted := subscriber.Decrypt(ciphertext)

	// Assert
	if !bytes.Equal(decrypted, plaintext) {
		t.Fatalf("decrypted plaintext %q does not match original %q", decrypted, plaintext)
	}
}
