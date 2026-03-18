---
name: rag
description: "本地 RAG 知识库——索引文档、检索回答、管理知识。触发词：/rag-index、/rag-query、/rag-status、/rag-forget，或当用户说'搜索知识库'、'索引这个文件'、'记住这个'等。"
allowed-tools:
  - Bash
  - Read
  - Write
---

# RAG Skill（本地知识库）

用本地向量库管理你的"可检索知识"：把文件/网页/视频等内容索引进库，再按问题检索出相关片段（JSON 输出）。

> 注意：索引与检索会把文本发送到**远程 embedding**（以及可选的 rerank）服务进行向量化/重排，请确认数据合规。

## 触发条件

### 显式触发

- `/rag-index`
- `/rag-query`
- `/rag-status`
- `/rag-forget`

### 自然语言触发（例）

- "搜索知识库 / 查一下知识库 / 从知识库找"
- "索引这个文件 / 索引这个目录 / 记住这个"
- "索引这个 URL / 记住这篇文章"
- "把这个 YouTube 视频内容记下来"
- "忘掉这个文档 / 删除这条知识"

## 前置检查（每次执行前确认）

1. Python 3.10+ 可用
2. 运行安装脚本（推荐）：

```bash
# Linux / macOS
bash ~/.claude/skills/rag/scripts/install.sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File ~/.claude/skills/rag/scripts/install.ps1
```

3. 或手动安装基础依赖：

```bash
pip install -r ~/.claude/skills/rag/scripts/requirements.txt
```

4. 安装可选依赖（PDF/Word/Excel 支持）：

```bash
bash ~/.claude/skills/rag/scripts/install.sh --with-docs
```

5. 可选：若你启用 YouTube Whisper 转录路径，通常需要 `ffmpeg`：

```bash
# macOS
brew install ffmpeg
```

## 运行约定

- 所有 Bash 命令的 `workdir`：`~/.claude/skills/rag/scripts/`
- CLI 入口：`python -m rag.cli ...`
- 配置加载优先级：
  1) `--config <path>` → 2) `RAG_CONFIG` → 3) `~/.claude/skills/rag/config.yaml` → 4) 内置默认

> 关键点：`input`、`query`、`doc_id` 是 **位置参数**。不要写成 `--input/--question/--doc-id`。

---

## /rag-index — 索引文档

### 目的

摄取输入 → 切分 chunks → 调 embedding 向量化 → 写入本地向量库（Chroma）。

### 参数

- `<input>`（必需）：路径或 URL
- `--collection <name>`（可选）：覆盖默认 collection
- `--config <path>`（可选）：指定配置文件

### 命令模板

```bash
python -m rag.cli index <input> [--collection <name>] [--config <path>]
```

### 支持数据源（自动识别类型）

- 文本：`.md` / `.txt` / `.rst`
- 代码：单文件或目录（目录会递归收集，受 `ingestion.code_extensions` / `ingestion.ignore_patterns` 控制）
- 文档：`.pdf` / `.docx` / `.xlsx`（需要可选依赖）
- 网页：`http(s)://...`
- YouTube：`youtube.com` / `youtu.be`

### 输出解读

```text
documents=1 chunks=N upserts=N
```

- `chunks`：切分得到的 chunk 数
- `upserts`：实际写入/更新的 chunk 数

增量索引：若内容未变化，会输出 `upserts=0`（跳过更新）。

---

## /rag-query — 检索查询

### 参数

- `<query>`（必需）：查询文本
- `--collection <name>`（可选）
- `--no-rerank`（可选）：禁用 rerank
- `--no-llm`（可选）：仅输出 chunks JSON（当前实现始终输出 JSON；该开关为工作流预留）
- `--config <path>`（可选）

### 命令模板

```bash
python -m rag.cli query "<question>" [--collection <name>] [--no-rerank] [--no-llm] [--config <path>]
```

### 输出

JSON 数组，每项包含（字段以实际输出为准）：

- `text`：chunk 文本
- `score`：相关性分数
- `source_uri`：来源（文件路径/URL/YouTube 等）
- 以及 `chunk_id`、`source_type`、`title`、`chunk_index`

---

## /rag-status — 查看索引状态

### 参数

- `--collection <name>`（可选）
- `--config <path>`（可选）

### 命令模板

```bash
python -m rag.cli status [--collection <name>] [--config <path>]
```

### 输出

JSON 对象：

- `status`：存储状态（例如 chunk 总数等）
- `documents`：文档列表（用于定位 `doc_id`）

---

## /rag-forget — 删除文档

### 参数

- `<doc_id>`（必需）
- `--collection <name>`（可选）
- `--config <path>`（可选）

### 命令模板

```bash
python -m rag.cli forget <doc_id> [--collection <name>] [--config <path>]
```

### 输出解读

```text
deleted=N doc_id=<id>
```

---

## 使用示例

### 索引本地文件

用户: "帮我索引这个文件 ~/docs/report.pdf"

→ Bash(workdir="~/.claude/skills/rag/scripts/"):

```bash
python -m rag.cli index ~/docs/report.pdf
```

### 索引网页

用户: "记住这篇文章 https://example.com/article"

→ Bash(workdir="~/.claude/skills/rag/scripts/"):

```bash
python -m rag.cli index https://example.com/article
```

### 索引 YouTube 视频

用户: "把这个视频的内容记下来 https://youtube.com/watch?v=abc123"

→ Bash(workdir="~/.claude/skills/rag/scripts/"):

```bash
python -m rag.cli index https://youtube.com/watch?v=abc123
```

### 检索

用户: "搜索知识库：什么是向量检索？"

→ Bash(workdir="~/.claude/skills/rag/scripts/"):

```bash
python -m rag.cli query "什么是向量检索？"
```

### 查看状态

用户: "/rag-status"

→ Bash(workdir="~/.claude/skills/rag/scripts/"):

```bash
python -m rag.cli status
```

### 删除文档

用户: "/rag-forget abc123"

→ Bash(workdir="~/.claude/skills/rag/scripts/"):

```bash
python -m rag.cli forget abc123
```

---

## 目录结构

```
~/.claude/skills/rag/
├── SKILL.md                       # 本文件（Skill 总控说明）
├── README.md                      # 项目说明
├── scripts/
│   ├── rag/                       # Python 源码包
│   ├── tests/                     # 测试
│   ├── install.sh                 # Linux/macOS 安装脚本
│   ├── install.ps1                # Windows 安装脚本
│   ├── requirements.txt           # 基础依赖
│   ├── requirements-optional.txt  # 可选依赖
│   └── pyproject.toml             # 项目配置
├── assets/
│   ├── config.yaml.template       # 配置文件模板
│   └── .env.example               # 环境变量模板
└── references/
    ├── AGENTS.md                  # AI 代理编码规范
    ├── api.md                     # CLI 命令与数据模型参考
    └── configuration.md           # 配置项详解
```

## 安装指南

```bash
# 推荐：使用安装脚本（自动安装依赖 + 初始化配置）
bash ~/.claude/skills/rag/scripts/install.sh

# 安装全部依赖（含文档处理 + Whisper）
bash ~/.claude/skills/rag/scripts/install.sh --all

# 手动安装
pip install -r ~/.claude/skills/rag/scripts/requirements.txt
```

---

## 故障排除（常见问题）

1) **ChromaDB 初始化失败**：检查 `store.persist_dir` 是否可读写、路径是否存在。

2) **Embedding 服务不可达**：检查 `embedding.service_url`，确认当前网络可访问（内网/VPN/代理）。

3) **PDF/Word/Excel 不支持**：运行 `bash scripts/install.sh --with-docs`，否则会提示摄取适配器未就绪。

4) **YouTube 无字幕/抓取失败**：视频可能无可用字幕；若启用 Whisper 路径，安装 `ffmpeg`。

5) **索引不更新**：内容相同会增量跳过（`upserts=0`）；修改内容后重新索引。
