"""Independent integer-bit binary64 multiplication and integer rounding oracle.

No float multiplication, builtin round, production quantizer, model or NumPy.
struct and float.hex serialize representations; they do not compute expected math.
This reference consumes the same bounded synthetic scalar domain, not vehicle data.
"""
import struct
from math import isfinite

from quantization_types import Quantization


def _nearest_shift(n: int, shift: int) -> int:
    if shift <= 0:
        return n << -shift
    divisor = 1 << shift
    whole, remainder = divmod(n, divisor)
    if 2 * remainder > divisor or (2 * remainder == divisor and whole & 1):
        whole += 1
    return whole


def _decode(bits: int) -> tuple[int, int]:
    biased = (bits >> 52) & 2047
    fraction = bits & ((1 << 52) - 1)
    return (fraction, -1074) if biased == 0 else ((1 << 52) + fraction, biased - 1023 - 52)


def _product_bits(bits: int, scale: int) -> int:
    sign = bits & (1 << 63)
    mantissa, exponent = _decode(bits)
    exact = mantissa * scale
    if exact == 0:
        return sign
    highest = exact.bit_length() - 1 + exponent
    if highest < -1022:
        # Input exponent>=-1074, scale>=1: subnormal units remain exact integers.
        return sign | (exact << (exponent + 1074))
    shift = exact.bit_length() - 53
    rounded = _nearest_shift(exact, shift)
    output_exponent = exponent + shift
    if rounded == 1 << 53:
        rounded >>= 1
        output_exponent += 1
    biased = output_exponent + 52 + 1023
    return sign | (biased << 52) | (rounded - (1 << 52))


def _integer(bits: int) -> int:
    mantissa, exponent = _decode(bits)
    magnitude = _nearest_shift(mantissa, -exponent)
    return -magnitude if bits >> 63 else magnitude


def quantize_reference(q: float, scale: int) -> Quantization:
    if type(q) is not float or not isfinite(q) or not -1 <= q <= 1 or type(scale) is not int or not 1 <= scale <= 2048:
        raise ValueError("VALIDATED_SYNTHETIC_ORACLE_INPUT_REQUIRED")
    bits = int.from_bytes(struct.pack(">d", q), "big")
    product = _product_bits(bits, scale)
    product_hex = struct.unpack(">d", product.to_bytes(8, "big"))[0].hex()
    integer = _integer(product)
    return Quantization(q.hex(), scale, product_hex, integer, integer)
