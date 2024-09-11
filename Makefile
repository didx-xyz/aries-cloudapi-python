.PHONY: help
help:
	@echo "Available targets:"
	@echo "  stop_n_clean  : Stop and remove all Docker containers"
	@echo "  clean         : Remove all Docker containers"
	@echo "  start_usecache: Start the application using cache"
	@echo "  start         : Start the application"
	@echo "  stop          : Stop the application"
	@echo "  restart       : Restart the application"
	@echo "  unit-tests    : Run unit tests"
	@echo "  tests         : Run all tests"

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
