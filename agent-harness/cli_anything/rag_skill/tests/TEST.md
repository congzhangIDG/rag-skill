# 测试计划

## 范围

- 单元测试：核心命令实现（不依赖真实 `scripts/rag` 后端），用 FakeBackend 覆盖：
  - `index add/status` 基本流程
  - `config path` 输出

- 端到端测试：Click CLI 层（不启用 REPL），用 monkeypatch 注入 TinyBackend：
  - `cli-anything-rag-skill --json config show` 输出为 JSON 且 `ok=true`
  - `cli-anything-rag-skill --json index add <source>` 输出包含 `doc_id`

## 不在范围

- 真实 chromadb 持久化与向量检索
- 真实 embedding / rerank / llm 服务联调

## 通过标准

- `pytest` 全绿

## 结果

- 待执行
