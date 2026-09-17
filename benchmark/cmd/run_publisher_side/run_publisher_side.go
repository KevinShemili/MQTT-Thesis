package main

import (
	"fmt"
	"os"
	"thesis/benchmark/macro"
	"thesis/benchmark/macro/shared"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

func main() {

	mqttConfig := shared.NewMQTTConfig()
	experimentConfig := shared.NewExperimentConfig()

	tlsConfig, err := mqtt.NewTLSConfig(
		mqttConfig.CACertificate,
		mqttConfig.BrokerURL,
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}

	client := mqtt.NewClient(mqtt.ClientConfig{
		BrokerURL: mqttConfig.BrokerURL,
		ClientID:  mqttConfig.PublisherClientID,
		Username:  mqttConfig.PublisherUsername,
		Password:  mqttConfig.PublisherPassword,
		TLSConfig: tlsConfig,
	})

	err = macro.ExecutePublishBenchmark(
		client,
		serialization.JSONSerializer{},
		experimentConfig,
		os.Stdout,
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}
}
