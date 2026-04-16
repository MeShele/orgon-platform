"""Test running backend with direct HTTP"""
import requests
import json

print("=== Testing running backend on localhost:8890 ===")

# Test health
try:
    resp = requests.get("http://localhost:8890/api/health", timeout=5)
    print(f"Health: {resp.status_code}")
except Exception as e:
    print(f"Health FAILED: {e}")

# Test networks (no auth needed)
try:
    resp = requests.get("http://localhost:8890/api/networks", timeout=5)
    data = resp.json()
    print(f"Networks: {resp.status_code}, count={len(data)}")
except Exception as e:
    print(f"Networks FAILED: {e}")

# Test login
try:
    resp = requests.post(
        "http://localhost:8890/api/auth/login",
        json={"email": "test@orgon.app", "password": "test1234"},
        timeout=5
    )
    print(f"Login: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
except Exception as e:
    print(f"Login FAILED: {e}")

print("\n=== Check if backend process is running ===")
import subprocess
ps_result = subprocess.run(
    ["ps", "aux"],
    capture_output=True,
    text=True
)
for line in ps_result.stdout.split('\n'):
    if 'backend.main' in line and 'grep' not in line:
        print(line)
