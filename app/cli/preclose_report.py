from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from typing import Sequence

from app.core.config import load_settings
from app.services.preclose_report_run import run_preclose_report_once


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the 14:55 report once.")
    parser.add_argument("--as-of", dest="as_of", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    try:
        as_of = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now()
    except ValueError:
        parser.error("--as-of must use YYYY-MM-DDTHH:MM:SS")

    try:
        result = run_preclose_report_once(load_settings(), as_of, force=args.force)
    except Exception as exc:
        print(f"preclose report run failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
