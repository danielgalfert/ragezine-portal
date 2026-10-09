# Ragezine Portal

A public submission form and a staff dashboard for reviewing and exporting submissions. The browser app is React; the API and admin are Django.

## Container layout

`docker-compose.yml` runs three services:

| Service | Job | Persistent state |
| --- | --- | --- |
| `db` | PostgreSQL stores submission, document, user, and session records. | `postgres_data` |
| `backend` | Django serves `/api/` and `/admin/`, sends email, and authorizes file downloads. | Uploaded files in `media_data`; generated admin assets in `static_data` |
| `nginx` | Serves the built React files and `/static/`, and proxies `/api/` and `/admin/` to Django. | None of its own |

The nginx image uses a **build stage** with Node to run `npm ci` and `npm run build`. It then copies the static output into a small nginx runtime image. There is no React or Node server running in production. nginx gives the browser one origin for the site, API, and admin, which also simplifies session cookies and CSRF handling. The previous Compose file used a separate frontend build service; the current image folds that step into the nginx build.

The frontend does not inherently require a container. Static hosting plus a suitable reverse proxy could serve the same files. In this repository, the nginx container makes the site and proxy part of one reproducible Compose stack.

Uploaded files are **not** served from `/media/`. Django checks staff access before returning a document or export. Keep `postgres_data` and `media_data` together in backups; database rows can refer to files in that separate volume. `static_data` can be regenerated with `collectstatic`.

## Local Compose run

Copy `.env.example` to `.env`, then set a unique `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD`. The example uses production settings; set `DJANGO_DEBUG=1` for local development. Start the stack with `docker compose up --build`; the site is at `http://localhost:8080` unless `RAGEZINE_HTTP_PORT` is changed. `docker compose down` stops it without removing volumes.

The backend can also run locally with SQLite by setting `DJANGO_DB_ENGINE=sqlite`; Compose explicitly selects PostgreSQL. For frontend development, run `npm run dev` in `frontend/ragezine-portal` and the Django development server in `backend`.

## Submission upload limits

The root `.env` sets `RAGEZINE_MAX_FILE_MB=5120` (5 GiB) for each file and
`RAGEZINE_MAX_TOTAL_FILES_MB=10240` (10 GiB) for all files in one submission.
These values are measured in MiB (1,048,576 bytes). Django
rejects oversized submissions with HTTP 400 before saving a record or files.
The Compose nginx proxy also caps the entire request body with
`RAGEZINE_NGINX_MAX_BODY_SIZE=11g` and returns HTTP 413 when that cap is
exceeded. Keep the nginx cap above the total file cap to allow for multipart
form fields. Add these entries from `.env.example` to any existing deployment
`.env`, then recreate the backend and nginx containers to apply changes.
The browser does not time out submission uploads. The nginx proxy and Gunicorn
wait up to `RAGEZINE_NGINX_PROXY_READ_TIMEOUT=14400s` and
`RAGEZINE_GUNICORN_TIMEOUT=14400` while Django processes a request. The
proxy and Django may each need temporary disk space for the request, in
addition to the final file storage. Provision enough space for simultaneous
uploads and generated ZIP downloads. Large archives are built on temporary
disk and sent as streamed downloads rather than held in memory.

Submission receipts do not attach uploaded files, including videos.

## Staff accounts

With the Compose stack running, create a dashboard account from the project root:

```sh
docker compose exec backend python manage.py create_staff_user editor --email editor@example.com
```

The command prompts twice for a password. It creates a staff account without superuser privileges. Omit `--email` if it is not needed. For full Django admin privileges, use `docker compose exec backend python manage.py createsuperuser` instead. The same `create_staff_user` command also works directly from `backend` when running Django locally.

On the Lightsail test deployment, staff sign in at
`https://admin.submissions.danielgalfert.com/login`. The public submission form
remains at `https://submissions.danielgalfert.com/`.

## Code map

- `frontend/ragezine-portal/src/App.jsx`: browser routes for the form, login, and dashboard.
- `frontend/ragezine-portal/src/api/client.js` and `src/services/`: browser calls to Django.
- `backend/submissions/api/`: submission, authentication, and download endpoints.
- `backend/submissions/serializers.py`: submission validation and response shape.
- `backend/submissions/models.py` and `repositories.py`: stored records and ORM access.
- `backend/ragezine_portal/settings.py`: database, file storage, email, and Django configuration.

## Checks

Run `python manage.py test submissions` from `backend` with the intended database engine selected. Run `npm run lint` and `npm run build` from `frontend/ragezine-portal`. `docker compose --env-file .env.example config --quiet` validates the Compose configuration without starting services.
