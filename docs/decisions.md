# Project decisions

This log records the current decisions for the RAGE Zine submission portal. It describes the product and the code in the `codex/submission-iteration` branch. It does not mean that the iteration has been merged or deployed.

## Submissions and artists

### D-01: One form request, one submission record, several works

The public form has two parts: artist information and submission information. A submission has one artist and one or more works. The contributor uses + and − controls to add or remove works. Each work has its own title, type, description, year, language, publication details, files, and links. The staff details page shows artist information first, then the numbered pieces, then tags, votes, and comments.

### D-02: Keep later form requests separate

Each public form request creates a new artist and submission record. A form can contain several works, which share that submission record. A later request creates another record even when the artist name and email match. The public form does not use a name and email as proof that the sender owns an earlier record.

Votes, tags, comments, and artist details stay with their own submission. The receipt lists the works in the new request and gives its new reference. Staff can review separate submissions from the same artist without merging their review records.

### D-03: Votes, tags, and comments belong to the whole submission

Each staff account has at most one vote on a submission. The choices are Yes, No, and See comment. No vote is the default; selecting it deletes that account's vote and does not add to the totals. Staff can change a vote. The vote list shows who voted and the time of the last change. See comment is a vote choice; it does not require or create a comment. Staff comments stay in one separate Comments section.

## Public form and files

### D-04: Use clear form groups and flexible entries

The form separates artist information from work information. Pronouns use suggested tags, and contributors can enter their own. Country of origin and country of residence both accept several countries. Pronouns and socials sit side by side; short bio and the message to the editors sit side by side. The layout stacks these fields on phones.

The current work type choices are Poetry, Visual art, Short form writing, Long form writing, and Other. `TBD` is a placeholder for a future type, not a choice in the form. Work links and uploaded files can be used together. The Links box accepts several HTTPS links, each with a name. A work needs at least one file or link.

### D-05: Keep file limits suited to video

The file limit is 5 GiB for one file and 10 GiB for all files in one form submission. Text uploads accept DOC, DOCX, and PDF. Visual uploads accept TIFF and PNG. Video uploads accept MP4, MOV, and WebM. File formats appear above each file picker; the size note appears below the file boxes. Each file box has its own clear control. The 1500-word text guidance is not an enforced limit.

### D-06: Confirm receipt by email

The backend tries to send one receipt after it saves a form submission. The receipt lists the works received in that request and gives its new submission reference. Uploaded files are not attached to the email. If email delivery fails, the submission stays saved and the server logs the error.

## Staff review and exports

### D-07: Group pieces under their artist in the staff list

The staff list shows one artist header for each submission, with one row per piece below it. Each row shows its title, a short description preview, type, and a download button without a number or date. The header shows the submission date and labels both origin and residence countries. Search matches artist names, piece titles, and full piece descriptions. Close title spellings also match. When a piece matches, the list shows it under its artist. Staff choose the sort category and direction in separate controls. The default order is newest submission first.

### D-08: Keep files private and preview them in the staff portal

Only staff can open submission details, files, and previews. The list download button gives staff a ZIP with only that piece's files and details. Staff can also download files one by one from the details page. The details page previews PDFs, supported documents, images, and videos where possible. Private S3 videos play in the site through short-lived signed URLs. The S3 bucket must remain private. Files that cannot be previewed can still be downloaded by staff.

### D-09: Export the same structure staff review

Excel starts with a Submissions sheet. It has one row per form request with artist details, submission date, piece titles, tags, and vote totals. Category tabs follow the form choices, plus an Uncategorized tab for older records. Each category row is one piece linked by submission ID and piece ID. Votes and Comments link to the submission. Files and Links link to the piece. There is no No vote column. The complete files ZIP includes this Excel workbook, one folder per submission, a submission summary, and separate folders with details and files for each piece.

## Operations and release

### D-10: Keep production settings outside Git

Production must run with `DJANGO_DEBUG=0`. The server keeps its private `.env` outside Git; example files contain variable names, not secrets. Django uses PostgreSQL in the Compose deployment and SQLite for local work. Rate limits and upload limits are set through environment variables. Production rate limits use shared Redis so all backend workers apply the same limits.

### D-11: Release through reviewed changes

The release path is a pull request to `main`, followed by CI checks and deployment from `main` to the Lightsail instance. The public portal and staff portal use separate HTTPS hostnames. Caddy handles public TLS; nginx serves the frontend and forwards API requests to Django. Review the branch and its CI results before merge.

### D-12: Prepare staff roles while keeping current access

All staff can review submissions. The `Submission Managers` group adds permission to delete submissions and download the complete ZIP or Excel export. Migration 0018 gives the group to all existing staff. New and newly promoted staff also receive it. A superuser can later remove the group from selected staff accounts to restrict these actions. The API checks the permissions, and the dashboard hides buttons that an account cannot use. See [staff roles](staff-roles.md).

## Open decisions

- **Future artist account:** If artists need to add work to an earlier submission, require proof that they control its email address before adding the work or showing earlier data.

For implementation details, see [the project README](../README.md), [production environment](production-environment.md), and [rate limiting](rate-limiting.md).
