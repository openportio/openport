#!/usr/bin/env bash
set -ex
cd $(dirname $0)

docker build . -t sshserver
docker run -it -v $(pwd):/apps/sshserver sshserver go build OpenportClient.go
