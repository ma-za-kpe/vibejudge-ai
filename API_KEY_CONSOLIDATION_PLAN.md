# API Key System Consolidation Plan

## Problem Statement
VibeJudge currently has TWO conflicting API key systems that don't work together, causing authentication failures and security gaps.

## Decision: Keep Advanced API Key System

### Why Advanced System Wins
1. **Rate Limiting**: 2 req/sec, 100/day (prevents abuse)
2. **Budget Control**: $10 limit for FREE tier (prevents cost explosion)
3. **Tier System**: Can upgrade users to STARTER/PRO/ENTERPRISE
4. **Expiration**: Security best practice
5. **Multiple Keys**: Users can have dev/prod keys
6. **Industry Standard Format**: `vj_live_xxx` (like Stripe/GitHub)

## Summary

Fixed the public hackathons endpoint by creating a dedicated public router. The endpoint now works without authentication and returns only CONFIGURED hackathons with minimal public data.

Created comprehensive plan for API key system consolidation to remove the conflicting simple key system and use only the Advanced API key system with rate limiting, budget control, and proper security features.

