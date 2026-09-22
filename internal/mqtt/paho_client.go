package mqtt

import (
	"crypto/tls"
	"fmt"

	mqtt "github.com/eclipse/paho.mqtt.golang"
)

const (
	protocolVersion = 4 // MQTT 3.1.1
	qos             = 0
)

type ClientConfig struct {
	BrokerURL string
	ClientID  string
	Username  string
	Password  string
	TLSConfig *tls.Config
}

type PahoClient struct {
	pahoClient mqtt.Client
}

var _ Client = (*PahoClient)(nil)

func NewClient(cfg ClientConfig) *PahoClient {

	options := mqtt.NewClientOptions().
		AddBroker(cfg.BrokerURL).
		SetClientID(cfg.ClientID).
		SetUsername(cfg.Username).
		SetPassword(cfg.Password).
		SetTLSConfig(cfg.TLSConfig).
		SetProtocolVersion(protocolVersion).
		SetAutoReconnect(false)

	return &PahoClient{
		pahoClient: mqtt.NewClient(options),
	}
}

func (pahoClient *PahoClient) Connect() error {
	token := pahoClient.pahoClient.Connect()
	token.Wait()

	if err := token.Error(); err != nil {
		return fmt.Errorf("connect to MQTT broker: %w", err)
	}

	return nil
}

func (pahoClient *PahoClient) Subscribe(topic string, handler func(MQTTDelivery)) error {
	token := pahoClient.pahoClient.Subscribe(topic, qos, func(_ mqtt.Client, message mqtt.Message) {
		handler(MQTTDelivery{
			Topic:   message.Topic(),
			Payload: message.Payload(),
		})
	},
	)

	token.Wait()

	if err := token.Error(); err != nil {
		return fmt.Errorf("subscribe to %s: %w", topic, err)
	}

	return nil
}

func (pahoClient *PahoClient) Publish(topic string, payload []byte) PublishToken {
	return pahoClient.pahoClient.Publish(topic, qos, false, payload)
}

func (pahoClient *PahoClient) Disconnect() {
	pahoClient.pahoClient.Disconnect(250)
}
