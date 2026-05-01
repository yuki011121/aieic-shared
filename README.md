# aieic-shared

Shared schemas, HTTP clients, and mock servers for the AIEIC Lab Multi-Agent System.

## What this package is (and isn't)

**This package is the Orchestrator's SDK and the team's integration toolkit.**

It contains three things:
- **Wire-format schemas** — the request/response shapes that flow *between* agents over HTTP. These define what the Orchestrator sends and expects to receive.
- **Typed HTTP clients** — used by the Orchestrator to call each agent. Validates requests/responses at every call site.
- **Mock servers** — stand-in FastAPI apps that let any developer build against the full system before every agent is ready.

**What it is not:** a library that individual agents must use internally. Each agent owns its own internal data models and can evolve them freely. The only requirement is that an agent's *API responses* conform to the shapes defined here.

---

## Who should import what

| Role | What to import |
|---|---|
| **Orchestrator** | Everything — schemas, clients, orchestrator schemas |
| **Individual agent (e.g. Curriculum Designer)** | Only `core.py` enums if useful (`LabPhase`, `StudentStatus`, etc.). Not required to import response schemas internally. |
| **Test / integration code** | Schemas (for assertions) and mock servers |

The key rule: **if only one agent uses a type, it belongs in that agent's repo.** If a type must be agreed upon by both sides of an HTTP call, it belongs here.

---

## When to update this package

**You must update shared when:**
- Adding or removing a required field from an API request or response
- Changing a field's type or name
- Adding or removing an endpoint (update the client + mock too)
- Changing an enum value (this is a breaking change — see versioning below)

**You do NOT need to update shared when:**
- Adding fields to your agent's internal model
- Changing your agent's internal logic, DB schema, or implementation details
- Adding an optional field to your API response (callers will just ignore it)
- Any change that stays entirely within your agent's repo

If in doubt: ask yourself "does the Orchestrator need to know about this change?" If no, don't touch shared.

---

## Installation

```bash
# Local development — install in editable mode
pip install -e /path/to/aieic-shared

# In CI/CD
pip install git+https://github.com/<your-org>/aieic-shared.git@v0.1.0

# With mock server support (needed to run mock agents)
pip install -e ".[mocks]"
```

---

## Usage

### Orchestrator: using HTTP clients

```python
from aieic_shared.clients import (
    ParticipantClient,
    LabCompanionClient,
    AssessmentClient,
    CurriculumClient,
)

participant = ParticipantClient(base_url="http://participant:8001")
companion   = LabCompanionClient(base_url="http://companion:8002")

context = await participant.get_student_context("alex_m")

reply = await companion.chat(
    student_id="alex_m",
    session_id="...",
    message="How do I insert at position 3?",
    student_context_summary=context.summary,
    conversation_history=[],
    lab_id="lab4",
)
```

### Individual agent: importing core enums (optional)

If you want to use the shared enums instead of redefining them, you can:

```python
from aieic_shared.schemas.core import LabPhase, StudentStatus

# Use in your own internal model
class MyInternalState(BaseModel):
    phase: LabPhase
    status: StudentStatus
```

You are **not** required to use `CurriculumMaterial`, `AssessmentResult`, etc. internally. Define your own richer model and convert to the wire format at the router level:

```python
# Your internal model — evolve freely
class LabMaterial(BaseModel):
    lab_id: str
    spec_markdown: str
    feedback_history: list[FeedbackEntry]  # internal only
    material_content: str | None           # internal only
    ...

# Router — strip internal fields before responding
@router.get("/{lab_id}", response_model=LabMaterial,
            response_model_exclude={"feedback_history", "material_content"})
async def get_lab(lab_id: str) -> LabMaterial:
    return store.get(lab_id)
```

### Running mock servers for parallel development

Lets you develop against the full system without waiting for other agents.

```bash
# Terminal 1 — mock Lab Companion
python -m aieic_shared.mocks.lab_companion --port 8002

# Terminal 2 — mock Curriculum Designer
python -m aieic_shared.mocks.curriculum_designer --port 8003

# Terminal 3 — mock Participant Agent
python -m aieic_shared.mocks.participant --port 8001

# Terminal 4 — mock Assessment Agent
python -m aieic_shared.mocks.assessment --port 8004

# Terminal 5 — your real agent or Orchestrator
uvicorn main:app --port 8000
```

Or run all mocks at once:

```bash
python -m aieic_shared.mocks.run_all
```

---

## Package structure

```
aieic_shared/
├── schemas/           # Wire-format Pydantic models (API contract)
│   ├── core.py        # Shared enums and reference types (LabPhase, StudentRef, …)
│   ├── companion.py   # ChatRequest, ChatResponse
│   ├── participant.py # LogInteractionRequest, StudentContextResponse
│   ├── curriculum.py  # CurriculumMaterial, GenerateCurriculumRequest, …
│   ├── assessment.py  # AssessmentResult, ManualReviewRequest, …
│   └── orchestrator.py# DashboardResponse, OrchestratorSessionState, …
├── clients/           # Typed httpx clients (Orchestrator uses these)
│   ├── base.py
│   ├── companion.py
│   ├── participant.py
│   ├── curriculum.py
│   └── assessment.py
└── mocks/             # FastAPI apps returning realistic fixed data
    ├── lab_companion.py
    ├── curriculum_designer.py
    ├── participant.py
    ├── assessment.py
    └── run_all.py
```

The authoritative interface specification lives in [`INTERFACE_CONTRACT.md`](./INTERFACE_CONTRACT.md). The Python code here is the *implementation* of that contract — if they ever disagree, the contract doc wins.

---

## Versioning

This package follows the same versioning as `INTERFACE_CONTRACT.md`.

- **Breaking change** (bump major: `v0.x` → `v1.0`): removing a field, changing a type, renaming an endpoint, changing an enum value.
- **Additive change** (bump minor: `v0.1` → `v0.2`): adding optional fields, adding new endpoints, documentation updates.

For breaking changes, coordinate with all affected agent owners before merging. See the [change process](./INTERFACE_CONTRACT.md#versioning--change-process) in the contract doc.
