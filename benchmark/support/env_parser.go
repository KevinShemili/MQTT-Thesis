package support

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

func ParseIntListFromEnv(envVarName string) []int {
	rawValue := os.Getenv(envVarName)
	rawParts := strings.Split(rawValue, ",")
	values := make([]int, len(rawParts))

	for i, part := range rawParts {
		value, err := strconv.Atoi(strings.TrimSpace(part))
		if err != nil {
			panic(err)
		}
		values[i] = value
	}

	return values
}

func ParseIntFromEnv(envVarName string) int {
	rawValue := os.Getenv(envVarName)
	value, err := strconv.Atoi(strings.TrimSpace(rawValue))
	if err != nil {
		panic(err)
	}
	return value
}

func ParseStringFromEnv(envVarName string) string {

	value := strings.TrimSpace(os.Getenv(envVarName))

	if value == "" {
		panic(fmt.Sprintf("environment variable %s is not set", envVarName))
	}

	return value
}
