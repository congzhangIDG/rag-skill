from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from typing import Optional

from rag.ingestion.base import BaseIngester, IngestedDocument


class YoutubeIngester(BaseIngester):
  def canHandle(self, source: str) -> bool:
    sourceLower = source.lower()
    return "youtube.com" in sourceLower or "youtu.be" in sourceLower

  def ingest(self, source: str) -> IngestedDocument:
    url = source

    if shutil.which("yt-dlp") is None:
      raise RuntimeError("yt-dlp 未安装，请执行: pip install yt-dlp")

    with tempfile.TemporaryDirectory() as tmpDir:
      title = self._getTitle(url)
      text = self._extractSubtitles(url, output_dir=tmpDir)
      if text is None:
        text = self._transcribeWithWhisper(url, output_dir=tmpDir)

      contentBytes = text.encode("utf-8")
      return IngestedDocument(
        text=text,
        title=title,
        source_type="youtube",
        source_uri=url,
        content_bytes=contentBytes,
      )

  def _getTitle(self, url: str) -> str:
    cmd = ["yt-dlp", "--print", "title", url]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    title = (result.stdout or "").strip()
    return title or url

  def _extractSubtitles(self, url: str, output_dir: str) -> Optional[str]:
    outputTemplate = os.path.join(output_dir, "sub")

    manualCmd = [
      "yt-dlp",
      "--write-sub",
      "--sub-lang",
      "zh,en",
      "--skip-download",
      "-o",
      outputTemplate,
      url,
    ]
    subprocess.run(manualCmd, capture_output=True, text=True, timeout=300)
    vttPath = self._findFirstVtt(output_dir)
    if vttPath:
      return self._parseVtt(vttPath)

    autoCmd = [
      "yt-dlp",
      "--write-auto-sub",
      "--sub-lang",
      "zh,en",
      "--skip-download",
      "-o",
      outputTemplate,
      url,
    ]
    subprocess.run(autoCmd, capture_output=True, text=True, timeout=300)
    vttPath = self._findFirstVtt(output_dir)
    if vttPath:
      return self._parseVtt(vttPath)

    return None

  def _findFirstVtt(self, output_dir: str) -> Optional[str]:
    try:
      files = os.listdir(output_dir)
    except OSError:
      return None

    vttFiles = [f for f in files if f.lower().endswith(".vtt")]
    if not vttFiles:
      return None
    vttFiles.sort()
    return os.path.join(output_dir, vttFiles[0])

  def _transcribeWithWhisper(self, url: str, output_dir: str) -> str:
    if shutil.which("ffmpeg") is None:
      raise RuntimeError(
        "此视频无字幕。如需音频转录，请安装 whisper 和 ffmpeg: pip install openai-whisper"
      )

    try:
      import whisper  # type: ignore
    except ImportError as e:
      raise RuntimeError(
        "此视频无字幕。如需音频转录，请安装 whisper 和 ffmpeg: pip install openai-whisper"
      ) from e

    outputTemplate = os.path.join(output_dir, "audio.%(ext)s")
    cmd = [
      "yt-dlp",
      "-x",
      "--audio-format",
      "wav",
      "-o",
      outputTemplate,
      url,
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    audioPath = os.path.join(output_dir, "audio.wav")
    if not os.path.exists(audioPath):
      try:
        files = os.listdir(output_dir)
      except OSError:
        files = []
      wavFiles = [f for f in files if f.lower().endswith(".wav")]
      if not wavFiles:
        raise RuntimeError("音频下载失败，未生成 wav 文件")
      wavFiles.sort()
      audioPath = os.path.join(output_dir, wavFiles[0])

    model = whisper.load_model("base")
    result = model.transcribe(audioPath)
    text = (result.get("text") if isinstance(result, dict) else None) or ""
    return text.strip()

  def _parseVtt(self, vtt_path: str) -> str:
    with open(vtt_path, "rb") as f:
      contentBytes = f.read()
    content = contentBytes.decode("utf-8", errors="replace")

    lines = content.splitlines()
    if lines and lines[0].strip().upper() == "WEBVTT":
      lines = lines[1:]

    timePattern = re.compile(
      r"^\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}"
    )

    cleaned: list[str] = []
    for line in lines:
      stripped = line.strip()
      if not stripped:
        continue
      if timePattern.match(stripped):
        continue
      if stripped.isdigit():
        continue
      cleaned.append(stripped)

    deduped: list[str] = []
    last: Optional[str] = None
    for item in cleaned:
      if last is not None and item == last:
        continue
      deduped.append(item)
      last = item

    return "\n".join(deduped).strip()
