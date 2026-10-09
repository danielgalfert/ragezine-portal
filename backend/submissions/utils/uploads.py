"""Validate public uploads before any object is stored."""

from pathlib import PurePath
from zipfile import BadZipFile, ZipFile

from rest_framework import serializers


TEXT_EXTENSIONS = {".doc", ".docx", ".pdf"}
VISUAL_EXTENSIONS = {".tif", ".tiff", ".mp4", ".mov", ".webm"}
CONTENT_TYPES = {
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
}
OLE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
TIFF_SIGNATURES = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")


def _matches_signature(uploaded_file, extension):
    position = uploaded_file.tell()
    try:
        header = uploaded_file.read(4096)
        if extension == ".pdf":
            return header.startswith(b"%PDF-")
        if extension == ".doc":
            return header.startswith(OLE_SIGNATURE)
        if extension == ".docx":
            if not header.startswith(b"PK\x03\x04"):
                return False
            try:
                with ZipFile(uploaded_file) as package:
                    if len(package.filelist) > 10000:
                        return False
                    package.getinfo("[Content_Types].xml")
                    package.getinfo("word/document.xml")
                return True
            except (BadZipFile, KeyError, OSError, ValueError):
                return False
        if extension in {".tif", ".tiff"}:
            return header.startswith(TIFF_SIGNATURES)
        if extension in {".mp4", ".mov"}:
            return len(header) >= 12 and header[4:8] == b"ftyp"
        if extension == ".webm":
            return header.startswith(b"\x1a\x45\xdf\xa3") and b"webm" in header[:128].lower()
        return False
    finally:
        uploaded_file.seek(position)


def validate_upload(uploaded_file, field):
    name = uploaded_file.name or ""
    extension = PurePath(name.replace("\\", "/")).suffix.lower()
    allowed = TEXT_EXTENSIONS if field == "text_files" else VISUAL_EXTENSIONS
    if not name or len(name) > 255 or extension not in allowed:
        raise serializers.ValidationError({field: "Unsupported file name or extension."})
    if uploaded_file.size == 0 or not _matches_signature(uploaded_file, extension):
        raise serializers.ValidationError({field: "File content does not match its extension."})
    uploaded_file.content_type = CONTENT_TYPES[extension]
