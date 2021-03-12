FROM alpine:3.12

# Install mosquitto
RUN apk add --no-cache --virtual mosquitto mosquitto-clients moreutils && rm -rf /var/cache/apk/* /tmp/*

COPY docker-entrypoint.sh /docker-entrypoint.sh

ENV PATH /usr/sbin:$PATH

ENTRYPOINT ["/docker-entrypoint.sh"]
