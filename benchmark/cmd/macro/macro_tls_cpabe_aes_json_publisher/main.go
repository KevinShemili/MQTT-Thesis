package main

import (
	"bufio"
	"fmt"
	"os"

	"thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro"
	"thesis/benchmark/macro/tls_cpabe_aes_json"
	"thesis/internal/cryptography/cpabe"
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

	authority := cpabe.AuthorityFromPublicKeyBytes(cache.Load(cache.CPABEPublicKeyFileName))
	policy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.Cryptography.AttributeCount)

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

				result, err := tls_cpabe_aes_json.RunPublishBenchmark(tls_cpabe_aes_json.TLSCPABEAESPublisherInput{
					Client:       client,
					Config:       config,
					Authority:    authority,
					Policy:       policy,
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

			_, err := tls_cpabe_aes_json.RunPublishBenchmark(tls_cpabe_aes_json.TLSCPABEAESPublisherInput{
				Client:      client,
				Config:      config,
				Authority:   authority,
				Policy:      policy,
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
