#!/bin/bash

# Chaos Experiment Monitoring Script
# Run this in a separate terminal DURING the chaos experiment

echo "Chaos Experiment Monitoring"
echo "Testing client resilience patterns while backend pods are failing"
echo "Make sure port-forward is running: kubectl port-forward service/client-service 8082:80"

# Function to test endpoint and show result
test_endpoint() {
    local endpoint=$1
    local description=$2
    echo "Testing $description ($endpoint)."
    
    start_time=$(date +%s)
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}\nTOTAL_TIME:%{time_total}" "http://localhost:8082$endpoint" 2>/dev/null)
    end_time=$(date +%s)
    
    echo "Response: $response"
    echo "Duration: $((end_time - start_time)) seconds"
    echo "---"
}

# Continuous monitoring function
monitor_during_chaos() {
    echo "Monitoring started - testing every 10 seconds."
    
    counter=1
    while true; do
        echo
        echo "Test Round $counter ($(date))"
        
        # Test baselin
        test_endpoint "/fetch" "Baseline"
        
        # Test circuit breaker
        test_endpoint "/fetchBreaker" "Circuit Breaker"
        
        # Test retry
        test_endpoint "/fetchRetry" "Retry Pattern"
        
        # Check pod status
        echo "Pod Status:"
        kubectl get pods -l app=backend --no-headers 2>/dev/null || echo "Backend pods not found"
        kubectl get pods -l app=client --no-headers 2>/dev/null || echo "Client pods not found"
        
        counter=$((counter + 1))
        sleep 10
    done
}

# Manual testing function
manual_testing() {
    echo "Manual Testing Mode"
    echo "Run these commands to test resilience patterns:"
    echo
    echo "1. Baseline (no resilience):"
    echo "   curl http://localhost:8082/fetch"
    echo "   curl http://localhost:8082/loop?n=5"
    echo
    echo "2. Circuit Breaker:"
    echo "   curl http://localhost:8082/fetchBreaker"
    echo "   curl http://localhost:8082/loopBreaker?n=10"
    echo
    echo "3. Retry Pattern:"
    echo "   curl http://localhost:8082/fetchRetry"
    echo "   curl http://localhost:8082/loopRetry?n=5"
    echo
    echo "4. Monitor pods:"
    echo "   kubectl get pods -w"
    echo
    echo "5. Check circuit breaker state in client logs:"
    echo "   kubectl logs -l app=client --tail=20"
}

# Main menu
echo "Choose monitoring mode:"
echo "1. Automatic monitoring (tests every 10 seconds)"
echo "2. Manual testing (show commands to run)"
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        monitor_during_chaos
        ;;
    2)
        manual_testing
        ;;
    *)
        echo "Invalid choice. Showing manual testing commands..."
        manual_testing
        ;;
esac