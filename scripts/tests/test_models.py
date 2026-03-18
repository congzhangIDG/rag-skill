import re


from rag.models import (
  ChunkMeta,
  DocumentMeta,
  generateChunkId,
  generateDocId,
  generateDocVersion,
)


def test_generateDocId_deterministic():
  a = generateDocId("test.md", b"hello")
  b = generateDocId("test.md", b"hello")
  assert a == b


def test_generateDocId_length():
  doc_id = generateDocId("test.md", b"hello")
  assert len(doc_id) == 16
  assert re.fullmatch(r"[0-9a-f]{16}", doc_id)


def test_generateDocVersion_deterministic():
  a = generateDocVersion(b"hello")
  b = generateDocVersion(b"hello")
  assert a == b


def test_generateChunkId_stable():
  a = generateChunkId("doc", 0, "hello")
  b = generateChunkId("doc", 0, "hello")
  assert a == b


def test_generateChunkId_sensitive():
  a = generateChunkId("doc", 0, "hello")
  b = generateChunkId("doc", 0, "hello!")
  assert a != b


def test_toChromaMeta_no_text_key():
  chunk = ChunkMeta(
    chunk_id="c",
    doc_id="d",
    doc_version="v",
    source_type="text",
    source_uri="u",
    title="t",
    chunk_index=1,
    char_start=0,
    char_end=5,
    text="hello",
    created_at=123.0,
  )
  meta = chunk.toChromaMeta()
  assert "text" not in meta


def test_toChromaMeta_all_values_scalar():
  doc = DocumentMeta(
    doc_id="d",
    doc_version="v",
    source_type="text",
    source_uri="u",
    title="t",
    created_at=123.0,
  )
  doc_meta = doc.toChromaMeta()
  assert all(isinstance(v, (str, int, float, bool)) for v in doc_meta.values())

  chunk = ChunkMeta(
    chunk_id="c",
    doc_id=doc.doc_id,
    doc_version=doc.doc_version,
    source_type=doc.source_type,
    source_uri=doc.source_uri,
    title=doc.title,
    chunk_index=1,
    char_start=0,
    char_end=5,
    text="hello",
    created_at=123.0,
  )
  chunk_meta = chunk.toChromaMeta()
  assert all(isinstance(v, (str, int, float, bool)) for v in chunk_meta.values())
