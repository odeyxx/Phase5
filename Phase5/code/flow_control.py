class ReceiveWindow:
    """Tracks receiver buffer space in segments."""

    def __init__(self, capacity_segments=32):
        self.capacity = max(1, int(capacity_segments))
        self.used = 0

    def available(self):
        return max(0, self.capacity - self.used)

    def can_accept(self):
        return self.available() > 0

    def mark_received(self):
        if not self.can_accept():
            return False
        self.used += 1
        return True

    def mark_delivered(self):
        if self.used > 0:
            self.used -= 1
            return True
        return False
