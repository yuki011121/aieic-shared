"""
Participant Agent schemas.

These mirror the schemas in participant-agent-AIEIC-main/main.py. By moving
them here, the Orchestrator and any other caller can import the typed shapes
directly instead of re-defining them.

Owner: Yayun
"""

from __future__ import annotations
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    """Categories of student questions, as classified by the Participant Agent."""
    DEBUGGING = "debugging"
    CONCEPT = "concept"
    SETUP = "setup"
    OTHER = "other"


# ============================================================================
# POST /participant/log
# ============================================================================

class LogInteractionRequest(BaseModel):
    """Body for POST /participant/log."""
    student_id: str
    session_id: str
    message: str = Field(..., description="Student's message; will be truncated to 500 chars")
    response_time_ms: Optional[int] = Field(
        default=None,
        description="Optional: how long the Companion took to respond, in ms",
    )


class LogInteractionResponse(BaseModel):
    """Response from POST /participant/log."""
    status: str = Field(default="ok")
    interaction_id: str = Field(..., description="UUID4 of the persisted interaction")


# ============================================================================
# GET /participant/context/{student_id}
# ============================================================================

class StudentContextResponse(BaseModel):
    """
    Aggregated student profile, returned by GET /participant/context/{student_id}.

    The `summary` field is the LLM-generated narrative used by the Lab Companion
    to personalize its responses.
    """
    total_questions: int = Field(default=0)
    question_type_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Mapping of QuestionType → count",
    )
    avg_hint_level: float = Field(
        default=0.0,
        description="Average hint level needed (1–3, see ChatResponse.hint_level)",
    )
    sessions_count: int = Field(default=0)
    avg_questions_per_session: float = Field(default=0.0)
    session_help_frequency: dict[str, int] = Field(
        default_factory=dict,
        description="Mapping of session_id → number of help requests",
    )
    summary: str = Field(
        default="",
        description="Narrative summary for downstream agents to use as context",
    )
