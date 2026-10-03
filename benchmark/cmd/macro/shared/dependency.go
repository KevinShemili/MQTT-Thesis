package shared

type PublisherDependency struct {
	Connect      func() error
	Disconnect   func()
	ReadSignal   func(string) error
	WriteSignal  func(string) error
	RunBenchmark func(payloadIndex int, payloadSize int, run int, isWarmup bool) error
	WriteResults func() error
}

type SubscriberDependency struct {
	Connect      func() error
	Disconnect   func()
	ReadSignal   func(string) error
	WriteSignal  func(string) error
	RunBenchmark func(payloadIndex int, run int, isWarmup bool, onReady func() error) error
	WriteResults func() error
}
