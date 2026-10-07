package main

import (
	"fmt"
	"os"

	"thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro"
	"thesis/benchmark/macro/tls_psk"
	"thesis/internal/cryptography/aes"
	"thesis/utility/golang/cache"
)

func main() {

	config := macro.NewMacroConfig()

	cipher := aes.NewAES(cache.Load(cache.AESKeyFileName))

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}

	if err := shared.RunSubscriber(config, client, tls_psk.PSKSubscriberScenario{Cipher: cipher},
		os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}
}
