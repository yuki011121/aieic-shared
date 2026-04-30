"""
Mock Lab Companion server.

This is the MOST IMPORTANT mock for the Orchestrator developer right now,
because the real Lab Companion (x80_helper) does not yet expose an HTTP API.

Run:
    python -m aieic_shared.mocks.lab_companion --port 8002
"""

from __future__ import annotations
import argparse

from fastapi import FastAPI

from aieic_shared.schemas.companion import (
    ChatRequest,
    ChatResponse,
    ChatSource,
    EscalateRequest,
)
from aieic_shared.schemas.core import HealthResponse


def create_app() -> FastAPI:
    """Build the mock Lab Companion FastAPI app."""
    app = FastAPI(title="Mock Lab Companion", version="0.1.0")

    @app.get("/")
    async def root():
        return {"status": "ok", "agent": "companion-mock", "version": "0.1.0"}

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(status="healthy", agent="companion-mock")

    @app.post("/companion/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        # Generate a believable mock response based on the message.
        msg = request.message.lower()
        if "insert" in msg:
            reply = (
                "Think about what changes when you insert at the head versus the middle. "
                "What pointer needs to be updated first?"
            )
            hint = 1
        elif "delete" in msg or "remove" in msg:
            reply = (
                "Before you free a node, you need to make sure no other pointer still "
                "references it. Walk through what happens to the previous node's `next` field."
            )
            hint = 2
        elif "cycle" in msg or "loop" in msg:
            reply = (
                "Look up Floyd's tortoise and hare algorithm — the two-pointer technique. "
                "It's covered in section 4.3 of the lab spec."
            )
            hint = 3
        else:
            reply = (
                f"Good question about '{request.message[:50]}...'. "
                "What part of the lab spec are you working on right now?"
            )
            hint = 1

        return ChatResponse(
            reply=reply,
            sources=[
                ChatSource(
                    title=f"{request.lab_id}_specification.pdf",
                    uid=f"{request.lab_id}_chunk_03",
                    snippet="See section on pointer manipulation...",
                )
            ],
            hint_level=hint,
            tokens_used=120 + len(request.message),
            should_escalate=False,
        )

    @app.post("/companion/escalate")
    async def escalate(request: EscalateRequest):
        return {"status": "escalated", "session_id": request.session_id}

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock Lab Companion server")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    import uvicorn

    print(f"Starting Mock Lab Companion on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
