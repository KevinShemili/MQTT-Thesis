package envelope

import (
	"encoding/json"

	"github.com/fxamacker/cbor/v2"
)

type Envelope struct {
	ABECiphertext []byte `json:"ABECiphertext" cbor:"ABECiphertext"`
	Nonce         []byte `json:"nonce" cbor:"nonce"`
	AESCiphertext []byte `json:"AESCiphertext" cbor:"AESCiphertext"`
}

func SerializeJSON(env Envelope) []byte {

	data, err := json.Marshal(env)
	if err != nil {
		panic(err)
	}

	return data
}

func DeserializeJSON(data []byte) Envelope {

	var env Envelope
	err := json.Unmarshal(data, &env)
	if err != nil {
		panic(err)
	}

	return env
}

func SerializeCBOR(env Envelope) []byte {

	data, err := cbor.Marshal(env)
	if err != nil {
		panic(err)
	}

	return data
}

func DeserializeCBOR(data []byte) Envelope {

	var env Envelope
	err := cbor.Unmarshal(data, &env)
	if err != nil {
		panic(err)
	}

	return env
}
