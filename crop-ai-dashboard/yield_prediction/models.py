from django.db import models


class YieldPrediction(models.Model):
    crop = models.CharField(max_length=32)
    district = models.CharField(max_length=64)
    province = models.CharField(max_length=64)
    season = models.CharField(max_length=16)
    year = models.PositiveIntegerField()
    rainfall_mm = models.FloatField()
    avg_temp_c = models.FloatField()
    soil_ph = models.FloatField()
    organic_carbon_pct = models.FloatField()
    nitrogen_ppm = models.FloatField()
    phosphorus_ppm = models.FloatField()
    potassium_ppm = models.FloatField()
    cultivated_area_hectares = models.FloatField()
    predicted_yield_t_ha = models.FloatField()
    historical_average_t_ha = models.FloatField()
    delta_vs_average_pct = models.FloatField()
    summary = models.TextField()
    top_factors = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    historical_series = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.crop} @ {self.district} ({self.predicted_yield_t_ha:.2f} t/ha)"
