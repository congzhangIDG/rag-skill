import os

from rag.ingestion.text import TextIngester


def testTextIngesterCanHandle() -> None:
  ingester = TextIngester()
  assert ingester.canHandle("test.md") is True
  assert ingester.canHandle("test.txt") is True
  assert ingester.canHandle("test.rst") is True
  assert ingester.canHandle("test.pdf") is False


def testTextIngesterIngestMarkdownTitleAndText() -> None:
  ingester = TextIngester()
  samplePath = os.path.join("tests", "fixtures", "sample.md")
  doc = ingester.ingest(samplePath)

  assert doc.title == "测试文档：向量检索原理"
  assert "向量检索是一种基于向量空间模型" in doc.text
  assert doc.source_uri == samplePath
  assert isinstance(doc.content_bytes, (bytes, bytearray))
