from types import SimpleNamespace
import sys
from pathlib import Path

PLUGIN_PARENT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(PLUGIN_PARENT))

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
