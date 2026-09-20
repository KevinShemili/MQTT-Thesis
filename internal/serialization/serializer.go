package serialization

type Serializer interface {
	Serialize(value any) ([]byte, error)
	Deserialize(data []byte, value any) error
}
