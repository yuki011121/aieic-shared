"""Typed HTTP client for the Curriculum Designer Agent."""

from __future__ import annotations
from typing import Literal, Optional

from aieic_shared.clients.base import AgentClient
from aieic_shared.schemas.curriculum import (
    ApprovalRequest,
    CurriculumMaterial,
    GenerateCurriculumRequest,
    RequestChangesRequest,
    TypoCheckResponse,
)


class CurriculumClient(AgentClient):
    """Client for the Curriculum Designer (port 8003 by default)."""

    AGENT_NAME = "curriculum"

    async def generate(
        self,
        course_id: str,
        lab_id: str,
        title: str,
        learning_objectives: list[str],
        instructor_id: str,
        difficulty: Literal["basic", "intermediate", "challenge"] = "intermediate",
        estimated_duration_min: int = 60,
    ) -> CurriculumMaterial:
        """POST /curriculum/generate — generate a new lab from objectives."""
        body = GenerateCurriculumRequest(
            course_id=course_id,
            lab_id=lab_id,
            title=title,
            learning_objectives=learning_objectives,
            difficulty=difficulty,
            estimated_duration_min=estimated_duration_min,
            instructor_id=instructor_id,
        )
        data = await self._post("/curriculum/generate", json=body.model_dump())
        return CurriculumMaterial(**data)

    async def get(self, lab_id: str) -> CurriculumMaterial:
        """GET /curriculum/{lab_id} — fetch existing lab materials."""
        data = await self._get(f"/curriculum/{lab_id}")
        return CurriculumMaterial(**data)

    async def approve(
        self,
        lab_id: str,
        approved_by: str,
        notes: str = "",
    ) -> CurriculumMaterial:
        """POST /curriculum/{lab_id}/approve."""
        body = ApprovalRequest(approved_by=approved_by, notes=notes)
        data = await self._post(f"/curriculum/{lab_id}/approve", json=body.model_dump())
        return CurriculumMaterial(**data)

    async def request_changes(
        self,
        lab_id: str,
        feedback: str,
        requested_by: str,
    ) -> CurriculumMaterial:
        """POST /curriculum/{lab_id}/request-changes."""
        body = RequestChangesRequest(feedback=feedback, requested_by=requested_by)
        data = await self._post(
            f"/curriculum/{lab_id}/request-changes",
            json=body.model_dump(),
        )
        return CurriculumMaterial(**data)

    async def check_typos(self, lab_id: str) -> TypoCheckResponse:
        """POST /curriculum/{lab_id}/check-typos."""
        data = await self._post(f"/curriculum/{lab_id}/check-typos")
        return TypoCheckResponse(**data)
