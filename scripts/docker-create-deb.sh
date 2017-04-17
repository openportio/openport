#!/bin/bash

set -e
set -x


docker rm docker-openport -f || echo ""
docker run -d --name docker-openport -v $(dirname $(dirname $(dirname $(pwd)/$0))):/apps/openport/ jandebleser/openport-client2 
docker exec -it docker-openport sudo -u docker ./scripts/create_exes.sh --no-gui
docker exec -it docker-openport bash -ex ./scripts/distribution/debian/createdeb.sh --no-gui
docker exec -it docker-openport bash -c "dpkg -i ./scripts/distribution/debian/*.deb"
docker exec -it docker-openport openport 22
