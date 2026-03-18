from __future__ import annotations

import sys

import pytest


try:
  import pysqlite3  # type: ignore

  sys.modules["sqlite3"] = pysqlite3
except Exception:
  pass


import sqlite3


def _getSqliteVersionTuple():
  parts = sqlite3.sqlite_version.split(".")
  nums = [int(p) for p in parts[:3]]
  while len(nums) < 3:
    nums.append(0)
  return tuple(nums)


if _getSqliteVersionTuple() < (3, 35, 0):
  pytest.skip("sqlite3 版本 < 3.35.0, ChromaDB 不可用", allow_module_level=True)


try:
  import chromadb  # type: ignore  # noqa: F401
except Exception:
  pytest.skip("ChromaDB 不可用", allow_module_level=True)


# ruff: noqa: E402


from rag.chunker import detectLanguage, splitCodeChunks, splitTextChunks
from rag.ingestion.code import CodeIngester
from rag.ingestion.text import TextIngester
from rag.models import ChunkMeta, generateChunkId, generateDocId, generateDocVersion
from rag.store import VectorStore


def _buildChunks(ingested, docId: str, docVersion: str, spans):
  chunks = []
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
  return chunks


def _indexText(store: VectorStore, path: str, embeddingClient):
  ingested = TextIngester().ingest(path)
  docId = generateDocId(ingested.source_uri, ingested.content_bytes)
  docVersion = generateDocVersion(ingested.content_bytes)
  spans = splitTextChunks(ingested.text, chunk_size=10000, overlap=0)
  chunks = _buildChunks(ingested, docId, docVersion, spans)
  embeddings = embeddingClient.embedTexts([c.text for c in chunks])
  upserts = store.upsertChunks(chunks, embeddings)
  return docId, docVersion, upserts


def _indexCode(store: VectorStore, path: str, embeddingClient):
  ingested = CodeIngester().ingest(path)
  docId = generateDocId(ingested.source_uri, ingested.content_bytes)
  docVersion = generateDocVersion(ingested.content_bytes)
  lang = detectLanguage(path)
  spans = splitCodeChunks(ingested.text, language=lang, chunk_size=10000, overlap=0)
  chunks = _buildChunks(ingested, docId, docVersion, spans)
  embeddings = embeddingClient.embedTexts([c.text for c in chunks])
  upserts = store.upsertChunks(chunks, embeddings)
  return docId, docVersion, upserts


def test_full_lifecycle(tmp_persist_dir, sample_md_path, mock_embedding_client):
  store = VectorStore(tmp_persist_dir, "e2e")
  try:
    _indexText(store, sample_md_path, mock_embedding_client)

    status = store.getStatus()
    assert status["total_docs"] >= 1

    items = store.query(mock_embedding_client.embedText("向量检索"), top_k=3)
    assert items
    assert items[0]["metadata"]["source_uri"] == sample_md_path

    docs = store.listDocuments()
    assert docs
    docId = docs[0]["doc_id"]

    store.deleteByDocId(docId)
    status2 = store.getStatus()
    assert status2["total_docs"] == 0
  finally:
    store.close()


def test_incremental_index(tmp_persist_dir, sample_md_path, mock_embedding_client):
  store = VectorStore(tmp_persist_dir, "e2e_inc")
  try:
    docId, docVersion, upserts = _indexText(store, sample_md_path, mock_embedding_client)
    assert upserts >= 1
    assert store.shouldReindex(docId, docVersion) is False

    ingested2 = TextIngester().ingest(sample_md_path)
    docVersion2 = generateDocVersion(ingested2.content_bytes)
    assert store.shouldReindex(docId, docVersion2) is False
  finally:
    store.close()


def test_code_index_and_query(tmp_persist_dir, sample_py_path, mock_embedding_client):
  store = VectorStore(tmp_persist_dir, "e2e_code")
  try:
    _indexCode(store, sample_py_path, mock_embedding_client)

    items = store.query(mock_embedding_client.embedText("Calculator"), top_k=3)
    assert items
    assert any("Calculator" in (it.get("text") or "") for it in items)
  finally:
    store.close()


def test_multi_type_index(tmp_persist_dir, sample_md_path, sample_py_path, mock_embedding_client):
  store = VectorStore(tmp_persist_dir, "e2e_multi")
  try:
    _indexText(store, sample_md_path, mock_embedding_client)
    _indexCode(store, sample_py_path, mock_embedding_client)

    status = store.getStatus()
    assert status["total_docs"] == 2
  finally:
    store.close()
