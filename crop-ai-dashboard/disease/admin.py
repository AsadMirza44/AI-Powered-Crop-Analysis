from django.contrib import admin

from .models import DiseasePrediction


@admin.register(DiseasePrediction)
class DiseasePredictionAdmin(admin.ModelAdmin):
    list_display = ("crop", "predicted_label", "confidence", "created_at")
    search_fields = ("crop", "predicted_label")
    list_filter = ("crop", "predicted_label")
