# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Refresh the whole library on demand: data -> figures -> analysis.

    uv run scripts/refresh.py            # full refresh (re-pulls the DHS API)
    uv run scripts/refresh.py --no-pull  # keep data/, rebuild figures + docs only

Chains the three build scripts and stamps the data vintage in the README.
Each stage is also runnable on its own:

    build_gradient_library.py   pull the DHS API, rewrite data/
    make_figures.py             rebuild figures/ from data/
    build_analysis.py           regenerate ANALYSIS.md + README numbers from data/
"""

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def run(script):
    print(f"==> {script}")
    subprocess.run(["uv", "run", str(SCRIPTS / script)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--no-pull",
        action="store_true",
        help="skip the DHS API pull; rebuild figures and docs from existing data/",
    )
    args = ap.parse_args()

    if not args.no_pull:
        run("build_gradient_library.py")
        # Stamp the data vintage wherever the README states it
        readme = ROOT / "README.md"
        today = datetime.date.today().strftime("%-d %B %Y")
        text = re.sub(r"API pull of \d{1,2} \w+ \d{4}", f"API pull of {today}", readme.read_text())
        readme.write_text(text)
        print(f"stamped data vintage: {today}")

    run("make_figures.py")
    run("build_analysis.py")
    print("refresh complete — review `git diff`, then commit.")


if __name__ == "__main__":
    sys.exit(main())
