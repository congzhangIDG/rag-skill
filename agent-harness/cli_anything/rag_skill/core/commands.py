from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from cli_anything.rag_skill.core.session import RagSession


def _getStoreCfg(cfg: Dict[str, Any]) -> Tuple[str, str]:
  storeCfg = cfg.get("store") or {}
  persistDir = str(storeCfg.get("persist_dir") or "")
  defaultCollection = str(storeCfg.get("default_collection") or "rag_default")
  return persistDir, defaultCollection


def _getChunkingCfg(cfg: Dict[str, Any]) -> Tuple[int, int]:
  chunkingCfg = cfg.get("chunking") or {}
  chunkSize = int(chunkingCfg.get("chunk_size", 600) or 600)
  overlapSize = int(chunkingCfg.get("overlap_size", 100) or 100)
  return chunkSize, overlapSize


def _getEmbeddingCfg(cfg: Dict[str, Any]) -> Tuple[str, int, int]:
  embeddingCfg = cfg.get("embedding") or {}
  serviceUrl = str(embeddingCfg.get("service_url") or "")
  batchSize = int(embeddingCfg.get("batch_size", 16) or 16)
  dimension = int(embeddingCfg.get("dimension", 768) or 768)
  return serviceUrl, batchSize, dimension


def _getRerankCfg(cfg: Dict[str, Any]) -> Tuple[str, int]:
  rerankCfg = cfg.get("rerank") or {}
  serviceUrl = str(rerankCfg.get("service_url") or "")
  batchSize = int(rerankCfg.get("batch_size", 16) or 16)
  return serviceUrl, batchSize


def _getRetrievalCfg(cfg: Dict[str, Any]) -> Tuple[int, int]:
  retrievalCfg = cfg.get("retrieval") or {}
  topK = int(retrievalCfg.get("top_k", 10) or 10)
  rerankTopK = int(retrievalCfg.get("rerank_top_k", 5) or 5)
  return topK, rerankTopK


def _getLlmCfg(cfg: Dict[str, Any]) -> Tuple[str, str, float, int]:
  llmCfg = cfg.get("llm") or {}
  baseUrl = str(llmCfg.get("base_url") or "")
  model = str(llmCfg.get("model") or "default")
  temperature = float(llmCfg.get("temperature", 0.1) or 0.1)
  maxTokens = int(llmCfg.get("max_tokens", 2048) or 2048)
  return baseUrl, model, temperature, maxTokens


def initSession(backend: Any, config_path: Optional[str] = None, collection: Optional[str] = None) -> RagSession:
  cfg = backend.loadConfig(config_path)
  try:
    resolvedConfigPath = backend.resolveConfigPath(config_path)
  except Exception:
    resolvedConfigPath = None

  if isinstance(cfg, dict):
    meta = cfg.get("__harness__")
    if not isinstance(meta, dict):
      meta = {}
      cfg["__harness__"] = meta
    meta["config_path"] = resolvedConfigPath

  _, defaultCollection = _getStoreCfg(cfg)
  currentCollection = str(collection or defaultCollection)
  return RagSession(
    config=cfg,
    current_collection=currentCollection,
    last_results=[],
    history=[],
    store=None,
  )


def closeSession(session: RagSession) -> None:
  store = session.store
  session.store = None
  if store is None:
    return
  closeFn = getattr(store, "close", None)
  if callable(closeFn):
    closeFn()


def _getOrCreateStore(backend: Any, session: RagSession, collection_name: Optional[str] = None):
  persistDir, _ = _getStoreCfg(session.config)
  collectionName = str(collection_name or session.current_collection)

  store = session.store
  if store is not None:
    existingCollection = getattr(store, "collectionName", None)
    existingPersist = getattr(store, "persistDir", None)
    if str(existingCollection) == collectionName and str(existingPersist) == persistDir:
      return store

    closeFn = getattr(store, "close", None)
    if callable(closeFn):
      closeFn()
    session.store = None

  session.store = backend.createVectorStore(persist_dir=persistDir, collection_name=collectionName)
  return session.store


def configShow(backend: Any, session: RagSession) -> Dict[str, Any]:
  return {
    "config": session.config,
  }


def configPath(backend: Any, config_path: Optional[str]) -> Dict[str, Any]:
  resolved = backend.resolveConfigPath(config_path)
  return {
    "config_path": resolved,
  }


def indexAdd(
  backend: Any,
  session: RagSession,
  source: str,
  collection_name: Optional[str] = None,
) -> Dict[str, Any]:
  sourceType = backend.detectSourceType(source)
  ingested = backend.ingest(sourceType, source, session.config)

  contentBytes = getattr(ingested, "content_bytes", None)
  if not isinstance(contentBytes, (bytes, bytearray)):
    raise RuntimeError("摄取结果无效：缺少 content_bytes")

  sourceUri = str(getattr(ingested, "source_uri", "") or "")
  text = str(getattr(ingested, "text", "") or "")
  title = str(getattr(ingested, "title", "") or "")
  ingestedType = str(getattr(ingested, "source_type", "") or sourceType)

  docId = backend.generateDocId(sourceUri, bytes(contentBytes))
  docVersion = backend.generateDocVersion(bytes(contentBytes))

  chunkSize, overlapSize = _getChunkingCfg(session.config)
  if ingestedType == "code" and os.path.isfile(source):
    lang = backend.detectLanguage(source)
    spans = backend.splitCodeChunks(text, language=lang, chunk_size=chunkSize, overlap=overlapSize)
  else:
    spans = backend.splitTextChunks(text, chunk_size=chunkSize, overlap=overlapSize)

  chunks: List[Any] = []
  for i, span in enumerate(spans):
    spanText = str(getattr(span, "text"))
    chunkId = backend.generateChunkId(docId, i, spanText)
    chunks.append(
      backend.createChunkMeta(
        chunk_id=chunkId,
        doc_id=docId,
        doc_version=docVersion,
        source_type=ingestedType,
        source_uri=sourceUri,
        title=title,
        chunk_index=i,
        char_start=int(getattr(span, "char_start")),
        char_end=int(getattr(span, "char_end")),
        text=spanText,
      )
    )

  store = _getOrCreateStore(backend, session, collection_name=collection_name)
  if not store.shouldReindex(docId, docVersion):
    return {
      "collection": str(getattr(store, "collectionName", "") or ""),
      "doc_id": docId,
      "doc_version": docVersion,
      "chunks": len(chunks),
      "upserts": 0,
      "reindexed": False,
    }

  store.deleteByDocId(docId)
  embedUrl, embedBatch, dimension = _getEmbeddingCfg(session.config)
  embeddingClient = backend.createEmbeddingClient(service_url=embedUrl, batch_size=embedBatch, dimension=dimension)
  embeddings = embeddingClient.embedTexts([c.text for c in chunks])
  upserts = store.upsertChunks(chunks, embeddings)
  return {
    "collection": str(getattr(store, "collectionName", "") or ""),
    "doc_id": docId,
    "doc_version": docVersion,
    "chunks": len(chunks),
    "upserts": int(upserts),
    "reindexed": True,
  }


def indexStatus(backend: Any, session: RagSession, collection_name: Optional[str] = None) -> Dict[str, Any]:
  store = _getOrCreateStore(backend, session, collection_name=collection_name)
  status = store.getStatus()
  documents = store.listDocuments()
  return {
    "status": status,
    "documents": documents,
  }


def indexForget(backend: Any, session: RagSession, doc_id: str, collection_name: Optional[str] = None) -> Dict[str, Any]:
  store = _getOrCreateStore(backend, session, collection_name=collection_name)
  deleted = store.deleteByDocId(doc_id)
  return {
    "doc_id": doc_id,
    "deleted": int(deleted),
  }


def querySearch(
  backend: Any,
  session: RagSession,
  question: str,
  collection_name: Optional[str] = None,
  no_rerank: bool = False,
  no_llm: bool = False,
) -> Dict[str, Any]:
  store = _getOrCreateStore(backend, session, collection_name=collection_name)
  embedUrl, embedBatch, dimension = _getEmbeddingCfg(session.config)
  embeddingClient = backend.createEmbeddingClient(service_url=embedUrl, batch_size=embedBatch, dimension=dimension)

  rerankClient = None
  if not no_rerank:
    rerankUrl, rerankBatch = _getRerankCfg(session.config)
    if rerankUrl:
      rerankClient = backend.createRerankClient(service_url=rerankUrl, batch_size=rerankBatch)

  topK, rerankTopK = _getRetrievalCfg(session.config)
  retriever = backend.createRetriever(
    store=store,
    embedding_client=embeddingClient,
    rerank_client=rerankClient,
    top_k=topK,
    rerank_top_k=rerankTopK,
  )
  results = retriever.retrieve(question)
  payload: List[Dict[str, Any]] = []
  for r in results:
    payload.append({
      "chunk_id": r.chunk_id,
      "text": r.text,
      "score": float(r.score),
      "source_uri": r.source_uri,
      "source_type": r.source_type,
      "title": r.title,
      "chunk_index": int(r.chunk_index),
    })
  session.last_results = payload
  return {
    "collection": str(getattr(store, "collectionName", "") or ""),
    "question": question,
    "no_rerank": bool(no_rerank),
    "no_llm": bool(no_llm),
    "results": payload,
  }


def queryAsk(backend: Any, session: RagSession, question: str, collection_name: Optional[str] = None) -> Dict[str, Any]:
  store = _getOrCreateStore(backend, session, collection_name=collection_name)
  embedUrl, embedBatch, dimension = _getEmbeddingCfg(session.config)
  embeddingClient = backend.createEmbeddingClient(service_url=embedUrl, batch_size=embedBatch, dimension=dimension)

  rerankClient = None
  rerankUrl, rerankBatch = _getRerankCfg(session.config)
  if rerankUrl:
    rerankClient = backend.createRerankClient(service_url=rerankUrl, batch_size=rerankBatch)

  topK, rerankTopK = _getRetrievalCfg(session.config)
  retriever = backend.createRetriever(
    store=store,
    embedding_client=embeddingClient,
    rerank_client=rerankClient,
    top_k=topK,
    rerank_top_k=rerankTopK,
  )

  baseUrl, model, temperature, maxTokens = _getLlmCfg(session.config)
  llmClient = None
  if baseUrl:
    llmClient = backend.createLlmClient(
      base_url=baseUrl,
      model=model,
      temperature=temperature,
      max_tokens=maxTokens,
    )

  answerPayload = retriever.retrieveAndAnswer(question, llm_client=llmClient)
  results = answerPayload.get("sources") or []
  session.last_results = results
  return {
    "collection": str(getattr(store, "collectionName", "") or ""),
    "question": question,
    "answer": answerPayload.get("answer", ""),
    "sources": results,
    "chunks_used": int(answerPayload.get("chunks_used", 0) or 0),
  }
