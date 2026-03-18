from __future__ import annotations

from typing import Any, Dict, List

import requests


class LLMError(Exception):
  pass


class LLMTimeoutError(LLMError):
  pass


class LLMAPIError(LLMError):
  def __init__(self, status_code: int, response_body: str):
    self.status_code = status_code
    self.response_body = response_body
    super().__init__(f"LLM API 错误: HTTP {status_code}")


class LLMParseError(LLMError):
  pass


class LLMClient:
  def __init__(
    self,
    base_url: str,
    model: str = "default",
    temperature: float = 0.1,
    max_tokens: int = 2048,
    timeout: int = 120,
  ):
    self.baseUrl = base_url.rstrip("/")
    self.model = model
    self.temperature = temperature
    self.maxTokens = max_tokens
    self.timeout = timeout

  def generateAnswer(
    self, question: str, contexts: List[str], source_refs: List[Dict[str, Any]]
  ) -> str:
    """构造 RAG prompt 并调用 LLM。"""

    messages = self._buildPrompt(question, contexts, source_refs)
    url = f"{self.baseUrl}/chat/completions"
    try:
      resp = requests.post(
        url,
        json={
          "model": self.model,
          "messages": messages,
          "temperature": self.temperature,
          "max_tokens": self.maxTokens,
        },
        timeout=self.timeout,
      )
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
      raise LLMTimeoutError(f"请求超时或连接失败: {url}")
    except Exception as e:
      raise LLMTimeoutError(str(e))

    if resp.status_code != 200:
      raise LLMAPIError(resp.status_code, resp.text)

    try:
      data = resp.json()
    except Exception:
      raise LLMParseError("响应不是有效 JSON")

    return self._parseAnswer(data)

  def _buildPrompt(
    self, question: str, contexts: List[str], source_refs: List[Dict[str, Any]]
  ) -> List[Dict[str, str]]:
    systemContent = (
      "你是一个知识库助手。基于以下参考资料回答问题。如果参考资料不足以回答，请明确说明。"
    )

    refLines: List[str] = ["参考资料:"]
    for i, context in enumerate(contexts):
      ref = source_refs[i] if i < len(source_refs) else {}
      sourceUri = str(ref.get("source_uri") or "")
      contextText = self._truncateText(str(context or ""), 500)
      refLines.append(f"[{i + 1}] {sourceUri}: {contextText}")

    userContent = "\n".join(refLines) + f"\n\n问题: {question}"
    return [
      {"role": "system", "content": systemContent},
      {"role": "user", "content": userContent},
    ]

  def _truncateText(self, text: str, max_chars: int) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(cleaned) <= max_chars:
      return cleaned
    return cleaned[:max_chars]

  def _parseAnswer(self, data: Any) -> str:
    if not isinstance(data, dict):
      raise LLMParseError("响应格式异常: 期望对象")

    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
      raise LLMParseError("响应格式异常: 缺少 choices")

    first = choices[0]
    if not isinstance(first, dict):
      raise LLMParseError("响应格式异常: choices[0] 必须为对象")

    message = first.get("message")
    if not isinstance(message, dict):
      raise LLMParseError("响应格式异常: 缺少 message")

    content = message.get("content")
    if not isinstance(content, str):
      raise LLMParseError("响应格式异常: content 必须为字符串")

    return content
