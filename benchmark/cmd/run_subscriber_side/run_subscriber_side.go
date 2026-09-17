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
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}

	client := mqtt.NewClient(mqtt.ClientConfig{
		BrokerURL: mqttConfig.BrokerURL,
		ClientID:  mqttConfig.SubscriberClientID,
		Username:  mqttConfig.SubscriberUsername,
		Password:  mqttConfig.SubscriberPassword,
		TLSConfig: tlsConfig,
	})

	err = macro.ExecuteSubscribeBenchmark(
		client,
		serialization.JSONSerializer{},
		experimentConfig,
		os.Stdout,
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}
}
