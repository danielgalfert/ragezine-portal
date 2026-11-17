# Submission iteration review

Branch: `codex/submission-iteration`

This review describes the branch changes before merge. Production continues to run `main` until the pull request is merged.

## Public form

- Split the form into **Artist information** and **Submission information**.
- Added artist history questions and a message to the editors.
- Added repeatable piece cards. The form shows only + and − controls to add or remove one.
- Added publication history and an optional note for each piece.
- Added one named-link box beside the text, visual, and video file boxes. Contributors can add several links, give each one a name, and remove or clear links before they submit.
- Added PNG visual uploads. Put file formats above each upload input and size limits below it.
- Removed the form-wide clear button. Each upload box has a clear files button.
- Kept the existing pronoun suggestion system. Contributors can also enter their own pronouns.
- Placed pronouns beside socials, and short bio beside the message to the editors. These pairs stack on narrow screens.
- Kept country of origin and residence as multiple-country selectors.
- Trimmed text and link values before sending them. A source scan found no trailing spaces in the edited files.
- Left `TBD` as a placeholder for a future submission type, as requested. It is not a form choice.
- Placed the guidance boxes above the form and widened the form across the page. Used more columns for artist fields, work fields, links, and uploads. Moved pronoun controls out of the field grid to remove the empty space they caused beside shorter fields.
- Aligned the file boxes: their headings and format notes reserve equal space, and the file pickers stay in place when a file is selected. Each box keeps its own height when another box grows. Selected files appear below the picker in a scrollable list. A single size note appears below the boxes. The picker button no longer shows the browser's unused "No file chosen" label.
- Put one link access note below the four boxes for each piece.

## Server

- Added Artist and Work entities. A submission has one artist and one or more ordered works. Each work owns its files and links and has its own timestamp. Tags, votes, and comments belong to the submission.
- Added a migration that copies each existing submission into an artist and one work. It retains the old submission columns for compatibility and rollback during review. Old grouped records remain separate submissions to avoid merging votes or comments without an agreed rule.
- Added a batch submission endpoint. It validates all pieces before it saves any of them, then creates one submission with several works and sends one receipt email with the new titles.
- Each public form request creates a new artist and submission record, even when the name and email match an earlier request. Works in one form still share one submission.
- A later request cannot change an earlier artist profile, votes, tags, or comments. Its response and receipt cover its own works and new reference.
- Artist email is normalized for new submissions. The public form does not treat a name and email as proof of ownership of an earlier record.
- Kept the single submission endpoint for older clients.
- Added fields for the new questions and notes, plus named links and PNG upload validation. Migration 0017 adds a link name field while keeping old links valid.
- Kept the 5 GiB per-file and 10 GiB total upload limits. The form limits a batch to 60 files.

## Staff portal and exports

- Added a `Submission Managers` role. All current, new, and newly promoted staff receive it at first. Removing the role keeps review access but blocks deletion and complete ZIP or Excel export in the API and dashboard.

- Added separate controls for sort category (submission date or artist name) and direction. The default list order is newest submission first.
- Changed list search to match artist names, piece titles, and full piece descriptions.
- Made labels more prominent in the submission list and detail view.
- The list groups piece rows under a submission's artist header. Each row shows its title, a short description preview, type, and a down arrow download button without a number or date. The header shows the submission date and labels origin and residence countries. Each button downloads a ZIP with only that piece's files and details. Staff can also download each file from the details page. The details page shows the artist name, then numbered pieces with each work's fields, files, links, and previews. Tags, votes, and comments follow the pieces.
- Added the new fields to the detail view, Excel export, and ZIP details text. Excel has a Submissions sheet with one row per form request, category tabs with one row per piece, and Votes, Comments, Files, and Links sheets linked by IDs. The complete files ZIP includes the Excel workbook, a summary for each submission, and one details file and file folder per piece.
- Added an **Uncategorized** Excel tab for old records with no valid type. The other tabs follow the form categories.
- Kept the existing vote export columns. There is no **No vote** column.

## Checks

- Backend: all 102 tests passed, including migration, separate submission, staff role, piece download, and complete ZIP tests.
- Database migration check: no missing migration changes.
- Frontend: lint, build, and 10 utility tests passed. The production dependency audit found no vulnerabilities. A full audit reports a high-severity issue in the build-only `picomatch` package; see `docs/public-release-security.md`.
- Backend dependency audit: no known vulnerabilities found.
- No trailing source whitespace found by the scan.
- The local browser check covered the public form, staff dashboard, and submission details at 390 px and 1280 px widths. No horizontal overflow appeared. The form controls and staff list remained usable.
- A live local submission with two works and a small PDF returned HTTP 201. The file was saved, the console email backend produced the receipt, and the staff dashboard showed both works. Staff download, Excel and complete ZIP export, logout, and anonymous download denial passed. The test record and staff account were removed after the check.
- The production S3 upload path and a full 5 GiB transfer still need a check after deployment. Local testing uses SQLite and local file storage; the pull request CI uses PostgreSQL.

## Local sample data

- Applied migrations 0016 through 0018 to this worktree's SQLite database.
- Added five sample submissions (IDs 2-6) with eight works, seven local files, and three named links. The original submission (ID 1) remains. The database now has six submissions.
- Added `backend/scripts/seed_local_submissions.py` for later local samples. It adds records, keeps existing data, and refuses nonlocal database or file storage settings. The older `seed_mock_submissions.py` still deletes existing submissions; use the new script for local review.
- Before the migration, saved a verified SQLite backup at `C:\Users\daniel\Desktop\projects\ragezine-portal\backend\media\local-backups\submission-iteration-before-samples-20261115.sqlite3`.

## Review and revert

The worktree had no pre-existing edits when this iteration started. Review the pull request diff before merge. The SQLite backup can restore the local database to its state before the sample run.
