from django.core.files.base import ContentFile
from django.contrib import messages
from django.shortcuts import render

from dashboard.services import annotate_disease_records
from smart_crop_ai.demo_data import DISEASE_DEMO_SAMPLES
from smart_crop_ai.monitoring import disease_alert_severity, severity_label

from .forms import DiseaseUploadForm
from .models import DiseasePrediction
from .services import get_disease_service


def disease_analysis(request):
    form = DiseaseUploadForm(request.POST or None, request.FILES or None)
    result = None

    if request.method == "POST" and form.is_valid():
        try:
            service = get_disease_service()
            crop = form.cleaned_data["crop"]
            demo_sample = form.cleaned_data.get("demo_sample")
            uploaded_image = form.cleaned_data.get("image")

            if demo_sample:
                sample = DISEASE_DEMO_SAMPLES[demo_sample]
                raw_bytes = sample["file_path"].read_bytes()
                uploaded_image = ContentFile(raw_bytes, name=sample["upload_name"])
                crop = sample["crop"]
            else:
                raw_bytes = uploaded_image.read()

            prediction = service.predict(raw_bytes, crop=crop, source_name=uploaded_image.name)
            record = DiseasePrediction.objects.create(
                crop=crop,
                image=uploaded_image,
                overlay_image=prediction.overlay_path,
                predicted_label=prediction.predicted_label,
                confidence=prediction.confidence,
                summary=prediction.summary,
                probabilities=prediction.probabilities,
                recommendations=prediction.recommendations,
                plant_coverage_pct=prediction.coverage_pct,
                hotspot_pct=prediction.hotspot_pct,
            )
            record.alert_severity = disease_alert_severity(record.predicted_label, record.confidence, record.hotspot_pct)
            record.alert_label = severity_label(record.alert_severity)
            result = record
            messages.success(request, "Disease analysis completed and saved to history.")
        except (FileNotFoundError, ValueError) as exc:
            messages.error(request, str(exc))

    context = {
        "form": form,
        "result": result,
        "recent_predictions": annotate_disease_records(DiseasePrediction.objects.order_by("-created_at")[:5]),
        "demo_samples": [{"key": key, **value} for key, value in DISEASE_DEMO_SAMPLES.items()],
    }
    return render(request, "disease/analyze.html", context)
