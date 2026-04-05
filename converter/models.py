import uuid
from django.conf import settings
from django.db import models


def upload_path(instance, filename):
    return f"uploads/{instance.user.id}/{uuid.uuid4().hex}/{filename}"


def output_path(instance, filename):
    return f"outputs/{instance.user.id}/{uuid.uuid4().hex}/{filename}"


class Conversion(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversions"
    )
    original_filename = models.CharField(max_length=255)
    docx_file = models.FileField(upload_to=upload_path)
    html_file = models.FileField(upload_to=output_path, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    use_transpect = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.status})"
