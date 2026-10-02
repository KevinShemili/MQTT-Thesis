package cmdshared

type ProvisionDependencies struct {
	GenerateRandomBytes func(int) []byte
	Store               func(string, []byte)
}
