from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .auth import csrf, login_view, logout_view, session_view
from .downloads import complete_download, excel_download, submission_download
from .submission_views import SubmissionViewSet


router = DefaultRouter()
router.register(r"submissions", SubmissionViewSet)

urlpatterns = [
    path("auth/csrf/", csrf, name="auth-csrf"),
    path("auth/login/", login_view, name="auth-login"),
    path("auth/logout/", logout_view, name="auth-logout"),
    path("auth/session/", session_view, name="auth-session"),
    path("downloads/complete/", complete_download, name="downloads-complete"),
    path("downloads/excel/", excel_download, name="downloads-excel"),
    path("downloads/submissions/<int:submission_id>/", submission_download, name="downloads-submission"),
    path("", include(router.urls)),
]
