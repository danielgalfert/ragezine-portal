"""Safe, bounded previews for staff review of uploaded files."""

from io import BytesIO
from pathlib import Path
import warnings
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, LargeZipFile, ZipFile

from defusedxml.ElementTree import fromstring
from defusedxml.common import DefusedXmlException
from PIL import Image, UnidentifiedImageError


MAX_TEXT_PREVIEW_BYTES = 2 * 1024 * 1024
MAX_DOCUMENT_PREVIEW_BYTES = 20 * 1024 * 1024
MAX_TIFF_PREVIEW_BYTES = 100 * 1024 * 1024
MAX_XML_PREVIEW_BYTES = 2 * 1024 * 1024
MAX_PREVIEW_CHARS = 100_000
MAX_IMAGE_PIXELS = 40_000_000

IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".avif": "image/avif",
}
VIDEO_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".ogv": "video/ogg",
    ".avi": "video/x-msvideo",
}
TEXT_SUFFIXES = {".txt", ".md", ".csv", ".rtf"}
DOCUMENT_SUFFIXES = {".docx", ".odt"}
TIFF_SUFFIXES = {".tif", ".tiff"}


class PreviewUnavailable(Exception):
    """The file cannot be rendered safely as an inline preview."""


def document_suffix(document):
    return Path(document.original_filename or document.file.name).suffix.lower()


def preview_kind(document):
    suffix = document_suffix(document)
    size = document.size or 0
    if suffix == ".pdf":
        return "pdf"
    if suffix in VIDEO_TYPES:
        return "video"
    if suffix in IMAGE_TYPES:
        return "image"
    if suffix in TIFF_SUFFIXES and size <= MAX_TIFF_PREVIEW_BYTES:
        return "image"
    if suffix in TEXT_SUFFIXES and size <= MAX_TEXT_PREVIEW_BYTES:
        return "text"
    if suffix in DOCUMENT_SUFFIXES and size <= MAX_DOCUMENT_PREVIEW_BYTES:
        return "document"
    return None


def preview_content_type(document):
    suffix = document_suffix(document)
    if suffix in IMAGE_TYPES:
        return IMAGE_TYPES[suffix]
    if suffix in VIDEO_TYPES:
        return VIDEO_TYPES[suffix]
    if suffix in TIFF_SUFFIXES:
        return "image/png"
    if suffix == ".pdf":
        return "application/pdf"
    return "text/plain; charset=utf-8"


def read_text_preview(stored_file):
    stored_file.open("rb")
    try:
        content = stored_file.read(MAX_TEXT_PREVIEW_BYTES + 1)
    finally:
        stored_file.close()
    if len(content) > MAX_TEXT_PREVIEW_BYTES:
        raise PreviewUnavailable("This text file is too large to preview.")
    return content.decode("utf-8-sig", errors="replace")[:MAX_PREVIEW_CHARS]


def read_document_preview(stored_file, suffix):
    stored_file.open("rb")
    try:
        if stored_file.size > MAX_DOCUMENT_PREVIEW_BYTES:
            raise PreviewUnavailable("This document is too large to preview.")
        try:
            with ZipFile(stored_file) as archive:
                if len(archive.filelist) > 10000:
                    raise PreviewUnavailable("This document is too large to preview.")
                part_name = "word/document.xml" if suffix == ".docx" else "content.xml"
                part = archive.getinfo(part_name)
                if part.file_size > MAX_XML_PREVIEW_BYTES:
                    raise PreviewUnavailable("This document is too large to preview.")
                with archive.open(part) as xml_file:
                    xml_content = xml_file.read(MAX_XML_PREVIEW_BYTES + 1)
            if len(xml_content) > MAX_XML_PREVIEW_BYTES:
                raise PreviewUnavailable("This document is too large to preview.")
            root = fromstring(xml_content)
        except (BadZipFile, LargeZipFile, KeyError, OSError, ParseError, RuntimeError, ValueError, DefusedXmlException) as exc:
            raise PreviewUnavailable("This document cannot be previewed.") from exc
    finally:
        stored_file.close()

    if suffix == ".docx":
        paragraph_tag = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
        text_tag = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
        lines = [
            "".join(node.text or "" for node in paragraph.iter(text_tag)).strip()
            for paragraph in root.iter(paragraph_tag)
        ]
    else:
        text_namespace = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
        lines = [
            "".join(paragraph.itertext()).strip()
            for paragraph in root.iter()
            if paragraph.tag in {f"{text_namespace}p", f"{text_namespace}h"}
        ]

    text = "\n\n".join(line for line in lines if line)
    return text[:MAX_PREVIEW_CHARS] or "This document has no text to preview."


def render_tiff_preview(stored_file):
    stored_file.open("rb")
    try:
        if stored_file.size > MAX_TIFF_PREVIEW_BYTES:
            raise PreviewUnavailable("This image is too large to preview.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(stored_file) as image:
                    if image.width * image.height > MAX_IMAGE_PIXELS:
                        raise PreviewUnavailable("This image is too large to preview.")
                    image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                    output = BytesIO()
                    image.save(output, format="PNG")
                    return output.getvalue()
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
            raise PreviewUnavailable("This image cannot be previewed.") from exc
    finally:
        stored_file.close()
