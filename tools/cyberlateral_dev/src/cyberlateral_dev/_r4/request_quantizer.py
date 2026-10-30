"""Synthetic builtin-binary64 request conversion, not actual actuator ABI truth."""
from math import isfinite

from .quantization_types import Quantization


class QuantizationError(ValueError):
    """Outside the synthetic model domain, not an original Controller exception."""


def quantize(q: float, scale: int) -> Quantization:
    if type(q) is not float or not isfinite(q) or not -1 <= q <= 1:
        raise QuantizationError("BUILTIN_FINITE_NORMALIZED_FLOAT_REQUIRED")
    if type(scale) is not int or not 1 <= scale <= 2048:
        raise QuantizationError("EXPLICIT_SYNTHETIC_INTEGER_SCALE_REQUIRED")
    product = q * scale
    rounded = round(product)
    command = int(rounded)
    # Representation only: validated builtin operands already produced a float.
    return Quantization(q.hex(), scale, float(product).hex(), rounded, command)
