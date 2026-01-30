from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .core import (
    GeneratorError,
    generate_all,
    generate_resource,
    reset_stale_cache_used,
    stale_cache_used,
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="generator")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate dist/*.rsc")
    gen.add_argument("--resource", help="resource_id to generate")
    gen.add_argument("--all", action="store_true", help="generate all resources")
    gen.add_argument("--base-dir", default=".", help="repository base dir")
    gen.add_argument(
        "--allow-cache",
        action="store_true",
        help="allow using cached URL responses only on HTTP 304",
    )
    gen.add_argument(
        "--allow-stale-cache",
        action="store_true",
        help="allow using cached URL responses on non-200/timeout (stale)",
    )

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)

    if args.command == "generate":
        if bool(args.resource) == bool(args.all):
            print("error: specify --resource or --all", file=sys.stderr)
            return 2

        base_dir = Path(args.base_dir).resolve()
        reset_stale_cache_used()
        try:
            if args.all:
                generate_all(
                    base_dir,
                    allow_cache=args.allow_cache,
                    allow_stale_cache=args.allow_stale_cache,
                )
            else:
                generate_resource(
                    args.resource,
                    base_dir,
                    allow_cache=args.allow_cache,
                    allow_stale_cache=args.allow_stale_cache,
                )
            if args.allow_stale_cache and stale_cache_used():
                print("CACHE_STALE_USED=true")
        except GeneratorError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
