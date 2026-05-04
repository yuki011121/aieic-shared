# AIEIC Lab — Interface Contract v0.1

**Status:** Draft for team review
**Last updated:** April 2026

---

## Purpose

This document defines the **agreed-upon interfaces** between every agent in the AIEIC Lab Multi-Agent System. Once approved, all agents must conform to these contracts. Internal implementation details are up to each agent owner.

The goal: **enable parallel development**. Anyone can develop their agent against this contract using mocks, then swap in real agents during integration without code changes.

---

## Table of Contents

1. [Architecture Snapshot](#architecture-snapshot)
2. [Communication Conventions](#communication-conventions)
3. [Shared Schemas](#shared-schemas)
4. [Agent Contracts](#agent-contracts)
   - [Orchestrator](#orchestrator-agent)
   - [Lab Companion (x80_helper)](#lab-companion-agent)
   - [Participant Agent](#participant-agent)
   - [Curriculum Designer](#curriculum-designer-agent)
   - [Assessment Agent](#assessment-agent)
   - [Integrity Agent](#integrity-agent)
5. [Frontend → Orchestrator Mapping (Figma Dashboard)](#frontend--orchestrator-mapping)
6. [End-to-End Flows](#end-to-end-flows)
7. [Versioning & Change Process](#versioning--change-process)

---

## Architecture Snapshot

```
                    ┌─────────────────────────────┐
                    │  Frontend (React + Figma)   │
                    │  Student / Instructor UIs   │
                    └─────────────┬───────────────┘
                                  │ HTTPS
                                  ▼
                    ┌────────────────────────────────────┐
                    │            ORCHESTRATOR            │  ← Single entry point
                    │        FastAPI · port 8000         │     for the frontend.
                    │   Owns: routing, state,            │     Coordinates agents.
                    │          auth, aggregation         │
                    └─┬──────┬──────┬──────┬──────┬──────┘
              REST    │      │      │      │      │   REST
                      ▼      ▼      ▼      ▼      ▼
            ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌────────────┐ ┌────────────┐
            │   Lab    │ │Particip-│ │Curricu-  │ │ Assessment │ │ Integrity  │
            │Companion │ │  ant    │ │  lum     │ │   Agent    │ │   Agent    │
            │  :8002   │ │  :8001  │ │  :8003   │ │   :8004    │ │   :8005    │
            └──────────┘ └─────────┘ └──────────┘ └────────────┘ └────────────┘
                  │           │           │             │               │
                  ▼           ▼           ▼             ▼               ▼
            ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌────────────┐ ┌────────────┐
            │  Azure   │ │ Cosmos  │ │ Cosmos   │ │  Cosmos    │ │  Cosmos    │
            │  Search  │ │   DB    │ │   DB     │ │    DB      │ │    DB      │
            │  (RAG)   │ │interact-│ │curriculum│ │ submissions│ │ integrity  │
            │          │ │  ions   │ │          │ │            │ │ sessions   │
            └──────────┘ └─────────┘ └──────────┘ └────────────┘ └────────────┘
```

**Key principle:** The frontend talks **only** to the Orchestrator. Agents talk to each other **only** through the Orchestrator (or, where direct calls are explicitly listed in this doc, through documented direct endpoints).

---

## Communication Conventions

### Protocol
- **Default:** HTTP/REST + JSON
- **Real-time student chat:** WebSocket via Orchestrator (proxies to Lab Companion)
- **Async events (Phase 2+):** Azure Service Bus (NOT in scope for v0.1)

### Base URLs (development)
| Service | Local URL |
|---------|-----------|
| Orchestrator | `http://localhost:8000` |
| Participant Agent | `http://localhost:8001` |
| Lab Companion | `http://localhost:8002` |
| Curriculum Designer | `http://localhost:8003` |
| Assessment Agent | `http://localhost:8004` |
| Integrity Agent | `http://localhost:8005` |

### Required Endpoints (every agent)
Every agent **MUST** expose:
- `GET /health` → `{"status": "healthy", "agent": "<name>", "version": "0.1.0"}`
- `GET /` → `{"status": "ok", "agent": "<name>", "version": "<x.y.z>"}`

### Authentication
- **v0.1 (now):** No auth between agents (assume private network / Azure VNet).
- **v0.2 (production):** Service-to-service via Managed Identity; user-facing via OAuth2 + JWT.

### Error Format
All non-2xx responses use `ErrorResponse` — see [Shared Schemas](#shared-schemas).

### Identifiers
- `student_id`: short string, e.g., `"alex_m"` (matches the Figma mocks)
- `lab_id`: short string, e.g., `"lab4"`
- `course_id`: e.g., `"csc580"`
- `submission_id`, `interaction_id`, `session_id`: UUID4

---

## Shared Schemas

These are defined in the [`aieic-shared`](#) Python package and **must be imported** rather than redefined by any agent.

### `LabPhase` (enum)
```python
class LabPhase(str, Enum):
    PRE_LAB = "pre_lab"
    DURING_LAB = "during_lab"
    POST_LAB = "post_lab"
```

### `StudentStatus` (enum)
Used in the Student Activity dashboard.
```python
class StudentStatus(str, Enum):
    ON_TRACK = "on_track"
    NEEDS_HELP = "needs_help"
    FLAGGED = "flagged"
    INACTIVE = "inactive"
```

### `Severity` (enum)
```python
class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
```

### `HintLevel` (enum)
Shared by Lab Companion and Participant Agent.
```python
class HintLevel(int, Enum):
    NUDGE = 1         # subtle hint, don't give the answer
    EXPLAIN = 2       # explain the error
    POINT_TO_DOCS = 3 # direct reference to docs/spec
```

### Core Reference Models
```python
class StudentRef(BaseModel):
    student_id: str
    course_id: str = "csc580"

class LabRef(BaseModel):
    lab_id: str
    course_id: str = "csc580"

class SessionRef(BaseModel):
    session_id: str
    student_id: str
    lab_id: str
    started_at: datetime
```

### `ErrorResponse`
```python
class ErrorDetail(BaseModel):
    code: str        # e.g. "STUDENT_NOT_FOUND"
    message: str
    agent: str
    request_id: str  # UUID4

class ErrorResponse(BaseModel):
    error: ErrorDetail
```

### `HealthResponse`
```python
class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    agent: str
    version: str = "0.1.0"
```

See `aieic_shared/` for full type definitions.

---

## Agent Contracts

---

### Orchestrator Agent

**Role:** Single entry point for the frontend. Routes requests to backend agents, aggregates responses, manages session state, enforces policies, and handles human-in-the-loop escalations.

#### Endpoints — Student-facing

##### `POST /orchestrator/student/message`
Student sends a message to the Lab Companion. Orchestrator coordinates:
1. Get/refresh student context from Participant Agent (learning behavior profile)
2. Check with Integrity Agent — if blocked, return refusal immediately
3. Forward to Lab Companion with context + guidance_level injected
4. Log interaction back to Participant Agent (fire-and-forget)
5. Return AI reply

**Request:**
```json
{
  "student_id": "alex_m",
  "session_id": "uuid-or-null-for-new",
  "lab_id": "lab4",
  "message": "How do I insert at position 3?"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "reply": "...",
  "sources": [{"title": "lab4_spec.pdf", "uid": "..."}],
  "hint_level": 1,
  "tokens_used": 142
}
```

**Note:** If `session_id` is null in the request, Orchestrator creates a new session. The `session_id` is always returned in the response and must be stored by the client for subsequent turns.

##### `POST /orchestrator/student/submit`
Student submits final lab work. Orchestrator forwards to Assessment Agent.

**Request (multipart/form-data):**
- `student_id`: string
- `assignment_id`: string  (= lab_id)
- `code_file`: file (optional)
- `report_file`: file (optional)

**Response:** Mirrors `AssessmentResult` from Assessment Agent (see [Assessment Agent](#assessment-agent)).

#### Endpoints — Instructor-facing

##### `GET /orchestrator/instructor/dashboard/{lab_id}`
Returns the unified dashboard payload for the Figma "Instructor Panel" screen.

**Query params:** `tab` (optional) — one of `material | activity | grades | stats`. If omitted, returns all tabs.

**Response (full):**
```json
{
  "lab": {
    "lab_id": "lab4",
    "title": "Linked Lists Quiz",
    "phase": "during_lab",
    "students_enrolled": 35
  },
  "material": {
    "spec_file": "lab4_specification.pdf",
    "quiz": [...],
    "approval_status": "pending"
  },
  "activity": {
    "needs_help": [...],
    "flagged": [...],
    "on_track": [...]
  },
  "grades": {
    "submissions_total": 35,
    "auto_graded": 30,
    "needs_review": 3,
    "flagged": 2,
    "rows": [...]
  },
  "stats": {
    "class_average": 78.4,
    "grade_distribution": {...},
    "ai_assistance": {...},
    "per_student": [...]
  }
}
```

**Inside, the Orchestrator calls (in parallel where possible):**
- `Curriculum Designer GET /curriculum/{lab_id}` → for `material`
- `Participant Agent GET /participant/context/{student_id}` for each enrolled student → for `activity`
- `Assessment Agent GET /results?assignment_id={lab_id}` → for `grades`
- `Assessment Agent GET /review-queue` → for flagged items
- Aggregates everything into `stats`

##### `POST /orchestrator/instructor/material/approve`
**Request:**
```json
{
  "lab_id": "lab4",
  "approved_by": "instructor_id",
  "notes": "Looks good"
}
```
Orchestrator calls `Curriculum Designer POST /curriculum/{lab_id}/approve`.

##### `POST /orchestrator/instructor/material/request-changes`
**Request:**
```json
{
  "lab_id": "lab4",
  "feedback": "Make Q3 harder",
  "requested_by": "instructor_id"
}
```

##### `POST /orchestrator/instructor/review/{submission_id}/complete`
Forwards to Assessment Agent's `POST /review-queue/{submission_id}/complete`.

##### `POST /orchestrator/instructor/material/upload`
Upload lab material files (PDF, etc.).

**Request (multipart/form-data):** `lab_id`, `instructor_id`, `files[]`

**Response:** `{"lab_id": "lab4", "files_uploaded": ["lab4_specification.pdf"]}`

##### `POST /orchestrator/instructor/material/instructions`
Upload custom system-prompt instructions for the Lab Companion for a specific lab.

**Request (multipart/form-data):** `lab_id`, `instructor_id`, `instructions_file`

**Response:** `{"lab_id": "lab4", "status": "ok"}`

##### `POST /orchestrator/instructor/material/generate-quiz`
Generate quiz from learning objectives. Calls `POST /curriculum/generate` on Curriculum Designer.

**Request:**
```json
{
  "lab_id": "lab4",
  "course_id": "csc580",
  "learning_objectives": ["..."],
  "difficulty": "intermediate",
  "instructor_id": "kurfess"
}
```

**Response:** Same shape as Curriculum Designer `POST /curriculum/generate` response.

##### `POST /orchestrator/instructor/material/generate-tasks`
Generate lab task descriptions. Same request/response shape as `generate-quiz`.

##### `POST /orchestrator/instructor/material/check-typos`
**Query params:** `lab_id`. Forwards to `POST /curriculum/{lab_id}/check-typos`. Response mirrors Curriculum Designer's response.

##### `POST /orchestrator/instructor/material/refine`
Streaming. Refine lab materials based on instructor feedback. Calls Curriculum Designer.

**Request:**
```json
{"lab_id": "lab4", "instructor_id": "kurfess", "message": "Make Q3 harder"}
```

**Response:** SSE stream. Final event contains the updated material (same shape as `GET /curriculum/{lab_id}`).

##### `POST /orchestrator/instructor/grade-batch`
**Query params:** `lab_id`. Triggers Assessment Agent to grade all pending submissions.

**Response:** `{"lab_id": "lab4", "submissions_queued": 35}`

##### `GET /orchestrator/instructor/submission/{submission_id}`
Single submission detail. Forwards to `GET /results/{submission_id}` on Assessment Agent.

##### `GET /orchestrator/instructor/submission/{submission_id}/download`
Download raw submission files as an attachment.

##### `GET /orchestrator/instructor/grades/csv`
**Query params:** `lab_id`. Export all grades for a lab as a CSV file.

#### Internal State

Orchestrator maintains session state in Cosmos DB (container: `orchestrator-state`, partition key: `/session_id`):

```python
class OrchestratorSessionState(BaseModel):
    session_id: str
    student_id: str
    lab_id: str
    phase: LabPhase
    conversation_turn_count: int = 0
    integrity_flags: list[str] = []
    needs_instructor_review: bool = False
    last_updated: datetime
```

---

### Lab Companion Agent

**Role:** Real-time student tutor. Uses RAG over course materials. Provides progressive hints rather than direct answers.

#### Required Refactor
The current Chainlit app (`x80_helper/app.py`) handles UI, auth, RAG, and LLM calls in one process. To integrate, it must expose a stateless HTTP API. **Two options** — to be decided by the Lab Companion owner:

- **Option A (recommended):** Keep Chainlit for direct student access. Add a parallel FastAPI app exposing `/companion/*` endpoints that share the underlying RAG + LLM logic.
- **Option B:** Replace Chainlit entirely with FastAPI; build a new student chat UI in the unified frontend.

This contract specifies what Option A or B must implement.

#### Endpoints

##### `POST /companion/chat`
Stateless chat — caller must supply full conversation context.

**Request:**
```json
{
  "student_id": "alex_m",
  "session_id": "uuid",
  "message": "How do I insert at position 3?",
  "conversation_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "student_context_summary": "Student has asked 12 questions, primarily debugging-type, average hint level 1.5",
  "lab_id": "lab4"
}
```

**Response:**
```json
{
  "reply": "Try walking the list with two pointers...",
  "sources": [
    {"title": "lab4_spec.pdf", "uid": "abc_chunk_03", "snippet": "..."}
  ],
  "hint_level": 2,
  "tokens_used": 187,
  "should_escalate": false
}
```

**Notes:**
- `conversation_history` is supplied by the Orchestrator, not stored by Lab Companion. This makes the service stateless and horizontally scalable.
- `student_context_summary` is the `summary` field from Participant Agent's `/participant/context/{student_id}`.
- `hint_level`: 1 = subtle nudge, 2 = explain error, 3 = point to docs (matches Participant Agent's classification).
- `should_escalate: true` when the question is out of scope or the student appears stuck after multiple hints.

##### `POST /companion/escalate`
Triggered when Lab Companion cannot answer; logs an escalation event.

**Request:**
```json
{
  "student_id": "alex_m",
  "session_id": "uuid",
  "reason": "out_of_scope" | "repeated_failure" | "policy_violation",
  "context": "..."
}
```

##### Health
- `GET /health`

---

### Participant Agent

**Role:** Tracks every student interaction. Provides aggregated context so the Lab Companion can personalize responses.

> **Scope boundary:** This agent handles *learning behavior analytics*  — understanding what a student is struggling with and how they learn across sessions. It's different from the **Integrity Agent**. The two agents use separate classification schemes for different purposes: this agent classifies for pedagogical personalization; the Integrity Agent classifies for policy compliance.

#### Endpoints

##### `POST /participant/log`
Log a single student interaction. Called by Orchestrator after every student message.

**Request:**
```json
{
  "student_id": "alex_m",
  "session_id": "uuid",
  "message": "How do I insert at position 3?",
  "response_time_ms": 1234
}
```

**Response:**
```json
{
  "status": "ok",
  "interaction_id": "uuid"
}
```

**Side effects:**
- Classifies the message for **learning analytics** via Azure OpenAI: question_type (debugging / concept / setup), hint_level, difficulty. This is distinct from the Integrity Agent's policy classification, which determines whether a question is permitted and at what guidance level.
- Persists to Cosmos DB container `interactions` (partition key: `/student_id`)

##### `GET /participant/context/{student_id}`
Returns the student's aggregated learning profile. Called by Orchestrator at session start and periodically refreshed.

**Response:**
```json
{
  "total_questions": 12,
  "question_type_distribution": {"debugging": 7, "concept": 3, "setup": 2},
  "avg_hint_level": 1.5,
  "sessions_count": 3,
  "avg_questions_per_session": 4.0,
  "session_help_frequency": {"sess1": 5, "sess2": 4, "sess3": 3},
  "summary": "Student has asked 12 questions across 3 sessions. Primary focus: debugging. Moderate assistance level."
}
```

##### Planned (v0.2) endpoints — not yet implemented
- `GET /participant/cohort/{lab_id}` → returns activity summary for ALL students in a lab. **Currently the Orchestrator must call `/context/{student_id}` per student**, which is N requests. Adding this batch endpoint is on the roadmap.
- `GET /participant/student/{student_id}/status` → simple `StudentStatus` (on_track / needs_help / flagged) classification.

##### Health
- `GET /health`

---

### Curriculum Designer Agent

**Role:** Generates lab materials (specs, quizzes, rubrics) from learning objectives. Supports instructor approval workflow.

#### Endpoints

##### `POST /curriculum/generate`
Generate a new lab from teaching objectives.

**Request:**
```json
{
  "course_id": "csc580",
  "lab_id": "lab4",
  "title": "Linked Lists",
  "learning_objectives": [
    "Implement singly linked list operations",
    "Understand pointer semantics",
    "Analyze time complexity"
  ],
  "difficulty": "intermediate",
  "estimated_duration_min": 90,
  "instructor_id": "kurfess"
}
```

**Response:**
```json
{
  "lab_id": "lab4",
  "title": "Linked Lists Quiz",
  "spec_markdown": "# Lab 4 — Linked Lists\n...",
  "quiz": [
    {
      "id": "q1",
      "question": "What is the time complexity of inserting a node at the head of a singly linked list?",
      "type": "short_answer",
      "expected_answer": "O(1)",
      "rubric_points": 10
    }
  ],
  "rubric": {
    "code_weight": 0.6,
    "report_weight": 0.3,
    "manual_weight": 0.1,
    "criteria": [...]
  },
  "approval_status": "pending",
  "generated_at": "2026-04-29T..."
}
```

##### `GET /curriculum/{lab_id}`
Retrieve current lab materials.

**Response:** Same shape as `POST /curriculum/generate` response.

##### `POST /curriculum/{lab_id}/approve`
Mark lab materials as approved. Called by Orchestrator after instructor clicks "Approve" in the dashboard.

**Request:**
```json
{
  "approved_by": "kurfess",
  "notes": ""
}
```

##### `POST /curriculum/{lab_id}/request-changes`
**Request:**
```json
{
  "feedback": "Make Q3 harder",
  "requested_by": "kurfess"
}
```
Triggers regeneration. Status moves back to `pending`.

##### `POST /curriculum/{lab_id}/check-typos`
AI action button in Figma — checks materials for errors.

**Response:**
```json
{
  "issues_found": 2,
  "issues": [
    {"location": "Q3", "type": "typo", "suggestion": "..."}
  ]
}
```

##### Health
- `GET /health`

---

### Assessment Agent

**Role:** Automated grading: code testing (60%) + report evaluation (30%) + manual review (10%). Anomaly detection for plagiarism / over-reliance on AI.

#### Endpoints

##### `POST /submit-json`
Submit a student's work for grading via JSON body.

**Request:**
```json
{
  "student_id": "alex_m",
  "assignment_id": "lab4",
  "code": "def insert(...): ...",
  "report": "# My Report\n...",
  "submission_type": "full"
}
```

**Response:** `AssessmentResult` (see `assessment_agent.models.AssessmentResult`):
```json
{
  "submission_id": "uuid8",
  "student_id": "alex_m",
  "assignment_id": "lab4",
  "submission_type": "full",
  "code_grade": {
    "test_results": [...],
    "tests_passed": 8,
    "tests_total": 10,
    "raw_score": 80.0,
    "weighted_score": 48.0
  },
  "report_evaluation": {...},
  "anomaly_report": {
    "flags": [],
    "overall_risk": "low"
  },
  "feedback": {
    "summary": "Well-structured logic. Minor edge case missed.",
    "strengths": [...],
    "improvements": [...]
  },
  "automated_score": 92.0,
  "final_score": null,
  "status": "completed"
}
```

##### `POST /submit`
Same as `/submit-json` but uses multipart/form-data with file uploads. Used by the Orchestrator to forward student submissions.

##### `GET /results`
List results, optionally filtered.

**Query params:** `student_id`, `assignment_id` (optional)

**Response:** array of `AssessmentResult`.

##### `GET /results/{submission_id}`
Single result detail.

##### `GET /assignments`
List available assignments (those with test cases configured).

##### `GET /assignments/{assignment_id}/test-cases`
Get test case metadata for an assignment.

##### `GET /assignments/{assignment_id}/rubric`
Get the parsed rubric.

##### `GET /review-queue`
Get the manual review queue.

**Query params:** `status` (optional) — `pending | in_review | completed`

**Response:** array of `ManualReviewRequest`.

##### `POST /review-queue/{submission_id}/complete`
Complete a manual review.

**Request (form-data):**
- `instructor_score`: float (0-10)
- `notes`: string

##### `GET /anomalies`
List flagged anomaly reports.

**Query params:** `reviewed` (optional, bool)

##### Health
- `GET /health`

---

### Integrity Agent

**Role:** Real-time academic integrity enforcement. Classifies every student question before the Lab Companion responds, determines the permitted guidance level, and logs violations. Escalates to the instructor when violation thresholds are exceeded.

**Key distinctions from Participant Agent:**

| | Integrity Agent | Participant Agent |
|---|---|---|
| Called | **Synchronously** — blocks response | **Asynchronously** — fire-and-forget after response |
| Classification purpose | Policy compliance (is this question permitted?) | Learning analytics (what kind of help does the student need?) |
| Classification taxonomy | conceptual / clarification / procedural / answer_farming / direct_solution_request | debugging / concept / setup |
| Output used for | Gating Lab Companion response | Personalizing Lab Companion response |

#### Endpoints

##### `POST /integrity/check`
Synchronous policy gate. Called by the Orchestrator **after** loading student context and **before** forwarding the message to the Lab Companion.

**Request:**
```json
{
  "student_id": "alex_m",
  "session_id": "uuid",
  "message": "What is the answer to question 3?"
}
```

**Response:**
```json
{
  "blocked": false,
  "guidance_level": "FULL",
  "question_type": "conceptual",
  "violation": false,
  "warning_message": null
}
```

**`guidance_level` values:**

| Value | Meaning |
|---|---|
| `FULL` | Unrestricted guidance — normal Lab Companion response |
| `MODERATE` | Hints only — Lab Companion should not give direct answers |
| `MINIMAL` | Confirm approach only — no implementation details |
| `REJECTED` | Blocked — Orchestrator returns refusal, Lab Companion not called |

**Orchestrator behavior on response:**
- `blocked: true` → skip Lab Companion, return `"You've reached the AI assistance limit for this period."`
- Otherwise → pass `guidance_level` to Lab Companion via `student_context_summary`

**Violation escalation thresholds (enforced internally by Integrity Agent):**
- Q13: warning message returned in `warning_message`
- Q16+: `blocked: true` (hard block)
- 3+ violations in a session: `escalated: true` in session report

##### `GET /integrity/report/{session_id}`
Returns the full integrity report for a session. Called by the Orchestrator when populating the instructor dashboard's flagged entries.

**Response:**
```json
{
  "session_id": "uuid",
  "student_id": "alex_m",
  "total_questions": 18,
  "violations": [
    {
      "question_number": 13,
      "question_type": "direct_solution_request",
      "message": "...",
      "guidance_level": "REJECTED",
      "timestamp": "2026-04-30T..."
    }
  ],
  "violation_count": 3,
  "escalated": true,
  "final_status": "flagged"
}
```

##### Health
- `GET /health`

> **Note:** Port `:8005` and exact request/response schema must be confirmed with the Integrity Agent owner before integration. The Orchestrator's `policy_check` node is already scaffolded to call this endpoint.

---

## Frontend → Orchestrator Mapping

This maps every interaction in the Figma "AIEIC Instructor Panel — Unified Dashboard v2" to its Orchestrator endpoint. Frontend developers should reference this when wiring up the React app.

> **Note:** Endpoints use `lab4` as the example `lab_id` throughout. In the React app, this is a dynamic route parameter.

### Sidebar (always visible)

| UI element | Orchestrator endpoint |
|---|---|
| `Lab4_specification.pdf` (uploaded indicator) | `GET /orchestrator/instructor/dashboard/lab4` → `material.spec_file` |
| `Upload Material` button | `POST /orchestrator/instructor/material/upload` (multipart) |
| `Upload Agent Instructions` button | `POST /orchestrator/instructor/material/instructions` |
| `Check for Typos & Errors` AI action | `POST /orchestrator/instructor/material/check-typos?lab_id=lab4` |
| `Generate Lab Tasks` AI action | `POST /orchestrator/instructor/material/generate-tasks` |
| `Generate Quiz` AI action | `POST /orchestrator/instructor/material/generate-quiz` |
| `Grade Submissions` (primary CTA) | `POST /orchestrator/instructor/grade-batch?lab_id=lab4` |

### Tab 1 — Material Preview
| UI element | Endpoint / Field |
|---|---|
| Lab title, question count, status | `GET /orchestrator/instructor/dashboard/lab4` → `material.quiz` |
| Q1–Q5 list | `material.quiz[]` |
| `Approve` button (green) | `POST /orchestrator/instructor/material/approve` |
| `Request Changes` button | `POST /orchestrator/instructor/material/request-changes` |
| Refinement chat input ("Make Q3 harder…") | `POST /orchestrator/instructor/material/refine` (streams) |
| Pagination 1/4 | Client-side; backend returns full quiz array |

### Tab 2 — Student Activity
| UI element | Endpoint / Field |
|---|---|
| `35 students enrolled · Lab in session` header | `GET /orchestrator/instructor/dashboard/lab4` → `lab.students_enrolled`, `lab.phase` |
| Needs Help (red) cards: Carlos R, Ethan L | `activity.needs_help[]` |
| Flagged (yellow) card: Nina Q | `activity.flagged[]` |
| On Track (green) cards: Alex M, Bella K, etc. | `activity.on_track[]` |
| Card fields: prompts, last message, top topic | Each from `participant/context/{id}` |

**Note:** This tab needs near-real-time data. v0.1 polls every 10s; v0.2 will use Server-Sent Events from Orchestrator.

### Tab 3 — Graded Submissions
| UI element | Endpoint / Field |
|---|---|
| `35 submissions · 30 auto-graded · 3 pending` | `grades.submissions_total`, `auto_graded`, `needs_review` |
| Table rows | `grades.rows[]` (one per submission) |
| `Score` column | `row.automated_score` (final_score if reviewed) |
| `Status` column | `row.status` ("Graded" / "Flagged" / "Needs Review") |
| `AI Feedback` column | `row.feedback.summary` |
| `Download` link | `GET /orchestrator/instructor/submission/{id}/download` |
| `Download All (CSV)` | `GET /orchestrator/instructor/grades/csv?lab_id=lab4` |

### Tab 4 — Statistics
| UI element | Endpoint / Field |
|---|---|
| Class Average · Submissions · Auto-graded · Needs Review · Flagged | `stats.*` (top metric cards) |
| Grade Distribution bar chart | `stats.grade_distribution` |
| AI Assistance metrics | `stats.ai_assistance` |
| Per-Student Breakdown table | `stats.per_student[]` |

---

## End-to-End Flows

### Flow 1: Pre-Lab — Instructor approves AI-generated quiz

```
1. Instructor clicks "Generate Quiz" in Figma sidebar
   Frontend → POST /orchestrator/instructor/material/generate-quiz
              { lab_id: "lab4" }
   
2. Orchestrator → POST /curriculum/generate
                  { course_id, lab_id, learning_objectives, ... }
   Curriculum Designer generates quiz, returns it.
   
3. Orchestrator returns quiz JSON to frontend.
   Frontend renders Material Preview tab.

4. Instructor reviews, clicks "Approve"
   Frontend → POST /orchestrator/instructor/material/approve
              { lab_id: "lab4", approved_by: "kurfess" }
   
5. Orchestrator → POST /curriculum/lab4/approve
   Curriculum Designer marks status = "approved".
   
6. Orchestrator returns success.
```

### Flow 2: During-Lab — Student asks a question

```
1. Student types message in chat.
   Frontend → POST /orchestrator/student/message
              { student_id, session_id, lab_id, message }

2. Orchestrator — sequential, in order:
   a. GET /participant/context/{student_id}
      → returns summary, hint_level pattern (learning analytics)

   b. POST /integrity/check
      { student_id, session_id, message }
      → returns blocked, guidance_level, question_type
      → if blocked: skip step c, return refusal to student

   c. POST /companion/chat  (skipped if step b returned blocked: true)
      { student_id, session_id, message,
        conversation_history (from session state),
        student_context_summary (from step 2a, with guidance_level from step 2b appended),
        lab_id }
      → returns reply, sources, hint_level

3. Orchestrator (fire-and-forget):
   POST /participant/log
   { student_id, session_id, message }

4. Orchestrator updates session state (turn count, etc.)
5. Returns reply to frontend.
```

### Flow 3: Post-Lab — Submission and grading

```
1. Student submits final code + report.
   Frontend → POST /orchestrator/student/submit (multipart)

2. Orchestrator forwards to:
   POST /submit (Assessment Agent, multipart)
   → returns AssessmentResult with automated_score

3. If anomaly_report.overall_risk == "high":
   - Submission auto-routed to instructor review queue
     (Assessment Agent does this internally)

4. Orchestrator returns AssessmentResult to frontend.

5. Instructor opens Tab 3 (Graded Submissions):
   Frontend → GET /orchestrator/instructor/dashboard/lab4?tab=grades
   Orchestrator → GET /results?assignment_id=lab4 (Assessment)
                → GET /review-queue?status=pending (Assessment)
   Aggregates and returns.

6. Instructor clicks Carlos R (flagged):
   Frontend → GET /orchestrator/instructor/submission/{id}
   Orchestrator → GET /results/{submission_id}

7. Instructor completes manual review:
   Frontend → POST /orchestrator/instructor/review/{id}/complete
              { instructor_score: 6.5, notes: "..." }
   Orchestrator → POST /review-queue/{id}/complete (Assessment)
```

---

## Versioning & Change Process

### Versioning
This document is versioned. Breaking changes bump the **major** version (v0.1 → v1.0). Additive changes (new optional fields, new endpoints) bump **minor** (v0.1 → v0.2).

### When does a change require updating this doc + `aieic-shared`?

**Yes — coordinate and update shared when:**
- Adding or removing a **required** field on any request or response
- Changing a field's type or name
- Adding or removing an endpoint
- Changing an enum value (e.g. an `approval_status` string)
- Changing HTTP method or URL path

**No — do NOT update shared for:**
- Changes to an agent's **internal** data model (your own DB schema, extra computed fields, internal state)
- Adding an **optional** field to a response — callers ignore unknown fields by default; just add it
- Any change that stays entirely within one agent's repo and doesn't affect what the Orchestrator or other agents receive
- Refactoring, renaming internal variables, changing how you store data


### Do individual agents need to import from `aieic-shared`?

No — not for internal models. Each agent owns its internal representation and can evolve it freely. The only obligation is that the agent's **HTTP responses** match the shapes defined in this document.

`aieic-shared` is primarily the **Orchestrator's dependency**. Individual agents may optionally import core enums (`LabPhase`, `StudentStatus`, etc.) to avoid redefining them, but are never required to use the response schema classes internally.

### Process for Changes
Any agent owner who needs to change a contract:

1. **Open an issue / PR** against this doc with the proposed change. Tag affected agent owners.
2. **Discuss** in the next sync (or async on Slack/Discord).
3. **Approve** by majority of affected owners.
4. **Update both** this doc AND the `aieic-shared` package in the same PR.
5. **Bump version**.
6. **Notify**: post in team channel.


---

## Implementation Status (April 2026)

| Agent | Owner | Status | Port | Action Items |
|---|---|---|---|---|
| Orchestrator | TBD | 🟢 Implemented | 8000 | Build skeleton this week |
| Lab Companion | TBD | 🟡 Needs HTTP API | 8002 | Refactor: add FastAPI layer |
| Participant Agent | TBD | 🟢 Implemented | 8001 | Add `/cohort` batch endpoint (v0.2) |
| Curriculum Designer | TBD | 🟢 Implemented | 8003 | Build after Orchestrator skeleton |
| Assessment Agent | TBD | 🟢 Implemented | 8004 | No blocking changes |
| Integrity Agent | TBD (Parastou) | 🟢 Implemented | 8005* | Confirm port + endpoint schema with owner; wire into Orchestrator `policy_check` node |
| Frontend (React) | TBD | 🟡 Figma only | — | Wire to `/orchestrator/*` once skeleton up |

### Immediate Blockers
1. **Lab Companion HTTP API** — without this, the Orchestrator cannot route student messages. **This is the #1 blocker for system integration.** 

---

## Appendix A: Mock Servers for Parallel Development

While the real agents are being built, the Orchestrator developer can run **mock servers** that conform to this contract. The `aieic-shared` package includes mock implementations:

```python
from aieic_shared.mocks import (
    mock_lab_companion_app,
    mock_curriculum_designer_app,
    mock_participant_agent_app,
    mock_assessment_agent_app,
)
# All return FastAPI apps. Run on the standard ports.
```

This lets the Orchestrator be developed end-to-end without waiting for real implementations.

