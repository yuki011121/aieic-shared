# aieic-shared

Shared schemas, HTTP clients, and mock servers for the AIEIC Lab Multi-Agent System.

## Overview

When multiple agents need to exchange data, subtle mismatches in field names or types can cause hard-to-debug failures. This package keeps everyone on the same page by providing a single source of truth for:

- **Pydantic schemas** — every agent imports from here instead of defining its own.
- **Typed HTTP clients** — the Orchestrator uses these to call agents, so request/response shapes are validated at every call site.
- **Mock servers** — stand-ins for agents still in development, so you can test the full request/response loop without waiting for other teams.

## Installation

```bash
# Local development
pip install -e /path/to/aieic-shared

# In CI/CD
pip install git+https://github.com/<your-org>/aieic-shared.git@v0.1.0

# With mock server support
pip install -e ".[mocks]"
```

## Usage

### Importing schemas

```python
from aieic_shared.schemas import (
    StudentRef, LabRef, LabPhase, StudentStatus,
    ChatRequest, ChatResponse,
    LogInteractionRequest, StudentContextResponse,
    AssessmentResult, ManualReviewRequest,
)

from fastapi import FastAPI

app = FastAPI()

@app.post("/companion/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    ...
```

### Using HTTP clients (Orchestrator side)

```python
from aieic_shared.clients import (
    ParticipantClient,
    LabCompanionClient,
    AssessmentClient,
    CurriculumClient,
)

participant = ParticipantClient(base_url="http://participant:8001")
companion = LabCompanionClient(base_url="http://companion:8002")

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

### Running mock servers

Useful when you want to develop end-to-end without waiting for other agents to be ready.

```bash
# Terminal 1: mock Lab Companion
python -m aieic_shared.mocks.lab_companion --port 8002

# Terminal 2: mock Curriculum Designer
python -m aieic_shared.mocks.curriculum_designer --port 8003

# Terminal 3: your real agent
cd participant-agent-AIEIC-main && uvicorn main:app --port 8001

# Terminal 4: Orchestrator under development
cd orchestrator && uvicorn main:app --port 8000
```

## Package structure

```
aieic_shared/
├── schemas/          # Pydantic models — source of truth for all agent I/O
│   ├── core.py       # LabPhase, StudentRef, LabRef, etc.
│   ├── companion.py  # ChatRequest, ChatResponse
│   ├── participant.py
│   ├── curriculum.py
│   ├── assessment.py
│   └── orchestrator.py
├── clients/          # Typed httpx clients for each agent
│   ├── base.py
│   ├── companion.py
│   ├── participant.py
│   ├── curriculum.py
│   └── assessment.py
└── mocks/            # FastAPI apps that return realistic fixed data
    ├── lab_companion.py
    ├── curriculum_designer.py
    ├── participant.py
    └── assessment.py
```

## Versioning

Breaking schema changes require a coordinated update: bump the version, update this package, and notify all agent owners.

## Contributing

Need a schema change? Open a PR with:

1. The schema update in this package.
2. A corresponding contract doc update.
3. Tags for any affected agent owners.

If the field you need doesn't exist yet, adding it here first keeps things consistent across agents.
