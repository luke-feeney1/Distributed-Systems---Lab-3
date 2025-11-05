
# Client Service (Python) - Parts A & B: Baseline + Resilience
from flask import Flask, jsonify, request
import requests
import os
import time
import random
import threading
from datetime import datetime, timedelta

app = Flask(__name__)

# Configuration
BACKEND_HOST = os.getenv('BACKEND_HOST', 'backend')
BACKEND_PORT = os.getenv('BACKEND_PORT', '5001')
TIMEOUT_MS = float(os.getenv('TIMEOUT_MS', '3000'))
TIMEOUT_SECONDS = TIMEOUT_MS / 1000.0
backend_url = f"http://{BACKEND_HOST}:{BACKEND_PORT}/data"


# Simple Circuit Breaker Implementation
class SimpleCircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=5):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'
        self.lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        with self.lock:
            now = datetime.now()

            # Check if we should transition from open to half-open
            if self.state == 'open':
                if self.last_failure_time and (now - self.last_failure_time).seconds >= self.recovery_timeout:
                    self.state = 'half-open'
                    print("Circuit Breaker: HALF-OPEN - Testing limited requests")
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                result = func(*args, **kwargs)
                # Success - reset failure count
                if self.state == 'half-open':
                    self.state = 'closed'
                    print("Circuit Breaker: CLOSED - System recovered")
                self.failure_count = 0
                return result

            except Exception as e:
                # Failure - increment count
                self.failure_count += 1
                self.last_failure_time = now

                if self.failure_count >= self.failure_threshold:
                    self.state = 'open'
                    print("Circuit Breaker: OPEN - Requests are being blocked")

                raise e


# Create circuit breaker instance
circuit_breaker = SimpleCircuitBreaker(failure_threshold=5, recovery_timeout=5)


def backend_call():
    """Function to be protected by circuit breaker"""
    response = requests.get(backend_url, timeout=TIMEOUT_SECONDS)
    if response.status_code >= 400:
        raise Exception(f"HTTP {response.status_code}: {response.text}")
    return response.json()


# 1. BASELINE MODE (Part A)

# Health check
@app.route('/health')
def health_check():
    return jsonify({"status": "ok"})


# Single request - Baseline (no resilience patterns)
@app.route('/fetch')
def fetch_data():
    start_time = time.time()
    try:
        response = requests.get(backend_url, timeout=TIMEOUT_SECONDS)
        elapsed_ms = (time.time() - start_time) * 1000

        return jsonify({
            "backendUrl": backend_url,
            "status": response.status_code,
            "elapsed_ms": elapsed_ms,
            "payload": response.json()
        }), response.status_code

    except requests.exceptions.RequestException as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return jsonify({
            "backendUrl": backend_url,
            "error": str(e),
            "elapsed_ms": elapsed_ms
        }), 502


# Multiple requests - Baseline
@app.route('/loop')
def loop_requests():
    n = int(request.args.get('n', 10))
    results = []

    for i in range(n):
        start_time = time.time()
        try:
            response = requests.get(backend_url, timeout=TIMEOUT_SECONDS)
            elapsed_ms = (time.time() - start_time) * 1000

            results.append({
                "i": i,
                "status": response.status_code,
                "elapsed_ms": elapsed_ms
            })

        except requests.exceptions.RequestException as e:
            elapsed_ms = (time.time() - start_time) * 1000
            results.append({
                "i": i,
                "error": str(e),
                "elapsed_ms": elapsed_ms
            })

    return jsonify({
        "mode": "baseline",
        "count": n,
        "backendUrl": backend_url,
        "results": results
    })

# 2. CIRCUIT BREAKER MODE (Part B)
# Single request - with Circuit Breaker
@app.route('/fetchBreaker')
def fetch_with_breaker():
    start_time = time.time()
    try:
        result = circuit_breaker.call(backend_call)
        elapsed_ms = (time.time() - start_time) * 1000

        return jsonify({
            "mode": "breaker",
            "backendUrl": backend_url,
            "status": "OK",
            "elapsed_ms": elapsed_ms,
            "payload": result,
            "circuit_state": circuit_breaker.state
        })

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return jsonify({
            "mode": "breaker",
            "backendUrl": backend_url,
            "error": str(e),
            "elapsed_ms": elapsed_ms,
            "circuit_state": circuit_breaker.state
        }), 502


# Multiple requests - with Circuit Breaker
@app.route('/loopBreaker')
def loop_with_breaker():
    n = int(request.args.get('n', 10))
    results = []

    for i in range(n):
        start_time = time.time()
        try:
            result = circuit_breaker.call(backend_call)
            elapsed_ms = (time.time() - start_time) * 1000

            results.append({
                "i": i,
                "status": "OK",
                "elapsed_ms": elapsed_ms,
                "circuit_state": circuit_breaker.state
            })

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            results.append({
                "i": i,
                "status": "FAILED",
                "error": str(e),
                "elapsed_ms": elapsed_ms,
                "circuit_state": circuit_breaker.state
            })

    return jsonify({
        "mode": "breaker",
        "count": n,
        "backendUrl": backend_url,
        "results": results
    })


# 3. RETRY PATTERN (Part B)
# Single request - with Retry and Exponential Backoff
@app.route('/fetchRetry')
def fetch_with_retry():
    max_retries = 5
    base_delay = 0.5  # 500ms in seconds
    jitter = 0.2  # 200ms in seconds
    start_time = time.time()

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(backend_url, timeout=TIMEOUT_SECONDS)
            elapsed_ms = (time.time() - start_time) * 1000

            if response.status_code >= 400:
                raise requests.exceptions.HTTPError(f"HTTP {response.status_code}")

            return jsonify({
                "mode": "retry",
                "attempt": attempt,
                "backendUrl": backend_url,
                "status": response.status_code,
                "elapsed_ms": elapsed_ms,
                "payload": response.json()
            })

        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            if attempt == max_retries:
                elapsed_ms = (time.time() - start_time) * 1000
                return jsonify({
                    "mode": "retry",
                    "backendUrl": backend_url,
                    "error": f"Failed after {attempt} retries: {str(e)}",
                    "elapsed_ms": elapsed_ms
                }), 502

            # Calculate exponential delay + jitter
            delay = base_delay * (2 ** (attempt - 1)) + (random.random() * jitter)
            print(f"Attempt {attempt} failed: {str(e)}. Retrying in {delay:.3f}s")
            time.sleep(delay)


# Multiple requests - with Retry pattern
@app.route('/loopRetry')
def loop_with_retry():
    n = int(request.args.get('n', 10))
    max_retries = 5
    base_delay = 0.5  # 500ms in seconds
    jitter = 0.2  # 200ms in seconds
    results = []

    for i in range(n):
        start_time = time.time()
        success = False
        attempt = 0

        while attempt < max_retries and not success:
            attempt += 1
            try:
                response = requests.get(backend_url, timeout=TIMEOUT_SECONDS)
                elapsed_ms = (time.time() - start_time) * 1000

                if response.status_code >= 400:
                    raise requests.exceptions.HTTPError(f"HTTP {response.status_code}")

                results.append({
                    "i": i,
                    "attempt": attempt,
                    "status": response.status_code,
                    "elapsed_ms": elapsed_ms
                })
                success = True

            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                if attempt == max_retries:
                    elapsed_ms = (time.time() - start_time) * 1000
                    results.append({
                        "i": i,
                        "attempt": attempt,
                        "error": str(e),
                        "elapsed_ms": elapsed_ms
                    })
                else:
                    delay = base_delay * (2 ** (attempt - 1)) + (random.random() * jitter)
                    print(f"Request {i}, Attempt {attempt} failed: {str(e)}. Retrying in {delay:.3f}s")
                    time.sleep(delay)

    return jsonify({
        "mode": "retry",
        "count": n,
        "backendUrl": backend_url,
        "results": results
    })


# Start server
if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=True)