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
	pytest app --ignore=app/tests/e2e

.PHONY: tests
tests:
	pytest .