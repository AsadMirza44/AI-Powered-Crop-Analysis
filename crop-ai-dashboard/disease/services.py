from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
import tensorflow as tf
from django.conf import settings

from recommendations.services import build_disease_recommendations
from smart_crop_ai.reference_data import CROP_PROFILES, DISEASE_CLASS_DETAILS


@dataclass
class DiseaseResult:
    predicted_label: str
    confidence: float
    probabilities: list[dict]
    recommendations: list[str]
    summary: str
    coverage_pct: float
    hotspot_pct: float
    overlay_path: str


class DiseasePredictionService:
    def __init__(self) -> None:
        self.model_path = Path(settings.DISEASE_MODEL_PATH)
        self.metadata_path = Path(settings.DISEASE_METADATA_PATH)
        if not self.model_path.exists() or not self.metadata_path.exists():
            raise FileNotFoundError(
                "TensorFlow disease artifacts are missing. Run training/disease/train_demo_disease_model.py first."
            )
        self.model = tf.keras.models.load_model(self.model_path)
        self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        self.class_names = self.metadata["class_names"]
        self.class_details = self.metadata.get("class_details", DISEASE_CLASS_DETAILS)
        self.image_size = tuple(self.metadata.get("image_size", [128, 128]))
        self.last_conv_layer = self.metadata.get("last_conv_layer", "gradcam_conv")

    def predict(self, raw_bytes: bytes, crop: str, source_name: str | None = None) -> DiseaseResult:
        original_rgb, batch = self._preprocess(raw_bytes)
        probabilities = self.model.predict(batch, verbose=0)[0]
        crop_probabilities = self._filter_probabilities_for_crop(probabilities, crop)
        predicted_index = int(np.argmax(crop_probabilities))
        predicted_key = self.class_names[predicted_index]
        predicted_label = self._display_label(predicted_key)
        confidence = float(crop_probabilities[predicted_index])

        heatmap = self._gradcam(batch, predicted_index)
        coverage_pct, hotspot_pct = self._leaf_metrics(original_rgb, heatmap)
        overlay_path = self._save_overlay(original_rgb, heatmap, source_name)

        ranked = sorted(
            (
                {"label": self._display_label(label), "probability": round(float(probability), 4)}
                for label, probability in zip(self.class_names, crop_probabilities, strict=True)
                if probability > 0
            ),
            key=lambda item: item["probability"],
            reverse=True,
        )

        crop_label = CROP_PROFILES[crop]["label"]
        summary = (
            f"{crop_label} leaf analysis suggests {predicted_label.lower()} with "
            f"{confidence:.0%} confidence. Plant coverage is {coverage_pct:.1f}% and the "
            f"highlighted stress zone covers {hotspot_pct:.1f}% of the visible leaf area."
        )

        return DiseaseResult(
            predicted_label=predicted_label,
            confidence=confidence,
            probabilities=ranked,
            recommendations=build_disease_recommendations(crop, predicted_label, confidence, hotspot_pct),
            summary=summary,
            coverage_pct=coverage_pct,
            hotspot_pct=hotspot_pct,
            overlay_path=overlay_path,
        )

    def _preprocess(self, raw_bytes: bytes) -> tuple[np.ndarray, np.ndarray]:
        array = np.frombuffer(raw_bytes, dtype=np.uint8)
        frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Unsupported image file.")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, self.image_size)
        normalized = resized.astype("float32") / 255.0
        return rgb, normalized[np.newaxis, ...]

    def _display_label(self, label_key: str) -> str:
        return str(self.class_details.get(label_key, {}).get("display_name", label_key))

    def _filter_probabilities_for_crop(self, probabilities: np.ndarray, crop: str) -> np.ndarray:
        mask = np.asarray(
            [
                1.0 if self.class_details.get(label_key, {}).get("crop") == crop else 0.0
                for label_key in self.class_names
            ],
            dtype="float32",
        )
        if float(mask.sum()) == 0:
            return probabilities
        filtered = probabilities * mask
        total = float(filtered.sum())
        if total <= 0:
            return probabilities
        return filtered / total

    def _gradcam(self, batch: np.ndarray, predicted_index: int) -> np.ndarray:
        grad_model = tf.keras.models.Model(
            self.model.input,
            [self.model.get_layer(self.last_conv_layer).output, self.model.output],
        )
        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model(batch)
            loss = predictions[:, predicted_index]
        grads = tape.gradient(loss, conv_outputs)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        conv_outputs = conv_outputs[0]
        heatmap = tf.reduce_sum(conv_outputs * pooled_grads, axis=-1)
        heatmap = np.maximum(heatmap.numpy(), 0)
        if np.max(heatmap) > 0:
            heatmap /= np.max(heatmap)
        return heatmap.astype("float32")

    def _leaf_metrics(self, original_rgb: np.ndarray, heatmap: np.ndarray) -> tuple[float, float]:
        hsv = cv2.cvtColor(original_rgb, cv2.COLOR_RGB2HSV)
        leaf_mask = cv2.inRange(hsv, (20, 25, 25), (110, 255, 255))
        coverage_pct = (float(np.count_nonzero(leaf_mask)) / leaf_mask.size) * 100

        resized_mask = cv2.resize(leaf_mask, (heatmap.shape[1], heatmap.shape[0]), interpolation=cv2.INTER_NEAREST)
        hotspot_mask = (heatmap > 0.55).astype("uint8") * 255
        masked_hotspots = cv2.bitwise_and(hotspot_mask, resized_mask)
        denominator = max(np.count_nonzero(resized_mask), 1)
        hotspot_pct = (float(np.count_nonzero(masked_hotspots)) / denominator) * 100
        return round(coverage_pct, 2), round(hotspot_pct, 2)

    def _save_overlay(self, original_rgb: np.ndarray, heatmap: np.ndarray, source_name: str | None) -> str:
        overlay_dir = Path(settings.MEDIA_ROOT) / "uploads" / "overlays"
        overlay_dir.mkdir(parents=True, exist_ok=True)
        source_stem = Path(source_name or "leaf").stem
        output_name = f"{source_stem}_{uuid4().hex[:8]}.png"
        output_path = overlay_dir / output_name

        resized_heatmap = cv2.resize(heatmap, (original_rgb.shape[1], original_rgb.shape[0]))
        color_map = cv2.applyColorMap(np.uint8(resized_heatmap * 255), cv2.COLORMAP_INFERNO)
        overlay = cv2.addWeighted(cv2.cvtColor(original_rgb, cv2.COLOR_RGB2BGR), 0.6, color_map, 0.4, 0)
        cv2.imwrite(str(output_path), overlay)
        return f"uploads/overlays/{output_name}"


@lru_cache(maxsize=1)
def get_disease_service() -> DiseasePredictionService:
    return DiseasePredictionService()
