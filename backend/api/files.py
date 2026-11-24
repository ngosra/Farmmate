from pathlib import Path

from rest_framework import serializers

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
BLOCKED_TYPES = {"text/html", "application/javascript", "image/svg+xml", "text/xml"}


def validate_upload(upload):
    if upload in (None, ""):
        return upload
    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise serializers.ValidationError("Upload a PDF, JPG, PNG, or WEBP file.")
    if getattr(upload, "size", 0) and upload.size > MAX_UPLOAD_BYTES:
        raise serializers.ValidationError("File is larger than 10 MB.")
    content_type = getattr(upload, "content_type", "") or ""
    if content_type in BLOCKED_TYPES:
        raise serializers.ValidationError("This file type is not allowed.")
    return upload
