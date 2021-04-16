FROM python:3.8-alpine

# Install mosquitto
RUN apk add --no-cache mosquitto mosquitto-clients moreutils expect gcc musl-dev linux-headers && rm -rf /var/cache/apk/* /tmp/*

WORKDIR /msgs

COPY . . 

ENV PATH /usr/sbin:$PATH

ENTRYPOINT ["/msgs/docker-entrypoint.sh"]
