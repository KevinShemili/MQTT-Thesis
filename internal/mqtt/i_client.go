package mqtt

type IClient interface {
	Connect() error
	Subscribe(topic string, handler func(MQTTDelivery)) error
	Publish(topic string, payload []byte)
	Disconnect()
}

type MQTTDelivery struct {
	Topic   string
	Payload []byte
}
