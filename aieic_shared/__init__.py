"""
aieic-shared — Shared schemas, clients, and mocks for the AIEIC Lab Multi-Agent System.

This package is the canonical implementation of the contracts defined in
INTERFACE_CONTRACT.md. Every agent depends on it.

Quick start:
    from aieic_shared.schemas import StudentRef, ChatRequest, ChatResponse
    from aieic_shared.clients import ParticipantClient, LabCompanionClient

See README.md for full usage.
"""

__version__ = "0.1.0"

# Re-export the most commonly used schemas at top-level for convenience.
from aieic_shared.schemas import (
    # Core
    LabPhase,
    StudentStatus,
    Severity,
    StudentRef,
    LabRef,
    SessionRef,
    HealthResponse,
    ErrorResponse,
    # Companion
    ChatRequest,
    ChatResponse,
    ChatSource,
    EscalateRequest,
    # Participant
    LogInteractionRequest,
    LogInteractionResponse,
    StudentContextResponse,
    # Curriculum
    GenerateCurriculumRequest,
    CurriculumMaterial,
    QuizQuestion,
    Rubric,
    # Assessment
    AssessmentRequest,
    AssessmentResult,
    ManualReviewRequest,
    AnomalyFlag,
    AnomalyReport,
    FeedbackReport,
    SubmissionType,
    # Orchestrator
    StudentMessageRequest,
    StudentMessageResponse,
    DashboardResponse,
)

__all__ = [
    "__version__",
    # Core
    "LabPhase",
    "StudentStatus",
    "Severity",
    "StudentRef",
    "LabRef",
    "SessionRef",
    "HealthResponse",
    "ErrorResponse",
    # Companion
    "ChatRequest",
    "ChatResponse",
    "ChatSource",
    "EscalateRequest",
    # Participant
    "LogInteractionRequest",
    "LogInteractionResponse",
    "StudentContextResponse",
    # Curriculum
    "GenerateCurriculumRequest",
    "CurriculumMaterial",
    "QuizQuestion",
    "Rubric",
    # Assessment
    "AssessmentRequest",
    "AssessmentResult",
    "ManualReviewRequest",
    "AnomalyFlag",
    "AnomalyReport",
    "FeedbackReport",
    "SubmissionType",
    # Orchestrator
    "StudentMessageRequest",
    "StudentMessageResponse",
    "DashboardResponse",
]
