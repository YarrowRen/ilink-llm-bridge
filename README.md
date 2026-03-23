# iLink LLM Bridge

将微信（WeChat）通过腾讯 iLink API 接入任意主流 LLM 提供商的独立桥接服务。无框架依赖，配置驱动，开箱即用。

---

## 功能特性

- **微信消息双向通信**：长轮询拉取消息，自动维护对话上下文
- **兼容主流 LLM 提供商**：OpenAI / Claude / Gemini / Dify / Qwen / Grok / Seed
- **对话历史持久化**：每用户独立存储，重启后保留上下文
- **长回复自动分块**：超出阈值时按段落/句子智能分割，分批发送
- **多模态支持**：图片消息自动下载解密，传递给支持视觉的 LLM
- **并发安全**：同用户消息串行处理，不同用户并行，不互相阻塞
- **会话保护**：token 失效（errcode -14）自动暂停 1 小时，防止无效请求
- **断点续传**：`get_updates_buf` 持久化到磁盘，重启后不丢消息

---

## 快速开始

### 环境要求

- Python 3.9+
- 微信账号（需扫码登录 iLink Bot）

### 安装依赖

```bash
cd ilink-llm-bridge
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

如需运行测试或代码检查，安装开发依赖：

```bash
pip install -r requirements-dev.txt
```

### 第一步：微信扫码登录

```bash
python login.py
```

终端会显示二维码，用手机微信扫描并确认。登录成功后生成 `credentials.json`。

### 第二步：配置

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，填入 LLM 提供商信息：

```yaml
provider:
  name: openai        # 修改此处切换提供商
  api_key: "sk-..."
  model: "gpt-4o"
```

### 第三步：启动

```bash
python -m src.main
```

---

## LLM 提供商配置

### OpenAI

```yaml
provider:
  name: openai
  api_key: "sk-..."
  model: "gpt-4o"
```

### Claude (Anthropic)

```yaml
provider:
  name: claude
  api_key: "sk-ant-..."
  model: "claude-opus-4-5"
  max_tokens: 4096     # 必填
```

### Gemini (Google)

```yaml
provider:
  name: gemini
  api_key: "AIza..."
  model: "gemini-2.0-flash"
```

### Dify

```yaml
provider:
  name: dify
  api_key: "app-..."
  base_url: "https://api.dify.ai/v1"  # 或自托管地址
```

### Qwen（通义千问）

```yaml
provider:
  name: qwen
  api_key: "sk-..."
  model: "qwen-plus"
```

### Grok (xAI)

```yaml
provider:
  name: grok
  api_key: "xai-..."
  model: "grok-3"
```

### Seed（字节跳动豆包）

```yaml
provider:
  name: seed
  api_key: "..."
  model: "doubao-pro-32k"
```

---

## 完整配置说明

```yaml
ilink:
  base_url: ""          # 由 login.py 自动写入
  cdn_base_url: "https://novac2c.cdn.weixin.qq.com/c2c"

provider:
  name: openai
  api_key: "sk-..."
  model: "gpt-4o"
  max_tokens: 2048       # Claude 必填，其他可选
  base_url: ""           # Dify 必填，其他提供商有内置默认值

bot:
  system_prompt: "You are a helpful assistant."
  max_history_length: 20   # 每用户保留的最大消息条数
  chunk_size: 1000          # 超过此字符数自动分段发送
  allow_from: []            # ilink_user_id 白名单，空 = 允许所有人

storage:
  history_dir: "./data/history"
  media_dir: "./data/media"

log:
  level: info              # debug | info | warn | error
```

---

## 项目结构

```
ilink-llm-bridge/
├── login.py                     # 微信扫码登录脚本
├── config.example.yaml          # 配置模板
├── config.yaml                  # 实际配置（gitignore）
├── credentials.json             # 登录凭证（由 login.py 生成，gitignore）
├── pyproject.toml
├── src/
│   ├── main.py                  # 程序入口
│   ├── config/                  # 配置加载与类型定义
│   ├── ilink/                   # iLink API 客户端、会话保护、消息出站
│   ├── cdn/                     # CDN 媒体下载与 AES-128-ECB 解密
│   ├── history/                 # 对话历史管理（内存 + 磁盘）
│   ├── llm/
│   │   ├── providers/           # 7 个 LLM 提供商适配器
│   │   └── registry.py          # 提供商工厂函数
│   ├── bridge/
│   │   ├── loop.py              # 长轮询主循环
│   │   ├── handler.py           # 单条消息处理流程
│   │   └── chunker.py           # 长文本分块
│   └── util/                    # 日志、脱敏工具
└── data/
    ├── history/                 # 对话历史 JSON（运行时创建）
    └── media/                   # 临时媒体文件（运行时创建）
```

---

## 消息处理流程

```
微信消息
  │
  ▼
loop.py: getupdates 长轮询（35s）
  │
  ▼
handler.py: MessageHandler.enqueue()
  ├─ 允许列表过滤
  ├─ 发送"正在输入"状态
  ├─ 提取文本 + 图片（如有）
  ├─ 拼接历史 + 调用 LLM
  ├─ 持久化历史
  ├─ split_chunks() 分块
  └─ 逐块发送（300ms 间隔）
```

---

## 安全说明

- `credentials.json` 和 `config.yaml` 包含敏感凭证，已加入 `.gitignore`
- CDN 媒体通过 AES-128-ECB 加解密传输
- 日志中的 token 和 URL 自动脱敏
- 支持 `allow_from` 白名单限制访问用户

---

## 常见问题

**Q: 登录后 token 失效怎么办？**

重新运行 `python login.py` 获取新的 credentials.json。

**Q: 如何只允许特定用户使用？**

在 `config.yaml` 的 `bot.allow_from` 中填入 ilink_user_id 列表。

**Q: Dify 的对话历史怎么管理？**

Dify 通过 `conversation_id` 在服务端维护上下文，本地只记录文本日志。stale conversation_id 会自动重置重试。

**Q: 如何调试？**

将 `log.level` 设为 `debug`，可查看完整的 HTTP 请求/响应日志。
