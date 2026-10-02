# Rate limiting

The API applies these defaults:

| Endpoint | Key | Default limit |
| --- | --- | --- |
| `POST /api/submissions/` | Client IP | 3 per hour |
| `POST /api/auth/login/` | Client IP | 10 per minute |
| `POST /api/auth/login/` | Normalized username | 5 per minute |
| Complete ZIP, Excel, and submission ZIP downloads | Staff account | 10 per hour across these exports |

Rejected API requests return HTTP 429 with a `Retry-After` header. The
username cache key is hashed so the cache does not retain usernames in keys.
These application limits are intended to control ordinary overuse. nginx also
limits bursts of dashboard login, Django admin login, and submission requests
and returns HTTP 429 before forwarding them to Django.

Set `RAGEZINE_SUBMISSION_RATE`, `RAGEZINE_LOGIN_IP_RATE`,
`RAGEZINE_LOGIN_USERNAME_RATE`, and `RAGEZINE_EXPORT_RATE` in the root
`.env` to change the limits. Rates use the Django REST Framework format,
such as `5/minute` or `3/hour`. Test any change against real submission
traffic, especially users sharing a public IP address.

Docker Compose starts an internal Redis service and sets
`RAGEZINE_REDIS_URL=redis://redis:6379/0` for Django. Production deployments
outside Compose must provide a shared Redis URL. Django refuses to start with
`DJANGO_DEBUG=0` and no Redis URL, because a per-process cache would make the
limit inconsistent across Gunicorn workers. Development uses a local cache.
Redis is only a cache: no submission data is stored there.

The Compose nginx proxy overwrites `X-Forwarded-For` with its observed client
address. Django assumes this single trusted proxy (`RAGEZINE_PROXY_COUNT=1`).
If another proxy or load balancer is placed in front of nginx, configure
nginx's real IP handling to trust only that proxy and verify the observed
client address before launch. Do not accept a client-supplied
`X-Forwarded-For` value as the rate-limit identity.

The nginx limits are per nginx instance and the built-in Django REST Framework
cache throttles can admit a few concurrent requests beyond their nominal
limit. Use a centralized edge limit if the site later runs multiple public
nginx instances or requires a strict global cap.
