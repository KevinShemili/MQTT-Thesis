FROM eclipse-mosquitto:2.1.2-alpine

USER root

RUN apk add --no-cache openssl

COPY mosquitto.conf /mosquitto/config/mosquitto.conf
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
