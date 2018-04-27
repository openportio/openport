FROM ubuntu:16.04
RUN apt-get update && apt-get install -y wget python && apt-get clean

RUN wget https://openport.io/download/debian64/latest.deb
RUN dpkg -i latest.deb
ENV USER=root

VOLUME /root
WORKDIR /apps/openport
ADD entrypoint.sh /apps/openport
CMD ./entrypoint.sh