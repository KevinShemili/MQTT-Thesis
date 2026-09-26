package cpu

type CPU interface {
	Enable() error
	Stop() (uint64, error)
	Abort()
}
