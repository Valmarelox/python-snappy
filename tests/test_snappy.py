"""
Unit tests for pure Python snappy decompression.

These tests verify that the pure Python decompression implementation
produces output identical to the standard python-snappy library.
"""

import pytest


class TestSnappyDecompression:
    """Test pure Python snappy decompression against python-snappy library."""

    @pytest.fixture
    def snappy_lib(self):
        """Get the standard snappy library, skip if not available."""
        try:
            import snappy

            return snappy
        except ImportError:
            pytest.skip("python-snappy not installed")

    @pytest.fixture
    def custom_snappy(self):
        """Get the custom snappy decompression function."""
        from python_snappy import decompress

        return decompress

    def test_simple_literal(self, snappy_lib, custom_snappy):
        """Test decompression of simple literal data."""
        original = b"Hello, World!"
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_empty_data(self, snappy_lib, custom_snappy):
        """Test decompression of empty data."""
        original = b""
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_single_byte(self, snappy_lib, custom_snappy):
        """Test decompression of single byte."""
        original = b"X"
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_repeated_data_short(self, snappy_lib, custom_snappy):
        """Test decompression of short repeated data (triggers copy operations)."""
        original = b"ABCD" * 10
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_repeated_data_long(self, snappy_lib, custom_snappy):
        """Test decompression of longer repeated data."""
        original = b"The quick brown fox jumps over the lazy dog. " * 100
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_binary_data(self, snappy_lib, custom_snappy):
        """Test decompression of binary data with all byte values."""
        original = bytes(range(256)) * 4
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_highly_compressible(self, snappy_lib, custom_snappy):
        """Test decompression of highly compressible data (many copies)."""
        original = b"\x00" * 10000
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_random_like_data(self, snappy_lib, custom_snappy):
        """Test decompression of pseudo-random data (mostly literals)."""
        # Generate deterministic pseudo-random data
        import hashlib

        original = b""
        for i in range(100):
            original += hashlib.sha256(str(i).encode()).digest()
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_json_like_data(self, snappy_lib, custom_snappy):
        """Test decompression of JSON-like data."""
        original = b'{"_id": 1, "name": "test", "values": [1, 2, 3, 4, 5]}' * 50
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_bson_like_data(self, snappy_lib, custom_snappy):
        """Test decompression of BSON-like binary data."""
        # Simulate BSON document structure
        original = b"\x1f\x00\x00\x00"  # document size
        original += b"\x02name\x00\x05\x00\x00\x00test\x00"  # string field
        original += b"\x10value\x00\x2a\x00\x00\x00"  # int32 field
        original += b"\x00"  # document terminator
        original = original * 100
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_large_data(self, snappy_lib, custom_snappy):
        """Test decompression of larger data (64KB+)."""
        # Mix of compressible and less compressible data
        original = (b"Header: " + bytes(range(256))) * 300
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_copy_type_1_offset(self, snappy_lib, custom_snappy):
        """Test data that triggers copy type 1 (1-byte offset, length 4-11)."""
        # Short repetitive pattern with small offset
        original = b"ABCDEFGH" * 20
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_copy_type_2_offset(self, snappy_lib, custom_snappy):
        """Test data that triggers copy type 2 (2-byte offset)."""
        # Pattern with larger offset (> 2047 bytes back)
        original = b"X" * 3000 + b"START" + b"Y" * 100 + b"START"
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original


class TestSnappyEdgeCases:
    """Test edge cases in snappy decompression."""

    @pytest.fixture
    def snappy_lib(self):
        try:
            import snappy

            return snappy
        except ImportError:
            pytest.skip("python-snappy not installed")

    @pytest.fixture
    def custom_snappy(self):
        from python_snappy import decompress

        return decompress

    def test_large_literal_61_bytes(self, snappy_lib, custom_snappy):
        """Test literal > 60 bytes (uses 1 extra length byte)."""
        original = bytes(range(256))[:61]  # Exactly 61 bytes
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_large_literal_256_bytes(self, snappy_lib, custom_snappy):
        """Test literal requiring 1 extra length byte."""
        original = bytes(range(256))
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_large_literal_1000_bytes(self, snappy_lib, custom_snappy):
        """Test literal requiring 2 extra length bytes."""
        original = bytes([i % 256 for i in range(1000)])
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_overlapping_copy(self, snappy_lib, custom_snappy):
        """Test copy where length > offset (run-length encoding effect)."""
        # Pattern that creates overlapping copies: small pattern repeated many times
        original = b"AB" * 500  # Should create copies with offset=2, length>2
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_copy_with_offset_1(self, snappy_lib, custom_snappy):
        """Test copy with minimum offset (1), creating RLE effect."""
        original = b"X" + b"X" * 999  # RLE-like: copy from offset 1
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original

    def test_mixed_literals_and_copies(self, snappy_lib, custom_snappy):
        """Test interleaved literals and various copy types."""
        # Create data that mixes unique and repeated sections
        original = b"HEADER_" + b"DATA" * 100 + b"_MIDDLE_" + b"MORE" * 100 + b"_FOOTER"
        compressed = snappy_lib.compress(original)
        result = custom_snappy(compressed)
        assert result == original


class TestSnappyErrorHandling:
    """Test error handling in snappy decompression."""

    @pytest.fixture
    def custom_snappy(self):
        from python_snappy import decompress

        return decompress

    def test_truncated_varint(self, custom_snappy):
        """Test handling of truncated varint."""
        from python_snappy import CompressionError

        # High bit set but no continuation byte
        with pytest.raises(CompressionError):
            custom_snappy(b"\x80")

    def test_truncated_literal(self, custom_snappy):
        """Test handling of truncated literal data."""
        from python_snappy import CompressionError

        # Varint says 10 bytes, but only header present
        with pytest.raises(CompressionError):
            custom_snappy(b"\x0a\x04")  # length 10, literal tag for 2 bytes
