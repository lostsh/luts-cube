FROM alpine:latest

RUN apk add --update ffmpeg

#USER user
WORKDIR /home/user/mount/
COPY alpinply.sh /bin/

CMD alpinply.sh -p "$PIC" -c "$CUBE" -o "$OUT"
