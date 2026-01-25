#!/bin/bash

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${GREEN}    Welcome to Telegram News Reader Dev Container!    ${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""
echo -e "${YELLOW}Project Overview:${NC}"
echo -e "A service for fetching and processing news from Telegram channels."
echo ""
echo -e "${YELLOW}Project Structure:${NC}"
echo -e "  - ${CYAN}news-fetcher/${NC} - Main Python service for fetching Telegram messages"
echo -e "  - ${CYAN}poc/${NC}          - Proof of concept scripts"
echo -e "  - ${CYAN}docs/${NC}         - Project documentation"
echo ""
echo -e "${YELLOW}Available Commands:${NC}"
echo -e "  - ${GREEN}python news-fetcher/main.py${NC} - Run the news fetcher"
echo -e "  - ${GREEN}pytest${NC}                      - Run tests"
echo -e "  - ${GREEN}black .${NC}                     - Format code"
echo -e "  - ${GREEN}ruff check .${NC}                - Lint code"
echo ""
echo -e "${YELLOW}Database:${NC}"
echo -e "  MongoDB is available at: ${GREEN}mongodb:27017${NC}"
echo -e "  Connection string: ${GREEN}\$MONGODB_URI${NC}"
echo ""
echo -e "${YELLOW}First Time Setup:${NC}"
echo -e "  1. Copy ${GREEN}.env.example${NC} to ${GREEN}.env${NC} and configure your Telegram API credentials"
echo ""
echo -e "${BLUE}================================================================${NC}"
