"""
Base class for typed HTTP clients to AIEIC agents.

Provides:
  - Connection lifecycle (open / close / context manager)
  - Common health check
  - Centralized error handling
  - Default timeouts and retries
"""

from __future__ import annotations
from typing import Any, Optional

import httpx

from aieic_shared.schemas.core import HealthResponse


class AgentClientError(Exception):
    """Raised when an agent call fails (network error, non-2xx status, validation, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        agent: Optional[str] = None,
        response_body: Optional[Any] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.agent = agent
        self.response_body = response_body


class AgentClient:
    """
    Base class. Subclasses should add typed methods for each agent endpoint.

    Default timeout is generous (30s) because some agents do LLM calls. Override
    per-call when you know the operation is fast (e.g., GET /health).
    """

    AGENT_NAME: str = "agent"

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None  # only close if we created it

    async def __aenter__(self) -> "AgentClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client. Safe to call multiple times."""
        if self._owns_client:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health(self) -> HealthResponse:
        """GET /health — every agent must implement this."""
        data = await self._get("/health")
        return HealthResponse(**data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: Optional[dict] = None) -> Any:
        """Internal GET helper. Returns parsed JSON. Raises AgentClientError on failure."""
        try:
            resp = await self._client.get(f"{self.base_url}{path}", params=params)
        except httpx.HTTPError as e:
            raise AgentClientError(
                f"Network error calling {self.AGENT_NAME} GET {path}: {e}",
                agent=self.AGENT_NAME,
            ) from e
        return self._handle_response(resp, "GET", path)

    async def _post(
        self,
        path: str,
        *,
        json: Optional[dict] = None,
        data: Optional[dict] = None,
        files: Optional[dict] = None,
    ) -> Any:
        """Internal POST helper. Returns parsed JSON. Raises AgentClientError on failure."""
        try:
            resp = await self._client.post(
                f"{self.base_url}{path}",
                json=json,
                data=data,
                files=files,
            )
        except httpx.HTTPError as e:
            raise AgentClientError(
                f"Network error calling {self.AGENT_NAME} POST {path}: {e}",
                agent=self.AGENT_NAME,
            ) from e
        return self._handle_response(resp, "POST", path)

    def _handle_response(self, resp: httpx.Response, method: str, path: str) -> Any:
        """Parse response, raising AgentClientError on non-2xx."""
        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise AgentClientError(
                f"{self.AGENT_NAME} {method} {path} returned {resp.status_code}",
                status_code=resp.status_code,
                agent=self.AGENT_NAME,
                response_body=body,
            )
        if resp.status_code == 204 or not resp.content:
            return None
        try:
            return resp.json()
        except Exception as e:
            raise AgentClientError(
                f"Could not parse JSON response from {self.AGENT_NAME} {method} {path}: {e}",
                status_code=resp.status_code,
                agent=self.AGENT_NAME,
                response_body=resp.text,
            ) from e
