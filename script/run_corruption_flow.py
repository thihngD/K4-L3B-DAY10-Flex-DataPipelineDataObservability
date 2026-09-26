from __future__ import annotations

import argparse

from pipelines.corruption_flow import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the lab comparison or the B2 auto-repair pipeline.")
    parser.add_argument(
        "--auto-repair", action="store_true",
        help="Check existing corrupted data and, if validation fails, repair its records using only the data itself.",
    )
    args = parser.parse_args()
    if args.auto_repair:
        from pipelines.auto_repair import main as auto_repair_main

        auto_repair_main()
    else:
        main()
