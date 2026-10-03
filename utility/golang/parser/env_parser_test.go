package parser

import "testing"

func TestParseIntListFromEnv(t *testing.T) {

	// Arrange
	t.Setenv("TEST_INT_LIST", "16, 256, 4096")

	// Act
	result := ParseIntListFromEnv("TEST_INT_LIST")

	// Assert
	expected := []int{16, 256, 4096}

	if len(result) != len(expected) {
		t.Fatalf("expected %d values, got %d", len(expected), len(result))
	}

	for index := range expected {
		if result[index] != expected[index] {
			t.Fatalf(
				"expected value %d at index %d, got %d",
				expected[index],
				index,
				result[index],
			)
		}
	}
}

func TestParseIntListFromEnvPanicsForInvalidValue(t *testing.T) {

	// Arrange
	t.Setenv("TEST_INT_LIST", "16,invalid,4096")

	// Act
	defer func() {

		// Assert
		if recover() == nil {
			t.Fatal("expected panic")
		}
	}()

	ParseIntListFromEnv("TEST_INT_LIST")
}

func TestParseIntFromEnv(t *testing.T) {

	// Arrange
	t.Setenv("TEST_INT", " 42 ")

	// Act
	result := ParseIntFromEnv("TEST_INT")

	// Assert
	if result != 42 {
		t.Fatalf("expected 42, got %d", result)
	}
}

func TestParseIntFromEnvPanicsForInvalidValue(t *testing.T) {

	// Arrange
	t.Setenv("TEST_INT", "invalid")

	// Act
	defer func() {

		// Assert
		if recover() == nil {
			t.Fatal("expected panic")
		}
	}()

	ParseIntFromEnv("TEST_INT")
}

func TestParseStringFromEnv(t *testing.T) {

	// Arrange
	t.Setenv("TEST_STRING", "  hello  ")

	// Act
	result := ParseStringFromEnv("TEST_STRING")

	// Assert
	if result != "hello" {
		t.Fatalf("expected %q, got %q", "hello", result)
	}
}

func TestParseStringFromEnvPanicsWhenEmpty(t *testing.T) {

	// Arrange
	t.Setenv("TEST_STRING", "   ")

	// Act
	defer func() {

		// Assert
		if recover() == nil {
			t.Fatal("expected panic")
		}
	}()

	ParseStringFromEnv("TEST_STRING")
}
