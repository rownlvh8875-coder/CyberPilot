"""Independent integer quotient/binary32 oracle; no production package imports."""
import struct
from math import isfinite


def _nearest(n, denominator):
    whole, remainder = divmod(n, denominator)
    return whole + int(2 * remainder > denominator or (2 * remainder == denominator and whole & 1))


def _shift(n, shift):
    return n << -shift if shift <= 0 else _nearest(n, 1 << shift)


def _ratio_bits(n, d):
    if n == 0:
        return 0
    sign, numerator = int(n < 0), abs(n)
    exponent = numerator.bit_length() - d.bit_length()
    below = numerator < d << exponent if exponent >= 0 else numerator << -exponent < d
    if below:
        exponent -= 1
    mantissa = _nearest(numerator << (52 - exponent), d)
    if mantissa == 1 << 53:
        mantissa >>= 1
        exponent += 1
    return (sign << 63) | ((exponent + 1023) << 52) | (mantissa - (1 << 52))


def _float32_bits(bits):
    sign, biased = (bits >> 63) << 31, (bits >> 52) & 2047
    mantissa = bits & ((1 << 52) - 1)
    exponent = -1074
    if biased:
        mantissa += 1 << 52
        exponent = biased - 1023 - 52
    if mantissa == 0:
        return sign
    highest = mantissa.bit_length() - 1 + exponent
    if highest < -126:
        return sign | _shift(mantissa, -(exponent + 149))
    shift = mantissa.bit_length() - 24
    rounded = _shift(mantissa, shift)
    output_exponent = exponent + shift
    if rounded == 1 << 24:
        rounded >>= 1
        output_exponent += 1
    return sign | ((output_exponent + 23 + 127) << 23) | (rounded - (1 << 23))


def _projection_from_bits(bits):
    word = _float32_bits(bits).to_bytes(4, "big")
    return {"bits_hex": word.hex(), "value_hex": struct.unpack(">f", word)[0].hex()}


def float32_reference(value):
    if type(value) is not float or not isfinite(value) or abs(value) > 2048:
        raise ValueError("VALIDATED_SYNTHETIC_CODEC_INPUT_REQUIRED")
    return _projection_from_bits(int.from_bytes(struct.pack(">d", value), "big"))


def project_reference(command, scale):
    if type(command) is not int or not -2048 <= command <= 2048 or type(scale) is not int or not 1 <= scale <= 2048:
        raise ValueError("VALIDATED_SYNTHETIC_RATIO_INPUT_REQUIRED")
    normalized_bits = _ratio_bits(command, scale)
    value = struct.unpack(">d", normalized_bits.to_bytes(8, "big"))[0]
    return {"integer_command": command, "scale": scale, "normalized_expression": value,
            "normalized_expression_hex": value.hex(), "torque_float32": _projection_from_bits(normalized_bits),
            "torque_output_can_float32": _projection_from_bits(_ratio_bits(command, 1)),
            "status": "SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE"}
