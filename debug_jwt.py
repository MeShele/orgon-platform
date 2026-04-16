#!/usr/bin/env python3

import os
import requests
import jwt
from datetime import datetime, timedelta

# Load JWT secret from env
JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "SET_JWT_SECRET_KEY_IN_ENV")
JWT_ALGORITHM = "HS256"

# Create test token manually 
payload = {
    "sub": "15",
    "email": "test2@example.com", 
    "role": "viewer",
    "type": "access",
    "exp": int((datetime.utcnow() + timedelta(minutes=15)).timestamp()),
    "iat": int(datetime.utcnow().timestamp())
}

test_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
print(f"Manual test token: {test_token}")

# Test organizations API
headers = {"Authorization": f"Bearer {test_token}"}
response = requests.get("http://localhost:8000/api/organizations", headers=headers)

print(f"Organizations API response: {response.status_code}")
print(f"Response body: {response.text}")

# Test auth/me API for comparison
response2 = requests.get("http://localhost:8000/api/auth/me", headers=headers) 
print(f"Auth me API response: {response2.status_code}")
print(f"Response body: {response2.text}")