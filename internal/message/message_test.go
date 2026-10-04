package message

import (
	"bytes"
	"testing"

	"github.com/google/uuid"
)

func TestNewMessage(t *testing.T) {

	// Arrange
	const payloadSize = 12
	expectedPayload := bytes.Repeat([]byte{0xAB}, payloadSize)

	// Act
	msg := NewMessage(payloadSize)

	// Assert
	if msg.ID == uuid.Nil {
		t.Fatal("message ID is nil")
	}

	if !bytes.Equal(msg.Payload, expectedPayload) {
		t.Fatalf("payload produced %x, want %x", msg.Payload, expectedPayload)
	}
}

func TestBuildMessagesCreatesRequestedNumberOfMessages(t *testing.T) {

	// Arrange
	messageCount := 3
	payloadSize := 256

	// Act
	messages := BuildMessages(messageCount, payloadSize)

	// Assert
	if len(messages) != messageCount {
		t.Fatalf("expected %d messages, got %d", messageCount, len(messages))
	}
}
