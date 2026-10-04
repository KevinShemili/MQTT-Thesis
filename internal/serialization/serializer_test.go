package serialization

import (
	"bytes"
	"testing"

	"thesis/internal/message"

	"github.com/google/uuid"
)

func TestJSONSerializerRoundTrip(t *testing.T) {

	// Arrange
	original := message.Message{
		ID:      uuid.MustParse("b9961566-8504-4a98-bbbe-cba09c5ee7cb"),
		Payload: []byte("test payload"),
	}
	serializer := JSONSerializer{}
	var decoded message.Message

	// Act
	serialized, err := serializer.Serialize(original)
	if err != nil {
		t.Fatal(err)
	}

	if err := serializer.Deserialize(serialized, &decoded); err != nil {
		t.Fatal(err)
	}

	// Assert
	if decoded.ID != original.ID {
		t.Fatalf("decoded ID %s does not match original %s", decoded.ID, original.ID)
	}

	if !bytes.Equal(decoded.Payload, original.Payload) {
		t.Fatalf("decoded payload %q does not match original %q", decoded.Payload, original.Payload)
	}
}

func TestCBORSerializerRoundTrip(t *testing.T) {

	// Arrange
	original := message.Message{
		ID:      uuid.MustParse("b9961566-8504-4a98-bbbe-cba09c5ee7cb"),
		Payload: []byte("test payload"),
	}
	serializer := CBORSerializer{}
	var decoded message.Message

	// Act
	serialized, err := serializer.Serialize(original)
	if err != nil {
		t.Fatal(err)
	}

	if err := serializer.Deserialize(serialized, &decoded); err != nil {
		t.Fatal(err)
	}

	// Assert
	if decoded.ID != original.ID {
		t.Fatalf("decoded ID %s does not match original %s", decoded.ID, original.ID)
	}

	if !bytes.Equal(decoded.Payload, original.Payload) {
		t.Fatalf("decoded payload %q does not match original %q", decoded.Payload, original.Payload)
	}
}

func TestIntegerKeyCBORSerializerRoundTrip(t *testing.T) {

	// Arrange
	original := message.MessageIntKeys{
		ID:      uuid.MustParse("b9961566-8504-4a98-bbbe-cba09c5ee7cb"),
		Payload: []byte("test payload"),
	}
	serializer := CBORSerializer{}
	var decoded message.MessageIntKeys

	// Act
	serialized, err := serializer.Serialize(original)
	if err != nil {
		t.Fatal(err)
	}

	if err := serializer.Deserialize(serialized, &decoded); err != nil {
		t.Fatal(err)
	}

	// Assert
	if decoded.ID != original.ID {
		t.Fatalf("decoded ID %s does not match original %s", decoded.ID, original.ID)
	}

	if !bytes.Equal(decoded.Payload, original.Payload) {
		t.Fatalf("decoded payload %q does not match original %q", decoded.Payload, original.Payload)
	}
}
