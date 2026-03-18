import pytest


def testDetectSourceType_youtube():
  from rag.cli import detectSourceType

  assert detectSourceType("https://www.youtube.com/watch?v=abc") == "youtube"
  assert detectSourceType("https://youtu.be/abc") == "youtube"
  assert detectSourceType("www.youtube.com/watch?v=abc") == "youtube"


def testDetectSourceType_http_web():
  from rag.cli import detectSourceType

  assert detectSourceType("https://example.com/a") == "web"
  assert detectSourceType("http://example.com/a") == "web"


def testDetectSourceType_pdf():
  from rag.cli import detectSourceType

  assert detectSourceType("/tmp/a.pdf") == "pdf"
  assert detectSourceType("C:/tmp/a.PDF") == "pdf"


def testDetectSourceType_code_file_extensions():
  from rag.cli import detectSourceType

  assert detectSourceType("a.py") == "code"
  assert detectSourceType("a.ts") == "code"
  assert detectSourceType("a.TSX") == "code"


def testDetectSourceType_text_extensions():
  from rag.cli import detectSourceType

  assert detectSourceType("a.md") == "text"
  assert detectSourceType("a.txt") == "text"
  assert detectSourceType("a.rst") == "text"


def testDetectSourceType_default_text():
  from rag.cli import detectSourceType

  assert detectSourceType("a.unknown") == "text"
  assert detectSourceType("") == "text"


def testArgparse_help_has_commands(capsys):
  from rag.cli import buildParser

  parser = buildParser()
  with pytest.raises(SystemExit):
    parser.parse_args(["--help"])
  out = capsys.readouterr().out
  assert "index" in out
  assert "query" in out
  assert "status" in out
  assert "forget" in out


def testArgparse_parse_index():
  from rag.cli import buildParser
  from rag.cli import handleIndex

  parser = buildParser()
  args = parser.parse_args(["--config", "a.yaml", "index", "./x", "--collection", "c1"])
  assert args.command == "index"
  assert args.input == "./x"
  assert args.collection == "c1"
  assert args.config == "a.yaml"
  assert args.func is handleIndex


def testArgparse_parse_query_flags():
  from rag.cli import buildParser
  from rag.cli import handleQuery

  parser = buildParser()
  args = parser.parse_args(["query", "hello", "--no-rerank", "--no-llm"])
  assert args.command == "query"
  assert args.query == "hello"
  assert args.no_rerank is True
  assert args.no_llm is True
  assert args.func is handleQuery
