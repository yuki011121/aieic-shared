"""
Core schemas shared across every agent.

These are the universal building blocks. Every agent imports these — never
redefine LabPhase, StudentRef, etc. anywhere else.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class LabPhase(str, Enum):
    """Where in the lifecycle of a lab the student is."""
    PRE_LAB = "pre_lab"
    DURING_LAB = "during_lab"
    POST_LAB = "post_lab"


class StudentStatus(str, Enum):
    """High-level student health, used in the live activity dashboard."""
    ON_TRACK = "on_track"
    NEEDS_HELP = "needs_help"
    FLAGGED = "flagged"
    INACTIVE = "inactive"


class Severity(str, Enum):
    """Severity scale for flags, anomalies, and review priorities."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ============================================================================
# Reference models — lightweight identifiers passed between agents
# ============================================================================

class StudentRef(BaseModel):
    """Universal student identifier."""
    student_id: str = Field(..., description="Short string id, e.g. 'alex_m'")
    course_id: str = Field(default="csc580", description="Course this student belongs to")


class LabRef(BaseModel):
    """Universal lab identifier."""
    lab_id: str = Field(..., description="Short string id, e.g. 'lab4'")
    course_id: str = Field(default="csc580")


class SessionRef(BaseModel):
    """A single student-lab interaction session."""
    session_id: str = Field(..., description="UUID4")
    student_id: str
    lab_id: str
    started_at: datetime


# ============================================================================
# Universal response envelopes
# ============================================================================

class HealthResponse(BaseModel):
    """Returned by every agent's GET /health."""
    status: str = Field(..., description="'healthy' | 'degraded' | 'unhealthy'")
    agent: str = Field(..., description="Agent name, e.g. 'participant'")
    version: str = Field(default="0.1.0")


class ErrorDetail(BaseModel):
    """Inner error detail."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable message")
    agent: str = Field(..., description="Which agent produced this error")
    request_id: Optional[str] = Field(default=None, description="For tracing")


class ErrorResponse(BaseModel):
    """Standard error envelope returned for all non-2xx responses."""
    error: ErrorDetail
