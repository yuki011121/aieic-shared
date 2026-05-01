# aieic-shared

Shared schemas, HTTP clients, and mock servers for the AIEIC Lab Multi-Agent System.

- **Wire-format schemas** — request/response shapes that flow between agents over HTTP
- **Typed HTTP clients** — used by the Orchestrator; validates requests/responses at every call site
- **Mock servers** — stand-in FastAPI apps for parallel development before all agents are ready

---

## Import guide

| Role | What to import |
|---|---|
| **Orchestrator** | Everything — schemas, clients, orchestrator schemas |
| **Individual agent** | Only `core.py` enums if useful (`LabPhase`, `StudentStatus`, etc.) |
| **Test / integration code** | Schemas (for assertions) and mock servers |

If a type is used by only one agent, it belongs in that agent's repo. If both sides of an HTTP call must agree on it, it belongs here.

---

## Update policy

Update for any change to the HTTP interface between agents:
- Adding, removing, or renaming a field in a request or response
- Changing a field's type
- Adding or removing an endpoint (update the client and mock too)
- Changing an enum value (breaking — see versioning)

Do **not** update for internal-only changes: agent logic, DB schema, internal models, or additive optional response fields.

---

## Installation

```bash
# Local development
pip install -e /path/to/aieic-shared

# CI/CD
pip install git+https://github.com/<your-org>/aieic-shared.git@v0.1.0

# With mock server support
pip install -e ".[mocks]"
```

---

## Usage

### Orchestrator: HTTP clients

```python
from aieic_shared.clients import ParticipantClient, LabCompanionClient

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

### Individual agents: core enums

```python
from aieic_shared.schemas.core import LabPhase, StudentStatus
```

Define your own internal model and convert to the wire format at the router level — do not use `CurriculumMaterial`, `AssessmentResult`, etc. internally:

```python
# Internal model — evolve freely
class LabMaterial(BaseModel):
    lab_id: str
    spec_markdown: str
    feedback_history: list[FeedbackEntry]  # internal only

# Strip internal fields at the router boundary
@router.get("/{lab_id}", response_model=LabMaterial,
            response_model_exclude={"feedback_history"})
async def get_lab(lab_id: str) -> LabMaterial:
    return store.get(lab_id)
```

### Mock servers

```bash
# Run individual mocks
python -m aieic_shared.mocks.lab_companion      --port 8002
python -m aieic_shared.mocks.curriculum_designer --port 8003
python -m aieic_shared.mocks.participant         --port 8001
python -m aieic_shared.mocks.assessment          --port 8004

# Or run all at once
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

The authoritative interface specification is [`INTERFACE_CONTRACT.md`](./INTERFACE_CONTRACT.md). If the Python code and the contract doc ever disagree, the contract wins.

---

## Versioning

Versioned in sync with `INTERFACE_CONTRACT.md`.

- **Breaking** (bump major: `v0.x` → `v1.0`): removing a field, changing a type, renaming an endpoint, changing an enum value
- **Additive** (bump minor: `v0.1` → `v0.2`): new optional fields, new endpoints, documentation updates

For breaking changes, coordinate with all affected agent owners before merging. See the [change process](./INTERFACE_CONTRACT.md#versioning--change-process).
