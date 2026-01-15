"""Pure Python Snappy decompression.

This module implements a complete Snappy decompressor in pure Python.
"""

from __future__ import annotations

from .exceptions import CompressionError


def _decode_varint(data: bytes, pos: int) -> tuple[int, int]:
    """
    Decode a varint from data starting at pos.

    Returns:
        Tuple of (value, new_position)
    """
    result = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise CompressionError("Truncated varint in snappy data", algorithm="snappy")
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
        if shift > 32:
            raise CompressionError("Varint too large in snappy data", algorithm="snappy")
    return result, pos


def decompress(data: bytes) -> bytes:
    """
    Decompress Snappy compressed data.

    Snappy format:
    - Varint: uncompressed length
    - Elements: sequence of literals and copies

    Element types (lower 2 bits of tag):
    - 00: Literal
    - 01: Copy with 1-byte offset
    - 10: Copy with 2-byte offset
    - 11: Copy with 4-byte offset

    Args:
        data: Snappy compressed data

    Returns:
        Decompressed bytes

    Raises:
        CompressionError: If decompression fails
    """
    if not data:
        return b""

    pos = 0

    # Decode uncompressed length
    uncompressed_len, pos = _decode_varint(data, pos)

    # Pre-allocate output
    output = bytearray(uncompressed_len)
    out_pos = 0

    while pos < len(data) and out_pos < uncompressed_len:
        tag = data[pos]
        pos += 1
        element_type = tag & 0x03

        if element_type == 0:  # Literal
            # Length encoding depends on upper 6 bits
            length = (tag >> 2) + 1
            if length <= 60:
                # Length is directly encoded (1-60)
                pass
            else:
                # Length is encoded in following bytes
                extra_bytes = length - 60
                if pos + extra_bytes > len(data):
                    raise CompressionError("Truncated literal length", algorithm="snappy")
                length = 1
                for i in range(extra_bytes):
                    length += data[pos + i] << (i * 8)
                pos += extra_bytes

            # Copy literal bytes
            if pos + length > len(data):
                raise CompressionError("Truncated literal data", algorithm="snappy")
            if out_pos + length > uncompressed_len:
                raise CompressionError("Output overflow in literal", algorithm="snappy")

            output[out_pos : out_pos + length] = data[pos : pos + length]
            pos += length
            out_pos += length

        elif element_type == 1:  # Copy with 1-byte offset
            # Length: 4-11 (3 bits in tag >> 2) + 4
            # Offset: 3 bits in tag + 8 bits
            length = ((tag >> 2) & 0x07) + 4
            if pos >= len(data):
                raise CompressionError("Truncated copy1 offset", algorithm="snappy")
            offset = ((tag >> 5) << 8) | data[pos]
            pos += 1

            if offset == 0:
                raise CompressionError("Invalid zero offset in copy", algorithm="snappy")
            if offset > out_pos:
                raise CompressionError(
                    f"Copy offset {offset} exceeds output position {out_pos}", algorithm="snappy"
                )
            if out_pos + length > uncompressed_len:
                raise CompressionError("Output overflow in copy1", algorithm="snappy")

            # Copy bytes (may overlap)
            for i in range(length):
                output[out_pos + i] = output[out_pos - offset + i]
            out_pos += length

        elif element_type == 2:  # Copy with 2-byte offset
            # Length: upper 6 bits + 1
            length = (tag >> 2) + 1
            if pos + 2 > len(data):
                raise CompressionError("Truncated copy2 offset", algorithm="snappy")
            offset = data[pos] | (data[pos + 1] << 8)
            pos += 2

            if offset == 0:
                raise CompressionError("Invalid zero offset in copy", algorithm="snappy")
            if offset > out_pos:
                raise CompressionError(
                    f"Copy offset {offset} exceeds output position {out_pos}", algorithm="snappy"
                )
            if out_pos + length > uncompressed_len:
                raise CompressionError("Output overflow in copy2", algorithm="snappy")

            # Copy bytes (may overlap)
            for i in range(length):
                output[out_pos + i] = output[out_pos - offset + i]
            out_pos += length

        else:  # element_type == 3: Copy with 4-byte offset
            # Length: upper 6 bits + 1
            length = (tag >> 2) + 1
            if pos + 4 > len(data):
                raise CompressionError("Truncated copy4 offset", algorithm="snappy")
            offset = (
                data[pos] | (data[pos + 1] << 8) | (data[pos + 2] << 16) | (data[pos + 3] << 24)
            )
            pos += 4

            if offset == 0:
                raise CompressionError("Invalid zero offset in copy", algorithm="snappy")
            if offset > out_pos:
                raise CompressionError(
                    f"Copy offset {offset} exceeds output position {out_pos}", algorithm="snappy"
                )
            if out_pos + length > uncompressed_len:
                raise CompressionError("Output overflow in copy4", algorithm="snappy")

            # Copy bytes (may overlap)
            for i in range(length):
                output[out_pos + i] = output[out_pos - offset + i]
            out_pos += length

    if out_pos != uncompressed_len:
        raise CompressionError(
            f"Output size mismatch: expected {uncompressed_len}, got {out_pos}", algorithm="snappy"
        )

    return bytes(output)
