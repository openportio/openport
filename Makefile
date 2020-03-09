build-docker-test:
	docker build -f Dockerfile.test -t openport-test .

test:
	docker run -it -v $$(pwd):/apps/openport openport-test

bash-test:
	docker run -it -v $$(pwd):/apps/openport openport-test bash

build-docker:
	docker build -t jandebleser/openport .

run-proxy-test:
	docker-compose -f ./docker-compose/proxy-test.yaml run openport
