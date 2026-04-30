"""
Lab Companion (a.k.a. tutoring agent, x80_helper) schemas.

The Lab Companion is the student-facing tutor. These schemas define how the
Orchestrator talks to it.

KEY DESIGN DECISION: The Lab Companion is STATELESS at this API layer.
The Orchestrator is responsible for tracking conversation history and
supplying it on every call. This makes the service horizontally scalable.
"""

from __future__ import annotations
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single turn in a conversation."""
    role: Literal["user", "assistant", "system"]
    content: str


class ChatSource(BaseModel):
    """A document chunk that grounded the response."""
    title: str = Field(..., description="Source filename or document title")
    uid: str = Field(..., description="Chunk UID, e.g. 'parent_id_chunk_id'")
    snippet: Optional[str] = Field(default=None, description="Optional preview text")


class ChatRequest(BaseModel):
    """
    POST /companion/chat — request body.

    The caller (Orchestrator) supplies all context the Companion needs to respond.
    """
    student_id: str
    session_id: str
    message: str = Field(..., description="The student's latest message")
    conversation_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Previous turns in this session, in chronological order",
    )
    student_context_summary: Optional[str] = Field(
        default=None,
        description="Narrative summary from Participant Agent's /context endpoint",
    )
    lab_id: str = Field(..., description="Which lab the student is working on")


class ChatResponse(BaseModel):
    """POST /companion/chat — response body."""
    reply: str = Field(..., description="The Companion's natural-language response")
    sources: list[ChatSource] = Field(
        default_factory=list,
        description="RAG sources cited in the reply",
    )
    hint_level: int = Field(
        default=1,
        ge=1,
        le=3,
        description="1 = subtle nudge, 2 = explain error, 3 = point to docs",
    )
    tokens_used: int = Field(default=0, description="Total tokens for this turn")
    should_escalate: bool = Field(
        default=False,
        description="True if Companion thinks instructor should intervene",
    )


class EscalateRequest(BaseModel):
    """POST /companion/escalate — log when the Companion gives up."""
    student_id: str
    session_id: str
    reason: Literal["out_of_scope", "repeated_failure", "policy_violation", "other"]
    context: str = Field(default="", description="Free-form description of why")
