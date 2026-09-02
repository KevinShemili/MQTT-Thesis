package shared

import (
	"benchmark/utility"
)

type AttributeKeyScalingConfig struct {
	AttributeCounts  []int
	SubscriberCounts []int
	RSAKeyBits       []int
	FixedRSAKeyBits  int
	AESKeySize       int
}

func NewAttributeKeyScalingConfig() AttributeKeyScalingConfig {

	return AttributeKeyScalingConfig{
		AttributeCounts: utility.ParseIntListFromEnv(
			"ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT",
		),
		SubscriberCounts: utility.ParseIntListFromEnv(
			"ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT",
		),
		RSAKeyBits: utility.ParseIntListFromEnv(
			"ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES",
		),
		FixedRSAKeyBits: utility.ParseIntFromEnv(
			"ATTRIBUTE_KEY_SCALING_FIXED_RSA_KEY_SIZE",
		),
		AESKeySize: utility.ParseIntFromEnv(
			"ATTRIBUTE_KEY_SCALING_AES_KEY_SIZE",
		),
	}
}
