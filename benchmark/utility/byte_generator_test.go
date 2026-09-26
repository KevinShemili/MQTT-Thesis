package utility

import "testing"

func TestGenerateRandomBytesReturnsRequestedLength(t *testing.T) {

	// Arrange
	count := 32

	// Act
	result := GenerateRandomBytes(count)

	// Assert
	if len(result) != count {
		t.Fatalf("expected length %d, got %d", count, len(result))
	}
}

func TestGenerateRandomBytesWithZeroCount(t *testing.T) {

	// Arrange
	count := 0

	// Act
	result := GenerateRandomBytes(count)

	// Assert
	if len(result) != 0 {
		t.Fatalf("expected empty result, got length %d", len(result))
	}
}
