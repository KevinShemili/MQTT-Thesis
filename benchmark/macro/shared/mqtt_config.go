package shared

import (
	"thesis/benchmark/utility"
)

type MQTTConfig struct {
	BrokerURL     string
	CACertificate string

	PublisherUsername string
	PublisherPassword string
	PublisherClientID string

	SubscriberUsername string
	SubscriberPassword string
	SubscriberClientID string
}

func NewMQTTConfig() MQTTConfig {
	return MQTTConfig{
		BrokerURL:          utility.ParseStringFromEnv("MACRO_BROKER_URL"),
		CACertificate:      utility.ParseStringFromEnv("MACRO_CA_CERTIFICATE"),
		PublisherUsername:  utility.ParseStringFromEnv("MACRO_PUBLISHER_USERNAME"),
		PublisherPassword:  utility.ParseStringFromEnv("MACRO_PUBLISHER_PASSWORD"),
		PublisherClientID:  utility.ParseStringFromEnv("MACRO_PUBLISHER_CLIENT_ID"),
		SubscriberUsername: utility.ParseStringFromEnv("MACRO_SUBSCRIBER_USERNAME"),
		SubscriberPassword: utility.ParseStringFromEnv("MACRO_SUBSCRIBER_PASSWORD"),
		SubscriberClientID: utility.ParseStringFromEnv("MACRO_SUBSCRIBER_CLIENT_ID"),
	}
}
