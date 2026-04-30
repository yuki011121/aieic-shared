"""Typed HTTP client for the Participant Agent."""

from __future__ import annotations
from typing import Optional

from aieic_shared.clients.base import AgentClient
from aieic_shared.schemas.participant import (
    LogInteractionRequest,
    LogInteractionResponse,
    StudentContextResponse,
)


class ParticipantClient(AgentClient):
    """Client for the Participant Agent (port 8001 by default)."""

    AGENT_NAME = "participant"

    async def log_interaction(
        self,
        student_id: str,
        session_id: str,
        message: str,
        response_time_ms: Optional[int] = None,
    ) -> LogInteractionResponse:
        """POST /participant/log — log a single student interaction."""
        body = LogInteractionRequest(
            student_id=student_id,
            session_id=session_id,
            message=message,
            response_time_ms=response_time_ms,
        )
        data = await self._post("/participant/log", json=body.model_dump())
        return LogInteractionResponse(**data)

    async def get_student_context(self, student_id: str) -> StudentContextResponse:
        """GET /participant/context/{student_id} — aggregated learning profile."""
        data = await self._get(f"/participant/context/{student_id}")
        return StudentContextResponse(**data)
