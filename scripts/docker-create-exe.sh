#!/bin/bash

set -e
set -x


docker rm docker-openport -f
docker run -d --name docker-openport -v $(dirname $(dirname $(realpath $0))):/apps/openport/ jandebleser/openport-client 
docker exec -it docker-openport sudo -u docker ./scripts/create_exes.sh --no-gui 
