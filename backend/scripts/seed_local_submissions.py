"""Add a small set of sample submissions to the local development database."""

import argparse
import random
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from PIL import Image, ImageDraw

import seed_mock_submissions as samples
from submissions.models import Artist, Submission, SubmissionLink, Work
from submissions.repositories import SubmissionDocumentRepository


def check_local_database():
    database = settings.DATABASES["default"]
    expected_path = (samples.BACKEND_DIR / "db.sqlite3").resolve()
    if (
        not settings.DEBUG
        or database["ENGINE"] != "django.db.backends.sqlite3"
        or Path(database["NAME"]).resolve() != expected_path
        or settings.STORAGE_BACKEND != "local"
    ):
        raise SystemExit("This script runs only with the local development SQLite database and local file storage.")
    executor = MigrationExecutor(connection)
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        raise SystemExit("Apply the database migrations before you add sample submissions.")


def make_pdf(title, artist_name):
    label = f"{title} by {artist_name}".replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 18 Tf 72 740 Td ({label}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    return bytes(pdf)


def make_png(number):
    colors = [(246, 165, 217), (204, 185, 241), (163, 214, 205), (247, 206, 150)]
    image = Image.new("RGB", (480, 320), colors[number % len(colors)])
    ImageDraw.Draw(image).text((24, 24), f"RAGE Zine sample {number}", fill=(15, 10, 20))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def add_sample(number, documents):
    artist_name = samples.make_artist_name()
    origin = samples.make_country_origin()
    artist = Artist.objects.create(
        artist_name=artist_name,
        pronouns=random.choice(samples.PRONOUNS),
        email=samples.make_email(artist_name, number),
        short_bio=samples.make_short_bio(),
        socials=samples.make_socials(artist_name),
        country_origin=origin,
        countries_residence=samples.make_countries_residence(origin),
        message_to_editors="Sample record for the local staff portal.",
        submitted_before=False,
        featured_before=False,
    )
    title = samples.make_title()
    description = samples.make_description()
    submission_type = random.choice(list(Submission.SubmissionType.values))
    language = random.choice(samples.LANGUAGES)
    submission = Submission.objects.create(
        artist=artist,
        artist_name=artist.artist_name,
        pronouns=artist.pronouns,
        email=artist.email,
        short_bio=artist.short_bio,
        socials=artist.socials,
        country_origin=artist.country_origin,
        countries_residence=artist.countries_residence,
        message_to_editors=artist.message_to_editors,
        submitted_before=False,
        featured_before=False,
        title=title,
        description=description,
        submission_type=submission_type,
        language=language,
        published_elsewhere=False,
    )
    work_count = 2 if number % 3 == 0 else 1
    for position in range(1, work_count + 1):
        work_title = title if position == 1 else samples.make_title()
        work_type = submission_type if position == 1 else Submission.SubmissionType.VISUAL_ART
        work = Work.objects.create(
            submission=submission,
            position=position,
            title=work_title,
            description=description if position == 1 else samples.make_description(),
            submission_type=work_type,
            language=language,
            published_elsewhere=False,
        )
        if work_type == Submission.SubmissionType.VISUAL_ART:
            upload = SimpleUploadedFile(f"sample-{number}-{position}.png", make_png(number + position), content_type="image/png")
            documents.create_visual_document(submission, upload, work=work)
        else:
            upload = SimpleUploadedFile(f"sample-{number}-{position}.pdf", make_pdf(work_title, artist_name), content_type="application/pdf")
            documents.create_text_document(submission, upload, work=work)
        if position == 1 and number % 2 == 0:
            SubmissionLink.objects.create(
                submission=submission,
                work=work,
                link_type=SubmissionLink.LinkType.OTHER,
                name="Example link",
                url="https://example.com/",
            )
    return submission


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=5, help="Number of records to add (default: 5).")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42).")
    args = parser.parse_args()
    if not 1 <= args.count <= 20:
        raise SystemExit("Choose a count from 1 to 20.")
    check_local_database()
    random.seed(args.seed)
    first_number = (Submission.objects.order_by("-pk").values_list("pk", flat=True).first() or 0) + 1
    documents = SubmissionDocumentRepository()
    created = []
    for number in range(first_number, first_number + args.count):
        with transaction.atomic():
            created.append(add_sample(number, documents).pk)
    print(f"Added {len(created)} local sample submissions: {', '.join(map(str, created))}.")


if __name__ == "__main__":
    main()
