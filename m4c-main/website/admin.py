from django.contrib import admin

from .models import MemberProfile, VerificationCode, VolunteerRegistration


@admin.register(VolunteerRegistration)
class VolunteerRegistrationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "county", "interest", "phone_number", "email", "created_at")
    list_filter = ("county", "interest", "created_at")
    search_fields = ("full_name", "phone_number", "email", "county")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


admin.site.register(MemberProfile)
admin.site.register(VerificationCode)
