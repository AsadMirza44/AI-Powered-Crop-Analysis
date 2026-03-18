from django.contrib import admin

from .models import YieldPrediction


@admin.register(YieldPrediction)
class YieldPredictionAdmin(admin.ModelAdmin):
    list_display = ("crop", "district", "predicted_yield_t_ha", "delta_vs_average_pct", "created_at")
    search_fields = ("crop", "district")
    list_filter = ("crop", "district", "province")
