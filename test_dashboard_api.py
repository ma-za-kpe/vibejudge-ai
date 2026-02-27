#!/usr/bin/env python3
"""Test dashboard authentication flow with current API configuration."""
import requests

API_KEY = "419a05e9dd8b005e567c02c6ad0333bc8bba8c50d3bdc06e21d98380301e53e6"

# Test 1: What base URL does dashboard use?
DASHBOARD_BASE = "https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev"

print("=" * 70)
print("TEST 1: Auth validation endpoint (dashboard simulates this)")
print("=" * 70)
print(f"Base URL: {DASHBOARD_BASE}")
print(f"Endpoint: {DASHBOARD_BASE}/hackathons")
print()

response = requests.get(
    f"{DASHBOARD_BASE}/hackathons",
    headers={"X-API-Key": API_KEY},
    timeout=5
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}")
print()

print("=" * 70)
print("TEST 2: Correct endpoint")
print("=" * 70)
CORRECT_BASE = "https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev/api/v1"
print(f"Base URL: {CORRECT_BASE}")
print(f"Endpoint: {CORRECT_BASE}/hackathons")
print()

response2 = requests.get(
    f"{CORRECT_BASE}/hackathons",
    headers={"X-API-Key": API_KEY},
    timeout=5
)
print(f"Status: {response2.status_code}")
print(f"Response: {response2.text[:200]}")
