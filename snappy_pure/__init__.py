"""Pure Python Snappy decompression library.

This module provides a pure Python implementation of the Snappy
decompression algorithm.
"""

from .exceptions import CompressionError, SnappyError
from .snappy import decompress

__all__ = ["decompress", "CompressionError", "SnappyError"]
__version__ = "0.1.0"
