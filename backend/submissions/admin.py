from django.contrib import admin

# Register your models here.
from .models import Submission, SubmissionVisual

admin.site.register(Submission)
admin.site.register(SubmissionVisual)