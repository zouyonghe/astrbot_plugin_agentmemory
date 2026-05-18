from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from astrbot.api import AstrBotConfig, logger, star
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import LLMResponse, ProviderRequest

from .agentmemory_client import AgentMemoryClient


class AgentMemoryPlugin(star.Star):
    def __init__(self, context: star.Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.config = config

    def _enabled(self) -> bool:
        return bool(self.config.get("enabled", True))

    def _client(self) -> AgentMemoryClient:
        return AgentMemoryClient(
            base_url=str(self.config.get("base_url", "http://localhost:3111")),
            secret=str(self.config.get("secret", "")),
            timeout_seconds=float(self.config.get("timeout_seconds", 3.0)),
        )

    def _project(self) -> str:
        project = str(self.config.get("project", "astrbot")).strip()
        return project or "astrbot"

    def _recall_config(self) -> dict[str, Any]:
        recall = self.config.get("recall", {})
        return recall if isinstance(recall, dict) else {}

    def _capture_config(self) -> dict[str, Any]:
        capture = self.config.get("capture", {})
        return capture if isinstance(capture, dict) else {}

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        if max_chars <= 0 or len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip() + "..."

    @staticmethod
    def _extract_memory_text(result: Any) -> str:
        if isinstance(result, str):
            return result.strip()
        if not isinstance(result, dict):
            return ""

        observation = result.get("observation")
        if isinstance(observation, dict):
            title = str(observation.get("title") or "").strip()
            narrative = str(observation.get("narrative") or "").strip()
            content = str(observation.get("content") or "").strip()
            return ": ".join(part for part in (title, narrative or content) if part)

        title = str(result.get("title") or "").strip()
        narrative = str(result.get("narrative") or "").strip()
        content = str(result.get("content") or "").strip()
        return ": ".join(part for part in (title, narrative or content) if part)

    def _format_search_results(self, payload: dict[str, Any], limit: int) -> str:
        results = payload.get("results", [])
        if not isinstance(results, list):
            return ""

        lines = []
        for result in results[:limit]:
            text = self._extract_memory_text(result)
            if text:
                lines.append(f"- {text}")

        if not lines:
            return ""

        return (
            "[Relevant Long-Term Memory from agentmemory]\n"
            "Treat these notes as background context. Current user instructions "
            "and current conversation state take precedence.\n" + "\n".join(lines)
        )

    @filter.on_llm_request()
    async def inject_agentmemory_context(
        self, event: AstrMessageEvent, req: ProviderRequest
    ) -> None:
        if not self._enabled() or not req.prompt:
            return

        recall = self._recall_config()
        if not bool(recall.get("enabled", True)):
            return

        query = req.prompt.strip()
        if not query:
            return

        limit = int(recall.get("limit", 5) or 5)
        try:
            payload = await self._client().smart_search(query, limit=limit)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(f"agentmemory recall failed: {exc}")
            return

        memory_block = self._format_search_results(payload, limit)
        if not memory_block:
            return

        req.system_prompt = f"{req.system_prompt or ''}\n\n{memory_block}\n"

    @filter.on_llm_response()
    async def capture_agentmemory_observation(
        self, event: AstrMessageEvent, resp: LLMResponse
    ) -> None:
        if not self._enabled():
            return

        capture = self._capture_config()
        if not bool(capture.get("enabled", True)):
            return

        user_text = (event.message_str or "").strip()
        assistant_text = (resp.completion_text or "").strip()
        if not user_text or not assistant_text:
            return

        max_user_chars = int(capture.get("max_user_chars", 1000) or 1000)
        max_assistant_chars = int(capture.get("max_assistant_chars", 4000) or 4000)
        try:
            await self._client().observe(
                hook_type="post_tool_use",
                session_id=event.unified_msg_origin,
                project=self._project(),
                cwd=str(Path.cwd()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                data={
                    "tool_name": "conversation",
                    "tool_input": self._truncate(user_text, max_user_chars),
                    "tool_output": self._truncate(assistant_text, max_assistant_chars),
                },
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(f"agentmemory capture failed: {exc}")

    @filter.command("am_status")
    async def am_status(self, event: AstrMessageEvent):
        """Check agentmemory service status."""
        if not self._enabled():
            yield event.plain_result("agentmemory plugin is disabled.")
            return
        try:
            payload = await self._client().health()
        except (httpx.HTTPError, ValueError) as exc:
            yield event.plain_result(f"agentmemory unavailable: {exc}")
            return

        status = payload.get("status", "unknown")
        service = payload.get("service", "agentmemory")
        version = payload.get("version", "unknown")
        yield event.plain_result(f"{service} status: {status}, version: {version}")

    @filter.command("am_search")
    async def am_search(self, event: AstrMessageEvent):
        """Search agentmemory long-term memory."""
        query = event.message_str.strip()
        if not query:
            yield event.plain_result("Usage: /am_search <query>")
            return

        limit = int(self._recall_config().get("limit", 5) or 5)
        try:
            payload = await self._client().smart_search(query, limit=limit)
        except (httpx.HTTPError, ValueError) as exc:
            yield event.plain_result(f"agentmemory search failed: {exc}")
            return

        result = self._format_search_results(payload, limit)
        yield event.plain_result(result or "No related memory found.")

    @filter.command("am_remember")
    async def am_remember(self, event: AstrMessageEvent):
        """Save a manual memory to agentmemory."""
        content = event.message_str.strip()
        if not content:
            yield event.plain_result("Usage: /am_remember <content>")
            return

        try:
            payload = await self._client().remember(content, memory_type="fact")
        except (httpx.HTTPError, ValueError) as exc:
            yield event.plain_result(f"agentmemory remember failed: {exc}")
            return

        memory = payload.get("memory") if isinstance(payload, dict) else None
        memory_id = memory.get("id") if isinstance(memory, dict) else None
        suffix = f" ({memory_id})" if memory_id else ""
        yield event.plain_result(f"Memory saved{suffix}.")
