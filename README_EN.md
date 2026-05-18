# astrbot_plugin_agentmemory

An AstrBot plugin for integrating with agentmemory long-term memory.

This plugin connects AstrBot to [agentmemory](https://github.com/rohitg00/agentmemory) through its REST API. It keeps AstrBot's built-in conversation management unchanged and adds an optional long-term memory layer: relevant memories are recalled before LLM requests, and completed conversation turns are captured after LLM responses.

中文文档: [README.md](README.md)

## When To Use It

Use this plugin if you want AstrBot to remember information across conversations, such as:

- Long-term user preferences, including names, language style, and output format preferences.
- Persistent group-chat context, including project background, recurring issues, and shared conventions.
- Useful facts from previous conversations that should remain available later.

If you only need current conversation history, AstrBot's built-in conversation manager may already be enough.

## How It Works

The plugin does not replace AstrBot's conversation system or knowledge base.

- AstrBot's `ConversationManager` still handles current conversation history.
- AstrBot's knowledge base still handles document retrieval.
- agentmemory handles long-term memory storage, search, and recall.

For a normal turn:

1. The user sends a message.
2. The plugin searches agentmemory for relevant long-term memory.
3. The plugin appends recalled memories to the LLM system prompt as background context.
4. After the assistant responds, the plugin writes the user message and assistant response to agentmemory.

## Start agentmemory

This plugin does not bundle the agentmemory service. Start it separately:

```bash
npx @agentmemory/agentmemory
```

The default API endpoint is:

```text
http://localhost:3111
```

If you configured `AGENTMEMORY_SECRET`, set the same value in this plugin's `secret` config field.

## Installation

Clone this repository into AstrBot's plugin directory:

```bash
cd AstrBot/data/plugins
git clone https://github.com/zouyonghe/astrbot_plugin_agentmemory
```

If AstrBot does not install dependencies automatically, install them manually:

```bash
pip install -r astrbot_plugin_agentmemory/requirements.txt
```

Then reload plugins in the AstrBot WebUI.

## Configuration

The plugin can be configured in the AstrBot WebUI.

| Field | Default | Description |
| --- | --- | --- |
| `enabled` | `true` | Enable or disable the plugin |
| `base_url` | `http://localhost:3111` | agentmemory REST API base URL |
| `secret` | empty | Bearer token for agentmemory |
| `project` | `astrbot` | Project name stored in agentmemory |
| `timeout_seconds` | `3.0` | HTTP timeout |
| `recall.enabled` | `true` | Recall memory before LLM requests |
| `recall.limit` | `5` | Maximum recalled memories per request |
| `capture.enabled` | `true` | Capture completed conversation turns |
| `capture.max_user_chars` | `1000` | Maximum stored user message length |
| `capture.max_assistant_chars` | `4000` | Maximum stored assistant response length |

## Commands

### Check Service Status

```text
/am_status
```

Checks whether the configured agentmemory service is available.

### Search Long-Term Memory

```text
/am_search user preference
```

Searches memories stored in agentmemory.

### Save A Manual Memory

```text
/am_remember The user prefers concise answers in Chinese.
```

Saves one long-term memory manually.

## Privacy Notes

The plugin sends text conversation snippets to the configured agentmemory service.

The current version does not upload:

- Images
- Files
- Audio
- Video
- Raw platform event payloads

If agentmemory runs on a remote server and uses `AGENTMEMORY_SECRET`, use HTTPS, private networking, or an SSH tunnel to avoid sending bearer tokens and chat content over plaintext HTTP.

## FAQ

### Will this break normal chat if agentmemory is down?

No. agentmemory failures are logged but do not block normal AstrBot replies.

### Does it conflict with AstrBot group-chat context awareness?

Not directly. AstrBot's built-in group-chat context awareness is short-term and in-process. agentmemory is for cross-session long-term memory. Keep the recall limit modest to avoid overly long prompts.

### How is it different from a knowledge base?

Knowledge bases are best for documents, manuals, and reference material. agentmemory is better for user preferences, facts learned during conversations, long-term conventions, and historical context.

### What happens if agentmemory is not running?

`/am_status` reports it as unavailable. Automatic recall and capture are skipped, and normal chat continues.

## Status

This is a minimal usable version focused on stable integration:

- Automatic recall
- Automatic capture
- Manual search
- Manual remember
- Health check

Potential future improvements:

- Optional LLM tools for model-initiated memory search/write.
- Session or group allowlists.
- Dashboard page.
- More memory management commands.
