package tls_cpabe_aes_json

import (
	"bytes"
	"slices"
	"strconv"
	"testing"
	"time"

	"thesis/benchmark/cpu"
	"thesis/benchmark/macro"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/envelope"
	"thesis/internal/message"
	"thesis/internal/mqtt"
	"thesis/internal/serialization"
)

func TestRunPublishBenchmarkMeasuredCallOrder(t *testing.T) {

	// Arrange
	calls := []string{}

	tokens := []*fakePublishToken{
		{
			calls: &calls,
			index: 1,
		},
		{
			calls: &calls,
			index: 2,
		},
	}

	client := &fakeMQTTClient{
		calls:  &calls,
		tokens: tokens,
	}

	cpuMeasurement := &fakeCPU{
		calls: &calls,
	}

	config := macro.BenchmarkConfig{
		MessageCount:    2,
		PublishInterval: 0,
		Topic:           "test/topic",
	}

	policy, _ := cpabe.BuildSyntheticPolicyAndAttributes(3)
	authority := cpabe.NewAuthority()
	measurements := make([]macro.PublisherMeasurement, config.MessageCount)

	newCPU := func() (cpu.CPU, error) {
		calls = append(calls, "new cpu")
		return cpuMeasurement, nil
	}

	expected := []string{
		"new cpu",
		"enable",
		"publish 1",
		"publish 2",
		"wait 1",
		"wait 2",
		"stop",
	}

	// Act
	result, err := runPublishBenchmark(TLSCPABEAESPublisherInput{
		Client: client,
		Config: macro.MacroConfig{
			Benchmark: config,
			Cryptography: macro.CryptographyConfig{
				SymmetricKeySize: 16,
			},
		},
		Authority:    authority,
		Policy:       policy,
		PayloadSize:  16,
		Measurements: measurements,
		IsWarmup:     false,
	}, newCPU)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if result.Measurements[0].StartTime == 0 {
		t.Fatal("expected publisher timestamp to be recorded")
	}

	if result.Measurements[0].StartTime > client.firstPublishTime {
		t.Fatal("publisher timestamp must precede publishing")
	}

	if result.Cycles != 123 {
		t.Fatalf("expected 123 cycles, got %d", result.Cycles)
	}

	if !slices.Equal(calls, expected) {
		t.Fatalf("unexpected call order:\nexpected: %v\ngot: %v", expected, calls)
	}
}

func TestRunPublishBenchmarkWarmupDoesNotMeasure(t *testing.T) {

	// Arrange
	calls := []string{}

	tokens := []*fakePublishToken{
		{
			calls: &calls,
			index: 1,
		},
	}

	client := &fakeMQTTClient{
		calls:  &calls,
		tokens: tokens,
	}

	config := macro.BenchmarkConfig{
		MessageCount:    1,
		PublishInterval: 0,
		Topic:           "test/topic",
	}

	policy, _ := cpabe.BuildSyntheticPolicyAndAttributes(3)
	authority := cpabe.NewAuthority()

	newCPU := func() (cpu.CPU, error) {
		calls = append(calls, "new cpu")
		return &fakeCPU{calls: &calls}, nil
	}

	expected := []string{
		"publish 1",
		"wait 1",
	}

	// Act
	result, err := runPublishBenchmark(TLSCPABEAESPublisherInput{
		Client: client,
		Config: macro.MacroConfig{
			Benchmark: config,
			Cryptography: macro.CryptographyConfig{
				SymmetricKeySize: 16,
			},
		},
		Authority:   authority,
		Policy:      policy,
		PayloadSize: 16,
		IsWarmup:    true,
	}, newCPU)

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

func TestPublishMessageConstructsDecryptablePayload(t *testing.T) {

	// Arrange
	calls := []string{}

	tokens := []*fakePublishToken{
		{
			calls: &calls,
			index: 1,
		},
	}

	client := &fakeMQTTClient{
		calls:  &calls,
		tokens: tokens,
	}

	config := macro.MacroConfig{
		Benchmark: macro.BenchmarkConfig{
			Topic: "test/topic",
		},
		Cryptography: macro.CryptographyConfig{
			SymmetricKeySize: 16,
		},
	}

	policy, attributes := cpabe.BuildSyntheticPolicyAndAttributes(3)
	authority := cpabe.NewAuthority()
	privateKey := authority.IssuePrivateKey(attributes)

	msg := message.NewMessage(16)
	serializer := serialization.JSONSerializer{}

	// Act
	_, err := publishMessage(TLSCPABEAESPublisherInput{
		Client:    client,
		Config:    config,
		Authority: authority,
		Policy:    policy,
	}, serializer, msg)

	// Assert
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if client.publishedTopic != config.Benchmark.Topic {
		t.Fatalf("expected topic %q, got %q", config.Benchmark.Topic, client.publishedTopic)
	}

	var env envelope.AsymmetricEnvelope

	if err := serializer.Deserialize(client.publishedPayload, &env); err != nil {
		t.Fatalf("failed to deserialize published envelope: %v", err)
	}

	symmetricKey := privateKey.Decrypt(env.AsymmetricCiphertext)
	cipher := aes.NewAES(symmetricKey)
	plaintext := cipher.Decrypt(nil, env.Nonce, env.SymmetricCiphertext)

	var decoded message.Message

	if err := serializer.Deserialize(plaintext, &decoded); err != nil {
		t.Fatalf("failed to deserialize decrypted message: %v", err)
	}

	if decoded.ID != msg.ID {
		t.Fatal("decrypted message must contain the original message ID")
	}

	if !bytes.Equal(decoded.Payload, msg.Payload) {
		t.Fatalf("decrypted payload %q does not match original %q", decoded.Payload, msg.Payload)
	}
}

type fakeCPU struct {
	calls *[]string
}

func (measurement *fakeCPU) Enable() error {

	*measurement.calls = append(*measurement.calls, "enable")
	return nil
}

func (measurement *fakeCPU) Stop() (uint64, error) {

	*measurement.calls = append(*measurement.calls, "stop")
	return 123, nil
}

func (measurement *fakeCPU) Abort() {

	*measurement.calls = append(*measurement.calls, "abort")
}

type fakeMQTTClient struct {
	calls            *[]string
	tokens           []*fakePublishToken
	publishIndex     int
	firstPublishTime int64
	publishedTopic   string
	publishedPayload []byte
}

func (client *fakeMQTTClient) Connect() error {
	return nil
}

func (client *fakeMQTTClient) Subscribe(_ string, _ func(mqtt.MQTTDelivery)) error {
	return nil
}

func (client *fakeMQTTClient) Publish(topic string, payload []byte) mqtt.PublishToken {

	if client.publishIndex == 0 {
		client.firstPublishTime = time.Now().UnixNano()
	}

	client.publishedTopic = topic
	client.publishedPayload = payload

	index := client.publishIndex
	client.publishIndex++

	*client.calls = append(*client.calls, "publish "+strconv.Itoa(index+1))

	return client.tokens[index]
}

func (client *fakeMQTTClient) Disconnect() {
}

type fakePublishToken struct {
	calls *[]string
	index int
}

func (token *fakePublishToken) Wait() bool {

	*token.calls = append(*token.calls, "wait "+strconv.Itoa(token.index))
	return true
}

func (token *fakePublishToken) Error() error {
	return nil
}
