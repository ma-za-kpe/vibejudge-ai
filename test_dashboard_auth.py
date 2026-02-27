#!/usr/bin/env python3
"""Test dashboard authentication flow with deployed configuration."""
import requests

API_KEY = "419a05e9dd8b005e567c02c6ad0333bc8bba8c50d3bdc06e21d98380301e53e6"
DASHBOARD_BASE = "https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev/api/v1"

print("=" * 70)
print("TESTING DASHBOARD AUTHENTICATION (auth.py simulation)")
print("=" * 70)
print(f"Base URL: {DASHBOARD_BASE}")
print(f"Validation endpoint: {DASHBOARD_BASE}/hackathons")
print(f"API Key: {API_KEY[:20]}...")
print()

# Simulate auth.py validate_api_key() function
try:
    base_url = DASHBOARD_BASE.rstrip("/")
    response = requests.get(
        f"{base_url}/hackathons",
        headers={"X-API-Key": API_KEY},
        timeout=5
    )
    
    is_valid = response.status_code == 200
    
    print(f"Response Status: {response.status_code}")
    print(f"Authentication: {'✅ VALID' if is_valid else '❌ INVALID'}")
    
    if is_valid:
        data = response.json()
        print(f"\nHackathons returned: {len(data.get('hackathons', []))}")
        for hack in data.get('hackathons', []):
            print(f"  - {hack.get('name')} (ID: {hack.get('hack_id')})")
    else:
        print(f"\nError: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ Connection failed: {e}")

print("\n" + "=" * 70)
