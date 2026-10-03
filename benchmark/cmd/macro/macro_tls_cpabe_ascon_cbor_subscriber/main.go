package main

import (
	"bufio"
	"fmt"
	"os"

	"thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro"
	"thesis/benchmark/macro/tls_cpabe_ascon_cbor"
	"thesis/internal/cryptography/cpabe"
	"thesis/utility/golang/cache"
	"thesis/utility/golang/communication"
)

func main() {

	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}
}

func run() error {

	config := macro.NewMacroConfig()

	privateKey := cpabe.PrivateKeyFromBytes(cache.Load(cache.CPABEPrivateKeyFileName))

	client, err := shared.NewSubscriberClient(config.MQTT)
	if err != nil {
		return err
	}

	results := shared.PrepareSubscriberResults(config.Benchmark)

	startSignal := bufio.NewReader(os.Stdin)

	dependencies := shared.SubscriberDependency{
		Connect:    client.Connect,
		Disconnect: client.Disconnect,
		ReadSignal: func(expected string) error {
			return communication.ReadSignal(startSignal, expected)
		},
		WriteSignal: func(signal string) error {
			return communication.WriteSignal(os.Stdout, signal)
		},
		RunBenchmark: func(payloadIndex int, run int, isWarmup bool, onReady func() error) error {

			if !isWarmup {

				resultIndex := payloadIndex*config.Benchmark.Runs + run - config.Benchmark.WarmupRuns

				result, err := tls_cpabe_ascon_cbor.RunSubscribeBenchmark(tls_cpabe_ascon_cbor.TLSCPABEASCONSubscriberInput{
					Client:       client,
					Config:       config,
					PrivateKey:   privateKey,
					Measurements: results[resultIndex].Measurements,
					IsWarmup:     false,
				}, onReady)
				if err != nil {
					return err
				}

				results[resultIndex] = result

				return nil
			}

			_, err := tls_cpabe_ascon_cbor.RunSubscribeBenchmark(tls_cpabe_ascon_cbor.TLSCPABEASCONSubscriberInput{
				Client:     client,
				Config:     config,
				PrivateKey: privateKey,
				IsWarmup:   true,
			}, onReady)

			return err
		},

		WriteResults: func() error {
			return shared.WriteSubscriberResults(results, config.Benchmark)
		},
	}

	return shared.RunSubscriber(config.Benchmark, dependencies)
}
