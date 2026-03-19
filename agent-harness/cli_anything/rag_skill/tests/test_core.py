from __future__ import annotations

from typing import Any, Dict, List, Optional

from cli_anything.rag_skill.core import commands


class FakeStore:
  def __init__(self, persist_dir: str, collection_name: str):
    self.persistDir = persist_dir
    self.collectionName = collection_name
    self._docs: Dict[str, Dict[str, Any]] = {}

  def close(self):
    return

  def shouldReindex(self, doc_id: str, new_version: str) -> bool:
    doc = self._docs.get(doc_id)
    if not doc:
      return True
    return doc.get("doc_version") != new_version

  def deleteByDocId(self, doc_id: str) -> int:
    if doc_id in self._docs:
      del self._docs[doc_id]
      return 1
    return 0

  def upsertChunks(self, chunks: List[Any], embeddings: List[List[float]]) -> int:
    if not chunks:
      return 0
    docId = chunks[0].doc_id
    self._docs[docId] = {
      "doc_id": docId,
      "doc_version": chunks[0].doc_version,
      "chunk_count": len(chunks),
    }
    return len(chunks)

  def getStatus(self) -> Dict[str, Any]:
    totalDocs = len(self._docs)
    totalChunks = 0
    for d in self._docs.values():
      totalChunks += int(d.get("chunk_count", 0) or 0)
    return {
      "collection": self.collectionName,
      "total_chunks": totalChunks,
      "total_docs": totalDocs,
    }

  def listDocuments(self) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for d in self._docs.values():
      out.append({
        "doc_id": d.get("doc_id"),
        "doc_version": d.get("doc_version"),
        "chunk_count": d.get("chunk_count"),
        "source_uri": "",
        "source_type": "",
      })
    return out


class FakeEmbeddingClient:
  def embedTexts(self, texts: List[str]) -> List[List[float]]:
    return [[0.0] for _ in texts]

  def embedText(self, text: str) -> List[float]:
    return [0.0]


class FakeRetriever:
  def __init__(self):
    self._results = []

  def retrieve(self, query: str):
    return []

  def retrieveAndAnswer(self, question: str, llm_client: Optional[Any] = None) -> dict:
    return {
      "answer": "",
      "sources": [],
      "chunks_used": 0,
    }


class FakeBackend:
  def __init__(self):
    self._stores: Dict[str, FakeStore] = {}

  def loadConfig(self, config_path: Optional[str] = None) -> Dict[str, Any]:
    return {
      "store": {
        "persist_dir": "/tmp/chroma",
        "default_collection": "rag_default",
      },
      "chunking": {
        "chunk_size": 10,
        "overlap_size": 0,
      },
      "embedding": {
        "service_url": "http://emb",
        "batch_size": 16,
        "dimension": 1,
      },
      "rerank": {
        "service_url": "",
        "batch_size": 16,
      },
      "retrieval": {
        "top_k": 10,
        "rerank_top_k": 5,
      },
      "llm": {
        "base_url": "",
        "model": "default",
        "temperature": 0.1,
        "max_tokens": 32,
      },
    }

  def resolveConfigPath(self, config_path: Optional[str] = None) -> Optional[str]:
    return config_path

  def detectSourceType(self, input_path: str) -> str:
    return "text"

  def ingest(self, sourceType: str, source: str, cfg: Dict[str, Any]):
    class Doc:
      text = "hello world"
      title = "t"
      source_type = "text"
      source_uri = source
      content_bytes = b"hello world"

    return Doc()

  def generateDocId(self, source_uri: str, content_bytes: bytes) -> str:
    return "doc1"

  def generateDocVersion(self, content_bytes: bytes) -> str:
    return "v1"

  def generateChunkId(self, doc_id: str, chunk_index: int, chunk_text: str) -> str:
    return f"{doc_id}:{chunk_index}"

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
  ):
    class Chunk:
      def __init__(self):
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.doc_version = doc_version
        self.source_type = source_type
        self.source_uri = source_uri
        self.title = title
        self.chunk_index = chunk_index
        self.char_start = char_start
        self.char_end = char_end
        self.text = text

    return Chunk()

  def detectLanguage(self, file_path: str) -> str:
    return "text"

  def splitTextChunks(self, text: str, chunk_size: int, overlap: int):
    class Span:
      def __init__(self, t: str, s: int, e: int):
        self.text = t
        self.char_start = s
        self.char_end = e

    return [Span(text, 0, len(text))]

  def splitCodeChunks(self, text: str, language: str, chunk_size: int, overlap: int):
    return self.splitTextChunks(text, chunk_size, overlap)

  def createVectorStore(self, persist_dir: str, collection_name: str):
    key = persist_dir + ":" + collection_name
    if key not in self._stores:
      self._stores[key] = FakeStore(persist_dir, collection_name)
    return self._stores[key]

  def createEmbeddingClient(self, service_url: str, batch_size: int, dimension: int, timeout: Optional[float] = None):
    return FakeEmbeddingClient()

  def createRerankClient(self, service_url: str, batch_size: int):
    return None

  def createRetriever(self, store: Any, embedding_client: Any, rerank_client: Any, top_k: int, rerank_top_k: int):
    return FakeRetriever()

  def createLlmClient(self, base_url: str, model: str, temperature: float, max_tokens: int, timeout: Optional[float] = None):
    return None


def test_index_add_and_status():
  backend = FakeBackend()
  session = commands.initSession(backend)
  try:
    out = commands.indexAdd(backend, session, source="x.txt")
    assert out["doc_id"] == "doc1"
    status = commands.indexStatus(backend, session)
    assert status["status"]["total_docs"] == 1
  finally:
    commands.closeSession(session)


def test_config_path():
  backend = FakeBackend()
  out = commands.configPath(backend, config_path="/a/b.yaml")
  assert out["config_path"] == "/a/b.yaml"
