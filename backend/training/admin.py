from django.contrib import admin

from training.models import Attendance, TrainingMaterial, TrainingSession

admin.site.register(TrainingSession)
admin.site.register(TrainingMaterial)
admin.site.register(Attendance)
