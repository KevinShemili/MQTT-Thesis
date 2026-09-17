package serialization

type ISerializer interface {
	Serialize(value any) ([]byte, error)

	Deserialize(data []byte, value any) error
}
