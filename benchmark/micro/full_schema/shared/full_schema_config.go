package shared

import "benchmark/utility"

type FullSchemaConfig struct {
	PayloadSizes   []int
	AESKeySize     int
	AttributeCount int
	RSAKeyBits     int
}

func LoadFullSchemaConfig() FullSchemaConfig {

	return FullSchemaConfig{
		PayloadSizes: utility.ParseIntListFromEnv(
			"PAYLOAD_SIZES",
		),
		AESKeySize: utility.ParseIntFromEnv(
			"FULL_SCHEMA_AES_KEY_SIZE",
		),
		AttributeCount: utility.ParseIntFromEnv(
			"FULL_SCHEMA_ATTRIBUTE_COUNT",
		),
		RSAKeyBits: utility.ParseIntFromEnv(
			"FULL_SCHEMA_RSA_KEY_BITS",
		),
	}
}
