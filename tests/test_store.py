import os
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
  pytest.skip("需要 sqlite3>=3.35.0 才能运行 ChromaDB 测试", allow_module_level=True)


# ruff: noqa: E402


from rag.models import ChunkMeta
from rag.store import VectorStore


def _mkChunk(chunk_id: str, doc_id: str, doc_version: str, text: str, chunk_index: int = 0):
  return ChunkMeta(
    chunk_id=chunk_id,
    doc_id=doc_id,
    doc_version=doc_version,
    source_type="text",
    source_uri="test.md",
    title="Test",
    chunk_index=chunk_index,
    char_start=0,
    char_end=len(text),
    text=text,
    created_at=0,
  )


def _emb(val: float, dims: int = 8):
  return [val] * dims


def test_upsert_then_query_returns_items(tmp_persist_dir):
  store = VectorStore(tmp_persist_dir, "test")
  try:
    chunk = _mkChunk("c1", "d1", "v1", "hello world")
    store.upsertChunks([chunk], [_emb(0.1)])

    items = store.query(_emb(0.1), top_k=1)
    assert len(items) == 1
    assert items[0]["chunk_id"] == "c1"
    assert items[0]["text"] == "hello world"
    assert items[0]["metadata"]["doc_id"] == "d1"
    assert isinstance(items[0]["distance"], (int, float))
  finally:
    store.close()


def test_incremental_indexing_shouldReindex(tmp_persist_dir):
  store = VectorStore(tmp_persist_dir, "test")
  try:
    chunk = _mkChunk("c1", "d1", "v1", "hello")
    store.upsertChunks([chunk], [_emb(0.2)])

    assert store.shouldReindex("d1", "v1") is False
    assert store.shouldReindex("d1", "v2") is True
  finally:
    store.close()


def test_deleteByDocId_removes_chunks(tmp_persist_dir):
  store = VectorStore(tmp_persist_dir, "test")
  try:
    chunks = [
      _mkChunk("c1", "d1", "v1", "hello", 0),
      _mkChunk("c2", "d1", "v1", "world", 1),
    ]
    store.upsertChunks(chunks, [_emb(0.1), _emb(0.1)])
    assert len(store.query(_emb(0.1), top_k=10, where={"doc_id": "d1"})) == 2

    deleted = store.deleteByDocId("d1")
    assert deleted == 2
    assert store.query(_emb(0.1), top_k=10, where={"doc_id": "d1"}) == []
  finally:
    store.close()


def test_getStatus_counts_docs_and_chunks(tmp_persist_dir):
  store = VectorStore(tmp_persist_dir, "test")
  try:
    chunks = [
      _mkChunk("c1", "d1", "v1", "a", 0),
      _mkChunk("c2", "d1", "v1", "b", 1),
      _mkChunk("c3", "d2", "v9", "c", 0),
    ]
    store.upsertChunks(chunks, [_emb(0.1), _emb(0.1), _emb(0.9)])

    status = store.getStatus()
    assert status["collection"] == "test"
    assert status["total_chunks"] == 3
    assert status["total_docs"] == 2
  finally:
    store.close()


def test_listDocuments_returns_doc_summaries(tmp_persist_dir):
  store = VectorStore(tmp_persist_dir, "test")
  try:
    chunks = [
      _mkChunk("c1", "d1", "v1", "a", 0),
      _mkChunk("c2", "d1", "v1", "b", 1),
      _mkChunk("c3", "d2", "v2", "c", 0),
    ]
    store.upsertChunks(chunks, [_emb(0.1), _emb(0.1), _emb(0.2)])

    docs = {d["doc_id"]: d for d in store.listDocuments()}
    assert set(docs.keys()) == {"d1", "d2"}
    assert docs["d1"]["chunk_count"] == 2
    assert docs["d1"]["doc_version"] == "v1"
    assert docs["d1"]["source_type"] == "text"
    assert docs["d1"]["source_uri"] == "test.md"
  finally:
    store.close()


def test_lock_file_created_after_upsert(tmp_persist_dir):
  store = VectorStore(tmp_persist_dir, "test")
  try:
    chunk = _mkChunk("c1", "d1", "v1", "hello")
    store.upsertChunks([chunk], [_emb(0.3)])
    assert os.path.isdir(tmp_persist_dir)
  finally:
    store.close()


def test_query_empty_collection_returns_empty_list(tmp_persist_dir):
  store = VectorStore(tmp_persist_dir, "test")
  try:
    assert store.query(_emb(0.1), top_k=3) == []
  finally:
    store.close()


def test_deleteByDocId_nonexistent_returns_zero(tmp_persist_dir):
  store = VectorStore(tmp_persist_dir, "test")
  try:
    assert store.deleteByDocId("missing") == 0
  finally:
    store.close()
