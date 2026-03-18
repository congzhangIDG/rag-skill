#!/usr/bin/env bash
# RAG Skill 安装脚本（Linux / macOS）
# 用法：bash ~/.claude/skills/rag/scripts/install.sh [--with-docs] [--with-whisper]

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> 安装 RAG Skill 基础依赖..."
pip install -r "$SCRIPTS_DIR/requirements.txt"

if [[ "${1:-}" == "--with-docs" || "${1:-}" == "--all" ]]; then
  echo "==> 安装文档处理依赖（PDF/DOCX/XLSX）..."
  pip install -r "$SCRIPTS_DIR/requirements-optional.txt"
fi

# 可选：YouTube Whisper 转录（需要 ffmpeg）
if [[ "${1:-}" == "--with-whisper" || "${1:-}" == "--all" ]]; then
  echo "==> 安装 Whisper 转录依赖..."
  pip install openai-whisper
  if ! command -v ffmpeg &>/dev/null; then
    echo "  ⚠ 未检测到 ffmpeg，Whisper 转录需要 ffmpeg。"
    echo "    macOS:  brew install ffmpeg"
    echo "    Ubuntu: sudo apt install ffmpeg"
  fi
fi

# 初始化配置文件（如果不存在）
if [[ ! -f "$SKILL_DIR/config.yaml" ]]; then
  echo "==> 从模板创建 config.yaml..."
  cp "$SKILL_DIR/assets/config.yaml.template" "$SKILL_DIR/config.yaml"
fi

if [[ ! -f "$SKILL_DIR/.env" ]]; then
  echo "==> 从模板创建 .env..."
  cp "$SKILL_DIR/assets/.env.example" "$SKILL_DIR/.env"
  echo "  ⚠ 请编辑 $SKILL_DIR/.env 填入实际服务地址。"
fi

echo "==> 安装完成。"
echo "  配置文件: $SKILL_DIR/config.yaml"
echo "  环境变量: $SKILL_DIR/.env"
echo "  运行测试: cd $SCRIPTS_DIR && pytest"
