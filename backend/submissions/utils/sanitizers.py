import os
import re

from django.utils.text import get_valid_filename


CONTROL_CHARS_RE = re.compile(r"[\x00-\x1F\x7F]")
MULTISPACE_RE = re.compile(r"[ \t]+")


def sanitize_single_line(value):
    value = CONTROL_CHARS_RE.sub("", str(value or ""))
    value = MULTISPACE_RE.sub(" ", value)
    return value.strip()


def sanitize_multiline(value):
    value = CONTROL_CHARS_RE.sub("", str(value or ""))
    normalized_lines = (
        value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    )
    lines = [MULTISPACE_RE.sub(" ", line).strip() for line in normalized_lines]
    return "\n".join(line for line in lines if line).strip()


def sanitize_uploaded_filename(uploaded_file):
    base_name = os.path.basename(uploaded_file.name or "upload")
    safe_name = get_valid_filename(CONTROL_CHARS_RE.sub("", base_name).strip()) or "upload"
    uploaded_file.name = safe_name
    return uploaded_file
