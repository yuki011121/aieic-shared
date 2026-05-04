"""Typed HTTP client for the Integrity Agent."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from aieic_shared.clients.base import AgentClient
from aieic_shared.schemas.integrity import (
    EndSessionRequest,
    EndSessionResponse,
    LabAnalyticsResponse,
    StartSessionRequest,
    StartSessionResponse,
    ValidateQuestionRequest,
    ValidateQuestionResponse,
)


class IntegrityClient(AgentClient):
    """
    Client for the Integrity Agent (port 8005 by default).

    All endpoints except GET /health require an internal token, passed via
    the X-Internal-Token header. Supply it via the `internal_token` argument;
    it is baked into every request automatically.
    """

    AGENT_NAME = "integrity"

    def __init__(
        self,
        base_url: str,
        *,
        internal_token: str = "",
        timeout: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        # Bake the auth header into the shared httpx client so every call
        # inherits it without the base class needing to know about it.
        if client is None:
            client = httpx.AsyncClient(
                timeout=timeout,
                headers={"X-Internal-Token": internal_token},
            )
        super().__init__(base_url, client=client)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def start_session(
        self,
        student_id: str,
        session_id: str,
        lab_id: str,
        course_id: str = "CSC580",
    ) -> StartSessionResponse:
        """POST /session/start — initialize integrity tracking for a new session."""
        body = StartSessionRequest(
            student_id=student_id,
            session_id=session_id,
            lab_id=lab_id,
            course_id=course_id,
        )
        data = await self._post("/session/start", json=body.model_dump())
        return StartSessionResponse(**data)

    async def end_session(
        self,
        student_id: str,
        session_id: str,
    ) -> EndSessionResponse:
        """POST /session/end — close session and generate integrity summary."""
        body = EndSessionRequest(student_id=student_id, session_id=session_id)
        data = await self._post("/session/end", json=body.model_dump())
        return EndSessionResponse(**data)

    # ------------------------------------------------------------------
    # Per-message policy gate
    # ------------------------------------------------------------------

    async def validate(
        self,
        student_id: str,
        session_id: str,
        lab_id: str,
        question_text: str,
        conversation_history: Optional[list[dict]] = None,
        course_id: str = "CSC580",
    ) -> ValidateQuestionResponse:
        """
        POST /validate — synchronous policy gate.

        Call this BEFORE forwarding the student message to the Lab Companion.
        If the response has session_escalated=True, return a refusal to the
        student and skip the Lab Companion entirely.
        """
        body = ValidateQuestionRequest(
            student_id=student_id,
            session_id=session_id,
            lab_id=lab_id,
            course_id=course_id,
            question_text=question_text,
            conversation_history=conversation_history or [],
        )
        data = await self._post("/validate", json=body.model_dump())
        return ValidateQuestionResponse(**data)

    # ------------------------------------------------------------------
    # Instructor dashboard data
    # ------------------------------------------------------------------

    async def get_lab_analytics(
        self,
        lab_id: str,
        course_id: Optional[str] = None,
    ) -> LabAnalyticsResponse:
        """GET /analytics/lab/{lab_id} — per-student integrity stats for instructor dashboard."""
        params = {"course_id": course_id} if course_id else None
        data = await self._get(f"/analytics/lab/{lab_id}", params=params)
        return LabAnalyticsResponse(**data)

    async def get_report(self, report_id: str, student_id: str) -> Any:
        """GET /report/{report_id} — retrieve a specific integrity report."""
        data = await self._get(f"/report/{report_id}", params={"student_id": student_id})
        return data
