from django.test import TestCase


class RecommendationViewTests(TestCase):
    def test_recommendation_center_loads(self):
        self.assertEqual(self.client.get("/recommendations/").status_code, 200)
