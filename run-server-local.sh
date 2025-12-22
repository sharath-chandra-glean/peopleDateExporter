#!/bin/bash

# Local Testing Script for HTTP Server
# This script runs the Flask server locally for testing

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Starting People Data Exporter Server (Local) ===${NC}"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Copy env.template to .env and configure it first"
    exit 1
fi

# Start server using docker-compose
echo -e "${GREEN}Starting HTTP server on http://localhost:8080${NC}"
echo ""
echo "Available endpoints:"
echo "  - GET  http://localhost:8080/         (service info)"
echo "  - GET  http://localhost:8080/health   (health check)"
echo "  - POST http://localhost:8080/sync     (trigger sync)"
echo ""
echo "Press Ctrl+C to stop"
echo ""

docker-compose up people-exporter-server

# Cleanup on exit
trap "docker-compose down" EXIT

