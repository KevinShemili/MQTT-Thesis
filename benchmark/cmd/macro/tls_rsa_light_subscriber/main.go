package main

import (
	"fmt"
	"os"

	"thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro"
	"thesis/benchmark/macro/tls_rsa_light"
	"thesis/internal/cryptography/rsa"
	"thesis/utility/golang/cache"
)

func main() {

	config := macro.NewMacroConfig()

	rsaScheme := rsa.RSAFromPrivateKeyBytes(cache.Load(cache.RSAPrivateKeyFileName))

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}

	if err := shared.RunSubscriber(config, client, tls_rsa_light.RSALightSubscriberScenario{RSAScheme: rsaScheme},
		os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}
}
