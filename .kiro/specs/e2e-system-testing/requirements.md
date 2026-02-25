# End-to-End System Testing - Requirements

## Overview

Validate the complete VibeJudge AI platform (Backend API + Streamlit Dashboard) with comprehensive end-to-end tests covering full user workflows, error scenarios, performance benchmarks, and security validation.

## Goals

- Verify full organizer workflow from login to results viewing
- Test error handling and recovery across frontend and backend
- Validate performance under load (200 concurrent submissions)
- Ensure security controls prevent unauthorized access and cost abuse
- Automate E2E tests for regression prevention
- Document test coverage and pass/fail criteria

## Non-Goals

- Unit testing (already covered in backend and frontend)
- Load testing beyond 200 concurrent users
- Penetration testing (manual security audit later)
- Cross-browser testing (Streamlit works on modern browsers)

---

## Requirements

### Requirement 1: Full Organizer Workflow Test

**User Story:** As a hackathon organizer, I want to verify the complete platform workflow works end-to-end.

**Acceptance Criteria:**
1.1. Test creates organizer account and receives API key
1.2. Test authenticates in Streamlit dashboard with API key
1.3. Test creates a new hackathon with custom rubric
1.4. Test retrieves hackathon stats (0 submissions initially)
1.5. Test submits 3 GitHub repositories for analysis
1.6. Test triggers batch analysis with cost estimate
1.7. Test monitors progress until completion (all 3 analyzed)
1.8. Test views leaderboard with correct rankings
1.9. Test drills into individual scorecard with file:line citations
1.10. Test accesses intelligence dashboard with hiring insights

### Requirement 2: Error Handling and Recovery

**User Story:** As a platform operator, I want to verify the system handles errors gracefully without data loss.

**Acceptance Criteria:**
2.1. Invalid API key returns 401 and shows error message in UI
2.2. Budget exceeded (402) stops analysis and shows clear message
2.3. Analysis conflict (409) prevents duplicate jobs
2.4. Invalid GitHub URL (422) shows validation error before submission
2.5. Backend timeout shows retry button in UI
2.6. Network failure displays user-friendly error with retry
2.7. Failed submission marked as "failed" in dashboard with error details
2.8. Backend Lambda timeout (15min) gracefully terminates with partial results
2.9. Bedrock rate limit (429) triggers exponential backoff retry
2.10. Invalid rubric JSON shows validation error on hackathon creation

### Requirement 3: Performance Benchmarks

**User Story:** As a business owner, I want to know the system can handle Ghana Innovation Challenge scale (200 teams).

**Acceptance Criteria:**
3.1. Dashboard loads in <2 seconds with empty hackathon
3.2. Dashboard loads in <3 seconds with 200 submissions
3.3. Leaderboard search/filter responds in <500ms
3.4. Batch analysis of 200 submissions completes in <30 minutes
3.5. Individual submission analysis completes in <2 minutes
3.6. API Gateway handles 10 requests/second without throttling
3.7. CloudWatch shows <5% error rate during load test
3.8. DynamoDB read latency stays under 10ms (p99)
3.9. Step Functions successfully orchestrates 200 parallel Lambda invocations
3.10. Total cost for 200 submissions is within 10% of estimate ($12.60 ± $1.26)

### Requirement 4: Security Validation

**User Story:** As a security engineer, I want to verify the platform prevents unauthorized access and abuse.

**Acceptance Criteria:**
4.1. Unauthenticated requests to /hackathons return 401
4.2. API key from Hackathon A cannot access Hackathon B data
4.3. Expired API keys are rejected with 401
4.4. Rate limiting kicks in after 10 req/sec from single IP
4.5. SQL injection attempts in team names are escaped
4.6. XSS attempts in descriptions are sanitized
4.7. Budget limits enforce cost caps (test with $1 limit)
4.8. CloudWatch logs do not contain API keys or sensitive data
4.9. CORS headers only allow configured origins
4.10. HTTPS enforced (HTTP requests redirect to HTTPS)

### Requirement 5: Data Consistency and Integrity

**User Story:** As a developer, I want to verify data consistency across DynamoDB, Step Functions, and API responses.

**Acceptance Criteria:**
5.1. Submission count in /hackathons/{id}/stats matches DynamoDB query
5.2. Leaderboard rankings match sorted overall_score values
5.3. Cost tracking matches sum of individual agent costs
5.4. Team member count matches unique contributors in scorecard
5.5. Analysis status updates in real-time (polling interval <5 seconds)
5.6. Concurrent submissions don't create duplicate analysis jobs
5.7. Failed analysis updates submission status to "failed" in database
5.8. Partial results are saved if Lambda times out mid-analysis
5.9. Intelligence aggregation matches sum of individual scorecards
5.10. Repository metadata (languages, commits) matches GitHub API

### Requirement 6: Edge Cases and Boundary Conditions

**User Story:** As a QA engineer, I want to test uncommon scenarios that could break the system.

**Acceptance Criteria:**
6.1. Empty GitHub repository (0 files) returns validation error
6.2. Repository with 500+ files completes without timeout
6.3. Repository with non-UTF8 filenames handles gracefully
6.4. Team name with 200 characters displays correctly in UI
6.5. Hackathon with 0 submissions shows "No data" message
6.6. Analysis of repository with no code files (only markdown) completes
6.7. Very long commit messages (5000+ chars) don't break parsing
6.8. Repository with 100+ contributors completes team dynamics analysis
6.9. Budget limit of $0.01 stops analysis immediately
6.10. Hackathon name with special characters (!@#$%^&*) stores correctly

### Requirement 7: Integration Points Validation

**User Story:** As an integration engineer, I want to verify all external service integrations work correctly.

**Acceptance Criteria:**
7.1. Amazon Bedrock Claude Sonnet 4 API returns valid agent analysis
7.2. Amazon Bedrock Nova Lite API returns valid intelligence insights
7.3. GitHub API successfully clones public repositories
7.4. GitHub API handles private repository access errors (403)
7.5. DynamoDB single-table queries return correct partition/sort key data
7.6. Step Functions state machine transitions through all states correctly
7.7. CloudWatch Logs capture all Lambda execution logs
7.8. API Gateway request/response transformations preserve data integrity
7.9. S3 (if used) stores repository snapshots with correct metadata
7.10. EventBridge (if used) triggers scheduled analysis jobs

### Requirement 8: User Interface Validation

**User Story:** As a UI/UX designer, I want to verify the Streamlit dashboard provides good user experience.

**Acceptance Criteria:**
8.1. Login form shows clear error for wrong API key
8.2. Loading spinners display during API calls >500ms
8.3. Progress bar updates in real-time during analysis
8.4. Error messages are user-friendly (no stack traces shown)
8.5. Pagination works correctly with 200+ submissions
8.6. Search filters results without page reload
8.7. Sort dropdown changes leaderboard order correctly
8.8. Team scorecard displays all 4 agent results in expandable sections
8.9. Charts render correctly (technology trends, progress bars)
8.10. Mobile responsive design works on viewport width <768px

### Requirement 9: Cost Tracking Accuracy

**User Story:** As a business owner, I want to verify cost tracking is accurate within 1% margin.

**Acceptance Criteria:**
9.1. Single submission cost matches Bedrock token usage × pricing
9.2. Batch analysis cost equals sum of individual submission costs
9.3. Intelligence layer cost (Nova Lite) tracked separately
9.4. Cost estimate before analysis is within 10% of actual cost
9.5. DynamoDB costs are negligible (<$0.01 per 200 submissions)
9.6. Lambda compute costs are tracked in CloudWatch
9.7. API Gateway costs correlate with request count
9.8. Step Functions costs match number of state transitions
9.9. Total event cost matches: Bedrock + Lambda + API Gateway + Step Functions + DynamoDB
9.10. Cost breakdown by agent shown in scorecard adds up to total

### Requirement 10: Automated Test Suite

**User Story:** As a DevOps engineer, I want automated E2E tests that can run on every deployment.

**Acceptance Criteria:**
10.1. Test suite runs via `pytest tests/e2e/` command
10.2. Tests use production API endpoint (not mocked)
10.3. Tests clean up created resources (hackathons, submissions) after run
10.4. Test report shows pass/fail for each workflow
10.5. Tests can run in CI/CD pipeline (GitHub Actions)
10.6. Flaky tests are retried automatically (max 3 retries)
10.7. Test fixtures create reusable test data (sample repos, API keys)
10.8. Test execution time <10 minutes for full suite
10.9. Test coverage report shows which API endpoints are tested
10.10. Tests can run against both dev and prod environments

---

## Technical Constraints

1. **Test Framework:** pytest with requests library
2. **Test Data:** Use real GitHub repositories (public, non-sensitive)
3. **API Endpoint:** https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev
4. **Cleanup:** Delete test hackathons after each run to avoid clutter
5. **Parallelization:** Tests must be independent (no shared state)
6. **Timeout:** Each test has 5-minute timeout

## Dependencies

- Production backend API deployed and accessible
- Streamlit dashboard deployed (AWS ECS or Streamlit Cloud)
- Valid API key for testing (with generous rate limits)
- GitHub test repositories (3-5 sample repos of varying sizes)
- AWS credentials for CloudWatch log inspection

## Success Metrics

- **Coverage:** 90%+ of API endpoints tested
- **Reliability:** <5% flaky test rate
- **Performance:** Full suite runs in <10 minutes
- **Pass Rate:** 100% on main branch
- **Documentation:** All test scenarios documented with expected results

## Out of Scope

- Browser automation (Selenium/Playwright) - Streamlit testing is complex
- Chaos engineering (intentional service failures)
- Compliance testing (SOC2, GDPR, HIPAA)
- Internationalization testing (English only)
