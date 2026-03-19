from __future__ import annotations

import cmd
import shlex
from typing import Any, List, Optional, Tuple

from cli_anything.rag_skill.core import commands
from cli_anything.rag_skill.core.output import printError, printResult
from cli_anything.rag_skill.core.session import RagSession


def _parseJsonFlag(argv: List[str]) -> Tuple[bool, List[str]]:
  asJson = False
  out: List[str] = []
  for a in argv:
    if a == "--json":
      asJson = True
      continue
    out.append(a)
  return asJson, out


class RagRepl(cmd.Cmd):
  prompt = "rag-skill> "

  def __init__(self, backend: Any, session: RagSession):
    super().__init__()
    self.backend = backend
    self.session = session

  def preloop(self) -> None:
    self.intro = "输入 help 查看可用命令"

  def emptyline(self) -> bool:
    return False

  def precmd(self, line: str) -> str:
    stripped = (line or "").strip()
    if stripped:
      self.session.history.append(stripped)
    return line

  def do_exit(self, arg: str) -> bool:
    return True

  def do_quit(self, arg: str) -> bool:
    return True

  def do_history(self, arg: str) -> None:
    argv = shlex.split(arg or "")
    asJson, argv = _parseJsonFlag(argv)
    if asJson:
      printResult({"history": list(self.session.history)}, as_json=True)
      return
    for i, line in enumerate(self.session.history):
      print(f"{i + 1}: {line}")

  def do_use(self, arg: str) -> None:
    argv = shlex.split(arg or "")
    asJson, argv = _parseJsonFlag(argv)
    if not argv:
      printError("用法: use <collection>", as_json=asJson)
      return
    name = str(argv[0]).strip()
    if not name:
      printError("用法: use <collection>", as_json=asJson)
      return
    self.session.current_collection = name
    printResult({"collection": name}, as_json=asJson)

  def _extractCollectionOption(self, argv: List[str]) -> Tuple[Optional[str], List[str]]:
    collectionName: Optional[str] = None
    out: List[str] = []
    i = 0
    while i < len(argv):
      a = argv[i]
      if a == "--collection":
        if i + 1 >= len(argv):
          raise RuntimeError("--collection 需要参数")
        collectionName = argv[i + 1]
        i += 2
        continue
      out.append(a)
      i += 1
    return collectionName, out

  def do_config(self, arg: str) -> None:
    argv = shlex.split(arg or "")
    asJson, argv = _parseJsonFlag(argv)
    if not argv:
      printError("用法: config show|path", as_json=asJson)
      return

    sub = argv[0]
    try:
      if sub == "show":
        out = commands.configShow(self.backend, self.session)
        printResult(out, as_json=asJson)
        return
      if sub == "path":
        meta = (self.session.config.get("__harness__") or {}) if isinstance(self.session.config, dict) else {}
        configPath = meta.get("config_path") if isinstance(meta, dict) else None
        out = {"config_path": configPath}
        printResult(out, as_json=asJson)
        return
      printError("不支持的子命令: config " + sub, as_json=asJson)
    except Exception as e:
      printError(str(e), as_json=asJson, errorType=type(e).__name__)

  def do_index(self, arg: str) -> None:
    argv = shlex.split(arg or "")
    asJson, argv = _parseJsonFlag(argv)
    if not argv:
      printError("用法: index add|status|forget ...", as_json=asJson)
      return
    sub = argv[0]

    try:
      if sub == "add":
        collectionName, argv = self._extractCollectionOption(argv)
        if len(argv) < 2:
          printError("用法: index add <source>", as_json=asJson)
          return
        out = commands.indexAdd(self.backend, self.session, source=argv[1], collection_name=collectionName)
        printResult(out, as_json=asJson)
        return
      if sub == "status":
        collectionName, argv = self._extractCollectionOption(argv)
        out = commands.indexStatus(self.backend, self.session, collection_name=collectionName)
        printResult(out, as_json=asJson)
        return
      if sub == "forget":
        collectionName, argv = self._extractCollectionOption(argv)
        if len(argv) < 2:
          printError("用法: index forget <doc_id>", as_json=asJson)
          return
        out = commands.indexForget(self.backend, self.session, doc_id=argv[1], collection_name=collectionName)
        printResult(out, as_json=asJson)
        return
      printError("不支持的子命令: index " + sub, as_json=asJson)
    except Exception as e:
      printError(str(e), as_json=asJson, errorType=type(e).__name__)

  def do_query(self, arg: str) -> None:
    argv = shlex.split(arg or "")
    asJson, argv = _parseJsonFlag(argv)
    if not argv:
      printError("用法: query search|ask ...", as_json=asJson)
      return
    sub = argv[0]
    try:
      if sub == "search":
        collectionName, argv = self._extractCollectionOption(argv)
        if len(argv) < 2:
          printError("用法: query search <question>", as_json=asJson)
          return
        noRerank = "--no-rerank" in argv
        noLlm = "--no-llm" in argv
        qParts = [a for a in argv[1:] if a not in {"--no-rerank", "--no-llm"}]
        question = " ".join(qParts).strip()
        out = commands.querySearch(
          self.backend,
          self.session,
          question=question,
          collection_name=collectionName,
          no_rerank=noRerank,
          no_llm=noLlm,
        )
        printResult(out, as_json=asJson)
        return
      if sub == "ask":
        collectionName, argv = self._extractCollectionOption(argv)
        if len(argv) < 2:
          printError("用法: query ask <question>", as_json=asJson)
          return
        question = " ".join(argv[1:]).strip()
        out = commands.queryAsk(self.backend, self.session, question=question, collection_name=collectionName)
        printResult(out, as_json=asJson)
        return
      printError("不支持的子命令: query " + sub, as_json=asJson)
    except Exception as e:
      printError(str(e), as_json=asJson, errorType=type(e).__name__)

  def default(self, line: str) -> None:
    stripped = (line or "").strip()
    if not stripped:
      return
    argv = shlex.split(stripped)
    if not argv:
      return
    cmdName = argv[0]
    rest = " ".join(argv[1:])
    if cmdName in {"config", "index", "query", "use", "history", "help", "exit", "quit"}:
      if cmdName == "config":
        self.do_config(rest)
        return
      if cmdName == "index":
        self.do_index(rest)
        return
      if cmdName == "query":
        self.do_query(rest)
        return
      if cmdName == "use":
        self.do_use(rest)
        return
      if cmdName == "history":
        self.do_history(rest)
        return
      if cmdName == "help":
        self.do_help(rest)
        return
      if cmdName == "exit":
        self.do_exit(rest)
        return
      if cmdName == "quit":
        self.do_quit(rest)
        return
      return
    printError("未知命令: " + cmdName, as_json=False)


def runRepl(backend: Any, session: commands.RagSession) -> int:
  repl = RagRepl(backend=backend, session=session)
  try:
    while True:
      try:
        repl.cmdloop()
        return 0
      except KeyboardInterrupt:
        printError("已中断（Ctrl-C）。输入 exit 退出。", as_json=False)
        continue
  finally:
    commands.closeSession(session)
