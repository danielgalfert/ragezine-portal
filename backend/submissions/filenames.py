import re
from pathlib import Path

from submissions.utils import sanitize_single_line


def _name_part(value, fallback):
    part = re.sub(r"[^\w]+|_", "-", sanitize_single_line(value), flags=re.UNICODE)
    return part.strip("-") or fallback


def submission_document_filename(document):
    """Use the name shown on the submission form for every stored document."""
    submission = document.submission
    artist = submission.artist.artist_name if submission.artist_id else submission.artist_name
    title = document.work.title if document.work_id else submission.title
    suffix = Path(document.original_filename or document.file.name).suffix.lower()

    siblings = document.work.documents.all() if document.work_id else submission.documents.all()
    number = 0
    for sibling in siblings:
        sibling_suffix = Path(sibling.original_filename or sibling.file.name).suffix.lower()
        if (document.work_id or sibling.work_id is None) and sibling_suffix == suffix and sibling.pk <= document.pk:
            number += 1

    duplicate = f"-{number}" if number > 1 else ""
    artist_part = _name_part(artist, "Artist")[:120].rstrip("-")
    title_part = _name_part(title, "Submission")[:120].rstrip("-")
    stem = f"{artist_part}_{title_part}"
    stem = stem[: 255 - len(duplicate) - len(suffix)].rstrip("-_ ")
    return f"{stem}{duplicate}{suffix}"
