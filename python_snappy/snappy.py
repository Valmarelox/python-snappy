"""Pure Python Snappy compression and decompression.

This module implements a complete Snappy compressor and decompressor in pure Python.
"""

from __future__ import annotations

from .exceptions import CompressionError

# Hash table size for compression (must be power of 2)
_HASH_TABLE_SIZE = 1 << 14  # 16384 entries

# Maximum offset for each copy type
_MAX_OFFSET_1 = 2047  # 11 bits
_MAX_OFFSET_2 = 65535  # 16 bits


def _encode_varint(value: int) -> bytes:
    """
    Encode an integer as a varint.

    Args:
        value: Non-negative integer to encode

    Returns:
        Varint-encoded bytes
    """
    result = bytearray()
    while value >= 0x80:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)


def _hash_4_bytes(data: bytes, pos: int) -> int:
    """
    Compute hash of 4 bytes at position for hash table lookup.

    Args:
        data: Input data
        pos: Position to hash from

    Returns:
        Hash value in range [0, _HASH_TABLE_SIZE)
    """
    # Use a simple multiplicative hash
    val = (data[pos] | (data[pos + 1] << 8) | (data[pos + 2] << 16) | (data[pos + 3] << 24))
    return (val * 0x1E35A7BD) >> (32 - 14) & (_HASH_TABLE_SIZE - 1)


def _emit_literal(output: bytearray, data: bytes, start: int, length: int) -> None:
    """
    Emit a literal element to the output.

    Args:
        output: Output buffer to append to
        data: Source data
        start: Start position in source
        length: Number of bytes to emit as literal
    """
    if length <= 0:
        return

    if length <= 60:
        # Length fits in tag (1-60 -> tag value 0-59)
        output.append((length - 1) << 2)
    elif length <= 256:
        # 1 extra byte for length
        output.append(60 << 2)  # tag = 60 means 1 extra byte
        output.append(length - 1)
    elif length <= 65536:
        # 2 extra bytes for length
        output.append(61 << 2)  # tag = 61 means 2 extra bytes
        output.append((length - 1) & 0xFF)
        output.append(((length - 1) >> 8) & 0xFF)
    elif length <= 16777216:
        # 3 extra bytes for length
        output.append(62 << 2)  # tag = 62 means 3 extra bytes
        output.append((length - 1) & 0xFF)
        output.append(((length - 1) >> 8) & 0xFF)
        output.append(((length - 1) >> 16) & 0xFF)
    else:
        # 4 extra bytes for length
        output.append(63 << 2)  # tag = 63 means 4 extra bytes
        output.append((length - 1) & 0xFF)
        output.append(((length - 1) >> 8) & 0xFF)
        output.append(((length - 1) >> 16) & 0xFF)
        output.append(((length - 1) >> 24) & 0xFF)

    output.extend(data[start:start + length])


def _emit_copy(output: bytearray, offset: int, length: int) -> None:
    """
    Emit a copy element to the output.

    Args:
        output: Output buffer to append to
        offset: Back-reference offset (1 to 65535)
        length: Number of bytes to copy (4 to 64)
    """
    while length > 0:
        if length >= 4 and length <= 11 and offset <= _MAX_OFFSET_1:
            # Copy type 1: 1-byte offset, length 4-11
            # Tag format: OOOOLLLL where O is upper 3 bits of offset, L is (length-4)
            tag = 0x01 | ((length - 4) << 2) | ((offset >> 8) << 5)
            output.append(tag)
            output.append(offset & 0xFF)
            return
        elif offset <= _MAX_OFFSET_2:
            # Copy type 2: 2-byte offset, length 1-64
            copy_len = min(length, 64)
            tag = 0x02 | ((copy_len - 1) << 2)
            output.append(tag)
            output.append(offset & 0xFF)
            output.append((offset >> 8) & 0xFF)
            length -= copy_len
        else:
            # Copy type 3: 4-byte offset (rarely needed)
            copy_len = min(length, 64)
            tag = 0x03 | ((copy_len - 1) << 2)
            output.append(tag)
            output.append(offset & 0xFF)
            output.append((offset >> 8) & 0xFF)
            output.append((offset >> 16) & 0xFF)
            output.append((offset >> 24) & 0xFF)
            length -= copy_len


def compress(data: bytes) -> bytes:
    """
    Compress data using the Snappy algorithm.

    Args:
        data: Uncompressed data

    Returns:
        Snappy compressed data

    Raises:
        CompressionError: If compression fails
    """
    if not data:
        return _encode_varint(0)

    data_len = len(data)
    output = bytearray()

    # Write uncompressed length as varint header
    output.extend(_encode_varint(data_len))

    # For very short data, just emit as literal
    if data_len < 4:
        _emit_literal(output, data, 0, data_len)
        return bytes(output)

    # Hash table: maps hash -> position in input
    hash_table = [0] * _HASH_TABLE_SIZE

    pos = 0
    literal_start = 0

    while pos <= data_len - 4:
        # Hash the 4 bytes at current position
        h = _hash_4_bytes(data, pos)
        candidate = hash_table[h]
        hash_table[h] = pos

        # Check if we have a match
        if (candidate > 0 or (candidate == 0 and pos > 0)) and \
           pos - candidate <= _MAX_OFFSET_2 and \
           data[candidate:candidate + 4] == data[pos:pos + 4]:
            # Found a match - emit pending literal first
            if pos > literal_start:
                _emit_literal(output, data, literal_start, pos - literal_start)

            # Calculate match length
            offset = pos - candidate
            match_len = 4
            max_match = min(data_len - pos, 64)  # Snappy max copy length is 64

            while match_len < max_match and \
                  data[candidate + match_len] == data[pos + match_len]:
                match_len += 1

            # Emit copy
            _emit_copy(output, offset, match_len)

            pos += match_len
            literal_start = pos

            # Update hash table for positions we skipped
            if pos <= data_len - 4:
                hash_table[_hash_4_bytes(data, pos - 1)] = pos - 1
        else:
            pos += 1

    # Emit any remaining literal
    if literal_start < data_len:
        _emit_literal(output, data, literal_start, data_len - literal_start)

    return bytes(output)


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
