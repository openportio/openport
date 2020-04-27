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

run-proxy-test-go:
	docker-compose -f ./docker-compose/proxy-test.yaml run openport-go

run-proxy-test-go-no-password:
	docker-compose -f ./docker-compose/proxy-test-no-password.yaml run openport-go
