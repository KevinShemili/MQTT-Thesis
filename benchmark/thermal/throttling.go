package thermal

import (
	"os/exec"
	"slices"
	"strconv"
	"strings"
)

// Live bits correspond to:
// 3: Soft temp limit
const softTempLimitBit = 3

type ThrottleWatch struct {
	bits string
}

func NewThrottleWatch() ThrottleWatch {

	return ThrottleWatch{
		bits: readThrottleBits(),
	}
}

func (watch ThrottleWatch) IsThrottled() bool {

	currentBits := readThrottleBits()

	if watch.bits == "" || currentBits == "" {
		return false
	}

	// Check whether the soft temp limit was active at the start or end of the benchmark
	return watch.bits[softTempLimitBit] == '1' || currentBits[softTempLimitBit] == '1'
}

func readThrottleBits() string {

	// Read vcgencmd get_throttled
	output, err := exec.Command("/usr/bin/vcgencmd", "get_throttled").Output()
	if err != nil {
		return ""
	}

	// Output has following shape: "throttled=0x50005" -> Cut and obtain only 50005
	_, hexadecimalNumber, _ := strings.Cut(strings.TrimSpace(string(output)), "=0x")

	// Convert hexadecimal to decimal
	decimalNumber, err := strconv.ParseUint(hexadecimalNumber, 16, 64)
	if err != nil {
		return ""
	}

	// Convert decimal to binary
	binaryNumber := strconv.FormatUint(decimalNumber, 2)

	// Add missing leading zeroes so we have 20 bits (5*4)
	// Conversion to binary removes leading zeroes, so we need to add them back
	binaryNumber = strings.Repeat("0", 20-len(binaryNumber)) + binaryNumber

	// In binary convention, 0 starts from right
	// In Go indexing, 0 starts from left
	// Reverse the string, such that array index matches bit number
	bits := []byte(binaryNumber)
	slices.Reverse(bits)

	return string(bits)
}
