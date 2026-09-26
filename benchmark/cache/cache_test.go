package cache

import (
	"bytes"
	"path/filepath"
	"testing"
)

func TestStoreAndLoad(t *testing.T) {

	// Arrange
	cacheDirectory = filepath.Join(t.TempDir(), "cache")

	fileName := "test-file"
	expected := []byte{1, 2, 3, 4}

	// Act
	Store(fileName, expected)
	actual := Load(fileName)

	// Assert
	if !bytes.Equal(actual, expected) {
		t.Fatalf(
			"expected %v, got %v",
			expected,
			actual,
		)
	}
}
