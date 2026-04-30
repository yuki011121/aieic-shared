"""
Mock Participant Agent server.

Useful even though the real Participant Agent is implemented — when integration-
testing the Orchestrator without spinning up Cosmos DB, this mock is faster.

Run:
    python -m aieic_shared.mocks.participant --port 8001
"""

from __future__ import annotations
import argparse
import uuid

from fastapi import FastAPI

from aieic_shared.schemas.core import HealthResponse
from aieic_shared.schemas.participant import (
    LogInteractionRequest,
    LogInteractionResponse,
    StudentContextResponse,
)


# In-memory log of interactions keyed by student_id
_LOG: dict[str, list[dict]] = {}


def _classify(message: str) -> str:
    """Crude question classifier matching the real agent's output shape."""
    m = message.lower()
    if any(k in m for k in ("error", "exception", "bug", "doesn't work", "stack trace")):
        return "debugging"
    if any(k in m for k in ("what is", "explain", "why", "concept", "understand")):
        return "concept"
    if any(k in m for k in ("install", "setup", "config", "compile", "run")):
        return "setup"
    return "other"


def create_app() -> FastAPI:
    app = FastAPI(title="Mock Participant Agent", version="0.1.0")

    @app.get("/")
    async def root():
        return {"status": "ok", "agent": "participant-mock", "version": "0.1.0"}

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(status="healthy", agent="participant-mock")

    @app.post("/participant/log", response_model=LogInteractionResponse)
    async def log(req: LogInteractionRequest):
        _LOG.setdefault(req.student_id, []).append(
            {
                "session_id": req.session_id,
                "message": req.message[:500],
                "question_type": _classify(req.message),
                "hint_level": 2 if "error" in req.message.lower() else 1,
            }
        )
        return LogInteractionResponse(status="ok", interaction_id=str(uuid.uuid4()))

    @app.get(
        "/participant/context/{student_id}",
        response_model=StudentContextResponse,
    )
    async def get_context(student_id: str):
        items = _LOG.get(student_id, [])
        if not items:
            return StudentContextResponse(
                summary="New student - no previous interactions recorded.",
            )

        type_counts: dict[str, int] = {}
        sessions: dict[str, int] = {}
        hint_levels: list[int] = []
        for item in items:
            type_counts[item["question_type"]] = type_counts.get(item["question_type"], 0) + 1
            sessions[item["session_id"]] = sessions.get(item["session_id"], 0) + 1
            hint_levels.append(item["hint_level"])

        total = len(items)
        sessions_count = len(sessions)
        primary = max(type_counts, key=type_counts.get) if type_counts else "other"
        avg_hint = sum(hint_levels) / len(hint_levels) if hint_levels else 0.0

        summary = (
            f"Student has asked {total} questions across {sessions_count} session(s). "
            f"Primary focus: {primary}. "
            + (
                "Often needs detailed explanations."
                if avg_hint > 2
                else "Moderate assistance level."
                if avg_hint > 1.5
                else "Often understands with minimal hints."
            )
        )

        return StudentContextResponse(
            total_questions=total,
            question_type_distribution=type_counts,
            avg_hint_level=round(avg_hint, 2),
            sessions_count=sessions_count,
            avg_questions_per_session=round(total / sessions_count, 1),
            session_help_frequency=sessions,
            summary=summary,
        )

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock Participant Agent server")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    import uvicorn

    print(f"Starting Mock Participant Agent on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
