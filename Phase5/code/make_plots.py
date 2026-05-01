#!/usr/bin/env python3
"""Makes the three required Phase 5 plots."""

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def plot_chart1(input_csv=DATA / "phase5_chart1_timing.csv", output_png=DATA / "chart1_phase5_loss.png"):
    times = defaultdict(list)
    with open(input_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            times[int(row["loss_rate"])].append(float(row["completion_time_seconds"]))
    x = sorted(times)
    y = [mean(times[k]) for k in x]
    plt.figure()
    plt.plot(x, y, marker="o")
    plt.xlabel("Packet Loss Rate (%)")
    plt.ylabel("Average Completion Time (seconds)")
    plt.title("Chart 1: Phase 5 Completion Time vs Packet Loss")
    plt.grid(True)
    plt.savefig(output_png, bbox_inches="tight")
    print(f"Saved {output_png}")


def plot_chart2(input_csv=DATA / "cwnd_option3.csv", output_png=DATA / "chart2_cwnd.png"):
    rounds = []
    cwnds = []
    events = []
    with open(input_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rounds.append(int(row["round"]))
            cwnds.append(float(row["cwnd"]))
            events.append(row.get("event", ""))
    plt.figure()
    plt.plot(rounds, cwnds, marker="o")
    plt.xlabel("Transmission Round")
    plt.ylabel("Congestion Window (cwnd)")
    plt.title("Chart 2: Congestion Window Evolution")
    plt.grid(True)
    plt.savefig(output_png, bbox_inches="tight")
    print(f"Saved {output_png}")


def plot_chart3(input_csv=DATA / "phase_comparison_timing.csv", output_png=DATA / "chart3_phase_comparison.png"):
    phase_order = ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5"]
    times = defaultdict(list)
    with open(input_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            times[row["phase"]].append(float(row["completion_time_seconds"]))
    y = [mean(times[p]) if times[p] else 0 for p in phase_order]
    plt.figure()
    plt.bar(phase_order, y)
    plt.xlabel("Project Phase")
    plt.ylabel("Average Completion Time (seconds)")
    plt.title("Chart 3: Phase 1 to Phase 5 Completion Time Comparison")
    plt.savefig(output_png, bbox_inches="tight")
    print(f"Saved {output_png}")


def main():
    if (DATA / "phase5_chart1_timing.csv").exists():
        plot_chart1()
    else:
        print("Skipping Chart 1: missing data/phase5_chart1_timing.csv")

    if (DATA / "cwnd_option3.csv").exists():
        plot_chart2()
    elif (DATA / "cwnd_option1.csv").exists():
        plot_chart2(DATA / "cwnd_option1.csv")
    else:
        print("Skipping Chart 2: run option 3 first to create cwnd log")

    if (DATA / "phase_comparison_timing.csv").exists():
        plot_chart3()
    else:
        print("Skipping Chart 3: missing data/phase_comparison_timing.csv")

if __name__ == "__main__":
    main()
