from django.contrib import admin

from inventory.models import InputApproval, InputProduct, StockMovement, Supplier

admin.site.register(Supplier)
admin.site.register(InputProduct)
admin.site.register(InputApproval)
admin.site.register(StockMovement)
