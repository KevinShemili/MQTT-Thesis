package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path"
	"path/filepath"

	"thesis/benchmark/utility"

	"github.com/joho/godotenv"
)

var (
	payloadSizes        []int
	runs                int
	warmupRuns          int
	resultDirectory     string
	publisherTarget     string
	subscriberTarget    string
	publisherDirectory  string
	subscriberDirectory string
)

const remoteGoExecutable = "/usr/local/go/bin/go"
const SSH = "/usr/bin/ssh"
const SCP = "/usr/bin/scp"
const python3 = "python3"

func main() {

	loadEnvironmentVariables()

	if err := buildBinary(publisherTarget, publisherDirectory, "macro_publisher"); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=coordinator error=%q\n", err)
		os.Exit(1)
	}

	if err := buildBinary(subscriberTarget, subscriberDirectory, "macro_subscriber"); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=coordinator error=%q\n", err)
		os.Exit(1)
	}

	if err := orchestrateMacro(publisherTarget, publisherDirectory, subscriberTarget, subscriberDirectory, len(payloadSizes)*(warmupRuns+runs)); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=coordinator error=%q\n", err)
		os.Exit(1)
	}

	if err := os.MkdirAll(resultDirectory, utility.DirectoryPermissions); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=coordinator error=%q\n", err)
		os.Exit(1)
	}

	if err := transferResult(publisherTarget, publisherDirectory, resultDirectory, "publisher.csv"); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=coordinator error=%q\n", err)
		os.Exit(1)
	}

	if err := transferResult(
		subscriberTarget,
		subscriberDirectory,
		resultDirectory,
		"subscriber.csv",
	); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=coordinator error=%q\n", err)
		os.Exit(1)
	}

	if err := generateReport(); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=coordinator error=%q\n", err)
		os.Exit(1)
	}

	fmt.Printf("Finished: %s\n", resultDirectory)
}

func orchestrateMacro(publisherTarget string, publisherDirectory string, subscriberTarget string, subscriberDirectory string, repetitions int) error {

	subscriber, subscriberInput, subscriberOutput, err := startBenchmark(
		subscriberTarget,
		subscriberDirectory,
		"macro_subscriber",
	)
	if err != nil {
		return err
	}

	publisher, publisherInput, publisherOutput, err := startBenchmark(
		publisherTarget,
		publisherDirectory,
		"macro_publisher",
	)
	if err != nil {
		return err
	}

	for range repetitions {

		if _, err := fmt.Fprintln(subscriberInput, "GO"); err != nil {
			return err
		}

		if err := readSignal(subscriberOutput, "READY"); err != nil {
			return err
		}

		if _, err := fmt.Fprintln(publisherInput, "GO"); err != nil {
			return err
		}

		if err := readSignal(publisherOutput, "DONE"); err != nil {
			return err
		}

		if err := readSignal(subscriberOutput, "DONE"); err != nil {
			return err
		}
	}

	if _, err := fmt.Fprintln(publisherInput, "FINISH"); err != nil {
		return err
	}

	if _, err := fmt.Fprintln(subscriberInput, "FINISH"); err != nil {
		return err
	}

	if err := publisher.Wait(); err != nil {
		return err
	}

	if err := subscriber.Wait(); err != nil {
		return err
	}

	return nil
}

func loadEnvironmentVariables() {

	if err := godotenv.Overload("environment/benchmark.env"); err != nil {
		panic(err)
	}

	payloadSizes = utility.ParseIntListFromEnv("MACRO_PAYLOAD_SIZES")
	runs = utility.ParseIntFromEnv("MACRO_RUNS")
	warmupRuns = utility.ParseIntFromEnv("MACRO_WARMUP_RUNS")
	resultDirectory = utility.ParseStringFromEnv("MACRO_RESULT_DIR")
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
			"cd %s && %s build -o /tmp/mqtt-thesis-%s ./benchmark/cmd/%s",
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

	copyCommand := exec.Command(
		SCP,
		"-p",
		target+":"+remoteFile,
		localFile,
	)

	copyCommand.Stdout = os.Stdout
	copyCommand.Stderr = os.Stderr

	if err := copyCommand.Run(); err != nil {
		return err
	}

	deleteCommand := exec.Command(
		SSH,
		target,
		"rm",
		remoteFile,
	)

	deleteCommand.Stdout = os.Stdout
	deleteCommand.Stderr = os.Stderr

	return deleteCommand.Run()
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

func generateReport() error {

	command := exec.Command(python3, "-m", "report.analysis.macro_report")
	command.Stdout = os.Stdout
	command.Stderr = os.Stderr

	return command.Run()
}
