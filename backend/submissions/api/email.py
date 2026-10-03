import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape

from submissions.documents import iter_submission_files
from submissions.serializers import country_name


def _submission_detail_rows(submission):
    countries_residence = ", ".join(
        country_name(code) for code in submission.countries_residence
    ) or "-"

    attached_files = [Path(stored_file.name).name for stored_file in iter_submission_files(submission)]
    attached_files_label = ", ".join(attached_files) if attached_files else "-"

    return [
        ("Submission ID", submission.id),
        ("Title", submission.title),
        ("Submission Type", f"{submission.get_submission_type_display()} ({submission.submission_type})"),
        ("Artist Name", submission.artist_name),
        ("Email", submission.email),
        ("Year", submission.year or "-"),
        ("Description", submission.description or "-"),
        ("Pronouns", submission.pronouns),
        ("Short Bio", submission.short_bio),
        ("Socials", submission.socials or "-"),
        ("Country of Origin", country_name(submission.country_origin)),
        ("Countries of Residence", countries_residence),
        ("Language", submission.language),
        ("Allow Translation", "yes" if submission.allow_translation else "no"),
        ("Created At", submission.created_at.isoformat()),
        ("Updated At", submission.updated_at.isoformat()),
        ("Files", attached_files_label),
    ]


def _format_corpus_html(corpus):
    if not corpus:
        return ""
    paragraphs = [segment.strip() for segment in corpus.split("\n\n") if segment.strip()]
    return "".join(
        f"<p style=\"margin:0 0 14px;line-height:1.7;\">{escape(paragraph).replace(chr(10), '<br>')}</p>"
        for paragraph in paragraphs
    )


def _build_plaintext_body(submission, corpus, attachment_note=""):
    detail_lines = [
        f"{label}: {value}"
        for label, value in _submission_detail_rows(submission)
    ]
    parts = [corpus.strip(), "", *detail_lines] if corpus else detail_lines
    if attachment_note:
        parts.extend(["", attachment_note])
    return "\n".join(parts).strip() + "\n"


def _build_html_body(submission, corpus, attachment_note=""):
    attachment_notice = f"<p>{escape(attachment_note)}</p>" if attachment_note else ""
    rows = "".join(
        (
            "<tr>"
            f"<th style=\"width:220px;padding:12px 16px;text-align:left;border:1px solid #d6d0e3;background:#f2eee8;color:#1a1a1a;vertical-align:top;font-weight:600;\">{escape(str(label))}</th>"
            f"<td style=\"padding:12px 16px;border:1px solid #e1d9d1;vertical-align:top;white-space:pre-wrap;color:#2f2a24;\">{escape(str(value))}</td>"
            "</tr>"
        )
        for label, value in _submission_detail_rows(submission)
    )

    return (
        "<div style=\"font-family:Georgia,'Times New Roman',serif;background:#f6f1ea;padding:24px;color:#211c16;\">"
        "<div style=\"max-width:860px;margin:0 auto;background:#fffdf8;border:1px solid #ddd2c4;\">"
        "<div style=\"padding:24px 28px;border-bottom:1px solid #e5ddd3;background:#efe6da;\">"
        "<div style=\"font-size:12px;letter-spacing:0.24em;text-transform:uppercase;color:#7d6c59;\">Rage Zine</div>"
        "<h2 style=\"margin:10px 0 0;font-size:28px;font-weight:600;\">Submission Received</h2>"
        "</div>"
        "<div style=\"padding:24px 28px;\">"
        f"{_format_corpus_html(corpus)}"
        "<div style=\"margin-top:20px;border:1px solid #ddd2c4;\">"
        "<table style=\"width:100%;border-collapse:collapse;background:#fff;\">"
        f"{rows}"
        "</table>"
        f"{attachment_notice}"
        "</div>"
        "</div>"
        "</div>"
        "</div>"
    )


def _build_message(submission, recipient):
    from_email = settings.SUBMISSION_EMAIL_FROM.strip()
    subject = settings.SUBMISSION_EMAIL_SUBJECT.strip()
    corpus = settings.SUBMISSION_EMAIL_BODY.strip()

    if not recipient or not from_email:
        return None

    files = list(iter_submission_files(submission))
    include_attachments = (
        sum(stored_file.size for stored_file in files)
        <= settings.SUBMISSION_EMAIL_ATTACHMENT_MAX_BYTES
    )
    attachment_note = (
        ""
        if include_attachments
        else "Files are stored with the submission and are not attached to this email."
    )

    message = EmailMultiAlternatives(
        subject=subject,
        body=_build_plaintext_body(submission, corpus, attachment_note),
        from_email=from_email,
        to=[recipient],
    )
    message.attach_alternative(
        _build_html_body(submission, corpus, attachment_note), "text/html"
    )

    for stored_file in files if include_attachments else ():
        stored_file.open("rb")
        try:
            content_type = mimetypes.guess_type(stored_file.name)[0] or "application/octet-stream"
            message.attach(
                filename=Path(stored_file.name).name,
                content=stored_file.read(),
                mimetype=content_type,
            )
        finally:
            stored_file.close()

    return message


def send_submission_emails(submission):
    applicant_message = _build_message(submission, submission.email)

    sent = 0
    outbound_messages = [applicant_message]
    outbound_messages.extend(
        _build_message(submission, recipient)
        for recipient in settings.SUBMISSION_NOTIFICATION_TO
    )

    for message in outbound_messages:
        if message is None:
            continue
        message.send(fail_silently=False)
        sent += 1
    return sent
