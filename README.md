# snappy-pure

Pure Python Snappy decompression library.

## Features

- Pure Python implementation - no C dependencies required
- Supports all Snappy element types: literals and copy operations
- Handles 1-byte, 2-byte, and 4-byte offset copies

## Installation

```bash
uv add snappy-pure
```

Or with pip:
```bash
pip install snappy-pure
```

## Usage

```python
from snappy_pure import decompress

# Decompress snappy data
compressed_data = b'...'  # Your snappy compressed data
decompressed = decompress(compressed_data)
```

## Limitations

- Decompression only (no compression support)
- Performance is slower than C-based implementations

For production use with large data, consider using the `python-snappy` package from PyPI which wraps the C library.

## Development

```bash
uv sync --extra test
uv run pytest
```

## License

MIT
