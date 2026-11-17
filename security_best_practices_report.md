# Security best practices review

Reviewed branch: `codex/submission-iteration` on 2026-11-16. This is a code review. It is not a live server audit or a penetration test.

## Summary

The critical public artist matching issue was fixed in this worktree. Each public request now creates a new artist and submission record. A manager role now guards deletion and full exports, but all staff get that role at first by request. The branch still accepts very large public uploads on one VM.

## Critical issue fixed in this worktree

### 1. Public requests can take over an existing artist submission

- **Rule:** DJANGO-AUTHZ-001
- **Previous behavior:** The two public create actions matched an existing record using only `artist_name` and `email`. A match changed the stored artist and returned earlier submission data.
- **Impact before the fix:** Someone who knew an artist's name and email could change that artist's submission and read earlier work.
- **Fix:** `backend/submissions/api/submission_views.py:47-57` creates a fresh artist and submission for each request. Both public actions call it. `backend/submissions/test_batch.py` checks that matching details do not change or disclose an earlier submission.
- **Remaining limit:** If artists need to add work to an earlier submission later, that flow will need proof of email control. No such flow is offered now.

## High severity

### 2. Every staff account starts with delete and full export access

- **Rule:** DJANGO-AUTHZ-001
- **Location:** `backend/submissions/api/submission_views.py:71-77`, `backend/submissions/api/permissions.py`, `backend/submissions/migrations/0018_staff_manager_role.py`, `backend/submissions/signals.py`
- **Evidence:** The API checks `delete_submission` for deletion and `export_all_submissions` for full exports. Migration 0018 gives both permissions to all existing staff through `Submission Managers`. New staff receive the same group when created.
- **Impact:** A lost or misused staff session can delete the full submission set and its files through the API.
- **Next step:** Remove the manager group from staff who only need review access. The role gate is in place; the initial broad assignment is a deliberate policy choice.
- **Mitigation:** Keep tested PostgreSQL and S3 backups or S3 versioning. Log each deletion with the staff user and submission ID.
- **Policy note:** The user confirmed that every staff account should keep this access for now.

### 3. Public uploads can fill temporary disk space on the VM

- **Rule:** DJANGO-UPLOAD-001
- **Location:** `frontend/ragezine-portal/nginx.conf:38-43`, `frontend/ragezine-portal/nginx.conf:72-86`, `docker-compose.yml:68-72`, `docker-compose.yml:89-95`, `backend/ragezine_portal/settings.py:132-137`, `backend/submissions/api/submission_views.py:233-278`
- **Evidence:** nginx accepts an 11 GiB request body and up to two active upload requests. Django checks file totals after request parsing. Large files use temporary storage under Django's default upload handlers, and nginx buffers request bodies by default. The repo does not set a separate temporary disk quota.
- **Impact:** An anonymous caller can consume many gigabytes before the app rejects a request. A full disk can stop uploads, database writes, and deployment on this VM. Rate limits reduce the risk but do not remove it.
- **Fix:** Give nginx and Django bounded temporary storage. Reject bodies above the true request limit at the edge. For a durable design, send large files directly to private S3 with short-lived, scoped authorization, then finalize the submission after server checks.
- **Mitigation:** Alert on free disk space, keep the connection limits, and measure disk use during a full-size test upload. The requested 5 GiB file limit can stay.
- **False positive check:** Confirm live free space, mount points, and quotas. These are outside this branch.

## Medium severity

### 4. Staff login has no second factor

- **Rule:** DJANGO-ADMIN-001
- **Location:** `backend/submissions/api/auth.py:28-56`, `backend/ragezine_portal/urls.py:5`, `docs/public-release-security.md:28`
- **Evidence:** Staff login uses a username and password. Login rate limits are present, but this branch has no second factor. Django admin is enabled at `/admin/`.
- **Impact:** A stolen staff password can expose applicant data. A stolen superuser password can grant Django admin access.
- **Fix:** Add a tested second factor that covers staff login and Django admin, or restrict Django admin to a trusted network.
- **Mitigation:** Keep unique passwords, short sessions, login alerts, and prompt account removal.
- **False positive check:** Verify whether an external identity or network layer requires a second factor in production.

### 5. Uploaded documents are not checked for malware

- **Rule:** DJANGO-UPLOAD-001
- **Location:** `backend/submissions/utils/uploads.py:27-72`, `backend/submissions/api/downloads.py:375-397`, `docs/public-release-security.md:26`
- **Evidence:** Upload validation checks extensions and signatures. Staff can download original files. The repo has no malware scan or quarantine step.
- **Impact:** A malicious document can reach staff who open it in a local application.
- **Fix:** Scan new objects before staff can download them, or quarantine them until a scan completes.
- **Mitigation:** Use updated viewers. Do not enable document macros. Prefer safe inline previews where possible.
- **False positive check:** An external S3 scan service may exist, but it is not visible in the repo.

## Controls seen in this branch

- Submission list and detail, downloads, previews, comments, tags, and votes require staff access.
- Login uses CSRF checks and rate limits. Production uses secure session and CSRF cookies.
- Uploads have extension, signature, count, and size checks. Link fields accept public HTTPS URLs; the server does not fetch them.
- The frontend renders applicant text with React escaping. nginx sets a CSP and browser security headers.
- CI runs tests, deployment checks, and dependency audits.

## Limits of this review

I did not inspect the live S3 policy, IAM permissions, disk quotas, backups, TLS behavior, or external identity controls. I made no code or server changes during this review.
