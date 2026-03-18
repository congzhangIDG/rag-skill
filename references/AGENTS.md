# AGENTS.md — rag-skill

## 项目概述

RAG (Retrieval-Augmented Generation) CLI 工具，支持多种数据源（文本、代码、PDF、DOCX、XLSX、网页、YouTube）的索引与检索。基于 ChromaDB 向量存储，通过外部 Embedding/Rerank/LLM 服务实现完整 RAG 流程。

## 项目结构

```
scripts/rag/
├── __init__.py          # 版本号
├── cli.py               # CLI 入口、命令处理（index/query/status/forget）
├── config.py            # YAML 配置加载、环境变量覆盖、深度合并
├── models.py            # 数据模型（DocumentMeta、ChunkMeta）、ID 生成
├── chunker.py           # 文本/代码分块（递归分隔符 + 代码边界检测）
├── store.py             # ChromaDB 向量存储（FileLock 并发保护）
├── embedding.py         # Embedding 服务客户端（带重试）
├── reranker.py          # Rerank 服务客户端（带重试）
├── retriever.py         # 检索器（向量查询 + 可选 rerank + LLM 回答）
├── llm.py               # LLM 客户端（OpenAI 兼容接口）
└── ingestion/
    ├── base.py           # IngestedDocument 数据类、BaseIngester 抽象基类
    ├── text.py           # 文本文件摄取
    ├── code.py           # 代码目录摄取
    ├── web.py            # 网页摄取（trafilatura）
    ├── youtube.py        # YouTube 视频摄取
    └── document.py       # PDF/DOCX/XLSX 摄取
```

## 构建与测试

所有命令在 `scripts/` 目录下执行：

```bash
cd scripts/

# 安装依赖
pip install -r requirements.txt

# 可选依赖（文档处理、Whisper 等）
pip install -r requirements-optional.txt

# 运行全部测试
pytest

# 运行单个测试文件
pytest tests/test_chunker.py

# 运行单个测试函数
pytest tests/test_chunker.py::test_function_name -v

# 运行匹配关键字的测试
pytest -k "keyword" -v
```

**注意**：`scripts/pyproject.toml` 配置了 `testpaths = ["tests"]`、`pythonpath = ["."]`。项目无 linter/formatter 配置，无 CI 流水线。

## 配置机制

- YAML 配置路径优先级：`--config` 参数 > `RAG_CONFIG` 环境变量 > `~/.claude/skills/rag/config.yaml`
- URL 通过环境变量注入（参见 `assets/.env.example`）：
  - `RAG_EMBEDDING_SERVICE_URL` → `embedding.service_url`
  - `RAG_RERANK_SERVICE_URL` → `rerank.service_url`
  - `RAG_LLM_BASE_URL` → `llm.base_url`
- 优先级：环境变量 > config.yaml > 代码默认值

## 代码风格

### 缩进

**2 空格缩进**，全项目统一。

### 命名约定

| 元素 | 风格 | 示例 |
|------|------|------|
| 局部变量 | camelCase | `serviceUrl`, `batchSize`, `lastError` |
| 函数（公开） | camelCase | `loadConfig()`, `embedTexts()`, `generateDocId()` |
| 函数（私有） | `_` 前缀 + camelCase | `_deepMerge()`, `_requestBatch()`, `_parseVectors()` |
| 类 | PascalCase | `VectorStore`, `EmbeddingClient`, `ChunkMeta` |
| 异常类 | PascalCase + Error/Exception | `EmbeddingAPIError`, `LLMTimeoutError` |
| 常量/模块级数据 | UPPER_SNAKE_CASE | `DEFAULT_SEPARATORS`, `_ENV_OVERRIDES` |
| 函数参数 | snake_case | `service_url`, `batch_size`, `chunk_size` |
| dataclass 字段 | snake_case | `doc_id`, `source_uri`, `chunk_index` |

**关键规则**：参数用 snake_case，赋值给实例属性后转 camelCase：
```python
def __init__(self, service_url: str, batch_size: int = 16):
  self.serviceUrl = service_url
  self.batchSize = batch_size
```

### 导入

1. `from __future__ import annotations` 放首行（大部分文件都有）
2. 标准库 → 空行 → 第三方库 → 空行 → 项目内模块
3. 使用**绝对导入**：`from rag.ingestion.base import BaseIngester`
4. CLI 中使用**延迟导入**（在函数体内 import），减少启动开销

```python
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests

from rag.ingestion.base import BaseIngester, IngestedDocument
```

### 类型标注

- 使用 `typing` 模块：`Dict[str, Any]`, `List[str]`, `Optional[str]`
- 有 `from __future__ import annotations` 的文件也用 `list[str]` 小写形式
- 函数参数和返回值标注类型，局部变量通常不标注（除非需要显式声明）
- 不使用 `as any`、`# type: ignore`（仅 `store.py` 中 `pysqlite3` 导入例外）

### 数据模型

- 用 `@dataclass` 定义数据结构（`ChunkMeta`, `DocumentMeta`, `IngestedDocument`, `RetrievalResult`）
- 用 `namedtuple` 定义轻量元组（`ChunkSpan`）
- 不使用 Pydantic

### 错误处理

每个客户端模块定义独立的异常层级：
```
embedding.py: EmbeddingTimeoutError, EmbeddingAPIError, EmbeddingDimensionError, EmbeddingParseError
reranker.py:  RerankTimeoutError, RerankAPIError, RerankParseError
llm.py:       LLMError → LLMTimeoutError, LLMAPIError, LLMParseError
```

模式：
- 网络请求带 3 次重试 + `time.sleep(1)` 退避
- API 错误和解析错误立即抛出不重试
- 超时/连接错误重试后抛出最后一个错误
- 用户错误消息用中文：`raise RuntimeError("摄取结果无效")`

### 字符串

- 双引号 `"` 为主
- 中文错误消息和提示信息

## 关键模式

### API 客户端结构

```python
class XxxClient:
  def __init__(self, service_url: str, batch_size: int = 16, timeout: int = 60):
    self.serviceUrl = service_url
    self.batchSize = batch_size
    self.timeout = timeout

  def publicMethod(self, inputs): ...      # 对外接口，分批处理
  def _requestBatch(self, batch): ...      # 单批请求，含重试逻辑
  def _parseResponse(self, data): ...      # 响应解析与验证
```

### 资源管理

- `VectorStore` 实现 `close()` 方法，调用方用 `try/finally` 确保关闭
- `FileLock` 保护写操作（upsert、delete）

### 摄取器接口

继承 `BaseIngester`，实现 `canHandle(source) -> bool` 和 `ingest(source) -> IngestedDocument`。

## 禁止事项

- 不要用 4 空格缩进
- 不要用 snake_case 命名局部变量和方法（参数除外）
- 不要引入新的格式化工具或 linter 配置
- 不要使用 `@ts-ignore` / `type: ignore`（pysqlite3 例外）
- 不要在 catch 块中吞掉异常
- 不要修改环境变量覆盖的优先级顺序
