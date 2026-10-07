package command

// Extract logic from main.go to enable integration tests to test pipeline
// without having to spawn a new process for each test case

import (
	"io"
	"thesis/benchmark/cmd/macro/shared"
	"thesis/benchmark/macro"
	"thesis/benchmark/macro/tls"
	"thesis/benchmark/macro/tls_cpabe"
	"thesis/benchmark/macro/tls_cpabe_light"
	"thesis/benchmark/macro/tls_light"
	"thesis/benchmark/macro/tls_psk"
	"thesis/benchmark/macro/tls_psk_light"
	"thesis/benchmark/macro/tls_rsa"
	"thesis/benchmark/macro/tls_rsa_light"
	"thesis/internal/cryptography/aes"
	"thesis/internal/cryptography/ascon"
	"thesis/internal/cryptography/cpabe"
	"thesis/internal/cryptography/rsa"
	"thesis/utility/golang/cache"
)

func ExecuteCPABELightPublisher(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	authority := cpabe.AuthorityFromPublicKeyBytes(cache.Load(cache.CPABEPublicKeyFileName))

	policy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.Cryptography.AttributeCount)

	client, err := shared.NewPublisherTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunPublisher(
		config,
		client,
		tls_cpabe_light.CPABELightPublisherScenario{
			Authority: authority,
			Policy:    policy,
		},
		input,
		output,
	)
}

func ExecuteCPABELightSubscriber(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	privateKey := cpabe.PrivateKeyFromBytes(cache.Load(cache.CPABEPrivateKeyFileName))

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunSubscriber(
		config,
		client,
		tls_cpabe_light.CPABELightSubscriberScenario{
			PrivateKey: privateKey,
		},
		input,
		output,
	)
}

func ExecuteCPABEPublisher(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	authority := cpabe.AuthorityFromPublicKeyBytes(cache.Load(cache.CPABEPublicKeyFileName))

	policy, _ := cpabe.BuildSyntheticPolicyAndAttributes(config.Cryptography.AttributeCount)

	client, err := shared.NewPublisherTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunPublisher(
		config,
		client,
		tls_cpabe.CPABEPublisherScenario{
			Authority: authority,
			Policy:    policy,
		},
		input,
		output,
	)
}

func ExecuteCPABESubscriber(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	privateKey := cpabe.PrivateKeyFromBytes(
		cache.Load(cache.CPABEPrivateKeyFileName),
	)

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunSubscriber(
		config,
		client,
		tls_cpabe.CPABESubscriberScenario{
			PrivateKey: privateKey,
		},
		input,
		output,
	)
}

func ExecuteTLSLightPublisher(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	client, err := shared.NewPublisherTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunPublisher(
		config,
		client,
		tls_light.TLSLightPublisherScenario{},
		input,
		output,
	)
}

func ExecuteTLSLightSubscriber(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunSubscriber(
		config,
		client,
		tls_light.TLSLightSubscriberScenario{},
		input,
		output,
	)
}

func ExecutePSKLightPublisher(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	cipher := ascon.NewASCON(cache.Load(cache.ASCONKeyFileName))

	client, err := shared.NewPublisherTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunPublisher(
		config,
		client,
		tls_psk_light.PSKLightPublisherScenario{
			Cipher: cipher,
		},
		input,
		output,
	)
}

func ExecutePSKLightSubscriber(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	cipher := ascon.NewASCON(cache.Load(cache.ASCONKeyFileName))

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunSubscriber(
		config,
		client,
		tls_psk_light.PSKLightSubscriberScenario{
			Cipher: cipher,
		},
		input,
		output,
	)
}
func ExecutePSKPublisher(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	cipher := aes.NewAES(cache.Load(cache.AESKeyFileName))

	client, err := shared.NewPublisherTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunPublisher(
		config,
		client,
		tls_psk.PSKPublisherScenario{
			Cipher: cipher,
		},
		input,
		output,
	)
}

func ExecutePSKSubscriber(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	cipher := aes.NewAES(cache.Load(cache.AESKeyFileName))

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunSubscriber(
		config,
		client,
		tls_psk.PSKSubscriberScenario{
			Cipher: cipher,
		},
		input,
		output,
	)
}

func ExecuteTLSPublisher(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	client, err := shared.NewPublisherTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunPublisher(
		config,
		client,
		tls.TLSPublisherScenario{},
		input,
		output,
	)
}

func ExecuteTLSSubscriber(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunSubscriber(
		config,
		client,
		tls.TLSSubscriberScenario{},
		input,
		output,
	)
}

func ExecuteRSALightPublisher(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	rsaScheme := rsa.RSAFromPublicKeyBytes(cache.Load(cache.RSAPublicKeyFileName))

	client, err := shared.NewPublisherTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunPublisher(
		config,
		client,
		tls_rsa_light.RSALightPublisherScenario{
			RSAScheme: rsaScheme,
		},
		input,
		output,
	)
}

func ExecuteRSALightSubscriber(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	rsaScheme := rsa.RSAFromPrivateKeyBytes(cache.Load(cache.RSAPrivateKeyFileName))

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunSubscriber(
		config,
		client,
		tls_rsa_light.RSALightSubscriberScenario{
			RSAScheme: rsaScheme,
		},
		input,
		output,
	)
}

func ExecuteRSAPublisher(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	rsaScheme := rsa.RSAFromPublicKeyBytes(cache.Load(cache.RSAPublicKeyFileName))

	client, err := shared.NewPublisherTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunPublisher(
		config,
		client,
		tls_rsa.RSAPublisherScenario{
			RSAScheme: rsaScheme,
		},
		input,
		output,
	)
}

func ExecuteRSASubscriber(input io.Reader, output io.Writer) error {

	config := macro.NewMacroConfig()

	rsaScheme := rsa.RSAFromPrivateKeyBytes(cache.Load(cache.RSAPrivateKeyFileName))

	client, err := shared.NewSubscriberTLSClient(config.MQTT)
	if err != nil {
		return err
	}

	return shared.RunSubscriber(
		config,
		client,
		tls_rsa.RSASubscriberScenario{
			RSAScheme: rsaScheme,
		},
		input,
		output,
	)
}
