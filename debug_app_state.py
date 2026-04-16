#!/usr/bin/env python3

import requests
import json

# Test a specific debug endpoint to check app state
response = requests.get('http://localhost:8000/api/debug/auth-service-info')
print(f"Debug endpoint response: {response.status_code}")
print(f"Response text: {response.text}")

# Test with current token directly
test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiUxNSIsImVtYWlsIjoidGVzdDJAZXhhbXBsZS5jb20iLCJyb2xlIjoidmlld2VyIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTc3MTAyOTg3NiwiaWF0IjoxNzcxMDI4OTc2fQ.EPNtRWE5yHAmSGurKHaIekNWjbAj_dDtqrGA5HyrNkM"

response = requests.post('http://localhost:8000/api/debug/validate-token', 
                        json={'token': test_token})
print(f"Token validation response: {response.status_code}")
print(f"Response: {response.text}")