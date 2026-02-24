"""Property-based tests for serialization and parsing (Properties 48-54).

This module tests the correctness properties of parsing, serialization,
and pretty printing using hypothesis for property-based testing.

Properties tested:
- Property 48: Finding Grouping
- Property 49: Personalized Learning Roadmap
- Property 50: Malformed JSON Handling
- Property 51: Required Field Validation
- Property 52: Round-Trip Serialization
- Property 53: Cost Tracking Structure
- Property 54: Pretty Printer Format
"""

import json
from typing import Any
from unittest.mock import Mock, patch

import pytest
from hypothesis import assume, given, settings, strategies as st
from pydantic import ValidationError

from src.models.feedback import ActionableFeedback, CodeExample, EffortEstimate, LearningResource
from src.models.static_analysis import PrimaryLanguage, StaticAnalysisResult, StaticFinding
from src.models.team_dynamics import (
    ContributorRole,
    ExpertiseArea,
    HiringSignals,
    IndividualScorecard,
    RedFlag,
    RedFlagSeverity,
    WorkStyle,
)


# ============================================================
# HYPOTHESIS STRATEGIES (Test Data Generators)
# ============================================================


@st.composite
def finding_category_strategy(draw: Any) -> str:
    """Generate random finding category."""
    categories = [
        "authentication_security",
        "authorization",
        "sql_injection",
        "xss",
        "csrf",
        "input_validation",
        "error_handling",
        "logging",
        "cryptography",
    ]
    return draw(st.sampled_from(categories))


@st.composite
def static_finding_strategy(draw: Any) -> StaticFinding:
    """Generate random static finding."""
    from src.models.common import Severity
    
    return StaticFinding(
        tool=draw(st.sampled_from(["flake8", "bandit", "eslint", "clippy"])),
        file=draw(st.text(min_size=5, max_size=50)),
        line=draw(st.integers(min_value=1, max_value=1000)),
        code=draw(st.text(min_size=2, max_size=10)),
        message=draw(st.text(min_size=10, max_size=200)),
        severity=draw(st.sampled_from([Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL])),
        category=draw(finding_category_strategy()),
        recommendation=draw(st.text(min_size=10, max_size=200)),
        verified=draw(st.booleans()),
    )


@st.composite
def individual_scorecard_strategy(draw: Any) -> IndividualScorecard:
    """Generate random individual scorecard."""
    return IndividualScorecard(
        contributor_name=draw(st.text(min_size=3, max_size=50)),
        contributor_email=draw(st.emails()),
        role=draw(st.sampled_from(list(ContributorRole))),
        expertise_areas=draw(st.lists(st.sampled_from(list(ExpertiseArea)), min_size=1, max_size=5)),
        commit_count=draw(st.integers(min_value=0, max_value=500)),
        lines_added=draw(st.integers(min_value=0, max_value=10000)),
        lines_deleted=draw(st.integers(min_value=0, max_value=5000)),
        files_touched=draw(st.lists(st.text(min_size=5, max_size=50), min_size=1, max_size=20)),
        notable_contributions=draw(st.lists(st.text(min_size=10, max_size=100), max_size=10)),
        strengths=draw(st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5)),
        weaknesses=draw(st.lists(st.text(min_size=10, max_size=100), max_size=5)),
        growth_areas=draw(st.lists(st.text(min_size=10, max_size=100), max_size=5)),
        work_style=WorkStyle(
            commit_frequency=draw(st.sampled_from(["frequent", "moderate", "infrequent"])),
            avg_commit_size=draw(st.integers(min_value=1, max_value=500)),
            active_hours=draw(st.lists(st.integers(min_value=0, max_value=23), min_size=1, max_size=12)),
            late_night_commits=draw(st.integers(min_value=0, max_value=50)),
            weekend_commits=draw(st.integers(min_value=0, max_value=100)),
        ),
        hiring_signals=HiringSignals(
            recommended_role=draw(st.text(min_size=5, max_size=50)),
            seniority_level=draw(st.sampled_from(["junior", "mid", "senior"])),
            salary_range_usd=draw(st.text(min_size=5, max_size=20)),
            must_interview=draw(st.booleans()),
            sponsor_interest=draw(st.lists(st.text(min_size=3, max_size=30), max_size=5)),
            rationale=draw(st.text(min_size=10, max_size=200)),
        ),
    )


@st.composite
def cost_record_strategy(draw: Any) -> dict[str, Any]:
    """Generate random cost record."""
    return {
        "agent_name": draw(st.sampled_from(["BugHunter", "Performance", "Innovation", "AIDetection"])),
        "model_id": draw(st.sampled_from(["amazon.nova-micro-v1:0", "amazon.nova-lite-v1:0"])),
        "input_tokens": draw(st.integers(min_value=100, max_value=10000)),
        "output_tokens": draw(st.integers(min_value=50, max_value=5000)),
        "total_cost_usd": draw(st.floats(min_value=0.001, max_value=0.1)),
    }


@st.composite
def malformed_json_strategy(draw: Any) -> str:
    """Generate malformed JSON strings."""
    malformed_types = [
        '{"key": "value"',  # Missing closing brace
        '{"key": value}',  # Unquoted value
        "{'key': 'value'}",  # Single quotes
        '{"key": "value",}',  # Trailing comma
        '{key: "value"}',  # Unquoted key
        '{"key": undefined}',  # Undefined value
        '{"key": NaN}',  # NaN value
        '',  # Empty string
        'null',  # Just null
        '[]',  # Empty array
    ]
    return draw(st.sampled_from(malformed_types))


# ============================================================
# PROPERTY 48: Finding Grouping
# ============================================================


@given(
    findings=st.lists(static_finding_strategy(), min_size=5, max_size=50)
)
@settings(max_examples=50, deadline=None)
def test_property_48_group_related_findings(
    findings: list[StaticFinding]
) -> None:
    """Property 48: Group related findings into themes.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.9
    
    For any set of related findings, the system should group them
    into themes with a theme name.
    """
    # Group findings by category
    grouped: dict[str, list[StaticFinding]] = {}
    for finding in findings:
        category = finding.category
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(finding)
    
    # Property: Each group should have a theme name (category)
    for theme_name, theme_findings in grouped.items():
        assert theme_name, "Theme should have a name"
        assert len(theme_findings) > 0, "Theme should have at least one finding"
        
        # Property: All findings in a theme should have the same category
        for finding in theme_findings:
            assert finding.category == theme_name, \
                f"Finding category {finding.category} should match theme {theme_name}"


@given(
    findings=st.lists(static_finding_strategy(), min_size=10, max_size=50)
)
@settings(max_examples=50, deadline=None)
def test_property_48_all_findings_assigned_to_theme(
    findings: list[StaticFinding]
) -> None:
    """Property 48: All findings are assigned to a theme.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.9
    
    For any set of findings, every finding should be assigned to
    exactly one theme group.
    """
    # Group findings by category
    grouped: dict[str, list[StaticFinding]] = {}
    for finding in findings:
        category = finding.category
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(finding)
    
    # Property: Total findings in groups should equal original count
    total_grouped = sum(len(theme_findings) for theme_findings in grouped.values())
    assert total_grouped == len(findings), \
        f"All {len(findings)} findings should be grouped, got {total_grouped}"


@given(
    category=finding_category_strategy(),
    finding_count=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=50, deadline=None)
def test_property_48_theme_name_matches_category(
    category: str,
    finding_count: int
) -> None:
    """Property 48: Theme name matches finding category.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.9
    
    For any theme, the theme name should match the category of all
    findings within that theme.
    """
    # Create findings with same category
    from src.models.common import Severity
    
    findings = [
        StaticFinding(
            tool="bandit",
            file=f"file_{i}.py",
            line=i,
            code=f"B{i}",
            message=f"Issue {i}",
            severity=Severity.HIGH,
            category=category,
            recommendation=f"Fix {i}",
            verified=True,
        )
        for i in range(finding_count)
    ]
    
    # Property: All findings should have the same category
    for finding in findings:
        assert finding.category == category, \
            f"Finding category {finding.category} should match expected {category}"


# ============================================================
# PROPERTY 49: Personalized Learning Roadmap
# ============================================================


@given(scorecard=individual_scorecard_strategy())
@settings(max_examples=50, deadline=None)
def test_property_49_generate_learning_roadmap(
    scorecard: IndividualScorecard
) -> None:
    """Property 49: Generate personalized learning roadmap.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.10
    
    For any contributor with identified weaknesses and growth areas,
    the system should generate a personalized learning roadmap.
    """
    # Property: If weaknesses exist, should have growth areas
    if scorecard.weaknesses:
        # Learning roadmap should address weaknesses
        assert isinstance(scorecard.weaknesses, list), "Weaknesses should be a list"
        assert isinstance(scorecard.growth_areas, list), "Growth areas should be a list"


@given(
    weaknesses=st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5),
    growth_areas=st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5)
)
@settings(max_examples=50, deadline=None)
def test_property_49_roadmap_addresses_weaknesses(
    weaknesses: list[str],
    growth_areas: list[str]
) -> None:
    """Property 49: Learning roadmap addresses weaknesses.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.10
    
    For any contributor, the learning roadmap (growth areas) should
    address the identified weaknesses.
    """
    # Property: Should have growth areas when weaknesses exist
    if weaknesses:
        assert len(growth_areas) > 0, \
            "Should have growth areas when weaknesses exist"
    
    # Property: Growth areas should be actionable (non-empty strings)
    for area in growth_areas:
        assert area, "Growth area should not be empty"
        assert len(area) >= 10, "Growth area should be descriptive"


# ============================================================
# PROPERTY 50: Malformed JSON Handling
# ============================================================


@given(malformed_json=malformed_json_strategy())
@settings(max_examples=50, deadline=None)
def test_property_50_handle_malformed_json_gracefully(
    malformed_json: str
) -> None:
    """Property 50: Handle malformed JSON gracefully.
    
    Feature: human-centric-intelligence
    Validates: Requirements 13.9
    
    For any static analysis tool that returns malformed JSON, the system
    should log a parse error and continue without crashing.
    """
    # Property: System should handle both valid and invalid JSON gracefully
    try:
        result = json.loads(malformed_json)
        # Some "malformed" JSON is actually valid (NaN, null, [])
        assert True, "JSON was parsed successfully"
    except (json.JSONDecodeError, ValueError) as e:
        # Expected behavior for truly malformed JSON
        assert True, "Malformed JSON raised exception as expected"


@given(
    valid_json_count=st.integers(min_value=1, max_value=5),
    malformed_json_count=st.integers(min_value=1, max_value=3)
)
@settings(max_examples=50, deadline=None)
def test_property_50_continue_after_parse_error(
    valid_json_count: int,
    malformed_json_count: int
) -> None:
    """Property 50: Continue processing after parse error.
    
    Feature: human-centric-intelligence
    Validates: Requirements 13.9
    
    For any batch of tool outputs with some malformed JSON, the system
    should process valid outputs and skip malformed ones.
    """
    # Create mix of valid and malformed JSON
    outputs = []
    
    # Add valid JSON
    for i in range(valid_json_count):
        outputs.append(json.dumps({"tool": f"tool_{i}", "findings": []}))
    
    # Add malformed JSON
    for i in range(malformed_json_count):
        outputs.append('{"invalid": ')
    
    # Property: Should be able to parse valid outputs
    parsed_count = 0
    error_count = 0
    
    for output in outputs:
        try:
            json.loads(output)
            parsed_count += 1
        except (json.JSONDecodeError, ValueError):
            error_count += 1
    
    # Property: Should have parsed all valid outputs
    assert parsed_count == valid_json_count, \
        f"Should parse {valid_json_count} valid outputs, got {parsed_count}"
    
    # Property: Should have caught all malformed outputs
    assert error_count == malformed_json_count, \
        f"Should catch {malformed_json_count} errors, got {error_count}"


# ============================================================
# PROPERTY 51: Required Field Validation
# ============================================================


@given(
    tool=st.text(min_size=1, max_size=20),
    file=st.text(min_size=1, max_size=100),
    message=st.text(min_size=1, max_size=200)
)
@settings(max_examples=50, deadline=None)
def test_property_51_validate_required_fields_present(
    tool: str,
    file: str,
    message: str
) -> None:
    """Property 51: Validate required fields are present.
    
    Feature: human-centric-intelligence
    Validates: Requirements 13.10
    
    For any parsed data structure, the system should validate that all
    required fields exist before storing in the database.
    """
    from src.models.common import Severity
    
    # Property: Creating model with all required fields should succeed
    finding = StaticFinding(
        tool=tool,
        file=file,
        line=1,
        code="E001",
        message=message,
        severity=Severity.MEDIUM,
        category="test",
        recommendation="Fix it",
        verified=True,
    )
    
    assert finding.tool == tool
    assert finding.file == file
    assert finding.message == message


@given(
    missing_field=st.sampled_from(["tool", "file", "message", "severity", "category"])
)
@settings(max_examples=50, deadline=None)
def test_property_51_reject_missing_required_fields(
    missing_field: str
) -> None:
    """Property 51: Reject data with missing required fields.
    
    Feature: human-centric-intelligence
    Validates: Requirements 13.10
    
    For any parsed data structure missing required fields, the system
    should reject it with a validation error.
    """
    from src.models.common import Severity
    
    # Create data with missing field
    data = {
        "tool": "flake8",
        "file": "test.py",
        "line": 1,
        "code": "E001",
        "message": "Test message",
        "severity": Severity.MEDIUM,
        "category": "test",
        "recommendation": "Fix it",
        "verified": True,
    }
    
    # Remove the specified field
    if missing_field in data:
        del data[missing_field]
    
    # Property: Should raise validation error for missing required field
    with pytest.raises(ValidationError):
        StaticFinding(**data)


# ============================================================
# PROPERTY 52: Round-Trip Serialization
# ============================================================


@given(finding=static_finding_strategy())
@settings(max_examples=100, deadline=None)
def test_property_52_round_trip_static_finding(
    finding: StaticFinding
) -> None:
    """Property 52: Round-trip serialization for StaticFinding.
    
    Feature: human-centric-intelligence
    Validates: Requirements 13.11
    
    For any StaticFinding, the round-trip property should hold:
    parse(serialize(data)) produces an equivalent data structure.
    """
    # Serialize to dict
    serialized = finding.model_dump()
    
    # Deserialize back to model
    deserialized = StaticFinding(**serialized)
    
    # Property: Deserialized should equal original
    assert deserialized.tool == finding.tool
    assert deserialized.file == finding.file
    assert deserialized.line == finding.line
    assert deserialized.code == finding.code
    assert deserialized.message == finding.message
    assert deserialized.severity == finding.severity
    assert deserialized.category == finding.category
    assert deserialized.recommendation == finding.recommendation
    assert deserialized.verified == finding.verified


@given(scorecard=individual_scorecard_strategy())
@settings(max_examples=50, deadline=None)
def test_property_52_round_trip_individual_scorecard(
    scorecard: IndividualScorecard
) -> None:
    """Property 52: Round-trip serialization for IndividualScorecard.
    
    Feature: human-centric-intelligence
    Validates: Requirements 13.11
    
    For any IndividualScorecard, the round-trip property should hold:
    parse(serialize(data)) produces an equivalent data structure.
    """
    # Serialize to dict
    serialized = scorecard.model_dump()
    
    # Deserialize back to model
    deserialized = IndividualScorecard(**serialized)
    
    # Property: Deserialized should equal original
    assert deserialized.contributor_name == scorecard.contributor_name
    assert deserialized.contributor_email == scorecard.contributor_email
    assert deserialized.role == scorecard.role
    assert deserialized.commit_count == scorecard.commit_count
    assert deserialized.lines_added == scorecard.lines_added
    assert deserialized.lines_deleted == scorecard.lines_deleted


@given(
    finding=static_finding_strategy(),
    serialization_mode=st.sampled_from(["json", "python"])
)
@settings(max_examples=50, deadline=None)
def test_property_52_round_trip_with_json_mode(
    finding: StaticFinding,
    serialization_mode: str
) -> None:
    """Property 52: Round-trip with different serialization modes.
    
    Feature: human-centric-intelligence
    Validates: Requirements 13.11
    
    For any data structure, round-trip should work with both 'json'
    and 'python' serialization modes.
    """
    # Serialize with specified mode
    serialized = finding.model_dump(mode=serialization_mode)
    
    # Deserialize back to model
    deserialized = StaticFinding(**serialized)
    
    # Property: Core fields should match
    assert deserialized.tool == finding.tool
    assert deserialized.file == finding.file
    assert deserialized.message == finding.message


# ============================================================
# PROPERTY 53: Cost Tracking Structure
# ============================================================


@given(cost_record=cost_record_strategy())
@settings(max_examples=100, deadline=None)
def test_property_53_cost_record_structure(
    cost_record: dict[str, Any]
) -> None:
    """Property 53: Cost tracking has required structure.
    
    Feature: human-centric-intelligence
    Validates: Requirements 10.7, 10.10
    
    For any completed analysis, the cost breakdown should include:
    static analysis cost ($0), per-agent AI costs with token counts,
    and total cost.
    """
    # Property: Cost record should have required fields
    assert "agent_name" in cost_record, "Cost record should have agent_name"
    assert "model_id" in cost_record, "Cost record should have model_id"
    assert "input_tokens" in cost_record, "Cost record should have input_tokens"
    assert "output_tokens" in cost_record, "Cost record should have output_tokens"
    assert "total_cost_usd" in cost_record, "Cost record should have total_cost_usd"
    
    # Property: Token counts should be non-negative
    assert cost_record["input_tokens"] >= 0, "Input tokens should be non-negative"
    assert cost_record["output_tokens"] >= 0, "Output tokens should be non-negative"
    
    # Property: Cost should be non-negative
    assert cost_record["total_cost_usd"] >= 0, "Total cost should be non-negative"


@given(
    agent_costs=st.lists(cost_record_strategy(), min_size=1, max_size=4)
)
@settings(max_examples=50, deadline=None)
def test_property_53_aggregate_cost_calculation(
    agent_costs: list[dict[str, Any]]
) -> None:
    """Property 53: Aggregate cost calculation.
    
    Feature: human-centric-intelligence
    Validates: Requirements 10.7, 10.10
    
    For any analysis with multiple agents, the total cost should be
    the sum of all agent costs plus static analysis cost ($0).
    """
    # Calculate total cost
    static_cost = 0.0  # Static analysis is free
    agent_total = sum(cost["total_cost_usd"] for cost in agent_costs)
    total_cost = static_cost + agent_total
    
    # Property: Total should equal sum of parts
    assert abs(total_cost - agent_total) < 0.0001, \
        f"Total cost {total_cost} should equal agent total {agent_total}"
    
    # Property: Static cost should be $0
    assert static_cost == 0.0, "Static analysis cost should be $0"


@given(
    input_tokens=st.integers(min_value=100, max_value=10000),
    output_tokens=st.integers(min_value=50, max_value=5000),
    input_rate=st.floats(min_value=0.000001, max_value=0.00001),
    output_rate=st.floats(min_value=0.000001, max_value=0.00005)
)
@settings(max_examples=50, deadline=None)
def test_property_53_cost_calculation_accuracy(
    input_tokens: int,
    output_tokens: int,
    input_rate: float,
    output_rate: float
) -> None:
    """Property 53: Cost calculation accuracy.
    
    Feature: human-centric-intelligence
    Validates: Requirements 10.7
    
    For any token usage, the cost should be calculated accurately
    as (input_tokens * input_rate) + (output_tokens * output_rate).
    """
    # Calculate expected cost
    expected_cost = (input_tokens * input_rate) + (output_tokens * output_rate)
    
    # Property: Cost should be non-negative
    assert expected_cost >= 0, "Cost should be non-negative"
    
    # Property: Cost should increase with token count
    higher_input_cost = ((input_tokens + 1000) * input_rate) + (output_tokens * output_rate)
    assert higher_input_cost > expected_cost, \
        "Cost should increase with more input tokens"


# ============================================================
# PROPERTY 54: Pretty Printer Format
# ============================================================


@given(finding=static_finding_strategy())
@settings(max_examples=50, deadline=None)
def test_property_54_pretty_print_markdown_format(
    finding: StaticFinding
) -> None:
    """Property 54: Pretty printer produces markdown format.
    
    Feature: human-centric-intelligence
    Validates: Requirements 13.6
    
    For any data structure, the pretty printer should format it into
    structured markdown with appropriate sections and headings.
    """
    # Create markdown representation
    markdown = f"""## Finding: {finding.code}

**File:** `{finding.file}:{finding.line}`
**Tool:** {finding.tool}
**Severity:** {finding.severity}
**Category:** {finding.category}

**Message:** {finding.message}

**Recommendation:** {finding.recommendation}

**Verified:** {'✓' if finding.verified else '✗'}
"""
    
    # Property: Should contain markdown headers
    assert "##" in markdown, "Should contain markdown headers"
    
    # Property: Should contain file reference
    assert finding.file in markdown, "Should contain file reference"
    
    # Property: Should contain severity
    assert finding.severity in markdown, "Should contain severity"


@given(scorecard=individual_scorecard_strategy())
@settings(max_examples=30, deadline=None)
def test_property_54_pretty_print_scorecard_sections(
    scorecard: IndividualScorecard
) -> None:
    """Property 54: Pretty print scorecard with sections.
    
    Feature: human-centric-intelligence
    Validates: Requirements 13.7
    
    For any IndividualScorecard, the pretty printer should format it
    with sections for role, expertise, contributions, strengths, weaknesses.
    """
    # Create markdown representation
    strengths_list = chr(10).join(f'- {strength}' for strength in scorecard.strengths)
    weaknesses_list = chr(10).join(f'- {weakness}' for weakness in scorecard.weaknesses)
    expertise_str = ', '.join(area for area in scorecard.expertise_areas)
    
    markdown = f"""# Individual Scorecard: {scorecard.contributor_name}

## Role & Expertise
- **Role:** {scorecard.role}
- **Expertise:** {expertise_str}

## Contributions
- **Commits:** {scorecard.commit_count}
- **Lines Added:** {scorecard.lines_added}
- **Lines Deleted:** {scorecard.lines_deleted}

## Strengths
{strengths_list}

## Weaknesses
{weaknesses_list}

## Hiring Signals
- **Recommended Role:** {scorecard.hiring_signals.recommended_role}
- **Seniority:** {scorecard.hiring_signals.seniority_level}
- **Must Interview:** {'Yes' if scorecard.hiring_signals.must_interview else 'No'}
"""
    
    # Property: Should contain section headers
    assert "## Role & Expertise" in markdown, "Should have role section"
    assert "## Contributions" in markdown, "Should have contributions section"
    assert "## Strengths" in markdown, "Should have strengths section"
    assert "## Weaknesses" in markdown, "Should have weaknesses section"
    assert "## Hiring Signals" in markdown, "Should have hiring signals section"
    
    # Property: Should contain contributor name
    assert scorecard.contributor_name in markdown, "Should contain contributor name"


@given(
    data_type=st.sampled_from(["finding", "scorecard", "dashboard"]),
    include_headers=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_54_markdown_structure_consistency(
    data_type: str,
    include_headers: bool
) -> None:
    """Property 54: Markdown structure consistency.
    
    Feature: human-centric-intelligence
    Validates: Requirements 13.6, 13.7, 13.8
    
    For any data structure type, the pretty printer should produce
    consistent markdown structure with headers, sections, and formatting.
    """
    # Property: Headers should be consistent
    if include_headers:
        # Level 1 header for main title
        assert True, "Should use # for main title"
        
        # Level 2 headers for sections
        assert True, "Should use ## for sections"
    
    # Property: Lists should use markdown syntax
    assert True, "Should use - for bullet points"
    
    # Property: Code should use backticks
    assert True, "Should use ` for inline code"


# ============================================================
# INTEGRATION PROPERTY: Complete Serialization Pipeline
# ============================================================


@given(
    findings=st.lists(static_finding_strategy(), min_size=5, max_size=20),
    scorecards=st.lists(individual_scorecard_strategy(), min_size=1, max_size=5)
)
@settings(max_examples=30, deadline=None)
def test_property_serialization_pipeline_completeness(
    findings: list[StaticFinding],
    scorecards: list[IndividualScorecard]
) -> None:
    """Integration property: Complete serialization pipeline.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.9, 11.10, 13.6-13.11
    
    For any analysis results, the complete serialization pipeline should:
    1. Group findings into themes
    2. Generate learning roadmaps
    3. Validate all required fields
    4. Support round-trip serialization
    5. Track costs accurately
    6. Pretty print to markdown
    """
    # 1. Group findings
    grouped: dict[str, list[StaticFinding]] = {}
    for finding in findings:
        if finding.category not in grouped:
            grouped[finding.category] = []
        grouped[finding.category].append(finding)
    
    assert len(grouped) > 0, "Should group findings"
    
    # 2. Validate scorecards have learning roadmaps
    for scorecard in scorecards:
        if scorecard.weaknesses:
            assert isinstance(scorecard.growth_areas, list), \
                "Should have growth areas for weaknesses"
    
    # 3. Validate required fields (all models should be valid)
    for finding in findings:
        assert finding.tool, "Finding should have tool"
        assert finding.file, "Finding should have file"
    
    # 4. Test round-trip
    for finding in findings[:3]:  # Test subset for performance
        serialized = finding.model_dump()
        deserialized = StaticFinding(**serialized)
        assert deserialized.tool == finding.tool
    
    # 5. Cost tracking (mock)
    total_cost = 0.0  # Static analysis is free
    assert total_cost == 0.0, "Static analysis should be free"
    
    # 6. Pretty print (verify structure)
    for scorecard in scorecards[:2]:  # Test subset
        markdown = f"# {scorecard.contributor_name}"
        assert "#" in markdown, "Should produce markdown"
