from django.contrib import admin

from organizations.models import Farmer, Membership, Organization


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ("user",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (MembershipInline,)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("user__email", "user__farmer_id", "organization__name")
    autocomplete_fields = ("user", "organization")


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "farmer_id", "organization", "user")
    search_fields = ("display_name", "farmer_id", "user__email")
    autocomplete_fields = ("organization", "user")
