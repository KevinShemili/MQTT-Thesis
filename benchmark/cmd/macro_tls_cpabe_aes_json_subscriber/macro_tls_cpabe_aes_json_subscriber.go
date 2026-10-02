package main

import (
	"bufio"
	"fmt"
	"os"

	"thesis/benchmark/cache"
	"thesis/benchmark/macro/shared"
	"thesis/benchmark/macro/tls_cpabe_aes_json"
	"thesis/benchmark/memory"
	"thesis/benchmark/utility"
	"thesis/benchmark/utility/csv"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/mqtt"
)

type subscriberDependencies struct {
	connect      func() error
	disconnect   func()
	readSignal   func(string) error
	writeSignal  func(string) error
	runBenchmark func(payloadIndex int, run int, isWarmup bool, onReady func() error) error
	writeResults func() error
}

func main() {

	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}
}

func run() error {

	config := shared.NewMacroConfig()

	privateKey := cpabe.PrivateKeyFromBytes(cache.Load(shared.CPABEPrivateKeyFileName))

	tlsConfig, err := mqtt.NewTLSConfig(config.MQTT.CACertificate, config.MQTT.BrokerURL)
	if err != nil {
		return err
	}

	client := mqtt.NewClient(mqtt.ClientConfig{
		BrokerURL: config.MQTT.BrokerURL,
		ClientID:  config.MQTT.SubscriberClientID,
		Username:  config.MQTT.SubscriberUsername,
		Password:  config.MQTT.SubscriberPassword,
		TLSConfig: tlsConfig,
	})

	results := make([]shared.SubscriberResult, len(config.Benchmark.PayloadSizes)*config.Benchmark.Runs)
	measurements := make([]shared.SubscriberMeasurement, len(config.Benchmark.PayloadSizes)*config.Benchmark.Runs*config.Benchmark.MessageCount)

	// Touch memory once
	memory.TouchMemory(measurements)

	// Assign the pre-allocated memory to results
	for run := range results {

		start := run * config.Benchmark.MessageCount
		end := start + config.Benchmark.MessageCount

		results[run].Measurements = measurements[start:end]
	}

	startSignal := bufio.NewReader(os.Stdin)

	dependencies := subscriberDependencies{
		connect:    client.Connect,
		disconnect: client.Disconnect,
		readSignal: func(expected string) error {
			return utility.ReadSignal(startSignal, expected)
		},
		writeSignal: func(signal string) error {
			return utility.WriteSignal(os.Stdout, signal)
		},
		runBenchmark: func(payloadIndex int, run int, isWarmup bool, onReady func() error) error {

			if !isWarmup {

				resultIndex := payloadIndex*config.Benchmark.Runs + run - config.Benchmark.WarmupRuns

				result, err := tls_cpabe_aes_json.RunSubscribeBenchmark(tls_cpabe_aes_json.TLSCPABEAESSubscriberInput{
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

			_, err := tls_cpabe_aes_json.RunSubscribeBenchmark(tls_cpabe_aes_json.TLSCPABEAESSubscriberInput{
				Client:     client,
				Config:     config,
				PrivateKey: privateKey,
				IsWarmup:   true,
			}, onReady)

			return err
		},

		writeResults: func() error {
			return csv.WriteSubscriberResults(results, config.Benchmark)
		},
	}

	return runSubscriber(config.Benchmark, dependencies)
}

func runSubscriber(config shared.BenchmarkConfig, dependencies subscriberDependencies) error {

	if err := dependencies.connect(); err != nil {
		return err
	}

	for payloadIndex := range config.PayloadSizes {

		for run := 0; run < config.WarmupRuns+config.Runs; run++ {

			if err := dependencies.readSignal("GO"); err != nil {
				return err
			}

			isWarmup := run < config.WarmupRuns

			if err := dependencies.runBenchmark(payloadIndex, run, isWarmup, func() error {
				return dependencies.writeSignal("READY")
			},
			); err != nil {
				return err
			}

			if err := dependencies.writeSignal("DONE"); err != nil {
				return err
			}
		}
	}

	if err := dependencies.readSignal("FINISH"); err != nil {
		return err
	}

	dependencies.disconnect()
	return dependencies.writeResults()
}
