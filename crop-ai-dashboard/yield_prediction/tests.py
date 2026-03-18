from django.test import TestCase

from .models import YieldPrediction


class YieldViewTests(TestCase):
    def test_yield_forecast_page_includes_demo_mode_controls(self):
        response = self.client.get("/yield/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "District autofill")
        self.assertContains(response, "Balanced Maize Season")
        self.assertContains(response, "Cotton")
        self.assertContains(response, "Sugarcane")

    def test_yield_forecast_creates_prediction_record(self):
        response = self.client.post(
            "/yield/",
            {
                "crop": "maize",
                "district": "Faisalabad",
                "season": "Kharif",
                "year": 2026,
                "rainfall_mm": 390,
                "avg_temp_c": 28.4,
                "soil_ph": 7.1,
                "organic_carbon_pct": 1.02,
                "nitrogen_ppm": 58,
                "phosphorus_ppm": 23,
                "potassium_ppm": 200,
                "cultivated_area_hectares": 15000,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(YieldPrediction.objects.count(), 1)

    def test_yield_forecast_shows_most_recent_historical_years(self):
        response = self.client.post(
            "/yield/",
            {
                "crop": "cotton",
                "district": "Faisalabad",
                "season": "Kharif",
                "year": 2026,
                "rainfall_mm": 390,
                "avg_temp_c": 28.4,
                "soil_ph": 7.1,
                "organic_carbon_pct": 1.02,
                "nitrogen_ppm": 58,
                "phosphorus_ppm": 23,
                "potassium_ppm": 200,
                "cultivated_area_hectares": 15000,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Latest official yield history shown: 2019-2024")
        self.assertContains(response, "2024")
