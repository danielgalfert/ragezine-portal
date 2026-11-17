from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryFile
from zipfile import ZIP_STORED, ZipFile

from django.core.exceptions import SuspiciousFileOperation
from django.db.models import Prefetch
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.text import get_valid_filename
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAdminUser

from submissions.api.throttles import StaffExportThrottle
from submissions.api.permissions import CanExportAllSubmissions
from submissions.models import Submission, SubmissionDocument, SubmissionVote, Work
from submissions.repositories import SubmissionRepository
from submissions.serializers import country_name, origin_codes
from submissions.utils import sanitize_single_line


EXPORT_FILENAME = "ragezine-submissions-complete.zip"
SUBMISSION_DETAILS_FILENAME = "submission_details.txt"
PIECE_DETAILS_FILENAME = "piece_details.txt"
SUBMISSION_COLUMNS = [
    ("submission_id", "Submission ID"),
    ("artist_id", "Artist ID"),
    ("artist_name", "Artist Name"),
    ("pronouns", "Pronouns"),
    ("email", "Email"),
    ("country_origin", "Countries of Origin"),
    ("countries_residence", "Countries of Residence"),
    ("short_bio", "Short Bio"),
    ("socials", "Socials"),
    ("message_to_editors", "Message to Editors"),
    ("submitted_before", "Submitted Before"),
    ("featured_before", "Featured Before"),
    ("volume", "Volume"),
    ("submitted_at", "Submitted At"),
    ("piece_count", "Piece Count"),
    ("piece_titles", "Piece Titles"),
    ("tags", "Tags"),
    ("vote_yes", "Yes Votes"),
    ("vote_no", "No Votes"),
    ("vote_see_comment", "See Comment Votes"),
    ("vote_total", "Total Votes"),
]
PIECE_COLUMNS = [
    ("submission_id", "Submission ID"),
    ("piece_number", "Piece Number"),
    ("piece_id", "Piece ID"),
    ("artist_name", "Artist Name"),
    ("title", "Title"),
    ("submission_type", "Type"),
    ("description", "Description"),
    ("year", "Year"),
    ("language", "Language"),
    ("published_elsewhere", "Published Elsewhere"),
    ("published_where", "Published Where"),
    ("anything_else", "Anything Else"),
    ("file_count", "File Count"),
    ("link_count", "Link Count"),
]
VOTES_COLUMNS = [
    ("submission_id", "Submission ID"),
    ("artist_name", "Artist Name"),
    ("piece_titles", "Piece Titles"),
    ("voter", "Voter"),
    ("vote", "Vote"),
    ("last_changed", "Last Changed"),
]
COMMENTS_COLUMNS = [
    ("submission_id", "Submission ID"),
    ("artist_name", "Artist Name"),
    ("author", "Author"),
    ("comment", "Comment"),
    ("created_at", "Created At"),
]
FILES_COLUMNS = [
    ("submission_id", "Submission ID"),
    ("piece_id", "Piece ID"),
    ("piece_title", "Piece Title"),
    ("file_type", "File Type"),
    ("filename", "Filename"),
    ("size", "Size (bytes)"),
]
LINKS_COLUMNS = [
    ("submission_id", "Submission ID"),
    ("piece_id", "Piece ID"),
    ("piece_title", "Piece Title"),
    ("type", "Type"),
    ("name", "Name"),
    ("link", "Link"),
]
WIDE_TEXT_FIELDS = {
    "description", "short_bio", "message_to_editors", "published_where",
    "anything_else", "piece_titles", "comment", "link",
}
VOTE_COLUMN_CHOICES = {
    "vote_yes": SubmissionVote.Choice.YES,
    "vote_no": SubmissionVote.Choice.NO,
    "vote_see_comment": SubmissionVote.Choice.SEE_COMMENT,
}
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n", "\x00", "＝", "＋", "－", "＠")
submission_repository = SubmissionRepository()


def _works(submission):
    works = list(submission.works.all())
    return works or [submission]


def _safe_path_segment(value, fallback):
    try:
        cleaned = get_valid_filename(sanitize_single_line(value))
    except SuspiciousFileOperation:
        cleaned = ""
    return cleaned or fallback


def _submission_archive_name(submission):
    artist_segment = _safe_path_segment(
        submission.artist_name,
        f"submission-{submission.id}",
    )
    return f"ragezine-submission-{submission.id}-{artist_segment}.zip"


def _submission_detail_lines(submission):
    artist = submission.artist or submission
    countries_residence = ", ".join(
        country_name(code) for code in artist.countries_residence
    ) or "-"
    return [
        f"Submission ID: {submission.id}",
        f"Artist ID: {submission.artist_id or '-'}",
        f"Artist Name: {artist.artist_name}",
        f"Email: {artist.email}",
        f"Pronouns: {artist.pronouns}",
        f"Short Bio: {artist.short_bio}",
        f"Message to Editors: {artist.message_to_editors or '-'}",
        f"Submitted Before: {_excel_yes_no(artist.submitted_before) or '-'}",
        f"Featured Before: {_excel_yes_no(artist.featured_before) or '-'}",
        f"Socials: {artist.socials or '-'}",
        f"Country of Origin: {', '.join(country_name(code) for code in origin_codes(artist.country_origin))}",
        f"Countries of Residence: {countries_residence}",
        f"Submitted At: {submission.created_at.isoformat()}",
    ]


def _format_piece_details(work, position):
    lines = [
        f"Piece {position}",
        f"Title: {work.title}",
        f"Submission Type: {work.get_submission_type_display()} ({work.submission_type})",
        f"Year: {work.year or '-'}",
        f"Description: {work.description or '-'}",
        f"Language: {work.language}",
        f"Published Elsewhere: {_excel_yes_no(work.published_elsewhere) or '-'}",
        f"Published Where: {work.published_where or '-'}",
        f"Anything Else: {work.anything_else or '-'}",
        "Files:",
    ]
    lines.extend(f"- {document.original_filename or Path(document.file.name).name}" for document in work.documents.all())
    lines.append("Links:")
    lines.extend(f"- {link.name or link.get_link_type_display()}: {link.url}" for link in work.links.all())
    return "\n".join(lines) + "\n"


def _format_submission_details(submission, selected_work=None):
    lines = _submission_detail_lines(submission)
    works = [(selected_work.position, selected_work)] if selected_work else enumerate(_works(submission), start=1)
    for position, work in works:
        lines.extend(["", _format_piece_details(work, position).rstrip("\n")])
    return "\n".join(lines) + "\n"


def _format_submission_summary(submission):
    lines = _submission_detail_lines(submission)
    lines.extend(["", "Pieces:"])
    for position, work in enumerate(_works(submission), start=1):
        lines.append(f"{position}. {work.title} ({work.get_submission_type_display()})")
    return "\n".join(lines) + "\n"


def _safe_excel_text(value):
    if isinstance(value, str) and value.lstrip().startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def _excel_yes_no(value):
    return "" if value is None else "Yes" if value else "No"


def _excel_datetime(value):
    return value.replace(tzinfo=None) if value else None


def _piece_id(work):
    return work.pk if isinstance(work, Work) else ""


def _submission_excel_row(submission, works):
    artist = submission.artist or submission
    vote_counts = Counter(vote.choice for vote in submission.export_votes)
    values = {
        "submission_id": submission.pk,
        "artist_id": submission.artist_id or "",
        "artist_name": artist.artist_name,
        "pronouns": artist.pronouns,
        "email": artist.email,
        "country_origin": ", ".join(country_name(code) for code in origin_codes(artist.country_origin)),
        "countries_residence": ", ".join(country_name(code) for code in artist.countries_residence),
        "short_bio": artist.short_bio,
        "socials": artist.socials,
        "message_to_editors": artist.message_to_editors,
        "submitted_before": _excel_yes_no(artist.submitted_before),
        "featured_before": _excel_yes_no(artist.featured_before),
        "volume": submission.volume,
        "submitted_at": _excel_datetime(submission.created_at),
        "piece_count": len(works),
        "piece_titles": ", ".join(work.title for work in works),
        "tags": ", ".join(tag.name for tag in submission.tags.all()),
        "vote_total": sum(vote_counts.values()),
    }
    values.update({field: vote_counts[choice] for field, choice in VOTE_COLUMN_CHOICES.items()})
    return [_safe_excel_text(values[field]) for field, _ in SUBMISSION_COLUMNS]


def _piece_excel_row(submission, work, position, known_types):
    values = {
        "submission_id": submission.pk,
        "piece_number": position,
        "piece_id": _piece_id(work),
        "artist_name": (submission.artist or submission).artist_name,
        "title": work.title,
        "submission_type": work.get_submission_type_display() if work.submission_type in known_types else "Uncategorized",
        "description": work.description,
        "year": work.year,
        "language": work.language,
        "published_elsewhere": _excel_yes_no(work.published_elsewhere),
        "published_where": work.published_where,
        "anything_else": work.anything_else,
        "file_count": work.documents.count(),
        "link_count": work.links.count(),
    }
    return [_safe_excel_text(values[field]) for field, _ in PIECE_COLUMNS]


def _resolve_excel_filename(submissions):
    volumes = sorted({submission.volume for submission in submissions if submission.volume is not None})
    if len(volumes) == 1:
        volume_number = volumes[0]
    else:
        volume_number = Submission._meta.get_field("volume").default
    return f"rage_submissions_volume{volume_number}.xlsx"


def _autosize_worksheet(worksheet, columns):
    for column_index, (field_name, _) in enumerate(columns, start=1):
        column_letter = worksheet.cell(row=1, column=column_index).column_letter
        if field_name in WIDE_TEXT_FIELDS:
            worksheet.column_dimensions[column_letter].width = 80 if field_name == "link" else 48
            continue

        max_length = 0
        for row in worksheet.iter_rows(
            min_row=1,
            max_row=worksheet.max_row,
            min_col=column_index,
            max_col=column_index,
        ):
            value = row[0].value
            if value is None:
                continue
            max_length = max(max_length, len(str(value)))
        worksheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 36)


def _add_excel_sheet(workbook, name, columns):
    worksheet = workbook.create_sheet(title=name)
    worksheet.freeze_panes = "A2"
    worksheet.append([header for _, header in columns])
    worksheet.row_dimensions[1].height = 32
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    return worksheet


def _finish_excel_sheet(worksheet, columns):
    for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
        for column_index, cell in enumerate(row, start=1):
            field_name = columns[column_index - 1][0]
            cell.alignment = Alignment(vertical="top", wrap_text=field_name in WIDE_TEXT_FIELDS)
        if row:
            worksheet.row_dimensions[row[0].row].height = 52
    _autosize_worksheet(worksheet, columns)


def _get_export_submissions():
    return list(
        submission_repository.list().select_related("artist").prefetch_related(
            "tags",
            "staff_comments",
            "works__documents",
            "works__links",
            Prefetch(
                "votes",
                queryset=SubmissionVote.objects.filter(
                    choice__in=SubmissionVote.Choice.values
                ).select_related("voter"),
                to_attr="export_votes",
            )
        )
    )


def _build_excel_workbook(submissions=None):
    if submissions is None:
        submissions = _get_export_submissions()
    records = [(submission, _works(submission)) for submission in submissions]
    buffer = BytesIO()
    workbook = Workbook()
    workbook.remove(workbook.active)

    submissions_sheet = _add_excel_sheet(workbook, "Submissions", SUBMISSION_COLUMNS)
    for submission, works in records:
        submissions_sheet.append(_submission_excel_row(submission, works))
    _finish_excel_sheet(submissions_sheet, SUBMISSION_COLUMNS)

    categories = [(submission_type.value, submission_type.label) for submission_type in Submission.SubmissionType]
    categories.append(("uncategorized", "Uncategorized"))
    known_types = {value for value, _ in categories}
    category_sheets = {
        value: _add_excel_sheet(workbook, label, PIECE_COLUMNS)
        for value, label in categories
    }
    for submission, works in records:
        for position, work in enumerate(works, start=1):
            category = work.submission_type if work.submission_type in known_types else "uncategorized"
            category_sheets[category].append(_piece_excel_row(submission, work, position, known_types))
    for worksheet in category_sheets.values():
        _finish_excel_sheet(worksheet, PIECE_COLUMNS)

    votes_sheet = _add_excel_sheet(workbook, "Votes", VOTES_COLUMNS)
    comments_sheet = _add_excel_sheet(workbook, "Comments", COMMENTS_COLUMNS)
    files_sheet = _add_excel_sheet(workbook, "Files", FILES_COLUMNS)
    links_sheet = _add_excel_sheet(workbook, "Links", LINKS_COLUMNS)
    for submission, works in records:
        artist_name = _safe_excel_text((submission.artist or submission).artist_name)
        piece_titles = _safe_excel_text(", ".join(work.title for work in works))
        for vote in submission.export_votes:
            votes_sheet.append([
                submission.pk,
                artist_name,
                piece_titles,
                _safe_excel_text(vote.voter.get_username()),
                vote.get_choice_display(),
                _excel_datetime(vote.updated_at),
            ])
        for comment in submission.staff_comments.all():
            comments_sheet.append([
                submission.pk,
                artist_name,
                _safe_excel_text(comment.author_name),
                _safe_excel_text(comment.body),
                _excel_datetime(comment.created_at),
            ])
        for work in works:
            for document in work.documents.all():
                files_sheet.append([
                    submission.pk,
                    _piece_id(work),
                    _safe_excel_text(work.title),
                    document.get_document_type_display(),
                    _safe_excel_text(document.original_filename or Path(document.file.name).name),
                    document.size,
                ])
            for link in work.links.all():
                links_sheet.append([
                    submission.pk,
                    _piece_id(work),
                    _safe_excel_text(work.title),
                    link.get_link_type_display(),
                    _safe_excel_text(link.name),
                    _safe_excel_text(link.url),
                ])
    for worksheet, columns in (
        (votes_sheet, VOTES_COLUMNS),
        (comments_sheet, COMMENTS_COLUMNS),
        (files_sheet, FILES_COLUMNS),
        (links_sheet, LINKS_COLUMNS),
    ):
        _finish_excel_sheet(worksheet, columns)

    workbook.save(buffer)
    buffer.seek(0)
    return buffer.getvalue(), _resolve_excel_filename(submissions)


def _build_complete_download_zip():
    buffer = TemporaryFile(mode="w+b")

    try:
        submissions = _get_export_submissions()
        workbook_bytes, workbook_name = _build_excel_workbook(submissions)
        with ZipFile(buffer, "w", compression=ZIP_STORED, allowZip64=True) as archive:
            archive.writestr(workbook_name, workbook_bytes)
            archive.writestr("submissions/", b"")

            for submission in submissions:
                _write_submission_to_archive(archive, submission, separate_piece_details=True)

        buffer.seek(0)
        return buffer
    except Exception:
        buffer.close()
        raise


def _write_submission_to_archive(archive, submission, selected_work=None, separate_piece_details=False):
    artist_segment = _safe_path_segment(
        (submission.artist or submission).artist_name,
        f"submission-{submission.id}",
    )
    submission_root = f"submissions/{artist_segment}-{submission.id}"
    archive.writestr(
        f"{submission_root}/{SUBMISSION_DETAILS_FILENAME}",
        _format_submission_summary(submission) if separate_piece_details
        else _format_submission_details(submission, selected_work),
    )

    used_names_by_piece = defaultdict(set)
    if separate_piece_details:
        for position, work in enumerate(_works(submission), start=1):
            piece_folder = f"piece-{position}"
            archive.writestr(
                f"{submission_root}/{piece_folder}/{PIECE_DETAILS_FILENAME}",
                _format_piece_details(work, position),
            )
            used_names_by_piece[piece_folder].add(PIECE_DETAILS_FILENAME.casefold())

    documents = selected_work.documents.all() if selected_work else submission.documents.all()
    for document in documents:
        stored_file = document.file
        piece_folder = f"piece-{document.work.position}" if document.work_id else "piece-1"
        used_names = used_names_by_piece[piece_folder]
        file_name = _safe_path_segment(
            document.original_filename or Path(stored_file.name).name,
            f"file-{len(used_names) + 1}",
        )
        stem = Path(file_name).stem
        suffix = Path(file_name).suffix
        number = 2
        while file_name.casefold() in used_names:
            file_name = f"{stem}-{number}{suffix}"
            number += 1
        used_names.add(file_name.casefold())

        stored_file.open("rb")
        try:
            with archive.open(
                f"{submission_root}/{piece_folder}/{file_name}", "w", force_zip64=True
            ) as archived_file:
                copyfileobj(stored_file, archived_file, length=1024 * 1024)
        finally:
            stored_file.close()


def _build_submission_download_zip(submission):
    buffer = TemporaryFile(mode="w+b")
    try:
        with ZipFile(buffer, "w", compression=ZIP_STORED, allowZip64=True) as archive:
            _write_submission_to_archive(archive, submission)
        buffer.seek(0)
        return buffer, _submission_archive_name(submission)
    except Exception:
        buffer.close()
        raise


def _build_work_download_zip(work):
    buffer = TemporaryFile(mode="w+b")
    try:
        with ZipFile(buffer, "w", compression=ZIP_STORED, allowZip64=True) as archive:
            _write_submission_to_archive(archive, work.submission, selected_work=work)
        buffer.seek(0)
        title_segment = _safe_path_segment(work.title, f"work-{work.pk}")
        return buffer, f"ragezine-submission-{work.submission_id}-work-{work.position}-{title_segment}.zip"
    except Exception:
        buffer.close()
        raise


@api_view(["GET"])
@permission_classes([IsAdminUser])
def document_download(request, document_id):
    document = get_object_or_404(SubmissionDocument, pk=document_id)
    stored_file = document.file
    if not stored_file.name or not stored_file.storage.exists(stored_file.name):
        raise Http404("Document file not found.")

    filename = _safe_path_segment(
        document.original_filename or Path(stored_file.name).name,
        f"document-{document_id}",
    )
    try:
        stored_file.open("rb")
    except OSError as exc:
        raise Http404("Document file not found.") from exc
    return FileResponse(
        stored_file,
        as_attachment=True,
        filename=filename,
        content_type="application/octet-stream",
    )


@api_view(["GET"])
@permission_classes([CanExportAllSubmissions])
@throttle_classes([StaffExportThrottle])
def complete_download(request):
    return FileResponse(
        _build_complete_download_zip(),
        as_attachment=True,
        filename=EXPORT_FILENAME,
        content_type="application/zip",
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
@throttle_classes([StaffExportThrottle])
def submission_download(request, submission_id):
    submission = get_object_or_404(
        submission_repository.list_with_documents(),
        pk=submission_id,
    )
    zip_file, export_filename = _build_submission_download_zip(submission)
    return FileResponse(
        zip_file,
        as_attachment=True,
        filename=export_filename,
        content_type="application/zip",
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
@throttle_classes([StaffExportThrottle])
def work_download(request, work_id):
    work = get_object_or_404(
        Work.objects.select_related("submission").prefetch_related("documents", "links"),
        pk=work_id,
    )
    zip_file, export_filename = _build_work_download_zip(work)
    return FileResponse(
        zip_file,
        as_attachment=True,
        filename=export_filename,
        content_type="application/zip",
    )


@api_view(["GET"])
@permission_classes([CanExportAllSubmissions])
@throttle_classes([StaffExportThrottle])
def excel_download(request):
    workbook_bytes, export_filename = _build_excel_workbook()
    response = HttpResponse(
        workbook_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{export_filename}"'
    response["Content-Length"] = str(len(workbook_bytes))
    return response
