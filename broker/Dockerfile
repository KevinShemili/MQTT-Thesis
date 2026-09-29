FROM eclipse-mosquitto:2.1.2-alpine

USER root

RUN apk add --no-cache openssl

COPY mosquitto.conf /mosquitto/config/mosquitto.conf
COPY --chown=mosquitto:mosquitto --chmod=0700 acl /mosquitto/config/acl
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]