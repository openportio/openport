#!/bin/bash

MACHINE=$(uname -m)
DOCKERARGS=
if [ "$MACHINE" == "armv7l" ] ; then
	DOCKERARGS="--build-arg FROMIMAGE=resin/rpi-raspbian:jessie"

fi
export DOCKER_API_VERSION=1.23

docker build $DOCKERARGS -t jandebleser/openport-client2 .

