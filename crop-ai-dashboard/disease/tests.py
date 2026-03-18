from io import BytesIO

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from .models import DiseasePrediction


class DiseaseViewTests(TestCase):
    def test_disease_upload_creates_prediction_record(self):
        image = Image.new("RGB", (160, 160), color=(76, 150, 60))
        arr = np.array(image)
        arr[30:70, 70:108] = [180, 95, 40]
        arr[92:126, 50:84] = [130, 65, 32]
        image = Image.fromarray(arr)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        upload = SimpleUploadedFile("leaf.png", buffer.getvalue(), content_type="image/png")

        response = self.client.post("/disease/", {"crop": "maize", "image": upload})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(DiseasePrediction.objects.count(), 1)

    def test_disease_demo_sample_creates_prediction_record(self):
        response = self.client.post("/disease/", {"crop": "maize", "demo_sample": "maize_rust"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(DiseasePrediction.objects.count(), 1)
