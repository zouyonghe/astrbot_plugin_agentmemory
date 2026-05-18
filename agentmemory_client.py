from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class AgentMemoryClient:
    base_url: str
    secret: str = ""
    timeout_seconds: float = 3.0

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/") or "http://localhost:3111"
        if self.timeout_seconds <= 0:
            self.timeout_seconds = 3.0

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.secret:
            headers["Authorization"] = f"Bearer {self.secret}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(),
                json=json,
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {"data": data}

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/agentmemory/health")

    async def smart_search(self, query: str, limit: int = 5) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/agentmemory/smart-search",
            json={"query": query, "limit": max(limit, 1)},
        )

    async def expand_search_results(
        self, results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        expand_ids = []
        for result in results:
            obs_id = result.get("obsId")
            if not isinstance(obs_id, str) or not obs_id:
                continue
            session_id = result.get("sessionId")
            item: dict[str, Any] = {"obsId": obs_id}
            if isinstance(session_id, str) and session_id:
                item["sessionId"] = session_id
            expand_ids.append(item)

        if not expand_ids:
            return {"mode": "expanded", "results": []}

        return await self._request(
            "POST",
            "/agentmemory/smart-search",
            json={"expandIds": expand_ids},
        )

    async def observe(
        self,
        *,
        hook_type: str,
        session_id: str,
        project: str,
        cwd: str,
        timestamp: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/agentmemory/observe",
            json={
                "hookType": hook_type,
                "sessionId": session_id,
                "project": project,
                "cwd": cwd,
                "timestamp": timestamp,
                "data": data,
            },
        )

    async def remember(self, content: str, memory_type: str = "fact") -> dict[str, Any]:
        return await self._request(
            "POST",
            "/agentmemory/remember",
            json={"content": content, "type": memory_type},
        )
