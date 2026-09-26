package cpu

import (
	"bufio"
	"bytes"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"
)

type CPUPerf struct {
	command       *exec.Cmd
	controlWriter *os.File
	ackReader     *bufio.Reader
	ackFile       *os.File
	output        bytes.Buffer
}

var _ CPU = (*CPUPerf)(nil)

func NewCPUPerf() (CPU, error) {

	controlReader, controlWriter, err := os.Pipe()
	if err != nil {
		return nil, err
	}

	ackReader, ackWriter, err := os.Pipe()
	if err != nil {
		controlReader.Close()
		controlWriter.Close()
		return nil, err
	}

	measurement := &CPUPerf{
		controlWriter: controlWriter,
		ackReader:     bufio.NewReader(ackReader),
		ackFile:       ackReader,
	}

	measurement.command = exec.Command(
		"/usr/bin/perf",
		"stat",
		"--delay=-1",
		"--event=cycles",
		"--field-separator=,",
		"--control=fd:3,4",
		"--pid="+strconv.Itoa(os.Getpid()),
	)

	measurement.command.ExtraFiles = []*os.File{
		controlReader,
		ackWriter,
	}

	measurement.command.Stderr = &measurement.output

	if err := measurement.command.Start(); err != nil {
		controlReader.Close()
		controlWriter.Close()
		ackReader.Close()
		ackWriter.Close()
		return nil, err
	}

	controlReader.Close()
	ackWriter.Close()

	return measurement, nil
}

func (measurement *CPUPerf) Enable() error {

	return measurement.sendControl("enable")
}

func (measurement *CPUPerf) Stop() (uint64, error) {

	if err := measurement.sendControl("disable"); err != nil {
		measurement.Abort()
		return 0, err
	}

	signalErr := measurement.command.Process.Signal(os.Interrupt)
	waitErr := measurement.command.Wait()

	measurement.controlWriter.Close()
	measurement.ackFile.Close()

	if signalErr != nil && !errors.Is(signalErr, os.ErrProcessDone) {
		return 0, fmt.Errorf("stop perf: %w", signalErr)
	}

	if waitErr != nil && !isPerfInterrupt(waitErr) {
		return 0, fmt.Errorf(
			"wait for perf: %w: %s",
			waitErr,
			strings.TrimSpace(measurement.output.String()),
		)
	}

	return parsePerfCycles(measurement.output.String())
}

func (measurement *CPUPerf) Abort() {

	measurement.controlWriter.Close()

	_ = measurement.command.Process.Kill()
	_ = measurement.command.Wait()

	measurement.ackFile.Close()
}

func (measurement *CPUPerf) sendControl(command string) error {

	if _, err := fmt.Fprintln(measurement.controlWriter, command); err != nil {
		return err
	}

	acknowledgement, err := measurement.ackReader.ReadString('\n')
	if err != nil {
		return err
	}

	if strings.TrimSpace(acknowledgement) != "ack" {
		return fmt.Errorf("perf did not acknowledge %s", command)
	}

	return nil
}

func isPerfInterrupt(err error) bool {

	var exitError *exec.ExitError

	if !errors.As(err, &exitError) {
		return false
	}

	// perf may handle SIGINT and exit with 130, or terminate by SIGINT.
	if exitError.ExitCode() == 130 {
		return true
	}

	waitStatus, ok := exitError.Sys().(syscall.WaitStatus)

	return ok &&
		waitStatus.Signaled() &&
		waitStatus.Signal() == syscall.SIGINT
}

func parsePerfCycles(output string) (uint64, error) {

	for _, line := range strings.Split(output, "\n") {

		fields := strings.Split(line, ",")

		if len(fields) < 3 {
			continue
		}

		if strings.TrimSpace(fields[2]) != "cycles" {
			continue
		}

		cycles, err := strconv.ParseUint(
			strings.TrimSpace(fields[0]),
			10,
			64,
		)
		if err != nil {
			return 0, err
		}

		return cycles, nil
	}

	return 0, fmt.Errorf(
		"cycles measurement not found in perf output: %s",
		strings.TrimSpace(output),
	)
}
