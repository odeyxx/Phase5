import time

class RetransmissionTimer:
    def __init__(self, timeout_seconds=0.5):
        self.timeout_seconds = timeout_seconds
        self.start_time = None

    def start(self):
        self.start_time = time.monotonic()

    def stop(self):
        self.start_time = None

    def restart(self):
        self.start()

    def expired(self):
        if self.start_time is None:
            return False
        return (time.monotonic() - self.start_time) >= self.timeout_seconds
