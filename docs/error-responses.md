# Error responses

The portal has two error surfaces: JSON for `/api/` requests and pages for visitors or staff.

| Status | API response | Page response |
| --- | --- | --- |
| 404 | `{"detail":"We could not find that page.","code":"not_found"}` | A page with a route back to the portal or Django admin. |
| 500 | `{"detail":"Please try again later.","code":"server_error"}` | A page that hides internal error details. |
| 413 | nginx returns JSON with `code: "upload_too_large"`. | Not used for normal pages. |
| 429 | nginx returns JSON with `code: "rate_limited"` and `Retry-After`. | Not used for normal pages. |

`PortalErrorMiddleware` handles Django 404 and 500 responses. In local debug mode, Django keeps its technical 500 page. It does not replace validation errors, so the form still receives field errors. React shows a page for unknown portal routes and a recovery page for render failures. nginx handles upload and rate limits before a request reaches Django.

The frontend is a single-page app. nginx currently serves its entry file with HTTP 200 for an unknown frontend path, then React displays the missing-page view. API and Django page 404 responses keep HTTP 404.

If Django or nginx is unavailable, this middleware cannot run. Check the reverse proxy and service logs for gateway failures.
