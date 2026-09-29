#!/bin/sh

set -eu

STATE_DIR="/state"
CERT_DIR="$STATE_DIR/certs"
PASSWORD_FILE="$STATE_DIR/passwords"

: "${MACRO_BROKER_URL:?}"
: "${MACRO_PUBLISHER_USERNAME:?}"
: "${MACRO_PUBLISHER_PASSWORD:?}"
: "${MACRO_SUBSCRIBER_USERNAME:?}"
: "${MACRO_SUBSCRIBER_PASSWORD:?}"

mkdir -p "$CERT_DIR"


# ============================================================
# TLS CERTIFICATES
# ============================================================

if [ ! -f "$CERT_DIR/ca.crt" ]; then

    echo "Generating broker TLS certificates..."

    BROKER_HOST="${MACRO_BROKER_URL#ssl://}"
    BROKER_HOST="${BROKER_HOST%%:*}"
    SAN="IP:127.0.0.1,IP:$BROKER_HOST"

    echo "Broker certificate SANs: $SAN"

    # Create CA.
    # The CA private key exists only temporarily and is deleted
    # after signing the broker certificate.
    openssl req \
        -x509 \
        -newkey rsa:2048 \
        -nodes \
        -sha256 \
        -days 3650 \
        -subj "/CN=MQTT Thesis CA" \
        -addext "basicConstraints=critical,CA:TRUE" \
        -addext "keyUsage=critical,keyCertSign,cRLSign" \
        -keyout /tmp/ca.key \
        -out "$CERT_DIR/ca.crt"

    # Create broker private key and certificate request.
    openssl req \
        -new \
        -newkey rsa:2048 \
        -nodes \
        -sha256 \
        -subj "/CN=mqtt-thesis-broker" \
        -keyout "$CERT_DIR/broker.key" \
        -out /tmp/broker.csr

    cat > /tmp/broker.ext <<EOF
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature
extendedKeyUsage=serverAuth
subjectAltName=$SAN
EOF

    # Sign broker certificate with our CA.
    openssl x509 \
        -req \
        -in /tmp/broker.csr \
        -CA "$CERT_DIR/ca.crt" \
        -CAkey /tmp/ca.key \
        -CAcreateserial \
        -sha256 \
        -days 825 \
        -extfile /tmp/broker.ext \
        -out "$CERT_DIR/broker.crt"

    rm -f \
        /tmp/ca.key \
        /tmp/broker.csr \
        /tmp/broker.ext \
        "$CERT_DIR/ca.srl"
fi


# ============================================================
# MQTT USERS
# ============================================================

echo "Creating MQTT password database..."

rm -f "$PASSWORD_FILE"

mosquitto_passwd \
    -b \
    -c \
    "$PASSWORD_FILE" \
    "$MACRO_PUBLISHER_USERNAME" \
    "$MACRO_PUBLISHER_PASSWORD"

mosquitto_passwd \
    -b \
    "$PASSWORD_FILE" \
    "$MACRO_SUBSCRIBER_USERNAME" \
    "$MACRO_SUBSCRIBER_PASSWORD"


# ============================================================
# PERMISSIONS
# ============================================================

chown -R mosquitto:mosquitto "$STATE_DIR"

chmod 644 \
    "$CERT_DIR/ca.crt" \
    "$CERT_DIR/broker.crt"

chmod 600 \
    "$CERT_DIR/broker.key" \
    "$PASSWORD_FILE"


# ============================================================
# START BROKER
# ============================================================

echo "Starting Mosquitto..."

exec mosquitto \
    -c /mosquitto/config/mosquitto.conf