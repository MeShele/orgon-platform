#!/usr/bin/env python3

import os
import sys
sys.path.append('/root/ORGON')

from backend.config import settings

print(f"JWT_SECRET_KEY from os.getenv: {os.getenv('JWT_SECRET_KEY')}")
print(f"Settings SECRET_KEY: {settings.SECRET_KEY}")
print(f"Are they equal? {os.getenv('JWT_SECRET_KEY') == settings.SECRET_KEY}")

# Test JWT creation and verification
import jwt
from backend.services.auth_service import JWT_SECRET, JWT_ALGORITHM

payload = {"sub": "test", "type": "access"}
token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
print(f"Created token: {token[:50]}...")

# Verify token
try:
    decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    print(f"Token verified successfully: {decoded}")
except Exception as e:
    print(f"Token verification failed: {e}")