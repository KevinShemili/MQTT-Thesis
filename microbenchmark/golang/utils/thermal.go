package utils

import (
	"log"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

const thermalSensorPath = "/sys/class/thermal/thermal_zone0/temp"
const millidegreesPerDegree = 1000.0
const cooldownPollInterval = 5 * time.Second

// vcgencmd prints a bitmask, ex. "throttled=0x50005". Bits 1, 2 and 3 are the state at
// the moment of the read: ARM frequency capped, currently throttled, soft temperature
// limit active. Bits 17, 18 and 19 are those same three conditions latched since boot,
// which the firmware never clears. Under-voltage, bits 0 and 16, is not thermal
const throttleLiveMask = 0xE
const throttleStickyMask = 0xE0000

func ReadCPUTemperature() (float64, bool) {

	rawValue, err := os.ReadFile(thermalSensorPath)
	if err != nil {
		return 0, false
	}

	millidegrees, err := strconv.Atoi(strings.TrimSpace(string(rawValue)))
	if err != nil {
		return 0, false
	}

	return float64(millidegrees) / millidegreesPerDegree, true
}

func WaitForCooldown(thresholdCelsius int, timeout time.Duration) {

	temperature, available := ReadCPUTemperature()

	if !available || temperature < float64(thresholdCelsius) {
		return
	}

	log.Printf(
		"Cooling down from %.1f°C, waiting for below %d°C...\n",
		temperature,
		thresholdCelsius,
	)

	deadline := time.Now().Add(timeout)

	for time.Now().Before(deadline) {

		time.Sleep(cooldownPollInterval)

		temperature, available = ReadCPUTemperature()

		if !available {
			return
		}

		if temperature < float64(thresholdCelsius) {
			log.Printf("Cooled down to %.1f°C\n", temperature)
			return
		}
	}

	log.Printf("Cooldown timed out at %.1f°C, continuing\n", temperature)
}

// The throttle state at one point in time, kept so that a later read can be compared against it
type ThrottleWatch struct {
	flags     uint64
	available bool
}

func WatchThrottling() ThrottleWatch {

	flags, available := readThrottleFlags()

	return ThrottleWatch{flags: flags, available: available}
}

// Whether the firmware throttled since the watch was taken, as 1 or 0 ready for
// b.ReportMetric, and whether a reading was available at all.
//
// The sticky bits accumulate since boot, so a case owns only the bits that appeared
// while it ran. The live bits cover a case that was already being throttled when it
// started, which sets no new sticky bit and would otherwise pass as clean
func (watch ThrottleWatch) Throttled() (float64, bool) {

	flags, available := readThrottleFlags()

	if !watch.available || !available {
		return 0, false
	}

	appeared := (flags &^ watch.flags) & throttleStickyMask
	live := (watch.flags | flags) & throttleLiveMask

	if appeared|live == 0 {
		return 0, true
	}

	return 1, true
}

// Unavailable wherever vcgencmd does not exist, ex. a development laptop, so that the
// caller omits the metric instead of reporting a zero it cannot stand behind
func readThrottleFlags() (uint64, bool) {

	output, err := exec.Command("vcgencmd", "get_throttled").Output()
	if err != nil {
		return 0, false
	}

	// "throttled=0x50005"
	_, hexDigits, found := strings.Cut(strings.TrimSpace(string(output)), "=0x")
	if !found {
		return 0, false
	}

	flags, err := strconv.ParseUint(hexDigits, 16, 64)
	if err != nil {
		return 0, false
	}

	return flags, true
}
