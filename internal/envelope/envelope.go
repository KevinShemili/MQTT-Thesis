package envelope

type AsymmetricEnvelope struct {
	AsymmetricCiphertext []byte `json:"asymmetricCiphertext" cbor:"asymmetricCiphertext"`
	Nonce                []byte `json:"nonce" cbor:"nonce"`
	SymmetricCiphertext  []byte `json:"symmetricCiphertext" cbor:"symmetricCiphertext"`
}

type SymmetricEnvelope struct {
	Nonce      []byte `json:"nonce" cbor:"nonce"`
	Ciphertext []byte `json:"ciphertext" cbor:"ciphertext"`
}
