package main

import (
	"fmt"
	"os"

	"thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro"
	"thesis/benchmark/macro/tls_psk_light"
	"thesis/internal/cryptography/ascon"
	"thesis/utility/golang/cache"
)

func main() {

	config := macro.NewMacroConfig()

	cipher := ascon.NewASCON(cache.Load(cache.ASCONKeyFileName))

	client, err := shared.NewPublisherTLSClient(config.MQTT)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}

	if err := shared.RunPublisher(config, client, tls_psk_light.PSKLightPublisherScenario{Cipher: cipher},
		os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}
}
