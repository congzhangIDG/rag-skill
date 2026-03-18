from unittest.mock import MagicMock, patch

import pytest
import requests

from rag.embedding import (
  EmbeddingAPIError,
  EmbeddingClient,
  EmbeddingDimensionError,
  EmbeddingTimeoutError,
)


def _makeOkResponse(vectors):
  mock_resp = MagicMock()
  mock_resp.status_code = 200
  mock_resp.json.return_value = [vectors]
  mock_resp.text = "OK"
  return mock_resp


def testEmbedTexts_ok_returnsVectors_andRequestBody():
  vec1 = [0.1] * 768
  vec2 = [0.2] * 768
  mock_resp = _makeOkResponse([vec1, vec2])

  with patch("requests.post", return_value=mock_resp) as mock_post:
    client = EmbeddingClient("http://test/embed")
    vectors = client.embedTexts(["hello", "world"])

  assert vectors == [vec1, vec2]
  assert mock_post.call_count == 1
  assert mock_post.call_args.kwargs["json"] == {"inputs": ["hello", "world"]}


def testEmbedTexts_dimensionMismatch_raisesEmbeddingDimensionError():
  vec1 = [0.1] * 512
  mock_resp = _makeOkResponse([vec1])

  with patch("requests.post", return_value=mock_resp):
    client = EmbeddingClient("http://test/embed")
    with pytest.raises(EmbeddingDimensionError) as exc:
      client.embedTexts(["hello"])

  assert exc.value.expected == 768
  assert exc.value.got == 512


def testEmbedTexts_batchSplit_callsTwice():
  texts = [f"t{i}" for i in range(20)]
  vec = [0.1] * 768
  resp1 = _makeOkResponse([vec] * 16)
  resp2 = _makeOkResponse([vec] * 4)

  with patch("requests.post", side_effect=[resp1, resp2]) as mock_post:
    client = EmbeddingClient("http://test/embed")
    vectors = client.embedTexts(texts)

  assert len(vectors) == 20
  assert mock_post.call_count == 2
  assert mock_post.call_args_list[0].kwargs["json"] == {"inputs": texts[:16]}
  assert mock_post.call_args_list[1].kwargs["json"] == {"inputs": texts[16:]}


def testEmbedTexts_http500_raisesEmbeddingAPIError():
  mock_resp = MagicMock()
  mock_resp.status_code = 500
  mock_resp.text = "boom"

  with patch("requests.post", return_value=mock_resp):
    client = EmbeddingClient("http://test/embed")
    with pytest.raises(EmbeddingAPIError) as exc:
      client.embedTexts(["hello"])

  assert exc.value.status_code == 500
  assert exc.value.response_body == "boom"


def testEmbedTexts_timeout_retriesThreeTimes_thenRaisesEmbeddingTimeoutError():
  with patch("time.sleep", return_value=None):
    with patch("requests.post", side_effect=requests.exceptions.Timeout()) as mock_post:
      client = EmbeddingClient("http://test/embed")
      with pytest.raises(EmbeddingTimeoutError):
        client.embedTexts(["hello"])

  assert mock_post.call_count == 3


def testEmbedText_returnsSingleVector():
  vec = [0.1] * 768
  mock_resp = _makeOkResponse([vec])

  with patch("requests.post", return_value=mock_resp):
    client = EmbeddingClient("http://test/embed")
    vector = client.embedText("hello")

  assert vector == vec
