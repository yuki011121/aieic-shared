"""Typed HTTP client for the Assessment Agent."""

from __future__ import annotations
from typing import Optional

from aieic_shared.clients.base import AgentClient
from aieic_shared.schemas.assessment import (
    AssessmentRequest,
    AssessmentResult,
    ManualReviewRequest,
    SubmissionType,
)


class AssessmentClient(AgentClient):
    """Client for the Assessment Agent (port 8004 by default)."""

    AGENT_NAME = "assessment"

    async def submit(
        self,
        student_id: str,
        assignment_id: str,
        code: Optional[str] = None,
        report: Optional[str] = None,
        submission_type: Optional[SubmissionType] = None,
    ) -> AssessmentResult:
        """POST /submit-json — submit student work for grading."""
        body = AssessmentRequest(
            student_id=student_id,
            assignment_id=assignment_id,
            code=code,
            report=report,
            submission_type=submission_type,
        )
        data = await self._post("/submit-json", json=body.model_dump())
        return AssessmentResult(**data)

    async def list_results(
        self,
        student_id: Optional[str] = None,
        assignment_id: Optional[str] = None,
    ) -> list[AssessmentResult]:
        """GET /results?student_id=...&assignment_id=..."""
        params: dict = {}
        if student_id:
            params["student_id"] = student_id
        if assignment_id:
            params["assignment_id"] = assignment_id
        data = await self._get("/results", params=params or None)
        return [AssessmentResult(**item) for item in data]

    async def get_result(self, submission_id: str) -> AssessmentResult:
        """GET /results/{submission_id}."""
        data = await self._get(f"/results/{submission_id}")
        return AssessmentResult(**data)

    async def get_review_queue(
        self,
        status: Optional[str] = None,
    ) -> list[ManualReviewRequest]:
        """GET /review-queue — manual review queue."""
        params = {"status": status} if status else None
        data = await self._get("/review-queue", params=params)
        return [ManualReviewRequest(**item) for item in data]

    async def complete_review(
        self,
        submission_id: str,
        instructor_score: float,
        notes: str = "",
    ) -> dict:
        """
        POST /review-queue/{submission_id}/complete.

        Note: Assessment Agent expects form data, not JSON.
        """
        return await self._post(
            f"/review-queue/{submission_id}/complete",
            data={"instructor_score": instructor_score, "notes": notes},
        )

    async def get_anomalies(self, reviewed: Optional[bool] = None) -> list[dict]:
        """GET /anomalies — flagged anomaly reports."""
        params: dict = {}
        if reviewed is not None:
            params["reviewed"] = str(reviewed).lower()
        return await self._get("/anomalies", params=params or None)
