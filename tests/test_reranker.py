from typing import List
from unittest.mock import Mock, call, patch

import pytest
import requests

from rag.reranker import RerankAPIError, RerankClient, RerankTimeoutError


def _makeResp(status_code: int, json_data=None, text: str = ""):
  resp = Mock()
  resp.status_code = status_code
  resp.text = text
  if json_data is not None:
    resp.json = Mock(return_value=json_data)
  else:
    resp.json = Mock(side_effect=ValueError("bad json"))
  return resp


@patch("requests.post")
def test_rerankTexts_ok_and_request_format(mockPost: Mock):
  mockPost.return_value = _makeResp(200, [[{"score": 0.9}, {"score": 0.3}]])

  client = RerankClient("http://rerank", batch_size=16, timeout=3)
  scores = client.rerankTexts("q", ["t1", "t2"])

  assert scores == [0.9, 0.3]
  mockPost.assert_called_once_with(
    "http://rerank",
    json={"query": "q", "texts": ["t1", "t2"]},
    timeout=3,
  )


@patch("requests.post")
def test_rerankTexts_batch_split(mockPost: Mock):
  texts: List[str] = [f"t{i}" for i in range(20)]
  scores1 = [{"score": float(i)} for i in range(16)]
  scores2 = [{"score": float(i)} for i in range(4)]
  mockPost.side_effect = [
    _makeResp(200, [scores1]),
    _makeResp(200, [scores2]),
  ]

  client = RerankClient("http://rerank", batch_size=16, timeout=10)
  scores = client.rerankTexts("q", texts)

  assert scores == [float(i) for i in range(16)] + [float(i) for i in range(4)]
  assert mockPost.call_count == 2
  assert mockPost.call_args_list == [
    call(
      "http://rerank",
      json={"query": "q", "texts": texts[:16]},
      timeout=10,
    ),
    call(
      "http://rerank",
      json={"query": "q", "texts": texts[16:]},
      timeout=10,
    ),
  ]


@patch("requests.post")
def test_rerankTexts_http_500_raise_api_error(mockPost: Mock):
  mockPost.return_value = _makeResp(500, json_data=[[{"score": 0.1}]], text="boom")
  client = RerankClient("http://rerank")

  with pytest.raises(RerankAPIError) as e:
    client.rerankTexts("q", ["t1"])

  assert e.value.status_code == 500
  assert e.value.response_body == "boom"


@patch("requests.post")
def test_rerankTexts_timeout_retry_then_fail(mockPost: Mock):
  mockPost.side_effect = requests.exceptions.Timeout("timeout")
  client = RerankClient("http://rerank")

  with pytest.raises(RerankTimeoutError):
    client.rerankTexts("q", ["t1"])

  assert mockPost.call_count == 3
