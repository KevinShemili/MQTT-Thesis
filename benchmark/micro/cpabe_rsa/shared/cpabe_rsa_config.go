package shared

import (
	"benchmark/utility"
)

type CPABERSAConfig struct {
	AttributeCounts  []int
	SubscriberCounts []int
	RSAKeyBits       []int
	FixedRSAKeyBits  int
	AESKeySize       int
}

func NewCPABERSAConfig() CPABERSAConfig {

	return CPABERSAConfig{
		AttributeCounts: utility.ParseIntListFromEnv(
			"CPABE_RSA_ATTRIBUTE_COUNT",
		),
		SubscriberCounts: utility.ParseIntListFromEnv(
			"CPABE_RSA_SUBSCRIBER_COUNT",
		),
		RSAKeyBits: utility.ParseIntListFromEnv(
			"CPABE_RSA_RSA_KEY_SIZES",
		),
		FixedRSAKeyBits: utility.ParseIntFromEnv(
			"CPABE_RSA_FIXED_RSA_KEY_SIZE",
		),
		AESKeySize: utility.ParseIntFromEnv(
			"SYMMETRIC_KEY_SIZE",
		),
	}
}
