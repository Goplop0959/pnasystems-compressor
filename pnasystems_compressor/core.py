"""Core compression engine implementing a hybrid custom algorithm."""

import os
import struct
import json
import hashlib
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Tuple, Union
from datetime import datetime


MAGIC_FILE = b"PNASCMP"
MAGIC_STRING = b"PNASCMS"
VERSION = 1
FLAG_NONE = 0

WINDOW_SIZE = 32768
MIN_MATCH = 3
MAX_MATCH = 258

HASH_SIZE = 65536
HASH_MASK = HASH_SIZE - 1

ProgressCallback = Optional[Callable[[str, int, int], None]]


def _safe_update_progress(
    callback: ProgressCallback, phase: str, current: int, total: int
) -> None:
    if callback:
        try:
            callback(phase, current, total)
        except Exception:
            pass


def _encode_varint(value: int) -> bytes:
    buf = bytearray()
    while value >= 0x80:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    buf.append(value & 0x7F)
    return bytes(buf)


def _decode_varint(data: bytes, pos: int) -> Tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise ValueError("Truncated varint")
        b = data[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return value, pos


def _get_file_metadata(path: Path) -> Dict[str, Any]:
    stat_info = path.stat()
    return {
        "original_name": path.name,
        "original_size": stat_info.st_size,
        "created": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
        "mode": stat_info.st_mode,
    }


def _restore_file_metadata(path: Path, metadata: Dict[str, Any]) -> None:
    try:
        created = datetime.fromisoformat(metadata["created"])
        modified = datetime.fromisoformat(metadata["modified"])
        os.utime(
            path,
            (created.timestamp(), modified.timestamp())
        )
        os.chmod(path, metadata.get("mode", 0o644))
    except Exception:
        pass


class _LZ77Compressor:
    def __init__(self, data: bytes, progress: ProgressCallback = None):
        self.data = data
        self.pos = 0
        self.total = len(data)
        self.progress = progress
        self.output = bytearray()
        self.hash_table = [0] * HASH_SIZE
        self.hash_chain = [0] * WINDOW_SIZE

    def _hash(self, pos: int) -> int:
        if pos + 2 >= self.total:
            return 0
        a = self.data[pos]
        b = self.data[pos + 1]
        c = self.data[pos + 2]
        return ((a << 16) | (b << 8) | c) & HASH_MASK

    def _find_longest_match(self, pos: int) -> Tuple[int, int]:
        if pos + MIN_MATCH > self.total:
            return 0, 0
        best_len = MIN_MATCH - 1
        best_dist = 0
        start = max(0, pos - WINDOW_SIZE)
        h = self._hash(pos)
        chain_pos = self.hash_table[h]
        depth = 0
        max_depth = 256
        while chain_pos >= start and depth < max_depth:
            max_cmp = min(self.total - pos, MAX_MATCH)
            l = 0
            while l < max_cmp and self.data[chain_pos + l] == self.data[pos + l]:
                l += 1
            if l > best_len:
                best_len = l
                best_dist = pos - chain_pos
                if best_len == MAX_MATCH:
                    break
            chain_pos = self.hash_chain[chain_pos & (WINDOW_SIZE - 1)]
            depth += 1
        return best_dist, best_len

    def _update_hash(self, pos: int) -> None:
        if pos + 2 >= self.total:
            return
        h = self._hash(pos)
        idx = pos & (WINDOW_SIZE - 1)
        self.hash_chain[idx] = self.hash_table[h]
        self.hash_table[h] = pos

    def compress(self) -> bytes:
        _safe_update_progress(self.progress, "compressing", 0, self.total)
        while self.pos < self.total:
            if self.pos % 1024 == 0:
                _safe_update_progress(
                    self.progress, "compressing", self.pos, self.total
                )
            dist, length = self._find_longest_match(self.pos)
            if length >= MIN_MATCH:
                self.output.append(0x80)
                self.output.extend(_encode_varint(dist))
                self.output.extend(_encode_varint(length))
                for i in range(length):
                    self._update_hash(self.pos + i)
                self.pos += length
            else:
                literal = self.data[self.pos]
                if literal >= 0x80:
                    self.output.append(0x00)
                self.output.append(literal)
                self._update_hash(self.pos)
                self.pos += 1
        _safe_update_progress(self.progress, "compressing", self.total, self.total)
        return bytes(self.output)


class _LZ77Decompressor:
    def __init__(self, compressed: bytes, progress: ProgressCallback = None):
        self.compressed = compressed
        self.pos = 0
        self.total = len(compressed)
        self.progress = progress
        self.output = bytearray()

    def decompress(self) -> bytes:
        _safe_update_progress(self.progress, "decompressing", 0, self.total)
        while self.pos < self.total:
            if self.pos % 1024 == 0:
                _safe_update_progress(
                    self.progress, "decompressing", self.pos, self.total
                )
            flag = self.compressed[self.pos]
            self.pos += 1
            if flag == 0x00:
                if self.pos >= self.total:
                    raise ValueError("Unexpected end of stream")
                self.output.append(self.compressed[self.pos])
                self.pos += 1
            elif flag & 0x80:
                dist, self.pos = _decode_varint(self.compressed, self.pos)
                length, self.pos = _decode_varint(self.compressed, self.pos)
                if dist > len(self.output):
                    raise ValueError("Invalid distance")
                start = len(self.output) - dist
                for i in range(length):
                    self.output.append(self.output[start + i])
            else:
                self.output.append(flag)
        _safe_update_progress(self.progress, "decompressing", self.total, self.total)
        return bytes(self.output)


def Compress_File(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    progress: ProgressCallback = None,
) -> None:
    input_path = Path(input_path)
    output_path = Path(output_path)
    _safe_update_progress(progress, "reading", 0, 1)
    with open(input_path, "rb") as f:
        data = f.read()
    _safe_update_progress(progress, "reading", len(data), len(data))
    metadata = _get_file_metadata(input_path)
    metadata_json = json.dumps(metadata).encode("utf-8")
    compressor = _LZ77Compressor(data, progress)
    compressed_payload = compressor.compress()
    output = bytearray()
    output.extend(MAGIC_FILE)
    output.append(VERSION)
    output.append(FLAG_NONE)
    output.extend(struct.pack(">I", len(metadata_json)))
    output.extend(metadata_json)
    output.extend(compressed_payload)
    _safe_update_progress(progress, "writing", 0, len(output))
    with open(output_path, "wb") as f:
        f.write(output)
    _safe_update_progress(progress, "writing", len(output), len(output))


def Compress_String(
    input_string: str,
    output_path: Union[str, Path],
    progress: ProgressCallback = None,
) -> None:
    output_path = Path(output_path)
    data = input_string.encode("utf-8")
    _safe_update_progress(progress, "encoding", len(data), len(data))
    compressor = _LZ77Compressor(data, progress)
    compressed_payload = compressor.compress()
    output = bytearray()
    output.extend(MAGIC_STRING)
    output.append(VERSION)
    output.append(FLAG_NONE)
    output.extend(compressed_payload)
    _safe_update_progress(progress, "writing", 0, len(output))
    with open(output_path, "wb") as f:
        f.write(output)
    _safe_update_progress(progress, "writing", len(output), len(output))


def Decompress_File(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    progress: ProgressCallback = None,
) -> None:
    input_path = Path(input_path)
    output_path = Path(output_path)
    _safe_update_progress(progress, "reading", 0, 1)
    with open(input_path, "rb") as f:
        data = f.read()
    _safe_update_progress(progress, "reading", len(data), len(data))
    if len(data) < 7:
        raise ValueError("Invalid compressed file: too short")
    magic = data[:7]
    if magic != MAGIC_FILE:
        raise ValueError("Not a valid PNASystems CompressedFile")
    version = data[7]
    flags = data[8]
    pos = 9
    if len(data) < pos + 4:
        raise ValueError("Truncated header")
    meta_len = struct.unpack(">I", data[pos:pos+4])[0]
    pos += 4
    if len(data) < pos + meta_len:
        raise ValueError("Truncated metadata")
    metadata_json = data[pos:pos+meta_len]
    pos += meta_len
    metadata = json.loads(metadata_json.decode("utf-8"))
    compressed_payload = data[pos:]
    decompressor = _LZ77Decompressor(compressed_payload, progress)
    original_data = decompressor.decompress()
    _safe_update_progress(progress, "writing", 0, len(original_data))
    with open(output_path, "wb") as f:
        f.write(original_data)
    _safe_update_progress(progress, "writing", len(original_data), len(original_data))
    _restore_file_metadata(output_path, metadata)


def Decompress_String(
    input_path: Union[str, Path],
    progress: ProgressCallback = None,
) -> str:
    input_path = Path(input_path)
    _safe_update_progress(progress, "reading", 0, 1)
    with open(input_path, "rb") as f:
        data = f.read()
    _safe_update_progress(progress, "reading", len(data), len(data))
    if len(data) < 7:
        raise ValueError("Invalid compressed file: too short")
    magic = data[:7]
    if magic != MAGIC_STRING:
        raise ValueError("Not a valid PNASystems CompressedString")
    version = data[7]
    flags = data[8]
    compressed_payload = data[9:]
    decompressor = _LZ77Decompressor(compressed_payload, progress)
    original_bytes = decompressor.decompress()
    return original_bytes.decode("utf-8")
