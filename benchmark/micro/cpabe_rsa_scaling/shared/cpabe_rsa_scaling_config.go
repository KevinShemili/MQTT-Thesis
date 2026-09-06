package shared

import (
	"benchmark/utility"
)

type CPABERSAScalingConfig struct {
	AttributeCounts  []int
	SubscriberCounts []int
	RSAKeyBits       []int
	FixedRSAKeyBits  int
	AESKeySize       int
}

func NewCPABERSAScalingConfig() CPABERSAScalingConfig {

	return CPABERSAScalingConfig{
		AttributeCounts: utility.ParseIntListFromEnv(
			"CPABE_RSA_SCALING_ATTRIBUTE_COUNT",
		),
		SubscriberCounts: utility.ParseIntListFromEnv(
			"CPABE_RSA_SCALING_SUBSCRIBER_COUNT",
		),
		RSAKeyBits: utility.ParseIntListFromEnv(
			"CPABE_RSA_SCALING_RSA_KEY_SIZES",
		),
		FixedRSAKeyBits: utility.ParseIntFromEnv(
			"CPABE_RSA_SCALING_FIXED_RSA_KEY_SIZE",
		),
		AESKeySize: utility.ParseIntFromEnv(
			"CPABE_RSA_SCALING_AES_KEY_SIZE",
		),
	}
}
