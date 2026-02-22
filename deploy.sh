#!/bin/bash

# Deployment script for svitlo-power
# This script orchestrates the deployment process by stopping, building, and starting containers

set -e  # Exit on error

echo "Starting deployment process..."

# Step 1: Stop containers
echo "Step 1: Stopping containers..."
docker compose down

# Step 2: Build images without cache
echo "Step 2: Building images (no cache)..."
docker compose build --no-cache

# Step 3: Start containers in detached mode
echo "Step 3: Starting containers..."
docker compose up -d --scale svitlo-power-sse-back-end=3

# Step 4: Remove orphan images
echo "Cleaning up unused Docker resources..."
sudo docker container prune -f
sudo docker image prune -a -f

echo "Deployment completed successfully!"
