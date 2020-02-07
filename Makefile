build-docker-test:
	docker build -f Dockerfile.test -t openport-test .

bash-test:
	docker run -it -v $$(pwd):/apps/openport openport-test bash

