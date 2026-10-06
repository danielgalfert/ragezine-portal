# Production environment

The project-root `.env` is read by Docker Compose and passed to Django. Copy
`.env.example` to `.env` on the server, fill in the required values, and keep the
file outside Git. Restrict access to the deployment account. Do not put real
credentials in `.env.example`.

## Variables

| Variable | Purpose |
| --- | --- |
| `DJANGO_DEBUG` | Set to `0` in production. |
| `DJANGO_SECRET_KEY` | Unique, long random Django signing key. Keep it secret. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated public hostnames accepted by Django. |
| `DJANGO_DB_ENGINE` | `postgres` for the Compose deployment. |
| `POSTGRES_DB` | PostgreSQL database name. |
| `POSTGRES_USER` | PostgreSQL application user. |
| `POSTGRES_PASSWORD` | Strong password for that user; never reuse the superuser password. |
| `POSTGRES_HOST` | `db` inside Compose. |
| `POSTGRES_PORT` | PostgreSQL port, usually `5432`. |
| `RAGEZINE_HTTP_PORT` | Host port for nginx's HTTP listener. Configure HTTPS at the public edge. |
| `RAGEZINE_STORAGE_BACKEND` | `local` for the persistent Compose media volume or `s3` for private object storage. |
| `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_QUERYSTRING_AUTH` | Needed only when `RAGEZINE_STORAGE_BACKEND=s3`. Use a private bucket and least-privilege credentials. |
| `DJANGO_EMAIL_BACKEND` | SMTP backend for real receipt emails. |
| `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`, `DJANGO_EMAIL_USE_TLS`, `DJANGO_EMAIL_USE_SSL` | Mail-provider connection and credentials. Use the encryption mode and port specified by the provider. |
| `SUBMISSION_EMAIL_FROM` | Verified sender address for receipt emails. |
| `SUBMISSION_EMAIL_SUBJECT`, `SUBMISSION_EMAIL_BODY` | Applicant receipt content. |
| `SUBMISSION_NOTIFICATION_TO` | Optional comma-separated staff notification addresses. |

Set `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, and the mail credentials to real
server-specific values before starting the deployment. Do not use the example
domain or an unverified sender address. Keep the production `.env` out of
backups or archives that are accessible to the public.

## Create the first superuser

After the first `docker compose up -d` has applied migrations, create the superuser
account once with `docker compose exec backend python manage.py createsuperuser`.
The interactive command prompts for a username, email, and password, so the
password does not need to remain in the server `.env`.

For a non-interactive, one-time setup, Django also accepts
`DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and
`DJANGO_SUPERUSER_PASSWORD` from the environment. Temporarily add them to the
server `.env`, run
`docker compose run --rm --no-deps backend python manage.py createsuperuser --noinput`,
and remove them from `.env` immediately afterward. The account and hashed
password remain in PostgreSQL. Container startup deliberately does not run
this command.

## Existing Git history

Ignoring a file does not remove earlier commits. The repository history has
contained `.env` files and uploaded submission media. Before sharing or
deploying the repository, review who had access, rotate any real credentials
that appeared in those files, and coordinate removal of sensitive history if
needed. Do not copy historical submissions into a production deployment.
