"""
InfraGPT Chaos Engineering & Traffic Load Simulator
Simulates concurrent user load and traffic spikes on cluster services.
"""

import time
import urllib.request
import threading
import sys

def send_burst(target_url: str, count: int = 50):
    print(f"[CHAOS] Sending {count} concurrent HTTP requests to {target_url}...")
    success = 0
    errors = 0

    def make_req():
        nonlocal success, errors
        try:
            req = urllib.request.Request(target_url, headers={'User-Agent': 'InfraGPT-ChaosLoad/1.0'})
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    success += 1
        except Exception:
            errors += 1

    threads = [threading.Thread(target=make_req) for _ in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"[CHAOS] Completed: {success} Successful, {errors} Errors (Simulating Load Pressure)")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8888/api/cluster/status"
    send_burst(url, 30)
