# astrbot_plugin_agentmemory

Connect AstrBot to [agentmemory](https://github.com/rohitg00/agentmemory) through its REST API.

This plugin keeps AstrBot's built-in conversation management unchanged. It adds an optional long-term memory layer that recalls relevant memories before LLM requests and captures completed conversation turns after LLM responses.

## Requirements

Start agentmemory separately:

```bash
npx @agentmemory/agentmemory
```

The default API endpoint is `http://localhost:3111`.

If you set `AGENTMEMORY_SECRET`, configure the same token in this plugin's `secret` field.

## Installation

Clone this repository into AstrBot's plugin directory:

```bash
cd AstrBot/data/plugins
git clone https://github.com/buding/astrbot_plugin_agentmemory
```

Install dependencies if AstrBot does not install them automatically:

```bash
pip install -r astrbot_plugin_agentmemory/requirements.txt
```

Reload plugins in the AstrBot WebUI.

## Configuration

- `enabled`: enable or disable the plugin.
- `base_url`: agentmemory REST API base URL.
- `secret`: bearer token, only needed when agentmemory uses `AGENTMEMORY_SECRET`.
- `project`: project name stored in agentmemory.
- `timeout_seconds`: HTTP timeout.
- `recall.enabled`: inject memory before LLM requests.
- `recall.limit`: maximum search results to inject.
- `capture.enabled`: capture completed conversation turns.
- `capture.max_user_chars`: max stored user text length.
- `capture.max_assistant_chars`: max stored assistant text length.

## Commands

- `/am_status`: check agentmemory health.
- `/am_search <query>`: search long-term memory.
- `/am_remember <content>`: manually save a memory.

## Privacy Notes

The plugin sends text conversation snippets to the configured agentmemory server. It does not upload images, files, audio, or raw platform payloads. For non-localhost deployments with a bearer token, use HTTPS or an SSH tunnel.
