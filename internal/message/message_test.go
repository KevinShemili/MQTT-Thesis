package message

import (
	"bytes"
	"testing"

	"github.com/google/uuid"
)

func TestNewMessage(t *testing.T) {

	const payloadSize = 12

	msg := NewMessage(payloadSize)

	if msg.ID == uuid.Nil {
		t.Fatal("message ID is nil")
	}

	expectedPayload := bytes.Repeat([]byte{0xAB}, payloadSize)

	if !bytes.Equal(msg.Payload, expectedPayload) {
		t.Fatalf("payload produced %x, want %x", msg.Payload, expectedPayload)
	}
}
