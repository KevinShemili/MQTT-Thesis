package cpabe_rsa

import (
	"thesis/utility/golang/parser"
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
		AttributeCounts: parser.ParseIntListFromEnv(
			"CPABE_RSA_ATTRIBUTE_COUNT",
		),
		SubscriberCounts: parser.ParseIntListFromEnv(
			"CPABE_RSA_SUBSCRIBER_COUNT",
		),
		RSAKeyBits: parser.ParseIntListFromEnv(
			"CPABE_RSA_RSA_KEY_SIZES",
		),
		FixedRSAKeyBits: parser.ParseIntFromEnv(
			"CPABE_RSA_FIXED_RSA_KEY_SIZE",
		),
		AESKeySize: parser.ParseIntFromEnv(
			"SYMMETRIC_KEY_SIZE",
		),
	}
}
