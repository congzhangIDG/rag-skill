import os
import subprocess
import sys


def test_skill_structure():
  assert os.path.exists("SKILL.md")
  assert os.path.exists("rag/__init__.py")
  assert os.path.exists("config.yaml")
  assert os.path.exists("requirements.txt")
  assert os.path.exists("requirements-optional.txt")


def test_cli_entrypoint():
  result = subprocess.run(
    [sys.executable, "-m", "rag.cli", "--help"],
    capture_output=True,
    text=True,
  )
  assert result.returncode == 0
  assert "index" in result.stdout
  assert "query" in result.stdout
  assert "status" in result.stdout
  assert "forget" in result.stdout


def test_package_importable():
  import rag

  assert hasattr(rag, "__version__")


def test_skill_md_frontmatter():
  import yaml

  with open("SKILL.md", encoding="utf-8") as f:
    content = f.read()
  parts = content.split("---")
  assert len(parts) >= 3
  meta = yaml.safe_load(parts[1])
  assert meta["name"] == "rag"
  assert "Bash" in meta["allowed-tools"]
