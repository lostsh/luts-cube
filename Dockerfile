FROM alpine:latest

RUN apk add --update ffmpeg imagemagick
#RUN adduser --disabled-password user

#USER user
WORKDIR /home/user/mount/
COPY alpinply.sh /bin/

# TEST PURPOSES
#COPY sctest.sh /bin/
#CMD sctest.sh -p "$PIC" -c "$CUBE" -o "$OUT"
CMD alpinply.sh -p "$PIC" -c "$CUBE" -o "$OUT"
