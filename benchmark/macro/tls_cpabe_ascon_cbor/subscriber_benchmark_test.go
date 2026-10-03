package tls_cpabe_ascon_cbor

import (
	"slices"
	"testing"
	"time"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/envelope"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
	"thesis/utility/golang/generator"
)

func TestRunSubscribeBenchmarkMeasuredCallOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	payloadSize := 16

	config := macro.BenchmarkConfig{
		MessageCount: 2,
		Topic:        "test/topic",
	}

	messages := message.BuildMessages(config.MessageCount, payloadSize)

	policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(3)
	authority := cpabe.NewAuthority()
	privateKey := authority.IssuePrivateKey(attributes)

	cborSerializer := serialization.CBORSerializer{}

	firstPlaintext, err := cborSerializer.Serialize(messages[0])
	if err != nil {
		t.Fatalf("failed to serialize first message: %v", err)
	}

	firstSymmetricKey := generator.GenerateRandomBytes(16)
	firstCipher := ascon.NewASCON(firstSymmetricKey)
	firstNonce := generator.GenerateRandomBytes(firstCipher.NonceSize())
	firstAsymmetricCiphertext := authority.Encrypt(policy, firstSymmetricKey)
	firstCiphertext := firstCipher.Encrypt(nil, firstNonce, firstPlaintext)

	firstPayload, err := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
		AsymmetricCiphertext: firstAsymmetricCiphertext,
		Nonce:                firstNonce,
		SymmetricCiphertext:  firstCiphertext,
	})
	if err != nil {
		t.Fatalf("failed to serialize first envelope: %v", err)
	}

	secondPlaintext, err := cborSerializer.Serialize(messages[1])
	if err != nil {
		t.Fatalf("failed to serialize second message: %v", err)
	}

	secondSymmetricKey := generator.GenerateRandomBytes(16)
	secondCipher := ascon.NewASCON(secondSymmetricKey)
	secondNonce := generator.GenerateRandomBytes(secondCipher.NonceSize())
	secondAsymmetricCiphertext := authority.Encrypt(policy, secondSymmetricKey)
	secondCiphertext := secondCipher.Encrypt(nil, secondNonce, secondPlaintext)

	secondPayload, err := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
		AsymmetricCiphertext: secondAsymmetricCiphertext,
		Nonce:                secondNonce,
		SymmetricCiphertext:  secondCiphertext,
	})
	if err != nil {
		t.Fatalf("failed to serialize second envelope: %v", err)
	}

	client := &fakeSubscriberMQTTClient{calls: &calls}
	var firstHandlerStart, firstHandlerEnd int64

	cpuMeasurement := &fakeSubscriberCPU{calls: &calls}

	measurements := make([]macro.SubscriberMeasurement, config.MessageCount)

	newCPU := func() (cpu.CPU, error) {
		calls = append(calls, "new cpu")
		return cpuMeasurement, nil
	}

	notifyReady := func() error {

		calls = append(calls, "ready")

		firstHandlerStart = time.Now().UnixNano()

		client.handler(mqtt.MQTTDelivery{
			Payload: firstPayload,
		})

		firstHandlerEnd = time.Now().UnixNano()

		client.handler(mqtt.MQTTDelivery{
			Payload: secondPayload,
		})

		return nil
	}

	expected := []string{
		"new cpu",
		"subscribe",
		"enable",
		"ready",
		"stop",
	}

	// Act
	result, err := runSubscribeBenchmark(TLSCPABEASCONSubscriberInput{
		Client:       client,
		Config:       macro.MacroConfig{Benchmark: config},
		PrivateKey:   privateKey,
		Measurements: measurements,
		IsWarmup:     false,
	}, notifyReady, newCPU)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if measurements[0].EndTime == 0 {
		t.Fatal("expected subscriber timestamp to be recorded")
	}

	if measurements[0].EndTime < firstHandlerStart ||
		measurements[0].EndTime > firstHandlerEnd {
		t.Fatal("subscriber timestamp must be recorded during the MQTT handler")
	}

	if measurements[0].MessageID != messages[0].ID {
		t.Fatal("subscriber measurement must contain the decoded message ID")
	}

	if result.Cycles != 123 {
		t.Fatalf("expected 123 cycles, got %d", result.Cycles)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunSubscribeBenchmarkWarmupDoesNotMeasure(t *testing.T) {

	// Arrange
	calls := []string{}

	payloadSize := 16

	config := macro.BenchmarkConfig{
		MessageCount: 1,
		Topic:        "test/topic",
	}

	messages := message.BuildMessages(config.MessageCount, payloadSize)

	policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(3)
	authority := cpabe.NewAuthority()
	privateKey := authority.IssuePrivateKey(attributes)

	cborSerializer := serialization.CBORSerializer{}

	plaintext, err := cborSerializer.Serialize(messages[0])
	if err != nil {
		t.Fatalf("failed to serialize message: %v", err)
	}

	symmetricKey := generator.GenerateRandomBytes(16)
	cipher := ascon.NewASCON(symmetricKey)
	nonce := generator.GenerateRandomBytes(cipher.NonceSize())
	asymmetricCiphertext := authority.Encrypt(policy, symmetricKey)
	ciphertext := cipher.Encrypt(nil, nonce, plaintext)

	payload, err := cborSerializer.Serialize(envelope.AsymmetricEnvelope{
		AsymmetricCiphertext: asymmetricCiphertext,
		Nonce:                nonce,
		SymmetricCiphertext:  ciphertext,
	})
	if err != nil {
		t.Fatalf("failed to serialize envelope: %v", err)
	}

	client := &fakeSubscriberMQTTClient{calls: &calls}

	newCPU := func() (cpu.CPU, error) {
		calls = append(calls, "new cpu")
		return &fakeSubscriberCPU{calls: &calls}, nil
	}

	notifyReady := func() error {

		calls = append(calls, "ready")

		client.handler(mqtt.MQTTDelivery{
			Payload: payload,
		})

		return nil
	}

	expected := []string{
		"subscribe",
		"ready",
	}

	// Act
	result, err := runSubscribeBenchmark(TLSCPABEASCONSubscriberInput{
		Client:     client,
		Config:     macro.MacroConfig{Benchmark: config},
		PrivateKey: privateKey,
		IsWarmup:   true,
	}, notifyReady, newCPU)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(result.Measurements) != 0 {
		t.Fatal("warmup must not return measurements")
	}

	if result.Cycles != 0 {
		t.Fatal("warmup must not return CPU cycles")
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

type fakeSubscriberCPU struct {
	calls *[]string
}

func (measurement *fakeSubscriberCPU) Enable() error {

	*measurement.calls = append(
		*measurement.calls,
		"enable",
	)

	return nil
}

func (measurement *fakeSubscriberCPU) Stop() (uint64, error) {

	*measurement.calls = append(
		*measurement.calls,
		"stop",
	)

	return 123, nil
}

func (measurement *fakeSubscriberCPU) Abort() {

	*measurement.calls = append(
		*measurement.calls,
		"abort",
	)
}

type fakeSubscriberMQTTClient struct {
	calls   *[]string
	handler func(mqtt.MQTTDelivery)
}

func (client *fakeSubscriberMQTTClient) Connect() error {
	return nil
}

func (client *fakeSubscriberMQTTClient) Subscribe(
	_ string,
	handler func(mqtt.MQTTDelivery),
) error {

	*client.calls = append(
		*client.calls,
		"subscribe",
	)

	client.handler = handler

	return nil
}

func (client *fakeSubscriberMQTTClient) Publish(
	_ string,
	_ []byte,
) mqtt.PublishToken {
	return nil
}

func (client *fakeSubscriberMQTTClient) Disconnect() {
}
