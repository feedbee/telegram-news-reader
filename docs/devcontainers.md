# Development Container (Devcontainer) Setup Specification

This document describes the standardized approach for setting up development containers across projects. It is divided into platform-agnostic sections and technology-specific configurations.

---

## Table of Contents

1. [Generic Devcontainer Approach](#1-generic-devcontainer-approach)
2. [Node.js-Specific Configuration](#2-nodejs-specific-configuration)
3. [MongoDB via Docker Compose](#3-mongodb-via-docker-compose)
4. [Extension Points](#4-extension-points)

---

## 1. Generic Devcontainer Approach

This section describes the platform-agnostic structure and principles for devcontainer setups.

### 1.1 Directory Structure

```
project-root/
├── .devcontainer/
│   ├── devcontainer.json       # Main devcontainer configuration
│   ├── Dockerfile.dev          # Development-specific Dockerfile
│   ├── docker-compose.yml      # Multi-service orchestration
│   └── welcome-message.sh      # Optional: Post-create welcome script
├── ... (project source code)
```

### 1.2 Core Files Overview

| File                 | Purpose                                                               |
| -------------------- | --------------------------------------------------------------------- |
| `devcontainer.json`  | Primary configuration file for VS Code / Cursor devcontainer features |
| `Dockerfile.dev`     | Custom development image with project-specific tooling                |
| `docker-compose.yml` | Orchestrates workspace + dependent services (databases, caches, etc.) |
| `welcome-message.sh` | Optional script executed after container creation for onboarding      |

### 1.3 devcontainer.json Configuration

The `devcontainer.json` file is the entry point for the devcontainer setup.

```json
{
  "name": "Project Name",
  "dockerComposeFile": "docker-compose.yml",
  "service": "workspace",
  "workspaceFolder": "/workspace",
  "shutdownAction": "stopCompose",
  "features": {
    // Devcontainer features to install (language runtimes, tools)
  },
  "customizations": {
    "vscode": {
      "extensions": [
        // IDE extensions to auto-install
      ],
      "settings": {
        // IDE settings for the project
      }
    }
  },
  "forwardPorts": [
    // Ports to forward from container to host
  ],
  "portsAttributes": {
    // Port labels and auto-forward behavior
  },
  "postCreateCommand": "./.devcontainer/welcome-message.sh",
  "remoteUser": "node" // Or appropriate non-root user
}
```

**Key Configuration Options:**

| Option              | Description                                                |
| ------------------- | ---------------------------------------------------------- |
| `name`              | Human-readable name for the devcontainer                   |
| `dockerComposeFile` | Path to the docker-compose file                            |
| `service`           | The primary service to attach to                           |
| `workspaceFolder`   | Mount path inside the container                            |
| `shutdownAction`    | What to do when closing (`stopCompose` recommended)        |
| `features`          | Devcontainer features to install (language runtimes, CLIs) |
| `forwardPorts`      | Array of ports to forward to host                          |
| `portsAttributes`   | Labels and behavior for forwarded ports                    |
| `postCreateCommand` | Command/script to run after container creation             |
| `remoteUser`        | Non-root user to run as inside the container               |

### 1.4 Dockerfile.dev Guidelines

The development Dockerfile should:

1. **Use an appropriate base image** for your technology stack
2. **Avoid interactive prompts** with `DEBIAN_FRONTEND=noninteractive`
3. **Install system dependencies** required for development
4. **Install global development tools** (linters, formatters, build tools)
5. **Set the working directory** to `/workspace`
6. **Pre-install project dependencies** for faster startup
7. **Fix permissions** for non-root user access
8. **Use `sleep infinity`** as default command (devcontainer overrides this)

**Template:**

```dockerfile
FROM <base-image>

# Avoid interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    # ... other dependencies
    && rm -rf /var/lib/apt/lists/*

# Install global development tools
RUN <package-manager> install -g \
    <tool1> \
    <tool2>

# Set workspace directory
WORKDIR /workspace

# Copy and install dependencies
COPY <dependency-files> ./
RUN <install-command>

# Fix permissions for non-root user
RUN chown -R <user>:<group> /workspace

# Default command
CMD ["sleep", "infinity"]
```

### 1.5 Docker Compose Configuration

The docker-compose file orchestrates the workspace container and dependent services.

**Structure:**

```yaml
version: "3.8"

services:
  workspace:
    build:
      context: ..
      dockerfile: .devcontainer/Dockerfile.dev
    container_name: <project>-workspace
    volumes:
      - ..:/workspace:cached
      # Exclude dependency directories to prevent conflicts
      - /workspace/<dependency-dir>
    ports:
      - "<host-port>:<container-port>"
    environment:
      - <ENV_VAR>=<value>
    depends_on:
      - <service-name>
    networks:
      - <project>-network
    command: sleep infinity

  # Additional services (databases, caches, etc.)

volumes:
  # Named volumes for data persistence

networks:
  <project>-network:
    driver: bridge
```

**Key Patterns:**

| Pattern                 | Purpose                                            |
| ----------------------- | -------------------------------------------------- |
| `context: ..`           | Build from project root to access all files        |
| `:cached` volume flag   | Improve I/O performance on macOS/Windows           |
| Exclude dependency dirs | Prevent host/container conflicts                   |
| Named volumes           | Persist data across container recreations          |
| Custom network          | Enable service discovery by container name         |
| `sleep infinity`        | Keep container running for devcontainer attachment |

### 1.6 Welcome Message Script

An optional but recommended script that runs after container creation to:

- Display project overview
- Show available commands
- Guide first-time setup
- Optionally prompt to start development servers

**Template:**

```bash
#!/bin/bash

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${GREEN}      Welcome to <Project Name> Dev Container!      ${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""
echo -e "${YELLOW}Project Overview:${NC}"
echo -e "<Brief project description>"
echo ""
echo -e "${YELLOW}Available Commands:${NC}"
echo -e "  - ${GREEN}<command1>${NC} - <description>"
echo -e "  - ${GREEN}<command2>${NC} - <description>"
echo ""
echo -e "${YELLOW}First Time Setup:${NC}"
echo -e "  - ${GREEN}<setup-step1>${NC}"
echo -e "  - ${GREEN}<setup-step2>${NC}"
echo ""
echo -e "${BLUE}================================================================${NC}"
```

---

## 2. Node.js-Specific Configuration

This section describes Node.js-specific devcontainer configuration.

### 2.1 Base Image

Use the official Node.js image with Debian Bullseye for stability:

```dockerfile
FROM node:24-bullseye
```

**Version Selection:**

- Use LTS versions for production projects
- Specify the exact major version (e.g., `node:24-bullseye`)
- Use `-bullseye` or `-bookworm` for full Debian with common dev tools

### 2.2 System Dependencies

Install build essentials for native Node.js modules:

```dockerfile
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*
```

### 2.3 Global npm Packages

Install commonly needed global packages:

```dockerfile
RUN npm install -g \
    concurrently \
    nodemon \
    typescript \
    ts-node
```

| Package        | Purpose                              |
| -------------- | ------------------------------------ |
| `concurrently` | Run multiple npm scripts in parallel |
| `nodemon`      | Auto-restart on file changes         |
| `typescript`   | TypeScript compiler                  |
| `ts-node`      | Execute TypeScript directly          |

### 2.4 Multi-Project (Monorepo) Setup

For projects with multiple packages/apps (e.g., `api/` and `web/`):

**Dockerfile.dev:**

```dockerfile
# Set workspace directory
WORKDIR /workspace

# Install dependencies for all projects
COPY package*.json ./
COPY api/package*.json ./api/
COPY web/package*.json ./web/
RUN npm install

# Fix permissions for each project
RUN mkdir -p /workspace/api/node_modules && \
    touch /workspace/api/node_modules/.keep
RUN mkdir -p /workspace/web/node_modules && \
    touch /workspace/web/node_modules/.keep
RUN chown -R node:node /workspace
```

**docker-compose.yml volumes:**

```yaml
volumes:
  - ..:/workspace:cached
  - /workspace/node_modules
  - /workspace/api/node_modules
  - /workspace/web/node_modules
```

**Why exclude node_modules:**

- Prevents conflicts between host and container dependencies
- Different OS may require different native bindings
- Improves volume sync performance

### 2.5 devcontainer.json for Node.js

```json
{
  "name": "Project Name",
  "dockerComposeFile": "docker-compose.yml",
  "service": "workspace",
  "workspaceFolder": "/workspace",
  "shutdownAction": "stopCompose",
  "features": {
    "ghcr.io/devcontainers/features/node:1": {
      "version": "24"
    },
    "ghcr.io/devcontainers/features/git:1": {}
  },
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-vscode.vscode-typescript-next",
        "esbenp.prettier-vscode",
        "ms-vscode.vscode-eslint",
        "bradlc.vscode-tailwindcss",
        "ms-vscode.vscode-json",
        "ms-vscode.vscode-npm-scripts"
      ],
      "settings": {
        "typescript.preferences.importModuleSpecifier": "relative",
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "editor.codeActionsOnSave": {
          "source.fixAll.eslint": true
        }
      }
    }
  },
  "forwardPorts": [3000, 3001],
  "portsAttributes": {
    "3000": {
      "label": "Frontend App",
      "onAutoForward": "notify"
    },
    "3001": {
      "label": "API Server",
      "onAutoForward": "notify"
    }
  },
  "postCreateCommand": "./.devcontainer/welcome-message.sh",
  "remoteUser": "node"
}
```

**Recommended VS Code Extensions:**

| Extension                          | Purpose                      |
| ---------------------------------- | ---------------------------- |
| `ms-vscode.vscode-typescript-next` | TypeScript language features |
| `esbenp.prettier-vscode`           | Code formatting              |
| `ms-vscode.vscode-eslint`          | ESLint integration           |
| `bradlc.vscode-tailwindcss`        | Tailwind CSS IntelliSense    |
| `ms-vscode.vscode-json`            | JSON language support        |
| `ms-vscode.vscode-npm-scripts`     | npm scripts explorer         |

### 2.6 Environment Variables

Set Node.js-specific environment variables in docker-compose.yml:

```yaml
environment:
  - NODE_ENV=development
  - MONGODB_URI=mongodb://admin:password@mongodb:27017/dbname?authSource=admin
  # Add other environment variables as needed
```

---

## 3. MongoDB via Docker Compose

This section describes setting up MongoDB for development purposes.

### 3.1 MongoDB Service Configuration

```yaml
mongodb:
  image: mongo:7
  container_name: <project>-mongodb-dev
  restart: unless-stopped
  ports:
    - "27017:27017"
  environment:
    MONGO_INITDB_ROOT_USERNAME: admin
    MONGO_INITDB_ROOT_PASSWORD: password
    MONGO_INITDB_DATABASE: <database_name>
  volumes:
    - mongodb_dev_data:/data/db
  networks:
    - <project>-network
```

### 3.2 Configuration Options

| Option                       | Value            | Description                                |
| ---------------------------- | ---------------- | ------------------------------------------ |
| `image`                      | `mongo:7`        | Use MongoDB 7.x (adjust version as needed) |
| `restart`                    | `unless-stopped` | Auto-restart unless manually stopped       |
| `MONGO_INITDB_ROOT_USERNAME` | `admin`          | Root admin username                        |
| `MONGO_INITDB_ROOT_PASSWORD` | `password`       | Root admin password (dev only!)            |
| `MONGO_INITDB_DATABASE`      | `<name>`         | Default database to create                 |

### 3.3 Data Persistence

Use a named volume to persist data across container recreations:

```yaml
volumes:
  mongodb_dev_data:
```

**To reset the database:** Remove the named volume:

```bash
docker volume rm <project>_mongodb_dev_data
```

### 3.4 Connection String

From the workspace container, connect using the service name:

```
mongodb://admin:password@mongodb:27017/<database>?authSource=admin
```

**Components:**

- `admin:password` - Credentials
- `mongodb` - Docker service name (resolved via Docker network)
- `27017` - MongoDB default port
- `authSource=admin` - Authenticate against admin database

### 3.5 VS Code MongoDB Extension

Add to devcontainer.json for GUI-based database exploration:

```json
"extensions": [
  "mongodb.mongodb-vscode"
]
```

Forward the MongoDB port for host access:

```json
"forwardPorts": [27017],
"portsAttributes": {
  "27017": {
    "label": "MongoDB",
    "onAutoForward": "silent"
  }
}
```

### 3.6 Security Note

⚠️ **The credentials in this setup are for development only!**

- Never use these credentials in production
- Never commit production credentials to version control
- Use environment variables or secrets management for production

---

## 4. Extension Points

This section describes how to extend this setup for other technologies and services.

### 4.1 Other Languages/Runtimes

Replace the Node.js configuration with appropriate alternatives:

**Python:**

```dockerfile
FROM python:3.12-bullseye

RUN pip install --upgrade pip
RUN pip install poetry

WORKDIR /workspace
COPY pyproject.toml poetry.lock ./
RUN poetry install
```

**Go:**

```dockerfile
FROM golang:1.22-bullseye

RUN go install github.com/cosmtrek/air@latest  # Hot reload

WORKDIR /workspace
COPY go.mod go.sum ./
RUN go mod download
```

**Java:**

```dockerfile
FROM eclipse-temurin:21-jdk-jammy

RUN apt-get update && apt-get install -y maven gradle
WORKDIR /workspace
```

### 4.2 Additional Database Services

**PostgreSQL:**

```yaml
postgres:
  image: postgres:16
  container_name: <project>-postgres-dev
  restart: unless-stopped
  ports:
    - "5432:5432"
  environment:
    POSTGRES_USER: admin
    POSTGRES_PASSWORD: password
    POSTGRES_DB: <database_name>
  volumes:
    - postgres_dev_data:/var/lib/postgresql/data
  networks:
    - <project>-network
```

**Redis:**

```yaml
redis:
  image: redis:7-alpine
  container_name: <project>-redis-dev
  restart: unless-stopped
  ports:
    - "6379:6379"
  volumes:
    - redis_dev_data:/data
  networks:
    - <project>-network
```

### 4.3 Additional Services

**Mailhog (Email Testing):**

```yaml
mailhog:
  image: mailhog/mailhog
  container_name: <project>-mailhog
  ports:
    - "1025:1025" # SMTP
    - "8025:8025" # Web UI
  networks:
    - <project>-network
```

**MinIO (S3-compatible Storage):**

```yaml
minio:
  image: minio/minio
  container_name: <project>-minio
  command: server /data --console-address ":9001"
  ports:
    - "9000:9000"
    - "9001:9001"
  environment:
    MINIO_ROOT_USER: admin
    MINIO_ROOT_PASSWORD: password
  volumes:
    - minio_dev_data:/data
  networks:
    - <project>-network
```

### 4.4 Healthchecks

Add healthchecks for dependent services:

```yaml
mongodb:
  # ... other config
  healthcheck:
    test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/test --quiet
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 10s

workspace:
  depends_on:
    mongodb:
      condition: service_healthy
```

---

## Quick Reference Checklist

### Creating a New Devcontainer Setup

1. [ ] Create `.devcontainer/` directory
2. [ ] Create `devcontainer.json` with project configuration
3. [ ] Create `Dockerfile.dev` with development image
4. [ ] Create `docker-compose.yml` with services
5. [ ] (Optional) Create `welcome-message.sh` for onboarding
6. [ ] Configure port forwarding for all services
7. [ ] Add appropriate VS Code extensions
8. [ ] Test the complete setup

### Files to Copy/Adapt

```
.devcontainer/
├── devcontainer.json   # Adapt: name, features, extensions, ports
├── Dockerfile.dev      # Adapt: base image, dependencies, tools
├── docker-compose.yml  # Adapt: services, volumes, environment
└── welcome-message.sh  # Adapt: project name, commands, setup steps
```
