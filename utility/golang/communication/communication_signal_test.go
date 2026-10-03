package communication

import (
	"bufio"
	"bytes"
	"errors"
	"io"
	"strings"
	"testing"
)

func TestReadSignalReturnsNilWhenSignalMatches(t *testing.T) {

	// Arrange
	reader := bufio.NewReader(strings.NewReader("GO\n"))

	// Act
	err := ReadSignal(reader, "GO")

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
}

func TestReadSignalReturnsErrorWhenSignalDoesNotMatch(t *testing.T) {

	// Arrange
	reader := bufio.NewReader(strings.NewReader("DONE\n"))

	// Act
	err := ReadSignal(reader, "GO")

	// Assert
	if err == nil {
		t.Fatal("expected error, got nil")
	}

	expected := `expected GO, got "DONE\n"`

	if err.Error() != expected {
		t.Fatalf("expected %q, got %q", expected, err.Error())
	}
}

func TestReadSignalReturnsReadError(t *testing.T) {

	// Arrange
	reader := bufio.NewReader(errorReader{})

	// Act
	err := ReadSignal(reader, "GO")

	// Assert
	if !errors.Is(err, io.ErrClosedPipe) {
		t.Fatalf("expected %v, got %v", io.ErrClosedPipe, err)
	}
}

func TestWriteSignalWritesSignalWithNewline(t *testing.T) {

	// Arrange
	var output bytes.Buffer

	// Act
	err := WriteSignal(&output, "DONE")

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	expected := "DONE\n"

	if output.String() != expected {
		t.Fatalf("expected %q, got %q", expected, output.String())
	}
}

func TestWriteSignalReturnsWriteError(t *testing.T) {

	// Arrange
	writer := errorWriter{}

	// Act
	err := WriteSignal(writer, "DONE")

	// Assert
	if !errors.Is(err, io.ErrClosedPipe) {
		t.Fatalf("expected %v, got %v", io.ErrClosedPipe, err)
	}
}

type errorReader struct{}

func (errorReader) Read(_ []byte) (int, error) {
	return 0, io.ErrClosedPipe
}

type errorWriter struct{}

func (errorWriter) Write(_ []byte) (int, error) {
	return 0, io.ErrClosedPipe
}
