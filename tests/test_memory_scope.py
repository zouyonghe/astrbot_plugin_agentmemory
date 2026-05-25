import asyncio
import types
from types import SimpleNamespace
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import httpx

PLUGIN_PARENT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(PLUGIN_PARENT))


def _identity_decorator(*_args, **_kwargs):
    def decorator(func):
        return func

    return decorator


astrbot_module = types.ModuleType("astrbot")
astrbot_api_module = types.ModuleType("astrbot.api")
astrbot_event_module = types.ModuleType("astrbot.api.event")
astrbot_provider_module = types.ModuleType("astrbot.api.provider")
astrbot_core_module = types.ModuleType("astrbot.core")
astrbot_core_star_module = types.ModuleType("astrbot.core.star")
astrbot_core_filter_module = types.ModuleType("astrbot.core.star.filter")
astrbot_command_module = types.ModuleType("astrbot.core.star.filter.command")

astrbot_api_module.AstrBotConfig = dict
astrbot_api_module.llm_tool = _identity_decorator
astrbot_api_module.logger = SimpleNamespace(warning=lambda *_args, **_kwargs: None)
astrbot_api_module.star = SimpleNamespace(Star=object, Context=object)
astrbot_event_module.AstrMessageEvent = object
astrbot_event_module.filter = SimpleNamespace(
    command=_identity_decorator,
    on_llm_response=_identity_decorator,
)
astrbot_provider_module.LLMResponse = object
astrbot_command_module.GreedyStr = str

sys.modules.setdefault("astrbot", astrbot_module)
sys.modules.setdefault("astrbot.api", astrbot_api_module)
sys.modules.setdefault("astrbot.api.event", astrbot_event_module)
sys.modules.setdefault("astrbot.api.provider", astrbot_provider_module)
sys.modules.setdefault("astrbot.core", astrbot_core_module)
sys.modules.setdefault("astrbot.core.star", astrbot_core_star_module)
sys.modules.setdefault("astrbot.core.star.filter", astrbot_core_filter_module)
sys.modules.setdefault("astrbot.core.star.filter.command", astrbot_command_module)

from astrbot_plugin_agentmemory.main import (  # noqa: E402
    AgentMemoryPlugin,
    build_sender_scope,
    filter_results_for_session,
)


def test_build_sender_scope_uses_platform_and_sender_id():
    assert (
        build_sender_scope("bot-a", "webchat", "buding")
        == "bot-a:webchat:user:buding"
    )


def test_build_sender_scope_normalizes_empty_project_to_astrbot():
    assert build_sender_scope(None, "webchat", "buding") == "astrbot:webchat:user:buding"
    assert build_sender_scope("", "webchat", "buding") == "astrbot:webchat:user:buding"
    assert build_sender_scope("   ", "webchat", "buding") == "astrbot:webchat:user:buding"


def test_filter_results_for_session_keeps_only_matching_session():
    payload = {
        "mode": "compact",
        "results": [
            {"obsId": "obs_1", "sessionId": "bot-a:webchat:user:buding"},
            {"obsId": "obs_2", "sessionId": "bot-b:webchat:user:buding"},
            {"obsId": "obs_3"},
        ],
    }

    filtered = filter_results_for_session(payload, "bot-a:webchat:user:buding")

    assert filtered["results"] == [
        {"obsId": "obs_1", "sessionId": "bot-a:webchat:user:buding"}
    ]


def test_search_memory_caps_overfetch_limit():
    client = Mock()
    client.smart_search = AsyncMock(return_value={"mode": "expanded", "results": []})
    plugin = _plugin_with_client(client)

    asyncio.run(
        plugin._search_memory_with_text("deploy notes", 8, "bot-a:webchat:user:buding")
    )

    client.smart_search.assert_awaited_once_with("deploy notes", limit=50)


def test_search_memory_caps_large_limits_to_overfetch_max_results():
    client = Mock()
    client.smart_search = AsyncMock(return_value={"mode": "expanded", "results": []})
    plugin = _plugin_with_client(client)

    asyncio.run(
        plugin._search_memory_with_text("deploy notes", 100, "bot-a:webchat:user:buding")
    )

    client.smart_search.assert_awaited_once_with("deploy notes", limit=50)


def test_search_memory_uses_configured_overfetch_settings():
    client = Mock()
    client.smart_search = AsyncMock(return_value={"mode": "expanded", "results": []})
    plugin = _plugin_with_client(client)
    plugin.config["recall"] = {"overfetch_factor": 3, "overfetch_max_results": 20}

    asyncio.run(
        plugin._search_memory_with_text("deploy notes", 8, "bot-a:webchat:user:buding")
    )

    client.smart_search.assert_awaited_once_with("deploy notes", limit=20)


def test_search_memory_caps_pathological_overfetch_config():
    client = Mock()
    client.smart_search = AsyncMock(return_value={"mode": "expanded", "results": []})
    plugin = _plugin_with_client(client)
    plugin.config["recall"] = {"overfetch_factor": 1000, "overfetch_max_results": 1000}

    asyncio.run(
        plugin._search_memory_with_text("deploy notes", 50, "bot-a:webchat:user:buding")
    )

    client.smart_search.assert_awaited_once_with("deploy notes", limit=200)


def test_format_observe_result_reads_top_level_observation_id():
    payload = {"observationId": "obs_123"}

    assert (
        AgentMemoryPlugin._format_observe_result(payload)
        == "Memory saved (observation_id=obs_123)."
    )


def test_admin_only_blocks_non_admin_memory_access():
    plugin = AgentMemoryPlugin.__new__(AgentMemoryPlugin)
    plugin.config = {"admin_only": True}
    event = SimpleNamespace(role="member")

    assert plugin._memory_allowed(event) is False


def test_admin_only_allows_admin_memory_access():
    plugin = AgentMemoryPlugin.__new__(AgentMemoryPlugin)
    plugin.config = {"admin_only": True}
    event = SimpleNamespace(role="admin")

    assert plugin._memory_allowed(event) is True


def _event() -> SimpleNamespace:
    return SimpleNamespace(
        role="admin",
        plain_result=lambda message: message,
        get_sender_id=lambda: "buding",
        get_platform_id=lambda: "webchat",
    )


async def _collect_async_generator(generator):
    return [item async for item in generator]


def _plugin_with_client(client: Mock) -> AgentMemoryPlugin:
    plugin = AgentMemoryPlugin.__new__(AgentMemoryPlugin)
    plugin.config = {"admin_only": False, "project": "bot-a"}
    plugin._client = Mock(return_value=client)
    return plugin


def test_am_forget_empty_identifier_returns_usage_and_makes_no_client_calls():
    client = Mock()
    client.forget_memory = AsyncMock()
    client.forget_observations = AsyncMock()
    plugin = _plugin_with_client(client)

    result = asyncio.run(_collect_async_generator(plugin.am_forget(_event(), "")))

    assert result == ["Usage: /am_forget <observation_id>"]
    client.forget_memory.assert_not_called()
    client.forget_observations.assert_not_called()


def test_am_forget_non_obs_identifier_disallowed_and_does_not_call_forget_memory():
    client = Mock()
    client.forget_memory = AsyncMock()
    client.forget_observations = AsyncMock()
    plugin = _plugin_with_client(client)

    result = asyncio.run(_collect_async_generator(plugin.am_forget(_event(), "mem_123")))

    assert "memory_id deletion is not allowed" in result[0]
    client.forget_memory.assert_not_called()
    client.forget_observations.assert_not_called()


def test_am_forget_valid_obs_identifier_calls_forget_observations():
    client = Mock()
    client.forget_memory = AsyncMock()
    client.forget_observations = AsyncMock(return_value={})
    plugin = _plugin_with_client(client)

    result = asyncio.run(_collect_async_generator(plugin.am_forget(_event(), "obs_123")))

    assert result == ["Memory forgotten."]
    client.forget_observations.assert_awaited_once_with(
        "bot-a:webchat:user:buding", ["obs_123"]
    )
    client.forget_memory.assert_not_called()


def test_am_forget_obs_identifier_handles_http_error():
    client = Mock()
    client.forget_memory = AsyncMock()
    client.forget_observations = AsyncMock(side_effect=httpx.HTTPError("boom"))
    plugin = _plugin_with_client(client)

    result = asyncio.run(_collect_async_generator(plugin.am_forget(_event(), "obs_123")))

    assert len(result) == 1
    assert result[0].startswith("agentmemory forget failed: ")
    assert "boom" in result[0]
    client.forget_observations.assert_awaited_once_with(
        "bot-a:webchat:user:buding", ["obs_123"]
    )
    client.forget_memory.assert_not_called()


def test_agentmemory_forget_with_memory_id_disallowed_and_does_not_call_forget_memory():
    client = Mock()
    client.forget_memory = AsyncMock()
    client.forget_observations = AsyncMock()
    plugin = _plugin_with_client(client)

    result = asyncio.run(
        plugin.agentmemory_forget(_event(), memory_id="mem_123", observation_ids=None)
    )

    assert "memory_id deletion is not allowed" in result
    client.forget_memory.assert_not_called()
    client.forget_observations.assert_not_called()


def test_agentmemory_forget_rejects_non_obs_observation_ids():
    client = Mock()
    client.forget_memory = AsyncMock()
    client.forget_observations = AsyncMock()
    plugin = _plugin_with_client(client)

    result = asyncio.run(
        plugin.agentmemory_forget(_event(), memory_id=None, observation_ids=["mem_123"])
    )

    assert "memory_id deletion is not allowed" in result
    client.forget_memory.assert_not_called()
    client.forget_observations.assert_not_called()


def test_agentmemory_forget_with_only_observation_ids_calls_forget_observations():
    client = Mock()
    client.forget_memory = AsyncMock()
    client.forget_observations = AsyncMock(return_value={})
    plugin = _plugin_with_client(client)

    result = asyncio.run(
        plugin.agentmemory_forget(
            _event(), memory_id=None, observation_ids=["obs_1", "obs_2"]
        )
    )

    assert result == "Memory forgotten."
    client.forget_observations.assert_awaited_once_with(
        "bot-a:webchat:user:buding", ["obs_1", "obs_2"]
    )
    client.forget_memory.assert_not_called()


def test_agentmemory_forget_without_ids_returns_usage_message():
    client = Mock()
    client.forget_memory = AsyncMock()
    client.forget_observations = AsyncMock()
    plugin = _plugin_with_client(client)

    result = asyncio.run(
        plugin.agentmemory_forget(_event(), memory_id=None, observation_ids=None)
    )

    assert result == "Provide one or more observation_ids to forget."
    client.forget_memory.assert_not_called()
    client.forget_observations.assert_not_called()
