# RAG Skill 安装脚本（Windows PowerShell）
# 用法：powershell -ExecutionPolicy Bypass -File install.ps1 [-WithDocs] [-WithWhisper] [-All]

param(
  [switch]$WithDocs,
  [switch]$WithWhisper,
  [switch]$All
)

$ErrorActionPreference = "Stop"
$SkillDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

Write-Host "==> 安装 RAG Skill 基础依赖..."
pip install -r "$SkillDir\requirements.txt"

if ($WithDocs -or $All) {
  Write-Host "==> 安装文档处理依赖（PDF/DOCX/XLSX）..."
  pip install -r "$SkillDir\requirements-optional.txt"
}

if ($WithWhisper -or $All) {
  Write-Host "==> 安装 Whisper 转录依赖..."
  pip install openai-whisper
  if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Warning "未检测到 ffmpeg，Whisper 转录需要 ffmpeg。"
    Write-Warning "  安装方法: winget install ffmpeg 或 choco install ffmpeg"
  }
}

# 初始化配置文件（如果不存在）
if (-not (Test-Path "$SkillDir\config.yaml")) {
  Write-Host "==> 从模板创建 config.yaml..."
  Copy-Item "$SkillDir\assets\config.yaml.template" "$SkillDir\config.yaml"
}

if (-not (Test-Path "$SkillDir\.env")) {
  Write-Host "==> 从模板创建 .env..."
  Copy-Item "$SkillDir\assets\.env.example" "$SkillDir\.env"
  Write-Warning "请编辑 $SkillDir\.env 填入实际服务地址。"
}

Write-Host "==> 安装完成。"
Write-Host "  配置文件: $SkillDir\config.yaml"
Write-Host "  环境变量: $SkillDir\.env"
Write-Host "  运行测试: cd $SkillDir; pytest"
