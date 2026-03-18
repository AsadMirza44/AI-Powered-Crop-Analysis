from django.test import TestCase


class DashboardViewTests(TestCase):
    def test_dashboard_pages_load(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/metrics/").status_code, 200)
        self.assertEqual(self.client.get("/sources/").status_code, 200)
        self.assertEqual(self.client.get("/history/").status_code, 200)
