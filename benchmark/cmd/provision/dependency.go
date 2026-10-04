package provision

type Dependency struct {
	Store func(string, []byte)
}
