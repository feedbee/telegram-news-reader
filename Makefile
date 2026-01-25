# Default variables
DOCKER_USER ?= feedbee
REPO_NAME ?= telegram-news-reader-ingest
GIT_HASH := $(shell git rev-parse --short HEAD)
REPO_URL := $(DOCKER_USER)/$(REPO_NAME)

.PHONY: ingest-test ingest-build ingest-build-multiplatform ingest-push help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

ingest-test: ## Run tests locally
	cd ingest && pip install -r requirements.txt -r requirements-test.txt && PYTHONPATH=. pytest tests/

ingest-build: ## Build the Docker image locally
	docker build -t $(REPO_NAME) -f ingest/Dockerfile ingest/

ingest-build-multiplatform: ## Build multi-platform image (dry run, no push)
	docker buildx build \
		--platform linux/amd64,linux/arm64 \
		-t $(REPO_URL):latest \
		-t $(REPO_URL):$(GIT_HASH) \
		-f ingest/Dockerfile \
		ingest/

ingest-push: ## Authenticate and push multi-platform image to DockerHub
	docker login
	docker buildx build \
		--platform linux/amd64,linux/arm64 \
		-t $(REPO_URL):latest \
		-t $(REPO_URL):$(GIT_HASH) \
		-f ingest/Dockerfile \
		ingest/ \
		--push
