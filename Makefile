.PHONY: all
all: test tests

.PHONY: stop_n_clean
stop_n_clean:
	docker stop $(shell docker ps -a -q) && docker rm $(shell docker ps -a -q)

.PHONY: clean
clean:
	docker rm $(shell docker ps -a -q)

start_usecache:
	./manage up-daemon-usecache

.PHONY: start
start:
	./manage start

.PHONY: stop
stop:
	./manage stop

.PHONY: restart
restart:
	./manage stop && ./manage start

.PHONY: unit-tests
unit-tests:
	pytest --cov=app --ignore=app/tests/bdd

.PHONY: bdd-tests
bdd-tests:
	pytest --cov=app/tests/bdd app/tests/bdd

.PHONY: tests
tests:
	pytest --cov=app/ --cov=trustregistry trustregistry app