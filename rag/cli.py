from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


def detectSourceType(input_path: str) -> str:
  s = (input_path or "").strip()
  if not s:
    return "text"

  if re.match(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/", s, re.IGNORECASE):
    return "youtube"

  parsed = urlparse(s)
  if parsed.scheme in ("http", "https"):
    return "web"

  lower = s.lower()
  if lower.endswith("/") or lower.endswith("\\"):
    return "code"

  _, ext = os.path.splitext(lower)
  if ext == ".pdf":
    return "pdf"
  if ext == ".docx":
    return "docx"
  if ext == ".xlsx":
    return "xlsx"
  if ext in {".md", ".txt", ".rst"}:
    return "text"
  if ext in {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".cpp", ".c", ".h", ".cs", ".rb", ".php", ".swift", ".kt"}:
    return "code"

  return "text"


def buildParser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(prog="rag", description="RAG CLI")
  parser.add_argument("--config", dest="config", default=None, help="配置文件路径")

  sub = parser.add_subparsers(dest="command", required=True)

  indexParser = sub.add_parser("index", help="索引/更新文档")
  indexParser.add_argument("input", help="输入路径或 URL")
  indexParser.add_argument("--collection", default=None, help="覆盖默认 collection")
  indexParser.set_defaults(func=handleIndex)

  queryParser = sub.add_parser("query", help="检索查询")
  queryParser.add_argument("query", help="查询文本")
  queryParser.add_argument("--collection", default=None, help="覆盖默认 collection")
  queryParser.add_argument("--no-rerank", action="store_true", help="禁用 rerank")
  queryParser.add_argument("--no-llm", action="store_true", help="仅输出 chunks JSON")
  queryParser.set_defaults(func=handleQuery)

  statusParser = sub.add_parser("status", help="查看存储状态")
  statusParser.add_argument("--collection", default=None, help="覆盖默认 collection")
  statusParser.set_defaults(func=handleStatus)

  forgetParser = sub.add_parser("forget", help="删除指定 doc_id")
  forgetParser.add_argument("doc_id", help="文档 doc_id")
  forgetParser.add_argument("--collection", default=None, help="覆盖默认 collection")
  forgetParser.set_defaults(func=handleForget)

  return parser


def main(argv: Optional[List[str]] = None) -> int:
  parser = buildParser()
  args = parser.parse_args(argv)
  func = getattr(args, "func", None)
  if not callable(func):
    parser.print_help()
    return 2

  try:
    func(args)
    return 0
  except KeyboardInterrupt:
    return 130
  except Exception as e:
    print(str(e), file=sys.stderr)
    return 2


def handleIndex(args: argparse.Namespace) -> None:
  from rag.config import loadConfig
  from rag.models import ChunkMeta, generateChunkId, generateDocId, generateDocVersion
  from rag.chunker import detectLanguage, splitCodeChunks, splitTextChunks
  from rag.ingestion.base import IngestedDocument

  cfg = loadConfig(getattr(args, "config", None))
  source = str(getattr(args, "input"))
  sourceType = detectSourceType(source)

  ingested = _ingest(sourceType, source, cfg)
  if not isinstance(ingested, IngestedDocument):
    raise RuntimeError("摄取结果无效")

  docId = generateDocId(ingested.source_uri, ingested.content_bytes)
  docVersion = generateDocVersion(ingested.content_bytes)

  chunkingCfg = cfg.get("chunking") or {}
  chunkSize = int(chunkingCfg.get("chunk_size", 600) or 600)
  overlapSize = int(chunkingCfg.get("overlap_size", 100) or 100)

  if ingested.source_type == "code" and os.path.isfile(source):
    lang = detectLanguage(source)
    spans = splitCodeChunks(ingested.text, language=lang, chunk_size=chunkSize, overlap=overlapSize)
  else:
    spans = splitTextChunks(ingested.text, chunk_size=chunkSize, overlap=overlapSize)

  chunks: List[ChunkMeta] = []
  for i, span in enumerate(spans):
    chunkId = generateChunkId(docId, i, span.text)
    chunks.append(
      ChunkMeta(
        chunk_id=chunkId,
        doc_id=docId,
        doc_version=docVersion,
        source_type=ingested.source_type,
        source_uri=ingested.source_uri,
        title=ingested.title,
        chunk_index=i,
        char_start=int(span.char_start),
        char_end=int(span.char_end),
        text=span.text,
      )
    )

  storeCfg = cfg.get("store") or {}
  persistDir = str(storeCfg.get("persist_dir") or "")
  defaultCollection = str(storeCfg.get("default_collection") or "rag_default")
  collectionName = str(getattr(args, "collection", None) or defaultCollection)

  embeddingCfg = cfg.get("embedding") or {}
  serviceUrl = str(embeddingCfg.get("service_url") or "")
  batchSize = int(embeddingCfg.get("batch_size", 16) or 16)
  dimension = int(embeddingCfg.get("dimension", 768) or 768)

  store = None
  try:
    from rag.store import VectorStore
    from rag.embedding import EmbeddingClient

    store = VectorStore(persist_dir=persistDir, collection_name=collectionName)
    if not store.shouldReindex(docId, docVersion):
      print(f"documents=1 chunks={len(chunks)} upserts=0")
      return

    store.deleteByDocId(docId)
    embeddingClient = EmbeddingClient(service_url=serviceUrl, batch_size=batchSize, dimension=dimension)
    embeddings = embeddingClient.embedTexts([c.text for c in chunks])
    upserts = store.upsertChunks(chunks, embeddings)
    print(f"documents=1 chunks={len(chunks)} upserts={upserts}")
  finally:
    if store is not None:
      closeFn = getattr(store, "close", None)
      if callable(closeFn):
        closeFn()


def handleQuery(args: argparse.Namespace) -> None:
  from rag.config import loadConfig

  cfg = loadConfig(getattr(args, "config", None))
  storeCfg = cfg.get("store") or {}
  persistDir = str(storeCfg.get("persist_dir") or "")
  defaultCollection = str(storeCfg.get("default_collection") or "rag_default")
  collectionName = str(getattr(args, "collection", None) or defaultCollection)

  embeddingCfg = cfg.get("embedding") or {}
  embedUrl = str(embeddingCfg.get("service_url") or "")
  embedBatch = int(embeddingCfg.get("batch_size", 16) or 16)
  dimension = int(embeddingCfg.get("dimension", 768) or 768)

  retrievalCfg = cfg.get("retrieval") or {}
  topK = int(retrievalCfg.get("top_k", 10) or 10)
  rerankTopK = int(retrievalCfg.get("rerank_top_k", 5) or 5)

  rerankClient = None
  if not bool(getattr(args, "no_rerank", False)):
    rerankCfg = cfg.get("rerank") or {}
    rerankUrl = str(rerankCfg.get("service_url") or "")
    rerankBatch = int(rerankCfg.get("batch_size", 16) or 16)
    if rerankUrl:
      from rag.reranker import RerankClient

      rerankClient = RerankClient(service_url=rerankUrl, batch_size=rerankBatch)

  store = None
  try:
    from rag.store import VectorStore
    from rag.embedding import EmbeddingClient
    from rag.retriever import Retriever

    store = VectorStore(persist_dir=persistDir, collection_name=collectionName)
    embeddingClient = EmbeddingClient(service_url=embedUrl, batch_size=embedBatch, dimension=dimension)
    retriever = Retriever(
      store=store,
      embedding_client=embeddingClient,
      rerank_client=rerankClient,
      top_k=topK,
      rerank_top_k=rerankTopK,
    )
    results = retriever.retrieve(str(getattr(args, "query")))

    payload: List[Dict[str, Any]] = []
    for r in results:
      payload.append({
        "chunk_id": r.chunk_id,
        "text": r.text,
        "score": r.score,
        "source_uri": r.source_uri,
        "source_type": r.source_type,
        "title": r.title,
        "chunk_index": r.chunk_index,
      })

    print(json.dumps(payload, ensure_ascii=False))
  finally:
    if store is not None:
      closeFn = getattr(store, "close", None)
      if callable(closeFn):
        closeFn()


def handleStatus(args: argparse.Namespace) -> None:
  from rag.config import loadConfig

  cfg = loadConfig(getattr(args, "config", None))
  storeCfg = cfg.get("store") or {}
  persistDir = str(storeCfg.get("persist_dir") or "")
  defaultCollection = str(storeCfg.get("default_collection") or "rag_default")
  collectionName = str(getattr(args, "collection", None) or defaultCollection)

  store = None
  try:
    from rag.store import VectorStore

    store = VectorStore(persist_dir=persistDir, collection_name=collectionName)
    status = store.getStatus()
    docs = store.listDocuments()
    print(json.dumps({"status": status, "documents": docs}, ensure_ascii=False))
  finally:
    if store is not None:
      closeFn = getattr(store, "close", None)
      if callable(closeFn):
        closeFn()


def handleForget(args: argparse.Namespace) -> None:
  from rag.config import loadConfig

  cfg = loadConfig(getattr(args, "config", None))
  storeCfg = cfg.get("store") or {}
  persistDir = str(storeCfg.get("persist_dir") or "")
  defaultCollection = str(storeCfg.get("default_collection") or "rag_default")
  collectionName = str(getattr(args, "collection", None) or defaultCollection)

  docId = str(getattr(args, "doc_id"))
  store = None
  try:
    from rag.store import VectorStore

    store = VectorStore(persist_dir=persistDir, collection_name=collectionName)
    deleted = store.deleteByDocId(docId)
    print(f"deleted={deleted} doc_id={docId}")
  finally:
    if store is not None:
      closeFn = getattr(store, "close", None)
      if callable(closeFn):
        closeFn()


def _ingest(sourceType: str, source: str, cfg: Dict[str, Any]):
  creator = _getIngesterCreator(sourceType)
  if creator is None:
    if sourceType == "code":
      return _fallbackIngestCode(source, cfg)
    raise RuntimeError(f"不支持的数据源类型: {sourceType}")

  ingester = creator(cfg)
  canHandle = getattr(ingester, "canHandle", None)
  if callable(canHandle) and not canHandle(source):
    raise RuntimeError(f"摄取器无法处理输入: {source}")

  ingestFn = getattr(ingester, "ingest", None)
  if not callable(ingestFn):
    raise RuntimeError("摄取器缺少 ingest 方法")
  return ingestFn(source)


def _getIngesterCreator(sourceType: str):
  if sourceType == "text":
    return _createTextIngester
  if sourceType == "code":
    return _tryCreateAdapter("rag.ingestion.code", "CodeIngester")
  if sourceType == "pdf":
    return _tryCreateAdapter("rag.ingestion.document", "PdfIngester")
  if sourceType == "docx":
    return _tryCreateAdapter("rag.ingestion.document", "DocxIngester")
  if sourceType == "xlsx":
    return _tryCreateAdapter("rag.ingestion.document", "XlsxIngester")
  if sourceType == "web":
    return _tryCreateAdapter("rag.ingestion.web", "WebIngester")
  if sourceType == "youtube":
    return _tryCreateAdapter("rag.ingestion.youtube", "YoutubeIngester")
  return None


def _tryCreateAdapter(moduleName: str, className: str):
  def creator(_: Dict[str, Any]):
    try:
      import importlib

      mod = importlib.import_module(moduleName)
      cls = getattr(mod, className)
      return cls()
    except ImportError as e:
      raise RuntimeError(f"摄取适配器未就绪: {moduleName}.{className}") from e
    except AttributeError as e:
      raise RuntimeError(f"摄取适配器未实现: {moduleName}.{className}") from e

  return creator


def _createTextIngester(_: Dict[str, Any]):
  try:
    from rag.ingestion.text import TextIngester

    return TextIngester()
  except ImportError as e:
    raise RuntimeError("TextIngester 不可用") from e


def _fallbackIngestCode(source: str, cfg: Dict[str, Any]):
  from rag.ingestion.base import IngestedDocument

  ingestionCfg = cfg.get("ingestion") or {}
  codeExts = ingestionCfg.get("code_extensions") or []
  ignorePatterns = set(ingestionCfg.get("ignore_patterns") or [])
  maxFileSizeMb = float(ingestionCfg.get("max_file_size_mb", 10) or 10)
  maxBytes = int(maxFileSizeMb * 1024 * 1024)

  paths: List[str] = []
  if os.path.isdir(source):
    for root, dirs, files in os.walk(source):
      dirs[:] = [d for d in dirs if d not in ignorePatterns]
      for name in files:
        ext = os.path.splitext(name)[1].lower()
        if codeExts and ext not in set([str(x).lower() for x in codeExts]):
          continue
        fp = os.path.join(root, name)
        paths.append(fp)
  else:
    paths.append(source)

  paths = sorted(set(paths))
  texts: List[str] = []
  rawParts: List[bytes] = []
  for fp in paths:
    try:
      if os.path.isfile(fp):
        size = os.path.getsize(fp)
        if size > maxBytes:
          continue
    except Exception:
      pass

    try:
      with open(fp, "rb") as f:
        b = f.read()
      rawParts.append(fp.encode("utf-8") + b"\n" + b)
      t = b.decode("utf-8", errors="replace")
      texts.append(f"\n\n# FILE: {fp}\n\n{t}")
    except Exception:
      continue

  combinedText = "".join(texts).strip()
  combinedBytes = b"\n\n".join(rawParts)
  title = os.path.basename(os.path.abspath(source))
  return IngestedDocument(
    text=combinedText,
    title=title,
    source_type="code",
    source_uri=source,
    content_bytes=combinedBytes,
  )


if __name__ == "__main__":
  raise SystemExit(main())
