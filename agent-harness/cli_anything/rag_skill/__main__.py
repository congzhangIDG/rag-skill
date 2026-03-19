from __future__ import annotations

import sys
from typing import Optional

import click

from cli_anything.rag_skill.core import commands
from cli_anything.rag_skill.core.output import printError, printResult
from cli_anything.rag_skill.core.repl import runRepl
from cli_anything.rag_skill.utils.rag_backend import RagBackend


def createBackend() -> RagBackend:
  return RagBackend()


@click.group(invoke_without_command=True)
@click.option("--config", "config_path", default=None, help="配置文件路径")
@click.option("--collection", "collection_name", default=None, help="覆盖默认 collection")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
@click.pass_context
def cli(ctx: click.Context, config_path: Optional[str], collection_name: Optional[str], as_json: bool) -> None:
  ctx.ensure_object(dict)
  ctx.obj["config_path"] = config_path
  ctx.obj["collection_name"] = collection_name
  ctx.obj["as_json"] = bool(as_json)

  if ctx.invoked_subcommand is None:
    backend = createBackend()
    session = commands.initSession(backend, config_path=config_path, collection=collection_name)
    raise SystemExit(runRepl(backend, session))


@cli.group()
def config() -> None:
  pass


@config.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
  backend = createBackend()
  session = commands.initSession(backend, config_path=ctx.obj.get("config_path"), collection=ctx.obj.get("collection_name"))
  try:
    out = commands.configShow(backend, session)
    printResult(out, as_json=bool(ctx.obj.get("as_json")))
  except Exception as e:
    printError(str(e), as_json=bool(ctx.obj.get("as_json")), errorType=type(e).__name__)
    raise SystemExit(2)
  finally:
    commands.closeSession(session)


@config.command("path")
@click.pass_context
def config_path(ctx: click.Context) -> None:
  backend = createBackend()
  try:
    out = commands.configPath(backend, config_path=ctx.obj.get("config_path"))
    printResult(out, as_json=bool(ctx.obj.get("as_json")))
  except Exception as e:
    printError(str(e), as_json=bool(ctx.obj.get("as_json")), errorType=type(e).__name__)
    raise SystemExit(2)


@cli.group()
def index() -> None:
  pass


@index.command("add")
@click.argument("source")
@click.option("--collection", "collection_name", default=None)
@click.pass_context
def index_add(ctx: click.Context, source: str, collection_name: Optional[str]) -> None:
  backend = createBackend()
  session = commands.initSession(backend, config_path=ctx.obj.get("config_path"), collection=ctx.obj.get("collection_name"))
  try:
    out = commands.indexAdd(backend, session, source=source, collection_name=collection_name)
    printResult(out, as_json=bool(ctx.obj.get("as_json")))
  except Exception as e:
    printError(str(e), as_json=bool(ctx.obj.get("as_json")), errorType=type(e).__name__)
    raise SystemExit(2)
  finally:
    commands.closeSession(session)


@index.command("status")
@click.option("--collection", "collection_name", default=None)
@click.pass_context
def index_status(ctx: click.Context, collection_name: Optional[str]) -> None:
  backend = createBackend()
  session = commands.initSession(backend, config_path=ctx.obj.get("config_path"), collection=ctx.obj.get("collection_name"))
  try:
    out = commands.indexStatus(backend, session, collection_name=collection_name)
    printResult(out, as_json=bool(ctx.obj.get("as_json")))
  except Exception as e:
    printError(str(e), as_json=bool(ctx.obj.get("as_json")), errorType=type(e).__name__)
    raise SystemExit(2)
  finally:
    commands.closeSession(session)


@index.command("forget")
@click.argument("doc_id")
@click.option("--collection", "collection_name", default=None)
@click.pass_context
def index_forget(ctx: click.Context, doc_id: str, collection_name: Optional[str]) -> None:
  backend = createBackend()
  session = commands.initSession(backend, config_path=ctx.obj.get("config_path"), collection=ctx.obj.get("collection_name"))
  try:
    out = commands.indexForget(backend, session, doc_id=doc_id, collection_name=collection_name)
    printResult(out, as_json=bool(ctx.obj.get("as_json")))
  except Exception as e:
    printError(str(e), as_json=bool(ctx.obj.get("as_json")), errorType=type(e).__name__)
    raise SystemExit(2)
  finally:
    commands.closeSession(session)


@cli.group()
def query() -> None:
  pass


@query.command("search")
@click.argument("question")
@click.option("--no-rerank", is_flag=True, default=False)
@click.option("--no-llm", is_flag=True, default=False)
@click.option("--collection", "collection_name", default=None)
@click.pass_context
def query_search(
  ctx: click.Context,
  question: str,
  no_rerank: bool,
  no_llm: bool,
  collection_name: Optional[str],
) -> None:
  backend = createBackend()
  session = commands.initSession(backend, config_path=ctx.obj.get("config_path"), collection=ctx.obj.get("collection_name"))
  try:
    out = commands.querySearch(
      backend,
      session,
      question=question,
      collection_name=collection_name,
      no_rerank=bool(no_rerank),
      no_llm=bool(no_llm),
    )
    printResult(out, as_json=bool(ctx.obj.get("as_json")))
  except Exception as e:
    printError(str(e), as_json=bool(ctx.obj.get("as_json")), errorType=type(e).__name__)
    raise SystemExit(2)
  finally:
    commands.closeSession(session)


@query.command("ask")
@click.argument("question")
@click.option("--collection", "collection_name", default=None)
@click.pass_context
def query_ask(ctx: click.Context, question: str, collection_name: Optional[str]) -> None:
  backend = createBackend()
  session = commands.initSession(backend, config_path=ctx.obj.get("config_path"), collection=ctx.obj.get("collection_name"))
  try:
    out = commands.queryAsk(backend, session, question=question, collection_name=collection_name)
    printResult(out, as_json=bool(ctx.obj.get("as_json")))
  except Exception as e:
    printError(str(e), as_json=bool(ctx.obj.get("as_json")), errorType=type(e).__name__)
    raise SystemExit(2)
  finally:
    commands.closeSession(session)


def main() -> None:
  try:
    cli.main(standalone_mode=False)
  except click.ClickException as e:
    sys.stderr.write(str(e) + "\n")
    raise SystemExit(2)
  except click.Abort:
    raise SystemExit(130)
  except SystemExit:
    raise
  except Exception as e:
    sys.stderr.write(str(e) + "\n")
    raise SystemExit(2)


if __name__ == "__main__":
  main()
