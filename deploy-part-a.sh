#!/bin/bash

# Part A: Baseline Deployment Script
echo "Part A: Deploying Baseline Distributed Application"

# Build Docker images
echo "Building backend image."
docker build -t backend-python:latest ./backend/

echo "Building client image."
docker build -t client-python:latest ./client/

# Deploy to Kubernetes
echo "Deploying to Kubernetes."
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/client-deployment.yaml
kubectl apply -f k8s/client-service.yaml

# Wait for deployments
echo "Waiting for deployments to be ready."
kubectl wait --for=condition=available --timeout=300s deployment/backend-deployment
kubectl wait --for=condition=available --timeout=300s deployment/client-deployment

# Show status
echo "Deployment Status"
kubectl get pods
kubectl get services

echo "Testing the application"
echo "Get the client service URL:"
echo "kubectl get service client-service"
echo ""
echo "Test endpoints:"
echo "  /health - Health check"
echo "  /fetch - Single request to backend"
echo "  /loop?n=5 - Multiple requests to backend"