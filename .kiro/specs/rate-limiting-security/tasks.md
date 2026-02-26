# Rate Limiting and API Security - Implementation Tasks

## Overview

This document breaks down the implementation of the rate limiting and API security feature into actionable tasks. Tasks are organized by phase and include acceptance criteria for validation.

**Total Estimated Time:** 3-4 days  
**Priority:** HIGH (Critical for cost control and monetization)

---

## Phase 1: Data Models and DynamoDB Schema (Day 1 Morning)

### Task 1.1: Create Pydantic Models for API Keys
**File:** `src/models/api_key.py`

**Implementation:**
- [ ] Create `Tier` enum (FREE, STARTER, PRO, ENTERPRISE)
- [ ] Create `APIKey` Pydantic model with all fields from design
- [ ] Add validation rules (format, rate limits, budget limits)
- [ ] Add DynamoDB schema mapping methods
- [ ] Create `APIKeyCreate` request model
- [ ] Create `APIKeyResponse` response model (excludes secret key)
- [ ] Create `APIKeyListResponse` model

**Acceptance Criteria:**
- All fields match design document Model 1
- Validation enforces api_key format: `^vj_(live|test)_[A-Za-z0-9+/]{32}$`
- rate_limit_per_second > 0
- daily_quota > 0
- budget_limit_usd >= 0
- expires_at in future if set

**Testing:**
- Unit tests for model validation
- Test invalid formats rejected
- Test tier-based defaults

---

### Task 1.2: Create Pydantic Models for Rate Limiting
**File:** `src/models/rate_limit.py`

**Implementation:**
- [ ] Create `RateLimitCounter` model
- [ ] Create `UsageRecord` model
- [ ] Create `BudgetTracking` model
- [ ] Create `SecurityEvent` model with `Severity` enum
- [ ] Add DynamoDB schema mapping for all models
- [ ] Add TTL field handling

**Acceptance Criteria:**
- All models match design document Models 2-5
- TTL fields properly configured
- Validation rules enforced
- DynamoDB PK/SK patterns correct

**Testing:**
- Unit tests for each model
- Test TTL calculation
- Test DynamoDB serialization

---

### Task 1.3: Update DynamoDB Table Schema in SAM Template
**File:** `template.yaml`

**Implementation:**
- [ ] Add GSI for API key lookups by organizer
- [ ] Add GSI for API key lookups by hackathon
- [ ] Add GSI for usage tracking by date
- [ ] Add GSI for budget tracking by entity type
- [ ] Add GSI for security events by API key prefix
- [ ] Configure TTL attribute for RateLimitCounters table
- [ ] Configure TTL attribute for SecurityEvents table
- [ ] Keep provisioned capacity at 5 RCU/5 WCU (free tier)

**Acceptance Criteria:**
- All GSIs match design document DynamoDB schemas
- TTL enabled on appropriate tables
- Free tier capacity maintained
- No breaking changes to existing table structure

**Testing:**
- Deploy to dev environment
- Verify GSIs created
- Test TTL expiration (manual verification)

---

## Phase 2: Core Services (Day 1 Afternoon)

### Task 2.1: Implement API Key Service
**File:** `src/services/api_key_service.py`

**Implementation:**
- [ ] Implement `create_api_key()` with secure key generation
- [ ] Implement `validate_api_key()` with expiration check
- [ ] Implement `rotate_api_key()` with grace period
- [ ] Implement `revoke_api_key()` (soft delete)
- [ ] Implement `list_api_keys()` for organizer
- [ ] Implement `get_api_key_by_id()`
- [ ] Add tier-based default limits helper
- [ ] Use `secrets.token_bytes(24)` for key generation

**Acceptance Criteria:**
- Keys match format: `vj_{env}_{32-char-base64}`
- Collision probability < 1 in 2^256
- Rotation creates new key, marks old as deprecated
- Grace period = 7 days
- Soft delete sets active=false

**Testing:**
- Unit tests for all methods
- Test key uniqueness (generate 1000 keys)
- Test rotation workflow
- Test expiration validation

---

### Task 2.2: Implement Usage Tracking Service
**File:** `src/services/usage_tracking_service.py`

**Implementation:**
- [ ] Implement `record_request()` for logging
- [ ] Implement `check_daily_quota()` with reset logic
- [ ] Implement `get_usage_summary()` with date range
- [ ] Implement `export_usage_csv()` for reporting
- [ ] Add quota reset at midnight UTC logic
- [ ] Add endpoint usage breakdown tracking

**Acceptance Criteria:**
- Quota resets at midnight UTC
- CSV export includes all required fields
- Usage summary aggregates correctly
- Failed requests excluded from quota

**Testing:**
- Unit tests for quota logic
- Test midnight UTC reset (mock time)
- Test CSV export format
- Integration test with DynamoDB

---

### Task 2.3: Implement Cost Estimation Service
**File:** `src/services/cost_estimation_service.py`

**Implementation:**
- [ ] Implement `estimate_submission_cost()` based on repo size
- [ ] Implement `estimate_hackathon_cost()` for batch
- [ ] Implement `check_budget_availability()`
- [ ] Add large repo premium (>100 files = +$0.10)
- [ ] Use historical averages for estimation
- [ ] Add 80% budget warning threshold

**Acceptance Criteria:**
- Estimates within 20% of actual costs
- Large repo premium applied correctly
- Budget warnings at 80% threshold
- Cost breakdown by agent included

**Testing:**
- Unit tests with mock repo data
- Test large repo premium
- Test budget availability checks
- Compare estimates vs actual costs

---

## Phase 3: Middleware Components (Day 2 Morning)

### Task 3.1: Implement Rate Limit Middleware
**File:** `src/api/middleware/rate_limit.py`

**Implementation:**
- [ ] Create `RateLimitMiddleware` class
- [ ] Implement sliding window counter algorithm
- [ ] Implement atomic counter increment in DynamoDB
- [ ] Add RFC 6585 rate limit headers
- [ ] Exempt /health and /docs endpoints
- [ ] Add API key validation
- [ ] Add daily quota check

**Acceptance Criteria:**
- Rate limit check < 5ms latency
- Sliding window resets every second
- Atomic increments (no race conditions)
- Headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- 429 response with Retry-After header

**Testing:**
- Unit tests with mocked DynamoDB
- Load test with concurrent requests
- Test atomic increment behavior
- Integration test with FastAPI

---

### Task 3.2: Implement Budget Enforcement Middleware
**File:** `src/api/middleware/budget.py`

**Implementation:**
- [ ] Create `BudgetMiddleware` class
- [ ] Implement multi-level budget checks
- [ ] Check per-submission cap ($0.50)
- [ ] Check per-hackathon budget
- [ ] Check per-API-key budget
- [ ] Send alerts at 50%, 80%, 90%, 100%
- [ ] Return 402 Payment Required if exceeded

**Acceptance Criteria:**
- All three budget levels enforced
- Alerts sent at correct thresholds
- 402 response includes cost details
- No eventual consistency issues

**Testing:**
- Unit tests for budget logic
- Test all three budget levels
- Test alert thresholds
- Integration test with analysis endpoint

---

### Task 3.3: Implement Security Logger Middleware
**File:** `src/api/middleware/security.py`

**Implementation:**
- [ ] Create `SecurityLoggerMiddleware` class
- [ ] Log all 401/403 authentication failures
- [ ] Log all 429 rate limit violations
- [ ] Log all 402 budget exceeded events
- [ ] Detect anomalies (>100 req/min)
- [ ] Mask sensitive data (only log key prefix)
- [ ] Store events in DynamoDB with TTL

**Acceptance Criteria:**
- All security events logged
- API key prefix only (first 8 chars)
- Anomaly detection triggers CloudWatch alarm
- 30-day TTL on security events
- No sensitive data in logs

**Testing:**
- Unit tests for event logging
- Test anomaly detection thresholds
- Test data masking
- Integration test with CloudWatch

---

### Task 3.4: Register Middleware in FastAPI App
**File:** `src/api/main.py`

**Implementation:**
- [ ] Add middleware stack to FastAPI app
- [ ] Order: RateLimitMiddleware → BudgetMiddleware → SecurityLoggerMiddleware
- [ ] Configure exempt paths
- [ ] Add error handlers for 429, 402, 401
- [ ] Add rate limit headers to all responses

**Acceptance Criteria:**
- Middleware executes in correct order
- Exempt paths bypass rate limiting
- Error responses include helpful messages
- Headers added to all responses

**Testing:**
- Integration tests with TestClient
- Test middleware order
- Test exempt paths
- Test error responses

---

## Phase 4: API Routes (Day 2 Afternoon)

### Task 4.1: Create API Key Management Routes
**File:** `src/api/routes/api_keys.py`

**Implementation:**
- [ ] POST /api/v1/api-keys - Create new API key
- [ ] GET /api/v1/api-keys - List all keys for organizer
- [ ] GET /api/v1/api-keys/{key_id} - Get key details
- [ ] POST /api/v1/api-keys/{key_id}/rotate - Rotate key
- [ ] DELETE /api/v1/api-keys/{key_id} - Revoke key
- [ ] Add authentication (organizer must own keys)
- [ ] Return secret key only on creation

**Acceptance Criteria:**
- All CRUD operations working
- Authentication enforced
- Secret key shown only once
- Rotation creates new key with grace period
- Soft delete on revocation

**Testing:**
- Integration tests for all endpoints
- Test authentication
- Test key visibility rules
- Test rotation workflow

---

### Task 4.2: Add Cost Estimation Endpoint
**File:** `src/api/routes/analysis.py`

**Implementation:**
- [ ] POST /api/v1/hackathons/{id}/analyze/estimate
- [ ] Call CostEstimationService
- [ ] Return cost breakdown by agent
- [ ] Include budget warnings
- [ ] Free endpoint (no quota consumption)

**Acceptance Criteria:**
- Estimate includes breakdown
- Budget warnings at 80% threshold
- No quota consumption
- Response time < 200ms

**Testing:**
- Integration test with mock hackathon
- Test cost breakdown accuracy
- Test budget warnings
- Test performance

---

### Task 4.3: Add Usage Analytics Endpoints
**File:** `src/api/routes/usage.py`

**Implementation:**
- [ ] GET /api/v1/usage/summary - Usage summary with date range
- [ ] GET /api/v1/usage/export - CSV export
- [ ] Add authentication (organizer only)
- [ ] Add date range validation
- [ ] Add pagination for large datasets

**Acceptance Criteria:**
- Summary includes all required metrics
- CSV export format correct
- Date range validation working
- Pagination for >1000 records

**Testing:**
- Integration tests for both endpoints
- Test date range filtering
- Test CSV format
- Test pagination

---

## Phase 5: CloudWatch Monitoring (Day 3 Morning)

### Task 5.1: Add CloudWatch Billing Alarms
**File:** `template.yaml`

**Implementation:**
- [ ] Create SNS topic for billing alerts
- [ ] Add alarm for total daily spend ($50 threshold)
- [ ] Add separate alarms for Bedrock, Lambda, DynamoDB, API Gateway
- [ ] Configure 1-hour evaluation period
- [ ] Add email subscription to SNS topic

**Acceptance Criteria:**
- All alarms created
- SNS topic configured
- Email notifications working
- Alarms trigger at correct thresholds

**Testing:**
- Deploy to dev environment
- Manually trigger alarm (set low threshold)
- Verify email received
- Reset thresholds to production values

---

### Task 5.2: Add Custom CloudWatch Metrics
**File:** `src/utils/cloudwatch.py`

**Implementation:**
- [ ] Create CloudWatch client wrapper
- [ ] Add metric for rate limit violations
- [ ] Add metric for budget exceeded events
- [ ] Add metric for authentication failures
- [ ] Add metric for anomaly detections
- [ ] Batch metric writes for efficiency

**Acceptance Criteria:**
- All metrics published
- Batch writes reduce API calls
- Metrics visible in CloudWatch dashboard
- No performance impact (<1ms)

**Testing:**
- Unit tests for metric publishing
- Integration test with CloudWatch
- Test batch writes
- Verify metrics in console

---

### Task 5.3: Create CloudWatch Dashboard
**File:** `template.yaml`

**Implementation:**
- [ ] Create dashboard resource
- [ ] Add widget for rate limit violations
- [ ] Add widget for budget tracking
- [ ] Add widget for authentication failures
- [ ] Add widget for API key usage
- [ ] Add widget for cost by service

**Acceptance Criteria:**
- Dashboard shows all key metrics
- Widgets update in real-time
- Dashboard accessible in console
- Useful for monitoring and debugging

**Testing:**
- Deploy dashboard
- Verify all widgets display data
- Test real-time updates
- Get feedback from team

---

## Phase 6: Streamlit UI Integration (Day 3 Afternoon)

### Task 6.1: Create API Key Management Page
**File:** `streamlit_ui/pages/5_🔑_API_Keys.py`

**Implementation:**
- [ ] Add page to Streamlit app
- [ ] Create API key list view with status
- [ ] Add create key form (hackathon, expiration, tier, limits)
- [ ] Display generated key once (copyable)
- [ ] Add revoke button with confirmation
- [ ] Add rotate button with grace period info
- [ ] Show usage stats (requests, quota, budget)

**Acceptance Criteria:**
- All CRUD operations working
- Key displayed once on creation
- Usage stats accurate
- Rotation workflow clear
- Revoke requires confirmation

**Testing:**
- Manual testing of all features
- Test key creation flow
- Test rotation workflow
- Test revoke confirmation

---

### Task 6.2: Add Usage Analytics Page
**File:** `streamlit_ui/pages/6_📊_Usage_Analytics.py`

**Implementation:**
- [ ] Add page to Streamlit app
- [ ] Display usage summary with date picker
- [ ] Show cost breakdown by hackathon/key
- [ ] Add CSV export button
- [ ] Show peak usage hours chart
- [ ] Show error rate by endpoint chart
- [ ] Add cost forecasting based on trends

**Acceptance Criteria:**
- All charts display correctly
- Date picker filters data
- CSV export works
- Forecasting shows trend
- Charts use Plotly

**Testing:**
- Manual testing with sample data
- Test date filtering
- Test CSV export
- Test chart interactions

---

## Phase 7: Testing and Validation (Day 4)

### Task 7.1: Write Unit Tests for Services
**Files:** `tests/unit/test_api_key_service.py`, `tests/unit/test_usage_tracking_service.py`, `tests/unit/test_cost_estimation_service.py`

**Implementation:**
- [ ] Test API key generation (uniqueness, format)
- [ ] Test key validation (expiration, active status)
- [ ] Test rotation workflow
- [ ] Test usage tracking and quota reset
- [ ] Test cost estimation accuracy
- [ ] Test budget availability checks
- [ ] Target: 90%+ coverage

**Acceptance Criteria:**
- All services have unit tests
- Coverage > 90%
- All edge cases covered
- Tests run in < 10 seconds

---

### Task 7.2: Write Property-Based Tests
**Files:** `tests/property/test_properties_rate_limiting.py`

**Implementation:**
- [ ] Property 1: Rate limit enforcement (count ≤ limit)
- [ ] Property 2: Budget non-violation (spend + cost ≤ budget → allowed)
- [ ] Property 3: API key uniqueness (all keys unique and valid format)
- [ ] Property 4: Quota reset consistency (midnight UTC reset)
- [ ] Property 5: Security event logging (errors → events)
- [ ] Property 6: Atomic counter increment (concurrent requests)
- [ ] Use Hypothesis library with 1000+ iterations

**Acceptance Criteria:**
- All 6 properties implemented
- 1000+ iterations per property
- All properties pass
- Tests find edge cases

---

### Task 7.3: Write Integration Tests
**Files:** `tests/integration/test_rate_limiting.py`, `tests/integration/test_api_keys.py`

**Implementation:**
- [ ] Test end-to-end rate limiting flow
- [ ] Test budget enforcement flow
- [ ] Test API key lifecycle (create → use → rotate → revoke)
- [ ] Test quota reset at midnight
- [ ] Test security event logging
- [ ] Use LocalStack for AWS services

**Acceptance Criteria:**
- All integration tests pass
- Tests use LocalStack
- Tests cover happy path and errors
- Tests run in < 60 seconds

---

### Task 7.4: Performance Testing
**Files:** `tests/performance/test_rate_limit_performance.py`

**Implementation:**
- [ ] Load test rate limit middleware (1000 concurrent requests)
- [ ] Measure rate limit check latency (target < 5ms)
- [ ] Test DynamoDB atomic increment performance
- [ ] Test middleware overhead (target < 10ms total)
- [ ] Generate performance report

**Acceptance Criteria:**
- Rate limit check < 5ms
- Middleware overhead < 10ms
- No race conditions under load
- Performance report generated

---

## Phase 8: Documentation and Deployment

### Task 8.1: Update API Documentation
**Files:** `README.md`, `docs/API.md`

**Implementation:**
- [ ] Document new API key endpoints
- [ ] Document rate limit headers
- [ ] Document error responses (429, 402)
- [ ] Add examples for all endpoints
- [ ] Update Swagger/OpenAPI spec

**Acceptance Criteria:**
- All new endpoints documented
- Examples include curl commands
- Error responses explained
- Swagger UI updated

---

### Task 8.2: Update TESTING.md
**File:** `TESTING.md`

**Implementation:**
- [ ] Add section for rate limiting tests
- [ ] Document property-based tests
- [ ] Add performance testing guide
- [ ] Document LocalStack setup for integration tests

**Acceptance Criteria:**
- All new tests documented
- Setup instructions clear
- Examples provided
- Troubleshooting section added

---

### Task 8.3: Deploy to Dev Environment
**Commands:** `make deploy-dev`

**Implementation:**
- [ ] Deploy updated SAM template
- [ ] Verify all DynamoDB tables created
- [ ] Verify GSIs created
- [ ] Verify CloudWatch alarms created
- [ ] Verify SNS topic created
- [ ] Test all endpoints in dev

**Acceptance Criteria:**
- Deployment successful
- All resources created
- No errors in CloudWatch logs
- All endpoints responding

---

### Task 8.4: Deploy to Production
**Commands:** `make deploy-prod`

**Implementation:**
- [ ] Deploy to production
- [ ] Verify all resources created
- [ ] Test critical paths
- [ ] Monitor CloudWatch for errors
- [ ] Verify billing alarms working
- [ ] Update live API documentation

**Acceptance Criteria:**
- Production deployment successful
- All tests passing
- No errors in first hour
- Billing alarms configured
- Documentation updated

---

## Success Criteria (Overall)

- ✅ 0 unauthorized cost overruns in first 90 days
- ✅ Rate limit check adds <5ms latency
- ✅ Actual costs within 10% of estimates
- ✅ <1% false positive rate on rate limiting
- ✅ Clear error messages with actionable guidance
- ✅ 90%+ test coverage for new code
- ✅ All 6 correctness properties validated
- ✅ Production deployment successful

---

## Risk Mitigation

**Risk 1: DynamoDB Throttling**
- Mitigation: Use provisioned capacity (5 RCU/5 WCU)
- Fallback: Exponential backoff with 3 retries
- Monitoring: CloudWatch alarm for throttling

**Risk 2: Rate Limit False Positives**
- Mitigation: Sliding window algorithm (not token bucket)
- Testing: Load test with 1000 concurrent requests
- Monitoring: Track false positive rate in CloudWatch

**Risk 3: Budget Enforcement Bypass**
- Mitigation: Multi-level checks (submission, hackathon, API key)
- Testing: Property-based tests for budget logic
- Monitoring: Alert on budget exceeded events

**Risk 4: Performance Degradation**
- Mitigation: Cache API key metadata (10min TTL)
- Testing: Performance tests for <5ms latency
- Monitoring: CloudWatch metrics for latency

---

## Dependencies

**Blocked By:**
- None (all prerequisites met)

**Blocks:**
- Monetization feature (requires API key tiers)
- Multi-tenant SaaS (requires API key scoping)

**External Dependencies:**
- DynamoDB (AWS Free Tier)
- CloudWatch (AWS Free Tier)
- SNS (AWS Free Tier)

---

## Notes

- All tasks follow existing project structure and conventions
- No breaking changes to existing API
- Backward compatible with current authentication
- Free tier capacity sufficient for MVP
- Can be deployed incrementally (phase by phase)
