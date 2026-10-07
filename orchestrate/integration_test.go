package main

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"testing"

	"thesis/benchmark/cmd/macro/command"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
	"thesis/utility/golang/cache"
	"thesis/utility/golang/communication"
	"thesis/utility/golang/generator"

	"github.com/testcontainers/testcontainers-go"
	"github.com/testcontainers/testcontainers-go/wait"
)

var broker *Broker

func TestMain(m *testing.M) {

	// Setup broker before any tests
	var err error
	broker, err = StartBroker(context.Background())
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	// Run all tests
	exitCode := m.Run()

	// Cleanup broker after tests
	if err := broker.Close(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		exitCode = 1
	}
	os.Exit(exitCode)
}

func TestMacroTLSIntegration(t *testing.T) {

	// Arrange
	setup := setupMacroIntegration(t)

	// Act
	go func() {
		err := command.ExecuteTLSPublisher(setup.readFromTestPublisher, setup.writeToTestPublisher)
		setup.readFromTestPublisher.Close()
		setup.writeToTestPublisher.Close()
		setup.publisherDone <- err
	}()
	go func() {
		err := command.ExecuteTLSSubscriber(setup.readFromTestSubscriber, setup.writeToTestSubscriber)
		setup.readFromTestSubscriber.Close()
		setup.writeToTestSubscriber.Close()
		setup.subscriberDone <- err
	}()

	// Orchestrator coordinates
	if err := runCommunicationSignals(setup.communication); err != nil {
		t.Fatalf("orchestrate warmup: %v", err)
	}

	// Finish signal to publisher and subscriber
	if err := setup.communication.WritePublisher("FINISH"); err != nil {
		t.Fatalf("finish publisher: %v", err)
	}
	if err := setup.communication.WriteSubscriber("FINISH"); err != nil {
		t.Fatalf("finish subscriber: %v", err)
	}

	// Block until goroutines return
	publisherErr := <-setup.publisherDone
	subscriberErr := <-setup.subscriberDone

	// Assert
	if publisherErr != nil {
		t.Fatalf("expected publisher to return no error, got %v", publisherErr)
	}
	if subscriberErr != nil {
		t.Fatalf("expected subscriber to return no error, got %v", subscriberErr)
	}
	if _, err := os.Stat("publisher.csv"); err != nil {
		t.Fatalf("expected publisher.csv to exist, got %v", err)
	}
	if _, err := os.Stat("subscriber.csv"); err != nil {
		t.Fatalf("expected subscriber.csv to exist, got %v", err)
	}
}

func TestMacroTLSLightIntegration(t *testing.T) {

	// Arrange
	setup := setupMacroIntegration(t)

	// Act
	go func() {
		err := command.ExecuteTLSLightPublisher(setup.readFromTestPublisher, setup.writeToTestPublisher)
		setup.readFromTestPublisher.Close()
		setup.writeToTestPublisher.Close()
		setup.publisherDone <- err
	}()
	go func() {
		err := command.ExecuteTLSLightSubscriber(setup.readFromTestSubscriber, setup.writeToTestSubscriber)
		setup.readFromTestSubscriber.Close()
		setup.writeToTestSubscriber.Close()
		setup.subscriberDone <- err
	}()

	if err := runCommunicationSignals(setup.communication); err != nil {
		t.Fatalf("orchestrate warmup: %v", err)
	}
	if err := setup.communication.WritePublisher("FINISH"); err != nil {
		t.Fatalf("finish publisher: %v", err)
	}
	if err := setup.communication.WriteSubscriber("FINISH"); err != nil {
		t.Fatalf("finish subscriber: %v", err)
	}
	publisherErr := <-setup.publisherDone
	subscriberErr := <-setup.subscriberDone

	// Assert
	if publisherErr != nil {
		t.Fatalf("expected publisher to return no error, got %v", publisherErr)
	}
	if subscriberErr != nil {
		t.Fatalf("expected subscriber to return no error, got %v", subscriberErr)
	}
	if _, err := os.Stat("publisher.csv"); err != nil {
		t.Fatalf("expected publisher.csv to exist, got %v", err)
	}
	if _, err := os.Stat("subscriber.csv"); err != nil {
		t.Fatalf("expected subscriber.csv to exist, got %v", err)
	}
}

func TestMacroPSKIntegration(t *testing.T) {

	// Arrange
	setup := setupMacroIntegration(t)

	cache.Store(cache.AESKeyFileName, generator.GenerateRandomBytes(16))

	// Act
	go func() {
		err := command.ExecutePSKPublisher(setup.readFromTestPublisher, setup.writeToTestPublisher)
		setup.readFromTestPublisher.Close()
		setup.writeToTestPublisher.Close()
		setup.publisherDone <- err
	}()
	go func() {
		err := command.ExecutePSKSubscriber(setup.readFromTestSubscriber, setup.writeToTestSubscriber)
		setup.readFromTestSubscriber.Close()
		setup.writeToTestSubscriber.Close()
		setup.subscriberDone <- err
	}()

	if err := runCommunicationSignals(setup.communication); err != nil {
		t.Fatalf("orchestrate warmup: %v", err)
	}
	if err := setup.communication.WritePublisher("FINISH"); err != nil {
		t.Fatalf("finish publisher: %v", err)
	}
	if err := setup.communication.WriteSubscriber("FINISH"); err != nil {
		t.Fatalf("finish subscriber: %v", err)
	}
	publisherErr := <-setup.publisherDone
	subscriberErr := <-setup.subscriberDone

	// Assert
	if publisherErr != nil {
		t.Fatalf("expected publisher to return no error, got %v", publisherErr)
	}
	if subscriberErr != nil {
		t.Fatalf("expected subscriber to return no error, got %v", subscriberErr)
	}
	if _, err := os.Stat("publisher.csv"); err != nil {
		t.Fatalf("expected publisher.csv to exist, got %v", err)
	}
	if _, err := os.Stat("subscriber.csv"); err != nil {
		t.Fatalf("expected subscriber.csv to exist, got %v", err)
	}
}

func TestMacroPSKLightIntegration(t *testing.T) {

	// Arrange
	setup := setupMacroIntegration(t)

	cache.Store(cache.ASCONKeyFileName, generator.GenerateRandomBytes(16))

	// Act
	go func() {
		err := command.ExecutePSKLightPublisher(setup.readFromTestPublisher, setup.writeToTestPublisher)
		setup.readFromTestPublisher.Close()
		setup.writeToTestPublisher.Close()
		setup.publisherDone <- err
	}()
	go func() {
		err := command.ExecutePSKLightSubscriber(setup.readFromTestSubscriber, setup.writeToTestSubscriber)
		setup.readFromTestSubscriber.Close()
		setup.writeToTestSubscriber.Close()
		setup.subscriberDone <- err
	}()

	if err := runCommunicationSignals(setup.communication); err != nil {
		t.Fatalf("orchestrate warmup: %v", err)
	}
	if err := setup.communication.WritePublisher("FINISH"); err != nil {
		t.Fatalf("finish publisher: %v", err)
	}
	if err := setup.communication.WriteSubscriber("FINISH"); err != nil {
		t.Fatalf("finish subscriber: %v", err)
	}
	publisherErr := <-setup.publisherDone
	subscriberErr := <-setup.subscriberDone

	// Assert
	if publisherErr != nil {
		t.Fatalf("expected publisher to return no error, got %v", publisherErr)
	}
	if subscriberErr != nil {
		t.Fatalf("expected subscriber to return no error, got %v", subscriberErr)
	}
	if _, err := os.Stat("publisher.csv"); err != nil {
		t.Fatalf("expected publisher.csv to exist, got %v", err)
	}
	if _, err := os.Stat("subscriber.csv"); err != nil {
		t.Fatalf("expected subscriber.csv to exist, got %v", err)
	}
}

func TestMacroRSAIntegration(t *testing.T) {

	// Arrange
	setup := setupMacroIntegration(t)

	rsaScheme := rsa.NewRSA(2048)
	cache.Store(cache.RSAPublicKeyFileName, rsaScheme.PublicKeyBytes())
	cache.Store(cache.RSAPrivateKeyFileName, rsaScheme.PrivateKeyBytes())

	// Act
	go func() {
		err := command.ExecuteRSAPublisher(setup.readFromTestPublisher, setup.writeToTestPublisher)
		setup.readFromTestPublisher.Close()
		setup.writeToTestPublisher.Close()
		setup.publisherDone <- err
	}()
	go func() {
		err := command.ExecuteRSASubscriber(setup.readFromTestSubscriber, setup.writeToTestSubscriber)
		setup.readFromTestSubscriber.Close()
		setup.writeToTestSubscriber.Close()
		setup.subscriberDone <- err
	}()

	if err := runCommunicationSignals(setup.communication); err != nil {
		t.Fatalf("orchestrate warmup: %v", err)
	}
	if err := setup.communication.WritePublisher("FINISH"); err != nil {
		t.Fatalf("finish publisher: %v", err)
	}
	if err := setup.communication.WriteSubscriber("FINISH"); err != nil {
		t.Fatalf("finish subscriber: %v", err)
	}
	publisherErr := <-setup.publisherDone
	subscriberErr := <-setup.subscriberDone

	// Assert
	if publisherErr != nil {
		t.Fatalf("expected publisher to return no error, got %v", publisherErr)
	}
	if subscriberErr != nil {
		t.Fatalf("expected subscriber to return no error, got %v", subscriberErr)
	}
	if _, err := os.Stat("publisher.csv"); err != nil {
		t.Fatalf("expected publisher.csv to exist, got %v", err)
	}
	if _, err := os.Stat("subscriber.csv"); err != nil {
		t.Fatalf("expected subscriber.csv to exist, got %v", err)
	}
}

func TestMacroRSALightIntegration(t *testing.T) {

	// Arrange
	setup := setupMacroIntegration(t)

	rsaScheme := rsa.NewRSA(2048)
	cache.Store(cache.RSAPublicKeyFileName, rsaScheme.PublicKeyBytes())
	cache.Store(cache.RSAPrivateKeyFileName, rsaScheme.PrivateKeyBytes())

	// Act
	go func() {
		err := command.ExecuteRSALightPublisher(setup.readFromTestPublisher, setup.writeToTestPublisher)
		setup.readFromTestPublisher.Close()
		setup.writeToTestPublisher.Close()
		setup.publisherDone <- err
	}()
	go func() {
		err := command.ExecuteRSALightSubscriber(setup.readFromTestSubscriber, setup.writeToTestSubscriber)
		setup.readFromTestSubscriber.Close()
		setup.writeToTestSubscriber.Close()
		setup.subscriberDone <- err
	}()

	if err := runCommunicationSignals(setup.communication); err != nil {
		t.Fatalf("orchestrate warmup: %v", err)
	}
	if err := setup.communication.WritePublisher("FINISH"); err != nil {
		t.Fatalf("finish publisher: %v", err)
	}
	if err := setup.communication.WriteSubscriber("FINISH"); err != nil {
		t.Fatalf("finish subscriber: %v", err)
	}
	publisherErr := <-setup.publisherDone
	subscriberErr := <-setup.subscriberDone

	// Assert
	if publisherErr != nil {
		t.Fatalf("expected publisher to return no error, got %v", publisherErr)
	}
	if subscriberErr != nil {
		t.Fatalf("expected subscriber to return no error, got %v", subscriberErr)
	}
	if _, err := os.Stat("publisher.csv"); err != nil {
		t.Fatalf("expected publisher.csv to exist, got %v", err)
	}
	if _, err := os.Stat("subscriber.csv"); err != nil {
		t.Fatalf("expected subscriber.csv to exist, got %v", err)
	}
}

func TestMacroCPABEIntegration(t *testing.T) {

	// Arrange
	setup := setupMacroIntegration(t)

	authority := cpabe.NewAuthority()
	_, attributes := cpabe.BuildSyntheticPolicyAndAttributes(1)
	privateKey := authority.IssuePrivateKey(attributes)
	cache.Store(cache.CPABEPublicKeyFileName, authority.PublicKeyBytes())
	cache.Store(cache.CPABEPrivateKeyFileName, privateKey.Bytes())

	// Act
	go func() {
		err := command.ExecuteCPABEPublisher(setup.readFromTestPublisher, setup.writeToTestPublisher)
		setup.readFromTestPublisher.Close()
		setup.writeToTestPublisher.Close()
		setup.publisherDone <- err
	}()
	go func() {
		err := command.ExecuteCPABESubscriber(setup.readFromTestSubscriber, setup.writeToTestSubscriber)
		setup.readFromTestSubscriber.Close()
		setup.writeToTestSubscriber.Close()
		setup.subscriberDone <- err
	}()

	if err := runCommunicationSignals(setup.communication); err != nil {
		t.Fatalf("orchestrate warmup: %v", err)
	}
	if err := setup.communication.WritePublisher("FINISH"); err != nil {
		t.Fatalf("finish publisher: %v", err)
	}
	if err := setup.communication.WriteSubscriber("FINISH"); err != nil {
		t.Fatalf("finish subscriber: %v", err)
	}
	publisherErr := <-setup.publisherDone
	subscriberErr := <-setup.subscriberDone

	// Assert
	if publisherErr != nil {
		t.Fatalf("expected publisher to return no error, got %v", publisherErr)
	}
	if subscriberErr != nil {
		t.Fatalf("expected subscriber to return no error, got %v", subscriberErr)
	}
	if _, err := os.Stat("publisher.csv"); err != nil {
		t.Fatalf("expected publisher.csv to exist, got %v", err)
	}
	if _, err := os.Stat("subscriber.csv"); err != nil {
		t.Fatalf("expected subscriber.csv to exist, got %v", err)
	}
}

func TestMacroCPABELightIntegration(t *testing.T) {

	// Arrange
	setup := setupMacroIntegration(t)

	authority := cpabe.NewAuthority()
	_, attributes := cpabe.BuildSyntheticPolicyAndAttributes(1)
	privateKey := authority.IssuePrivateKey(attributes)
	cache.Store(cache.CPABEPublicKeyFileName, authority.PublicKeyBytes())
	cache.Store(cache.CPABEPrivateKeyFileName, privateKey.Bytes())

	// Act
	go func() {
		err := command.ExecuteCPABELightPublisher(setup.readFromTestPublisher, setup.writeToTestPublisher)
		setup.readFromTestPublisher.Close()
		setup.writeToTestPublisher.Close()
		setup.publisherDone <- err
	}()
	go func() {
		err := command.ExecuteCPABELightSubscriber(setup.readFromTestSubscriber, setup.writeToTestSubscriber)
		setup.readFromTestSubscriber.Close()
		setup.writeToTestSubscriber.Close()
		setup.subscriberDone <- err
	}()

	if err := runCommunicationSignals(setup.communication); err != nil {
		t.Fatalf("orchestrate warmup: %v", err)
	}
	if err := setup.communication.WritePublisher("FINISH"); err != nil {
		t.Fatalf("finish publisher: %v", err)
	}
	if err := setup.communication.WriteSubscriber("FINISH"); err != nil {
		t.Fatalf("finish subscriber: %v", err)
	}
	publisherErr := <-setup.publisherDone
	subscriberErr := <-setup.subscriberDone

	// Assert
	if publisherErr != nil {
		t.Fatalf("expected publisher to return no error, got %v", publisherErr)
	}
	if subscriberErr != nil {
		t.Fatalf("expected subscriber to return no error, got %v", subscriberErr)
	}
	if _, err := os.Stat("publisher.csv"); err != nil {
		t.Fatalf("expected publisher.csv to exist, got %v", err)
	}
	if _, err := os.Stat("subscriber.csv"); err != nil {
		t.Fatalf("expected subscriber.csv to exist, got %v", err)
	}
}

type macroIntegrationSetup struct {
	readFromTestPublisher  *io.PipeReader
	writeToTestPublisher   *io.PipeWriter
	readFromTestSubscriber *io.PipeReader
	writeToTestSubscriber  *io.PipeWriter
	publisherDone          chan error
	subscriberDone         chan error
	communication          communicationDependency
}

func setupMacroIntegration(t *testing.T) macroIntegrationSetup {
	t.Helper()

	cacheDirectory := t.TempDir()
	resultDirectory := t.TempDir()
	t.Chdir(resultDirectory)

	t.Setenv("MACRO_BROKER_URL", broker.URL)
	t.Setenv("MACRO_CA_CERTIFICATE", broker.CACertificate)
	t.Setenv("MACRO_BENCHMARK_TOPIC", "integration/macro")
	t.Setenv("MACRO_PUBLISHER_USERNAME", "publisher")
	t.Setenv("MACRO_PUBLISHER_PASSWORD", "publisher-password")
	t.Setenv("MACRO_SUBSCRIBER_USERNAME", "subscriber")
	t.Setenv("MACRO_SUBSCRIBER_PASSWORD", "subscriber-password")
	t.Setenv("MACRO_PUBLISHER_CLIENT_ID", "integration-publisher")
	t.Setenv("MACRO_SUBSCRIBER_CLIENT_ID", "integration-subscriber")
	t.Setenv("MACRO_PAYLOAD_SIZES", "16")
	t.Setenv("MACRO_MESSAGE_COUNT", "3")
	t.Setenv("MACRO_PUBLISH_INTERVAL_MILLISECONDS", "0")
	t.Setenv("MACRO_RUNS", "0")
	t.Setenv("MACRO_WARMUP_RUNS", "1") // use warm up to avoid real CPU
	t.Setenv("SYMMETRIC_KEY_SIZE", "16")
	t.Setenv("MACRO_RSA_KEY_BITS", "2048")
	t.Setenv("MACRO_ATTRIBUTE_COUNT", "1")
	t.Setenv("CACHE_DIRECTORY", cacheDirectory)

	// Simulate fake stdin / stdout connections

	// Test writes to publisher -> writeToPublisher
	// Publisher reads from test -> readFromTestPublisher
	readFromTestPublisher, writeToPublisher := io.Pipe()

	// Publisher writes to test -> writeToTestPublisher
	// Test reads from publisher -> readFromPublisher
	readFromPublisher, writeToTestPublisher := io.Pipe()

	// Test writes to subscriber -> writeToSubscriber
	// Subscriber reads from test -> readFromTestSubscriber
	readFromTestSubscriber, writeToSubscriber := io.Pipe()

	// Subscriber writes to test -> writeToTestSubscriber
	// Test reads from subscriber -> readFromSubscriber
	readFromSubscriber, writeToTestSubscriber := io.Pipe()

	t.Cleanup(func() {
		for _, pipe := range []io.Closer{
			readFromTestPublisher, writeToPublisher, readFromPublisher, writeToTestPublisher,
			readFromTestSubscriber, writeToSubscriber, readFromSubscriber, writeToTestSubscriber,
		} {
			pipe.Close()
		}
	})

	publisherSignals := bufio.NewReader(readFromPublisher)
	subscriberSignals := bufio.NewReader(readFromSubscriber)

	return macroIntegrationSetup{
		readFromTestPublisher:  readFromTestPublisher,
		writeToTestPublisher:   writeToTestPublisher,
		readFromTestSubscriber: readFromTestSubscriber,
		writeToTestSubscriber:  writeToTestSubscriber,
		publisherDone:          make(chan error, 1),
		subscriberDone:         make(chan error, 1),
		communication: communicationDependency{
			WritePublisher: func(signal string) error {
				return communication.WriteSignal(writeToPublisher, signal)
			},
			ReadPublisher: func(signal string) error {
				return communication.ReadSignal(publisherSignals, signal)
			},
			WriteSubscriber: func(signal string) error {
				return communication.WriteSignal(writeToSubscriber, signal)
			},
			ReadSubscriber: func(signal string) error {
				return communication.ReadSignal(subscriberSignals, signal)
			},
		},
	}
}

type Broker struct {
	URL           string
	CACertificate string

	container testcontainers.Container
	directory string
}

func StartBroker(ctx context.Context) (_ *Broker, err error) {

	directory, err := os.MkdirTemp("", "macro-integration-")
	if err != nil {
		return nil, err
	}

	broker := &Broker{directory: directory}
	defer func() {
		if err != nil {
			broker.Close()
		}
	}()

	broker.container, err = testcontainers.GenericContainer(ctx, testcontainers.GenericContainerRequest{
		ContainerRequest: testcontainers.ContainerRequest{
			FromDockerfile: testcontainers.FromDockerfile{Context: "../broker"},
			Env: map[string]string{
				"MACRO_BROKER_URL":          "ssl://127.0.0.1:8883",
				"MACRO_BENCHMARK_TOPIC":     "integration/macro",
				"MACRO_PUBLISHER_USERNAME":  "publisher",
				"MACRO_PUBLISHER_PASSWORD":  "publisher-password",
				"MACRO_SUBSCRIBER_USERNAME": "subscriber",
				"MACRO_SUBSCRIBER_PASSWORD": "subscriber-password",
			},
			ExposedPorts: []string{"8883/tcp"},
			WaitingFor:   wait.ForListeningPort("8883/tcp"),
		},
		Started: true,
	})
	if err != nil {
		return nil, fmt.Errorf("start broker: %w", err)
	}

	port, err := broker.container.MappedPort(ctx, "8883/tcp")
	if err != nil {
		return nil, fmt.Errorf("get broker port: %w", err)
	}
	broker.URL = "ssl://127.0.0.1:" + port.Port()

	certificate, err := broker.container.CopyFileFromContainer(ctx, "/state/certs/ca.crt")
	if err != nil {
		return nil, fmt.Errorf("copy broker CA: %w", err)
	}
	defer certificate.Close()

	certificateBytes, err := io.ReadAll(certificate)
	if err != nil {
		return nil, fmt.Errorf("read broker CA: %w", err)
	}
	broker.CACertificate = filepath.Join(directory, "ca.crt")
	if err := os.WriteFile(broker.CACertificate, certificateBytes, 0o644); err != nil {
		return nil, fmt.Errorf("write broker CA: %w", err)
	}

	return broker, nil
}

func (broker *Broker) Close() error {
	return errors.Join(testcontainers.TerminateContainer(broker.container), os.RemoveAll(broker.directory))
}
