from rest_framework.permissions import IsAdminUser


class CanDeleteSubmission(IsAdminUser):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.has_perm(
            "submissions.delete_submission"
        )


class CanExportAllSubmissions(IsAdminUser):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.has_perm(
            "submissions.export_all_submissions"
        )
