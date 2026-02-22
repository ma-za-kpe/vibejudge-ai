#!/usr/bin/env python3
"""Test script for local API testing."""

import sys
import time
import requests
from datetime import datetime

def test_health():
    """Test health endpoint."""
    print("Testing health endpoint...")
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_organizer_create():
    """Test creating an organizer."""
    print("\nTesting organizer creation...")
    payload = {
        "name": "Test Organizer",
        "email": "test@example.com",
        "organization": "Test Org"
    }
    try:
        response = requests.post(
            "http://localhost:8001/api/v1/organizers",
            json=payload,
            timeout=5
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run tests."""
    print("=" * 60)
    print("VibeJudge AI - Local API Test")
    print("=" * 60)
    print(f"Time: {datetime.now()}")
    print()
    
    # Wait for server to be ready
    print("Waiting for server to start...")
    for i in range(10):
        try:
            requests.get("http://localhost:8001/health", timeout=1)
            print("Server is ready!")
            break
        except:
            time.sleep(1)
            print(f"Attempt {i+1}/10...")
    else:
        print("Server did not start in time!")
        sys.exit(1)
    
    print()
    
    # Run tests
    results = []
    results.append(("Health Check", test_health()))
    results.append(("Create Organizer", test_organizer_create()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
