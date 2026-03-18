import pytest
import tempfile
import os

from unittest.mock import MagicMock


@pytest.fixture
def tmp_persist_dir():
    """临时 ChromaDB 持久化目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def fixtures_dir():
    """测试 fixture 目录"""
    return os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def sample_md_path(fixtures_dir):
    """sample.md 路径"""
    return os.path.join(fixtures_dir, "sample.md")


@pytest.fixture
def sample_py_path(fixtures_dir):
    """sample.py 路径"""
    return os.path.join(fixtures_dir, "sample.py")


@pytest.fixture
def mock_embedding_client():
    client = MagicMock()

    def _embed_texts(texts):
        import hashlib

        vectors = []
        for t in texts:
            h = hashlib.md5(t.encode()).hexdigest()
            vec = [float(int(h[i:i + 2], 16)) / 255.0 for i in range(0, min(len(h), 32), 2)]
            vec = (vec * 48)[:768]
            vectors.append(vec)
        return vectors

    client.embedTexts.side_effect = _embed_texts
    client.embedText.side_effect = lambda t: _embed_texts([t])[0]
    return client


@pytest.fixture
def mock_rerank_client():
    client = MagicMock()

    def _rerank(query, texts):
        scores = [1.0 - (i * 0.1) for i in range(len(texts))]
        return scores

    client.rerankTexts.side_effect = _rerank
    return client
