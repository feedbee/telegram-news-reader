# Load environment variables from .env file
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Default variables
DOCKER_USER ?= feedbee
GIT_HASH := $(shell git rev-parse --short HEAD)

# Multi-platform settings
PLATFORMS ?= linux/amd64,linux/arm64

# Detect local architecture for --load (buildx requires a single platform for --load)
UNAME_M := $(shell uname -m)
ifeq ($(UNAME_M),x86_64)
    LOCAL_PLATFORM := linux/amd64
else ifeq ($(UNAME_M),aarch64)
    LOCAL_PLATFORM := linux/arm64
else ifeq ($(UNAME_M),arm64)
    LOCAL_PLATFORM := linux/arm64
else
    LOCAL_PLATFORM := linux/amd64
endif

# Ingest Multi-platform build command
INGEST_REPO_NAME ?= telegram-news-reader-ingest
INGEST_REPO_URL := $(DOCKER_USER)/$(INGEST_REPO_NAME)
BUILDX_INGEST_CMD := docker buildx build \
	-t $(INGEST_REPO_URL):latest \
	-t $(INGEST_REPO_URL):$(GIT_HASH) \
	-f ingest/Dockerfile \
	ingest/

# Transform Multi-platform build command
TRANSFORM_REPO_NAME ?= telegram-news-reader-transform
TRANSFORM_REPO_URL := $(DOCKER_USER)/$(TRANSFORM_REPO_NAME)
BUILDX_TRANSFORM_CMD := docker buildx build \
	-t $(TRANSFORM_REPO_URL):latest \
	-t $(TRANSFORM_REPO_URL):$(GIT_HASH) \
	-f transform/Dockerfile \
	transform/

# Web Console Multi-platform build command
CONSOLE_REPO_NAME ?= telegram-news-reader-web-console
CONSOLE_REPO_URL := $(DOCKER_USER)/$(CONSOLE_REPO_NAME)
BUILDX_CONSOLE_CMD := docker buildx build \
	-t $(CONSOLE_REPO_URL):latest \
	-t $(CONSOLE_REPO_URL):$(GIT_HASH) \
	-f web-console/Dockerfile \
	web-console/

.PHONY: help \
	ingest-test ingest-run ingest-build ingest-build-multiplatform ingest-push-multiplatform \
	transform-test transform-run transform-build transform-build-multiplatform transform-push-multiplatform \
	console-frontend console-backend console-build console-build-multiplatform console-push-multiplatform

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# ==============================================================================
# Ingest Component
# ==============================================================================

ingest-test: ## Run tests locally
	cd ingest && pip install -r requirements.txt -r requirements-test.txt && PYTHONPATH=. pytest tests/

ingest-run: ## Run ingest in realtime mode with catch-up
	python ingest/main.py --mode realtime --catch-up

ingest-build: ## Build the Docker image locally (current architecture)
	docker build -t $(INGEST_REPO_URL) -f ingest/Dockerfile ingest/

ingest-build-multiplatform: ## Build with buildx for local architecture and load into local docker
	$(BUILDX_INGEST_CMD) --platform $(LOCAL_PLATFORM) --load

ingest-push-multiplatform: ## Authenticate and push multi-platform ingest image
	docker login
	$(BUILDX_INGEST_CMD) --platform $(PLATFORMS) --push

# ==============================================================================
# Transform Component
# ==============================================================================

transform-test: ## Run transform tests locally
	cd transform && pip install -r requirements.txt -r requirements-test.txt && PYTHONPATH=. pytest tests/

transform-run: ## Run transform API server
	python transform/server.py

transform-build: ## Build the transform Docker image locally
	docker build -t $(TRANSFORM_REPO_URL) -f transform/Dockerfile transform/

transform-build-multiplatform: ## Build with buildx for local architecture and load into local docker
	$(BUILDX_TRANSFORM_CMD) --platform $(LOCAL_PLATFORM) --load

transform-push-multiplatform: ## Authenticate and push multi-platform transform image
	docker login
	$(BUILDX_TRANSFORM_CMD) --platform $(PLATFORMS) --push

# ==============================================================================
# Web Console Component
# ==============================================================================

console-frontend: ## Run frontend dev server
	npm run dev --prefix web-console/frontend

console-backend: ## Run backend proxy
	python web-console/backend/main.py

console-build: ## Build the web-console Docker image locally
	docker build -t $(CONSOLE_REPO_URL) -f web-console/Dockerfile web-console/

console-build-multiplatform: ## Build with buildx for local architecture and load into local docker
	$(BUILDX_CONSOLE_CMD) --platform $(LOCAL_PLATFORM) --load

console-push-multiplatform: ## Authenticate and push multi-platform web-console image
	docker login
	$(BUILDX_CONSOLE_CMD) --platform $(PLATFORMS) --push

# ==============================================================================
# Full Stack
# ==============================================================================

full-stack: ## Run all components locally
	concurrently "make console-backend" "make console-frontend" "make transform-run" "make ingest-run"

