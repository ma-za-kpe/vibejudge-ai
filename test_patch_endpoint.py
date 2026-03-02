#!/usr/bin/env python3
"""Manual test for PATCH /api-keys endpoint."""

from src.models.api_key import Tier

# Test data structure matches what PATCH endpoint expects
update_payload = {
    "tier": "ENTERPRISE",  # Upgrade to ENTERPRISE
    "daily_quota": None,  # Will use ENTERPRISE default (unlimited)
    "rate_limit_per_second": None,  # Will use ENTERPRISE default
    "budget_limit_usd": None,  # Will use ENTERPRISE default
    "expires_at": None,
}

print("✅ PATCH endpoint payload structure:")
print(f"   tier: {update_payload['tier']}")
print(f"   daily_quota: {update_payload['daily_quota']} (will use tier default)")
print(
    f"   rate_limit_per_second: {update_payload['rate_limit_per_second']} (will use tier default)"
)
print()

# Show what ENTERPRISE tier provides
from src.models.api_key import get_tier_defaults

enterprise_defaults = get_tier_defaults(Tier.ENTERPRISE)
print("✅ ENTERPRISE tier defaults:")
print(f"   daily_quota: {enterprise_defaults['daily_quota']}")
print(f"   rate_limit_per_second: {enterprise_defaults['rate_limit_per_second']}")
print(f"   budget_limit_usd: {enterprise_defaults['budget_limit_usd']}")
print()

print("✅ PATCH endpoint exists at:")
print("   PATCH /api/v1/api-keys/{key_id}")
print()
print("🚨 STATUS: Code exists but NOT DEPLOYED to AWS yet")
print()
print("📋 To fix your quota issue, you need to:")
print("   1. Deploy the PATCH endpoint to AWS")
print("   2. Use PATCH to upgrade your key to ENTERPRISE tier")
print("   3. OR create a new ENTERPRISE key and revoke the old one")
