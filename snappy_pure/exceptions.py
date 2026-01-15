"""Exceptions for pure Python snappy decompressor."""


class SnappyError(Exception):
    """Base exception for snappy operations."""

    pass


class CompressionError(SnappyError):
    """Error decompressing snappy data."""

    def __init__(self, message: str, algorithm: str | None = None):
        super().__init__(message)
        self.algorithm = algorithm
