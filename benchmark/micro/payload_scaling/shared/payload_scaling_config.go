package shared

import "benchmark/utility"

type PayloadScalingConfig struct {
	PayloadSizes   []int
	AESKeySize     int
	AttributeCount int
	RSAKeyBits     int
}

func LoadPayloadScalingConfig() PayloadScalingConfig {

	return PayloadScalingConfig{
		PayloadSizes: utility.ParseIntListFromEnv(
			"PAYLOAD_SCALING_PAYLOAD_SIZES",
		),
		AESKeySize: utility.ParseIntFromEnv(
			"PAYLOAD_SCALING_AES_KEY_SIZE",
		),
		AttributeCount: utility.ParseIntFromEnv(
			"PAYLOAD_SCALING_ATTRIBUTE_COUNT",
		),
		RSAKeyBits: utility.ParseIntFromEnv(
			"PAYLOAD_SCALING_RSA_KEY_BITS",
		),
	}
}
