from __future__ import annotations

from typing import Any

from click.testing import CliRunner

import cli_anything.rag_skill.__main__ as mainMod


class TinyBackend:
  def loadConfig(self, config_path=None):
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

  def resolveConfigPath(self, config_path=None):
    return config_path

  def detectSourceType(self, input_path: str) -> str:
    return "text"

  def ingest(self, sourceType: str, source: str, cfg):
    class Doc:
      text = "hello"
      title = "t"
      source_type = "text"
      source_uri = source
      content_bytes = b"hello"

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
      def __init__(self, t: str):
        self.text = t
        self.char_start = 0
        self.char_end = len(t)

    return [Span(text)]

  def splitCodeChunks(self, text: str, language: str, chunk_size: int, overlap: int):
    return self.splitTextChunks(text, chunk_size, overlap)

  def createVectorStore(self, persist_dir: str, collection_name: str):
    class Store:
      persistDir = persist_dir
      collectionName = collection_name

      def close(self):
        return

      def shouldReindex(self, doc_id: str, new_version: str) -> bool:
        return True

      def deleteByDocId(self, doc_id: str) -> int:
        return 0

      def upsertChunks(self, chunks: Any, embeddings: Any) -> int:
        return len(chunks)

      def getStatus(self):
        return {"collection": collection_name, "total_chunks": 0, "total_docs": 0}

      def listDocuments(self):
        return []

    return Store()

  def createEmbeddingClient(self, service_url: str, batch_size: int, dimension: int, timeout=None):
    class Emb:
      def embedTexts(self, texts):
        return [[0.0] for _ in texts]

      def embedText(self, text):
        return [0.0]

    return Emb()

  def createRerankClient(self, service_url: str, batch_size: int):
    return None

  def createRetriever(self, store: Any, embedding_client: Any, rerank_client: Any, top_k: int, rerank_top_k: int):
    class Ret:
      def retrieve(self, query: str):
        return []

      def retrieveAndAnswer(self, question: str, llm_client=None) -> dict:
        return {"answer": "", "sources": [], "chunks_used": 0}

    return Ret()

  def createLlmClient(self, base_url: str, model: str, temperature: float, max_tokens: int, timeout=None):
    return None


def test_cli_config_show_json(monkeypatch):
  monkeypatch.setattr(mainMod, "createBackend", lambda: TinyBackend())
  runner = CliRunner()
  result = runner.invoke(mainMod.cli, ["--json", "config", "show"])
  assert result.exit_code == 0
  assert '"ok": true' in result.output.lower()


def test_cli_index_add_json(monkeypatch):
  monkeypatch.setattr(mainMod, "createBackend", lambda: TinyBackend())
  runner = CliRunner()
  result = runner.invoke(mainMod.cli, ["--json", "index", "add", "x.txt"])
  assert result.exit_code == 0
  assert '"doc_id": "doc1"' in result.output
