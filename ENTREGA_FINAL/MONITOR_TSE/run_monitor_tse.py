"""Ponto de entrada simples para execução do Monitor TSE.

Uso:
    python run_monitor_tse.py
    python run_monitor_tse.py --config caminho\\para\\monitor_tse.yaml

O programa atualiza o SQLite, preserva snapshots e gera:
    ENTREGA_FINAL/MONITOR_TSE/monitor_pesquisas_tse.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from monitor_tse.config import Config  # noqa: E402
from monitor_tse.pipeline import run_once  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa o monitor de pesquisas eleitorais do TSE")
    parser.add_argument(
        "--config",
        default=str(ROOT / "config" / "monitor_tse.yaml"),
        help="arquivo YAML de configuração (padrão: config/monitor_tse.yaml)",
    )
    args = parser.parse_args()

    config = Config.load(args.config)
    errors = config.validate()
    if errors:
        print("Configuração inválida:")
        for error in errors:
            print(f"- {error}")
        return 2

    exit_code = run_once(config)
    print(f"Execução concluída com código {exit_code}.")
    print(f"Planilha: {config.path_value('paths', 'output_dir') / 'monitor_pesquisas_tse.xlsx'}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
