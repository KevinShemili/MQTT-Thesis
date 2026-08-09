package utils

import (
	"log"
	"os"
	"strconv"
	"strings"
	"time"
)

const thermalSensorPath = "/sys/class/thermal/thermal_zone0/temp"
const millidegreesPerDegree = 1000.0
const cooldownPollInterval = 5 * time.Second

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
