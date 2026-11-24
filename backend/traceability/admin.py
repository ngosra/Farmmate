from django.contrib import admin

from traceability.models import Batch, BatchInput, Movement

admin.site.register(Batch)
admin.site.register(BatchInput)
admin.site.register(Movement)
