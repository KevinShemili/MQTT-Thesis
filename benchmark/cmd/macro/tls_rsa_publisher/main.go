package main

import (
	"fmt"
	"os"

	"thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro"
	"thesis/benchmark/macro/tls_rsa"
	"thesis/internal/cryptography/rsa"
	"thesis/utility/golang/cache"
)

func main() {

	config := macro.NewMacroConfig()

	rsaScheme := rsa.RSAFromPublicKeyBytes(cache.Load(cache.RSAPublicKeyFileName))

	client, err := shared.NewPublisherTLSClient(config.MQTT)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}

	if err := shared.RunPublisher(config, client, tls_rsa.RSAPublisherScenario{RSAScheme: rsaScheme},
		os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}
}
