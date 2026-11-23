"""CLI :  python -m game_asset_validator asset.json [--profile pc]   (code de sortie 1 si erreurs)"""
from __future__ import annotations

import argparse
import json
import sys

from .rules import PROFILES, validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="game_asset_validator")
    parser.add_argument("asset_json", help="fichier JSON décrivant l'asset (ou un tableau d'assets)")
    parser.add_argument("--profile", default="pc", choices=sorted(PROFILES))
    args = parser.parse_args(argv)

    with open(args.asset_json, encoding="utf-8") as fh:
        data = json.load(fh)
    assets = data if isinstance(data, list) else [data]

    exit_code = 0
    for asset in assets:
        report = validate(asset, args.profile)
        status = "OK " if report.ok else "KO "
        print(f"{status}{report.asset} [{report.profile}]")
        for issue in report.issues:
            print(f"   {issue.severity.upper():7} {issue.code}: {issue.message}")
        if not report.ok:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
