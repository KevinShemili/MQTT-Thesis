package thermal

import (
	"benchmark/utility"
	"log"
	"os"
	"strconv"
	"strings"
	"time"
)

// File that exposes the CPU temperature
const thermalSensorPath = "/sys/class/thermal/thermal_zone0/temp"

// Amount of time we wait (5 minutes)
const cooldownTimeout = 5 * time.Minute

// Polling interval (5 seconds)
const cooldownPollInterval = 5 * time.Second

// Convert reading to celsius (from millidegrees)
const millidegreesPerDegree = 1000.0

var temperatureThreshold = utility.ParseIntFromEnv("TEMPERATURE_THRESHOLD")

func WaitForCooldown() {

	temperature, isAvailable := readCPUTemperature()

	if !isAvailable || temperature < float64(temperatureThreshold) {
		return
	}

	log.Printf("Cooling Down From: %.1f°C... Waiting for Below: %d°C...\n", temperature, temperatureThreshold)

	deadline := time.Now().Add(cooldownTimeout)
	for time.Now().Before(deadline) {

		// Do not hammer sensor
		time.Sleep(cooldownPollInterval)

		temperature, _ := readCPUTemperature()

		if temperature < float64(temperatureThreshold) {
			log.Printf("Cooled Down To: %.1f°C\n", temperature)
			return
		}
	}

	log.Printf("Cooldown Timed Out At: %.1f°C... Continuing:\n", temperature)
}

func readCPUTemperature() (float64, bool) {

	rawValue, err := os.ReadFile(thermalSensorPath)
	if err != nil {
		return 0, false
	}

	millidegrees, err := strconv.Atoi(strings.TrimSpace(string(rawValue)))
	if err != nil {
		log.Printf("Error parsing thermal sensor reading: %v\n", err)
		return 0, false
	}

	return float64(millidegrees) / millidegreesPerDegree, true
}
