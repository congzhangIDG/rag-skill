from __future__ import annotations

from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from rag.llm import LLMAPIError, LLMClient, LLMTimeoutError


def _makeOkResponse(payload: Dict[str, Any]):
  resp = Mock()
  resp.status_code = 200
  resp.text = "OK"
  resp.json.return_value = payload
  return resp


def testBuildPromptShouldContainSystemAndNumberedRefs():
  client = LLMClient(base_url="http://example.com/v1", model="default")
  messages = client._buildPrompt(
    "问题?",
    ["ctx1", "ctx2"],
    [{"source_uri": "s1"}, {"source_uri": "s2"}],
  )
  assert isinstance(messages, list)
  assert messages[0]["role"] == "system"
  assert messages[1]["role"] == "user"
  userContent = messages[1]["content"]
  assert "[1]" in userContent
  assert "[2]" in userContent
  assert "s1" in userContent
  assert "s2" in userContent


@patch("requests.post")
def testGenerateAnswerShouldReturnContent(mockPost: Mock):
  mockPost.return_value = _makeOkResponse({"choices": [{"message": {"content": "答案"}}]})
  client = LLMClient(base_url="http://example.com/v1", model="default")
  answer = client.generateAnswer("Q", ["ctx"], [{"source_uri": "s"}])
  assert answer == "答案"

  args, kwargs = mockPost.call_args
  assert args[0] == "http://example.com/v1/chat/completions"
  body = kwargs.get("json")
  assert body.get("model") == "default"
  assert "messages" in body


@patch("requests.post")
def testGenerateAnswerShouldRaiseTimeoutOnConnectionError(mockPost: Mock):
  import requests

  mockPost.side_effect = requests.exceptions.ConnectionError("boom")
  client = LLMClient(base_url="http://example.com/v1", model="default")
  with pytest.raises(LLMTimeoutError):
    client.generateAnswer("Q", ["ctx"], [{"source_uri": "s"}])


@patch("requests.post")
def testGenerateAnswerShouldRaiseAPIErrorOnHttp500(mockPost: Mock):
  resp = Mock()
  resp.status_code = 500
  resp.text = "server error"
  mockPost.return_value = resp

  client = LLMClient(base_url="http://example.com/v1", model="default")
  with pytest.raises(LLMAPIError) as e:
    client.generateAnswer("Q", ["ctx"], [{"source_uri": "s"}])
  assert e.value.status_code == 500
