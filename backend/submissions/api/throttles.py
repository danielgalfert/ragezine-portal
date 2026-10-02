"""Rate limits for endpoints that create work or handle credentials."""

import hashlib

from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle

from submissions.utils import sanitize_single_line


class ClientIPThrottle(SimpleRateThrottle):
    """Apply a scope to every client IP, including logged-in users."""

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class SubmissionCreateThrottle(ClientIPThrottle):
    scope = "submission_create"


class LoginIPThrottle(ClientIPThrottle):
    scope = "login_ip"


class LoginUsernameThrottle(SimpleRateThrottle):
    scope = "login_username"

    def get_cache_key(self, request, view):
        username = sanitize_single_line(request.data.get("username")).casefold()
        if not username:
            return None
        digest = hashlib.sha256(username.encode("utf-8")).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}


class StaffExportThrottle(UserRateThrottle):
    scope = "staff_export"
