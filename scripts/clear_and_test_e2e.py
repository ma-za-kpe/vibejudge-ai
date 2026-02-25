#!/usr/bin/env python3
"""Clear old analysis data and run fresh E2E tests.

This script:
1. Connects to DynamoDB production table
2. Deletes old submissions and related records
3. Runs fresh E2E tests to validate all bugfixes

Usage:
    python scripts/clear_and_test_e2e.py
"""

import os
import sys

import boto3
from boto3.dynamodb.conditions import Key

# Configuration
TABLE_NAME = "vibejudge-dev"
REGION = "us-east-1"


def get_dynamodb_table():
    """Get DynamoDB table resource."""
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    return dynamodb.Table(TABLE_NAME)


def delete_submission_and_related_records(table, sub_id: str) -> int:
    """Delete submission and all related records (scores, analysis, feedback).

    Args:
        table: DynamoDB table resource
        sub_id: Submission ID (e.g., "SUB#01JKABCDEF")

    Returns:
        Number of records deleted
    """
    deleted_count = 0

    # Query all records for this submission
    response = table.query(KeyConditionExpression=Key("PK").eq(sub_id))

    items = response.get("Items", [])
    print(f"   Found {len(items)} records for {sub_id}")

    # Delete each record
    for item in items:
        pk = item["PK"]
        sk = item["SK"]
        table.delete_item(Key={"PK": pk, "SK": sk})
        deleted_count += 1
        print(f"   Deleted: {pk} / {sk}")

    return deleted_count


def list_all_submissions(table) -> list[str]:
    """List all submission IDs in the table.

    Returns:
        List of submission IDs (e.g., ["SUB#01JKABCDEF", ...])
    """
    submissions = []

    # Scan table for all items with PK starting with "SUB#"
    response = table.scan(
        FilterExpression="begins_with(PK, :prefix)",
        ExpressionAttributeValues={":prefix": "SUB#"},
    )

    for item in response.get("Items", []):
        pk = item["PK"]
        if pk not in submissions:
            submissions.append(pk)

    # Handle pagination
    while "LastEvaluatedKey" in response:
        response = table.scan(
            FilterExpression="begins_with(PK, :prefix)",
            ExpressionAttributeValues={":prefix": "SUB#"},
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        for item in response.get("Items", []):
            pk = item["PK"]
            if pk not in submissions:
                submissions.append(pk)

    return submissions


def clear_old_analysis_data():
    """Clear all old submission and analysis data from DynamoDB."""
    print("🗑️  Clearing old analysis data from DynamoDB...")
    print(f"   Table: {TABLE_NAME}")
    print(f"   Region: {REGION}\n")

    table = get_dynamodb_table()

    # List all submissions
    submissions = list_all_submissions(table)
    print(f"Found {len(submissions)} submissions to delete\n")

    if not submissions:
        print("✅ No submissions found - table is clean")
        return

    # Confirm deletion
    print("⚠️  This will delete ALL submissions and related records:")
    for sub_id in submissions:
        print(f"   - {sub_id}")

    response = input("\nProceed with deletion? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Deletion cancelled")
        sys.exit(0)

    # Delete each submission and related records
    total_deleted = 0
    for sub_id in submissions:
        print(f"\n🗑️  Deleting {sub_id}...")
        count = delete_submission_and_related_records(table, sub_id)
        total_deleted += count

    print(f"\n✅ Deleted {total_deleted} records from {len(submissions)} submissions")


def run_e2e_tests():
    """Run E2E tests using pytest."""
    print("\n" + "=" * 80)
    print("🧪 Running E2E Tests")
    print("=" * 80 + "\n")

    import subprocess

    result = subprocess.run(
        ["pytest", "tests/e2e/test_live_production.py", "-v", "-s", "--tb=short"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    if result.returncode == 0:
        print("\n✅ All E2E tests passed!")
    else:
        print(f"\n❌ E2E tests failed with exit code {result.returncode}")
        sys.exit(result.returncode)


def main():
    """Main execution."""
    print("=" * 80)
    print("VibeJudge AI - Clear Old Data & Run Fresh E2E Tests")
    print("=" * 80 + "\n")

    # Step 1: Clear old data
    clear_old_analysis_data()

    # Step 2: Run E2E tests
    run_e2e_tests()

    print("\n" + "=" * 80)
    print("✅ Complete! All bugfixes validated with fresh analysis data.")
    print("=" * 80)


if __name__ == "__main__":
    main()
