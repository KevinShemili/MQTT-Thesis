package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"os"
	"strconv"

	"thesis/benchmark/macro/baseline"
	"thesis/benchmark/macro/shared"
	"thesis/benchmark/utility"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

func main() {

	config := shared.NewExperimentConfig()
	mqttConfig := shared.NewMQTTConfig()
	runs := utility.ParseIntFromEnv("MACRO_RUNS")
	warmupRuns := utility.ParseIntFromEnv("MACRO_WARMUP_RUNS")

	tlsConfig, err := mqtt.NewTLSConfig(mqttConfig.CACertificate, mqttConfig.BrokerURL)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}

	client := mqtt.NewClient(mqtt.ClientConfig{
		BrokerURL: mqttConfig.BrokerURL,
		ClientID:  mqttConfig.PublisherClientID,
		Username:  mqttConfig.PublisherUsername,
		Password:  mqttConfig.PublisherPassword,
		TLSConfig: tlsConfig,
	})

	results := make([]baseline.PublisherResult, runs)
	measurements := make([]baseline.PublisherMeasurement, runs*config.MessageCount)
	warmupMeasurements := make([]baseline.PublisherMeasurement, config.MessageCount)

	// Touch memory once
	touchMemory(measurements)

	// Assign the pre-allocated memory to results
	for run := range results {

		start := run * config.MessageCount
		end := start + config.MessageCount

		results[run].Measurements = measurements[start:end]
	}

	if err := client.Connect(); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}

	// Wait for GO signal from the orchestrator before starting the benchmark
	startSignal := bufio.NewReader(os.Stdin)

	for run := 0; run < warmupRuns+runs; run++ {

		if err := readSignal(startSignal, "GO"); err != nil {
			fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
			os.Exit(1)
		}

		isCPUMeasured := run >= warmupRuns

		if isCPUMeasured {

			results[run-warmupRuns], err = baseline.RunPublishBenchmark(
				client,
				serialization.JSONSerializer{},
				config,
				results[run-warmupRuns].Measurements,
				true,
			)
			if err != nil {
				fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
				os.Exit(1)
			}

		} else {

			if _, err := baseline.RunPublishBenchmark(
				client,
				serialization.JSONSerializer{},
				config,
				warmupMeasurements,
				false,
			); err != nil {
				fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
				os.Exit(1)
			}
		}

		// Tell orchestrator that the benchmark is done
		if _, err := fmt.Fprintln(os.Stdout, "DONE"); err != nil {
			fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
			os.Exit(1)
		}
	}

	// The peer must also finish measuring before disconnect or persistence.
	if err := readSignal(startSignal, "FINISH"); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}
	client.Disconnect()

	if err := writeResults(results); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}
}

func writeResults(results []baseline.PublisherResult) error {
	output, err := os.Create("publisher.csv")
	if err != nil {
		return err
	}
	defer output.Close()

	writer := csv.NewWriter(output)

	writer.Write([]string{
		"repetition",
		"message_id",
		"publisher_started_unix_ns",
		"publisher_cycles",
	})

	for repetition, result := range results {

		for _, measurement := range result.Measurements {

			writer.Write([]string{

				strconv.Itoa(repetition + 1),
				measurement.MessageID.String(),
				strconv.FormatInt(measurement.StartTime, 10),
				strconv.FormatUint(result.Cycles, 10),
			})
		}
	}

	writer.Flush()
	return writer.Error()
}

func touchMemory(measurements []baseline.PublisherMeasurement) {
	for index := range measurements {
		measurements[index].StartTime = -1
	}
}

func readSignal(reader *bufio.Reader, expected string) error {
	signal, err := reader.ReadString('\n')
	if err != nil {
		return err
	}

	if signal != expected+"\n" {
		return fmt.Errorf("expected %s, got %q", expected, signal)
	}

	return nil
}
