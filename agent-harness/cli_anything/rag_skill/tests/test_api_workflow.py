"""API 全流程测试

覆盖完整工作流：
  initSession → indexAdd → indexStatus → querySearch → queryAsk
  → indexForget → indexStatus（验证删除）→ closeSession

使用 test_core.py 中的 FakeBackend 模式，无外部依赖。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from cli_anything.rag_skill.core import commands


# ---------------------------------------------------------------------------
# Fake 实现（复用 test_core 中的模式，增加 querySearch/queryAsk 支持）
# ---------------------------------------------------------------------------

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
    return [[0.1, 0.2] for _ in texts]

  def embedText(self, text: str) -> List[float]:
    return [0.1, 0.2]


class FakeRetrieveResult:
  """模拟检索结果"""
  def __init__(self, chunk_id: str, text: str, score: float):
    self.chunk_id = chunk_id
    self.text = text
    self.score = score
    self.source_uri = "test.txt"
    self.source_type = "text"
    self.title = "测试文档"
    self.chunk_index = 0


class FakeRetriever:
  def __init__(self):
    self._results: List[FakeRetrieveResult] = [
      FakeRetrieveResult("doc1:0", "hello world", 0.95),
    ]

  def retrieve(self, query: str) -> List[FakeRetrieveResult]:
    return self._results

  def retrieveAndAnswer(self, question: str, llm_client: Optional[Any] = None) -> dict:
    return {
      "answer": f"回答：{question}",
      "sources": [],
      "chunks_used": len(self._results),
    }


class FakeBackend:
  """完整的 FakeBackend，支持全部 commands API"""
  def __init__(self):
    self._stores: Dict[str, FakeStore] = {}
    self._docCounter = 0
    self._ingestCache: Dict[str, int] = {}

  def loadConfig(self, config_path: Optional[str] = None) -> Dict[str, Any]:
    return {
      "store": {
        "persist_dir": "/tmp/test_chroma",
        "default_collection": "test_collection",
      },
      "chunking": {
        "chunk_size": 20,
        "overlap_size": 0,
      },
      "embedding": {
        "service_url": "http://fake-emb",
        "batch_size": 8,
        "dimension": 2,
      },
      "rerank": {
        "service_url": "",
        "batch_size": 8,
      },
      "retrieval": {
        "top_k": 5,
        "rerank_top_k": 3,
      },
      "llm": {
        "base_url": "",
        "model": "fake-model",
        "temperature": 0.0,
        "max_tokens": 64,
      },
    }

  def resolveConfigPath(self, config_path: Optional[str] = None) -> Optional[str]:
    return config_path or "/tmp/config.yaml"

  def detectSourceType(self, input_path: str) -> str:
    if input_path.endswith(".py"):
      return "code"
    return "text"

  def ingest(self, sourceType: str, source: str, cfg: Dict[str, Any]):
    if source not in self._ingestCache:
      self._docCounter += 1
      self._ingestCache[source] = self._docCounter
    idx = self._ingestCache[source]
    content = f"文档内容 {idx}: {source}"

    class Doc:
      text = content
      title = f"doc_{idx}"
      source_type = sourceType
      source_uri = source
      content_bytes = content.encode("utf-8")

    return Doc()

  def generateDocId(self, source_uri: str, content_bytes: bytes) -> str:
    return f"did_{hash(source_uri) % 10000:04d}"

  def generateDocVersion(self, content_bytes: bytes) -> str:
    return f"v_{hash(content_bytes) % 10000:04d}"

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
    return "python" if file_path.endswith(".py") else "text"

  def splitTextChunks(self, text: str, chunk_size: int, overlap: int):
    class Span:
      def __init__(self, t: str, s: int, e: int):
        self.text = t
        self.char_start = s
        self.char_end = e

    # 按 chunk_size 切分
    spans = []
    for i in range(0, len(text), chunk_size):
      spans.append(Span(text[i:i + chunk_size], i, min(i + chunk_size, len(text))))
    return spans if spans else [Span(text, 0, len(text))]

  def splitCodeChunks(self, text: str, language: str, chunk_size: int, overlap: int):
    return self.splitTextChunks(text, chunk_size, overlap)

  def createVectorStore(self, persist_dir: str, collection_name: str):
    key = f"{persist_dir}:{collection_name}"
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


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------

class TestApiFullWorkflow:
  """完整 API 工作流测试：init → add → status → search → ask → forget → verify"""

  def setup_method(self):
    self.backend = FakeBackend()
    self.session = commands.initSession(self.backend)

  def teardown_method(self):
    commands.closeSession(self.session)

  def test_init_session_creates_valid_session(self):
    """initSession 应返回带有正确 collection 和空历史的 session"""
    assert self.session.current_collection == "test_collection"
    assert self.session.last_results == []
    assert self.session.history == []
    assert self.session.config is not None
    assert self.session.config["store"]["persist_dir"] == "/tmp/test_chroma"

  def test_config_show_returns_full_config(self):
    """configShow 应返回完整配置字典"""
    result = commands.configShow(self.backend, self.session)
    assert "config" in result
    cfg = result["config"]
    assert "store" in cfg
    assert "chunking" in cfg
    assert "embedding" in cfg
    assert "retrieval" in cfg
    assert "llm" in cfg

  def test_config_path_resolves(self):
    """configPath 应返回解析后的配置路径"""
    result = commands.configPath(self.backend, config_path="/custom/path.yaml")
    assert result["config_path"] == "/custom/path.yaml"

    # 不传路径时使用默认值
    result2 = commands.configPath(self.backend, config_path=None)
    assert result2["config_path"] == "/tmp/config.yaml"

  def test_index_add_single_document(self):
    """indexAdd 应摄取文档、生成 chunks 并返回正确的元数据"""
    result = commands.indexAdd(self.backend, self.session, source="readme.md")
    assert result["doc_id"].startswith("did_")
    assert result["doc_version"].startswith("v_")
    assert result["chunks"] >= 1
    assert result["upserts"] >= 1
    assert result["reindexed"] is True
    assert result["collection"] == "test_collection"

  def test_index_add_skip_reindex_on_duplicate(self):
    """同一文档再次 add 时，应跳过重建索引"""
    result1 = commands.indexAdd(self.backend, self.session, source="same.txt")
    assert result1["reindexed"] is True

    result2 = commands.indexAdd(self.backend, self.session, source="same.txt")
    assert result2["reindexed"] is False
    assert result2["upserts"] == 0

  def test_index_status_after_add(self):
    """indexAdd 后 indexStatus 应反映正确的文档数量"""
    commands.indexAdd(self.backend, self.session, source="a.txt")
    commands.indexAdd(self.backend, self.session, source="b.txt")

    status = commands.indexStatus(self.backend, self.session)
    assert status["status"]["total_docs"] == 2
    assert status["status"]["total_chunks"] >= 2
    assert len(status["documents"]) == 2

    docIds = [d["doc_id"] for d in status["documents"]]
    assert len(set(docIds)) == 2  # 两个不同的 doc_id

  def test_query_search_returns_results(self):
    """querySearch 应返回检索结果列表"""
    commands.indexAdd(self.backend, self.session, source="data.txt")

    result = commands.querySearch(
      self.backend, self.session, question="什么是RAG？"
    )
    assert result["question"] == "什么是RAG？"
    assert result["collection"] == "test_collection"
    assert isinstance(result["results"], list)
    assert result["no_rerank"] is False
    assert result["no_llm"] is False

  def test_query_search_with_no_rerank(self):
    """querySearch 应支持 no_rerank 参数"""
    commands.indexAdd(self.backend, self.session, source="data.txt")

    result = commands.querySearch(
      self.backend, self.session,
      question="测试查询",
      no_rerank=True,
    )
    assert result["no_rerank"] is True

  def test_query_ask_returns_answer(self):
    """queryAsk 应返回答案和来源信息"""
    commands.indexAdd(self.backend, self.session, source="data.txt")

    result = commands.queryAsk(
      self.backend, self.session, question="什么是向量检索？"
    )
    assert result["question"] == "什么是向量检索？"
    assert "answer" in result
    assert "sources" in result
    assert "chunks_used" in result
    assert result["chunks_used"] >= 0

  def test_index_forget_deletes_document(self):
    """indexForget 应删除指定文档"""
    addResult = commands.indexAdd(self.backend, self.session, source="to_delete.txt")
    docId = addResult["doc_id"]

    # 删除前确认存在
    statusBefore = commands.indexStatus(self.backend, self.session)
    assert statusBefore["status"]["total_docs"] == 1

    # 执行删除
    forgetResult = commands.indexForget(self.backend, self.session, doc_id=docId)
    assert forgetResult["doc_id"] == docId
    assert forgetResult["deleted"] == 1

    # 删除后确认为空
    statusAfter = commands.indexStatus(self.backend, self.session)
    assert statusAfter["status"]["total_docs"] == 0
    assert statusAfter["status"]["total_chunks"] == 0
    assert len(statusAfter["documents"]) == 0

  def test_index_forget_nonexistent_returns_zero(self):
    """indexForget 删除不存在的文档应返回 deleted=0"""
    result = commands.indexForget(
      self.backend, self.session, doc_id="nonexistent_id"
    )
    assert result["deleted"] == 0

  def test_full_workflow_end_to_end(self):
    """完整工作流：add → status → search → ask → forget → verify"""
    # 1. 添加两个文档
    add1 = commands.indexAdd(self.backend, self.session, source="doc1.md")
    add2 = commands.indexAdd(self.backend, self.session, source="doc2.md")
    assert add1["reindexed"] is True
    assert add2["reindexed"] is True
    docId1 = add1["doc_id"]
    docId2 = add2["doc_id"]

    # 2. 确认索引状态
    status = commands.indexStatus(self.backend, self.session)
    assert status["status"]["total_docs"] == 2

    # 3. 执行搜索
    searchResult = commands.querySearch(
      self.backend, self.session, question="测试全流程"
    )
    assert searchResult["question"] == "测试全流程"
    assert isinstance(searchResult["results"], list)

    # 4. 执行问答
    askResult = commands.queryAsk(
      self.backend, self.session, question="全流程问答测试"
    )
    assert "answer" in askResult

    # 5. 删除第一个文档
    forget1 = commands.indexForget(self.backend, self.session, doc_id=docId1)
    assert forget1["deleted"] == 1

    # 6. 验证只剩一个文档
    statusAfterForget = commands.indexStatus(self.backend, self.session)
    assert statusAfterForget["status"]["total_docs"] == 1
    remainingDocIds = [d["doc_id"] for d in statusAfterForget["documents"]]
    assert docId2 in remainingDocIds
    assert docId1 not in remainingDocIds

    # 7. 删除第二个文档
    forget2 = commands.indexForget(self.backend, self.session, doc_id=docId2)
    assert forget2["deleted"] == 1

    # 8. 确认完全清空
    statusEmpty = commands.indexStatus(self.backend, self.session)
    assert statusEmpty["status"]["total_docs"] == 0
    assert statusEmpty["status"]["total_chunks"] == 0
    assert len(statusEmpty["documents"]) == 0


class TestApiEdgeCases:
  """边界情况测试"""

  def setup_method(self):
    self.backend = FakeBackend()
    self.session = commands.initSession(self.backend)

  def teardown_method(self):
    commands.closeSession(self.session)

  def test_custom_collection_in_index_add(self):
    """indexAdd 支持指定自定义 collection"""
    result = commands.indexAdd(
      self.backend, self.session,
      source="custom.txt",
      collection_name="my_collection",
    )
    assert result["collection"] == "my_collection"

  def test_index_status_empty_collection(self):
    """空 collection 的 status 应返回 0"""
    status = commands.indexStatus(self.backend, self.session)
    assert status["status"]["total_docs"] == 0
    assert status["status"]["total_chunks"] == 0
    assert len(status["documents"]) == 0

  def test_close_session_is_idempotent(self):
    """closeSession 多次调用不应报错"""
    session = commands.initSession(self.backend)
    commands.closeSession(session)
    commands.closeSession(session)  # 第二次不报错

  def test_session_collection_from_parameter(self):
    """initSession 可通过参数指定 collection"""
    session = commands.initSession(
      self.backend, collection="custom_col"
    )
    assert session.current_collection == "custom_col"
    commands.closeSession(session)
