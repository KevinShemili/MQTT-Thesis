package serialization

import "encoding/json"

type JSONSerializer struct{}

var _ ISerializer = JSONSerializer{}

func (JSONSerializer) Serialize(value any) ([]byte, error) {
	return json.Marshal(value)
}

func (JSONSerializer) Deserialize(data []byte, value any) error {
	return json.Unmarshal(data, value)
}
