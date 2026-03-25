import argparse
import os
import random
import sys
from pathlib import Path

from django.core.files.base import ContentFile


BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ragezine_portal.settings")

import django  # noqa: E402

django.setup()

from submissions.models import Submission, SubmissionText, SubmissionVisual  # noqa: E402


FIRST_NAMES = [
    "Amina", "Sofia", "Lea", "Nora", "Maya", "Elin", "Zara", "Iris", "Lina", "Freja",
    "Dalia", "Nadia", "Rosa", "Clara", "Ari", "Luna", "Mila", "Aya", "Noor", "Sara",
]
LAST_NAMES = [
    "Hassan", "Lind", "Moreau", "Kovac", "Berg", "Ahmed", "Nielsen", "Conti", "Wright", "Petrov",
    "Silva", "Khan", "Jensen", "Costa", "Novak", "Dubois", "Rahman", "Madsen", "Ali", "Meyer",
]
TITLE_PREFIXES = [
    "Salt", "Fire", "Mother", "Static", "Archive", "Body", "Night", "Thread", "Tender", "Riot",
    "Blue", "Glass", "Noise", "Memory", "River", "Stone", "Signal", "Dust", "Wire", "Echo",
]
TITLE_SUFFIXES = [
    "Index", "Prayer", "Practice", "Bloom", "Manual", "Weather", "Study", "Letter", "Draft", "Score",
    "Room", "Map", "Promise", "Sequence", "Field", "Gesture", "Machine", "Pattern", "Witness", "Syntax",
]
YEARS = ["2022", "2023", "2024", "2025", "2026", ""]
LANGUAGES = ["English", "Spanish", "Danish", "French", "German", "Italian", "Portuguese", "Other"]
PRONOUNS = ["she/her", "he/him", "they/them", "she/they", "he/they", "xe/xem", "ze/zir", "any", "other"]
COUNTRY_CODES = ["DK", "SE", "NO", "DE", "FR", "IT", "ES", "PT", "GB", "US", "CA", "EG", "PK", "SK"]
SOCIAL_DOMAINS = ["instagram.com", "substack.com", "artist.site", "portfolio.example", "tiktok.com"]
DESCRIPTION_FRAGMENTS = [
    "A study in feminist anger and collective memory.",
    "Built from diary fragments, annotations, and found images.",
    "Moves between softness and rupture without resolving either.",
    "Written as a direct address to the institutions that fail us.",
    "Centres domestic ritual, labour, and inherited silence.",
    "Interested in texture, repetition, and public grief.",
]
BIO_FRAGMENTS = [
    "works across text, print, and installation.",
    "is based between two cities and collaborates with community archives.",
    "focuses on feminist publishing, performance, and sound.",
    "makes work about migration, labour, and informal memory.",
    "has exhibited in independent spaces and artist-run festivals.",
    "often writes through fragments, lists, and documentary residue.",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Delete all submissions and seed the database with mock submissions.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=60,
        help="Number of mock submissions to create. Default: 60.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic output. Default: 42.",
    )
    return parser.parse_args()


def make_artist_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def make_title():
    return f"{random.choice(TITLE_PREFIXES)} {random.choice(TITLE_SUFFIXES)}"


def make_description():
    return " ".join(random.sample(DESCRIPTION_FRAGMENTS, k=3))


def make_short_bio():
    return " ".join(random.sample(BIO_FRAGMENTS, k=2))


def make_socials(artist_name):
    handle = artist_name.lower().replace(" ", "")
    domain = random.choice(SOCIAL_DOMAINS)
    return f"@{handle}\nhttps://{domain}/{handle}"


def make_email(artist_name, index):
    slug = artist_name.lower().replace(" ", ".")
    return f"{slug}.{index}@example.com"


def make_country_origin():
    return random.choice(COUNTRY_CODES)


def make_countries_residence(origin):
    pool = [code for code in COUNTRY_CODES if code != origin]
    residences = {origin}
    residences.update(random.sample(pool, k=random.randint(0, 2)))
    return list(residences)


def build_pdf_bytes(title, artist_name):
    body = (
        "%PDF-1.4\n"
        f"Mock submission for {artist_name}\n"
        f"Title: {title}\n"
        "This is placeholder content for development only.\n"
    )
    return body.encode("utf-8")


def build_image_bytes(index):
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        + bytes([0, 0, 0, 1, 0, 0, 0, 1, 8, 2, 0, 0, 0])
        + b"\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00"
        + bytes([index % 255])
        + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def delete_existing_submissions():
    for submission in Submission.objects.prefetch_related("texts", "visuals"):
        if submission.text_file:
            submission.text_file.delete(save=False)
        for text in submission.texts.all():
            text.file.delete(save=False)
        for visual in submission.visuals.all():
            visual.image.delete(save=False)

    Submission.objects.all().delete()


def create_mock_submission(index):
    artist_name = make_artist_name()
    submission_type = random.choice(list(Submission.SubmissionType.values))
    title = make_title()
    country_origin = make_country_origin()
    language = random.choice(LANGUAGES)
    allow_translation = language == "English" or random.choice([True, False])

    submission = Submission.objects.create(
        title=title,
        year=random.choice(YEARS),
        description=make_description(),
        submission_type=submission_type,
        artist_name=artist_name,
        pronouns=random.choice(PRONOUNS),
        short_bio=make_short_bio(),
        socials=make_socials(artist_name),
        email=make_email(artist_name, index),
        country_origin=country_origin,
        countries_residence=make_countries_residence(country_origin),
        language=language,
        allow_translation=allow_translation,
    )

    include_primary_text = submission_type in {
        Submission.SubmissionType.POETRY,
        Submission.SubmissionType.SHORT_FORM_WRITING,
        Submission.SubmissionType.LONG_FORM_WRITING,
        Submission.SubmissionType.OTHER,
    } or random.choice([True, False])

    if include_primary_text:
        submission.text_file.save(
            f"{artist_name.lower().replace(' ', '_')}_{index}.pdf",
            ContentFile(build_pdf_bytes(title, artist_name)),
            save=True,
        )

    extra_text_count = random.randint(0, 2)
    visual_count = random.randint(0, 4)

    if submission_type == Submission.SubmissionType.VISUAL_ART:
        visual_count = max(1, visual_count)
    if not include_primary_text and extra_text_count == 0 and visual_count == 0:
        extra_text_count = 1

    for text_index in range(extra_text_count):
        submission_text = SubmissionText(submission=submission)
        submission_text.file.save(
            f"{artist_name.lower().replace(' ', '_')}_{index}_text_{text_index + 1}.pdf",
            ContentFile(build_pdf_bytes(f"{title} draft {text_index + 1}", artist_name)),
            save=True,
        )

    for visual_index in range(visual_count):
        submission_visual = SubmissionVisual(submission=submission)
        submission_visual.image.save(
            f"{artist_name.lower().replace(' ', '_')}_{index}_visual_{visual_index + 1}.png",
            ContentFile(build_image_bytes(index + visual_index)),
            save=True,
        )


def main():
    args = parse_args()
    random.seed(args.seed)

    if args.count < 50:
        raise SystemExit("Please use --count 50 or higher.")

    delete_existing_submissions()

    for index in range(1, args.count + 1):
        create_mock_submission(index)

    print(f"Seeded {args.count} mock submissions.")


if __name__ == "__main__":
    main()
