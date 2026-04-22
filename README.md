# PNASystems Compressor

A fully custom, lossless, high‑efficiency compression/decompression system for files and strings.

## Features

- Hybrid compression algorithm inspired by XZ, LZ, Zstd, LZMA, and RLE.
- Lossless and deterministic.
- Handles arbitrary binary data and Unicode strings.
- Metadata preservation (filename, timestamps).
- Optional progress hooks for integration with progress bars (e.g., tqdm).

## Installation

```bash
pip install pnasystems-compressor
```

## Usage

### Compress a file

```python
from pnasystems_compressor import Compress_File, Decompress_File

Compress_File("example.txt", "example.txt.CompressedFile")
Decompress_File("example.txt.CompressedFile", "restored_example.txt")
```

### Compress a string

```python
from pnasystems_compressor import Compress_String, Decompress_String

Compress_String("Hello, world!", "hello.CompressedString")
original = Decompress_String("hello.CompressedString")
print(original)  # "Hello, world!"
```

### Using progress hooks

```python
def progress_callback(phase, current, total):
    print(f"\r{phase}: {current}/{total}", end="")

Compress_File("large_file.bin", "large_file.CompressedFile", progress=progress_callback)
```

## API Reference

### `Compress_File(input_path, output_path, progress=None)`
Compress a file at `input_path` and write the compressed output to `output_path`.

### `Compress_String(input_string, output_path, progress=None)`
Compress a string and save to `output_path`.

### `Decompress_File(input_path, output_path, progress=None)`
Decompress a `.CompressedFile` and restore the original file.

### `Decompress_String(input_path, progress=None)`
Decompress a `.CompressedString` and return the original string.

## License

This software is provided under a custom license. See the [LICENSE](LICENSE) file for details.
