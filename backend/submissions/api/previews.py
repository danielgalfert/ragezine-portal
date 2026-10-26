"""Private inline previews with byte ranges for large PDF and video files."""

from pathlib import Path
import re

from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils.http import content_disposition_header
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from submissions.models import SubmissionDocument
from submissions.preview import (
    MAX_DOCUMENT_PREVIEW_BYTES,
    MAX_TEXT_PREVIEW_BYTES,
    MAX_TIFF_PREVIEW_BYTES,
    PreviewUnavailable,
    document_suffix,
    preview_content_type,
    preview_kind,
    read_document_preview,
    read_text_preview,
    render_tiff_preview,
)


class InvalidRange(Exception):
    pass


def _byte_range(header, size):
    if not header:
        return None
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
    if not match or size <= 0:
        raise InvalidRange
    first, last = match.groups()
    if first:
        start = int(first)
        end = int(last) if last else size - 1
        if start >= size or end < start:
            raise InvalidRange
        return start, min(end, size - 1)
    if not last or int(last) <= 0:
        raise InvalidRange
    suffix_length = int(last)
    return max(0, size - suffix_length), size - 1


def _stream_range(stored_file, remaining):
    try:
        while remaining:
            chunk = stored_file.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
    finally:
        stored_file.close()


def _set_preview_headers(response, filename):
    response["Cache-Control"] = "private, no-store"
    response["Content-Disposition"] = content_disposition_header(False, filename)
    response["X-Content-Type-Options"] = "nosniff"
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response


@api_view(["GET", "HEAD"])
@permission_classes([IsAdminUser])
def document_preview(request, document_id):
    document = get_object_or_404(SubmissionDocument, pk=document_id)
    kind = preview_kind(document)
    if not kind:
        return Response(
            {"detail": "A preview is not available for this file. Download it to view it."},
            status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    stored_file = document.file
    if not stored_file.name or not stored_file.storage.exists(stored_file.name):
        raise Http404("Document file not found.")
    filename = Path(document.original_filename or stored_file.name).name
    content_type = preview_content_type(document)
    suffix = document_suffix(document)

    if kind in {"text", "document"} or suffix in {".tif", ".tiff"}:
        size_limit = (
            MAX_TEXT_PREVIEW_BYTES if kind == "text"
            else MAX_DOCUMENT_PREVIEW_BYTES if kind == "document"
            else MAX_TIFF_PREVIEW_BYTES
        )
        if stored_file.size > size_limit:
            return Response(
                {"detail": "This file is too large to preview. Download it to view it."},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        if request.method == "HEAD":
            return _set_preview_headers(HttpResponse(content_type=content_type), filename)
        try:
            if kind == "text":
                content = read_text_preview(stored_file)
            elif kind == "document":
                content = read_document_preview(stored_file, suffix)
            else:
                content = render_tiff_preview(stored_file)
        except PreviewUnavailable as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except OSError as exc:
            raise Http404("Document file not found.") from exc
        return _set_preview_headers(HttpResponse(content, content_type=content_type), filename)

    size = stored_file.size
    try:
        byte_range = _byte_range(request.headers.get("Range"), size)
    except InvalidRange:
        response = HttpResponse(status=416)
        response["Content-Range"] = f"bytes */{size}"
        response["Accept-Ranges"] = "bytes"
        return _set_preview_headers(response, filename)

    start, end = byte_range or (0, size - 1)
    length = max(0, end - start + 1)
    response_status = 206 if byte_range else 200
    if request.method == "HEAD":
        response = HttpResponse(status=response_status, content_type=content_type)
    else:
        try:
            stored_file.open("rb")
            stored_file.seek(start)
        except (OSError, ValueError) as exc:
            stored_file.close()
            raise Http404("Document file not found.") from exc
        response = StreamingHttpResponse(
            _stream_range(stored_file, length),
            status=response_status,
            content_type=content_type,
        )
    response["Content-Length"] = str(length)
    response["Accept-Ranges"] = "bytes"
    if byte_range:
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
    return _set_preview_headers(response, filename)
