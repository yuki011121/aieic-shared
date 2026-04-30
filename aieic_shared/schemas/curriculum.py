"""
Curriculum Designer schemas.

The Curriculum Designer generates lab materials (specs, quizzes, rubrics) from
learning objectives and supports the instructor approval workflow.

Owner: Yayun (not yet implemented — contract defined here for forward planning)
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Quiz / Rubric building blocks
# ============================================================================

class QuizQuestionType(str, Enum):
    SHORT_ANSWER = "short_answer"
    MULTIPLE_CHOICE = "multiple_choice"
    CODE = "code"
    DIAGRAM = "diagram"


class QuizQuestion(BaseModel):
    """A single question in an AI-generated quiz."""
    id: str = Field(..., description="Question id, e.g. 'q1'")
    question: str
    type: QuizQuestionType = QuizQuestionType.SHORT_ANSWER
    expected_answer: Optional[str] = Field(
        default=None,
        description="Used by Assessment Agent for auto-grading",
    )
    rubric_points: float = Field(default=10.0)
    choices: Optional[list[str]] = Field(
        default=None,
        description="Only present for multiple_choice questions",
    )


class RubricCriterion(BaseModel):
    """A single line item in a grading rubric."""
    name: str
    weight: float = Field(..., description="Fraction of section's total")
    description: str = ""


class Rubric(BaseModel):
    """The grading rubric attached to a lab."""
    code_weight: float = Field(default=0.6, ge=0, le=1)
    report_weight: float = Field(default=0.3, ge=0, le=1)
    manual_weight: float = Field(default=0.1, ge=0, le=1)
    criteria: list[RubricCriterion] = Field(default_factory=list)
    guidance: str = Field(
        default="",
        description="Free-form guidance for the Assessment Agent's grader",
    )


# ============================================================================
# POST /curriculum/generate
# ============================================================================

class GenerateCurriculumRequest(BaseModel):
    """Body for POST /curriculum/generate."""
    course_id: str = "csc580"
    lab_id: str
    title: str
    learning_objectives: list[str] = Field(default_factory=list)
    difficulty: Literal["basic", "intermediate", "challenge"] = "intermediate"
    estimated_duration_min: int = Field(default=60, ge=10, le=300)
    instructor_id: str = Field(..., description="Who's requesting the generation")


# ============================================================================
# Lab material — returned by /curriculum/generate AND /curriculum/{lab_id}
# ============================================================================

class CurriculumMaterial(BaseModel):
    """The complete lab package."""
    lab_id: str
    course_id: str = "csc580"
    title: str
    spec_markdown: str = Field(..., description="Full lab spec in Markdown")
    quiz: list[QuizQuestion] = Field(default_factory=list)
    rubric: Rubric = Field(default_factory=Rubric)
    approval_status: Literal["pending", "approved", "changes_requested"] = "pending"
    approved_by: Optional[str] = None
    generated_at: datetime
    last_updated: datetime


# ============================================================================
# Approval workflow
# ============================================================================

class ApprovalRequest(BaseModel):
    """POST /curriculum/{lab_id}/approve."""
    approved_by: str
    notes: str = ""


class RequestChangesRequest(BaseModel):
    """POST /curriculum/{lab_id}/request-changes."""
    feedback: str = Field(..., min_length=1)
    requested_by: str


# ============================================================================
# Typo / error checking
# ============================================================================

class TypoIssue(BaseModel):
    """A single issue found in lab materials."""
    location: str = Field(..., description="Where in the doc, e.g. 'Q3' or 'spec.intro'")
    type: Literal["typo", "grammar", "ambiguity", "factual_error", "other"]
    suggestion: str
    original_text: Optional[str] = None


class TypoCheckResponse(BaseModel):
    """Response from POST /curriculum/{lab_id}/check-typos."""
    issues_found: int = 0
    issues: list[TypoIssue] = Field(default_factory=list)
