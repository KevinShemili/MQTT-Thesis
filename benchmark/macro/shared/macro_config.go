package shared

import (
	"time"

	"thesis/benchmark/utility"
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
		PayloadSizes: utility.ParseIntListFromEnv("MACRO_PAYLOAD_SIZES"),
		MessageCount: utility.ParseIntFromEnv("MACRO_MESSAGE_COUNT"),
		PublishInterval: time.Duration(
			utility.ParseIntFromEnv("MACRO_PUBLISH_INTERVAL_MILLISECONDS"),
		) * time.Millisecond,
		Topic:      utility.ParseStringFromEnv("MACRO_BENCHMARK_TOPIC"),
		Runs:       utility.ParseIntFromEnv("MACRO_RUNS"),
		WarmupRuns: utility.ParseIntFromEnv("MACRO_WARMUP_RUNS"),
	}
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

func NewCryptographyConfig() CryptographyConfig {
	return CryptographyConfig{
		SymmetricKeySize: utility.ParseIntFromEnv("SYMMETRIC_KEY_SIZE"),
		RSAKeyBits:       utility.ParseIntFromEnv("MACRO_RSA_KEY_BITS"),
		AttributeCount:   utility.ParseIntFromEnv("MACRO_ATTRIBUTE_COUNT"),
	}
}
