"""
Mock Assessment Agent server.

Run:
    python -m aieic_shared.mocks.assessment --port 8004
"""

from __future__ import annotations
import argparse
import uuid
from datetime import datetime

from fastapi import FastAPI, Form, HTTPException

from aieic_shared.schemas.assessment import (
    AnomalyFlag,
    AnomalyReport,
    AssessmentRequest,
    AssessmentResult,
    CodeGradeResult,
    FeedbackReport,
    ManualReviewRequest,
    ReportEvaluation,
    SubmissionType,
    TestCaseResult,
)
from aieic_shared.schemas.core import HealthResponse


# In-memory storage
_RESULTS: list[AssessmentResult] = []
_REVIEW_QUEUE: list[ManualReviewRequest] = []


def _make_mock_result(req: AssessmentRequest) -> AssessmentResult:
    """Generate a believable mock assessment based on the student id."""
    sub_type = req.submission_type or (
        SubmissionType.FULL if req.code and req.report
        else SubmissionType.CODE_ONLY if req.code
        else SubmissionType.REPORT_ONLY
    )

    # Crude scoring based on a hash of student id, so results are stable per student
    score_seed = sum(ord(c) for c in req.student_id) % 50
    base_score = 50 + score_seed  # 50-99

    code_grade = None
    if req.code:
        tests_passed = 8 if base_score > 70 else 5
        code_grade = CodeGradeResult(
            test_results=[
                TestCaseResult(
                    name=f"test_{i}",
                    passed=i < tests_passed,
                    expected_output="",
                    points_earned=10.0 if i < tests_passed else 0.0,
                )
                for i in range(10)
            ],
            tests_passed=tests_passed,
            tests_total=10,
            raw_score=tests_passed * 10.0,
            weighted_score=tests_passed * 10.0 * 0.6,
        )

    report_eval = None
    if req.report:
        report_eval = ReportEvaluation(
            raw_score=base_score,
            weighted_score=base_score * 0.3,
            llm_reasoning="Report covers the major points adequately.",
        )

    # Flag a few suspicious students for testing the review flow
    anomaly = None
    if req.student_id.lower() in ("carlos_r", "nina_q"):
        anomaly = AnomalyReport(
            flags=[
                AnomalyFlag(
                    flag_type="plagiarism",
                    confidence=0.87,
                    evidence="High similarity with another submission",
                    severity="high",
                )
            ],
            overall_risk="high",
            recommendation="Manual review recommended",
        )

    automated = (code_grade.weighted_score if code_grade else 0) + (
        report_eval.weighted_score if report_eval else 0
    )

    result = AssessmentResult(
        submission_id=str(uuid.uuid4())[:8],
        student_id=req.student_id,
        assignment_id=req.assignment_id,
        submission_type=sub_type,
        code_grade=code_grade,
        report_evaluation=report_eval,
        anomaly_report=anomaly,
        feedback=FeedbackReport(
            summary=(
                "Solid submission overall."
                if base_score > 75
                else "Partial completion. Some core concepts missing."
            ),
            strengths=["Clear structure"],
            improvements=["Edge case handling"],
        ),
        automated_score=round(automated, 2),
        status="completed",
        agent_reasoning="Mock orchestrator reasoning.",
    )

    if anomaly and anomaly.overall_risk == "high":
        review = ManualReviewRequest(
            submission_id=result.submission_id,
            student_id=req.student_id,
            assignment_id=req.assignment_id,
            automated_score=result.automated_score,
            anomaly_flags=anomaly.flags,
            priority="urgent",
        )
        result.manual_review = review
        _REVIEW_QUEUE.append(review)

    return result


def create_app() -> FastAPI:
    app = FastAPI(title="Mock Assessment Agent", version="0.1.0")

    @app.get("/")
    async def root():
        return {"status": "ok", "agent": "assessment-mock", "version": "0.1.0"}

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(status="healthy", agent="assessment-mock")

    @app.post("/submit-json", response_model=AssessmentResult)
    async def submit_json(req: AssessmentRequest):
        if not req.code and not req.report:
            raise HTTPException(400, "At least one of code or report is required")
        result = _make_mock_result(req)
        _RESULTS.append(result)
        return result

    @app.get("/results")
    async def list_results(student_id: str = None, assignment_id: str = None):
        results = _RESULTS
        if student_id:
            results = [r for r in results if r.student_id == student_id]
        if assignment_id:
            results = [r for r in results if r.assignment_id == assignment_id]
        return [r.model_dump() for r in results]

    @app.get("/results/{submission_id}", response_model=AssessmentResult)
    async def get_result(submission_id: str):
        for r in _RESULTS:
            if r.submission_id == submission_id:
                return r
        raise HTTPException(404, f"Submission '{submission_id}' not found")

    @app.get("/assignments")
    async def list_assignments():
        return [{"assignment_id": "lab4", "title": "Linked Lists"}]

    @app.get("/review-queue")
    async def list_review_queue(status: str = None):
        queue = _REVIEW_QUEUE
        if status:
            queue = [r for r in queue if r.status == status]
        return [r.model_dump() for r in queue]

    @app.post("/review-queue/{submission_id}/complete")
    async def complete_review(
        submission_id: str,
        instructor_score: float = Form(...),
        notes: str = Form(""),
    ):
        for r in _REVIEW_QUEUE:
            if r.submission_id == submission_id:
                r.status = "completed"
                r.instructor_score = instructor_score
                r.instructor_notes = notes
                # Update final score in result
                for res in _RESULTS:
                    if res.submission_id == submission_id:
                        res.final_score = round(
                            res.automated_score + instructor_score * 0.1 * 100,
                            2,
                        )
                        break
                return {"status": "completed", "submission_id": submission_id}
        raise HTTPException(404, f"Submission '{submission_id}' not in review queue")

    @app.get("/anomalies")
    async def list_anomalies(reviewed: bool = None):
        return [
            r.model_dump() for r in _RESULTS
            if r.anomaly_report and r.anomaly_report.flags
        ]

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock Assessment Agent server")
    parser.add_argument("--port", type=int, default=8004)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    import uvicorn

    print(f"Starting Mock Assessment Agent on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
