package tls_cpabe_ascon_cbor

import (
	"fmt"
	"time"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro/shared"
	"thesis/benchmark/utility"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/envelope"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"

	"github.com/cloudflare/circl/abe/cpabe/tkn20"
)

type TLSCPABEASCONPublisherInput struct {
	Client       mqtt.Client
	Config       shared.MacroConfig
	Authority    cpabe.Authority
	Policy       tkn20.Policy
	PayloadSize  int
	Measurements []shared.PublisherMeasurement
	IsWarmup     bool
}

func RunPublishBenchmark(input TLSCPABEASCONPublisherInput) (shared.PublisherResult, error) {

	return runPublishBenchmark(input, cpu.NewCPUPerf)
}

func runPublishBenchmark(input TLSCPABEASCONPublisherInput, newCPU func() (cpu.CPU, error)) (shared.PublisherResult, error) {

	messages := shared.BuildMessages(input.Config.Benchmark.MessageCount, input.PayloadSize)
	serializer := serialization.CBORSerializer{}
	publishTokens := make([]mqtt.PublishToken, input.Config.Benchmark.MessageCount)

	if input.IsWarmup {

		err := publishMessages(input, serializer, messages, publishTokens)
		if err != nil {
			return shared.PublisherResult{}, err
		}

		return shared.PublisherResult{}, nil
	}

	measurement, err := newCPU()
	if err != nil {
		return shared.PublisherResult{}, err
	}

	if err := measurement.Enable(); err != nil {
		measurement.Abort()
		return shared.PublisherResult{}, err
	}

	workloadErr := publishMessages(input, serializer, messages, publishTokens)
	if workloadErr != nil {
		measurement.Abort()
		return shared.PublisherResult{}, workloadErr
	}

	cycles, err := measurement.Stop()
	if err != nil {
		return shared.PublisherResult{}, err
	}

	return shared.PublisherResult{
		Measurements: input.Measurements,
		Cycles:       cycles,
	}, nil
}

func publishMessages(input TLSCPABEASCONPublisherInput, serializer serialization.CBORSerializer, messages []message.Message,
	publishTokens []mqtt.PublishToken) error {

	for messageIndex := range input.Config.Benchmark.MessageCount {

		time.Sleep(input.Config.Benchmark.PublishInterval)

		msg := messages[messageIndex]

		if input.IsWarmup {

			publishToken, err := publishMessage(input, serializer, msg)
			if err != nil {
				return err
			}

			publishTokens[messageIndex] = publishToken
			continue
		}

		startTime := time.Now().UnixNano()

		publishToken, err := publishMessage(input, serializer, msg)
		if err != nil {
			return err
		}

		publishTokens[messageIndex] = publishToken

		input.Measurements[messageIndex] = shared.PublisherMeasurement{
			MessageID: msg.ID,
			StartTime: startTime,
		}
	}

	for messageIndex, publishToken := range publishTokens {

		publishToken.Wait()

		if err := publishToken.Error(); err != nil {
			return fmt.Errorf("publish message %s: %w", messages[messageIndex].ID, err)
		}
	}

	return nil
}

func publishMessage(input TLSCPABEASCONPublisherInput, serializer serialization.CBORSerializer, msg message.Message) (mqtt.PublishToken, error) {

	plaintext, err := serializer.Serialize(msg)
	if err != nil {
		return nil, fmt.Errorf("serialize message %s: %w", msg.ID, err)
	}

	symmetricKey := utility.GenerateRandomBytes(input.Config.Cryptography.SymmetricKeySize)
	cipher := ascon.NewASCON(symmetricKey)
	nonce := utility.GenerateRandomBytes(cipher.NonceSize())
	asymmetricCiphertext := input.Authority.Encrypt(input.Policy, symmetricKey)
	symmetricCiphertext := cipher.Encrypt(nil, nonce, plaintext)

	payload, err := serializer.Serialize(envelope.AsymmetricEnvelope{
		AsymmetricCiphertext: asymmetricCiphertext,
		Nonce:                nonce,
		SymmetricCiphertext:  symmetricCiphertext,
	})
	if err != nil {
		return nil, fmt.Errorf("serialize envelope for message %s: %w", msg.ID, err)
	}

	return input.Client.Publish(input.Config.Benchmark.Topic, payload), nil
}
