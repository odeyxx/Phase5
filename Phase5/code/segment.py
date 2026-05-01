"""
TCP-like segment format for Phase 5.

Segment fields:
- seq: sequence number
- ack: acknowledgment number
- flags: SYN, ACK, FIN, DATA
- rwnd: receiver advertised window
- payload: bytes
- checksum: CRC32 over all fields except checksum

This uses JSON for readability. A struct-based format is also fine, but JSON is easier to debug for the demo.
"""

from dataclasses import dataclass
import base64
import json
import zlib

VALID_FLAGS = {"SYN", "ACK", "FIN", "DATA"}

@dataclass
class Segment:
    seq: int = 0
    ack: int = 0
    flags: tuple = ()
    rwnd: int = 0
    payload: bytes = b""
    checksum: int = 0

    def _body_without_checksum(self):
        return {
            "seq": self.seq,
            "ack": self.ack,
            "flags": list(self.flags),
            "rwnd": self.rwnd,
            "payload": base64.b64encode(self.payload).decode("ascii"),
        }

    def checksum_bytes(self) -> bytes:
        return json.dumps(self._body_without_checksum(), sort_keys=True).encode("utf-8")

    def compute_checksum(self) -> int:
        return zlib.crc32(self.checksum_bytes()) & 0xFFFFFFFF

    def finalize(self):
        self.checksum = self.compute_checksum()
        return self

    def is_valid(self) -> bool:
        return self.checksum == self.compute_checksum()

    def has(self, flag: str) -> bool:
        return flag in self.flags

    def to_bytes(self) -> bytes:
        body = self._body_without_checksum()
        body["checksum"] = self.checksum
        return json.dumps(body, sort_keys=True).encode("utf-8")

    @staticmethod
    def from_bytes(raw: bytes):
        body = json.loads(raw.decode("utf-8"))
        flags = tuple(body.get("flags", []))
        if not set(flags).issubset(VALID_FLAGS):
            raise ValueError("Invalid segment flag")
        return Segment(
            seq=int(body.get("seq", 0)),
            ack=int(body.get("ack", 0)),
            flags=flags,
            rwnd=int(body.get("rwnd", 0)),
            payload=base64.b64decode(body.get("payload", "")),
            checksum=int(body.get("checksum", 0)),
        )

def make_syn(seq=0):
    return Segment(seq=seq, flags=("SYN",)).finalize()

def make_syn_ack(seq=0, ack=1, rwnd=0):
    return Segment(seq=seq, ack=ack, flags=("SYN", "ACK"), rwnd=rwnd).finalize()

def make_ack(ack, rwnd=0):
    return Segment(ack=ack, flags=("ACK",), rwnd=rwnd).finalize()

def make_data(seq, payload, rwnd=0):
    return Segment(seq=seq, flags=("DATA",), rwnd=rwnd, payload=payload).finalize()

def make_fin(seq):
    return Segment(seq=seq, flags=("FIN",)).finalize()
