# astrbot_plugin_agentmemory

AstrBot 的 agentmemory 长期记忆接入插件。

本插件通过 REST API 连接 [agentmemory](https://github.com/rohitg00/agentmemory)，在不改动 AstrBot 内置会话管理的前提下，为机器人增加“按 project + sender_id 作用域的长期记忆”能力。插件不再自动把记忆注入 prompt，而是提供 LLM tools 和命令，让模型或管理员主动搜索、记录和删除记忆。

English documentation: [README_EN.md](README_EN.md)

## 适合谁使用

如果你希望 AstrBot 能记住这些内容，本插件会比较有用：

- 用户长期偏好，例如称呼、语言习惯、固定格式要求。
- 群聊里的长期上下文，例如项目背景、常见问题、约定俗成的规则。
- 多轮会话之外仍然有价值的信息，例如某个用户之前提到过的需求。

如果你只需要当前对话上下文，AstrBot 自带的会话管理已经足够，不一定需要本插件。

## 工作方式

插件不会替换 AstrBot 的会话系统，也不会替换知识库。

- AstrBot 原有 `ConversationManager` 继续负责当前会话历史。
- AstrBot 知识库继续负责文档检索。
- agentmemory 负责长期记忆的保存、搜索和召回。

一次普通对话的流程如下：

1. 用户发送消息。
2. 大模型需要记忆时，可主动调用 `agentmemory_search` / `agentmemory_remember` / `agentmemory_forget`。
3. 机器人回复后，插件可按配置把本轮对话片段写入对应 sender 的长期记忆。

## 准备 agentmemory 服务

本插件不内置 agentmemory 服务，需要单独启动。

推荐先在服务器或本机运行：

```bash
npx @agentmemory/agentmemory
```

默认 API 地址是：

```text
http://localhost:3111
```

如果你的网络环境访问 npm 较慢，可以使用国内 npm 镜像或提前在网络较好的环境安装 agentmemory。agentmemory 是独立服务，和 AstrBot 插件目录无关。

如果你为 agentmemory 配置了 `AGENTMEMORY_SECRET`，需要在插件配置里的 `secret` 填入同一个值。

## 安装插件

进入 AstrBot 插件目录：

```bash
cd AstrBot/data/plugins
git clone https://github.com/zouyonghe/astrbot_plugin_agentmemory
```

如果 AstrBot 没有自动安装依赖，可以手动执行：

```bash
pip install -r astrbot_plugin_agentmemory/requirements.txt
```

然后在 AstrBot WebUI 的插件管理页面重载插件。

## 插件配置

插件支持在 AstrBot WebUI 中配置。主要配置项如下：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `base_url`（agentmemory 服务地址） | `http://localhost:3111` | agentmemory REST API 地址 |
| `secret`（访问密钥） | 空 | agentmemory 的 Bearer Token |
| `project`（项目名称） | `astrbot` | 用于区分不同机器人或部署环境，会参与记忆 session 作用域 |
| `timeout_seconds`（请求超时时间） | `3.0` | HTTP 请求超时时间，单位为秒 |
| `admin_only`（仅管理员可使用记忆） | `false` | 开启后，只有管理员会触发自动沉淀、命令和 LLM tools |
| `recall.limit`（召回数量上限） | `5` | 命令或 LLM tools 每次最多返回多少条记忆 |
| `capture.enabled`（启用对话沉淀） | `true` | 是否在回复后写入对话片段 |
| `capture.max_user_chars`（用户消息最大长度） | `1000` | 写入的用户消息最大长度 |
| `capture.max_assistant_chars`（机器人回复最大长度） | `4000` | 写入的机器人回复最大长度 |

## 可用命令

### 查看服务状态

```text
/am_status
```

用于检查 agentmemory 服务是否可用。

### 搜索长期记忆

```text
/am_search 用户偏好
```

用于手动搜索 agentmemory 中的记忆。

### 手动保存记忆

```text
/am_remember 用户希望回答尽量简洁，并优先使用中文。
```

用于手动写入一条长期记忆。

### 删除记忆

```text
/am_forget obs_xxx
```

用于按 `observation_id` 删除当前 sender 作用域内的明确记忆。为避免共享 agentmemory 服务中的越权删除，插件不开放全局 `memory_id` 删除。

## 隐私说明

插件会把纯文本对话片段发送到你配置的 agentmemory 服务。

在群聊中，这意味着群聊文本也可能被写入 agentmemory。建议只在你明确希望启用长期记忆的会话中使用，并提前告知相关成员。

当前版本不会上传：

- 图片
- 文件
- 语音
- 视频
- 平台原始事件 payload

LLM tools 返回的记忆结果是“不可信背景文本”。即便如此，也建议不要把敏感信息、密钥或不希望模型长期参考的内容写入 agentmemory。

如果 agentmemory 不在本机，而是部署在远程服务器，并且配置了 `AGENTMEMORY_SECRET`，建议使用 HTTPS、内网访问或 SSH 隧道，避免 Bearer Token 和聊天内容在网络中明文传输。

## 常见问题

### 插件会不会影响正常聊天？

agentmemory 调用失败时，插件只会记录日志，不会阻断 AstrBot 正常回复。

### 它和 AstrBot 自带群聊上下文感知冲突吗？

不直接冲突。AstrBot 自带群聊上下文感知更偏短期、实时、进程内上下文；agentmemory 更偏跨会话长期记忆。建议不要把召回数量设置过大，避免 prompt 过长。

### 它和知识库有什么区别？

知识库适合放文档、资料、手册。agentmemory 适合放用户偏好、会话中沉淀下来的事实、长期约定和历史上下文。

### 没启动 agentmemory 会怎样？

`/am_status` 会提示不可用；记忆相关功能会跳过，不影响正常聊天。

## 开发状态

当前版本是最小可用版，重点是稳定接入：

- LLM tools 主动搜索、保存、忘却
- 手动搜索
- 手动保存
- 手动删除
- 服务状态检查

后续可以考虑增加：

- 更细粒度的会话/群聊白名单。
- Dashboard 页面。
- 更完整的记忆管理命令。
