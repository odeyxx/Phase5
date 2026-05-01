# Phase 5 Working Project

Basic TCP-like file transfer over an unreliable UDP channel.

This project is written for Phase 5. It builds from the Phase 4 idea of reliable UDP / Go-Back-N, but upgrades it into a TCP-like transport design with connection setup, teardown, flow control, congestion control, and performance plotting.

## Team split

- Odey Khello: sender logic, congestion control, retransmission, integration testing
- Kevin Pol: receiver logic, flow control, in-order reassembly
- Andrew Thach: experiments, plots, README/demo support, validation runs

## Files

```text
code/
  config.py
  segment.py
  unreliable_channel.py
  congestion_control.py
  retransmission_timer.py
  sender.py
  receiver.py
  flow_control.py
  reassembly.py
  run_demo.py
  experiments.py
  make_plots.py
  compare_files.py

data/
  sample_input.txt          # 50 KB demo file (Options 1-5, Chart 3)
  chart1_input.txt          # 5 KB file used for Chart 1 timing sweep
  phase_times_template.csv

docs/
  demo_script.md
  rubric_coverage.md
  phase4_to_phase5_continuation.md
```

## Quick demo

From inside the project folder:

```bash
python code/run_demo.py --option 1
```

This starts the receiver, runs the sender, transfers `data/sample_input.txt`, and compares the received output file.

## Demo options

```bash
python code/run_demo.py --option 1
python code/run_demo.py --option 2
python code/run_demo.py --option 3
python code/run_demo.py --option 4
python code/run_demo.py --option 5
```

Option meanings:

1. Normal setup, transfer, teardown
2. Flow-control-limited transfer using small receiver window
3. Slow start and congestion avoidance logging
4. Triple duplicate ACK / fast retransmit and fast recovery
5. Timeout-based congestion response

## Debugging flags

Two flags help when something goes wrong:

```bash
python code/run_demo.py --option 4 --verbose          # logs from BOTH sender and receiver, with timestamps
python code/run_demo.py --option 1 --loss 20 --seed 7 # reproducible loss pattern (replay the same drops)
```

`--verbose` works on `sender.py` and `receiver.py` directly too. `--seed` is also supported on both. Use the same seed to replay the same drop pattern.

## Run manually in two terminals

Terminal 1:

```bash
python code/receiver.py --listen-port 9000 --output data/received_output.txt
```

Terminal 2:

```bash
python code/sender.py --server-port 9000 --input data/sample_input.txt --cwnd-log data/cwnd_log.csv
```

Then compare:

```bash
python code/compare_files.py data/sample_input.txt data/received_output.txt
```

## Generate timing data and plots

```bash
python code/experiments.py --quick     # quick smoke test (3 rates, 2 runs each)
python code/experiments.py             # full sweep (0-95% in 5% steps, 5 runs each)
python code/make_plots.py
```

For final submission, run without `--quick` so Chart 1 uses the full 0% to 95% loss range.

The full sweep uses `data/chart1_input.txt` (5 KB) by default so high-loss runs finish in a reasonable time. Use the bigger `data/sample_input.txt` for Chart 3 (phase-to-phase comparison) where all phases must use the same input.

Each run is capped at 120 seconds; runs that hit the cap are skipped with a warning rather than hanging the script. Override with `--max-seconds N` or `--input path/to/file` if needed.

## Important note

This is a working baseline that demonstrates the required Phase 5 structure. Before final submission, test it with your actual transfer image/file and tune timeout, buffer size, cwnd, and loss settings.
