from django.db import models


class DiseasePrediction(models.Model):
    crop = models.CharField(max_length=32)
    image = models.ImageField(upload_to="uploads/originals/")
    overlay_image = models.ImageField(upload_to="uploads/overlays/", blank=True)
    predicted_label = models.CharField(max_length=64)
    confidence = models.FloatField()
    summary = models.TextField()
    probabilities = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    plant_coverage_pct = models.FloatField(default=0.0)
    hotspot_pct = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.crop} - {self.predicted_label} ({self.created_at:%Y-%m-%d %H:%M})"
