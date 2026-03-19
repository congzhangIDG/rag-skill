# cli-anything-rag-skill

`scripts/rag/` 的 CLI-Anything harness，提供 REPL 与一次性子命令。

## 快速开始

```bash
pip install -r scripts/requirements.txt
pip install -e agent-harness

cli-anything-rag-skill
```

## 命令

### config

```bash
cli-anything-rag-skill config path
cli-anything-rag-skill config show
```

### index

```bash
cli-anything-rag-skill index add <source>
cli-anything-rag-skill index status [--collection NAME]
cli-anything-rag-skill index forget <doc_id>
```

### query

```bash
cli-anything-rag-skill query search <question> [--no-rerank] [--no-llm]
cli-anything-rag-skill query ask <question>
```

## REPL

- `use <collection>`：切换 collection
- `history`：查看历史
- `help`：帮助
- `exit`/`quit`：退出

## JSON 输出

对所有命令加 `--json`：

```bash
cli-anything-rag-skill --json query search "..."
```
