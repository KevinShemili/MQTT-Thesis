package mqtt

import (
	"crypto/tls"
	"fmt"

	mqtt "github.com/eclipse/paho.mqtt.golang"
)

const (
	protocolVersion = 4 // MQTT 3.1.1
	qos             = 1
)

type ClientConfig struct {
	BrokerURL string
	ClientID  string
	Username  string
	Password  string
	TLSConfig *tls.Config
}

type Client struct {
	pahoClient mqtt.Client
}

var _ IClient = (*Client)(nil)

func NewClient(cfg ClientConfig) *Client {

	options := mqtt.NewClientOptions().
		AddBroker(cfg.BrokerURL).
		SetClientID(cfg.ClientID).
		SetUsername(cfg.Username).
		SetPassword(cfg.Password).
		SetTLSConfig(cfg.TLSConfig).
		SetProtocolVersion(protocolVersion).
		SetAutoReconnect(false)

	return &Client{
		pahoClient: mqtt.NewClient(options),
	}
}

func (client *Client) Connect() error {
	token := client.pahoClient.Connect()
	token.Wait()

	if err := token.Error(); err != nil {
		return fmt.Errorf("connect to MQTT broker: %w", err)
	}

	return nil
}

func (client *Client) Subscribe(topic string, handler func(MQTTDelivery)) error {
	token := client.pahoClient.Subscribe(topic, qos, func(_ mqtt.Client, message mqtt.Message) {
		handler(MQTTDelivery{
			Topic:     message.Topic(),
			Payload:   message.Payload(),
			Duplicate: message.Duplicate(),
		})
	},
	)

	token.Wait()

	if err := token.Error(); err != nil {
		return fmt.Errorf("subscribe to %s: %w", topic, err)
	}

	return nil
}

func (client *Client) Publish(topic string, payload []byte) IPublishToken {
	return PublishToken{
		token: client.pahoClient.Publish(topic, qos, false, payload),
	}
}

func (client *Client) Disconnect() {
	client.pahoClient.Disconnect(0)
}
