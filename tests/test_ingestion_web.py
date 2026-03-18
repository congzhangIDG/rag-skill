from __future__ import annotations

from unittest.mock import Mock, patch

from rag.ingestion.web import WebIngester


def testWebIngesterCanHandle() -> None:
  ingester = WebIngester()

  assert ingester.canHandle("https://example.com/a") is True
  assert ingester.canHandle("http://example.com") is True
  assert ingester.canHandle("https://www.youtube.com/watch?v=abc") is False
  assert ingester.canHandle("https://youtu.be/abc") is False
  assert ingester.canHandle("/tmp/file.txt") is False
  assert ingester.canHandle("ftp://example.com") is False


def testWebIngesterIngestTrafilaturaSuccess() -> None:
  ingester = WebIngester()
  source = "https://example.com/post"
  html = "<html><head><title>HTML 标题</title></head><body>ignored</body></html>"
  extractedWithMetadata = "---\ntitle: 元数据标题\n---\n正文内容"

  with patch("rag.ingestion.web.trafilatura.fetch_url", return_value=html) as fetchUrlMock:
    with patch("rag.ingestion.web.trafilatura.extract") as extractMock:
      extractMock.side_effect = [extractedWithMetadata, "不应调用"]

      doc = ingester.ingest(source)

  fetchUrlMock.assert_called_once_with(source)
  assert doc.text == "正文内容"
  assert doc.title == "元数据标题"
  assert doc.source_type == "web"
  assert doc.source_uri == source
  assert doc.content_bytes == html.encode("utf-8", errors="replace")


def testWebIngesterIngestFallbackRequestsWhenFetchUrlNone() -> None:
  ingester = WebIngester()
  source = "https://example.com/fallback"
  html = "<html><head><title>Fallback</title></head><body><p>Hi</p></body></html>"

  resp = Mock()
  resp.text = html
  resp.content = b"<bytes>"
  resp.raise_for_status = Mock()

  with patch("rag.ingestion.web.trafilatura.fetch_url", return_value=None):
    with patch("rag.ingestion.web.requests.get", return_value=resp) as getMock:
      with patch("rag.ingestion.web.trafilatura.extract", return_value="正文") as extractMock:
        doc = ingester.ingest(source)

  getMock.assert_called_once()
  args, kwargs = getMock.call_args
  assert args[0] == source
  assert kwargs["timeout"] == 30
  assert kwargs["headers"]["User-Agent"] == "Mozilla/5.0 (compatible; RAGBot/1.0)"
  resp.raise_for_status.assert_called_once()
  extractMock.assert_called_once()
  assert doc.text == "正文"
  assert doc.title == "Fallback"
  assert doc.content_bytes == b"<bytes>"


def testWebIngesterIngestFinalFallbackSimpleClean() -> None:
  ingester = WebIngester()
  source = "https://example.com/clean"
  html = (
    "<html>"
    "<head><title>Clean Title</title><style>.x{}</style></head>"
    "<body><header>H</header><nav>N</nav>"
    "<p>Hello <b>World</b></p><script>bad()</script>"
    "<footer>F</footer></body></html>"
  )

  with patch("rag.ingestion.web.trafilatura.fetch_url", return_value=html):
    with patch("rag.ingestion.web.trafilatura.extract", return_value=None):
      doc = ingester.ingest(source)

  assert doc.title == "Clean Title"
  assert doc.text == "Hello World"
