FROM alpine:3.12

# Install mosquitto
RUN apk --no-cache --virtual --purge -uU add mosquitto mosquitto-clients && rm -rf /var/cache/apk/* /tmp/*

COPY . /

# Expose TLS MQTT port
EXPOSE 1883 8883

#VOLUME /mosquitto

ENV PATH /usr/sbin:$PATH

ENTRYPOINT ["/docker-entrypoint.sh"]
