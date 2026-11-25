from django.conf import settings
from django.db import models

from organizations.models import Organization
from records import UUIDModel


class AssistantQuery(UUIDModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="assistant_queries"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assistant_queries"
    )
    question = models.TextField()
    answer = models.TextField()
    intents = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.question[:80]
