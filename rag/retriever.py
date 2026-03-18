from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class RetrievalResult:
  chunk_id: str
  text: str
  score: float
  source_uri: str
  source_type: str
  title: str
  chunk_index: int


class Retriever:
  def __init__(
    self,
    store: Any,
    embedding_client: Any,
    rerank_client: Optional[Any] = None,
    top_k: int = 10,
    rerank_top_k: int = 5,
  ):
    self.store = store
    self.embeddingClient = embedding_client
    self.rerankClient = rerank_client
    self.topK = top_k
    self.rerankTopK = rerank_top_k

  def retrieve(self, query: str) -> List[RetrievalResult]:
    queryEmbedding = self.embeddingClient.embedText(query)
    candidates = self.store.query(queryEmbedding, top_k=self.topK, where=None)
    if not candidates:
      return []

    results: List[RetrievalResult] = []
    for item in candidates:
      meta = item.get("metadata") or {}
      distance = item.get("distance")
      try:
        baseScore = 1.0 - float(distance)
      except Exception:
        baseScore = 0.0

      results.append(
        RetrievalResult(
          chunk_id=str(item.get("chunk_id", "")),
          text=str(item.get("text", "")),
          score=baseScore,
          source_uri=str(meta.get("source_uri", "")),
          source_type=str(meta.get("source_type", "")),
          title=str(meta.get("title", "")),
          chunk_index=int(meta.get("chunk_index", 0) or 0),
        )
      )

    if self.rerankClient is None:
      results.sort(key=lambda r: r.score, reverse=True)
      return results[: self.rerankTopK]

    rerankTexts = [r.text for r in results]
    rerankScores = self.rerankClient.rerankTexts(query, rerankTexts)
    for i, score in enumerate(rerankScores):
      if i >= len(results):
        break
      results[i].score = float(score)

    results.sort(key=lambda r: r.score, reverse=True)
    return results[: self.rerankTopK]

  def retrieveAndAnswer(self, question: str, llm_client: Optional[Any] = None) -> dict:
    results = self.retrieve(question)

    sources: List[dict] = []
    contexts: List[str] = []
    sourceRefs: List[dict] = []
    for r in results:
      excerpt = r.text
      if len(excerpt) > 200:
        excerpt = excerpt[:200]

      sources.append(
        {
          "source_uri": r.source_uri,
          "title": r.title,
          "score": float(r.score),
          "excerpt": excerpt,
        }
      )
      contexts.append(r.text)
      sourceRefs.append({"source_uri": r.source_uri, "title": r.title})

    answer = ""
    if llm_client is not None:
      answer = llm_client.generateAnswer(question, contexts, sourceRefs)

    return {
      "answer": answer,
      "sources": sources,
      "chunks_used": len(results),
    }
