package main

import (
	"fmt"
	"os"

	"thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro"
	"thesis/benchmark/macro/tls_cpabe_light"
	"thesis/internal/cryptography/cpabe"
	"thesis/utility/golang/cache"
)

func main() {

	config := macro.NewMacroConfig()

	authority := cpabe.AuthorityFromPublicKeyBytes(cache.Load(cache.CPABEPublicKeyFileName))
	policy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.Cryptography.AttributeCount)

	client, err := shared.NewPublisherTLSClient(config.MQTT)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}

	if err := shared.RunPublisher(config, client, tls_cpabe_light.CPABELightPublisherScenario{Authority: authority, Policy: policy},
		os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}
}
