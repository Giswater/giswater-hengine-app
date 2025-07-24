#!/bin/bash

# Create Docker network if it doesn't exist
if ! docker network ls | grep -q "api-network-2"; then
    echo "Creating api-network-2..."
    docker network create --subnet=172.21.1.0/24 api-network-2
    echo "Network created successfully"
else
    echo "Network api-network-2 already exists"
fi

# Start the application with docker-compose
echo "Starting Giswater Hydraulic Engine API..."
docker-compose up --build

echo "Application stopped"