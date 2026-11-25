from django.contrib import admin

from farms.models import Farm, FarmDocument, Field, LandUse

admin.site.register(Farm)
admin.site.register(Field)
admin.site.register(LandUse)
admin.site.register(FarmDocument)
