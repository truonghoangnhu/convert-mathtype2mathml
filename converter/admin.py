from django.contrib import admin
from .models import Conversion


@admin.register(Conversion)
class ConversionAdmin(admin.ModelAdmin):
    list_display = ["original_filename", "user", "status", "created_at", "completed_at"]
    list_filter = ["status", "use_transpect"]
    search_fields = ["original_filename", "user__username"]
    readonly_fields = ["id", "created_at", "completed_at"]
