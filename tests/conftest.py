import pytest
import tempfile
import os


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
