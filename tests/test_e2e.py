"""End-to-end smoke test: client calls mock via TestClient transport."""

import httpx
import pytest

from aieic_shared.clients import (
    LabCompanionClient,
    ParticipantClient,
    CurriculumClient,
    AssessmentClient,
)
from aieic_shared.mocks.assessment import app as assessment_app
from aieic_shared.mocks.curriculum_designer import app as curriculum_app
from aieic_shared.mocks.lab_companion import app as companion_app
from aieic_shared.mocks.participant import app as participant_app


# ---- Helper: build a client whose transport routes to the mock app -----

def _client_for(app, ClientClass):
    """Wire up a client to talk to a mock FastAPI app via in-process transport."""
    transport = httpx.ASGITransport(app=app)
    httpx_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    return ClientClass(base_url="http://testserver", client=httpx_client)


@pytest.mark.asyncio
async def test_companion_client_against_mock():
    client = _client_for(companion_app, LabCompanionClient)
    try:
        health = await client.health()
        assert health.status == "healthy"

        resp = await client.chat(
            student_id="alex_m",
            session_id="s1",
            message="How do I insert at position 3?",
            lab_id="lab4",
        )
        assert resp.reply
        assert 1 <= resp.hint_level <= 3
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_participant_client_against_mock():
    client = _client_for(participant_app, ParticipantClient)
    try:
        log_resp = await client.log_interaction(
            student_id="e2e_student",
            session_id="s1",
            message="What is recursion?",
        )
        assert log_resp.status == "ok"
        assert log_resp.interaction_id

        ctx = await client.get_student_context("e2e_student")
        assert ctx.total_questions == 1
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_curriculum_client_against_mock():
    client = _client_for(curriculum_app, CurriculumClient)
    try:
        material = await client.generate(
            course_id="csc580",
            lab_id="lab_e2e",
            title="E2E Test Lab",
            learning_objectives=["Test the contract"],
            instructor_id="kurfess",
        )
        assert material.lab_id == "lab_e2e"
        assert material.approval_status == "pending"

        approved = await client.approve("lab_e2e", approved_by="kurfess")
        assert approved.approval_status == "approved"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_assessment_client_against_mock():
    client = _client_for(assessment_app, AssessmentClient)
    try:
        result = await client.submit(
            student_id="alex_m",
            assignment_id="lab4",
            code="def foo(): return 1",
        )
        assert result.student_id == "alex_m"
        assert result.code_grade is not None

        # List results filtered by student
        results = await client.list_results(student_id="alex_m")
        assert any(r.student_id == "alex_m" for r in results)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_full_orchestrator_style_flow():
    """
    Simulates what the Orchestrator will do for a single student message:
      1. fetch student context from Participant
      2. ask Companion for a reply
      3. log interaction back to Participant
    """
    participant = _client_for(participant_app, ParticipantClient)
    companion = _client_for(companion_app, LabCompanionClient)

    try:
        # 1. Get context (new student → empty)
        ctx = await participant.get_student_context("alex_m")
        assert ctx.total_questions == 0

        # 2. Ask companion
        chat_resp = await companion.chat(
            student_id="alex_m",
            session_id="s1",
            message="How do I delete a node?",
            lab_id="lab4",
            student_context_summary=ctx.summary,
        )
        assert chat_resp.reply

        # 3. Log it
        log_resp = await participant.log_interaction(
            student_id="alex_m",
            session_id="s1",
            message="How do I delete a node?",
        )
        assert log_resp.status == "ok"

        # 4. Re-fetch context — should now have 1 interaction
        ctx2 = await participant.get_student_context("alex_m")
        assert ctx2.total_questions == 1
    finally:
        await participant.close()
        await companion.close()
