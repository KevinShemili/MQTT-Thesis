package main

import (
	"fmt"
	"os"

	"thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro"
	"thesis/benchmark/macro/tls"
)

func main() {

	config := macro.NewMacroConfig()

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}

	if err := shared.RunSubscriber(config, client, tls.TLSSubscriberScenario{},
		os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}
}
