from unittest.mock import MagicMock

from rag.retriever import RetrievalResult, Retriever


def test_retrieve_with_rerank_sorted_by_rerank_score():
  store = MagicMock()
  store.query.return_value = [
    {
      "chunk_id": "c1",
      "text": "t1",
      "metadata": {
        "source_uri": "u1",
        "source_type": "file",
        "title": "doc1",
        "chunk_index": 1,
      },
      "distance": 0.9,
    },
    {
      "chunk_id": "c2",
      "text": "t2",
      "metadata": {
        "source_uri": "u2",
        "source_type": "file",
        "title": "doc2",
        "chunk_index": 2,
      },
      "distance": 0.1,
    },
  ]

  embeddingClient = MagicMock()
  embeddingClient.embedText.return_value = [0.1, 0.2]

  rerankClient = MagicMock()
  rerankClient.rerankTexts.return_value = [0.2, 0.9]

  retriever = Retriever(store, embeddingClient, rerankClient, top_k=10, rerank_top_k=2)
  results = retriever.retrieve("q")

  assert [r.chunk_id for r in results] == ["c2", "c1"]
  assert results[0].score == 0.9
  rerankClient.rerankTexts.assert_called_once_with("q", ["t1", "t2"])


def test_retrieve_without_rerank_use_distance_score():
  store = MagicMock()
  store.query.return_value = [
    {
      "chunk_id": "c1",
      "text": "t1",
      "metadata": {
        "source_uri": "u1",
        "source_type": "file",
        "title": "doc1",
        "chunk_index": 1,
      },
      "distance": 0.9,
    },
    {
      "chunk_id": "c2",
      "text": "t2",
      "metadata": {
        "source_uri": "u2",
        "source_type": "file",
        "title": "doc2",
        "chunk_index": 2,
      },
      "distance": 0.1,
    },
  ]

  embeddingClient = MagicMock()
  embeddingClient.embedText.return_value = [0.1, 0.2]

  retriever = Retriever(store, embeddingClient, rerank_client=None, top_k=10, rerank_top_k=2)
  results = retriever.retrieve("q")

  assert [r.chunk_id for r in results] == ["c2", "c1"]
  assert results[0].score == 0.9


def test_retrieve_empty_store_return_empty_list():
  store = MagicMock()
  store.query.return_value = []
  embeddingClient = MagicMock()
  embeddingClient.embedText.return_value = [0.1, 0.2]

  retriever = Retriever(store, embeddingClient, rerank_client=None)
  results = retriever.retrieve("q")

  assert results == []


def test_retrieval_result_fields():
  r = RetrievalResult(
    chunk_id="c",
    text="t",
    score=0.1,
    source_uri="u",
    source_type="file",
    title="doc",
    chunk_index=3,
  )
  assert r.chunk_index == 3
