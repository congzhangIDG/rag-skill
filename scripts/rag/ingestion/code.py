from __future__ import annotations

import os
from typing import List, Optional

from rag.ingestion.base import BaseIngester, IngestedDocument


class CodeIngester(BaseIngester):
  def __init__(
    self,
    codeExtensions: Optional[List[str]] = None,
  ) -> None:
    self._codeExtensions = set(
      (codeExtensions or [
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".go",
        ".rs",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".cs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
      ])
    )

  def canHandle(self, source: str) -> bool:
    ext = os.path.splitext(source)[1].lower()
    return ext in self._codeExtensions

  def ingest(self, source: str) -> IngestedDocument:
    with open(source, "rb") as f:
      contentBytes = f.read()

    text = contentBytes.decode("utf-8", errors="replace")
    title = os.path.basename(source)

    return IngestedDocument(
      text=text,
      title=title,
      source_type="code",
      source_uri=source,
      content_bytes=contentBytes,
    )


class DirectoryIngester:
  def __init__(
    self,
    codeExtensions: Optional[List[str]] = None,
    ignorePatterns: Optional[List[str]] = None,
    maxFileSizeMb: float = 10,
  ) -> None:
    self._codeIngester = CodeIngester(codeExtensions=codeExtensions)
    self._ignorePatterns = ignorePatterns or [
      "node_modules",
      ".git",
      "__pycache__",
      ".venv",
      "dist",
      "build",
      ".next",
    ]
    self._maxFileSizeBytes = int(maxFileSizeMb * 1024 * 1024)

  def ingest(self, source: str) -> List[IngestedDocument]:
    docs: List[IngestedDocument] = []

    if not os.path.isdir(source):
      return docs

    for root, dirNames, fileNames in os.walk(source, followlinks=False):
      keptDirNames: List[str] = []
      for dirName in dirNames:
        dirPath = os.path.join(root, dirName)
        if os.path.islink(dirPath):
          continue
        if self._shouldIgnorePath(dirPath, baseDir=source):
          continue
        keptDirNames.append(dirName)
      dirNames[:] = keptDirNames

      for fileName in sorted(fileNames):
        filePath = os.path.join(root, fileName)
        if os.path.islink(filePath):
          continue
        if self._shouldIgnorePath(filePath, baseDir=source):
          continue
        if not self._codeIngester.canHandle(filePath):
          continue
        if self._isTooLarge(filePath):
          continue
        if self._isBinaryFile(filePath):
          continue

        docs.append(self._codeIngester.ingest(filePath))

    return docs

  def _shouldIgnorePath(self, path: str, baseDir: str) -> bool:
    relPath = os.path.relpath(path, baseDir)
    parts = relPath.split(os.sep)
    for part in parts:
      if part in self._ignorePatterns:
        return True
    return False

  def _isBinaryFile(self, filePath: str) -> bool:
    try:
      with open(filePath, "rb") as f:
        head = f.read(8192)
      return b"\x00" in head
    except OSError:
      return True

  def _isTooLarge(self, filePath: str) -> bool:
    try:
      size = os.path.getsize(filePath)
      return size > self._maxFileSizeBytes
    except OSError:
      return True
