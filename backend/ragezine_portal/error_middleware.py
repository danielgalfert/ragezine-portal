from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin


ERRORS = {
    404: ("Page not found", "We could not find that page.", "not_found"),
    500: ("Something went wrong", "Please try again later.", "server_error"),
}


class PortalErrorMiddleware(MiddlewareMixin):
    """Give API and Django pages safe, consistent 404 and 500 responses."""

    def process_response(self, request, response):
        if response.status_code not in ERRORS:
            return response
        if response.status_code == 500 and settings.DEBUG:
            return response

        title, detail, code = ERRORS[response.status_code]
        if request.path.startswith("/api/"):
            replacement = JsonResponse(
                {"detail": detail, "code": code}, status=response.status_code
            )
        else:
            admin_page = request.path.startswith("/admin/")
            replacement = render(
                request,
                "errors/error.html",
                {"status_code": response.status_code, "title": title,
                 "detail": detail,
                 "destination": "/admin/" if admin_page else "/",
                 "link_label": "Return to admin" if admin_page else "Return to the portal"},
                status=response.status_code,
            )
        replacement["Cache-Control"] = "no-store"
        return replacement
