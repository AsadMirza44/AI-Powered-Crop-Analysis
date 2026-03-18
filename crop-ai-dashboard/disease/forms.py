from django import forms

from smart_crop_ai.demo_data import DISEASE_DEMO_SAMPLES
from smart_crop_ai.reference_data import CROP_PROFILES


class DiseaseUploadForm(forms.Form):
    crop = forms.ChoiceField(
        choices=[
            (code, profile["label"])
            for code, profile in CROP_PROFILES.items()
            if profile["supports_disease"]
        ],
        widget=forms.Select(attrs={"class": "field-select"}),
    )
    demo_sample = forms.ChoiceField(
        required=False,
        choices=[(key, sample["title"]) for key, sample in DISEASE_DEMO_SAMPLES.items()],
        widget=forms.HiddenInput(),
    )
    image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "field-upload", "accept": "image/*"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("image") and not cleaned_data.get("demo_sample"):
            raise forms.ValidationError("Upload a leaf image or launch one of the demo samples.")
        return cleaned_data
