"""
Tests that the mock servers conform to the contracts.

These tests use FastAPI's TestClient — no real HTTP server is started.
Confirms that the mocks return data matching the shared schemas, so the
Orchestrator can rely on them.
"""

import pytest
from fastapi.testclient import TestClient

from aieic_shared.mocks.assessment import app as assessment_app
from aieic_shared.mocks.curriculum_designer import app as curriculum_app
from aieic_shared.mocks.lab_companion import app as companion_app
from aieic_shared.mocks.participant import app as participant_app
from aieic_shared.schemas.assessment import AssessmentResult, ManualReviewRequest
from aieic_shared.schemas.companion import ChatResponse
from aieic_shared.schemas.curriculum import CurriculumMaterial
from aieic_shared.schemas.participant import StudentContextResponse


# ---------- Lab Companion ----------

def test_companion_health():
    client = TestClient(companion_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_companion_chat_returns_valid_response():
    client = TestClient(companion_app)
    resp = client.post(
        "/companion/chat",
        json={
            "student_id": "alex_m",
            "session_id": "s1",
            "message": "How do I insert at position 3?",
            "conversation_history": [],
            "lab_id": "lab4",
        },
    )
    assert resp.status_code == 200
    # Must conform to ChatResponse schema
    parsed = ChatResponse(**resp.json())
    assert parsed.reply
    assert 1 <= parsed.hint_level <= 3


# ---------- Participant ----------

def test_participant_log_then_get_context():
    client = TestClient(participant_app)

    # Log a few interactions
    for i in range(3):
        resp = client.post(
            "/participant/log",
            json={
                "student_id": "test_student_1",
                "session_id": "sess1",
                "message": f"What is recursion? Question {i}",
            },
        )
        assert resp.status_code == 200

    # Now context should reflect them
    resp = client.get("/participant/context/test_student_1")
    assert resp.status_code == 200
    parsed = StudentContextResponse(**resp.json())
    assert parsed.total_questions == 3
    assert parsed.sessions_count == 1


def test_participant_context_for_unknown_student():
    client = TestClient(participant_app)
    resp = client.get("/participant/context/nobody")
    assert resp.status_code == 200
    parsed = StudentContextResponse(**resp.json())
    assert parsed.total_questions == 0
    assert "New student" in parsed.summary


# ---------- Curriculum ----------

def test_curriculum_generate_returns_material():
    client = TestClient(curriculum_app)
    resp = client.post(
        "/curriculum/generate",
        json={
            "lab_id": "lab_test",
            "title": "Test Lab",
            "learning_objectives": ["Objective 1"],
            "instructor_id": "kurfess",
        },
    )
    assert resp.status_code == 200
    parsed = CurriculumMaterial(**resp.json())
    assert parsed.lab_id == "lab_test"
    assert parsed.approval_status == "pending"
    assert len(parsed.quiz) > 0


def test_curriculum_approve_changes_status():
    client = TestClient(curriculum_app)
    # Generate first
    client.post(
        "/curriculum/generate",
        json={
            "lab_id": "lab_approve_test",
            "title": "Test",
            "learning_objectives": [],
            "instructor_id": "k",
        },
    )
    # Then approve
    resp = client.post(
        "/curriculum/lab_approve_test/approve",
        json={"approved_by": "kurfess", "notes": ""},
    )
    assert resp.status_code == 200
    parsed = CurriculumMaterial(**resp.json())
    assert parsed.approval_status == "approved"
    assert parsed.approved_by == "kurfess"


# ---------- Assessment ----------

def test_assessment_submit_returns_result():
    client = TestClient(assessment_app)
    resp = client.post(
        "/submit-json",
        json={
            "student_id": "alex_m",
            "assignment_id": "lab4",
            "code": "def foo(): pass",
        },
    )
    assert resp.status_code == 200
    parsed = AssessmentResult(**resp.json())
    assert parsed.student_id == "alex_m"
    assert parsed.code_grade is not None


def test_assessment_flagged_student_creates_review_item():
    client = TestClient(assessment_app)
    # Carlos R is hardcoded as flagged in the mock
    resp = client.post(
        "/submit-json",
        json={
            "student_id": "carlos_r",
            "assignment_id": "lab4",
            "code": "x = 1",
        },
    )
    assert resp.status_code == 200
    parsed = AssessmentResult(**resp.json())
    assert parsed.anomaly_report is not None
    assert parsed.anomaly_report.overall_risk == "high"

    # Should now be in review queue
    queue_resp = client.get("/review-queue")
    assert queue_resp.status_code == 200
    items = [ManualReviewRequest(**item) for item in queue_resp.json()]
    assert any(item.student_id == "carlos_r" for item in items)


def test_assessment_submit_requires_code_or_report():
    client = TestClient(assessment_app)
    resp = client.post(
        "/submit-json",
        json={"student_id": "alex_m", "assignment_id": "lab4"},
    )
    assert resp.status_code == 400
