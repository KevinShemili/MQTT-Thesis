package mqtt

type Client interface {
	Connect() error
	Subscribe(topic string, handler func(MQTTDelivery)) error
	Publish(topic string, payload []byte) PublishToken
	Disconnect()
}

type PublishToken interface {
	Wait() bool
	Error() error
}

type MQTTDelivery struct {
	Topic   string
	Payload []byte
}
