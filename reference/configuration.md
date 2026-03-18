# 配置参考

## 配置加载优先级

```
环境变量 > config.yaml > 代码默认值
```

### 配置文件查找顺序

1. `--config <path>` 命令行参数
2. `RAG_CONFIG` 环境变量
3. `~/.claude/skills/rag/config.yaml` 默认路径

## 环境变量

| 环境变量 | 对应配置项 | 说明 |
|----------|-----------|------|
| `RAG_EMBEDDING_SERVICE_URL` | `embedding.service_url` | Embedding 向量化服务地址 |
| `RAG_RERANK_SERVICE_URL` | `rerank.service_url` | Rerank 重排序服务地址（可选） |
| `RAG_LLM_BASE_URL` | `llm.base_url` | LLM 服务地址（OpenAI 兼容接口） |
| `RAG_CONFIG` | — | 配置文件路径 |

## 配置项详解

### embedding

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `service_url` | string | `""` | Embedding 服务 URL（必须通过环境变量或配置提供） |
| `batch_size` | int | `16` | 单次请求的文本数量 |
| `dimension` | int | `768` | 向量维度 |

### rerank

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `service_url` | string | `""` | Rerank 服务 URL（为空则跳过 rerank） |
| `batch_size` | int | `16` | 单次请求的文本数量 |

### chunking

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `chunk_size` | int | `600` | 每个 chunk 的最大字符数 |
| `overlap_size` | int | `100` | 相邻 chunk 的重叠字符数 |

### store

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `persist_dir` | string | `~/.claude/skills/rag/.data/chroma` | ChromaDB 持久化目录 |
| `default_collection` | string | `rag_default` | 默认 collection 名称 |

### llm

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `provider` | string | `openai_compatible` | LLM 提供者类型 |
| `base_url` | string | `""` | LLM 服务 URL（通过环境变量提供） |
| `model` | string | `default` | 模型名称 |
| `temperature` | float | `0.1` | 生成温度 |
| `max_tokens` | int | `2048` | 最大输出 token 数 |

### ingestion

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `code_extensions` | list | 见下方 | 目录索引时允许的代码文件扩展名 |
| `ignore_patterns` | list | 见下方 | 目录索引时跳过的目录名 |
| `max_file_size_mb` | int | `10` | 单文件大小上限（MB） |

默认 `code_extensions`：`.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.go`, `.rs`, `.java`, `.cpp`, `.c`, `.h`, `.cs`, `.rb`, `.php`, `.swift`, `.kt`

默认 `ignore_patterns`：`node_modules`, `.git`, `__pycache__`, `.venv`, `dist`, `build`, `.next`

### retrieval

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `top_k` | int | `10` | 向量检索返回的最大结果数 |
| `rerank_top_k` | int | `5` | Rerank 后保留的结果数 |
