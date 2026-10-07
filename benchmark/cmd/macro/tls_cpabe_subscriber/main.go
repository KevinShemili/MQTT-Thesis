package main

import (
	"fmt"
	"os"

	"thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro"
	"thesis/benchmark/macro/tls_cpabe"
	"thesis/internal/cryptography/cpabe"
	"thesis/utility/golang/cache"
)

func main() {

	config := macro.NewMacroConfig()

	privateKey := cpabe.PrivateKeyFromBytes(cache.Load(cache.CPABEPrivateKeyFileName))

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}

	if err := shared.RunSubscriber(config, client, tls_cpabe.CPABESubscriberScenario{PrivateKey: privateKey},
		os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}
}
