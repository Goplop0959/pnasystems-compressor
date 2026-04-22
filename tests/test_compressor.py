"""Tests for pnasystems-compressor."""

import os
import tempfile
import pytest
from pathlib import Path
from pnasystems_compressor import (
    Compress_File,
    Compress_String,
    Decompress_File,
    Decompress_String,
)


def test_compress_decompress_file():
    original_data = b"Hello, World! This is a test file for compression." * 100
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(original_data)
        orig_path = f.name

    comp_path = orig_path + ".CompressedFile"
    decomp_path = orig_path + ".restored"

    try:
        Compress_File(orig_path, comp_path)
        assert os.path.exists(comp_path)

        Decompress_File(comp_path, decomp_path)
        with open(decomp_path, "rb") as f:
            restored = f.read()
        assert restored == original_data
    finally:
        for p in (orig_path, comp_path, decomp_path):
            if os.path.exists(p):
                os.unlink(p)


def test_compress_decompress_string():
    original = "Hello, 世界! 🚀 " * 50
    with tempfile.NamedTemporaryFile(suffix=".CompressedString", delete=False) as f:
        comp_path = f.name

    try:
        Compress_String(original, comp_path)
        restored = Decompress_String(comp_path)
        assert restored == original
    finally:
        if os.path.exists(comp_path):
            os.unlink(comp_path)


def test_progress_hooks():
    progress_stages = []
    def cb(stage, current, total):
        progress_stages.append((stage, current, total))

    data = b"x" * 10000
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(data)
        orig_path = f.name
    comp_path = orig_path + ".CompressedFile"

    try:
        Compress_File(orig_path, comp_path, progress=cb)
        assert any(s[0] == "compressing" for s in progress_stages)
        assert any(s[0] == "writing" for s in progress_stages)

        progress_stages.clear()
        Decompress_File(comp_path, orig_path + ".out", progress=cb)
        assert any(s[0] == "decompressing" for s in progress_stages)
    finally:
        for p in (orig_path, comp_path, orig_path + ".out"):
            if os.path.exists(p):
                os.unlink(p)


if __name__ == "__main__":
    pytest.main([__file__])
