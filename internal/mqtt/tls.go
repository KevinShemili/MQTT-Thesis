package mqtt

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"net/url"
	"os"
)

func NewTLSConfig(caCertificatePath, brokerURL string) (*tls.Config, error) {

	// Read the CA certificate file
	certificateBytes, err := os.ReadFile(caCertificatePath)
	if err != nil {
		return nil, fmt.Errorf("read broker CA certificate: %w", err)
	}

	// Create an empty collection of CAs
	rootCertificates := x509.NewCertPool()

	// Add our CA certificate to the trusted collection
	// The broker certificate must be signed by this CA to be accepted
	if !rootCertificates.AppendCertsFromPEM(certificateBytes) {
		return nil, fmt.Errorf("broker CA certificate does not contain a valid PEM certificate")
	}

	// Extract the broker hostname from the MQTT URL. // Example: ssl://mqtt-broker.local:8883 -> mqtt-broker.local
	parsedBrokerURL, err := url.Parse(brokerURL)
	if err != nil || parsedBrokerURL.Scheme != "ssl" || parsedBrokerURL.Hostname() == "" {
		return nil, fmt.Errorf("broker URL must be a valid ssl:// URL")
	}

	return &tls.Config{
		MinVersion: tls.VersionTLS13,
		MaxVersion: tls.VersionTLS13,
		RootCAs:    rootCertificates,
		ServerName: parsedBrokerURL.Hostname(),
	}, nil
}
