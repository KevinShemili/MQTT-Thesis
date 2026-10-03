package tls_cpabe_aes_json

import (
	"fmt"
	"time"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/envelope"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
	"thesis/utility/golang/generator"

	"github.com/cloudflare/circl/abe/cpabe/tkn20"
)

type TLSCPABEAESPublisherInput struct {
	Client       mqtt.Client
	Config       macro.MacroConfig
	Authority    cpabe.Authority
	Policy       tkn20.Policy
	PayloadSize  int
	Measurements []macro.PublisherMeasurement
	IsWarmup     bool
}

func RunPublishBenchmark(input TLSCPABEAESPublisherInput) (macro.PublisherResult, error) {

	return runPublishBenchmark(input, cpu.NewCPUPerf)
}

func runPublishBenchmark(input TLSCPABEAESPublisherInput, newCPU func() (cpu.CPU, error)) (macro.PublisherResult, error) {

	messages := message.BuildMessages(input.Config.Benchmark.MessageCount, input.PayloadSize)
	serializer := serialization.JSONSerializer{}
	publishTokens := make([]mqtt.PublishToken, input.Config.Benchmark.MessageCount)

	if input.IsWarmup {

		err := publishMessages(input, serializer, messages, publishTokens)
		if err != nil {
			return macro.PublisherResult{}, err
		}

		return macro.PublisherResult{}, nil
	}

	measurement, err := newCPU()
	if err != nil {
		return macro.PublisherResult{}, err
	}

	if err := measurement.Enable(); err != nil {
		measurement.Abort()
		return macro.PublisherResult{}, err
	}

	workloadErr := publishMessages(input, serializer, messages, publishTokens)
	if workloadErr != nil {
		measurement.Abort()
		return macro.PublisherResult{}, workloadErr
	}

	cycles, err := measurement.Stop()
	if err != nil {
		return macro.PublisherResult{}, err
	}

	return macro.PublisherResult{
		Measurements: input.Measurements,
		Cycles:       cycles,
	}, nil
}

func publishMessages(input TLSCPABEAESPublisherInput, serializer serialization.JSONSerializer, messages []message.Message,
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

		input.Measurements[messageIndex] = macro.PublisherMeasurement{
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

func publishMessage(input TLSCPABEAESPublisherInput, serializer serialization.JSONSerializer, msg message.Message) (mqtt.PublishToken, error) {

	plaintext, err := serializer.Serialize(msg)
	if err != nil {
		return nil, fmt.Errorf("serialize message %s: %w", msg.ID, err)
	}

	symmetricKey := generator.GenerateRandomBytes(input.Config.Cryptography.SymmetricKeySize)
	cipher := aes.NewAES(symmetricKey)
	nonce := generator.GenerateRandomBytes(cipher.NonceSize())
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
