package main

import (
	"bufio"
	"fmt"
	"os"

	"thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro"
	"thesis/benchmark/macro/tls_psk_aes"
	"thesis/internal/cryptography/aes"
	"thesis/utility/golang/cache"
	"thesis/utility/golang/communication"
)

func main() {

	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}
}

func run() error {

	config := macro.NewMacroConfig()

	cipher := aes.NewAES(cache.Load(cache.AESKeyFileName))

	client, err := shared.NewPublisherClient(config.MQTT)
	if err != nil {
		return err
	}

	results := shared.PreparePublisherResults(config.Benchmark)

	startSignal := bufio.NewReader(os.Stdin)

	dependencies := shared.PublisherDependency{
		Connect:    client.Connect,
		Disconnect: client.Disconnect,
		ReadSignal: func(expected string) error {
			return communication.ReadSignal(startSignal, expected)
		},
		WriteSignal: func(signal string) error {
			return communication.WriteSignal(os.Stdout, signal)
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
			return shared.WritePublisherResults(results, config.Benchmark)
		},
	}

	return shared.RunPublisher(config.Benchmark, dependencies)
}
