"""Pure Python Snappy compression and decompression library.

This module provides a pure Python implementation of the Snappy
compression and decompression algorithms.
"""

from .exceptions import CompressionError, SnappyError
from .snappy import compress, decompress

__all__ = ["compress", "decompress", "CompressionError", "SnappyError"]
__version__ = "0.2.0"
