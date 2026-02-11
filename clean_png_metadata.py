#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PNG metadata cleaner
Batch remove PNG metadata chunks (tEXt, zTXt, iTXt, tIME, pHYs, gAMA, etc.).
Keeps core chunks IHDR, PLTE, IDAT, IEND. Other non-metadata chunks are preserved to avoid data loss.

Usage:
  python clean_png_metadata.py --input <DIR|FILE> [--output <DIR|FILE>]
                               [--recursive] [--backup] [--dry-run]

Options:
  --input       Path to a PNG file or a directory containing PNGs.
  --output      Destination path. If omitted, in-place replacement is performed.
                If this is a directory, preserves relative structure.
                If this is a file (and only one input), writes to that file.
  --recursive   Recursively process subdirectories (when --input is a directory).
  --backup      Create a .bak copy beside the original PNGs before overwriting.
  --dry-run     Do not write any files. Just show what would be done.

Notes:
  - No third-party libraries; only Python standard library.
  - CRCs of kept chunks are preserved (no re-computation unless chunk data changes).
  - Metadata chunks removed by default: tEXt, zTXt, iTXt, tIME, pHYs, gAMA.
  - Test PNG example path mentioned in plan: D:\\test\\111.png
"""

from __future__ import annotations

import argparse
import binascii
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple


# ----------------------------
# PNG chunk data structure
# ----------------------------
@dataclass
class PNGChunk:
    length: int
    type: str  # 4-char ASCII
    data: bytes
    crc: int

    def __repr__(self) -> str:
        return f"<Chunk {self.type} len={self.length} crc=0x{self.crc:08X}>"


# ----------------------------
# PNG utilities
# ----------------------------

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def compute_crc(type_bytes: bytes, data: bytes) -> int:
    # CRC is CRC-32 of chunk type + chunk data
    return binascii.crc32(type_bytes + data) & 0xFFFFFFFF


def read_png_chunks(file_path: Path) -> List[PNGChunk]:
    """
    Read all chunks from a PNG file, validating the signature and CRCs.
    Returns a list of PNGChunk.
    """
    chunks: List[PNGChunk] = []
    with file_path.open("rb") as f:
        sig = f.read(8)
        if sig != PNG_SIGNATURE:
            raise ValueError(f"Not a valid PNG file: {file_path}")

        while True:
            len_bytes = f.read(4)
            if not len_bytes:
                break  # EOF
            if len(len_bytes) != 4:
                raise ValueError(f"Unexpected EOF while reading length in {file_path}")

            length = int.from_bytes(len_bytes, "big")

            type_bytes = f.read(4)
            if len(type_bytes) != 4:
                raise ValueError(f"Unexpected EOF while reading type in {file_path}")
            chunk_type = type_bytes.decode("ascii", errors="replace")

            data = f.read(length)
            if len(data) != length:
                raise ValueError(f"Unexpected EOF while reading data for {chunk_type} in {file_path}")

            crc_bytes = f.read(4)
            if len(crc_bytes) != 4:
                raise ValueError(f"Unexpected EOF while reading CRC for {chunk_type} in {file_path}")
            crc = int.from_bytes(crc_bytes, "big")

            # CRC check
            expected_crc = compute_crc(type_bytes, data)
            if crc != expected_crc:
                raise ValueError(
                    f"CRC mismatch for chunk {chunk_type} in {file_path}: "
                    f"expected 0x{expected_crc:08X}, got 0x{crc:08X}"
                )

            chunks.append(PNGChunk(length=length, type=chunk_type, data=data, crc=crc))
    return chunks


def write_png_chunks(chunks: List[PNGChunk], dest_path: Path) -> int:
    """
    Write PNG header + kept chunks to dest_path.
    Returns the size of the written file in bytes.
    """
    with dest_path.open("wb") as f:
        f.write(PNG_SIGNATURE)
        for ch in chunks:
            f.write(ch.length.to_bytes(4, "big"))
            f.write(ch.type.encode("ascii"))
            f.write(ch.data)
            f.write(ch.crc.to_bytes(4, "big"))
    return dest_path.stat().st_size


# ----------------------------
# Core processing
# ----------------------------

# Chunks that must be preserved as core image data
CORE_CHUNKS = {"IHDR", "PLTE", "IDAT", "IEND"}

# Chunk types to drop (metadata)
DROP_CHUNKS: Set[str] = {"tEXt", "zTXt", "iTXt", "tIME", "pHYs", "gAMA"}


def filter_chunks(chunks: List[PNGChunk]) -> Tuple[List[PNGChunk], int]:
    """
    Filter chunks: keep core chunks; drop known metadata chunks.
    Returns (kept_chunks, removed_count).
    Other non-metadata chunks are preserved as-is to avoid data loss.
    """
    kept: List[PNGChunk] = []
    removed = 0
    for ch in chunks:
        if ch.type in CORE_CHUNKS:
            kept.append(ch)
        elif ch.type in DROP_CHUNKS:
            removed += 1
            # drop
        else:
            # keep other non-core chunks to preserve information (e.g., sRGB, iCCP, etc.)
            kept.append(ch)
    return kept, removed


# ----------------------------
# File system helpers
# ----------------------------

def collect_png_files(input_path: Path, recursive: bool) -> List[Path]:
    """
    Returns a list of PNG file paths to process.
    If input_path is a file, returns [input_path].
    If a directory, returns all PNGs (.png, .PNG) according to recursion flag.
    """
    if input_path.is_file():
        if input_path.suffix.lower() == ".png":
            return [input_path]
        else:
            return []
    if not input_path.exists():
        return []

    if recursive:
        files = sorted(input_path.rglob("*.png"))
        files += sorted(input_path.rglob("*.PNG"))
    else:
        files = sorted(input_path.glob("*.png"))
        files += sorted(input_path.glob("*.PNG"))
    return [p for p in files if p.is_file()]


def ensure_parent_dirs(path: Path) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


# ----------------------------
# Notepad append (learnings)
# ----------------------------
NOTEPAD_BASE = Path(".sisyphus/notepads/default")  # plan-name default for safety


def append_to_notepad(log_lines: List[str]) -> None:
    """
    Append a small summary to the notepad file.
    Creates the directory if missing.
    This is intended for post-task learnings.
    """
    NOTEPAD_BASE.mkdir(parents=True, exist_ok=True)
    target = NOTEPAD_BASE / "learnings.md"

    # Read existing contents if any
    try:
        existing = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        existing = ""

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    addition = [
        f"## PNG metadata cleanup run — {timestamp}",
        "",
        *log_lines,
        "",
    ]
    new_content = existing + "\n" + "\n".join(addition)
    target.write_text(new_content, encoding="utf-8")


# ----------------------------
# CLI
# ----------------------------


def human_bytes(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024.0:
            return f"{n:.0f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"


def main():
    parser = argparse.ArgumentParser(
        description="Batch remove PNG metadata chunks (tEXt, zTXt, iTXt, tIME, pHYs, gAMA, etc.)."
    )
    parser.add_argument("--input", "-i", required=True, help="Input PNG file or directory.")
    parser.add_argument("--output", "-o", required=False, help="Output file or directory. If omitted, in-place.")
    parser.add_argument("--recursive", action="store_true", help="Recursively process subdirectories (when input is a directory).")
    parser.add_argument("--backup", action="store_true", help="Backup original PNG files before overwriting.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing any files.")

    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve() if args.output else None
    recursive = bool(args.recursive)
    backup = bool(args.backup)
    dry_run = bool(args.dry_run)

    # Gather PNGs
    files = collect_png_files(input_path, recursive)
    if not files:
        print("No PNG files found to process.")
        sys.exit(0)

    total = len(files)
    processed = 0
    total_removed = 0
    total_before = 0
    total_after = 0
    per_file_logs: List[str] = []

    start_time = time.time()

    for idx, src in enumerate(files, start=1):
        rel_src = src.name
        try:
            # Read original chunks
            chunks = read_png_chunks(src)
        except Exception as e:
            print(f"[{idx}/{total}] ERROR reading {src}: {e}")
            per_file_logs.append(f"- {src}: READ ERROR: {e}")
            continue

        # Backup path (if requested)
        if backup and not dry_run:
            backup_path = src.parent / (src.name + ".bak")
            try:
                shutil.copy2(src, backup_path)
            except Exception as e:
                print(f"[{idx}/{total}] WARNING: could not backup {src} -> {backup_path}: {e}")

        # Filter chunks
        kept, removed = filter_chunks(chunks)
        total_before += sum(ch.length for ch in chunks) + 12 * len(chunks)
        total_after += sum(ch.length for ch in kept) + 12 * len(kept)
        total_removed += removed

        # Prepare destination
        if output_path:
            # If output is a file path (ends with .png/.PNG) and there are multiple inputs, error
            if output_path.suffix.lower() in {".png"} and total > 1:
                print(f"ERROR: multiple input files but output path {output_path} looks like a single file.")
                sys.exit(2)

            # If output is a directory (or doesn't exist yet), mirror structure
            if output_path.exists() and output_path.is_file():
                dest = output_path
            else:
                base_src_parent = input_path if input_path.is_dir() else src.parent
                try:
                    relative = src.relative_to(base_src_parent)
                except Exception:
                    relative = src.name
                dest = output_path / relative
        else:
            dest = src  # overwrite

        if not dry_run:
            ensure_parent_dirs(dest)
        # Write new PNG if not dry-run
        if not dry_run:
            try:
                write_png_chunks(kept, dest)
            except Exception as e:
                print(f"[{idx}/{total}] ERROR writing {dest}: {e}")
                per_file_logs.append(f"- {src}: WRITE ERROR: {e}")
                continue

        # Progress
        percent = int((idx / total) * 100)
        print(f"[{idx}/{total}] {src} -> {dest} | removed: {removed} chunks | size: {human_bytes(sum(ch.length for ch in chunks))} -> {human_bytes(sum(ch.length for ch in kept))} | {percent}%")

        processed += 1
        total_before = 0
        total_after = 0
        per_file_logs.append(f"- {src}: removed {removed} metadata chunk(s)")

        # Show a tiny live progress indicator
        # (no external libs; simple inline update)
        # (We already print per-file line above.)

    elapsed = time.time() - start_time

    # Summary
    print("\nSummary:")
    print(f"  Total input PNGs: {total}")
    print(f"  Processed: {processed}")
    print(f"  Total metadata chunks removed: {total_removed}")
    print(f"  Time elapsed: {elapsed:.2f}s")
    print(f"  Dry-run: {'Yes' if dry_run else 'No'}")

    # Append learnings/notepad (exhaustive record)
    try:
        log_lines = [
            f"- Run time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
            f"- Input: {str(input_path)}",
            f"- Output: {str(output_path) if output_path else 'in-place'}",
            f"- Recursive: {recursive}",
            f"- Backup: {backup}",
            f"- Dry-run: {dry_run}",
            f"- PNGs processed: {total}",
            f"- Metadata chunks removed: {total_removed}",
            "",
            "Notes: This run preserves core PNG chunks (IHDR, PLTE, IDAT, IEND). All other non-metadata chunks are kept to avoid unwanted data loss unless explicitly dropped by DROP_CHUNKS.",
        ]
        append_to_notepad(log_lines)
    except Exception as e:
        # Do not fail user operation because of logging
        print(f"Warning: could not write to notepad log: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
