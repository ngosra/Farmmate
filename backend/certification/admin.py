from django.contrib import admin

from certification.models import (
    Certification,
    ComplianceItem,
    CorrectiveAction,
    Evidence,
    Reminder,
    Requirement,
    Standard,
)

admin.site.register(Standard)
admin.site.register(Requirement)
admin.site.register(Certification)
admin.site.register(ComplianceItem)
admin.site.register(Evidence)
admin.site.register(CorrectiveAction)
admin.site.register(Reminder)
