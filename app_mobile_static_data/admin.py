# app_mobile_static_data/admin.py
from django.contrib import admin
from django.utils.html import format_html
from app_mobile_static_data.models import (
    ProfessionalListModel,
    UserManualModel,
    UsefulLinksModel,
    ReportsLinksModel,
    AboutUsModel,
)





@admin.register(ProfessionalListModel)
class ProfessionalListAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "name",
        "title",
        "organization",
        "phone",
        "email_summary",
        "created_at",
        "updated_at",
        "profile_image_preview",
    )
    search_fields = ("key", "name", "title", "organization", "phone", "email")
    list_filter = ("organization",)
    readonly_fields = ("created_at", "updated_at", "profile_image_preview")
    ordering = ("name",)
    fieldsets = (
        (None, {
            "fields": ("key", "name", "title", "organization", "education", "researchInterest")
        }),
        ("Contacts", {
            "fields": ("email", "phone", "alternatePhone", "alternatePhone1")
        }),
        ("Profile image", {
            "fields": ("profileImage", "profile_image_preview")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )

    def email_summary(self, obj):
        """Display a short comma-separated summary of email JSONField."""
        try:
            if obj.email:
                # If it's list-like, join first few
                if isinstance(obj.email, (list, tuple)):
                    return ", ".join(obj.email[:3]) + ("…" if len(obj.email) > 3 else "")
                return str(obj.email)
        except Exception:
            pass
        return ""
    email_summary.short_description = "Emails"

    def profile_image_preview(self, obj):
        """Small image preview (admin only)."""
        if obj.profileImage:
            return format_html(
                '<img src="{}" style="max-height:80px; max-width:80px; object-fit:contain; border-radius:4px;" />',
                obj.profileImage.url
            )
        return "-"
    profile_image_preview.short_description = "Image"





@admin.register(UserManualModel)
class UserManualAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "path_preview")
    search_fields = ("title",)
    ordering = ("level",)
    readonly_fields = ("path_preview",)

    fieldsets = (
        (None, {
            "fields": ("title", "level", "path", "path_preview")
        }),
    )

    def path_preview(self, obj):
        """Small image preview in admin."""
        if obj.path:
            return format_html(
                '<img src="{}" style="max-height:80px; max-width:80px; object-fit:contain; border-radius:4px;" />',
                obj.path.url
            )
        return "-"
    path_preview.short_description = "Image"
    
    

@admin.register(UsefulLinksModel)
class UsefulLinksAdmin(admin.ModelAdmin):
    list_display = ("name", "link")
    search_fields = ("name", "link")
    ordering = ("name",)
    
    
@admin.register(ReportsLinksModel)
class ReportsLinksAdmin(admin.ModelAdmin):
    list_display = ("year", "link")
    search_fields = ("year", "link")
    ordering = ("year",)
    

@admin.register(AboutUsModel)
class AboutUsAdmin(admin.ModelAdmin):
    list_display = ("mission_preview", "vision_preview", "professionals_list")
    readonly_fields = ("professionals_list",)

    def mission_preview(self, obj):
        return obj.mission[:50] + "..." if obj.mission else "-"
    mission_preview.short_description = "Mission"

    def vision_preview(self, obj):
        return obj.vision[:50] + "..." if obj.vision else "-"
    vision_preview.short_description = "Vision"

    def professionals_list(self, obj):
        # List all professionals as HTML list
        professionals = ProfessionalListModel.objects.all()
        if not professionals:
            return "-"
        html = "<ul>"
        for p in professionals:
            html += f"<li>{p.name} ({p.key}) - {p.title}</li>"
        html += "</ul>"
        return format_html(html)
    professionals_list.short_description = "Professionals"
