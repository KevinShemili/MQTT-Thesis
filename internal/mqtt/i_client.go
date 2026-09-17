package mqtt

type IClient interface {
	Connect() error
	Subscribe(topic string, handler func(MQTTDelivery)) error
	Publish(topic string, payload []byte) IPublishToken
	Disconnect()
}

type MQTTDelivery struct {
	Topic     string
	Payload   []byte
	Duplicate bool
}
