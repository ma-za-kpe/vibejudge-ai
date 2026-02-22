#!/usr/bin/env python3
"""Direct API testing using FastAPI TestClient (no server needed)."""

import os
import json
import time

# Set environment variables before importing
os.environ["DYNAMODB_TABLE_NAME"] = "VibeJudgeTable"
os.environ["DYNAMODB_ENDPOINT_URL"] = "http://localhost:8000"
os.environ["AWS_ACCESS_KEY_ID"] = "dummy"
os.environ["AWS_SECRET_ACCESS_KEY"] = "dummy"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["LOG_LEVEL"] = "INFO"

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def print_response(title: str, response):
    """Pretty print response."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    if response.status_code < 400:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.text}")
    print()

def main():
    print("\n" + "="*60)
    print("VibeJudge AI - Direct API Test")
    print("="*60)
    
    # Use timestamp to make email unique
    timestamp = int(time.time())
    test_email = f"test+{timestamp}@vibejudge.ai"
    
    # Step 1: Health check
    print("\n[1/8] Testing health endpoint...")
    response = client.get("/health")
    print_response("Health Check", response)
    assert response.status_code == 200, "Health check failed"
    
    # Step 2: Create organizer
    print("[2/8] Creating organizer...")
    response = client.post("/api/v1/organizers", json={
        "name": "Test Organizer",
        "email": test_email,
        "organization": "Vibe Coders"
    })
    print_response("Create Organizer", response)
    assert response.status_code == 201, f"Failed to create organizer: {response.text}"
    
    org_data = response.json()
    org_id = org_data["org_id"]
    api_key = org_data["api_key"]
    print(f"✓ Organizer ID: {org_id}")
    print(f"✓ API Key: {api_key[:16]}...")
    
    # Step 3: Create hackathon
    print("\n[3/8] Creating hackathon...")
    response = client.post(
        "/api/v1/hackathons",
        json={
            "name": "Test Hackathon 2026",
            "description": "Testing VibeJudge AI MVP",
            "rubric": {
                "name": "Default Rubric",
                "version": "1.0",
                "max_score": 100.0,
                "dimensions": [
                    {
                        "name": "Code Quality",
                        "agent": "bug_hunter",
                        "weight": 0.3,
                        "description": "Code quality, security, and testing"
                    },
                    {
                        "name": "Architecture",
                        "agent": "performance",
                        "weight": 0.3,
                        "description": "Architecture, scalability, and performance"
                    },
                    {
                        "name": "Innovation",
                        "agent": "innovation",
                        "weight": 0.3,
                        "description": "Creativity, novelty, and documentation"
                    },
                    {
                        "name": "Authenticity",
                        "agent": "ai_detection",
                        "weight": 0.1,
                        "description": "Development authenticity and AI usage"
                    }
                ]
            },
            "agents_enabled": ["bug_hunter", "performance", "innovation", "ai_detection"],
        "ai_policy_mode": "ai_assisted",
        "budget_limit_usd": 50.0
        },
        headers={"X-API-Key": api_key}
    )
    print_response("Create Hackathon", response)
    assert response.status_code == 201, f"Failed to create hackathon: {response.text}"
    
    hack_data = response.json()
    hack_id = hack_data["hack_id"]
    print(f"✓ Hackathon ID: {hack_id}")
    
    # Step 4: Get hackathon
    print("\n[4/8] Retrieving hackathon...")
    response = client.get(f"/api/v1/hackathons/{hack_id}")
    print_response("Get Hackathon", response)
    assert response.status_code == 200, f"Failed to get hackathon: {response.text}"
    
    # Step 5: List hackathons
    print("\n[5/8] Listing hackathons...")
    response = client.get(
        "/api/v1/hackathons",
        headers={"X-API-Key": api_key}
    )
    print_response("List Hackathons", response)
    assert response.status_code == 200, f"Failed to list hackathons: {response.text}"
    
    # Step 6: Create submissions
    print("\n[6/8] Creating submissions...")
    response = client.post(f"/api/v1/hackathons/{hack_id}/submissions", json={
        "submissions": [
            {
                "team_name": "Team Alpha",
                "repo_url": "https://github.com/anthropics/anthropic-quickstarts"
            },
            {
                "team_name": "Team Beta",
                "repo_url": "https://github.com/fastapi/fastapi"
            }
        ]
    })
    print_response("Create Submissions", response)
    assert response.status_code == 201, f"Failed to create submissions: {response.text}"
    
    sub_data = response.json()
    sub_id = sub_data["submissions"][0]["sub_id"]
    print(f"✓ Created {len(sub_data['submissions'])} submissions")
    print(f"✓ First submission ID: {sub_id}")
    
    # Step 7: List submissions
    print("\n[7/8] Listing submissions...")
    response = client.get(f"/api/v1/hackathons/{hack_id}/submissions")
    print_response("List Submissions", response)
    assert response.status_code == 200, f"Failed to list submissions: {response.text}"
    
    # Step 8: Get submission
    print("\n[8/8] Retrieving submission...")
    response = client.get(f"/api/v1/submissions/{sub_id}")
    print_response("Get Submission", response)
    assert response.status_code == 200, f"Failed to get submission: {response.text}"
    
    # Summary
    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED!")
    print("="*60)
    print(f"\nCreated Resources:")
    print(f"  Organizer ID: {org_id}")
    print(f"  Hackathon ID: {hack_id}")
    print(f"  Submission ID: {sub_id}")
    print(f"\nNext steps:")
    print(f"  - Verify data in DynamoDB")
    print(f"  - Test cost estimation endpoint")
    print(f"  - Test analysis trigger (placeholder)")
    print()

if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
