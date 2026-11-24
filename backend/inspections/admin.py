from django.contrib import admin

from inspections.models import Inspection, InspectionCheck

admin.site.register(Inspection)
admin.site.register(InspectionCheck)
