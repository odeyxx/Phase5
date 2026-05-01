class RenoCongestionControl:
    """Small TCP Reno style congestion controller."""

    def __init__(self, initial_cwnd=1.0, initial_ssthresh=16.0):
        self.cwnd = float(initial_cwnd)
        self.ssthresh = float(initial_ssthresh)
        self.duplicate_ack_count = 0
        self.last_ack = None
        self.in_fast_recovery = False
        self.history = []

    def effective_window(self, rwnd):
        return max(1, int(min(self.cwnd, max(0, rwnd))))

    def on_ack(self, ack_number, rwnd_opened=False):
        # Same ack number with a larger rwnd is a window update from the
        # receiver, not a duplicate ACK. Treat it as a no-op for CC so we
        # don't trigger false fast retransmits during flow control.
        if ack_number == self.last_ack and not rwnd_opened:
            return self.on_duplicate_ack()

        if ack_number == self.last_ack and rwnd_opened:
            self._log("window_update", ack_number)
            return "window_update"

        self.last_ack = ack_number
        self.duplicate_ack_count = 0

        if self.in_fast_recovery:
            self.cwnd = self.ssthresh
            self.in_fast_recovery = False

        if self.cwnd < self.ssthresh:
            self.cwnd += 1.0
            event = "slow_start"
        else:
            self.cwnd += 1.0 / self.cwnd
            event = "congestion_avoidance"

        self._log(event, ack_number)
        return event

    def on_duplicate_ack(self):
        self.duplicate_ack_count += 1

        if self.duplicate_ack_count == 3:
            self.ssthresh = max(self.cwnd / 2.0, 1.0)
            self.cwnd = self.ssthresh + 3.0
            self.in_fast_recovery = True
            self._log("fast_retransmit", self.last_ack)
            return "fast_retransmit"

        if self.in_fast_recovery:
            self.cwnd += 1.0
            self._log("fast_recovery", self.last_ack)
            return "fast_recovery"

        self._log("duplicate_ack", self.last_ack)
        return "duplicate_ack"

    def on_timeout(self):
        self.ssthresh = max(self.cwnd / 2.0, 1.0)
        self.cwnd = 1.0
        self.duplicate_ack_count = 0
        self.in_fast_recovery = False
        self._log("timeout_slow_start", self.last_ack)
        return "timeout_slow_start"

    def _log(self, event, ack):
        self.history.append({
            "round": len(self.history) + 1,
            "event": event,
            "ack": -1 if ack is None else int(ack),
            "cwnd": round(self.cwnd, 3),
            "ssthresh": round(self.ssthresh, 3),
        })
