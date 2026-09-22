package unit

import (
	"bytes"
	"testing"

	"thesis/internal/message"

	"github.com/google/uuid"
)

func TestNewMessage(t *testing.T) {

	const payloadSize = 12

	msg := message.NewMessage(payloadSize)

	if msg.ID == uuid.Nil {
		t.Fatal("message ID is nil")
	}

	expectedPayload := bytes.Repeat([]byte{0xAB}, payloadSize)

	if !bytes.Equal(msg.Payload, expectedPayload) {
		t.Fatalf("payload produced %x, want %x", msg.Payload, expectedPayload)
	}
}

func TestValidateMessageAcceptsValidPayload(t *testing.T) {

	msg := message.Message{
		Payload: []byte{0xAB, 0xAB},
	}

	err := message.ValidateMessage(msg, 2)

	if err != nil {
		t.Fatalf("valid message was rejected: %v", err)
	}
}

func TestValidateMessageRejectsWrongPayloadSize(t *testing.T) {

	msg := message.Message{
		Payload: []byte{0xAB},
	}

	err := message.ValidateMessage(msg, 2)

	if err == nil {
		t.Fatal("message with wrong payload size was accepted")
	}
}

func TestValidateMessageRejectsWrongPayloadContents(t *testing.T) {

	msg := message.Message{
		Payload: []byte{0xAB, 0x00},
	}

	err := message.ValidateMessage(msg, 2)

	if err == nil {
		t.Fatal("message with wrong payload contents was accepted")
	}
}
