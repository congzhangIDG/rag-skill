# CLI-Anything Harness: RAG Skill

这个目录提供 `scripts/rag/` 的 CLI-Anything 封装（harness）。harness 不重写任何 RAG 逻辑，所有能力均委托给 `scripts/rag` Python 包。

## 安装

在仓库根目录执行：

```bash
pip install -r scripts/requirements.txt
pip install -e agent-harness
```

安装完成后会提供命令：`cli-anything-rag-skill`。

## 运行

### REPL（默认）

```bash
cli-anything-rag-skill
```

进入交互式提示符：`rag-skill> `。

### 一次性命令

```bash
cli-anything-rag-skill config show
cli-anything-rag-skill index add README.md
cli-anything-rag-skill index status
cli-anything-rag-skill query search "如何实现分块？"
cli-anything-rag-skill query ask "如何实现分块？"
```

### JSON 输出

所有命令支持 `--json`：

```bash
cli-anything-rag-skill --json index status
```

## 配置

后端配置逻辑与 `scripts/rag/config.py` 一致：

- `--config PATH` 指定配置文件
- 环境变量 `RAG_CONFIG` 指定配置文件
- 默认路径 `~/.claude/skills/rag/config.yaml`

环境变量覆盖同后端：`RAG_EMBEDDING_SERVICE_URL` / `RAG_RERANK_SERVICE_URL` / `RAG_LLM_BASE_URL`。
