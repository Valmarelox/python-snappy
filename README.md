# python-snappy

Pure Python Snappy decompression library.

## Features

- Pure Python implementation - no C dependencies required
- Supports all Snappy element types: literals and copy operations
- Handles 1-byte, 2-byte, and 4-byte offset copies

## Installation

```bash
pip install python-snappy
```

## Usage

```python
from python_snappy import decompress

# Decompress snappy data
compressed_data = b'...'  # Your snappy compressed data
decompressed = decompress(compressed_data)
```

## Limitations

- Decompression only (no compression support)
- Performance is slower than C-based implementations

For production use with large data, consider using the `python-snappy` package from PyPI which wraps the C library.

## License

MIT
