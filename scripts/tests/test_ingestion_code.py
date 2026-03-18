import os
from typing import List

from rag.ingestion.code import CodeIngester, DirectoryIngester


def _writeBinaryFile(path: str) -> None:
  with open(path, "wb") as f:
    f.write(b"\x00binary")


def _writeTextFile(path: str, text: str) -> None:
  with open(path, "wb") as f:
    f.write(text.encode("utf-8"))


def testCodeIngesterCanHandle() -> None:
  ingester = CodeIngester()
  assert ingester.canHandle("main.py") is True
  assert ingester.canHandle("main.ts") is True
  assert ingester.canHandle("doc.md") is False


def testCodeIngesterIngestCodeFile() -> None:
  ingester = CodeIngester()
  samplePath = os.path.join("tests", "fixtures", "sample.py")
  doc = ingester.ingest(samplePath)

  assert doc.source_type == "code"
  assert doc.source_uri == samplePath
  assert doc.title == "sample.py"
  assert "class Calculator" in doc.text
  assert isinstance(doc.content_bytes, (bytes, bytearray))


def testDirectoryIngesterSkipsNodeModulesAndBinary(tmp_path) -> None:
  root = str(tmp_path)

  keepDir = os.path.join(root, "src")
  os.makedirs(keepDir, exist_ok=True)
  keepFile = os.path.join(keepDir, "main.py")
  _writeTextFile(keepFile, "print('ok')")

  ignoredDir = os.path.join(root, "node_modules", "pkg")
  os.makedirs(ignoredDir, exist_ok=True)
  ignoredFile = os.path.join(ignoredDir, "index.js")
  _writeTextFile(ignoredFile, "console.log('ignore')")

  binaryFile = os.path.join(keepDir, "bin.py")
  _writeBinaryFile(binaryFile)

  ingester = DirectoryIngester()
  docs = ingester.ingest(root)

  uris: List[str] = [d.source_uri for d in docs]
  assert keepFile in uris
  assert ignoredFile not in uris
  assert binaryFile not in uris
