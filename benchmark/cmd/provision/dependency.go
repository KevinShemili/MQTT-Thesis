package provision

type Dependency struct {
	GenerateRandomBytes func(int) []byte
	Store               func(string, []byte)
}
