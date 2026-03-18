import os
import sys
from typing import Any, Dict, List, Optional

try:
  import pysqlite3  # type: ignore

  sys.modules["sqlite3"] = pysqlite3
except ImportError:
  pass

from filelock import FileLock

from rag.models import ChunkMeta


def _importChromadb():
  try:
    import chromadb  # type: ignore

    return chromadb
  except RuntimeError as e:
    msg = str(e)
    if "unsupported version of sqlite3" in msg or "requires sqlite3" in msg:
      raise RuntimeError(
        "当前环境 sqlite3 版本过低，无法导入 chromadb。"
        "需要 sqlite3>=3.35.0（当前 Python 3.9.4 内置 sqlite3=3.34.0）。"
        "请升级 Python 或提供满足要求的 sqlite3。"
      ) from e
    raise


class VectorStore:
  def __init__(self, persist_dir: str, collection_name: str = "rag_default"):
    self.persistDir = persist_dir
    self.collectionName = collection_name
    self.lockPath = os.path.join(persist_dir, ".rag.lock")
    self._client = None
    self._collection = None
    os.makedirs(persist_dir, exist_ok=True)
    self._ensureLockPath()

  def _ensureLockPath(self):
    lockDir = os.path.dirname(self.lockPath)
    os.makedirs(lockDir, exist_ok=True)
    if not os.path.exists(self.lockPath):
      open(self.lockPath, "a").close()

  def close(self):
    client = self._client
    self._client = None
    self._collection = None
    if client is None:
      return
    closeFn = getattr(client, "close", None)
    if callable(closeFn):
      closeFn()

    try:
      system = getattr(client, "_system", None)
    except Exception:
      system = None
    stopFn = getattr(system, "stop", None)
    if callable(stopFn):
      stopFn()

  def _getClient(self) -> Any:
    chromadb = _importChromadb()
    if self._client is None:
      self._client = chromadb.PersistentClient(path=self.persistDir)
    return self._client

  def _getCollection(self):
    if self._collection is None:
      client = self._getClient()
      self._collection = client.get_or_create_collection(
        name=self.collectionName,
        metadata={"hnsw:space": "cosine"},
      )
    return self._collection

  def upsertChunks(self, chunks: List[ChunkMeta], embeddings: List[List[float]]) -> int:
    if len(chunks) != len(embeddings):
      raise ValueError("chunks 与 embeddings 数量不一致")

    with FileLock(self.lockPath):
      self._ensureLockPath()
      collection = self._getCollection()
      ids = [c.chunk_id for c in chunks]
      documents = [c.text for c in chunks]
      metadatas = [c.toChromaMeta() for c in chunks]
      collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
      )
      return len(chunks)

  def getDocVersion(self, doc_id: str) -> Optional[str]:
    collection = self._getCollection()
    results = collection.get(
      where={"doc_id": doc_id},
      limit=1,
      include=["metadatas"],
    )
    ids = results.get("ids") or []
    metadatas = results.get("metadatas") or []
    if ids and metadatas:
      return (metadatas[0] or {}).get("doc_version")
    return None

  def shouldReindex(self, doc_id: str, new_version: str) -> bool:
    current = self.getDocVersion(doc_id)
    return current != new_version

  def deleteByDocId(self, doc_id: str) -> int:
    with FileLock(self.lockPath):
      collection = self._getCollection()
      results = collection.get(where={"doc_id": doc_id}, include=[])
      ids = results.get("ids") or []
      count = len(ids)
      if count > 0:
        collection.delete(where={"doc_id": doc_id})
      return count

  def query(
    self,
    query_embedding: List[float],
    top_k: int = 10,
    where: Optional[Dict[str, Any]] = None,
  ) -> List[Dict[str, Any]]:
    collection = self._getCollection()
    total = collection.count()
    if total == 0:
      return []

    kwargs: Dict[str, Any] = {
      "query_embeddings": [query_embedding],
      "n_results": min(top_k, total),
      "include": ["documents", "metadatas", "distances"],
    }
    if where:
      kwargs["where"] = where

    results = collection.query(**kwargs)
    ids = (results.get("ids") or [[]])[0]
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    items: List[Dict[str, Any]] = []
    for i in range(len(ids)):
      items.append({
        "chunk_id": ids[i],
        "text": documents[i],
        "metadata": metadatas[i],
        "distance": distances[i],
      })
    return items

  def getStatus(self) -> Dict[str, Any]:
    collection = self._getCollection()
    total_chunks = collection.count()

    doc_ids = set()
    if total_chunks > 0:
      all_meta = collection.get(include=["metadatas"])
      for meta in all_meta.get("metadatas") or []:
        if not meta:
          continue
        doc_ids.add(meta.get("doc_id", ""))

    return {
      "collection": self.collectionName,
      "total_chunks": total_chunks,
      "total_docs": len(doc_ids),
    }

  def listDocuments(self) -> List[Dict[str, Any]]:
    collection = self._getCollection()
    if collection.count() == 0:
      return []

    all_data = collection.get(include=["metadatas"])
    docs: Dict[str, Dict[str, Any]] = {}
    for meta in all_data.get("metadatas") or []:
      if not meta:
        continue
      doc_id = meta.get("doc_id", "")
      if doc_id not in docs:
        docs[doc_id] = {
          "doc_id": doc_id,
          "source_uri": meta.get("source_uri", ""),
          "source_type": meta.get("source_type", ""),
          "doc_version": meta.get("doc_version", ""),
          "chunk_count": 0,
        }
      docs[doc_id]["chunk_count"] += 1

    return list(docs.values())
