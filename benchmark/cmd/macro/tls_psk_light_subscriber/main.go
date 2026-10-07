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

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}

	if err := shared.RunSubscriber(config, client, tls_psk_light.PSKLightSubscriberScenario{Cipher: cipher},
		os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}

}
