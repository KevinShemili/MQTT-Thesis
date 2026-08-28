package utility

import (
	"os"
	"strconv"
	"strings"
)

const processPeakMemoryResetPath = "/proc/self/clear_refs"
const processStatusPath = "/proc/self/status"
const processPeakMemoryField = "VmHWM:"
const bytesPerKilobyte = 1024

// Resets Linux's peak-memory, preventing therefore memory not considered relevant
// from being counted towards the peak memory reported
func ResetPeakResidentMemory() bool {

	file, err := os.OpenFile(
		processPeakMemoryResetPath,
		os.O_WRONLY,
		0,
	)
	if err != nil {
		return false
	}
	defer file.Close()

	// Writing "5" to /proc/self/clear_refs resets the peak memory counter
	_, err = file.Write([]byte("5"))
	return err == nil
}

// Largest memory use process has reached since the last reset, in bytes
// Return false whenever /proc does not exist (ex. running from windows laptop)
func PeakResidentMemory() (float64, bool) {

	status, err := os.ReadFile(processStatusPath)
	if err != nil {
		return 0, false
	}

	// VmHWM is the kernel's peak resident-memory value for this process
	// Linux exposes something like this:
	//* Name:   benchmark-binary
	//* State:  R (running)
	//* Pid:    4312
	//* PPid:   4201
	//* VmPeak:   235812 kB
	//* VmSize:   235812 kB
	//* VmHWM:     18436 kB
	//* VmRSS:     17120 kB
	//* Threads:  5
	//* ...
	// Hence split it by new line to obtain the VmHWM line,
	// then split it by whitespace to obtain the value in kilobytes
	for line := range strings.SplitSeq(string(status), "\n") {

		// Have we reached line containing 'VmHWM:'?
		if !strings.HasPrefix(line, processPeakMemoryField) {
			continue
		}

		fields := strings.Fields(line)
		if len(fields) < 2 {
			return 0, false
		}

		kilobytes, err := strconv.Atoi(fields[1])
		if err != nil {
			return 0, false
		}

		// From KB to bytes
		return float64(kilobytes * bytesPerKilobyte), true
	}

	return 0, false
}
