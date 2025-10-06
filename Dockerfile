FROM ubuntu:latest

RUN apt-get update -yq
#RUN apt-get install -yq gcc g++ make git curl wget
#RUN apt-get install -yq nano tmux
#RUN apt-get install -yq python3 python3-pip python3
#RUN apt-get install -yq sudo

RUN apt-get install -yq ffmpeg imagemagick

USER ubuntu
WORKDIR /home/ubuntu/
