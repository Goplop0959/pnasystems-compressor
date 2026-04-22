"""PNASystems Compressor - Custom lossless compression."""

from .core import (
    Compress_File,
    Compress_String,
    Decompress_File,
    Decompress_String,
)

__version__ = "1.0.0"
__author__ = "Powerentity"
__all__ = [
    "Compress_File",
    "Compress_String",
    "Decompress_File",
    "Decompress_String",
]
