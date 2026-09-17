#!/usr/bin/env bash

set -eu

BROKER_IP="$1"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"
CERT_DIR="$CONFIG_DIR/certs"

IMAGE="eclipse-mosquitto:2.1.2-alpine"

rm -rf "$CERT_DIR"
rm -f "$CONFIG_DIR/passwords"

mkdir -p "$CERT_DIR"

openssl req \
    -x509 \
    -newkey rsa:2048 \
    -nodes \
    -sha256 \
    -days 3650 \
    -subj "/CN=MQTT Thesis CA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -keyout "$CERT_DIR/ca.key" \
    -out "$CERT_DIR/ca.crt"

openssl req \
    -new \
    -newkey rsa:2048 \
    -nodes \
    -sha256 \
    -subj "/CN=$BROKER_IP" \
    -keyout "$CERT_DIR/broker.key" \
    -out "$CERT_DIR/broker.csr"

cat > "$CERT_DIR/broker.ext" <<EOF
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature
extendedKeyUsage=serverAuth
subjectAltName=IP:$BROKER_IP
EOF

openssl x509 \
    -req \
    -in "$CERT_DIR/broker.csr" \
    -CA "$CERT_DIR/ca.crt" \
    -CAkey "$CERT_DIR/ca.key" \
    -CAcreateserial \
    -sha256 \
    -days 825 \
    -extfile "$CERT_DIR/broker.ext" \
    -out "$CERT_DIR/broker.crt"

rm \
    "$CERT_DIR/ca.key" \
    "$CERT_DIR/broker.csr" \
    "$CERT_DIR/broker.ext" \
    "$CERT_DIR/ca.srl"

echo "Password for macro_publisher:"
docker run --rm -it \
    --user "$(id -u):$(id -g)" \
    -v "$CONFIG_DIR:/mosquitto/config" \
    --entrypoint mosquitto_passwd \
    "$IMAGE" \
    -c /mosquitto/config/passwords macro_publisher

echo "Password for macro_subscriber:"
docker run --rm -it \
    --user "$(id -u):$(id -g)" \
    -v "$CONFIG_DIR:/mosquitto/config" \
    --entrypoint mosquitto_passwd \
    "$IMAGE" \
    /mosquitto/config/passwords macro_subscriber

docker run --rm \
    -v "$CONFIG_DIR:/mosquitto/config" \
    --entrypoint sh \
    "$IMAGE" \
    -c '
        chgrp 1883 /mosquitto/config/passwords /mosquitto/config/certs/broker.key
        chmod 640 /mosquitto/config/passwords /mosquitto/config/certs/broker.key
    '

echo
echo "Broker setup complete."
echo "CA certificate for publisher/subscriber:"
echo "$CERT_DIR/ca.crt"