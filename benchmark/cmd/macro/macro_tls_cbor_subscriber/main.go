package main

import (
	"bufio"
	"fmt"
	"os"

	cmdshared "thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro/shared"
	"thesis/benchmark/macro/tls_cbor"
	"thesis/benchmark/utility"
	"thesis/benchmark/utility/csv"
)

func main() {

	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}
}

func run() error {

	config := shared.NewMacroConfig()

	client, err := cmdshared.NewSubscriberClient(config.MQTT)
	if err != nil {
		return err
	}

	results := cmdshared.PrepareSubscriberResults(config.Benchmark)

	startSignal := bufio.NewReader(os.Stdin)

	dependencies := cmdshared.SubscriberDependencies{
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

				result, err := tls_cbor.RunSubscribeBenchmark(tls_cbor.TLSCBORSubscriberInput{
					Client:       client,
					Config:       config,
					Measurements: results[resultIndex].Measurements,
					IsWarmup:     false,
				}, onReady)
				if err != nil {
					return err
				}

				results[resultIndex] = result

				return nil
			}

			_, err := tls_cbor.RunSubscribeBenchmark(tls_cbor.TLSCBORSubscriberInput{
				Client:   client,
				Config:   config,
				IsWarmup: true,
			}, onReady)

			return err
		},

		WriteResults: func() error {
			return csv.WriteSubscriberResults(results, config.Benchmark)
		},
	}

	return cmdshared.RunSubscriber(config.Benchmark, dependencies)
}
