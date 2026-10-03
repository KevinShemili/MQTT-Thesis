package macro

import (
	"thesis/utility/golang/parser"
	"time"
)

type MacroConfig struct {
	Benchmark    BenchmarkConfig
	MQTT         MQTTConfig
	Cryptography CryptographyConfig
}

type BenchmarkConfig struct {
	PayloadSizes    []int
	MessageCount    int
	PublishInterval time.Duration
	Topic           string
	Runs            int
	WarmupRuns      int
}

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

type CryptographyConfig struct {
	SymmetricKeySize int
	RSAKeyBits       int
	AttributeCount   int
}

func NewMacroConfig() MacroConfig {
	return MacroConfig{
		Benchmark:    NewBenchmarkConfig(),
		MQTT:         NewMQTTConfig(),
		Cryptography: NewCryptographyConfig(),
	}
}

func NewBenchmarkConfig() BenchmarkConfig {
	return BenchmarkConfig{
		PayloadSizes: parser.ParseIntListFromEnv("MACRO_PAYLOAD_SIZES"),
		MessageCount: parser.ParseIntFromEnv("MACRO_MESSAGE_COUNT"),
		PublishInterval: time.Duration(
			parser.ParseIntFromEnv("MACRO_PUBLISH_INTERVAL_MILLISECONDS"),
		) * time.Millisecond,
		Topic:      parser.ParseStringFromEnv("MACRO_BENCHMARK_TOPIC"),
		Runs:       parser.ParseIntFromEnv("MACRO_RUNS"),
		WarmupRuns: parser.ParseIntFromEnv("MACRO_WARMUP_RUNS"),
	}
}

func NewMQTTConfig() MQTTConfig {
	return MQTTConfig{
		BrokerURL:          parser.ParseStringFromEnv("MACRO_BROKER_URL"),
		CACertificate:      parser.ParseStringFromEnv("MACRO_CA_CERTIFICATE"),
		PublisherUsername:  parser.ParseStringFromEnv("MACRO_PUBLISHER_USERNAME"),
		PublisherPassword:  parser.ParseStringFromEnv("MACRO_PUBLISHER_PASSWORD"),
		PublisherClientID:  parser.ParseStringFromEnv("MACRO_PUBLISHER_CLIENT_ID"),
		SubscriberUsername: parser.ParseStringFromEnv("MACRO_SUBSCRIBER_USERNAME"),
		SubscriberPassword: parser.ParseStringFromEnv("MACRO_SUBSCRIBER_PASSWORD"),
		SubscriberClientID: parser.ParseStringFromEnv("MACRO_SUBSCRIBER_CLIENT_ID"),
	}
}

func NewCryptographyConfig() CryptographyConfig {
	return CryptographyConfig{
		SymmetricKeySize: parser.ParseIntFromEnv("SYMMETRIC_KEY_SIZE"),
		RSAKeyBits:       parser.ParseIntFromEnv("MACRO_RSA_KEY_BITS"),
		AttributeCount:   parser.ParseIntFromEnv("MACRO_ATTRIBUTE_COUNT"),
	}
}
