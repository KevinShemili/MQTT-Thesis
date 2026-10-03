package tls_psk_ascon

import (
	"fmt"
	"time"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/envelope"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

type TLSPSKASCONSubscriberInput struct {
	Client       mqtt.Client
	Config       macro.MacroConfig
	Cipher       ascon.ASCON
	Measurements []macro.SubscriberMeasurement
	IsWarmup     bool
}

func RunSubscribeBenchmark(input TLSPSKASCONSubscriberInput, notifyReady func() error) (macro.SubscriberResult, error) {

	return runSubscribeBenchmark(input, notifyReady, cpu.NewCPUPerf)
}

func runSubscribeBenchmark(input TLSPSKASCONSubscriberInput, notifyReady func() error,
	newCPU func() (cpu.CPU, error)) (macro.SubscriberResult, error) {

	if input.IsWarmup {

		err := consumeMessages(input, notifyReady)
		if err != nil {
			return macro.SubscriberResult{}, err
		}

		return macro.SubscriberResult{}, nil
	}

	measurement, err := newCPU()
	if err != nil {
		return macro.SubscriberResult{}, err
	}

	workloadErr := consumeMessages(input, func() error {
		if err := measurement.Enable(); err != nil {
			return err
		}
		return notifyReady()
	})
	if workloadErr != nil {
		measurement.Abort()
		return macro.SubscriberResult{}, workloadErr
	}

	cycles, err := measurement.Stop()
	if err != nil {
		return macro.SubscriberResult{}, err
	}

	return macro.SubscriberResult{
		Measurements: input.Measurements,
		Cycles:       cycles,
	}, nil
}

func consumeMessages(input TLSPSKASCONSubscriberInput, notifyReady func() error) error {

	serializer := serialization.CBORSerializer{}

	messageIndex := 0
	benchmarkResult := make(chan error, 1)

	err := input.Client.Subscribe(input.Config.Benchmark.Topic, func(delivery mqtt.MQTTDelivery) {

		if input.IsWarmup {

			_, err := consumeMessage(input, serializer, delivery)
			if err != nil {
				benchmarkResult <- err
				return
			}

			messageIndex++
			if messageIndex == input.Config.Benchmark.MessageCount {
				benchmarkResult <- nil
			}
			return
		}

		msg, err := consumeMessage(input, serializer, delivery)
		if err != nil {
			benchmarkResult <- err
			return
		}

		endTime := time.Now().UnixNano()

		input.Measurements[messageIndex] = macro.SubscriberMeasurement{
			MessageID: msg.ID,
			EndTime:   endTime,
		}

		messageIndex++
		if messageIndex == input.Config.Benchmark.MessageCount {
			benchmarkResult <- nil
		}
	})
	if err != nil {
		return err
	}

	if err := notifyReady(); err != nil {
		return fmt.Errorf("notify subscriber ready: %w", err)
	}

	if err := <-benchmarkResult; err != nil {
		return err
	}

	return nil
}

func consumeMessage(input TLSPSKASCONSubscriberInput, serializer serialization.CBORSerializer, delivery mqtt.MQTTDelivery) (message.Message, error) {

	var env envelope.SymmetricEnvelope

	if err := serializer.Deserialize(delivery.Payload, &env); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received envelope: %w", err)
	}

	plaintext := input.Cipher.Decrypt(nil, env.Nonce, env.Ciphertext)

	var msg message.Message

	if err := serializer.Deserialize(plaintext, &msg); err != nil {
		return message.Message{}, fmt.Errorf("deserialize received message: %w", err)
	}

	return msg, nil
}
