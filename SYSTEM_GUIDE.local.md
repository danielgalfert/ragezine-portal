# Ragezine Portal: System and Debugging Guide

This document describes the code as it exists in this workspace on 2026-09-24. It is a local, Git-ignored operations note, not a deployment guarantee. Paths below are relative to the repository root. Avoid putting secrets or real applicant data into logs, shell history, issue reports, or this document.

## 1. System at a glance

The application collects public art/writing submissions and gives staff a private dashboard and Django admin interface for reviewing and exporting them. There is one React frontend, one Django REST Framework (DRF) backend, and one database. Uploaded files are stored separately from database rows. The backend also sends submission emails synchronously after the database write.

```text
Browser
  | HTTP (in production, TLS must terminate at an external proxy or a configured edge)
  v
nginx :80 (host port 8080 by default)
  |-- /, /login, /dashboard, /assets/* -> compiled React files
  |-- /static/*                   -> Django collectstatic volume
  |-- /api/*, /admin/*            -> backend:8000 (reverse proxy)
  `-- /media and /media/*         -> 404, deliberately
                                      |
                                      v
                               Gunicorn / Django / DRF
                                |        |         |
                                v        v         v
                             PostgreSQL media     SMTP or console email
                             (rows)     volume
```

The browser has one public origin in the Compose deployment. nginx forwards `/api/` and `/admin/` without issuing a browser redirect. Django is not directly published to the host by Compose. Only nginx's port is published. `docker-compose.yml` is the authoritative service topology.

## 2. Source map and ownership

| Area | Primary files | Responsibility |
| --- | --- | --- |
| Compose and images | `docker-compose.yml`, `backend/Dockerfile`, `frontend/ragezine-portal/Dockerfile`, `frontend/ragezine-portal/nginx.conf` | Build, process startup, network routing, persistent volumes |
| Django settings and URLs | `backend/ragezine_portal/settings.py`, `backend/ragezine_portal/urls.py`, `backend/submissions/api/urls.py` | Environment, middleware, storage, database, HTTP routing |
| Database injection | `backend/ragezine_portal/database.py` | Select SQLite or PostgreSQL configuration and the residence field type |
| Domain schema | `backend/submissions/models.py`, `backend/submissions/migrations/` | Submission and document rows and schema evolution |
| Persistence API | `backend/submissions/repositories.py` | Shared ORM queries and creation methods |
| API data boundary | `backend/submissions/serializers.py`, `backend/submissions/utils/` | Validation, normalization, output shape, filename sanitization |
| Submission endpoint | `backend/submissions/api/submission_views.py` | Public create; staff-only other CRUD actions |
| Authentication | `backend/submissions/api/auth.py` | CSRF bootstrap, staff login, logout, session introspection |
| Protected exports | `backend/submissions/api/downloads.py`, `backend/submissions/documents.py` | Individual file, per-submission ZIP, complete ZIP, Excel |
| Email | `backend/submissions/api/email.py` | Applicant and internal notification messages |
| Django admin | `backend/submissions/admin.py` | Staff back-office and protected document links |
| React entry and routes | `frontend/ragezine-portal/src/App.jsx`, `src/pages/` | Submission, login, dashboard screens |
| Browser API client | `frontend/ragezine-portal/src/api/client.js`, `src/services/` | Axios configuration, auth, submission, download calls |

`SubmissionViewSet` is a DRF `ModelViewSet`: DRF's router creates the ordinary list, retrieve, create, update, and delete routes. Its `get_queryset()` supplies the ORM `QuerySet` from `SubmissionRepository.list()`. A QuerySet is a lazy database query definition; evaluation happens when DRF serializes it or when code explicitly materializes it. The repository is shared across engines because Django's ORM performs common CRUD; the selected database handler configures the connection and engine-specific `countries_residence` model field. This is configuration-level dependency selection, not a second hand-written CRUD implementation.

## 3. Deployment, startup, and durable state

Compose defines exactly three services:

1. `db`: `postgres:16-alpine`; environment-derived database/user/password; `postgres_data` named volume; `pg_isready` health check.
2. `backend`: Python 3.12 image; loads root `.env`, forces `DJANGO_DB_ENGINE=postgres` and `POSTGRES_HOST=db`; waits for healthy `db`; runs `migrate --noinput`, `collectstatic --noinput`, then two Gunicorn workers on port 8000 with a 120-second worker timeout. It mounts `media_data` at `/app/media` and `static_data` at `/app/staticfiles`. Health is an internal GET of `/api/auth/csrf/`.
3. `nginx`: multi-stage build uses Node 22 and `npm ci`/`npm run build`, then copies the build into nginx 1.27. It waits for healthy backend; publishes `${RAGEZINE_HTTP_PORT:-8080}:80`; reads `static_data` at `/usr/share/nginx/html/static` read-only.

The frontend Docker build sets `VITE_API_URL=/api/`. Vite substitutes this at *build time*, so changing an environment variable on the running nginx container will not change the compiled client; rebuild the image. nginx serves SPA deep links via `try_files ... /index.html`, forwards `/api/` and `/admin/` to `http://backend:8000`, and returns 404 for `/media` and `/media/*`. There is no nginx media mount by design.

The three named volumes have different recovery needs: `postgres_data` holds relational data, `media_data` holds uploaded bytes, and `static_data` is regenerable via `collectstatic`. Back up and restore the first two as a consistent pair. A database row can reference a missing file, and an orphan file can outlive a rolled-back row. Do not equate a database backup alone with a full submission backup. `docker compose down --volumes` would delete these named volumes and must not be used casually.

The repo root `.env` supplies Compose interpolation and backend environment; `backend/.env` can be loaded by `python-dotenv` for local non-Compose runs. Use the example env files to discover variable names; do not commit real `.env` files. `DJANGO_DEBUG` defaults to enabled and `DJANGO_SECRET_KEY` has a development fallback, so production must explicitly override them. `DJANGO_ALLOWED_HOSTS` defaults to local hosts. The current nginx configuration is plain HTTP and does not itself terminate TLS.

## 4. Backend model, persistence, and storage

`Submission` stores metadata: title, year, description, category (`submission_type`), volume, artist identity and contact information, country codes, language/translation preference, and timestamps. Default ordering is newest first. `SubmissionDocument` has a cascading foreign key to `Submission`, a `text`/`visual` category, `FileField`, original filename, content type, size, and timestamp; an index covers `(submission, document_type)`. These are database metadata fields. The `FileField` value is a storage key, not the bytes themselves.

For local storage, Django's default `FileSystemStorage` writes under `MEDIA_ROOT` (normally `backend/media` locally, `/app/media` in the container). `upload_to` routes files under `submissions/texts/` or `submissions/visuals/`. Django storage may alter a colliding filename, so inspect the stored key instead of assuming the original name is the physical path. `SubmissionDocumentRepository` sanitizes uploaded names before creating a row. `SubmissionDocument.create_from_upload()` records the post-sanitization original name, MIME type supplied with the upload, and size. These metadata values should not be treated as content verification.

`RAGEZINE_STORAGE_BACKEND=s3` switches the default file storage to S3 using the `AWS_*` settings in `settings.py`; otherwise local filesystem storage is used. The S3 bucket must remain private. Application downloads still go through a staff-authorized Django endpoint; a storage URL is not an authorization boundary. Django static assets are a separate storage alias and output directory, not submission media.

`DJANGO_DB_ENGINE` defaults to `sqlite` for local Django commands; `postgres`/`postgresql` selects PostgreSQL. `SQLiteHandler` uses `backend/db.sqlite3` and a JSON field for `countries_residence`. `PostgreSQLHandler` uses `POSTGRES_*` connection settings and a PostgreSQL `ArrayField` for that column. The migration `0002_rename_countries_origin_submission_country_origin_and_more.py` calls the selected handler for its field type. Run migrations with the correct engine selected from the start; switching an existing database between engines is a data migration, not a configuration toggle. `SubmissionRepository` and `SubmissionDocumentRepository` are the application-level persistence entry points used by the API and exports; there is no raw SQL query layer in the normal request path.

## 5. HTTP API and authorization

`backend/ragezine_portal/urls.py` mounts Django admin at `/admin/` and the API at `/api/`. `backend/submissions/api/urls.py` defines:

| Endpoint | Method | Access | Effect |
| --- | --- | --- | --- |
| `/api/auth/csrf/` | GET | Public | Ensure `csrftoken` cookie exists |
| `/api/auth/login/` | POST | Public, but credentials must resolve to `is_staff` user | Create Django session |
| `/api/auth/logout/` | POST | Session/CSRF rules apply | Clear session |
| `/api/auth/session/` | GET | Public response | Return `authenticated` flag and user flags when logged in |
| `/api/submissions/` | POST | Public | Validate and store new submission |
| `/api/submissions/` | GET | Staff | List submissions and nested document metadata |
| `/api/submissions/<id>/` | GET, PUT, PATCH, DELETE | Staff | DRF standard detail operations |
| `/api/downloads/documents/<id>/` | GET | Staff | Stream one file as attachment |
| `/api/downloads/submissions/<id>/` | GET | Staff | Build one submission ZIP |
| `/api/downloads/complete/` | GET | Staff | Build all-submissions ZIP |
| `/api/downloads/excel/` | GET | Staff | Build workbook grouped by submission type |

`IsAdminUser` in DRF means authenticated and `is_staff=True`, not necessarily `is_superuser=True`. The viewset sets that permission for all actions except `create`, where `get_permissions()` returns `AllowAny`. The download functions also use `IsAdminUser`. Frontend guards and hidden buttons are convenience only; the backend permissions are the enforcement point. Django admin has its own Django permission checks and also requires staff access.

The login view calls Django `authenticate()` and rejects both invalid credentials and valid non-staff users with the same generic response, then calls `login()` to create a session. Django `SessionMiddleware` and `AuthenticationMiddleware` recover the user on subsequent requests from the session cookie. The browser client uses `withCredentials`, `withXSRFToken`, cookie `csrftoken`, and header `X-CSRFToken`. For unsafe requests with a session, Django/DRF CSRF checks matter; use `/api/auth/csrf/` before login. The code does not configure bearer tokens or JWT. A staff account can be created with `python manage.py createsuperuser`; a non-superuser staff account needs `is_staff=True` (for example through Django admin).

The serializer is the API's input/output contract. It sanitizes strings and validates category, pronouns, language, email, ISO alpha-2 country codes, a minimum-length title/bio/description, at least one uploaded text or visual, and translation consent for non-English submissions. It emits document IDs, metadata, and a `download_url` pointing to the protected API endpoint, never the raw storage URL. The browser has additional input hints and a five-visual limit; these are not equivalent to server-side file count, MIME/content, or byte-size limits. The server currently does not enforce those limits. A public create endpoint is therefore intentionally reachable without a staff session.

## 6. Frontend and common request paths

`App.jsx` routes `/` to `SubmissionPage`, `/login` to `LoginPage`, and `/dashboard` to `DashboardPage`. Unknown client routes go to `/`. `client.js` creates one Axios client with a 10-second timeout and `VITE_API_URL` as its base, falling back to `http://localhost:8000/api/` in local development. `vite.config.js` defines a `/api` development proxy, but the fallback absolute API URL bypasses that proxy unless `VITE_API_URL` is set to a relative path. `src/services/authService.js`, `submissionService.js`, and `downloadService.js` encapsulate requests. `DashboardSubmissionsList.jsx` paginates the fetched list client-side (20 per page), not via server-side pagination.

### A. Public page and submission

1. Browser GET `/`; nginx returns the compiled `index.html` and assets. React renders `SubmissionPage` without authentication.
2. The form builds `FormData`: scalar metadata, repeated `countries_residence` fields, newline-joined `socials`, booleans as strings, repeated `text_files`, and repeated `visuals`. Browser validation runs first. A direct API caller can bypass it.
3. Axios POSTs multipart data to `/api/submissions/`; nginx proxies it to Django. DRF dispatches the router's `create` action; `AllowAny` permits anonymous requests.
4. `SubmissionSerializer.is_valid()` normalizes and validates the metadata and checks at least one uploaded file. On invalid input DRF returns 400 with field errors, and no submission row is created.
5. Inside `transaction.atomic()`, `SubmissionRepository.create()` inserts a row, then `SubmissionDocumentRepository` creates each file-backed document row. Django's file storage writes the bytes. A database rollback does not automatically roll back already-written files.
6. After the transaction commits, `send_submission_emails()` builds applicant and configured internal messages and attaches stored file contents. Exceptions are logged, but the endpoint still returns 201; a successful submission is not proof of successful email delivery. In debug mode, email defaults to console output. In non-debug mode, it defaults to SMTP unless explicitly overridden.
7. The response serializer returns the submission plus nested document metadata; the browser shows success. If the frontend times out at 10 seconds but the backend later commits, retrying can create a duplicate. Check the database before manually resubmitting after an ambiguous timeout.

### B. Staff login and dashboard

1. Login page GETs `/api/auth/csrf/` and `/api/auth/session/`. A staff session is redirected to `/dashboard`.
2. POST `/api/auth/login/` sends username and password with the CSRF header/cookie. Django authenticates and sets a session cookie only for staff.
3. Dashboard checks `/api/auth/session/` and redirects non-staff users to login. It GETs `/api/submissions/`; DRF again independently checks `IsAdminUser` and serializes rows/documents.
4. The dashboard offers complete ZIP, Excel, per-submission ZIP, and individual file links. Export services request blobs, parse `Content-Disposition`, and create temporary browser object URLs for download. Individual document anchors use the API's `download_url`, carrying the browser's session cookie.
5. POST `/api/auth/logout/` clears the server session. A previously loaded UI might remain visible until navigation, but protected server calls should fail without a valid staff session.

### C. Protected file and export

For an individual file, `document_download` first authorizes staff, looks up `SubmissionDocument`, checks that storage still contains the key, and returns `FileResponse` with `Content-Disposition: attachment` and `application/octet-stream`. A missing row or missing backing object returns 404. `/media/...` is intentionally unavailable even if a database row contains that storage key. The Django admin's custom file widget also links through the protected API route.

For ZIP endpoints, `downloads.py` fetches submissions/documents, builds a ZIP in a `BytesIO` buffer, and reads file bytes from storage. The complete export groups entries by submission type and artist name and includes submission details. The Excel endpoint uses `openpyxl` and creates sheets by submission type. These exports are generated in process memory, not streamed incrementally, so large volumes can raise worker memory/timeout pressure. If two artists have the same name within a category, inspect ZIP paths for possible collisions/duplicate entries; the current path uses category and sanitized artist name rather than a unique submission ID.

### D. Admin

GET `/admin/` is proxied to Django; Django renders admin HTML and relies on `/static/admin/...` assets produced by `collectstatic`. Admin login and model permissions are Django-native, separate from the custom React login view. `backend/submissions/admin.py` registers submissions/documents and supplies protected document links. Admin's CSRF/session behavior still depends on the request origin, cookie, and trusted-host configuration.

## 7. Debugging by hand

Start at the outside and move inward. Keep a specific failing URL, HTTP method, status, response body, request ID/time, and submission/document ID. Browser Developer Tools > Network shows the actual request URL, cookies, `X-CSRFToken`, status, and response. Do not paste a session cookie or applicant payload into a shared log.

### Compose checks (PowerShell, repository root)

```powershell
docker compose config --quiet
docker compose ps
docker compose logs --tail=100 nginx
docker compose logs --tail=100 backend
docker compose logs --tail=100 db
docker compose exec backend python manage.py check
docker compose exec backend python manage.py showmigrations submissions
docker compose exec backend python manage.py shell -c "from django.db import connection; print(connection.vendor, connection.settings_dict['NAME'])"
curl.exe -i http://localhost:8080/api/auth/csrf/
curl.exe -I http://localhost:8080/static/admin/css/base.css
curl.exe -i http://localhost:8080/media/example
```

Expected: Compose services healthy; CSRF endpoint returns 200 and a `csrftoken` cookie; admin CSS returns 200 after `collectstatic`; `/media/example` returns 404. The database name from the shell command is not a password. If the host port differs, use `RAGEZINE_HTTP_PORT`. To inspect rows without changing data, use `docker compose exec db psql -U <POSTGRES_USER> -d <POSTGRES_DB>` with the values from local `.env`, then for example `SELECT id, artist_name, title, created_at FROM submissions_submission ORDER BY id DESC LIMIT 10;` and `SELECT id, submission_id, file FROM submissions_submissiondocument ORDER BY id DESC LIMIT 10;`. Substitute credentials locally; do not put the password on a command line.

For a local non-Compose setup, start Django from `backend/` with the project's Python environment and `python manage.py runserver`, and start the frontend from `frontend/ragezine-portal/` with `npm run dev`. The default browser API target is `http://localhost:8000/api/`. Check which `.env` supplied Django settings and which DB engine is active. `python manage.py test submissions` exercises backend tests; `npm run lint` and `npm run build` check frontend code/build. SQLite is the local default unless explicitly changed.

### Symptom-to-layer map

| Symptom | Inspect first | Likely explanation |
| --- | --- | --- |
| nginx 502/503 or frontend loads but API fails | `docker compose ps`, backend and db logs | Backend did not start, migration failed, health check failed, or DB unavailable |
| Browser 404 on `/dashboard` reload | nginx `location /` | SPA fallback missing or request is reaching Django directly |
| 400 `DisallowedHost` | `DJANGO_ALLOWED_HOSTS`, request `Host` | Public hostname not allowed by Django |
| 403 on staff API | `/api/auth/session/`, session cookie, `is_staff` | No valid session, not staff, or CSRF failure on unsafe request |
| 403 CSRF on login/admin/POST | `csrftoken`, `X-CSRFToken`, browser origin, Django CSRF settings | Missing/stale token, wrong origin or proxy scheme |
| Public POST 400 | JSON error body from serializer | Required field, invalid code/choice, no files, translation rule |
| POST 201 but no email | backend logs and email settings | Email runs after commit and errors are logged without changing 201 |
| Missing document (404) | document row's `file` key, storage object, media volume | Row absent or backing bytes missing; `/media/*` 404 itself is expected |
| Missing admin CSS | `collectstatic` startup log, `static_data` mount | Static assets did not populate or nginx mount/path wrong |
| Export stalls or 500 | backend logs, worker memory, file count | In-memory ZIP/workbook generation or missing storage object |
| Local works, deployed frontend calls localhost:8000 | built JS, `VITE_API_URL`, Docker build | Wrong build-time API base URL; rebuild frontend image |

Useful isolation: `curl.exe -i` establishes edge status; backend logs establish Django status; a read-only SQL query establishes row existence; storage inspection establishes byte existence. If a browser request fails but `curl` succeeds, compare URL, origin, cookies, and CSRF headers. If a write times out, check for a newly created row before retrying. When inspecting `FileField`, use the stored key and configured storage API rather than constructing an unauthenticated `/media/` URL.

## 8. Known boundaries and operational risks

- The current Compose endpoint is HTTP. The code has development defaults for secret key, debug mode, and allowed hosts. Production needs explicit secrets, host/origin/TLS/cookie/proxy settings and a deployment-specific ingress decision.
- Uploaded media is protected from direct nginx/Django URL serving, but file content/type/size/count are not comprehensively enforced server-side. The frontend's TIFF, word-count, and visual-count rules are mainly UX guidance.
- Filesystem/S3 writes and relational transactions are not one atomic resource; partial failures can leave orphan files. Database and media backup/restore must be coordinated.
- Email is synchronous and attachments are read into the request flow. Email errors are logged while the submission still succeeds. The frontend's 10-second Axios timeout can be shorter than upload/email/export work.
- ZIP and Excel are memory-backed; growth in submissions/files can outpace the two Gunicorn workers' capacity. Complete export paths can collide for same-name artists.
- There is no dedicated login rate limiting or public-submission abuse control visible in these request paths. `client_max_body_size 0` in nginx removes its upload-size cap by design.
- The Compose image/configuration and individual container checks have been exercised, but a full live three-service browser smoke test was not confirmed in the previous work session. Treat production deployment as unverified until that test is run.

## 9. Next steps

1. Perform a full Compose smoke test on a non-production instance: anonymous submission with a small file, staff login, dashboard list, protected file download, all export types, admin static files, and expected anonymous 403/404 cases. Verify the row and stored bytes agree.
2. Define the production edge: TLS termination, public hostname, `DJANGO_ALLOWED_HOSTS`, trusted origins, forwarded scheme handling, secure session/CSRF cookies, secret management, and a non-debug setting. Test login and uploads through the *actual* public URL.
3. Establish and rehearse paired PostgreSQL/media backups and restores. Record restore-time verification queries and a protected file download check.
4. Add observable failure signals: structured backend logs, email-delivery alerts, health monitoring, and a way to correlate an HTTP request with a submission ID without logging private content.
5. Decide whether to enforce server-side upload size/count/content rules and abuse/rate limits. The frontend's current hints are not a security boundary; choose explicit limits only when product requirements are settled.
6. As volume grows, move email and large exports to background jobs or streaming/object-storage delivery; add uniqueness to ZIP folder names and integration tests for the full request paths.
