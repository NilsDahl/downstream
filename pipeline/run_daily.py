"""
run_daily.py — orchestrates fetch_data → generate_draft.

Usage:
  python run_daily.py              # run now
  python run_daily.py --schedule   # print the cron line to add

Scheduling (Stockholm time = CET/CEST):
  Add to crontab with:  crontab -e
  30 9 * * 1-5  cd /path/to/downstream && python pipeline/run_daily.py >> logs/daily.log 2>&1
"""

import os
import subprocess
import sys
from datetime import datetime

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR     = os.path.dirname(PIPELINE_DIR)


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_step(label: str, script: str, extra_args: list[str] | None = None) -> str | None:
    """Run a pipeline script. Returns the last non-empty output line (for path passing)."""
    args = [sys.executable, os.path.join(PIPELINE_DIR, script)] + (extra_args or [])
    log(f"Starting: {label}")
    result = subprocess.run(args, capture_output=False, text=True)
    if result.returncode != 0:
        log(f"ERROR: {label} exited with code {result.returncode}")
        sys.exit(result.returncode)
    log(f"Done: {label}")


def main():
    if "--schedule" in sys.argv:
        print(
            "Add this line to your crontab (crontab -e) to run at 09:30 Stockholm time:\n"
            f"30 9 * * 1-5  cd {ROOT_DIR} && "
            f"{sys.executable} {os.path.join(PIPELINE_DIR, 'run_daily.py')} "
            f">> {os.path.join(ROOT_DIR, 'logs', 'daily.log')} 2>&1"
        )
        return

    os.makedirs(os.path.join(ROOT_DIR, "logs"), exist_ok=True)
    log("=== Downstream daily pipeline starting ===")

    # Step 1: fetch market data
    run_step("fetch_data", "fetch_data.py")

    # Step 2: generate draft (uses today's snapshot by default)
    run_step("generate_draft", "generate_draft.py")

    log("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
