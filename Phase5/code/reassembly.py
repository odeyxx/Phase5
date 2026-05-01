from collections import deque


class InOrderReassembler:
    """Buffers out-of-order segments and delivers them in order.

    When the next-expected segment arrives, any contiguous out-of-order
    segments already buffered are advanced through automatically. This lets
    one fast retransmit recover an entire gap (real-TCP behavior, no SACK).
    """

    def __init__(self):
        self.expected_seq = 0
        self.out_of_order = {}        # seq -> payload, for early arrivals
        self.pending_delivery = deque()  # contiguous payloads ready for the app
        self.delivered = bytearray()

    def accept(self, seq, payload):
        """Returns 'duplicate', 'out_of_order', or 'in_order'."""
        # Already-seen segment (sender retransmitted unnecessarily). Drop it.
        if seq < self.expected_seq:
            return "duplicate"

        # Future segment. Buffer it and report it was held for later.
        if seq > self.expected_seq:
            if seq in self.out_of_order:
                return "duplicate"
            self.out_of_order[seq] = payload
            return "out_of_order"

        # Exactly the next expected. Take it, then drain any contiguous
        # buffered segments (they may have arrived earlier out of order).
        self.pending_delivery.append(payload)
        self.expected_seq += 1
        while self.expected_seq in self.out_of_order:
            self.pending_delivery.append(self.out_of_order.pop(self.expected_seq))
            self.expected_seq += 1
        return "in_order"

    def next_expected(self):
        return self.expected_seq

    def has_pending(self):
        return bool(self.pending_delivery)

    def deliver_one(self):
        if not self.pending_delivery:
            return False
        self.delivered.extend(self.pending_delivery.popleft())
        return True

    def deliver_all(self):
        while self.deliver_one():
            pass

    def write_file(self, output_path):
        with open(output_path, "wb") as f:
            f.write(self.delivered)
