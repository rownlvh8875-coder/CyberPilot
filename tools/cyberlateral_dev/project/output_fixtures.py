"""Fixed synthetic ratio and codec inputs, not observations or policy values."""
import math
from itertools import product


def output_vectors():
    commands = [-2048, -1024, -95, -7, -3, -1, 0, 1, 3, 7, 95, 127, 255, 1024, 2048]
    scales = [1, 2, 3, 5, 7, 16, 31, 127, 1024, 2048]
    return [(f"OUT:{n}:{d}", n, d) for n, d in product(commands, scales)]


def codec_vectors():
    low, high = float.fromhex("0x1.000001p+0"), float.fromhex("0x1.000003p+0")
    half = float.fromhex("0x1p-150")
    values = [0.0, -0.0, 1.0, -1.0, 1 / 3, -1 / 3, low, math.nextafter(low, math.inf), high, -high,
              half, -half, math.nextafter(half, math.inf), float.fromhex("0x1p-149"),
              float.fromhex("0x1.fffffcp-127"), float.fromhex("0x1.fffffep-127"), float.fromhex("0x1p-126"),
              2048.0, -2048.0]
    return [(f"CODEC:{i:02d}", value) for i, value in enumerate(values)]
