#!/usr/bin/env python3
"""Collects timing data for Phase 5 plots.

Chart 1 sweeps loss from 0% to 95%. At the high end (90%+) each run can take
many seconds, so this script uses a smaller file (data/chart1_input.txt) by
default and gives each run a wall-clock cap. Override with --input and
--max-seconds if needed.
"""

import argparse
import csv
import random
from pathlib import Path

from config import LOSS_RATES, RUNS_PER_POINT
from run_demo import run_demo, DATA


def collect_chart1(quick=False, input_file=None, max_seconds=120.0):
    rates = [0, 10, 20] if quick else LOSS_RATES
    runs = 2 if quick else RUNS_PER_POINT
    out = DATA / "phase5_chart1_timing.csv"
    rows = []

    if input_file is None:
        # Chart 1 default: smaller file so 0-95% sweep finishes in reasonable time.
        chart1_file = DATA / "chart1_input.txt"
        input_file = chart1_file if chart1_file.exists() else (DATA / "sample_input.txt")

    print(f"Chart 1 using input file: {input_file}")
    print(f"Per-run cap: {max_seconds}s. Rates: {rates}. Runs per rate: {runs}.")

    for rate in rates:
        for run in range(1, runs + 1):
            port = random.randint(20001, 40000)
            t = run_demo(option=1, loss=rate, port=port,
                         input_file=input_file, max_seconds=max_seconds)
            if t is None:
                print(f"  rate={rate}% run={run} TIMED OUT (skipped)")
                continue
            rows.append({
                "loss_rate": rate,
                "run": run,
                "completion_time_seconds": round(t, 6),
            })

    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["loss_rate", "run", "completion_time_seconds"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {out}")


def create_phase5_phase_compare_template():
    """Template for Chart 3. Fill in real Phase 1-4 numbers from earlier phases.

    The Phase 5 row is auto-generated from a 10% loss run on the demo file
    (so phases use the same input). Edit the other rows by hand.
    """
    out = DATA / "phase_comparison_timing.csv"
    if out.exists():
        return
    rows = [
        {"phase": "Phase 1", "run": 1, "loss_rate": 10, "completion_time_seconds": 0.0},
        {"phase": "Phase 2", "run": 1, "loss_rate": 10, "completion_time_seconds": 0.0},
        {"phase": "Phase 3", "run": 1, "loss_rate": 10, "completion_time_seconds": 0.0},
        {"phase": "Phase 4", "run": 1, "loss_rate": 10, "completion_time_seconds": 0.0},
        {"phase": "Phase 5", "run": 1, "loss_rate": 10, "completion_time_seconds": 0.0},
    ]
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["phase", "run", "loss_rate", "completion_time_seconds"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Created template {out}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true", help="Use fewer runs for a quick test.")
    p.add_argument("--input", default=None,
                   help="Override the Chart 1 input file (default: data/chart1_input.txt).")
    p.add_argument("--max-seconds", type=float, default=120.0,
                   help="Wall-clock cap per run. Timed-out runs are skipped.")
    args = p.parse_args()
    input_file = Path(args.input) if args.input else None
    collect_chart1(args.quick, input_file, args.max_seconds)
    create_phase5_phase_compare_template()


if __name__ == "__main__":
    main()
