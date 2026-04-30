"""Typed HTTP client for the Lab Companion."""

from __future__ import annotations
from typing import Literal, Optional

from aieic_shared.clients.base import AgentClient
from aieic_shared.schemas.companion import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    EscalateRequest,
)


class LabCompanionClient(AgentClient):
    """Client for the Lab Companion (port 8002 by default)."""

    AGENT_NAME = "companion"

    async def chat(
        self,
        student_id: str,
        session_id: str,
        message: str,
        lab_id: str,
        conversation_history: Optional[list[ChatMessage]] = None,
        student_context_summary: Optional[str] = None,
    ) -> ChatResponse:
        """
        POST /companion/chat — stateless single-turn chat.

        The Orchestrator is responsible for tracking conversation_history and
        passing it on every call.
        """
        body = ChatRequest(
            student_id=student_id,
            session_id=session_id,
            message=message,
            lab_id=lab_id,
            conversation_history=conversation_history or [],
            student_context_summary=student_context_summary,
        )
        data = await self._post("/companion/chat", json=body.model_dump())
        return ChatResponse(**data)

    async def escalate(
        self,
        student_id: str,
        session_id: str,
        reason: Literal["out_of_scope", "repeated_failure", "policy_violation", "other"],
        context: str = "",
    ) -> None:
        """POST /companion/escalate — log an escalation event."""
        body = EscalateRequest(
            student_id=student_id,
            session_id=session_id,
            reason=reason,
            context=context,
        )
        await self._post("/companion/escalate", json=body.model_dump())
