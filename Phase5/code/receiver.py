#!/usr/bin/env python3
"""Phase 5 receiver.

Implements:
- simplified SYN / SYN-ACK / ACK setup
- checksum validation
- cumulative ACKs
- receiver advertised window rwnd
- in-order reassembly
- FIN / ACK teardown
"""

import argparse
import socket
import time
from pathlib import Path

from segment import Segment, make_syn_ack, make_ack
from flow_control import ReceiveWindow
from reassembly import InOrderReassembler
from unreliable_channel import should_drop, corrupt_bytes, seed as channel_seed
from config import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_RWND

class Phase5Receiver:
    def __init__(self, host, port, output_path, rwnd_capacity=DEFAULT_RWND,
                 data_loss=0.0, data_error=0.0, drop_seq_once=None,
                 app_drain_interval=0.0, verbose=False, seed=None):
        if seed is not None:
            channel_seed(seed)
        self.host = host
        self.port = port
        self.output_path = Path(output_path)
        self.window = ReceiveWindow(rwnd_capacity)
        self.reassembler = InOrderReassembler()
        self.data_loss = data_loss
        self.data_error = data_error
        self.drop_seq_once = drop_seq_once
        self.dropped_once = set()
        self.app_drain_interval = app_drain_interval
        self.verbose = verbose
        self.last_drain = time.monotonic()
        self.client_addr = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.sock.settimeout(0.05)

    def log(self, msg):
        if self.verbose:
            print(f"[receiver {time.monotonic():.3f}] {msg}", flush=True)

    def current_rwnd(self):
        return self.window.available()

    def send_ack(self, ack_number):
        if self.client_addr is None:
            return
        ack = make_ack(ack_number, self.current_rwnd())
        self.sock.sendto(ack.to_bytes(), self.client_addr)
        self.log(f"ACK {ack_number}, rwnd={self.current_rwnd()}")

    def maybe_drain_app(self, force=False, send_window_update=True):
        now = time.monotonic()
        if force or self.app_drain_interval <= 0 or (now - self.last_drain) >= self.app_drain_interval:
            if self.reassembler.deliver_one():
                self.window.mark_delivered()
                self.last_drain = now
                # Send a window update when space opens, but only when called
                # standalone (not inline from the data path, which sends its own ACK).
                if send_window_update and self.client_addr:
                    self.send_ack(self.reassembler.next_expected())

    def maybe_drop_data(self, seg):
        if self.drop_seq_once is not None and seg.seq == self.drop_seq_once and seg.seq not in self.dropped_once:
            self.dropped_once.add(seg.seq)
            self.log(f"forced drop DATA seq={seg.seq}")
            return True
        if should_drop(self.data_loss):
            self.log(f"random drop DATA seq={seg.seq}")
            return True
        return False

    def serve(self):
        self.log(f"listening on {self.host}:{self.port}")
        established = False
        done = False

        while not done:
            self.maybe_drain_app()
            try:
                raw, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                continue

            self.client_addr = addr

            if self.data_error and should_drop(self.data_error):
                raw = corrupt_bytes(raw)

            try:
                seg = Segment.from_bytes(raw)
            except Exception as e:
                self.log(f"malformed segment dropped: {e}")
                self.send_ack(self.reassembler.next_expected())
                continue

            if not seg.is_valid():
                self.log("corrupted segment")
                self.send_ack(self.reassembler.next_expected())
                continue

            if seg.has("SYN"):
                synack = make_syn_ack(seq=0, ack=seg.seq + 1, rwnd=self.current_rwnd())
                self.sock.sendto(synack.to_bytes(), addr)
                self.log("SYN received, sent SYN-ACK")
                continue

            if seg.has("ACK") and not established:
                established = True
                self.log("connection established")
                continue

            if seg.has("DATA"):
                if self.maybe_drop_data(seg):
                    # Do not ACK new data. This creates duplicate ACKs for later out-of-order data.
                    continue

                if not self.window.can_accept():
                    self.log(f"rwnd=0, cannot accept seq={seg.seq}")
                    self.send_ack(self.reassembler.next_expected())
                    continue

                result = self.reassembler.accept(seg.seq, seg.payload)
                if result == "in_order":
                    self.window.mark_received()
                    self.log(f"accepted DATA seq={seg.seq}")
                    if self.app_drain_interval <= 0:
                        # Inline drain. Skip the window-update ACK because the
                        # data path right below already sends one.
                        self.maybe_drain_app(force=True, send_window_update=False)
                elif result == "out_of_order":
                    self.window.mark_received()
                    self.log(f"buffered out-of-order DATA seq={seg.seq}, expected={self.reassembler.next_expected()}")
                else:
                    self.log(f"duplicate DATA seq={seg.seq}, expected={self.reassembler.next_expected()}")

                self.send_ack(self.reassembler.next_expected())
                continue

            if seg.has("FIN"):
                self.log("FIN received")
                self.reassembler.deliver_all()
                while self.window.used > 0:
                    self.window.mark_delivered()
                self.reassembler.write_file(self.output_path)
                self.send_ack(seg.seq + 1)
                done = True

        self.sock.close()
        self.log(f"wrote {self.output_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--listen-port", type=int, default=DEFAULT_PORT)
    p.add_argument("--output", default="data/received_output.txt")
    p.add_argument("--rwnd", type=int, default=DEFAULT_RWND)
    p.add_argument("--data-loss", type=float, default=0.0)
    p.add_argument("--data-error", type=float, default=0.0)
    p.add_argument("--drop-seq-once", type=int, default=None)
    p.add_argument("--app-drain-interval", type=float, default=0.0)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--seed", type=int, default=None,
                   help="Seed the loss/corruption RNG so drops are reproducible.")
    args = p.parse_args()

    r = Phase5Receiver(
        args.host, args.listen_port, args.output, args.rwnd,
        args.data_loss, args.data_error, args.drop_seq_once,
        args.app_drain_interval, args.verbose, args.seed
    )
    r.serve()

if __name__ == "__main__":
    main()
