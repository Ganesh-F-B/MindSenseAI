"""
backend/upload_guard.py

Secure upload helper for MindSenseAI (Security Hardening Phase 1).
Provides:
- Strict path traversal prevention (client filenames are NEVER used for filesystem paths)
- Per-user, per-request isolated temporary directories
- Strict streaming file-size limits (413 Request Entity Too Large)
- Deep magic-byte and file signature validation (400 Bad Request)
- Guaranteed temporary file cleanup on success, failure, or exception
- Startup sweeper for interrupted/crashed sessions
"""

import os
import re
import shutil
import tempfile
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Optional, Tuple, Set
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

# Base temporary upload directory (outside frontend, static, public, and source directories)
UPLOAD_TMP_DIR = os.getenv(
    "UPLOAD_TMP_DIR",
    os.path.abspath(os.path.join(tempfile.gettempdir(), "mindsense_secure_uploads"))
)

# Size limits by category / format (in bytes)
SIZE_LIMITS = {
    "txt": 1 * 1024 * 1024,        # 1 MB
    "pdf": 5 * 1024 * 1024,        # 5 MB
    "audio": 25 * 1024 * 1024,     # 25 MB
    "video": 100 * 1024 * 1024,    # 100 MB
}

# Allowed extensions by category
ALLOWED_EXTENSIONS = {
    "text_or_pdf": {"txt", "pdf"},
    "audio": {"webm", "wav", "mp3", "ogg", "flac", "m4a", "mp4"},
    "video": {"mp4", "mov", "avi", "webm"},
}

# Dangerous executable / script signatures
DANGEROUS_SIGNATURES = [
    b"MZ",                # Windows PE EXE/DLL
    b"\x7fELF",           # Linux ELF binary
    b"#!/",               # Unix shell script
    b"#! ",               # Unix shell script
    b"<?php",             # PHP script
    b"<html",             # HTML tag
    b"<!DOCTYPE",         # HTML doc
    b"PK\x03\x04",        # ZIP / JAR / Office macro containers (when masquerading as audio/video/text)
]


def sweep_stale_temp_uploads():
    """Remove leftover temporary files from previous interrupted runs.
    Strictly scoped to UPLOAD_TMP_DIR so unrelated files are never touched.
    """
    try:
        if os.path.exists(UPLOAD_TMP_DIR):
            for item in os.listdir(UPLOAD_TMP_DIR):
                item_path = os.path.join(UPLOAD_TMP_DIR, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)
                    else:
                        os.remove(item_path)
                except OSError as err:
                    logger.warning(f"[UploadGuard] Error removing stale temp item {item}: {err}")
    except Exception as e:
        logger.warning(f"[UploadGuard] Failed to sweep stale temp uploads: {e}")


def sanitize_and_validate_extension(filename: Optional[str], category: str) -> str:
    """Validate client filename without trusting it as a path.
    Rejects NUL bytes.
    Extracts a sanitized lowercase alphanumeric extension.
    Verifies that the extension belongs to the allowed category.
    """
    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required."
        )

    # Reject NUL bytes immediately
    if "\x00" in filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename: NUL bytes are not permitted."
        )

    # Check for extension
    if "." not in filename:
        raise HTTPException(
            status_code=400,
            detail="File has no extension. An allowed file extension is required."
        )

    ext_candidate = filename.rsplit(".", 1)[-1].lower()
    # Strip any non-alphanumeric characters from extension
    clean_ext = re.sub(r"[^a-z0-9]", "", ext_candidate)[:10]

    allowed = ALLOWED_EXTENSIONS.get(category, set())
    if clean_ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: .{clean_ext} is not allowed for category '{category}'."
        )

    return clean_ext


def validate_file_content(file_path: str, category: str, extension: str, file_size: int):
    """Deep magic-byte / file-signature inspection to prevent extension spoofing.
    Rejects executable binaries, MIME mismatches, and corrupted payloads.
    """
    if file_size == 0:
        # Empty text file is technically valid empty text; empty audio/video/pdf is invalid
        if extension == "txt":
            return
        if category == "audio" and file_size < 1000:
            # Preserved for microphone silent recordings (< 1KB)
            return
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty or corrupted."
        )

    with open(file_path, "rb") as f:
        header = f.read(4096)

    # Check for dangerous executable signatures (regardless of extension)
    for sig in DANGEROUS_SIGNATURES[:4]:  # MZ, ELF, shell scripts
        if header.startswith(sig):
            raise HTTPException(
                status_code=400,
                detail="Executable or script files are strictly prohibited."
            )

    # 1. TEXT / PDF Category
    if category == "text_or_pdf":
        if extension == "pdf":
            if not header.startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=400,
                    detail="File signature mismatch: expected valid PDF file."
                )
        elif extension == "txt":
            # Text must not be a PDF or ZIP
            if header.startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=400,
                    detail="File signature mismatch: PDF uploaded with .txt extension."
                )
            if header.startswith(b"PK\x03\x04"):
                raise HTTPException(
                    status_code=400,
                    detail="File signature mismatch: archive uploaded with .txt extension."
                )
            # Text must not contain binary NUL bytes
            if b"\x00" in header:
                raise HTTPException(
                    status_code=400,
                    detail="Text file contains binary or NUL characters."
                )
            # Must be valid UTF-8
            try:
                with open(file_path, "r", encoding="utf-8") as f_txt:
                    _ = f_txt.read(8192)
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Text file must be encoded in valid UTF-8."
                )

    # 2. AUDIO Category
    elif category == "audio":
        if file_size < 1000:
            # Short / silent audio recording preserved per baseline behavior
            return

        is_valid_audio = False
        # WebM / Matroska audio: 1A 45 DF A3
        if header.startswith(b"\x1a\x45\xdf\xa3"):
            is_valid_audio = True
        # WAV: RIFF....WAVE
        elif header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WAVE":
            is_valid_audio = True
        # MP3: ID3 tag or MPEG sync frames (0xFF followed by high 3 bits set)
        elif header.startswith(b"ID3") or (len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0):
            is_valid_audio = True
        # OGG: OggS
        elif header.startswith(b"OggS"):
            is_valid_audio = True
        # FLAC: fLaC
        elif header.startswith(b"fLaC"):
            is_valid_audio = True
        # MP4 / M4A: ftyp at offset 4
        elif len(header) >= 8 and header[4:8] == b"ftyp":
            is_valid_audio = True

        if not is_valid_audio:
            raise HTTPException(
                status_code=400,
                detail="File content does not match any supported audio signature."
            )

    # 3. VIDEO Category
    elif category == "video":
        is_valid_video = False
        # WebM: 1A 45 DF A3
        if header.startswith(b"\x1a\x45\xdf\xa3"):
            is_valid_video = True
        # AVI: RIFF....AVI
        elif header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"AVI ":
            is_valid_video = True
        # MP4 / MOV: box type at offset 4
        elif len(header) >= 8 and header[4:8] in (b"ftyp", b"moov", b"mdat", b"wide", b"skip"):
            is_valid_video = True

        if not is_valid_video:
            raise HTTPException(
                status_code=400,
                detail="File content does not match any supported video signature."
            )


@asynccontextmanager
async def secure_upload_context(
    file: UploadFile,
    user_id: int | str,
    category: str,
    custom_max_size: Optional[int] = None,
):
    """Async context manager that safely streams, limits, validates, and cleans up uploads.
    
    Structure:
      <UPLOAD_TMP_DIR>/<user_id>/<request_uuid>/<random_uuid>.<safe_ext>
      
    Guarantees:
      - Client filename is never concatenated or trusted as a path.
      - Traversal (../ or ..\\ or drive paths or NULs) cannot affect storage location.
      - Max file size is enforced during streaming (raises HTTP 413).
      - Magic-byte validation prevents file masquerading (raises HTTP 400).
      - Directory and files are strictly deleted in finally block upon completion or exception.
    """
    clean_ext = sanitize_and_validate_extension(file.filename, category)

    # Determine max size limit
    if custom_max_size:
        max_size = custom_max_size
    elif category == "text_or_pdf":
        max_size = SIZE_LIMITS.get(clean_ext, SIZE_LIMITS["txt"])
    else:
        max_size = SIZE_LIMITS.get(category, 25 * 1024 * 1024)

    # Check Content-Length header if present
    content_length_header = file.headers.get("content-length")
    if content_length_header:
        try:
            cl = int(content_length_header)
            if cl > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request Entity Too Large: file exceeds limit of {max_size} bytes."
                )
        except ValueError:
            pass

    # Create isolated per-user, per-request temporary directory
    request_uuid = uuid.uuid4().hex
    user_dir_name = f"user_{str(user_id)}"
    request_dir = os.path.join(UPLOAD_TMP_DIR, user_dir_name, request_uuid)
    os.makedirs(request_dir, exist_ok=True)

    # Cryptographically random stored filename (NEVER uses client filename)
    random_filename = f"{uuid.uuid4().hex}.{clean_ext}"
    stored_path = os.path.join(request_dir, random_filename)

    bytes_read = 0
    chunk_size = 64 * 1024  # 64 KB streaming buffer

    try:
        with open(stored_path, "wb") as f_out:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                bytes_read += len(chunk)
                if bytes_read > max_size:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Request Entity Too Large: file exceeds limit of {max_size} bytes."
                    )
                f_out.write(chunk)

        # Validate content and magic bytes
        validate_file_content(stored_path, category, clean_ext, bytes_read)

        # Yield safely stored file path to caller
        yield stored_path

    finally:
        # Guarantee full cleanup of file and request directory
        try:
            if os.path.exists(request_dir):
                shutil.rmtree(request_dir, ignore_errors=True)
            # If user parent directory is empty, clean it up as well
            user_dir = os.path.join(UPLOAD_TMP_DIR, user_dir_name)
            if os.path.exists(user_dir) and not os.listdir(user_dir):
                try:
                    os.rmdir(user_dir)
                except OSError:
                    pass
        except Exception as cleanup_err:
            logger.warning(f"[UploadGuard] Cleanup error on {request_dir}: {cleanup_err}")
