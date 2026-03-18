# RAG Skill

基于 ChromaDB 的 RAG (Retrieval-Augmented Generation) 命令行工具。支持对多种数据源建立向量索引并进行语义检索，可选接入 Rerank 和 LLM 服务生成回答。

## 功能

- **多数据源摄取**：文本（`.md`/`.txt`/`.rst`）、代码目录、PDF、DOCX、XLSX、网页、YouTube 视频
- **智能分块**：递归分隔符切分文本，代码按顶层定义（函数/类）边界切分
- **向量检索**：基于 ChromaDB 持久化存储，cosine 相似度匹配
- **可选 Rerank**：通过外部 Rerank 服务对检索结果重排序
- **可选 LLM 回答**：将检索到的上下文发送给 LLM 生成最终答案
- **增量索引**：基于内容哈希自动判断是否需要重新索引

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt

# 可选：PDF/DOCX/XLSX 文档支持、YouTube Whisper 转录
pip install -r requirements-optional.txt
```

### 配置

复制 `.env.example` 为 `.env`，填入实际服务地址：

```bash
cp .env.example .env
```

其余参数（分块大小、batch_size 等）在 `config.yaml` 中调整。

### 使用

```bash
# 索引文本文件
python -m rag.cli index README.md

# 索引代码目录（路径以 / 结尾）
python -m rag.cli index src/

# 索引网页
python -m rag.cli index https://example.com/article

# 索引 YouTube 视频
python -m rag.cli index https://www.youtube.com/watch?v=xxxxx

# 语义检索
python -m rag.cli query "如何实现分块？"

# 查看存储状态
python -m rag.cli status

# 删除已索引文档
python -m rag.cli forget <doc_id>
```

### CLI 参数

| 参数 | 说明 |
|------|------|
| `--config` | 指定配置文件路径 |
| `--collection` | 覆盖默认 collection 名 |
| `--no-rerank` | 禁用 rerank（仅 query） |
| `--no-llm` | 仅输出 chunks JSON，不调用 LLM（仅 query） |

## 配置优先级

环境变量 > `config.yaml` > 代码默认值

| 环境变量 | 对应配置 |
|----------|----------|
| `RAG_EMBEDDING_SERVICE_URL` | `embedding.service_url` |
| `RAG_RERANK_SERVICE_URL` | `rerank.service_url` |
| `RAG_LLM_BASE_URL` | `llm.base_url` |
| `RAG_CONFIG` | 配置文件路径 |

## 项目结构

```
rag/
├── cli.py          # CLI 入口
├── config.py       # 配置加载
├── models.py       # 数据模型与 ID 生成
├── chunker.py      # 文本/代码分块
├── store.py        # ChromaDB 向量存储
├── embedding.py    # Embedding 客户端
├── reranker.py     # Rerank 客户端
├── retriever.py    # 检索器
├── llm.py          # LLM 客户端
└── ingestion/      # 数据源摄取器
```

## 测试

```bash
pytest                                    # 全部测试
pytest tests/test_chunker.py              # 单个文件
pytest tests/test_chunker.py::test_xxx -v # 单个函数
```
