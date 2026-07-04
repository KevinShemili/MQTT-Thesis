package envelope

import (
	"encoding/json"

	"github.com/fxamacker/cbor/v2"
)

// Envelope bundles the CP-ABE protected session key with the AES-GCM protected payload for one MQTT message.
type Envelope struct {
	CpAbeCiphertext []byte `json:"cpAbeCiphertext" cbor:"cpAbeCiphertext"`
	Nonce           []byte `json:"nonce" cbor:"nonce"`
	Ciphertext      []byte `json:"ciphertext" cbor:"ciphertext"`
}

// SerializeJson marshals the envelope into JSON bytes; []byte fields are base64-encoded by encoding/json by default.
func SerializeJson(env Envelope) []byte {
	var data []byte
	var err error

	data, err = json.Marshal(env)
	if err != nil {
		panic(err)
	}

	return data
}

// DeserializeJson unmarshals JSON bytes back into an Envelope.
func DeserializeJson(data []byte) Envelope {
	var env Envelope
	var err error = json.Unmarshal(data, &env)
	if err != nil {
		panic(err)
	}

	return env
}

// SerializeCbor marshals the envelope into CBOR bytes; []byte fields are encoded natively, no base64 expansion.
func SerializeCbor(env Envelope) []byte {
	var data []byte
	var err error

	data, err = cbor.Marshal(env)
	if err != nil {
		panic(err)
	}

	return data
}

// DeserializeCbor unmarshals CBOR bytes back into an Envelope.
func DeserializeCbor(data []byte) Envelope {
	var env Envelope
	var err error = cbor.Unmarshal(data, &env)
	if err != nil {
		panic(err)
	}

	return env
}
