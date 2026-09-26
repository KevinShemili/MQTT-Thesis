package mqtt

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"encoding/pem"
	"math/big"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestNewTLSConfig(t *testing.T) {

	certificatePath, certificatePEM := createTestCACertificate(t)

	config, err := NewTLSConfig(
		certificatePath,
		"ssl://mqtt-broker.example:8883",
	)
	if err != nil {
		t.Fatal(err)
	}

	if config.MinVersion != tls.VersionTLS13 {
		t.Fatal("minimum TLS version is not TLS 1.3")
	}

	if config.MaxVersion != tls.VersionTLS13 {
		t.Fatal("maximum TLS version is not TLS 1.3")
	}

	if config.ServerName != "mqtt-broker.example" {
		t.Fatalf("server name is %q", config.ServerName)
	}

	expectedRoots := x509.NewCertPool()
	expectedRoots.AppendCertsFromPEM(certificatePEM)

	if !config.RootCAs.Equal(expectedRoots) {
		t.Fatal("configured CA certificate was not loaded")
	}
}

func TestNewTLSConfigRejectsNonSSLURL(t *testing.T) {

	certificatePath, _ := createTestCACertificate(t)

	_, err := NewTLSConfig(
		certificatePath,
		"tcp://mqtt-broker.example:1883",
	)

	if err == nil {
		t.Fatal("non-SSL broker URL was accepted")
	}
}

func createTestCACertificate(t *testing.T) (string, []byte) {

	privateKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}

	certificate := x509.Certificate{
		SerialNumber:          big.NewInt(1),
		NotBefore:             time.Now().Add(-time.Hour),
		NotAfter:              time.Now().Add(time.Hour),
		IsCA:                  true,
		BasicConstraintsValid: true,
		KeyUsage:              x509.KeyUsageCertSign,
	}

	certificateBytes, err := x509.CreateCertificate(
		rand.Reader,
		&certificate,
		&certificate,
		&privateKey.PublicKey,
		privateKey,
	)
	if err != nil {
		t.Fatal(err)
	}

	certificatePEM := pem.EncodeToMemory(&pem.Block{
		Type:  "CERTIFICATE",
		Bytes: certificateBytes,
	})

	certificatePath := filepath.Join(t.TempDir(), "ca.pem")

	if err := os.WriteFile(certificatePath, certificatePEM, 0o600); err != nil {
		t.Fatal(err)
	}

	return certificatePath, certificatePEM
}
