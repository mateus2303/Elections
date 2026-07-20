from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config
from .db import Database
from .pipeline import run_once


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitor auditável de pesquisas eleitorais do TSE")
    parser.add_argument("--config", default="config/monitor_tse.yaml")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("validate-config", "valida a configuração"), ("init-db", "cria o SQLite"), ("run", "executa uma verificação completa")):
        child = sub.add_parser(name, help=help_text)
        child.add_argument("--config", dest="command_config", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = Config.load(args.command_config or args.config)
        errors = config.validate()
        if errors:
            print("Configuração inválida:")
            for error in errors:
                print(f"- {error}")
            return 2
        if args.command == "validate-config":
            print(f"Configuração válida: {config.path}")
            return 0
        db_path = config.path_value("paths", "state_dir") / "monitor_tse.sqlite3"
        if args.command == "init-db":
            db = Database(db_path)
            db.init()
            db.close()
            print(f"Banco inicializado: {db_path}")
            return 0
        if args.command == "run":
            return run_once(config)
        return 2
    except FileNotFoundError as exc:
        print(f"Arquivo não encontrado: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 3
