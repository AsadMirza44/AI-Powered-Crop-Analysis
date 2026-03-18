from django import forms

from smart_crop_ai.reference_data import CROP_PROFILES, DISTRICT_PROFILES


class YieldForecastForm(forms.Form):
    crop = forms.ChoiceField(
        choices=[(code, profile["label"]) for code, profile in CROP_PROFILES.items() if profile["supports_yield"]],
        widget=forms.Select(attrs={"class": "field-select"}),
    )
    district = forms.ChoiceField(
        choices=sorted((name, f"{name}, {profile['province']}") for name, profile in DISTRICT_PROFILES.items()),
        widget=forms.Select(attrs={"class": "field-select"}),
    )
    season = forms.ChoiceField(
        choices=[("Kharif", "Kharif"), ("Rabi", "Rabi")],
        widget=forms.Select(attrs={"class": "field-select"}),
    )
    year = forms.IntegerField(min_value=2020, max_value=2035, widget=forms.NumberInput(attrs={"class": "field-input"}))
    rainfall_mm = forms.FloatField(min_value=0, widget=forms.NumberInput(attrs={"class": "field-input", "step": "0.1"}))
    avg_temp_c = forms.FloatField(widget=forms.NumberInput(attrs={"class": "field-input", "step": "0.1"}))
    soil_ph = forms.FloatField(widget=forms.NumberInput(attrs={"class": "field-input", "step": "0.1"}))
    organic_carbon_pct = forms.FloatField(
        widget=forms.NumberInput(attrs={"class": "field-input", "step": "0.01"})
    )
    nitrogen_ppm = forms.FloatField(widget=forms.NumberInput(attrs={"class": "field-input", "step": "0.1"}))
    phosphorus_ppm = forms.FloatField(widget=forms.NumberInput(attrs={"class": "field-input", "step": "0.1"}))
    potassium_ppm = forms.FloatField(widget=forms.NumberInput(attrs={"class": "field-input", "step": "0.1"}))
    cultivated_area_hectares = forms.FloatField(
        widget=forms.NumberInput(attrs={"class": "field-input", "step": "1"})
    )
