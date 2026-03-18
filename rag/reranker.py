import time
from typing import Any, List, Optional

import requests


class RerankTimeoutError(Exception):
  pass


class RerankAPIError(Exception):
  def __init__(self, status_code: int, response_body: str):
    self.status_code = status_code
    self.response_body = response_body
    super().__init__(f"Rerank API 错误: HTTP {status_code}")


class RerankParseError(Exception):
  pass


class RerankClient:
  def __init__(self, service_url: str, batch_size: int = 16, timeout: int = 60):
    self.serviceUrl = service_url
    self.batchSize = batch_size
    self.timeout = timeout

  def rerankTexts(self, query: str, texts: List[str]) -> List[float]:
    allScores: List[float] = []
    for i in range(0, len(texts), self.batchSize):
      batch = texts[i : i + self.batchSize]
      scores = self._requestBatch(query, batch)
      allScores.extend(scores)
    return allScores

  def _requestBatch(self, query: str, texts: List[str]) -> List[float]:
    lastError: Optional[Exception] = None
    for attempt in range(3):
      try:
        resp = requests.post(
          self.serviceUrl,
          json={"query": query, "texts": texts},
          timeout=self.timeout,
        )

        if resp.status_code != 200:
          raise RerankAPIError(resp.status_code, resp.text)

        try:
          data = resp.json()
        except Exception:
          raise RerankParseError("响应不是有效 JSON")

        scores = self._parseScores(data)
        if len(scores) != len(texts):
          raise RerankParseError(
            f"响应数量不匹配: 期望 {len(texts)}, 实际 {len(scores)}"
          )
        return scores
      except (RerankAPIError, RerankParseError):
        raise
      except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        if isinstance(e, requests.exceptions.Timeout):
          lastError = RerankTimeoutError(f"请求超时: {self.serviceUrl}")
        else:
          lastError = RerankTimeoutError(f"连接失败: {self.serviceUrl}")
        if attempt < 2:
          time.sleep(1)
      except Exception as e:
        lastError = RerankTimeoutError(str(e))
        if attempt < 2:
          time.sleep(1)

    if lastError is None:
      lastError = RerankTimeoutError("未知错误")
    raise lastError

  def _parseScores(self, data: Any) -> List[float]:
    if not isinstance(data, list) or len(data) == 0:
      raise RerankParseError("响应格式异常: 期望嵌套数组")
    items = data[0]
    if not isinstance(items, list):
      raise RerankParseError("响应格式异常: 期望对象列表")

    scores: List[float] = []
    for item in items:
      if not isinstance(item, dict) or "score" not in item:
        raise RerankParseError("响应格式异常: 期望包含 score 字段")
      score = item.get("score")
      if not isinstance(score, (int, float)):
        raise RerankParseError("响应格式异常: score 必须为数字")
      scores.append(float(score))
    return scores
