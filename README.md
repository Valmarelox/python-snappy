# python-snappy

Pure Python Snappy compression and decompression library.

## Features

- Pure Python implementation - no C dependencies required
- Full compression and decompression support
- Supports all Snappy element types: literals and copy operations
- Handles 1-byte, 2-byte, and 4-byte offset copies

## Installation

```bash
uv add python-snappy-pure
```

Or with pip:
```bash
pip install python-snappy-pure
```

## Usage

```python
from python_snappy import compress, decompress

# Compress data
data = b"Hello, World!" * 100
compressed = compress(data)

# Decompress data
decompressed = decompress(compressed)
assert decompressed == data
```

## Limitations

- Performance is slower than C-based implementations

For production use with large data, consider using the `python-snappy` package from PyPI which wraps the C library.

## Development

```bash
uv sync --extra test
uv run pytest
```

## License

MIT
