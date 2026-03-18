import time
from typing import Any

import requests


class EmbeddingTimeoutError(Exception):
  pass


class EmbeddingAPIError(Exception):
  def __init__(self, status_code: int, response_body: str):
    self.status_code = status_code
    self.response_body = response_body
    super().__init__(f"Embedding API 错误: HTTP {status_code}")


class EmbeddingDimensionError(Exception):
  def __init__(self, expected: int, got: int):
    self.expected = expected
    self.got = got
    super().__init__(f"向量维度不匹配: 期望 {expected}, 实际 {got}")


class EmbeddingParseError(Exception):
  pass


class EmbeddingClient:
  def __init__(
    self,
    service_url: str,
    batch_size: int = 16,
    dimension: int = 768,
    timeout: int = 60,
  ):
    self.serviceUrl = service_url
    self.batchSize = batch_size
    self.dimension = dimension
    self.timeout = timeout

  def embedTexts(self, texts: list[str]) -> list[list[float]]:
    all_vectors: list[list[float]] = []
    for i in range(0, len(texts), self.batchSize):
      batch = texts[i : i + self.batchSize]
      vectors = self._requestBatch(batch)
      all_vectors.extend(vectors)
    return all_vectors

  def embedText(self, text: str) -> list[float]:
    return self.embedTexts([text])[0]

  def _requestBatch(self, texts: list[str]) -> list[list[float]]:
    last_error: Exception | None = None
    for attempt in range(3):
      try:
        resp = requests.post(
          self.serviceUrl,
          json={"inputs": texts},
          timeout=self.timeout,
        )

        if resp.status_code != 200:
          raise EmbeddingAPIError(resp.status_code, resp.text)

        try:
          data = resp.json()
        except Exception:
          raise EmbeddingParseError("响应不是有效 JSON")

        vectors = self._parseVectors(data)
        self._validateDimension(vectors)
        return vectors
      except (EmbeddingAPIError, EmbeddingDimensionError, EmbeddingParseError):
        raise
      except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        if isinstance(e, requests.exceptions.Timeout):
          last_error = EmbeddingTimeoutError(f"请求超时: {self.serviceUrl}")
        else:
          last_error = EmbeddingTimeoutError(f"连接失败: {self.serviceUrl}")

        if attempt < 2:
          time.sleep(1)
      except Exception as e:
        last_error = EmbeddingTimeoutError(str(e))
        if attempt < 2:
          time.sleep(1)

    if last_error is None:
      last_error = EmbeddingTimeoutError("未知错误")
    raise last_error

  def _parseVectors(self, data: Any) -> list[list[float]]:
    if not isinstance(data, list) or len(data) == 0:
      raise EmbeddingParseError("响应格式异常: 期望嵌套数组")
    vectors = data[0]
    if not isinstance(vectors, list):
      raise EmbeddingParseError("响应格式异常: 期望向量列表")
    return vectors

  def _validateDimension(self, vectors: list[list[float]]):
    for vec in vectors:
      if not isinstance(vec, list):
        raise EmbeddingParseError("响应格式异常: 期望向量为数组")
      if len(vec) != self.dimension:
        raise EmbeddingDimensionError(self.dimension, len(vec))
