"""
Orchestrator schemas.

These define the public API that the frontend (React + Figma) consumes.
The Orchestrator is the single entry point — the frontend never talks
directly to other agents.

These schemas combine information from multiple downstream agents into
shapes that map cleanly onto the four dashboard tabs:
  Tab 1: Material Preview    → DashboardMaterialBlock
  Tab 2: Student Activity    → DashboardActivityBlock
  Tab 3: Graded Submissions  → DashboardGradesBlock
  Tab 4: Statistics          → DashboardStatsBlock

Owner: Yayun
"""

from __future__ import annotations
from typing import Literal, Optional

from pydantic import BaseModel, Field

from aieic_shared.schemas.companion import ChatSource
from aieic_shared.schemas.core import LabPhase, StudentStatus
from aieic_shared.schemas.curriculum import CurriculumMaterial


# ============================================================================
# Student-facing endpoints
# ============================================================================

class StudentMessageRequest(BaseModel):
    """POST /orchestrator/student/message — body."""
    student_id: str
    session_id: Optional[str] = Field(
        default=None,
        description="If null/empty, Orchestrator creates a new session",
    )
    lab_id: str
    message: str


class StudentMessageResponse(BaseModel):
    """POST /orchestrator/student/message — response."""
    session_id: str = Field(..., description="Echoed back; new if one was created")
    reply: str
    sources: list[ChatSource] = Field(default_factory=list)
    hint_level: int = Field(default=1, ge=1, le=3)
    tokens_used: int = Field(default=0)


class StudentSubmitRequest(BaseModel):
    """
    POST /orchestrator/student/submit — body (when sent as JSON).

    Multipart variant uploads files instead of inline content.
    """
    student_id: str
    assignment_id: str
    code: Optional[str] = None
    report: Optional[str] = None


# ============================================================================
# Instructor dashboard — top-level structure
# ============================================================================

class DashboardLabInfo(BaseModel):
    """Header info for the dashboard."""
    lab_id: str
    title: str
    phase: LabPhase
    students_enrolled: int


# ----- Tab 1: Material Preview ----------------------------------------------

class DashboardMaterialBlock(BaseModel):
    """Tab 1 content."""
    spec_file: Optional[str] = Field(
        default=None,
        description="Filename shown in 'LAB MATERIAL' sidebar, e.g. 'Lab4_specification.pdf'",
    )
    spec_size_mb: Optional[float] = None
    curriculum: Optional[CurriculumMaterial] = Field(
        default=None,
        description="The full generated material from Curriculum Designer",
    )


# ----- Tab 2: Student Activity ----------------------------------------------

class DashboardActivityCard(BaseModel):
    """One student card in Tab 2."""
    student_id: str
    display_name: str = Field(..., description="e.g. 'Alex M' — for UI display")
    status: StudentStatus
    prompt_count: int = 0
    last_message_preview: Optional[str] = Field(
        default=None,
        description="Truncated last message, e.g. 'Just give me the full insert function'",
    )
    top_topic: Optional[str] = Field(
        default=None,
        description="Most-asked-about topic, e.g. 'Insertion'",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Free-form note like 'Reached hint level 3, still stuck'",
    )
    similarity_match: Optional[str] = Field(
        default=None,
        description="If flagged for similarity, who they match",
    )
    similarity_pct: Optional[float] = None


class DashboardActivityBlock(BaseModel):
    """Tab 2 content — grouped student cards."""
    needs_help: list[DashboardActivityCard] = Field(default_factory=list)
    flagged: list[DashboardActivityCard] = Field(default_factory=list)
    on_track: list[DashboardActivityCard] = Field(default_factory=list)
    inactive: list[DashboardActivityCard] = Field(default_factory=list)


# ----- Tab 3: Graded Submissions --------------------------------------------

class DashboardGradesRow(BaseModel):
    """One row in the Tab 3 graded submissions table."""
    submission_id: str
    student_id: str
    display_name: str
    score: Optional[float] = Field(default=None, description="final_score or automated_score")
    status: Literal["graded", "flagged", "needs_review", "pending"]
    ai_feedback_summary: str = ""
    download_url: Optional[str] = None


class DashboardGradesBlock(BaseModel):
    """Tab 3 content."""
    submissions_total: int = 0
    auto_graded: int = 0
    needs_review: int = 0
    flagged: int = 0
    rows: list[DashboardGradesRow] = Field(default_factory=list)


# ----- Tab 4: Statistics ----------------------------------------------------

class GradeDistribution(BaseModel):
    """Histogram data for the grade distribution chart."""
    a_90_100: int = 0
    b_80_89: int = 0
    c_70_79: int = 0
    d_60_69: int = 0
    f_below_60: int = 0


class AIAssistanceStats(BaseModel):
    """Aggregated AI assistance metrics."""
    total_prompts: int = 0
    avg_per_student: float = 0.0
    progressive_hints_given: int = 0
    direct_answers_blocked: int = 0
    escalations_to_instructor: int = 0
    avg_completion_time_min: int = 0


class PerStudentRow(BaseModel):
    """A row in the per-student stats table (Tab 4)."""
    student_id: str
    display_name: str
    score: Optional[float] = None
    prompts: int = 0
    hints: int = 0
    status: StudentStatus


class DashboardStatsBlock(BaseModel):
    """Tab 4 content."""
    class_average: float = 0.0
    submissions: int = 0
    auto_graded: int = 0
    needs_review: int = 0
    flagged: int = 0
    grade_distribution: GradeDistribution = Field(default_factory=GradeDistribution)
    ai_assistance: AIAssistanceStats = Field(default_factory=AIAssistanceStats)
    per_student: list[PerStudentRow] = Field(default_factory=list)


# ----- Top-level dashboard response -----------------------------------------

class DashboardResponse(BaseModel):
    """
    GET /orchestrator/instructor/dashboard/{lab_id} — response.

    All four tabs in one payload. Frontend can render any tab without
    re-fetching. The Orchestrator may populate only the requested tab block
    if the `tab` query param is set, leaving others as None / default.
    """
    lab: DashboardLabInfo
    material: Optional[DashboardMaterialBlock] = None
    activity: Optional[DashboardActivityBlock] = None
    grades: Optional[DashboardGradesBlock] = None
    stats: Optional[DashboardStatsBlock] = None


# ============================================================================
# Instructor actions
# ============================================================================

class InstructorApprovalRequest(BaseModel):
    """POST /orchestrator/instructor/material/approve."""
    lab_id: str
    approved_by: str
    notes: str = ""
