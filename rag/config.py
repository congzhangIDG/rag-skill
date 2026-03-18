from __future__ import annotations

import os
from typing import Any, Dict, Optional

import yaml


def getDefaultConfig() -> Dict[str, Any]:
  return {
    "embedding": {
      "service_url": "",
      "batch_size": 16,
      "dimension": 768,
    },
    "rerank": {
      "service_url": "",
      "batch_size": 16,
    },
    "chunking": {
      "chunk_size": 600,
      "overlap_size": 100,
    },
    "store": {
      "persist_dir": "~/.claude/skills/rag/.data/chroma",
      "default_collection": "rag_default",
    },
    "llm": {
      "provider": "openai_compatible",
      "base_url": "",
      "model": "default",
      "temperature": 0.1,
      "max_tokens": 2048,
    },
    "ingestion": {
      "code_extensions": [
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".go",
        ".rs",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".cs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
      ],
      "ignore_patterns": [
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "dist",
        "build",
        ".next",
      ],
      "max_file_size_mb": 10,
    },
    "retrieval": {
      "top_k": 10,
      "rerank_top_k": 5,
    },
  }


def loadConfig(config_path: Optional[str] = None) -> Dict[str, Any]:
  resolvedPath = _resolveConfigPath(config_path)
  base = getDefaultConfig()

  if resolvedPath is None:
    return _expandPaths(_applyEnvOverrides(base))

  if not os.path.exists(resolvedPath):
    raise FileNotFoundError(f"配置文件不存在: {resolvedPath}")

  with open(resolvedPath, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}
  if not isinstance(data, dict):
    raise ValueError("配置文件格式错误：期望 YAML 顶层为对象")

  merged = _deepMerge(base, data)
  return _expandPaths(_applyEnvOverrides(merged))


def _resolveConfigPath(config_path: Optional[str]) -> Optional[str]:
  if config_path:
    return os.path.abspath(os.path.expanduser(config_path))

  envPath = os.environ.get("RAG_CONFIG")
  if envPath:
    return os.path.abspath(os.path.expanduser(envPath))

  defaultPath = os.path.expanduser("~/.claude/skills/rag/config.yaml")
  defaultPath = os.path.abspath(defaultPath)
  if os.path.exists(defaultPath):
    return defaultPath
  return None


def _deepMerge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
  out: Dict[str, Any] = {}
  for k, v in base.items():
    out[k] = v

  for k, v in override.items():
    if isinstance(v, dict) and isinstance(out.get(k), dict):
      out[k] = _deepMerge(out.get(k) or {}, v)
    else:
      out[k] = v
  return out


def _expandPaths(config: Dict[str, Any]) -> Dict[str, Any]:
  store = config.get("store")
  if isinstance(store, dict):
    persistDir = store.get("persist_dir")
    if isinstance(persistDir, str):
      store["persist_dir"] = os.path.expanduser(persistDir)
  return config


_ENV_OVERRIDES = (
  ("RAG_EMBEDDING_SERVICE_URL", "embedding", "service_url"),
  ("RAG_RERANK_SERVICE_URL", "rerank", "service_url"),
  ("RAG_LLM_BASE_URL", "llm", "base_url"),
)


def _applyEnvOverrides(config: Dict[str, Any]) -> Dict[str, Any]:
  for envKey, section, field in _ENV_OVERRIDES:
    val = os.environ.get(envKey)
    if val:
      if section not in config or not isinstance(config[section], dict):
        config[section] = {}
      config[section][field] = val
  return config
