from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def _ensureScriptsOnPath() -> str:
  here = os.path.abspath(os.path.dirname(__file__))
  repoRoot = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
  scriptsDir = os.path.join(repoRoot, "scripts")
  if scriptsDir not in sys.path:
    sys.path.insert(0, scriptsDir)
  return scriptsDir


def _requireBackend() -> None:
  _ensureScriptsOnPath()
  try:
    import rag  # noqa: F401
  except Exception as e:
    raise RuntimeError(
      "无法导入 scripts/rag 后端包（import rag 失败）。"
      "请确认已在仓库内安装依赖，并且通过 pip install -e agent-harness 安装了 harness。"
    ) from e


@dataclass
class BackendPaths:
  scriptsDir: str


class RagBackend:
  def __init__(self) -> None:
    scriptsDir = _ensureScriptsOnPath()
    self.paths = BackendPaths(scriptsDir=scriptsDir)
    _requireBackend()

  def loadConfig(self, config_path: Optional[str] = None) -> Dict[str, Any]:
    from rag.config import loadConfig

    return loadConfig(config_path)

  def resolveConfigPath(self, config_path: Optional[str] = None) -> Optional[str]:
    from rag import config as configMod

    fn = getattr(configMod, "_resolveConfigPath", None)
    if not callable(fn):
      return None
    return fn(config_path)

  def detectSourceType(self, input_path: str) -> str:
    from rag.cli import detectSourceType

    return detectSourceType(input_path)

  def ingest(self, sourceType: str, source: str, cfg: Dict[str, Any]) -> Any:
    from rag import cli as cliMod

    ingestFn = getattr(cliMod, "_ingest", None)
    if not callable(ingestFn):
      raise RuntimeError("后端缺少 rag.cli._ingest")
    return ingestFn(sourceType, source, cfg)

  def generateDocId(self, source_uri: str, content_bytes: bytes) -> str:
    from rag.models import generateDocId

    return generateDocId(source_uri, content_bytes)

  def generateDocVersion(self, content_bytes: bytes) -> str:
    from rag.models import generateDocVersion

    return generateDocVersion(content_bytes)

  def generateChunkId(self, doc_id: str, chunk_index: int, chunk_text: str) -> str:
    from rag.models import generateChunkId

    return generateChunkId(doc_id, chunk_index, chunk_text)

  def createChunkMeta(
    self,
    chunk_id: str,
    doc_id: str,
    doc_version: str,
    source_type: str,
    source_uri: str,
    title: str,
    chunk_index: int,
    char_start: int,
    char_end: int,
    text: str,
  ) -> Any:
    from rag.models import ChunkMeta

    return ChunkMeta(
      chunk_id=chunk_id,
      doc_id=doc_id,
      doc_version=doc_version,
      source_type=source_type,
      source_uri=source_uri,
      title=title,
      chunk_index=int(chunk_index),
      char_start=int(char_start),
      char_end=int(char_end),
      text=text,
    )

  def detectLanguage(self, file_path: str) -> str:
    from rag.chunker import detectLanguage

    return detectLanguage(file_path)

  def splitTextChunks(self, text: str, chunk_size: int, overlap: int) -> List[Any]:
    from rag.chunker import splitTextChunks

    return splitTextChunks(text, chunk_size=chunk_size, overlap=overlap)

  def splitCodeChunks(self, text: str, language: str, chunk_size: int, overlap: int) -> List[Any]:
    from rag.chunker import splitCodeChunks

    return splitCodeChunks(text, language=language, chunk_size=chunk_size, overlap=overlap)

  def createVectorStore(self, persist_dir: str, collection_name: str):
    from rag.store import VectorStore

    return VectorStore(persist_dir=persist_dir, collection_name=collection_name)

  def createEmbeddingClient(self, service_url: str, batch_size: int, dimension: int, timeout: Optional[float] = None):
    from rag.embedding import EmbeddingClient

    kwargs: Dict[str, Any] = {
      "service_url": service_url,
      "batch_size": batch_size,
      "dimension": dimension,
    }
    if timeout is not None:
      kwargs["timeout"] = timeout
    return EmbeddingClient(**kwargs)

  def createRerankClient(self, service_url: str, batch_size: int):
    from rag.reranker import RerankClient

    return RerankClient(service_url=service_url, batch_size=batch_size)

  def createRetriever(
    self,
    store: Any,
    embedding_client: Any,
    rerank_client: Optional[Any],
    top_k: int,
    rerank_top_k: int,
  ):
    from rag.retriever import Retriever

    return Retriever(
      store=store,
      embedding_client=embedding_client,
      rerank_client=rerank_client,
      top_k=top_k,
      rerank_top_k=rerank_top_k,
    )

  def createLlmClient(
    self,
    base_url: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: Optional[float] = None,
  ):
    from rag.llm import LLMClient

    kwargs: Dict[str, Any] = {
      "base_url": base_url,
      "model": model,
      "temperature": temperature,
      "max_tokens": max_tokens,
    }
    if timeout is not None:
      kwargs["timeout"] = timeout
    return LLMClient(**kwargs)
