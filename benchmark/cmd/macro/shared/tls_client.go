package shared

import (
	"thesis/benchmark/macro"
	"thesis/internal/mqtt"
)

func NewPublisherTLSClient(config macro.MQTTConfig) (*mqtt.PahoClient, error) {

	tlsConfig, err := mqtt.NewTLSConfig(config.CACertificate, config.BrokerURL)
	if err != nil {
		return nil, err
	}

	client := mqtt.NewClient(mqtt.ClientConfig{
		BrokerURL: config.BrokerURL,
		ClientID:  config.PublisherClientID,
		Username:  config.PublisherUsername,
		Password:  config.PublisherPassword,
		TLSConfig: tlsConfig,
	})

	return client, nil
}

func NewSubscriberTLSClient(config macro.MQTTConfig) (*mqtt.PahoClient, error) {

	tlsConfig, err := mqtt.NewTLSConfig(config.CACertificate, config.BrokerURL)
	if err != nil {
		return nil, err
	}

	client := mqtt.NewClient(mqtt.ClientConfig{
		BrokerURL: config.BrokerURL,
		ClientID:  config.SubscriberClientID,
		Username:  config.SubscriberUsername,
		Password:  config.SubscriberPassword,
		TLSConfig: tlsConfig,
	})

	return client, nil
}
