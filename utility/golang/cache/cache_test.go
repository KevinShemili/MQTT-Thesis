package cache

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestStoreAndLoad(t *testing.T) {

	// Arrange
	cacheDirectory := filepath.Join(t.TempDir(), "cache")
	t.Setenv("CACHE_DIRECTORY", cacheDirectory)

	fileName := "test-file.txt"
	expected := []byte{1, 2, 3, 4}

	// Act
	Store(fileName, expected)
	actual := Load(fileName)
	stored, err := os.ReadFile(filepath.Join(cacheDirectory, fileName))

	// Assert
	if !bytes.Equal(actual, expected) {
		t.Fatalf(
			"expected %v, got %v",
			expected,
			actual,
		)
	}
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(stored, expected) {
		t.Fatalf("expected file content %v, got %v", expected, stored)
	}
}
