"""Smoke tests for aieic-shared schemas — confirms imports work and basic validation."""

from datetime import datetime, timezone

from aieic_shared import (
    LabPhase,
    StudentStatus,
    StudentRef,
    LabRef,
    HealthResponse,
    ChatRequest,
    ChatResponse,
    ChatSource,
    LogInteractionRequest,
    StudentContextResponse,
    GenerateCurriculumRequest,
    CurriculumMaterial,
    QuizQuestion,
    Rubric,
    AssessmentRequest,
    AssessmentResult,
    SubmissionType,
    StudentMessageRequest,
    DashboardResponse,
)
from aieic_shared.schemas.orchestrator import DashboardLabInfo


def test_top_level_imports():
    """Top-level re-exports work."""
    assert LabPhase.PRE_LAB == "pre_lab"
    assert StudentStatus.ON_TRACK == "on_track"


def test_student_ref_defaults():
    s = StudentRef(student_id="alex_m")
    assert s.course_id == "csc580"


def test_chat_request_validates():
    req = ChatRequest(
        student_id="alex_m",
        session_id="abc-123",
        message="How do I insert?",
        lab_id="lab4",
    )
    assert req.conversation_history == []
    assert req.student_context_summary is None


def test_chat_response_hint_level_bounds():
    """hint_level must be 1-3."""
    import pytest
    from pydantic import ValidationError

    # Valid
    ChatResponse(reply="hi", hint_level=2)

    # Out of range
    with pytest.raises(ValidationError):
        ChatResponse(reply="hi", hint_level=0)
    with pytest.raises(ValidationError):
        ChatResponse(reply="hi", hint_level=4)


def test_log_interaction_optional_response_time():
    req = LogInteractionRequest(
        student_id="alex_m", session_id="s1", message="hi"
    )
    assert req.response_time_ms is None


def test_curriculum_material_roundtrip():
    """Building a CurriculumMaterial and serializing it works."""
    now = datetime.now(timezone.utc)
    mat = CurriculumMaterial(
        lab_id="lab4",
        title="Linked Lists",
        spec_markdown="# Lab 4",
        quiz=[QuizQuestion(id="q1", question="What is O(1)?")],
        rubric=Rubric(),
        generated_at=now,
        last_updated=now,
    )
    dump = mat.model_dump()
    assert dump["lab_id"] == "lab4"
    assert dump["approval_status"] == "pending"
    assert len(dump["quiz"]) == 1


def test_assessment_request_minimal():
    req = AssessmentRequest(student_id="alex_m", assignment_id="lab4", code="x = 1")
    assert req.submission_type is None  # inferred by the agent


def test_assessment_result_auto_id():
    """AssessmentResult auto-generates a submission_id."""
    r1 = AssessmentResult(
        student_id="a", assignment_id="lab4", submission_type=SubmissionType.CODE_ONLY
    )
    r2 = AssessmentResult(
        student_id="a", assignment_id="lab4", submission_type=SubmissionType.CODE_ONLY
    )
    assert r1.submission_id != r2.submission_id


def test_dashboard_response_optional_blocks():
    """Dashboard tabs can be partially populated."""
    resp = DashboardResponse(
        lab=DashboardLabInfo(
            lab_id="lab4",
            title="Linked Lists",
            phase=LabPhase.DURING_LAB,
            students_enrolled=35,
        )
    )
    assert resp.material is None
    assert resp.activity is None


def test_health_response():
    h = HealthResponse(status="healthy", agent="participant")
    assert h.version == "0.1.0"
