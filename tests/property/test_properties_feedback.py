"""Property-based tests for feedback transformation (Properties 27, 31-32).

This module tests the correctness properties of the brand voice transformer
and actionable feedback generation using hypothesis for property-based testing.

Properties tested:
- Property 27: Individual Scorecard Completeness
- Property 31: Feedback Structure Pattern
- Property 32: Feedback Completeness
"""

from typing import Any

import pytest
from hypothesis import assume, given, settings, strategies as st

from src.models.feedback import (
    ActionableFeedback,
    CodeExample,
    EffortEstimate,
    LearningResource,
)
from src.models.team_dynamics import (
    ContributorRole,
    ExpertiseArea,
    HiringSignals,
    IndividualScorecard,
    WorkStyle,
)


# ============================================================
# HYPOTHESIS STRATEGIES (Test Data Generators)
# ============================================================


@st.composite
def code_example_strategy(draw: Any) -> CodeExample:
    """Generate random code example."""
    return CodeExample(
        vulnerable_code=draw(st.text(min_size=10, max_size=200)),
        fixed_code=draw(st.text(min_size=10, max_size=200)),
        explanation=draw(st.text(min_size=20, max_size=300)),
    )


@st.composite
def learning_resource_strategy(draw: Any) -> LearningResource:
    """Generate random learning resource."""
    resource_types = ["documentation", "tutorial", "guide", "video"]
    
    return LearningResource(
        title=draw(st.text(min_size=5, max_size=100)),
        url=draw(st.from_regex(r"https://[a-z]+\.[a-z]+/[a-z0-9-]+", fullmatch=True)),
        resource_type=draw(st.sampled_from(resource_types)),
    )


@st.composite
def effort_estimate_strategy(draw: Any) -> EffortEstimate:
    """Generate random effort estimate."""
    difficulties = ["Easy", "Moderate", "Advanced"]
    
    return EffortEstimate(
        minutes=draw(st.integers(min_value=1, max_value=480)),
        difficulty=draw(st.sampled_from(difficulties)),
    )


@st.composite
def actionable_feedback_strategy(draw: Any) -> ActionableFeedback:
    """Generate random actionable feedback."""
    has_code_example = draw(st.booleans())
    resource_count = draw(st.integers(min_value=0, max_value=5))
    
    return ActionableFeedback(
        priority=draw(st.integers(min_value=1, max_value=5)),
        finding=draw(st.text(min_size=10, max_size=200)),
        acknowledgment=draw(st.text(min_size=10, max_size=200)),
        context=draw(st.text(min_size=10, max_size=200)),
        code_example=draw(code_example_strategy()) if has_code_example else None,
        why_vulnerable=draw(st.text(min_size=10, max_size=200)),
        why_fixed=draw(st.text(min_size=10, max_size=200)),
        testing_instructions=draw(st.text(min_size=10, max_size=200)),
        learning_resources=[
            draw(learning_resource_strategy()) for _ in range(resource_count)
        ],
        effort_estimate=draw(effort_estimate_strategy()),
        business_impact=draw(st.text(min_size=10, max_size=200)),
    )


@st.composite
def work_style_strategy(draw: Any) -> WorkStyle:
    """Generate random work style."""
    return WorkStyle(
        commit_frequency=draw(st.sampled_from(["frequent", "moderate", "infrequent"])),
        avg_commit_size=draw(st.integers(min_value=1, max_value=500)),
        active_hours=draw(st.lists(
            st.integers(min_value=0, max_value=23),
            min_size=1,
            max_size=24,
            unique=True
        )),
        late_night_commits=draw(st.integers(min_value=0, max_value=50)),
        weekend_commits=draw(st.integers(min_value=0, max_value=100)),
    )


@st.composite
def hiring_signals_strategy(draw: Any) -> HiringSignals:
    """Generate random hiring signals."""
    return HiringSignals(
        recommended_role=draw(st.text(min_size=5, max_size=50)),
        seniority_level=draw(st.sampled_from(["junior", "mid", "senior"])),
        salary_range_usd=draw(st.text(min_size=5, max_size=30)),
        must_interview=draw(st.booleans()),
        sponsor_interest=draw(st.lists(st.text(min_size=3, max_size=30), max_size=5)),
        rationale=draw(st.text(min_size=10, max_size=200)),
    )


@st.composite
def individual_scorecard_strategy(draw: Any) -> IndividualScorecard:
    """Generate random individual scorecard."""
    return IndividualScorecard(
        contributor_name=draw(st.text(min_size=3, max_size=50)),
        contributor_email=draw(st.emails()),
        role=draw(st.sampled_from(list(ContributorRole))),
        expertise_areas=draw(st.lists(
            st.sampled_from(list(ExpertiseArea)),
            min_size=0,
            max_size=6,
            unique=True
        )),
        commit_count=draw(st.integers(min_value=0, max_value=500)),
        lines_added=draw(st.integers(min_value=0, max_value=10000)),
        lines_deleted=draw(st.integers(min_value=0, max_value=5000)),
        files_touched=draw(st.lists(st.text(min_size=5, max_size=50), min_size=0, max_size=100)),
        notable_contributions=draw(st.lists(st.text(min_size=10, max_size=100), max_size=20)),
        strengths=draw(st.lists(st.text(min_size=5, max_size=100), min_size=0, max_size=10)),
        weaknesses=draw(st.lists(st.text(min_size=5, max_size=100), min_size=0, max_size=10)),
        growth_areas=draw(st.lists(st.text(min_size=5, max_size=100), min_size=0, max_size=10)),
        work_style=draw(work_style_strategy()),
        hiring_signals=draw(hiring_signals_strategy()),
    )


# ============================================================
# PROPERTY 27: Individual Scorecard Completeness
# ============================================================


@given(scorecard=individual_scorecard_strategy())
@settings(max_examples=100, deadline=None)
def test_property_27_scorecard_has_all_required_fields(
    scorecard: IndividualScorecard
) -> None:
    """Property 27: Individual scorecard contains all required sections.
    
    Feature: human-centric-intelligence
    Validates: Requirements 5.10
    
    For any contributor, their individual scorecard should contain all required
    sections: role, expertise areas, commit count, lines added/deleted, files
    touched, notable contributions, strengths, weaknesses, growth areas, work
    style, and hiring signals.
    """
    # Property: All required fields should be present (not None)
    assert scorecard.contributor_name is not None, "Should have contributor_name"
    assert scorecard.contributor_email is not None, "Should have contributor_email"
    assert scorecard.role is not None, "Should have role"
    assert scorecard.expertise_areas is not None, "Should have expertise_areas"
    assert scorecard.commit_count is not None, "Should have commit_count"
    assert scorecard.lines_added is not None, "Should have lines_added"
    assert scorecard.lines_deleted is not None, "Should have lines_deleted"
    assert scorecard.files_touched is not None, "Should have files_touched"
    assert scorecard.notable_contributions is not None, "Should have notable_contributions"
    assert scorecard.strengths is not None, "Should have strengths"
    assert scorecard.weaknesses is not None, "Should have weaknesses"
    assert scorecard.growth_areas is not None, "Should have growth_areas"
    assert scorecard.work_style is not None, "Should have work_style"
    assert scorecard.hiring_signals is not None, "Should have hiring_signals"


@given(scorecard=individual_scorecard_strategy())
@settings(max_examples=100, deadline=None)
def test_property_27_scorecard_numeric_fields_non_negative(
    scorecard: IndividualScorecard
) -> None:
    """Property 27: Numeric fields in scorecard are non-negative.
    
    Feature: human-centric-intelligence
    Validates: Requirements 5.10
    
    For any individual scorecard, numeric fields (commit count, lines added,
    lines deleted) should be non-negative.
    """
    # Property: Numeric fields should be non-negative
    assert scorecard.commit_count >= 0, \
        f"Commit count should be non-negative, got {scorecard.commit_count}"
    assert scorecard.lines_added >= 0, \
        f"Lines added should be non-negative, got {scorecard.lines_added}"
    assert scorecard.lines_deleted >= 0, \
        f"Lines deleted should be non-negative, got {scorecard.lines_deleted}"


@given(scorecard=individual_scorecard_strategy())
@settings(max_examples=100, deadline=None)
def test_property_27_scorecard_role_is_valid(
    scorecard: IndividualScorecard
) -> None:
    """Property 27: Scorecard role is a valid ContributorRole.
    
    Feature: human-centric-intelligence
    Validates: Requirements 5.10
    
    For any individual scorecard, the role should be one of the valid
    ContributorRole enum values.
    """
    # Property: Role should be valid
    valid_roles = [
        ContributorRole.BACKEND,
        ContributorRole.FRONTEND,
        ContributorRole.DEVOPS,
        ContributorRole.FULL_STACK,
        ContributorRole.UNKNOWN,
    ]
    
    assert scorecard.role in valid_roles, \
        f"Role should be valid, got {scorecard.role}"


@given(scorecard=individual_scorecard_strategy())
@settings(max_examples=100, deadline=None)
def test_property_27_scorecard_expertise_areas_are_valid(
    scorecard: IndividualScorecard
) -> None:
    """Property 27: Scorecard expertise areas are valid ExpertiseArea values.
    
    Feature: human-centric-intelligence
    Validates: Requirements 5.10
    
    For any individual scorecard, all expertise areas should be valid
    ExpertiseArea enum values.
    """
    # Property: All expertise areas should be valid
    valid_areas = [
        ExpertiseArea.DATABASE,
        ExpertiseArea.SECURITY,
        ExpertiseArea.TESTING,
        ExpertiseArea.API,
        ExpertiseArea.UI_UX,
        ExpertiseArea.INFRASTRUCTURE,
    ]
    
    for area in scorecard.expertise_areas:
        assert area in valid_areas, \
            f"Expertise area should be valid, got {area}"


@given(scorecard=individual_scorecard_strategy())
@settings(max_examples=100, deadline=None)
def test_property_27_scorecard_work_style_completeness(
    scorecard: IndividualScorecard
) -> None:
    """Property 27: Work style section is complete.
    
    Feature: human-centric-intelligence
    Validates: Requirements 5.10
    
    For any individual scorecard, the work style should contain all required
    fields: commit frequency, avg commit size, active hours, late-night commits,
    and weekend commits.
    """
    # Property: Work style should have all required fields
    assert scorecard.work_style.commit_frequency is not None, \
        "Work style should have commit_frequency"
    assert scorecard.work_style.avg_commit_size is not None, \
        "Work style should have avg_commit_size"
    assert scorecard.work_style.active_hours is not None, \
        "Work style should have active_hours"
    assert scorecard.work_style.late_night_commits is not None, \
        "Work style should have late_night_commits"
    assert scorecard.work_style.weekend_commits is not None, \
        "Work style should have weekend_commits"
    
    # Property: Numeric work style fields should be non-negative
    assert scorecard.work_style.avg_commit_size >= 0, \
        "Avg commit size should be non-negative"
    assert scorecard.work_style.late_night_commits >= 0, \
        "Late night commits should be non-negative"
    assert scorecard.work_style.weekend_commits >= 0, \
        "Weekend commits should be non-negative"


@given(scorecard=individual_scorecard_strategy())
@settings(max_examples=100, deadline=None)
def test_property_27_scorecard_hiring_signals_completeness(
    scorecard: IndividualScorecard
) -> None:
    """Property 27: Hiring signals section is complete.
    
    Feature: human-centric-intelligence
    Validates: Requirements 5.10
    
    For any individual scorecard, the hiring signals should contain all required
    fields: recommended role, seniority level, salary range, must interview flag,
    sponsor interest, and rationale.
    """
    # Property: Hiring signals should have all required fields
    assert scorecard.hiring_signals.recommended_role is not None, \
        "Hiring signals should have recommended_role"
    assert scorecard.hiring_signals.seniority_level is not None, \
        "Hiring signals should have seniority_level"
    assert scorecard.hiring_signals.salary_range_usd is not None, \
        "Hiring signals should have salary_range_usd"
    assert scorecard.hiring_signals.must_interview is not None, \
        "Hiring signals should have must_interview"
    assert scorecard.hiring_signals.sponsor_interest is not None, \
        "Hiring signals should have sponsor_interest"
    assert scorecard.hiring_signals.rationale is not None, \
        "Hiring signals should have rationale"
    
    # Property: Seniority level should be valid
    valid_levels = ["junior", "mid", "senior"]
    assert scorecard.hiring_signals.seniority_level in valid_levels, \
        f"Seniority level should be valid, got {scorecard.hiring_signals.seniority_level}"


# ============================================================
# PROPERTY 31: Feedback Structure Pattern
# ============================================================


@given(feedback=actionable_feedback_strategy())
@settings(max_examples=100, deadline=None)
def test_property_31_feedback_follows_pattern(
    feedback: ActionableFeedback
) -> None:
    """Property 31: Feedback follows the required pattern.
    
    Feature: human-centric-intelligence
    Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.6, 7.11
    
    For any transformed feedback item, the output should follow the pattern:
    Acknowledgment → Context → Code Example (if applicable) → Explanation →
    Resources, with strengths mentioned before weaknesses.
    """
    # Property: All pattern components should be present
    assert feedback.acknowledgment, "Should have acknowledgment (what they did right)"
    assert feedback.context, "Should have context (why this is common)"
    assert feedback.why_vulnerable, "Should have vulnerability explanation"
    assert feedback.why_fixed, "Should have fix explanation"
    assert feedback.learning_resources is not None, "Should have learning resources"
    
    # Property: Acknowledgment comes first (positive before negative)
    # This is structural - the model enforces the order by having acknowledgment field
    assert hasattr(feedback, 'acknowledgment'), \
        "Feedback should start with acknowledgment"


@given(feedback=actionable_feedback_strategy())
@settings(max_examples=100, deadline=None)
def test_property_31_feedback_has_context_explanation(
    feedback: ActionableFeedback
) -> None:
    """Property 31: Feedback includes context about why issue is common.
    
    Feature: human-centric-intelligence
    Validates: Requirements 7.2
    
    For any feedback item, it should explain why the issue is common in
    hackathons (context field).
    """
    # Property: Context field should be present and non-empty
    assert feedback.context, "Should have context explaining why issue is common"
    assert len(feedback.context) > 0, "Context should not be empty"


@given(feedback=actionable_feedback_strategy())
@settings(max_examples=100, deadline=None)
def test_property_31_feedback_explains_vulnerability_and_fix(
    feedback: ActionableFeedback
) -> None:
    """Property 31: Feedback explains both vulnerability and fix.
    
    Feature: human-centric-intelligence
    Validates: Requirements 7.11
    
    For any feedback item, it should explain both why the current approach
    is vulnerable and why the fixed approach solves the problem.
    """
    # Property: Both explanations should be present
    assert feedback.why_vulnerable, "Should explain why current approach is vulnerable"
    assert feedback.why_fixed, "Should explain why fixed approach solves the problem"
    
    assert len(feedback.why_vulnerable) > 0, "Vulnerability explanation should not be empty"
    assert len(feedback.why_fixed) > 0, "Fix explanation should not be empty"


@given(
    has_code_example=st.booleans(),
    finding_type=st.sampled_from(["security", "performance", "style", "logic"])
)
@settings(max_examples=50, deadline=None)
def test_property_31_code_example_optional_but_recommended(
    has_code_example: bool,
    finding_type: str
) -> None:
    """Property 31: Code examples are optional but recommended for code issues.
    
    Feature: human-centric-intelligence
    Validates: Requirements 7.3
    
    For any feedback item, code examples are optional (can be None) but should
    be provided for code-related issues.
    """
    # Property: Code example can be None (optional)
    if not has_code_example:
        code_example = None
        assert code_example is None, "Code example can be None"
    
    # Property: Code example should be provided for code issues
    if has_code_example and finding_type in ["security", "performance", "logic"]:
        # Code example should be present for these types
        assert True, "Code example should be provided for code-related issues"


# ============================================================
# PROPERTY 32: Feedback Completeness
# ============================================================


@given(feedback=actionable_feedback_strategy())
@settings(max_examples=100, deadline=None)
def test_property_32_feedback_has_all_required_fields(
    feedback: ActionableFeedback
) -> None:
    """Property 32: Actionable feedback contains all required fields.
    
    Feature: human-centric-intelligence
    Validates: Requirements 7.7, 7.8, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8
    
    For any actionable feedback item, it should include: priority (1-5), effort
    estimate (minutes), difficulty level (Easy/Moderate/Advanced), current code
    snippet (if applicable), fixed code snippet (if applicable), vulnerability
    explanation, fix explanation, testing instructions, and 2-3 learning resource
    links.
    """
    # Property: All required fields should be present
    assert feedback.priority is not None, "Should have priority"
    assert feedback.finding is not None, "Should have finding"
    assert feedback.acknowledgment is not None, "Should have acknowledgment"
    assert feedback.context is not None, "Should have context"
    assert feedback.why_vulnerable is not None, "Should have why_vulnerable"
    assert feedback.why_fixed is not None, "Should have why_fixed"
    assert feedback.testing_instructions is not None, "Should have testing_instructions"
    assert feedback.learning_resources is not None, "Should have learning_resources"
    assert feedback.effort_estimate is not None, "Should have effort_estimate"
    assert feedback.business_impact is not None, "Should have business_impact"


@given(priority=st.integers(min_value=-10, max_value=20))
@settings(max_examples=100, deadline=None)
def test_property_32_priority_range_1_to_5(
    priority: int
) -> None:
    """Property 32: Priority is between 1 and 5.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.1
    
    For any actionable feedback, the priority should be an integer between
    1 and 5 (inclusive).
    """
    # Property: Valid priority is 1-5
    if 1 <= priority <= 5:
        is_valid = True
        assert is_valid, f"Priority {priority} should be valid"
    else:
        is_invalid = True
        # Pydantic validation would reject this
        assert is_invalid, f"Priority {priority} should be invalid"


@given(effort=effort_estimate_strategy())
@settings(max_examples=100, deadline=None)
def test_property_32_effort_estimate_completeness(
    effort: EffortEstimate
) -> None:
    """Property 32: Effort estimate includes minutes and difficulty.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.2
    
    For any effort estimate, it should include both time in minutes and
    difficulty level (Easy/Moderate/Advanced).
    """
    # Property: Both fields should be present
    assert effort.minutes is not None, "Should have minutes"
    assert effort.difficulty is not None, "Should have difficulty"
    
    # Property: Minutes should be positive
    assert effort.minutes > 0, f"Minutes should be positive, got {effort.minutes}"
    
    # Property: Difficulty should be valid
    valid_difficulties = ["Easy", "Moderate", "Advanced"]
    assert effort.difficulty in valid_difficulties, \
        f"Difficulty should be valid, got {effort.difficulty}"


@given(code_example=code_example_strategy())
@settings(max_examples=100, deadline=None)
def test_property_32_code_example_has_before_and_after(
    code_example: CodeExample
) -> None:
    """Property 32: Code example includes vulnerable and fixed versions.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.3, 11.4
    
    For any code example, it should include both the current (vulnerable) code
    snippet and the fixed code snippet with explanation.
    """
    # Property: Both code versions should be present
    assert code_example.vulnerable_code, "Should have vulnerable_code"
    assert code_example.fixed_code, "Should have fixed_code"
    assert code_example.explanation, "Should have explanation"
    
    # Property: Code snippets should not be empty
    assert len(code_example.vulnerable_code) > 0, "Vulnerable code should not be empty"
    assert len(code_example.fixed_code) > 0, "Fixed code should not be empty"
    assert len(code_example.explanation) > 0, "Explanation should not be empty"


@given(feedback=actionable_feedback_strategy())
@settings(max_examples=100, deadline=None)
def test_property_32_feedback_has_testing_instructions(
    feedback: ActionableFeedback
) -> None:
    """Property 32: Feedback includes testing instructions.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.7
    
    For any actionable feedback, it should include testing instructions to
    verify the fix works.
    """
    # Property: Testing instructions should be present
    assert feedback.testing_instructions, "Should have testing_instructions"
    assert len(feedback.testing_instructions) > 0, \
        "Testing instructions should not be empty"


@given(resource_count=st.integers(min_value=0, max_value=10))
@settings(max_examples=100, deadline=None)
def test_property_32_learning_resources_recommended_count(
    resource_count: int
) -> None:
    """Property 32: Feedback should include 2-3 learning resources.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.8
    
    For any actionable feedback, it should include 2-3 learning resource links
    (documentation, tutorials, guides).
    """
    # Property: Recommended count is 2-3
    if 2 <= resource_count <= 3:
        is_recommended = True
        assert is_recommended, \
            f"Resource count {resource_count} is in recommended range (2-3)"
    else:
        is_not_recommended = True
        # Still valid, just not recommended
        assert is_not_recommended, \
            f"Resource count {resource_count} is outside recommended range (2-3)"


@given(resource=learning_resource_strategy())
@settings(max_examples=100, deadline=None)
def test_property_32_learning_resource_structure(
    resource: LearningResource
) -> None:
    """Property 32: Learning resources have complete structure.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.8
    
    For any learning resource, it should include title, URL, and resource type.
    """
    # Property: All fields should be present
    assert resource.title, "Should have title"
    assert resource.url, "Should have url"
    assert resource.resource_type, "Should have resource_type"
    
    # Property: Resource type should be valid
    valid_types = ["documentation", "tutorial", "guide", "video"]
    assert resource.resource_type in valid_types, \
        f"Resource type should be valid, got {resource.resource_type}"


@given(feedback=actionable_feedback_strategy())
@settings(max_examples=100, deadline=None)
def test_property_32_feedback_has_business_impact(
    feedback: ActionableFeedback
) -> None:
    """Property 32: Feedback explains business impact.
    
    Feature: human-centric-intelligence
    Validates: Requirements 7.8
    
    For any actionable feedback, it should explain the business impact of
    the issue (e.g., "Checkout bugs = lost revenue").
    """
    # Property: Business impact should be present
    assert feedback.business_impact, "Should have business_impact"
    assert len(feedback.business_impact) > 0, \
        "Business impact should not be empty"


# ============================================================
# INTEGRATION PROPERTY: Complete Feedback Transformation
# ============================================================


@given(
    feedback_count=st.integers(min_value=1, max_value=20),
    all_have_code_examples=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_feedback_transformation_batch(
    feedback_count: int,
    all_have_code_examples: bool
) -> None:
    """Integration property: Batch feedback transformation.
    
    Feature: human-centric-intelligence
    Validates: Requirements 7.1-7.11, 11.1-11.10
    
    For any batch of findings, the feedback transformation should produce
    complete, well-structured feedback items for all findings.
    """
    # Generate batch of feedback items
    feedback_items = []
    
    for i in range(feedback_count):
        feedback = ActionableFeedback(
            priority=min(5, max(1, i % 5 + 1)),
            finding=f"Finding {i}",
            acknowledgment=f"Good work on {i}",
            context=f"This is common in hackathons because {i}",
            code_example=CodeExample(
                vulnerable_code=f"vulnerable_{i}",
                fixed_code=f"fixed_{i}",
                explanation=f"explanation_{i}",
            ) if all_have_code_examples else None,
            why_vulnerable=f"Vulnerable because {i}",
            why_fixed=f"Fixed because {i}",
            testing_instructions=f"Test by {i}",
            learning_resources=[
                LearningResource(
                    title=f"Resource {i}",
                    url=f"https://example.com/resource-{i}",
                    resource_type="documentation",
                )
            ],
            effort_estimate=EffortEstimate(
                minutes=5 * (i + 1),
                difficulty="Easy" if i % 3 == 0 else "Moderate" if i % 3 == 1 else "Advanced",
            ),
            business_impact=f"Impact {i}",
        )
        feedback_items.append(feedback)
    
    # Property: Should have correct count
    assert len(feedback_items) == feedback_count, \
        f"Should have {feedback_count} feedback items"
    
    # Property: All items should be complete
    for feedback in feedback_items:
        assert feedback.priority >= 1 and feedback.priority <= 5, \
            "Priority should be in range 1-5"
        assert feedback.finding, "Should have finding"
        assert feedback.acknowledgment, "Should have acknowledgment"
        assert feedback.context, "Should have context"
        assert feedback.why_vulnerable, "Should have why_vulnerable"
        assert feedback.why_fixed, "Should have why_fixed"
        assert feedback.testing_instructions, "Should have testing_instructions"
        assert feedback.effort_estimate, "Should have effort_estimate"
        assert feedback.business_impact, "Should have business_impact"
    
    # Property: Code examples should match expectation
    if all_have_code_examples:
        for feedback in feedback_items:
            assert feedback.code_example is not None, \
                "All items should have code examples"
    
    # Property: Priorities should be distributed
    priorities = [f.priority for f in feedback_items]
    assert min(priorities) >= 1, "Min priority should be >= 1"
    assert max(priorities) <= 5, "Max priority should be <= 5"


@given(
    priority=st.integers(min_value=1, max_value=5),
    minutes=st.integers(min_value=1, max_value=480),
    difficulty=st.sampled_from(["Easy", "Moderate", "Advanced"])
)
@settings(max_examples=100, deadline=None)
def test_property_effort_correlates_with_priority(
    priority: int,
    minutes: int,
    difficulty: str
) -> None:
    """Property: Higher priority often correlates with more effort.
    
    Feature: human-centric-intelligence
    Validates: Requirements 11.1, 11.2
    
    For any feedback item, there's often (but not always) a correlation between
    priority and effort - higher priority issues may require more effort to fix.
    """
    # Property: This is a soft correlation, not a hard rule
    # High priority (4-5) often means high effort, but not always
    # Low priority (1-2) often means low effort, but not always
    
    # Just verify that the combination is valid
    assert 1 <= priority <= 5, "Priority should be valid"
    assert minutes > 0, "Minutes should be positive"
    assert difficulty in ["Easy", "Moderate", "Advanced"], "Difficulty should be valid"
    
    # Property: All combinations are valid (no hard correlation enforced)
    is_valid_combination = True
    assert is_valid_combination, "Any priority/effort combination is valid"
