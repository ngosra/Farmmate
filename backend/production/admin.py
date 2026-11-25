from django.contrib import admin

from production.models import Activity, Harvest, StorageRecord

admin.site.register(Activity)
admin.site.register(Harvest)
admin.site.register(StorageRecord)
