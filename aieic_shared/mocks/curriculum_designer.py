"""
Mock Curriculum Designer server.

Lets the Orchestrator developer test the pre-lab approval flow without
waiting for the real Curriculum Designer to be built.

Run:
    python -m aieic_shared.mocks.curriculum_designer --port 8003
"""

from __future__ import annotations
import argparse
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from aieic_shared.schemas.core import HealthResponse
from aieic_shared.schemas.curriculum import (
    ApprovalRequest,
    CurriculumMaterial,
    GenerateCurriculumRequest,
    QuizQuestion,
    QuizQuestionType,
    RequestChangesRequest,
    Rubric,
    TypoCheckResponse,
    TypoIssue,
)


# In-memory store keyed by lab_id
_STORE: dict[str, CurriculumMaterial] = {}


def _make_mock_material(req: GenerateCurriculumRequest) -> CurriculumMaterial:
    """Build a believable lab package from a generate request."""
    now = datetime.now(timezone.utc)
    return CurriculumMaterial(
        lab_id=req.lab_id,
        course_id=req.course_id,
        title=f"{req.title} Quiz",
        spec_markdown=(
            f"# {req.title}\n\n"
            f"## Learning Objectives\n"
            + "\n".join(f"- {obj}" for obj in req.learning_objectives)
            + f"\n\n## Estimated Duration\n{req.estimated_duration_min} minutes\n"
        ),
        quiz=[
            QuizQuestion(
                id="q1",
                question=(
                    "What is the time complexity of inserting a node at the head "
                    "of a singly linked list?"
                ),
                type=QuizQuestionType.SHORT_ANSWER,
                expected_answer="O(1)",
                rubric_points=10.0,
            ),
            QuizQuestion(
                id="q2",
                question="Explain the difference between a singly and doubly linked list.",
                type=QuizQuestionType.SHORT_ANSWER,
                rubric_points=10.0,
            ),
            QuizQuestion(
                id="q3",
                question="Write pseudocode for deleting a node with a given value.",
                type=QuizQuestionType.CODE,
                rubric_points=20.0,
            ),
            QuizQuestion(
                id="q4",
                question="What happens when you lose the reference to the head node?",
                type=QuizQuestionType.SHORT_ANSWER,
                rubric_points=10.0,
            ),
            QuizQuestion(
                id="q5",
                question="How would you detect a cycle in a linked list? Describe the algorithm.",
                type=QuizQuestionType.SHORT_ANSWER,
                rubric_points=15.0,
            ),
        ],
        rubric=Rubric(
            code_weight=0.6,
            report_weight=0.3,
            manual_weight=0.1,
            guidance="Focus on correctness, then style.",
        ),
        approval_status="pending",
        generated_at=now,
        last_updated=now,
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Mock Curriculum Designer", version="0.1.0")

    @app.get("/")
    async def root():
        return {"status": "ok", "agent": "curriculum-mock", "version": "0.1.0"}

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(status="healthy", agent="curriculum-mock")

    @app.post("/curriculum/generate", response_model=CurriculumMaterial)
    async def generate(req: GenerateCurriculumRequest):
        material = _make_mock_material(req)
        _STORE[req.lab_id] = material
        return material

    @app.get("/curriculum/{lab_id}", response_model=CurriculumMaterial)
    async def get_material(lab_id: str):
        if lab_id not in _STORE:
            # If never generated, generate one on the fly with default objectives
            req = GenerateCurriculumRequest(
                lab_id=lab_id,
                title=lab_id.replace("_", " ").title(),
                learning_objectives=["Sample objective 1", "Sample objective 2"],
                instructor_id="mock_instructor",
            )
            _STORE[lab_id] = _make_mock_material(req)
        return _STORE[lab_id]

    @app.post("/curriculum/{lab_id}/approve", response_model=CurriculumMaterial)
    async def approve(lab_id: str, req: ApprovalRequest):
        if lab_id not in _STORE:
            raise HTTPException(404, f"Lab '{lab_id}' not found")
        material = _STORE[lab_id]
        material.approval_status = "approved"
        material.approved_by = req.approved_by
        material.last_updated = datetime.now(timezone.utc)
        return material

    @app.post("/curriculum/{lab_id}/request-changes", response_model=CurriculumMaterial)
    async def request_changes(lab_id: str, req: RequestChangesRequest):
        if lab_id not in _STORE:
            raise HTTPException(404, f"Lab '{lab_id}' not found")
        material = _STORE[lab_id]
        material.approval_status = "changes_requested"
        material.last_updated = datetime.now(timezone.utc)
        return material

    @app.post("/curriculum/{lab_id}/check-typos", response_model=TypoCheckResponse)
    async def check_typos(lab_id: str):
        return TypoCheckResponse(
            issues_found=1,
            issues=[
                TypoIssue(
                    location="q3",
                    type="ambiguity",
                    suggestion="Specify whether the list is singly or doubly linked.",
                    original_text="Write pseudocode for deleting a node with a given value.",
                )
            ],
        )

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock Curriculum Designer server")
    parser.add_argument("--port", type=int, default=8003)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    import uvicorn

    print(f"Starting Mock Curriculum Designer on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
