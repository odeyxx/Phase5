# Intentional loss and corruption helper for demo scenarios and performance testing.

import random

# Module-level RNG so seeding from outside affects all calls.
_rng = random.Random()


def seed(value):
    """Seed the channel RNG so loss patterns are reproducible across runs."""
    _rng.seed(value)


def should_drop(probability_percent: float) -> bool:
    return _rng.random() < (probability_percent / 100.0)


def corrupt_bytes(data: bytes) -> bytes:
    if not data:
        return data
    b = bytearray(data)
    index = _rng.randrange(len(b))
    b[index] ^= 0x01
    return bytes(b)
