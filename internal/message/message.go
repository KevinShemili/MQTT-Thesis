package message

import (
	"bytes"

	"github.com/google/uuid"
)

type Message struct {
	ID      uuid.UUID `json:"id" cbor:"id"`
	Payload []byte    `json:"payload" cbor:"payload"`
}

type MessageIntKeys struct {
	ID      uuid.UUID `cbor:"0,keyasint"`
	Payload []byte    `cbor:"1,keyasint"`
}

func NewMessage(payloadSize int) Message {
	messageID := uuid.New()

	return Message{
		ID:      messageID,
		Payload: BuildPayload(payloadSize),
	}
}

func NewMessageIntKeys(payloadSize int) MessageIntKeys {
	messageID := uuid.New()

	return MessageIntKeys{
		ID:      messageID,
		Payload: BuildPayload(payloadSize),
	}
}

func BuildPayload(payloadSize int) []byte {
	return bytes.Repeat([]byte{0xAB}, payloadSize)
}
