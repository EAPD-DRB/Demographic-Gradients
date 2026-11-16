# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Refresh the whole library on demand: data -> figures -> analysis.

    uv run scripts/refresh.py            # full refresh (re-pulls the DHS API)
    uv run scripts/refresh.py --no-pull  # no DHS pull; rebuild library, figures, docs

Chains the three build scripts and stamps the data vintage in the README.
Each stage is also runnable on its own:

    build_gradient_library.py   pull the DHS API, rewrite the survey-based files in data/
                                (MICS values come from the copy written by fetch_mics.py)
    check_ogcore_units.py       re-run the OG-Core units check on the new DHS data
    make_figures.py             rebuild figures/ from data/
    build_analysis.py           regenerate the generated documentation from data/

The census and survey adult-mortality files are rebuilt separately, before
the general gradient, which reads them: build_adult_mortality.py (IPUMS),
build_adult_mortality_brazil.py, build_adult_mortality_colombia.py and
build_adult_mortality_survey.py, then build_census_child_mortality.py and
build_general_gradient.py. docs/files.md lists every script and the order of
a full rebuild.
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def run(script, *args):
    print(f"==> {script} {' '.join(args)}")
    subprocess.run(["uv", "run", str(SCRIPTS / script), *args], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--no-pull",
        action="store_true",
        help="skip the DHS API pull; rebuild the library, figures and docs from data/",
    )
    args = ap.parse_args()

    if not args.no_pull:
        run("build_gradient_library.py")  # also stamps the data vintage in the README
        run("check_ogcore_units.py")  # its quintile sets change with the DHS data
    else:
        run("build_gradient_library.py", "--no-pull")  # e.g. after fetch_mics.py
    run("make_figures.py")
    run("build_analysis.py")
    print("refresh complete — review `git diff`, then commit.")


if __name__ == "__main__":
    sys.exit(main())
