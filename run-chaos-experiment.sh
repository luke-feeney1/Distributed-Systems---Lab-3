#!/bin/bash

echo " Part C: Chaos Engineering Experiment"

# Check prerequisites
command -v chaos >/dev/null 2>&1 || { echo "   ERROR: chaos toolkit not installed. Install with: pip install chaostoolkit chaostoolkit-kubernetes"; exit 1; }
kubectl cluster-info >/dev/null 2>&1 || { echo "   ERROR: kubectl not connected to cluster"; exit 1; }
echo "Prerequisites adequate"

# Verify services are running
kubectl get pods -l app=backend >/dev/null 2>&1 || { echo "   ERROR: Backend pods not found"; exit 1; }
kubectl get pods -l app=client >/dev/null 2>&1 || { echo "   ERROR: Client pods not found"; exit 1; }
echo "Both client and backend pods are running"

# Show initial state
kubectl get pods -l app=backend
kubectl get pods -l app=client

# Run baseline test
echo "   Testing baseline endpoint."
curl -s http://localhost:8082/loop?n=5 | jq '.results | length' || echo "   Note: Ensure port-forward is running: kubectl port-forward service/client-service 8082:80"
echo

# Prepare monitoring
echo "   Monitor client behavior during backend failure"
echo "   You can run these commands in another terminal during the experiment:"
echo "   - curl http://localhost:8082/fetchBreaker"
echo "   - curl http://localhost:8082/fetchRetry" 
echo "   - curl http://localhost:8082/loopBreaker?n=10"
echo "   - kubectl get pods -w"
echo

# Run chaos experiment
echo "6. Executing chaos experiment (terminating backend pod)."
chaos run chaos/backend_pod_failure.json --journal-path chaos-experiment-journal.json

echo "7. Experiment completed. Check the results:"
echo "   - Journal file: chaos-experiment-journal.json"
echo "   - Pod status: kubectl get pods"
echo "   - Test resilience endpoints to see how they handled the failure"

echo "Experiment Analysis"
echo "Compare the behavior during chaos vs baseline:"
echo "1. Circuit Breaker: Should open quickly when backend fails"
echo "2. Retry Pattern: Should attempt retries but eventually fail"
echo "3. Baseline: Should fail immediately without resilience"
