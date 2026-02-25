# Rate Limiting and API Security - Requirements

## Overview

Implement comprehensive rate limiting, API key scoping, quota management, and security controls to prevent abuse, protect against unauthorized usage, and prepare the platform for monetization.

## Goals

- Prevent API abuse and cost runaway from malicious actors
- Implement per-API-key rate limiting and quota management
- Add API key scoping (per-hackathon, expiring keys)
- Set up CloudWatch billing alerts and cost monitoring
- Enforce budget caps at multiple levels (per-submission, per-hackathon, per-API-key)
- Log suspicious activity for security monitoring
- Prepare foundation for multi-tenant SaaS architecture

## Non-Goals

- DDoS protection at network layer (use AWS Shield/WAF later)
- IP-based geofencing or country blocking
- OAuth/SAML authentication (API keys sufficient for now)
- Advanced fraud detection (machine learning-based)

---

## Requirements

### Requirement 1: API Gateway Throttling

**User Story:** As a platform operator, I want global rate limits to prevent any single client from overwhelming the API.

**Acceptance Criteria:**
1.1. API Gateway enforces 10 requests per second rate limit globally
1.2. Burst limit set to 20 concurrent requests
1.3. Throttled requests return 429 Too Many Requests with Retry-After header
1.4. Throttle metrics visible in CloudWatch dashboard
1.5. Throttling applies to all endpoints except /health
1.6. Rate limits configurable via SAM template parameters

### Requirement 2: Per-API-Key Rate Limiting

**User Story:** As a platform operator, I want different rate limits for different API keys based on customer tier.

**Acceptance Criteria:**
2.1. Each API key has rate_limit_per_second field in DynamoDB
2.2. Lambda middleware enforces per-key rate limits using DynamoDB counters
2.3. Rate limit counter resets every second (sliding window)
2.4. Exceeded rate limit returns 429 with message: "Rate limit: {limit} req/sec"
2.5. Rate limits vary by tier: Free=2/sec, Starter=5/sec, Pro=10/sec, Enterprise=50/sec
2.6. Rate limit headers returned in response: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

### Requirement 3: API Key Scoping and Metadata

**User Story:** As a security engineer, I want API keys scoped to specific hackathons with expiration dates and metadata.

**Acceptance Criteria:**
3.1. API keys have schema: {api_key, tenant_id, hackathon_id, created_at, expires_at, active, rate_limit, daily_quota, budget_limit_usd}
3.2. Expired API keys (expires_at < now) return 401 Unauthorized
3.3. Inactive API keys (active=false) return 401 Unauthorized
3.4. API key scoped to hackathon_id cannot access other hackathons
3.5. API key creation endpoint: POST /api-keys with parameters: hackathon_id, expires_at, rate_limit, budget_limit
3.6. API key revocation endpoint: DELETE /api-keys/{key_id} sets active=false
3.7. API key listing endpoint: GET /api-keys returns all keys for authenticated user

### Requirement 4: Daily Quota Management

**User Story:** As a business owner, I want to limit daily API usage per key to control costs.

**Acceptance Criteria:**
4.1. Each API key has daily_quota field (e.g., 100 submissions/day)
4.2. DynamoDB tracks daily usage: {api_key, date, submission_count}
4.3. Quota resets at midnight UTC
4.4. Exceeded quota returns 429 with message: "Daily quota exceeded. Resets at {timestamp}"
4.5. Quota headers in response: X-Quota-Limit, X-Quota-Remaining, X-Quota-Reset
4.6. Quota tracking excludes failed/rejected submissions
4.7. Free tier: 100/day, Starter: 500/day, Pro: 2500/day, Enterprise: unlimited

### Requirement 5: Budget Limits (Multi-Level)

**User Story:** As a platform operator, I want budget caps at submission, hackathon, and API key levels to prevent cost overruns.

**Acceptance Criteria:**
5.1. Per-submission budget cap: MAX_COST_PER_SUBMISSION = $0.50 (configurable)
5.2. Submission exceeding cap returns 402 with estimated cost before analysis starts
5.3. Per-hackathon budget: budget_limit_usd field enforced in real-time
5.4. Per-API-key budget: budget_limit_usd tracked cumulatively across all usage
5.5. Budget exceeded returns 402 with message: "Budget limit ${limit} reached. Current spend: ${current}"
5.6. Cost tracking updated after each successful analysis
5.7. Budget alerts sent at 50%, 80%, 90%, 100% thresholds

### Requirement 6: CloudWatch Billing Alerts

**User Story:** As a business owner, I want to be notified immediately if AWS costs exceed expected thresholds.

**Acceptance Criteria:**
6.1. CloudWatch billing alarm triggers at $50/day spend
6.2. Alarm sends SNS notification to configured email/Slack
6.3. Alarm monitors EstimatedCharges metric
6.4. Alarm has 1-hour evaluation period
6.5. Separate alarms for: Bedrock, Lambda, DynamoDB, API Gateway
6.6. Budget alerts configurable via SAM template parameters
6.7. Alarm dashboard shows spend by service in real-time

### Requirement 7: Cost Estimation Endpoint

**User Story:** As an organizer, I want to know estimated cost before triggering expensive analysis.

**Acceptance Criteria:**
7.1. Endpoint POST /hackathons/{id}/estimate returns {estimated_cost_usd, submission_count}
7.2. Estimate based on: submission_count × $0.063 (average per submission)
7.3. Estimate includes breakdown: {bedrock_cost, lambda_cost, total}
7.4. Large repositories (>100 files) estimated at $0.10/submission
7.5. Estimate compares against remaining budget
7.6. Response includes warning if estimate exceeds 80% of budget
7.7. Estimation is free (doesn't consume quota)

### Requirement 8: API Key Management UI (Streamlit)

**User Story:** As an organizer, I want to create and manage API keys from the dashboard without AWS console access.

**Acceptance Criteria:**
8.1. Dashboard page: "API Keys" shows list of all keys
8.2. Create key form: hackathon selection, expiration date, rate limit, quota, budget
8.3. Key generated with prefix vj_live_ for production or vj_test_ for testing
8.4. Generated key displayed once (copyable, not stored in frontend)
8.5. Key list shows: created date, expires date, status (active/expired), usage stats
8.6. Revoke button sets active=false (soft delete)
8.7. Usage stats: requests today, quota remaining, budget spent/remaining

### Requirement 9: Security Logging and Monitoring

**User Story:** As a security engineer, I want comprehensive logs of suspicious activity for incident response.

**Acceptance Criteria:**
9.1. Log all 401/403 authentication failures with API key prefix (first 8 chars)
9.2. Log all 429 rate limit violations with API key and endpoint
9.3. Log all 402 budget exceeded events with cost details
9.4. Log unusual patterns: >100 requests from single key in 1 minute
9.5. CloudWatch Insights queries for: failed auth, rate limits, budget alerts
9.6. Logs exclude full API keys (only prefix) and sensitive data
9.7. Logs retained for 30 days
9.8. Anomaly detection: alert if request volume increases >200% vs 7-day average

### Requirement 10: IP-Based Rate Limiting (Future-Proofing)

**User Story:** As a security engineer, I want to block abusive IPs even if they rotate API keys.

**Acceptance Criteria:**
10.1. DynamoDB table tracks: {ip_address, requests_per_minute}
10.2. IP exceeding 50 requests/minute gets temporary block (5 minutes)
10.3. Blocked IP returns 429 with message: "IP temporarily blocked. Try again in {minutes} minutes"
10.4. Whitelist IPs for known good actors (CI/CD servers)
10.5. IP blocks logged to CloudWatch for security review
10.6. IP blocks expire automatically (no manual intervention)
10.7. IP rate limiting bypassed for requests from AWS service IPs (Lambda)

### Requirement 11: API Key Rotation

**User Story:** As a security-conscious organizer, I want to rotate API keys periodically without service disruption.

**Acceptance Criteria:**
11.1. Endpoint POST /api-keys/{id}/rotate generates new key, marks old as deprecated
11.2. Deprecated keys work for 7-day grace period
11.3. Deprecated key responses include header: X-API-Key-Deprecated: true, X-Deprecation-Date: {date}
11.4. Email notification sent when key deprecated
11.5. After grace period, deprecated key returns 401 with rotation instructions
11.6. Dashboard shows warning banner when using deprecated key
11.7. Rotation history logged in DynamoDB audit table

### Requirement 12: Usage Analytics and Reporting

**User Story:** As a business owner, I want detailed usage reports to understand customer behavior and optimize pricing.

**Acceptance Criteria:**
12.1. DynamoDB stores usage events: {tenant_id, timestamp, endpoint, status_code, response_time_ms, cost_usd}
12.2. Dashboard endpoint: GET /usage/summary returns {total_requests, total_cost, avg_cost_per_submission, submissions_by_day}
12.3. CSV export endpoint: GET /usage/export?start_date={}&end_date={} returns usage data
12.4. Analytics show: most active API keys, peak usage hours, error rates by endpoint
12.5. Cost attribution: track which hackathons/keys generate most AWS costs
12.6. Usage forecasting: predict next month's cost based on 30-day trend
12.7. Anomaly detection: flag unusual cost spikes (>3 std dev from mean)

---

## Technical Constraints

1. **Rate Limit Storage:** DynamoDB with TTL for automatic cleanup
2. **Rate Limit Algorithm:** Sliding window counter (not token bucket)
3. **Budget Tracking:** Real-time updates in DynamoDB (not eventual consistency)
4. **API Key Format:** `vj_{env}_{32-char-base64}` (e.g., vj_live_abc123...)
5. **Cost Precision:** Track to 4 decimal places ($0.0001)
6. **Response Headers:** Follow RFC 6585 for rate limiting headers

## Dependencies

- DynamoDB tables: api_keys, usage_tracking, rate_limit_counters
- CloudWatch Logs and Alarms
- SNS topic for billing alerts
- Lambda middleware for rate limiting logic
- Existing authentication system

## Success Metrics

- **Security:** 0 unauthorized cost overruns in first 90 days
- **Reliability:** <1% false positive rate on rate limiting
- **Performance:** Rate limit check adds <5ms latency
- **Cost Control:** Actual costs within 10% of estimates
- **User Experience:** Clear error messages with actionable guidance

## Out of Scope

- OAuth/OpenID Connect authentication
- Geographic rate limiting (per region)
- Custom rate limit algorithms (e.g., leaky bucket)
- Payment gateway integration (covered in monetization spec)
