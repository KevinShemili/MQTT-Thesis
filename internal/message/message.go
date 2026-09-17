package message

import (
	"bytes"
	"fmt"

	"github.com/google/uuid"
)

type Message struct {
	ID      uuid.UUID
	Payload []byte
}

func NewMessage(payloadSize int) Message {
	messageID := uuid.New()

	return Message{
		ID:      messageID,
		Payload: BuildPayload(payloadSize),
	}
}

func BuildPayload(payloadSize int) []byte {
	return bytes.Repeat([]byte{0xAB}, payloadSize)
}

func ValidateMessage(message Message, expectedPayloadSize int) error {
	if len(message.Payload) != expectedPayloadSize {
		return fmt.Errorf(
			"payload has %d bytes, expected %d",
			len(message.Payload),
			expectedPayloadSize,
		)
	}

	expectedPayload := BuildPayload(expectedPayloadSize)

	if !bytes.Equal(message.Payload, expectedPayload) {
		return fmt.Errorf("payload contents are invalid")
	}

	return nil
}
