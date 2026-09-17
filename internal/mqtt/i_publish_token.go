package mqtt

type IPublishToken interface {
	Wait() error
}
