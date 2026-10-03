package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path"
	"path/filepath"

	"thesis/benchmark/macro/shared"
	"thesis/benchmark/utility"

	"github.com/joho/godotenv"
)

var (
	payloadSizes        []int
	runs                int
	warmupRuns          int
	resultDirectory     string
	cacheDirectory      string
	publisherTarget     string
	subscriberTarget    string
	publisherDirectory  string
	subscriberDirectory string
)

const remoteGoExecutable = "/usr/local/go/bin/go"
const SSH = "/usr/bin/ssh"
const SCP = "/usr/bin/scp"
const python3 = "python3"

type coordinatorDependencies struct {
	LoadEnvironment    func()
	ProvisionFixtures  func() error
	DistributeFixtures func() error
	DistributeBrokerCA func() error
	BuildBinary        func(target, projectDirectory, executable string) error
	OrchestrateMacro   func(publisherTarget, publisherDirectory, subscriberTarget, subscriberDirectory, publisherExecutable, subscriberExecutable string, repetitions int) error
	TransferResult     func(target, projectDirectory, resultDirectory, filename string) error
	GenerateReport     func() error
}

type signalDependencies struct {
	WritePublisher  func(string) error
	ReadPublisher   func(string) error
	WriteSubscriber func(string) error
	ReadSubscriber  func(string) error
}

type scenario struct {
	name       string
	publisher  string
	subscriber string
}

var scenarios = []scenario{
	{"tls_json", "macro_tls_json_publisher", "macro_tls_json_subscriber"},
	{"tls_cbor", "macro_tls_cbor_publisher", "macro_tls_cbor_subscriber"},
	{"tls_psk_aes", "macro_tls_psk_aes_publisher", "macro_tls_psk_aes_subscriber"},
	{"tls_psk_ascon", "macro_tls_psk_ascon_publisher", "macro_tls_psk_ascon_subscriber"},
	{"tls_rsa_aes_json", "macro_tls_rsa_aes_json_publisher", "macro_tls_rsa_aes_json_subscriber"},
	{"tls_rsa_ascon_cbor", "macro_tls_rsa_ascon_cbor_publisher", "macro_tls_rsa_ascon_cbor_subscriber"},
	{"tls_cpabe_aes_json", "macro_tls_cpabe_aes_json_publisher", "macro_tls_cpabe_aes_json_subscriber"},
	{"tls_cpabe_ascon_cbor", "macro_tls_cpabe_ascon_cbor_publisher", "macro_tls_cpabe_ascon_cbor_subscriber"},
}

func main() {

	dependencies := coordinatorDependencies{
		LoadEnvironment:    loadEnvironmentVariables,
		ProvisionFixtures:  provisionFixtures,
		DistributeFixtures: distributeFixtures,
		DistributeBrokerCA: distributeBrokerCA,
		BuildBinary:        buildBinary,
		OrchestrateMacro:   orchestrateMacro,
		TransferResult:     transferResult,
		GenerateReport:     generateReport,
	}

	if err := runCoordinator(dependencies); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=coordinator error=%q\n", err)
		os.Exit(1)
	}

	fmt.Printf("Finished: %s\n", resultDirectory)
}

func runCoordinator(dependencies coordinatorDependencies) error {

	dependencies.LoadEnvironment()

	if err := dependencies.ProvisionFixtures(); err != nil {
		return err
	}

	if err := dependencies.DistributeFixtures(); err != nil {
		return err
	}

	if err := dependencies.DistributeBrokerCA(); err != nil {
		return err
	}

	for _, scenario := range scenarios {

		if err := dependencies.BuildBinary(publisherTarget, publisherDirectory, scenario.publisher); err != nil {
			return err
		}

		if err := dependencies.BuildBinary(subscriberTarget, subscriberDirectory, scenario.subscriber); err != nil {
			return err
		}

		if err := dependencies.OrchestrateMacro(publisherTarget, publisherDirectory, subscriberTarget, subscriberDirectory, scenario.publisher,
			scenario.subscriber, len(payloadSizes)*(warmupRuns+runs)); err != nil {
			return err
		}

		scenarioDirectory := filepath.Join(resultDirectory, scenario.name)

		if err := os.MkdirAll(scenarioDirectory, utility.DirectoryPermissions); err != nil {
			return err
		}

		if err := dependencies.TransferResult(publisherTarget, publisherDirectory, scenarioDirectory, "publisher.csv"); err != nil {
			return err
		}

		if err := dependencies.TransferResult(subscriberTarget, subscriberDirectory, scenarioDirectory, "subscriber.csv"); err != nil {
			return err
		}
	}

	return dependencies.GenerateReport()
}

func provisionFixtures() error {

	command := exec.Command("go", "run", "./benchmark/cmd/provision/provision_macro")
	command.Stdout = os.Stdout
	command.Stderr = os.Stderr

	return command.Run()
}

func distributeFixtures() error {

	publisherFiles := []string{
		shared.AESKeyFileName,
		shared.ASCONKeyFileName,
		shared.RSAPublicKeyFileName,
		shared.CPABEPublicKeyFileName,
	}

	subscriberFiles := []string{
		shared.AESKeyFileName,
		shared.ASCONKeyFileName,
		shared.RSAPrivateKeyFileName,
		shared.CPABEPrivateKeyFileName,
	}

	if err := copyFixtures(publisherTarget, publisherDirectory, publisherFiles); err != nil {
		return err
	}

	return copyFixtures(subscriberTarget, subscriberDirectory, subscriberFiles)
}

func distributeBrokerCA() error {

	const localCA = "environment/ca.crt"

	copyFromBroker := exec.Command("docker", "cp", "mqtt-thesis-broker:/state/certs/ca.crt", localCA)
	copyFromBroker.Stdout = os.Stdout
	copyFromBroker.Stderr = os.Stderr

	if err := copyFromBroker.Run(); err != nil {
		return err
	}

	targets := []struct {
		target           string
		projectDirectory string
	}{
		{publisherTarget, publisherDirectory},
		{subscriberTarget, subscriberDirectory},
	}

	for _, target := range targets {

		remoteDirectory := path.Join(target.projectDirectory, "environment")

		mkdir := exec.Command(SSH, target.target, "mkdir", "-p", remoteDirectory)
		mkdir.Stdout = os.Stdout
		mkdir.Stderr = os.Stderr

		if err := mkdir.Run(); err != nil {
			return err
		}

		copyCommand := exec.Command(SCP, "-p", localCA, target.target+":"+path.Join(remoteDirectory, "ca.crt"))
		copyCommand.Stdout = os.Stdout
		copyCommand.Stderr = os.Stderr

		if err := copyCommand.Run(); err != nil {
			return err
		}
	}

	return nil
}

func copyFixtures(target, projectDirectory string, files []string) error {

	remoteDirectory := path.Join(projectDirectory, cacheDirectory)

	mkdir := exec.Command(SSH, target, "mkdir", "-p", remoteDirectory)
	mkdir.Stdout = os.Stdout
	mkdir.Stderr = os.Stderr

	if err := mkdir.Run(); err != nil {
		return err
	}

	for _, name := range files {

		copyCommand := exec.Command(SCP, "-p", filepath.Join(cacheDirectory, name), target+":"+path.Join(remoteDirectory, name))
		copyCommand.Stdout = os.Stdout
		copyCommand.Stderr = os.Stderr

		if err := copyCommand.Run(); err != nil {
			return err
		}
	}

	return nil
}

func orchestrateMacro(publisherTarget string, publisherDirectory string, subscriberTarget string, subscriberDirectory string,
	publisherExecutable string, subscriberExecutable string, repetitions int) error {

	subscriber, subscriberInput, subscriberOutput, err := startBenchmark(subscriberTarget, subscriberDirectory, subscriberExecutable)
	if err != nil {
		return err
	}

	publisher, publisherInput, publisherOutput, err := startBenchmark(publisherTarget, publisherDirectory, publisherExecutable)
	if err != nil {
		return err
	}

	signalDependencies := signalDependencies{
		WritePublisher: func(signal string) error {
			return utility.WriteSignal(publisherInput, signal)
		},
		ReadPublisher: func(signal string) error {
			return utility.ReadSignal(publisherOutput, signal)
		},
		WriteSubscriber: func(signal string) error {
			return utility.WriteSignal(subscriberInput, signal)
		},
		ReadSubscriber: func(signal string) error {
			return utility.ReadSignal(subscriberOutput, signal)
		},
	}

	for range repetitions {
		if err := runCommunicationSignals(signalDependencies); err != nil {
			return err
		}
	}

	if err := utility.WriteSignal(publisherInput, "FINISH"); err != nil {
		return err
	}

	if err := utility.WriteSignal(subscriberInput, "FINISH"); err != nil {
		return err
	}

	if err := publisher.Wait(); err != nil {
		return err
	}

	return subscriber.Wait()
}

func runCommunicationSignals(dependencies signalDependencies) error {

	if err := dependencies.WriteSubscriber("GO"); err != nil {
		return err
	}

	if err := dependencies.ReadSubscriber("READY"); err != nil {
		return err
	}

	if err := dependencies.WritePublisher("GO"); err != nil {
		return err
	}

	if err := dependencies.ReadPublisher("DONE"); err != nil {
		return err
	}

	return dependencies.ReadSubscriber("DONE")
}

func loadEnvironmentVariables() {

	if err := godotenv.Overload("environment/benchmark.env"); err != nil {
		panic(err)
	}

	payloadSizes = utility.ParseIntListFromEnv("MACRO_PAYLOAD_SIZES")
	runs = utility.ParseIntFromEnv("MACRO_RUNS")
	warmupRuns = utility.ParseIntFromEnv("MACRO_WARMUP_RUNS")
	resultDirectory = utility.ParseStringFromEnv("MACRO_RESULT_DIR")
	cacheDirectory = utility.ParseStringFromEnv("CACHE_DIRECTORY")
	publisherTarget = utility.ParseStringFromEnv("MACRO_PUBLISHER_SSH_TARGET")
	subscriberTarget = utility.ParseStringFromEnv("MACRO_SUBSCRIBER_SSH_TARGET")
	publisherDirectory = utility.ParseStringFromEnv("MACRO_PUBLISHER_PROJECT_DIR")
	subscriberDirectory = utility.ParseStringFromEnv("MACRO_SUBSCRIBER_PROJECT_DIR")
}

func buildBinary(target, projectDirectory, executable string) error {

	command := exec.Command(
		SSH,
		target,
		fmt.Sprintf(
			"cd %s && %s build -o /tmp/mqtt-thesis-%s ./benchmark/cmd/macro/%s",
			projectDirectory,
			remoteGoExecutable,
			executable,
			executable,
		),
	)

	command.Stdout = os.Stdout
	command.Stderr = os.Stderr

	return command.Run()
}

func startBenchmark(target, projectDirectory, executable string) (*exec.Cmd, io.WriteCloser, *bufio.Reader, error) {

	command := exec.Command(
		SSH,
		"-T",
		target,
		fmt.Sprintf(
			"cd %s && set -a && . %s && set +a && exec /tmp/mqtt-thesis-%s",
			projectDirectory,
			path.Join(projectDirectory, "environment", "benchmark.env"),
			executable,
		),
	)

	input, err := command.StdinPipe()
	if err != nil {
		return nil, nil, nil, err
	}

	output, err := command.StdoutPipe()
	if err != nil {
		return nil, nil, nil, err
	}

	command.Stderr = os.Stderr

	if err := command.Start(); err != nil {
		return nil, nil, nil, err
	}

	return command, input, bufio.NewReader(output), nil
}

func transferResult(target, projectDirectory, resultDirectory, filename string) error {

	remoteFile := path.Join(projectDirectory, filename)
	localFile := filepath.Join(resultDirectory, filename)

	copyCommand := exec.Command(SCP, "-p", target+":"+remoteFile, localFile)
	copyCommand.Stdout = os.Stdout
	copyCommand.Stderr = os.Stderr

	if err := copyCommand.Run(); err != nil {
		return err
	}

	deleteCommand := exec.Command(SSH, target, "rm", remoteFile)
	deleteCommand.Stdout = os.Stdout
	deleteCommand.Stderr = os.Stderr

	return deleteCommand.Run()
}

func generateReport() error {

	command := exec.Command(python3, "-m", "report.analysis.macro_report")
	command.Stdout = os.Stdout
	command.Stderr = os.Stderr

	return command.Run()
}
