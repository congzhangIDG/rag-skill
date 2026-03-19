from setuptools import find_namespace_packages, setup


setup(
  name="cli-anything-rag-skill",
  version="0.1.0",
  description="CLI-Anything harness for scripts/rag backend",
  python_requires=">=3.9",
  packages=find_namespace_packages(include=["cli_anything.*"]),
  install_requires=[
    "click>=8.1.0",
    "chromadb>=1.0.0",
    "requests>=2.31.0",
    "pyyaml>=6.0",
    "trafilatura>=2.0.0",
    "yt-dlp>=2024.0.0",
    "filelock>=3.0.0",
    "pysqlite3>=0.5.2",
  ],
  extras_require={
    "test": [
      "pytest>=7.0.0",
    ],
  },
  entry_points={
    "console_scripts": [
      "cli-anything-rag-skill=cli_anything.rag_skill.__main__:main",
    ],
  },
  package_data={
    "cli_anything.rag_skill": [
      "README.md",
    ],
  },
  include_package_data=True,
)
