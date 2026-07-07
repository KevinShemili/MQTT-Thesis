package envelope

import (
	"encoding/json"

	"github.com/fxamacker/cbor/v2"
)

type Envelope struct {
	ABECiphertext []byte `json:"abeCiphertext" cbor:"abeCiphertext"`
	Nonce         []byte `json:"nonce" cbor:"nonce"`
	AESCiphertext []byte `json:"aesCiphertext" cbor:"aesCiphertext"`
}

// Same, but each field is tagged with a small integer CBOR key
// instead of a string name
type EnvelopeIntKeys struct {
	ABECiphertext []byte `cbor:"0,keyasint"`
	Nonce         []byte `cbor:"1,keyasint"`
	AESCiphertext []byte `cbor:"2,keyasint"`
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

func SerializeCBORKeyAsInt(env EnvelopeIntKeys) []byte {

	data, err := cbor.Marshal(env)
	if err != nil {
		panic(err)
	}

	return data
}

func DeserializeCBORKeyAsInt(data []byte) EnvelopeIntKeys {

	var env EnvelopeIntKeys
	err := cbor.Unmarshal(data, &env)
	if err != nil {
		panic(err)
	}

	return env
}
