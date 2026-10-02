package main

import (
	"bufio"
	"fmt"
	"os"

	"thesis/benchmark/cache"
	cmdshared "thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro/shared"
	"thesis/benchmark/macro/tls_psk_aes"
	"thesis/benchmark/utility"
	"thesis/benchmark/utility/csv"
	"thesis/internal/cryptography/aes"
)

func main() {

	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}
}

func run() error {

	config := shared.NewMacroConfig()

	cipher := aes.NewAES(cache.Load(shared.AESKeyFileName))

	client, err := cmdshared.NewPublisherClient(config.MQTT)
	if err != nil {
		return err
	}

	results := cmdshared.PreparePublisherResults(config.Benchmark)

	startSignal := bufio.NewReader(os.Stdin)

	dependencies := cmdshared.PublisherDependencies{
		Connect:    client.Connect,
		Disconnect: client.Disconnect,
		ReadSignal: func(expected string) error {
			return utility.ReadSignal(startSignal, expected)
		},
		WriteSignal: func(signal string) error {
			return utility.WriteSignal(os.Stdout, signal)
		},
		RunBenchmark: func(payloadIndex int, payloadSize int, run int, isWarmup bool) error {

			if !isWarmup {

				resultIndex := payloadIndex*config.Benchmark.Runs + run - config.Benchmark.WarmupRuns

				result, err := tls_psk_aes.RunPublishBenchmark(tls_psk_aes.TLSPSKAESPublisherInput{
					Client:       client,
					Config:       config,
					Cipher:       cipher,
					PayloadSize:  payloadSize,
					Measurements: results[resultIndex].Measurements,
					IsWarmup:     false,
				})
				if err != nil {
					return err
				}

				results[resultIndex] = result

				return nil
			}

			_, err := tls_psk_aes.RunPublishBenchmark(tls_psk_aes.TLSPSKAESPublisherInput{
				Client:      client,
				Config:      config,
				Cipher:      cipher,
				PayloadSize: payloadSize,
				IsWarmup:    true,
			})
			return err
		},

		WriteResults: func() error {
			return csv.WritePublisherResults(results, config.Benchmark)
		},
	}

	return cmdshared.RunPublisher(config.Benchmark, dependencies)
}
