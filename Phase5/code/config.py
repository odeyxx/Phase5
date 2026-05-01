# Shared Phase 5 configuration.

PAYLOAD_SIZE = 1024
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9000

# Keep this low enough that loss recovery does not take forever.
TIMEOUT_SECONDS = 0.50

# Reno starting values.
INITIAL_CWND = 1.0
INITIAL_SSTHRESH = 16.0
DEFAULT_RWND = 32

# Used for Chart 1.
LOSS_RATES = list(range(0, 100, 5))
RUNS_PER_POINT = 5
