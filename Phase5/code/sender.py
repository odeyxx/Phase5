#!/usr/bin/env python3
"""Phase 5 sender.

Implements:
- simplified SYN / SYN-ACK / ACK setup
- dynamic window = min(cwnd, rwnd)
- cumulative ACK handling
- Reno slow start / congestion avoidance
- triple duplicate ACK fast retransmit / fast recovery
- timeout congestion response
- FIN / ACK teardown
"""

import argparse
import csv
import socket
import time
from pathlib import Path

from segment import Segment, make_syn, make_ack, make_data, make_fin
from congestion_control import RenoCongestionControl
from retransmission_timer import RetransmissionTimer
from unreliable_channel import should_drop, corrupt_bytes, seed as channel_seed
from config import DEFAULT_HOST, DEFAULT_PORT, PAYLOAD_SIZE, TIMEOUT_SECONDS, INITIAL_CWND, INITIAL_SSTHRESH, DEFAULT_RWND

class Phase5Sender:
    def __init__(self, server_host, server_port, input_path, timeout=TIMEOUT_SECONDS,
                 initial_cwnd=INITIAL_CWND, initial_ssthresh=INITIAL_SSTHRESH,
                 ack_loss=0.0, ack_error=0.0, cwnd_log="data/cwnd_log.csv",
                 verbose=False, seed=None):
        if seed is not None:
            channel_seed(seed)
        self.server = (server_host, server_port)
        self.input_path = Path(input_path)
        self.timeout = timeout
        self.ack_loss = ack_loss
        self.ack_error = ack_error
        self.verbose = verbose
        self.cwnd_log = Path(cwnd_log)
        self.cc = RenoCongestionControl(initial_cwnd, initial_ssthresh)
        self.timer = RetransmissionTimer(timeout)
        self.rwnd = DEFAULT_RWND
        self.base = 0
        self.next_seq = 0
        self.unacked = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.05)

    def log(self, msg):
        if self.verbose:
            print(f"[sender {time.monotonic():.3f}] {msg}")

    def send_segment(self, seg):
        self.sock.sendto(seg.to_bytes(), self.server)

    def read_chunks(self):
        data = self.input_path.read_bytes()
        return [data[i:i + PAYLOAD_SIZE] for i in range(0, len(data), PAYLOAD_SIZE)] or [b""]

    def handshake(self):
        syn = make_syn(seq=0)
        start = time.monotonic()
        while True:
            self.send_segment(syn)
            self.log("sent SYN")
            try:
                raw, _ = self.sock.recvfrom(65535)
                seg = Segment.from_bytes(raw)
                if seg.is_valid() and seg.has("SYN") and seg.has("ACK"):
                    self.rwnd = seg.rwnd
                    self.send_segment(make_ack(ack=seg.seq + 1, rwnd=0))
                    self.log("received SYN-ACK, sent ACK")
                    return
            except socket.timeout:
                if time.monotonic() - start > 10:
                    raise TimeoutError("Handshake failed")
                continue

    def can_send_more(self, total_segments):
        if self.next_seq >= total_segments:
            return False
        in_flight = self.next_seq - self.base
        return in_flight < self.cc.effective_window(self.rwnd)

    def start_timer_if_needed(self):
        if self.unacked and self.timer.start_time is None:
            self.timer.start()

    def send_new_data(self, chunks):
        while self.can_send_more(len(chunks)):
            seg = make_data(seq=self.next_seq, payload=chunks[self.next_seq])
            self.send_segment(seg)
            self.unacked[self.next_seq] = seg
            self.log(f"sent DATA seq={self.next_seq}, cwnd={self.cc.cwnd:.2f}, rwnd={self.rwnd}")
            self.next_seq += 1
            self.start_timer_if_needed()

    def receive_ack_once(self):
        try:
            raw, _ = self.sock.recvfrom(65535)
        except socket.timeout:
            return None

        if should_drop(self.ack_loss):
            self.log("dropped ACK at sender receive path")
            return None

        if should_drop(self.ack_error):
            raw = corrupt_bytes(raw)

        try:
            seg = Segment.from_bytes(raw)
        except Exception as e:
            self.log(f"malformed segment dropped: {e}")
            return None

        if not seg.is_valid() or not seg.has("ACK"):
            self.log("bad ACK ignored")
            return None

        return seg

    def process_ack(self, ack_seg):
        ack_number = ack_seg.ack
        rwnd_opened = ack_seg.rwnd > self.rwnd  # detect window update before overwriting
        self.rwnd = ack_seg.rwnd
        old_base = self.base

        event = self.cc.on_ack(ack_number, rwnd_opened=rwnd_opened)
        self.log(f"ACK {ack_number}, event={event}, cwnd={self.cc.cwnd:.2f}, rwnd={self.rwnd}")

        if ack_number > self.base:
            self.base = ack_number
            for seq in list(self.unacked.keys()):
                if seq < ack_number:
                    del self.unacked[seq]
            if self.unacked:
                self.timer.restart()
            else:
                self.timer.stop()

        if event == "fast_retransmit":
            self.retransmit_missing(ack_number)

        return self.base != old_base

    def retransmit_missing(self, seq):
        if seq in self.unacked:
            self.log(f"fast retransmit seq={seq}")
            self.send_segment(self.unacked[seq])
            self.timer.restart()

    def retransmit_oldest(self):
        if not self.unacked:
            return
        seq = min(self.unacked.keys())
        self.log(f"timeout retransmit seq={seq}")
        self.send_segment(self.unacked[seq])
        self.timer.restart()

    def check_timeout(self):
        if self.timer.expired():
            self.cc.on_timeout()
            self.retransmit_oldest()

    def transfer_file(self):
        chunks = self.read_chunks()
        total = len(chunks)
        start = time.perf_counter()

        while self.base < total:
            self.send_new_data(chunks)
            ack = self.receive_ack_once()
            if ack:
                self.process_ack(ack)
            self.check_timeout()

        completion_time = time.perf_counter() - start
        return completion_time, total

    def teardown(self, fin_seq):
        fin = make_fin(seq=fin_seq)
        start = time.monotonic()
        while True:
            self.send_segment(fin)
            self.log("sent FIN")
            try:
                raw, _ = self.sock.recvfrom(65535)
                seg = Segment.from_bytes(raw)
                if seg.is_valid() and seg.has("ACK") and seg.ack >= fin_seq + 1:
                    self.log("FIN ACK received")
                    return
            except socket.timeout:
                if time.monotonic() - start > 10:
                    raise TimeoutError("Teardown failed")
                continue

    def write_cwnd_log(self):
        self.cwnd_log.parent.mkdir(parents=True, exist_ok=True)
        with self.cwnd_log.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["round", "event", "ack", "cwnd", "ssthresh"])
            writer.writeheader()
            writer.writerows(self.cc.history)

    def run(self):
        self.handshake()
        completion_time, total = self.transfer_file()
        self.teardown(fin_seq=total)
        self.write_cwnd_log()
        self.sock.close()
        print(f"completion_time_seconds={completion_time:.6f}")
        return completion_time


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--server-host", default=DEFAULT_HOST)
    p.add_argument("--server-port", type=int, default=DEFAULT_PORT)
    p.add_argument("--input", default="data/sample_input.txt")
    p.add_argument("--timeout", type=float, default=TIMEOUT_SECONDS)
    p.add_argument("--initial-cwnd", type=float, default=INITIAL_CWND)
    p.add_argument("--initial-ssthresh", type=float, default=INITIAL_SSTHRESH)
    p.add_argument("--ack-loss", type=float, default=0.0)
    p.add_argument("--ack-error", type=float, default=0.0)
    p.add_argument("--cwnd-log", default="data/cwnd_log.csv")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--seed", type=int, default=None,
                   help="Seed the loss/corruption RNG so runs are reproducible.")
    args = p.parse_args()

    s = Phase5Sender(
        args.server_host, args.server_port, args.input, args.timeout,
        args.initial_cwnd, args.initial_ssthresh, args.ack_loss, args.ack_error,
        args.cwnd_log, args.verbose, args.seed
    )
    s.run()

if __name__ == "__main__":
    main()
