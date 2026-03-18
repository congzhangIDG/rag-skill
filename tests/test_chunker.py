import re


from rag.chunker import detectLanguage, splitCodeChunks, splitTextChunks


def test_splitTextChunks_short_text_returns_single_chunk():
  text = "hello world"
  chunks = splitTextChunks(text, chunk_size=600, overlap=100)
  assert len(chunks) == 1
  assert chunks[0].text == text
  assert text[chunks[0].char_start:chunks[0].char_end] == chunks[0].text


def test_splitTextChunks_long_text_multiple_chunks_and_size_limit_and_no_empty():
  text = ("a" * 700) + "\n\n" + ("b" * 700)
  chunks = splitTextChunks(text, chunk_size=600, overlap=100)
  assert len(chunks) >= 3
  for c in chunks:
    assert len(c.text) <= 600
    assert c.text.strip() != ""
    assert text[c.char_start:c.char_end] == c.text


def test_splitTextChunks_overlap_about_100_chars():
  text = "x" * 1500
  chunks = splitTextChunks(text, chunk_size=600, overlap=100, separators=[""])
  assert len(chunks) == 3
  for i in range(len(chunks) - 1):
    a = chunks[i]
    b = chunks[i + 1]
    assert a.char_end - b.char_start == 100
    assert text[a.char_end - 100:a.char_end] == text[b.char_start:b.char_start + 100]


def test_splitTextChunks_char_span_accuracy_for_all_chunks():
  text = "第1段。\n\n第2段。\n\n第3段。" + ("内容" * 500)
  chunks = splitTextChunks(text, chunk_size=300, overlap=50)
  assert len(chunks) >= 2
  for c in chunks:
    assert text[c.char_start:c.char_end] == c.text


def test_splitTextChunks_chinese_text_not_mid_character_and_splits_by_punctuation():
  text = "你好世界。" * 300
  chunks = splitTextChunks(text, chunk_size=120, overlap=20)
  assert len(chunks) >= 3
  for c in chunks:
    assert len(c.text) <= 120
    assert text[c.char_start:c.char_end] == c.text


def test_splitCodeChunks_python_splits_class_and_function_separately_using_fixture():
  with open("tests/fixtures/sample.py", "r", encoding="utf-8") as f:
    code = f.read()

  chunks = splitCodeChunks(code, language="python", chunk_size=600, overlap=100)
  assert len(chunks) >= 2
  for c in chunks:
    assert c.text.strip() != ""
    assert code[c.char_start:c.char_end] == c.text

  joined = "\n---\n".join([c.text for c in chunks])
  assert "class Calculator" in joined
  assert "def fibonacci" in joined

  class_chunk = next(c for c in chunks if "class Calculator" in c.text)
  fib_chunk = next(c for c in chunks if "def fibonacci" in c.text)
  assert "def add" in class_chunk.text
  assert "def multiply" in class_chunk.text
  assert "return fibonacci" in fib_chunk.text
  assert "class Calculator" not in fib_chunk.text

  for c in chunks:
    starts = list(re.finditer(r"^(?:def |class |async def )", c.text, re.MULTILINE))
    assert len(starts) <= 1


def test_detectLanguage_extension_mapping():
  assert detectLanguage("a.py") == "python"
  assert detectLanguage("a.ts") == "typescript"
  assert detectLanguage("a.go") == "go"
  assert detectLanguage("a.java") == "java"
  assert detectLanguage("a.cs") == "csharp"
  assert detectLanguage("a.kt") == "kotlin"
  assert detectLanguage("a.rs") == "rust"
