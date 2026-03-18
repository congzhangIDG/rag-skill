# API 参考

## CLI 命令

所有命令通过 `python -m rag.cli` 调用。

### index — 索引文档

```bash
python -m rag.cli index <input> [--collection <name>] [--config <path>]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `<input>` | 位置参数 | 是 | 文件路径、目录路径或 URL |
| `--collection` | 可选 | 否 | 覆盖默认 collection 名称 |
| `--config` | 可选 | 否 | 指定配置文件路径 |

**支持的输入类型：**

| 类型 | 识别方式 | 示例 |
|------|----------|------|
| 文本 | `.md`, `.txt`, `.rst` | `~/docs/note.md` |
| 代码 | 单文件或目录 | `src/` |
| PDF | `.pdf` | `report.pdf` |
| DOCX | `.docx` | `contract.docx` |
| XLSX | `.xlsx` | `data.xlsx` |
| 网页 | `http(s)://` | `https://example.com` |
| YouTube | `youtube.com`, `youtu.be` | `https://youtube.com/watch?v=xxx` |

**输出格式：**
```
documents=1 chunks=N upserts=N
```

### query — 检索查询

```bash
python -m rag.cli query "<question>" [--collection <name>] [--no-rerank] [--no-llm] [--config <path>]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `<question>` | 位置参数 | 是 | 查询文本 |
| `--collection` | 可选 | 否 | 覆盖默认 collection 名称 |
| `--no-rerank` | 标志 | 否 | 禁用 rerank |
| `--no-llm` | 标志 | 否 | 仅输出 chunks JSON |
| `--config` | 可选 | 否 | 指定配置文件路径 |

**输出格式（JSON 数组）：**
```json
[
  {
    "text": "chunk 文本内容",
    "score": 0.85,
    "source_uri": "~/docs/note.md",
    "chunk_id": "abc123",
    "source_type": "text",
    "title": "note.md",
    "chunk_index": 0
  }
]
```

### status — 查看索引状态

```bash
python -m rag.cli status [--collection <name>] [--config <path>]
```

**输出格式（JSON 对象）：**
```json
{
  "status": { "total_chunks": 42 },
  "documents": [
    { "doc_id": "abc123", "source_uri": "~/docs/note.md", "chunks": 5 }
  ]
}
```

### forget — 删除文档

```bash
python -m rag.cli forget <doc_id> [--collection <name>] [--config <path>]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `<doc_id>` | 位置参数 | 是 | 文档 ID（从 status 命令获取） |

**输出格式：**
```
deleted=N doc_id=<id>
```

## 数据模型

### DocumentMeta

文档元数据，索引时自动生成。

| 字段 | 类型 | 说明 |
|------|------|------|
| `doc_id` | str | 基于来源 URI 的哈希 ID |
| `source_uri` | str | 原始路径或 URL |
| `source_type` | str | `text` / `code` / `web` / `youtube` / `pdf` / `docx` / `xlsx` |
| `title` | str | 文档标题 |

### ChunkMeta

单个 chunk 的元数据。

| 字段 | 类型 | 说明 |
|------|------|------|
| `chunk_id` | str | 基于 doc_id + chunk_index 的哈希 ID |
| `doc_id` | str | 所属文档 ID |
| `chunk_index` | int | 在文档中的序号 |
| `source_uri` | str | 原始路径或 URL |
| `source_type` | str | 数据源类型 |
| `title` | str | 文档标题 |
| `content_hash` | str | 内容哈希（用于增量索引判断） |

## 异常类型

### embedding.py

| 异常 | 场景 |
|------|------|
| `EmbeddingTimeoutError` | 请求超时（3 次重试后） |
| `EmbeddingAPIError` | API 返回错误状态码 |
| `EmbeddingDimensionError` | 返回向量维度不匹配 |
| `EmbeddingParseError` | 响应 JSON 解析失败 |

### reranker.py

| 异常 | 场景 |
|------|------|
| `RerankTimeoutError` | 请求超时（3 次重试后） |
| `RerankAPIError` | API 返回错误状态码 |
| `RerankParseError` | 响应解析失败 |

### llm.py

| 异常 | 场景 |
|------|------|
| `LLMError` | 基类 |
| `LLMTimeoutError` | 请求超时 |
| `LLMAPIError` | API 错误 |
| `LLMParseError` | 响应解析失败 |
