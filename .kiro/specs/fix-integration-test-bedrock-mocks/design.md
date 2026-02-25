# Fix Integration Test Bedrock Mocks - Bugfix Design

## Overview

Integration tests are failing because mock Bedrock responses lack required Pydantic fields. The fix updates mock JSON responses in `test_orchestrator_enhanced.py` and `test_performance_90s.py` to include all mandatory fields defined in agent response schemas (`BugHunterResponse`, `PerformanceResponse`, `InnovationResponse`, `AIDetectionResponse`).

The approach is minimal: replace incomplete mock JSON strings with complete, schema-compliant templates. No changes to test logic, assertions, or mocking strategy are required.

## Glossary

- **Bug_Condition (C)**: Mock Bedrock responses missing required Pydantic fields (`prompt_version`, `summary`, `scores` sub-fields)
- **Property (P)**: Mock responses must validate successfully against Pydantic schemas without raising "Field required" errors
- **Preservation**: Test logic, assertions, latency simulation, and mocking strategy remain unchanged
- **BedrockClient.converse()**: The method mocked in integration tests that returns agent responses
- **BaseAgent.parse_response()**: The method that validates mock JSON against Pydantic schemas

## Bug Details

### Fault Condition

The bug manifests when integration tests mock `BedrockClient.converse()` with incomplete JSON responses. The `BaseAgent.parse_response()` method calls Pydantic validation, which fails because mock responses lack mandatory fields.

**Formal Specification:**
```
FUNCTION isBugCondition(mock_response)
  INPUT: mock_response of type dict (parsed JSON from mock)
  OUTPUT: boolean

  RETURN ("prompt_version" NOT IN mock_response)
         OR ("summary" NOT IN mock_response)
         OR ("scores" NOT IN mock_response)
         OR (mock_response["scores"] is empty dict)
         OR (required_score_fields_missing(mock_response["scores"], agent_type))
END FUNCTION
```

### Examples

- **BugHunter Mock (Current)**: `{"overall_score": 8.5, "confidence": 0.9, "evidence": []}` → Missing `prompt_version`, `summary`, `scores.code_quality`, `scores.security`, etc.
- **Performance Mock (Current)**: `{"overall_score": 7.5, "confidence": 0.85, "evidence": []}` → Missing `prompt_version`, `summary`, `scores.architecture`, `scores.database_design`, etc.
- **Innovation Mock (Current)**: `{"overall_score": 9.0, "confidence": 0.95, "evidence": []}` → Missing `prompt_version`, `summary`, `scores.technical_novelty`, etc.
- **AIDetection Mock (Current)**: `{"overall_score": 8.0, "confidence": 0.9, "evidence": []}` → Missing `prompt_version`, `summary`, `scores.commit_authenticity`, etc.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Latency simulation with `time.sleep()` must continue to work
- Test assertions for `component_performance`, `cost_records`, `analysis_duration_ms` must remain unchanged
- Graceful degradation tests (component failures) must continue to validate error handling
- CI/CD parsing integration tests must continue to mock `ActionsAnalyzer`
- Intelligence layer component mocks (team analyzer, strategy detector, brand voice transformer) must remain unchanged
- Evidence validation tests must continue to include valid evidence items
- 90-second performance target tests must continue to measure duration

**Scope:**
All test logic, assertions, and mocking strategies that do NOT involve the structure of mock Bedrock JSON responses should be completely unaffected by this fix.

## Hypothesized Root Cause

Based on the bug description, the root cause is:

1. **Incomplete Mock Templates**: The original mock responses were created before all Pydantic fields were finalized, resulting in minimal JSON structures like `{"overall_score": 8.5, "confidence": 0.9, "evidence": []}`

2. **Missing Nested Score Objects**: Each agent type requires a `scores` object with 5 specific sub-fields (e.g., BugHunter needs `code_quality`, `security`, `test_coverage`, `error_handling`, `dependency_hygiene`), but mocks use empty `{}` or omit the field entirely

3. **Missing Base Fields**: All agent responses inherit from `BaseAgentResponse`, which requires `prompt_version` and `summary` fields that were not included in the original mocks

4. **No Schema Validation During Mock Creation**: The mocks were likely written manually without running them through Pydantic validation, so the missing fields went undetected until tests were executed

## Correctness Properties

Property 1: Fault Condition - Mock Responses Validate Successfully

_For any_ mock Bedrock response where the bug condition holds (missing required Pydantic fields), the fixed mock response SHALL include all required fields (`prompt_version`, `summary`, `scores` with all sub-fields) such that `BaseAgent.parse_response()` successfully validates and returns the appropriate agent response instance without raising Pydantic validation errors.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7**

Property 2: Preservation - Test Logic and Assertions Unchanged

_For any_ test logic, assertion, or mocking strategy that does NOT involve the structure of mock Bedrock JSON responses, the fixed code SHALL produce exactly the same behavior as the original code, preserving latency simulation, performance tracking validation, graceful degradation testing, CI/CD integration testing, intelligence layer component mocking, evidence validation, and performance target measurement.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**Files**:
- `tests/integration/test_orchestrator_enhanced.py`
- `tests/integration/test_performance_90s.py`

**Specific Changes**:

1. **Create Complete Mock Response Templates**: Define JSON templates for each agent type with all required fields

2. **BugHunter Mock Template**:
   ```json
   {
     "agent": "bug_hunter",
     "prompt_version": "v1",
     "overall_score": 8.5,
     "summary": "Code quality is strong with good testing practices.",
     "confidence": 0.9,
     "scores": {
       "code_quality": 8.5,
       "security": 9.0,
       "test_coverage": 7.5,
       "error_handling": 8.0,
       "dependency_hygiene": 8.5
     },
     "evidence": [],
     "ci_observations": {
       "has_ci": true,
       "has_automated_tests": true,
       "has_linting": false,
       "has_security_scanning": false
     }
   }
   ```

3. **Performance Mock Template**:
   ```json
   {
     "agent": "performance",
     "prompt_version": "v1",
     "overall_score": 7.5,
     "summary": "Architecture is well-structured with room for optimization.",
     "confidence": 0.85,
     "scores": {
       "architecture": 8.0,
       "database_design": 7.0,
       "api_design": 7.5,
       "scalability": 7.0,
       "resource_efficiency": 8.0
     },
     "evidence": [],
     "ci_observations": {
       "has_ci": true,
       "deployment_sophistication": "basic"
     },
     "tech_stack_assessment": {
       "technologies_identified": ["Python", "FastAPI"],
       "stack_appropriateness": "Good choice for API development",
       "notable_choices": "Modern async framework"
     }
   }
   ```

4. **Innovation Mock Template**:
   ```json
   {
     "agent": "innovation",
     "prompt_version": "v1",
     "overall_score": 9.0,
     "summary": "Highly innovative approach with creative solutions.",
     "confidence": 0.95,
     "scores": {
       "technical_novelty": 9.0,
       "creative_problem_solving": 8.5,
       "architecture_elegance": 9.0,
       "readme_quality": 8.0,
       "demo_potential": 9.5
     },
     "evidence": [],
     "innovation_highlights": ["Novel algorithm", "Elegant design"],
     "development_story": "Team showed strong iteration",
     "hackathon_context_assessment": "Well-suited for hackathon constraints"
   }
   ```

5. **AIDetection Mock Template**:
   ```json
   {
     "agent": "ai_detection",
     "prompt_version": "v1",
     "overall_score": 8.0,
     "summary": "Development patterns indicate authentic human work.",
     "confidence": 0.9,
     "scores": {
       "commit_authenticity": 8.5,
       "development_velocity": 8.0,
       "authorship_consistency": 8.0,
       "iteration_depth": 7.5,
       "ai_generation_indicators": 8.5
     },
     "evidence": [],
     "commit_analysis": {
       "total_commits": 50,
       "avg_lines_per_commit": 45.0,
       "largest_commit_lines": 200,
       "commit_frequency_pattern": "steady",
       "meaningful_message_ratio": 0.8
     },
     "ai_policy_observation": "No significant AI generation detected"
   }
   ```

6. **Replace Mock Responses**: Update all `mock_bedrock.converse.return_value` assignments in both test files to use the complete templates above

7. **Agent-Specific Mocks**: For tests that mock specific agents, use the corresponding template (e.g., BugHunter tests use BugHunter template)

8. **Multi-Agent Mocks**: For tests that run multiple agents, use `side_effect` to return different templates based on call order or use a helper function to return the appropriate template based on the system prompt content

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Run the existing integration tests on UNFIXED code to observe Pydantic validation failures. Examine the exact error messages to confirm which fields are missing.

**Test Cases**:
1. **BugHunter Validation Test**: Run `test_analyze_submission_with_intelligence_layer` (will fail with "4 validation errors for BugHunterResponse")
2. **Performance Validation Test**: Run `test_performance_target_90_seconds` (will fail with validation errors for PerformanceResponse)
3. **Multi-Agent Test**: Run `test_analyze_submission_all_agents` (will fail with validation errors for all 4 agent types)
4. **Graceful Degradation Test**: Run `test_graceful_degradation_agent_failure` (may fail if mock responses are incomplete)

**Expected Counterexamples**:
- Pydantic validation errors: "Field required" for `prompt_version`, `summary`
- Pydantic validation errors: "Field required" for `scores.code_quality`, `scores.architecture`, etc.
- Possible causes: incomplete mock JSON, missing nested objects, missing base fields

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL mock_response WHERE isBugCondition(mock_response) DO
  fixed_mock := add_required_fields(mock_response, agent_type)
  agent_response := BaseAgent.parse_response(fixed_mock)
  ASSERT agent_response is valid instance of agent response type
  ASSERT no Pydantic validation errors raised
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL test_logic WHERE NOT involves_mock_json_structure(test_logic) DO
  ASSERT test_behavior_after_fix(test_logic) = test_behavior_before_fix(test_logic)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for test assertions and mocking strategies, then verify these continue to work after fixing mock responses.

**Test Cases**:
1. **Latency Simulation Preservation**: Verify that `time.sleep()` calls in mocks continue to simulate realistic API latency
2. **Performance Tracking Preservation**: Verify that tests continue to validate `component_performance`, `cost_records`, and `analysis_duration_ms`
3. **Graceful Degradation Preservation**: Verify that component failure tests continue to validate error handling
4. **Intelligence Layer Preservation**: Verify that team analyzer, strategy detector, and brand voice transformer mocks continue to work

### Unit Tests

- Test that each mock template validates successfully against its Pydantic schema
- Test that mock responses with missing fields raise validation errors (negative test)
- Test that mock responses with extra fields are accepted (Pydantic ignores extra fields by default)

### Property-Based Tests

- Generate random valid mock responses and verify they all validate successfully
- Generate random incomplete mock responses and verify they all fail validation
- Test that all combinations of agent types and mock templates work correctly

### Integration Tests

- Run all 7 tests in `test_orchestrator_enhanced.py` and verify they pass
- Run all 5 tests in `test_performance_90s.py` and verify they pass
- Verify that test execution time remains similar (latency simulation preserved)
- Verify that all test assertions continue to pass with the same expected values
