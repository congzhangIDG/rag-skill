from dataclasses import dataclass, field
import hashlib
import time


@dataclass
class DocumentMeta:
  doc_id: str
  doc_version: str
  source_type: str
  source_uri: str
  title: str
  created_at: float = field(default_factory=time.time)

  def toChromaMeta(self) -> dict:
    return {
      "doc_id": self.doc_id,
      "doc_version": self.doc_version,
      "source_type": self.source_type,
      "source_uri": self.source_uri,
      "title": self.title,
      "created_at": self.created_at,
    }


@dataclass
class ChunkMeta:
  chunk_id: str
  doc_id: str
  doc_version: str
  source_type: str
  source_uri: str
  title: str
  chunk_index: int
  char_start: int
  char_end: int
  text: str
  created_at: float = field(default_factory=time.time)

  def toChromaMeta(self) -> dict:
    return {
      "chunk_id": self.chunk_id,
      "doc_id": self.doc_id,
      "doc_version": self.doc_version,
      "source_type": self.source_type,
      "source_uri": self.source_uri,
      "title": self.title,
      "chunk_index": self.chunk_index,
      "char_start": self.char_start,
      "char_end": self.char_end,
      "created_at": self.created_at,
    }


def generateDocId(source_uri: str, content_bytes: bytes) -> str:
  raw = source_uri.encode("utf-8") + content_bytes
  return hashlib.sha256(raw).hexdigest()[:16]


def generateDocVersion(content_bytes: bytes) -> str:
  return hashlib.sha256(content_bytes).hexdigest()


def generateChunkId(doc_id: str, chunk_index: int, chunk_text: str) -> str:
  raw = f"{doc_id}:{chunk_index}:{chunk_text}"
  return hashlib.sha1(raw.encode("utf-8")).hexdigest()
