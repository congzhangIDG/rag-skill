from __future__ import annotations

import os
import tempfile
from typing import Any, List
from unittest.mock import Mock, patch

import pytest

from rag.ingestion.youtube import YoutubeIngester


def testCanHandle() -> None:
  ingester = YoutubeIngester()
  assert ingester.canHandle("https://www.youtube.com/watch?v=abc") is True
  assert ingester.canHandle("https://youtu.be/abc") is True
  assert ingester.canHandle("https://example.com/page") is False


def testParseVttDedupAdjacent() -> None:
  ingester = YoutubeIngester()

  vtt = """WEBVTT

00:00:00.000 --> 00:00:01.000
你好

00:00:01.000 --> 00:00:02.000
你好

00:00:02.000 --> 00:00:03.000
世界

00:00:03.000 --> 00:00:04.000
世界

00:00:04.000 --> 00:00:05.000
世界
"""

  with tempfile.TemporaryDirectory() as tmpDir:
    path = os.path.join(tmpDir, "sub.zh.vtt")
    with open(path, "wb") as f:
      f.write(vtt.encode("utf-8"))

    text = ingester._parseVtt(path)
    assert text == "你好\n世界"


def testIngestSubtitleFlowManualFirst() -> None:
  ingester = YoutubeIngester()
  url = "https://www.youtube.com/watch?v=abc"

  def fakeRun(cmd: List[str], capture_output: bool, text: bool, timeout: int) -> Any:
    if cmd[:3] == ["yt-dlp", "--print", "title"]:
      return Mock(stdout="测试标题\n", returncode=0)

    if "--write-sub" in cmd:
      outIndex = cmd.index("-o") + 1
      outTemplate = cmd[outIndex]
      outDir = os.path.dirname(outTemplate)
      with open(os.path.join(outDir, "sub.zh.vtt"), "wb") as f:
        f.write(
          (
            "WEBVTT\n\n"
            "00:00:00.000 --> 00:00:01.000\n你好\n\n"
            "00:00:01.000 --> 00:00:02.000\n你好\n"
          ).encode("utf-8")
        )
      return Mock(stdout="", returncode=0)

    return Mock(stdout="", returncode=0)

  with patch("rag.ingestion.youtube.shutil.which", return_value="yt-dlp"):
    with patch("rag.ingestion.youtube.subprocess.run", side_effect=fakeRun) as runMock:
      doc = ingester.ingest(url)

  assert doc.source_type == "youtube"
  assert doc.source_uri == url
  assert doc.title == "测试标题"
  assert doc.text == "你好"
  assert doc.content_bytes == "你好".encode("utf-8")
  assert any("--write-sub" in call.args[0] for call in runMock.mock_calls)


def testYtDlpMissingRaises() -> None:
  ingester = YoutubeIngester()
  with patch("rag.ingestion.youtube.shutil.which", return_value=None):
    with pytest.raises(RuntimeError) as e:
      ingester.ingest("https://youtu.be/abc")
  assert "yt-dlp 未安装" in str(e.value)


def testWhisperMissingRaisesWhenNoSubtitles() -> None:
  ingester = YoutubeIngester()
  url = "https://www.youtube.com/watch?v=abc"

  def fakeWhich(name: str) -> Any:
    if name == "yt-dlp":
      return "yt-dlp"
    if name == "ffmpeg":
      return None
    return None

  def fakeRun(cmd: List[str], capture_output: bool, text: bool, timeout: int) -> Any:
    if cmd[:3] == ["yt-dlp", "--print", "title"]:
      return Mock(stdout="测试标题\n", returncode=0)
    return Mock(stdout="", returncode=0)

  with patch("rag.ingestion.youtube.shutil.which", side_effect=fakeWhich):
    with patch("rag.ingestion.youtube.subprocess.run", side_effect=fakeRun):
      with pytest.raises(RuntimeError) as e:
        ingester.ingest(url)

  assert "此视频无字幕" in str(e.value)
