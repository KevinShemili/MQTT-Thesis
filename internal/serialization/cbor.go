package serialization

import "github.com/fxamacker/cbor/v2"

type CBORSerializer struct{}

var _ ISerializer = CBORSerializer{}

func (CBORSerializer) Serialize(value any) ([]byte, error) {
	return cbor.Marshal(value)
}

func (CBORSerializer) Deserialize(data []byte, value any) error {
	return cbor.Unmarshal(data, value)
}
