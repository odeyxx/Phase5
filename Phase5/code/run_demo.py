#!/usr/bin/env python3
"""Runs receiver and sender together for the five Phase 5 demo options.

Pass --verbose to see timestamped logs from BOTH sender and receiver. Pass
--seed N for reproducible loss patterns (useful when a Chart 1 run hits an
edge case and you want to replay it).
"""

import argparse
import random
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
DATA = ROOT / "data"
PY = sys.executable


def run_cmd(cmd, cwd=ROOT, capture=True, timeout=None):
    try:
        return subprocess.run(cmd, cwd=cwd, text=True, capture_output=capture,
                              check=False, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        # Return a fake CompletedProcess so callers don't need special-case logic.
        class _Timeout:
            returncode = 124
            stdout = (e.stdout or "") if isinstance(e.stdout, str) else ""
            stderr = (e.stderr or "") if isinstance(e.stderr, str) else ""
            stderr += f"\n[run_cmd] timed out after {timeout}s"
        return _Timeout()


def start_receiver(option, port, output, loss, verbose, seed):
    cmd = [PY, str(CODE / "receiver.py"), "--listen-port", str(port), "--output", str(output)]

    if option == 2:
        # Small buffer and slow app drain creates visible flow-control limiting.
        cmd += ["--rwnd", "2", "--app-drain-interval", "0.08"]
    elif option == 4:
        # Drop one early segment while sender has enough cwnd for duplicate ACKs.
        cmd += ["--drop-seq-once", "2"]
    elif option == 5:
        # Drop first data segment once. With low cwnd this causes timeout.
        cmd += ["--drop-seq-once", "0"]
    else:
        if loss > 0:
            cmd += ["--data-loss", str(loss)]

    if verbose:
        cmd += ["--verbose"]
    if seed is not None:
        cmd += ["--seed", str(seed)]

    return subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def run_sender(option, port, input_file, cwnd_log, loss, verbose, seed, max_seconds=None):
    cmd = [PY, str(CODE / "sender.py"), "--server-port", str(port),
           "--input", str(input_file), "--cwnd-log", str(cwnd_log)]

    if option == 3:
        cmd += ["--initial-cwnd", "1", "--initial-ssthresh", "4"]
    elif option == 4:
        cmd += ["--initial-cwnd", "8", "--initial-ssthresh", "16"]
    elif option == 5:
        cmd += ["--initial-cwnd", "1", "--initial-ssthresh", "8", "--timeout", "0.25"]

    if verbose:
        cmd += ["--verbose"]
    if seed is not None:
        cmd += ["--seed", str(seed)]

    return run_cmd(cmd, timeout=max_seconds)


def parse_time(text):
    m = re.search(r"completion_time_seconds=([0-9.]+)", text)
    return float(m.group(1)) if m else None


def run_demo(option, loss=0.0, port=None, input_file=None, verbose=False, seed=None, max_seconds=None):
    DATA.mkdir(exist_ok=True)
    if port is None:
        port = random.randint(10000, 20000)
    if input_file is None:
        input_file = DATA / "sample_input.txt"
    output = DATA / f"received_option{option}.txt"
    cwnd_log = DATA / f"cwnd_option{option}.csv"

    if output.exists():
        output.unlink()

    receiver = start_receiver(option, port, output, loss, verbose, seed)
    time.sleep(0.15)
    sender_result = run_sender(option, port, input_file, cwnd_log, loss, verbose, seed, max_seconds)

    # Receiver wrap-up: give it time to drain after sender finishes (or after
    # the sender was killed for hitting max_seconds). 15s is plenty for FIN/ACK
    # cleanup; bigger values just slow down the test loop.
    try:
        receiver_out, receiver_err = receiver.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        receiver.kill()
        receiver_out, receiver_err = receiver.communicate()

    # Print sender output first.
    if sender_result.stdout.strip():
        print(sender_result.stdout.strip())
    if sender_result.stderr.strip():
        print(sender_result.stderr.strip())

    # In verbose mode, print receiver stdout too (this is where its log() goes).
    if verbose and receiver_out.strip():
        print(receiver_out.strip())
    if receiver_err.strip():
        print(receiver_err.strip())

    compare = run_cmd([PY, str(CODE / "compare_files.py"), str(input_file), str(output)])
    print(compare.stdout.strip())

    if sender_result.returncode != 0 or compare.returncode != 0:
        # Don't raise on a hard timeout — return None so experiments can record it.
        if sender_result.returncode == 124:
            return None
        raise SystemExit(1)

    return parse_time(sender_result.stdout) or 0.0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--option", type=int, choices=[1, 2, 3, 4, 5], required=True)
    p.add_argument("--loss", type=float, default=0.0)
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--input", default=None)
    p.add_argument("--verbose", action="store_true",
                   help="Show timestamped logs from sender AND receiver.")
    p.add_argument("--seed", type=int, default=None,
                   help="Seed loss/corruption RNG for reproducible runs.")
    p.add_argument("--max-seconds", type=float, default=None,
                   help="Kill the sender after this many seconds (prevents infinite hangs at extreme loss rates).")
    args = p.parse_args()

    t = run_demo(args.option, args.loss, args.port,
                 Path(args.input) if args.input else None,
                 args.verbose, args.seed, args.max_seconds)
    if t is None:
        print(f"demo_option={args.option}, time=TIMEOUT")
    else:
        print(f"demo_option={args.option}, time={t:.6f}s")


if __name__ == "__main__":
    main()
