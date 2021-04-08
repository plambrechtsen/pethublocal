FROM alpine as build-env

RUN apk add --no-cache build-base git libusb-dev

WORKDIR /data

# Compile the binaries
RUN git clone https://github.com/homewsn/whsniff

WORKDIR /data/whsniff

RUN make

FROM python:3.7-alpine

RUN apk --no-cache --virtual --purge -uU add tshark expect libusb grep gcc musl-dev linux-headers sqlite && rm -rf /var/cache/apk/* /tmp/*

COPY packages.txt packages.txt

RUN pip install -r packages.txt

COPY --from=build-env /data/whsniff/whsniff /data/whsniff

COPY . /data

WORKDIR /data

ENV PATH /usr/sbin:$PATH

ENTRYPOINT ["/data/docker-entrypoint.sh"]

