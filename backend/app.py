from flask import Flask, jsonify
import os
import time
import random

app = Flask(__name__)

# Configure error and delay probabilities
ERROR_RATE = float(os.getenv('ERROR_RATE', '0.1'))  # 10% chance of HTTP 500
SLOW_RATE = float(os.getenv('SLOW_RATE', '0.2'))  # 20% chance of delay
SLOW_MIN = float(os.getenv('SLOW_SECONDS_MIN', '2'))  # min delay in seconds
SLOW_MAX = float(os.getenv('SLOW_SECONDS_MAX', '6'))  # max delay in seconds


# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "ok"})


# Main data endpoint
@app.route('/data')
def get_data():
    r = random.random()

    # Simulate server error with ERROR_RATE probability
    if r < ERROR_RATE:
        return jsonify({"error": "Internal Server Error (simulated)"}), 500

    # Simulate slow response with SLOW_RATE probability
    if r < ERROR_RATE + SLOW_RATE:
        delay = random.uniform(SLOW_MIN, SLOW_MAX)
        time.sleep(delay)

    # Successful response
    return jsonify({
        "message": "Hello from Backend!",
        "note": "This endpoint randomly delays or fails for resilience testing"
    })


# Start the server
if __name__ == '__main__':
    port = int(os.getenv('PORT', '5001'))
    app.run(host='0.0.0.0', port=port, debug=True)






