"""
Typed HTTP clients for calling each agent.

These clients are what the Orchestrator uses to talk to the other agents.
Every method has a typed signature, so request/response shapes are checked
at every call site.

Example:
    from aieic_shared.clients import ParticipantClient

    client = ParticipantClient(base_url="http://participant:8001")
    context = await client.get_student_context("alex_m")
    print(context.summary)
    await client.close()

    # or as an async context manager:
    async with ParticipantClient(base_url="...") as client:
        context = await client.get_student_context("alex_m")
"""

from aieic_shared.clients.base import AgentClient, AgentClientError
from aieic_shared.clients.companion import LabCompanionClient
from aieic_shared.clients.participant import ParticipantClient
from aieic_shared.clients.curriculum import CurriculumClient
from aieic_shared.clients.assessment import AssessmentClient

__all__ = [
    "AgentClient",
    "AgentClientError",
    "LabCompanionClient",
    "ParticipantClient",
    "CurriculumClient",
    "AssessmentClient",
]
