"""
Assessment Agent schemas.

These mirror the schemas in assessment-agent/assessment_agent/models.py.
The Assessment Agent is already implemented; these schemas reflect what it
actually returns. Do NOT modify them without coordinating with the Assessment
Agent owner.

Owner: [Assessment Agent team]
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class SubmissionType(str, Enum):
    CODE_ONLY = "code_only"
    REPORT_ONLY = "report_only"
    FULL = "full"


# ============================================================================
# Code grading
# ============================================================================

class TestCase(BaseModel):
    """A single test case used to grade code."""
    name: str
    input: str
    expected_output: str
    points: float = 10.0
    timeout_seconds: float = 5.0
    description: str = ""


class TestCaseResult(BaseModel):
    """Result of running one test case against a submission."""
    name: str
    passed: bool
    expected_output: str
    actual_output: str = ""
    error: str = ""
    execution_time_ms: float = 0.0
    points_earned: float = 0.0
    points_possible: float = 10.0


class CodeGradeResult(BaseModel):
    """Aggregated code grading result (60% of automated score)."""
    test_results: list[TestCaseResult] = Field(default_factory=list)
    tests_passed: int = 0
    tests_total: int = 0
    raw_score: float = Field(default=0.0, description="0-100 before weighting")
    weighted_score: float = Field(default=0.0, description="raw_score * 0.60")
    compilation_error: str = ""
    runtime_errors: list[str] = Field(default_factory=list)


# ============================================================================
# Report evaluation
# ============================================================================

class ReportCriterion(BaseModel):
    """One line item in the report rubric evaluation."""
    name: str
    score: float = Field(default=0.0, description="0-10")
    max_score: float = 10.0
    justification: str = ""


class ReportEvaluation(BaseModel):
    """Aggregated report evaluation (30% of automated score)."""
    criteria: list[ReportCriterion] = Field(default_factory=list)
    raw_score: float = Field(default=0.0, description="0-100")
    weighted_score: float = Field(default=0.0, description="raw_score * 0.30")
    llm_reasoning: str = ""


# ============================================================================
# Anomaly / integrity
# ============================================================================

class AnomalyFlag(BaseModel):
    """A single integrity concern raised during grading."""
    flag_type: str = Field(
        ...,
        description="'style_change' | 'plagiarism' | 'ai_generated' | 'complexity_mismatch'",
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str = ""
    severity: str = Field(default="low", description="low | medium | high")


class AnomalyReport(BaseModel):
    """All anomaly flags for a single submission."""
    flags: list[AnomalyFlag] = Field(default_factory=list)
    overall_risk: str = Field(default="low", description="low | medium | high")
    recommendation: str = ""


# ============================================================================
# Feedback
# ============================================================================

class FeedbackReport(BaseModel):
    """Personalized feedback returned to the student."""
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    detailed_feedback: str = Field(default="", description="Full markdown feedback")


# ============================================================================
# Manual review queue (instructor co-pilot interface)
# ============================================================================

class ManualReviewRequest(BaseModel):
    """An item in the manual review queue."""
    submission_id: str
    student_id: str
    assignment_id: str
    automated_score: float
    anomaly_flags: list[AnomalyFlag] = Field(default_factory=list)
    priority: str = Field(default="normal", description="low | normal | high | urgent")
    status: str = Field(default="pending", description="pending | in_review | completed")
    instructor_score: Optional[float] = None
    instructor_notes: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# Top-level submission / result
# ============================================================================

class AssessmentRequest(BaseModel):
    """Body for POST /submit-json."""
    student_id: str
    assignment_id: str
    code: Optional[str] = None
    report: Optional[str] = None
    submission_type: Optional[SubmissionType] = None


class AssessmentResult(BaseModel):
    """The full result of grading one submission."""
    submission_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    student_id: str
    assignment_id: str
    submission_type: SubmissionType
    code_grade: Optional[CodeGradeResult] = None
    report_evaluation: Optional[ReportEvaluation] = None
    anomaly_report: Optional[AnomalyReport] = None
    feedback: Optional[FeedbackReport] = None
    manual_review: Optional[ManualReviewRequest] = None
    automated_score: float = Field(
        default=0.0,
        description="Combined weighted score (code 60% + report 30%)",
    )
    final_score: Optional[float] = Field(
        default=None,
        description="After instructor review adds the 10% manual portion",
    )
    status: str = "completed"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    agent_reasoning: str = Field(
        default="",
        description="The Assessment Agent orchestrator's chain-of-thought",
    )
