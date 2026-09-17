package envelope

type Envelope struct {
	AsymmetricCiphertext []byte `json:"asymmetricCiphertext" cbor:"asymmetricCiphertext"`
	Nonce                []byte `json:"nonce" cbor:"nonce"`
	SymmetricCiphertext  []byte `json:"symmetricCiphertext" cbor:"symmetricCiphertext"`
}

// Same, but each field is tagged with a small integer CBOR key
// instead of a string name
type EnvelopeIntKeys struct {
	AsymmetricCiphertext []byte `cbor:"0,keyasint"`
	Nonce                []byte `cbor:"1,keyasint"`
	SymmetricCiphertext  []byte `cbor:"2,keyasint"`
}
