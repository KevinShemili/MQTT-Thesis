package main

import (
	"bufio"
	"fmt"
	"os"

	"thesis/benchmark/cache"
	"thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro/shared"
	"thesis/benchmark/macro/tls_rsa_aes_json"
	"thesis/benchmark/utility"
	"thesis/benchmark/utility/csv"
	"thesis/internal/cryptography/rsa"
)

func main() {

	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}
}

func run() error {

	config := shared.NewMacroConfig()

	rsaScheme := rsa.RSAFromPrivateKeyBytes(cache.Load(shared.RSAPrivateKeyFileName))

	client, err := commands.NewSubscriberClient(config.MQTT)
	if err != nil {
		return err
	}

	results := commands.PrepareSubscriberResults(config.Benchmark)

	startSignal := bufio.NewReader(os.Stdin)

	dependencies := commands.SubscriberDependencies{
		Connect:    client.Connect,
		Disconnect: client.Disconnect,
		ReadSignal: func(expected string) error {
			return utility.ReadSignal(startSignal, expected)
		},
		WriteSignal: func(signal string) error {
			return utility.WriteSignal(os.Stdout, signal)
		},
		RunBenchmark: func(payloadIndex int, run int, isWarmup bool, onReady func() error) error {

			if !isWarmup {

				resultIndex := payloadIndex*config.Benchmark.Runs + run - config.Benchmark.WarmupRuns

				result, err := tls_rsa_aes_json.RunSubscribeBenchmark(tls_rsa_aes_json.TLSRSAAESSubscriberInput{
					Client:       client,
					Config:       config,
					RSAScheme:    rsaScheme,
					Measurements: results[resultIndex].Measurements,
					IsWarmup:     false,
				}, onReady)
				if err != nil {
					return err
				}

				results[resultIndex] = result

				return nil
			}

			_, err := tls_rsa_aes_json.RunSubscribeBenchmark(tls_rsa_aes_json.TLSRSAAESSubscriberInput{
				Client:    client,
				Config:    config,
				RSAScheme: rsaScheme,
				IsWarmup:  true,
			}, onReady)

			return err
		},

		WriteResults: func() error {
			return csv.WriteSubscriberResults(results, config.Benchmark)
		},
	}

	return commands.RunSubscriber(config.Benchmark, dependencies)
}
