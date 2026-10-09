import os
import re
import unicodedata

from django.utils.text import get_valid_filename


MULTISPACE_RE = re.compile(r"[ \t]+")
BIDI_CONTROLS_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")


def _clean_text(value, *, multiline=False):
    value = unicodedata.normalize("NFC", str(value or ""))
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = BIDI_CONTROLS_RE.sub("", value)
    cleaned = []
    for char in value:
        if unicodedata.category(char) == "Cc":
            cleaned.append("\n" if char == "\n" and multiline else " ")
        else:
            cleaned.append(char)
    return "".join(cleaned)


def sanitize_single_line(value):
    value = _clean_text(value)
    value = MULTISPACE_RE.sub(" ", value)
    return value.strip()


def sanitize_multiline(value):
    value = _clean_text(value, multiline=True)
    normalized_lines = value.split("\n")
    lines = [MULTISPACE_RE.sub(" ", line).strip() for line in normalized_lines]
    return "\n".join(line for line in lines if line).strip()


def sanitize_uploaded_filename(uploaded_file):
    base_name = os.path.basename((uploaded_file.name or "upload").replace("\\", "/"))
    safe_name = get_valid_filename(sanitize_single_line(base_name)) or "upload"
    safe_name = safe_name[:255]
    uploaded_file.name = safe_name
    return uploaded_file
