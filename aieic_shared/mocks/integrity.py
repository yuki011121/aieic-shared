"""
Mock Integrity Agent server.

Classifies questions with simple keyword heuristics and tracks per-session
violation counts in memory. Useful for Orchestrator integration tests when
the real Integrity Agent isn't running.

Run:
    python -m aieic_shared.mocks.integrity --port 8005
"""

from __future__ import annotations

import argparse
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query

from aieic_shared.schemas.integrity import (
    EndSessionRequest,
    EndSessionResponse,
    LabAnalyticsResponse,
    QuestionClassification,
    StartSessionRequest,
    StartSessionResponse,
    StudentLabSummary,
    ValidateQuestionRequest,
    ValidateQuestionResponse,
    ViolationType,
)


# In-memory state keyed by session_id
_sessions: dict[str, dict] = {}


def _classify(text: str) -> QuestionClassification:
    t = text.lower()
    if any(k in t for k in ("give me the answer", "what is the answer", "tell me the solution",
                             "write the code for", "write me", "complete this for me")):
        return QuestionClassification.ANSWER_FARMING
    if any(k in t for k in ("what is the solution", "solve this", "just give me",
                             "answer to question", "direct answer")):
        return QuestionClassification.DIRECT_SOLUTION
    if any(k in t for k in ("what does this mean", "can you clarify", "i don't understand",
                             "what is the requirement", "is it asking")):
        return QuestionClassification.CLARIFICATION
    if any(k in t for k in ("what is", "explain", "why does", "why is", "how does",
                             "what are", "concept", "theory", "understand")):
        return QuestionClassification.CONCEPTUAL
    return QuestionClassification.PROCEDURAL


def _is_violation(cls: QuestionClassification) -> tuple[bool, Optional[ViolationType]]:
    if cls == QuestionClassification.DIRECT_SOLUTION:
        return True, ViolationType.DIRECT_SOLUTION_REQUEST
    if cls == QuestionClassification.ANSWER_FARMING:
        return True, ViolationType.ANSWER_FARMING
    return False, None


def create_app() -> FastAPI:
    app = FastAPI(title="Mock Integrity Agent", version="0.1.0")

    @app.get("/")
    async def root():
        return {"status": "ok", "agent": "integrity-mock", "version": "0.1.0"}

    @app.get("/health")
    async def health():
        return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    @app.post("/session/start", response_model=StartSessionResponse)
    async def start_session(req: StartSessionRequest):
        _sessions[req.session_id] = {
            "student_id": req.student_id,
            "lab_id": req.lab_id,
            "course_id": req.course_id,
            "started_at": datetime.now(timezone.utc),
            "question_count": 0,
            "violation_count": 0,
            "violations": [],
            "classifications": [],
        }
        return StartSessionResponse(
            session_id=req.session_id,
            started_at=_sessions[req.session_id]["started_at"],
        )

    @app.post("/session/end", response_model=EndSessionResponse)
    async def end_session(req: EndSessionRequest):
        sess = _sessions.get(req.session_id, {})
        report_id = str(uuid.uuid4())
        return EndSessionResponse(
            session_id=req.session_id,
            report_id=report_id,
            ended_at=datetime.now(timezone.utc),
            summary={
                "question_count": sess.get("question_count", 0),
                "violation_count": sess.get("violation_count", 0),
                "final_status": "ESCALATED" if sess.get("violation_count", 0) >= 3 else
                                "WARNING" if sess.get("violation_count", 0) > 0 else "CLEAN",
            },
        )

    @app.post("/validate", response_model=ValidateQuestionResponse)
    async def validate(req: ValidateQuestionRequest):
        sess = _sessions.setdefault(req.session_id, {
            "student_id": req.student_id,
            "lab_id": req.lab_id,
            "question_count": 0,
            "violation_count": 0,
            "violations": [],
            "classifications": [],
        })

        classification = _classify(req.question_text)
        violated, violation_type = _is_violation(classification)

        sess["question_count"] += 1
        sess["classifications"].append(classification.value)
        if violated:
            sess["violation_count"] += 1
            sess["violations"].append(violation_type.value if violation_type else None)

        escalated = sess["violation_count"] >= 3

        return ValidateQuestionResponse(
            classification=classification,
            violation_detected=violated,
            violation_type=violation_type,
            violation_count=sess["violation_count"],
            question_count=sess["question_count"],
            session_escalated=escalated,
        )

    @app.get("/analytics/lab/{lab_id}", response_model=LabAnalyticsResponse)
    async def lab_analytics(lab_id: str, course_id: Optional[str] = Query(default=None)):
        lab_sessions = [s for s in _sessions.values() if s.get("lab_id") == lab_id]

        per_student: list[StudentLabSummary] = []
        classification_distribution: dict[str, int] = {}
        total_questions = 0
        total_violations = 0
        escalated_count = 0

        for sess in lab_sessions:
            q = sess.get("question_count", 0)
            v = sess.get("violation_count", 0)
            total_questions += q
            total_violations += v
            if v >= 3:
                escalated_count += 1
            breakdown: dict[str, int] = {}
            for c in sess.get("classifications", []):
                breakdown[c] = breakdown.get(c, 0) + 1
                classification_distribution[c] = classification_distribution.get(c, 0) + 1
            status = "FLAGGED" if v >= 3 else "NEEDS_HELP" if v > 0 else "ON_TRACK"
            per_student.append(StudentLabSummary(
                student_id=sess.get("student_id", "unknown"),
                question_count=q,
                violation_count=v,
                status=status,
                classification_breakdown=breakdown,
            ))

        n = len(lab_sessions) or 1
        return LabAnalyticsResponse(
            lab_id=lab_id,
            course_id=course_id or "CSC580",
            session_stats={
                "total_sessions": len(lab_sessions),
                "active_sessions": len(lab_sessions),
                "closed_sessions": 0,
            },
            question_stats={
                "total_questions": total_questions,
                "avg_questions_per_student": round(total_questions / n, 1),
                "direct_solution_attempts": sum(
                    1 for s in lab_sessions for v in s.get("violations", [])
                    if v == ViolationType.DIRECT_SOLUTION_REQUEST.value
                ),
                "answer_farming_attempts": sum(
                    1 for s in lab_sessions for v in s.get("violations", [])
                    if v == ViolationType.ANSWER_FARMING.value
                ),
                "escalated_session_count": escalated_count,
            },
            classification_distribution=classification_distribution,
            per_student=per_student,
        )

    @app.get("/report/{report_id}")
    async def get_report(report_id: str, student_id: str = Query(...)):
        return {
            "report_id": report_id,
            "student_id": student_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": "mock report — no persisted data in mock server",
        }

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock Integrity Agent server")
    parser.add_argument("--port", type=int, default=8005)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    import uvicorn
    print(f"Starting Mock Integrity Agent on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
