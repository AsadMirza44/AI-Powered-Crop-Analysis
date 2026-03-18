from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import urllib.parse
import zipfile
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import requests
import tensorflow as tf
from sklearn.model_selection import train_test_split

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from smart_crop_ai.reference_data import DISEASE_CLASS_DETAILS

RAW_DIR = ROOT_DIR / "data" / "raw" / "disease"
PROCESSED_DIR = ROOT_DIR / "data" / "processed" / "disease"
MODELS_DIR = ROOT_DIR / "models" / "disease"
TFDS_DIR = ROOT_DIR / "data" / "tfds"
PLANTVILLAGE_URL = "https://data.mendeley.com/public-files/datasets/tywbtsjrjv/files/d5652a28-c1d8-4b76-97f3-72fb80f94efc/file_downloaded"

PLANTVILLAGE_LABELS = {
    "maize_healthy": "Corn___healthy",
    "maize_common_rust": "Corn___Common_rust",
    "maize_northern_leaf_blight": "Corn___Northern_Leaf_Blight",
    "potato_healthy": "Potato___healthy",
    "potato_early_blight": "Potato___Early_blight",
    "potato_late_blight": "Potato___Late_blight",
    "tomato_healthy": "Tomato___healthy",
    "tomato_bacterial_spot": "Tomato___Bacterial_spot",
    "tomato_early_blight": "Tomato___Early_blight",
    "tomato_late_blight": "Tomato___Late_blight",
    "tomato_leaf_mold": "Tomato___Leaf_Mold",
    "tomato_septoria_leaf_spot": "Tomato___Septoria_leaf_spot",
    "tomato_tomato_yellow_leaf_curl_virus": "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
}

PLANTDOC_FOLDERS = {
    "maize_common_rust": ["Corn rust leaf"],
    "maize_northern_leaf_blight": ["Corn leaf blight", "Corn Gray leaf spot"],
    "potato_early_blight": ["Potato leaf early blight"],
    "potato_late_blight": ["Potato leaf late blight"],
    "tomato_healthy": ["Tomato leaf"],
    "tomato_bacterial_spot": ["Tomato leaf bacterial spot"],
    "tomato_early_blight": ["Tomato Early blight leaf"],
    "tomato_late_blight": ["Tomato leaf late blight"],
    "tomato_leaf_mold": ["Tomato mold leaf"],
    "tomato_septoria_leaf_spot": ["Tomato Septoria leaf spot"],
    "tomato_tomato_yellow_leaf_curl_virus": ["Tomato leaf yellow virus"],
}

PLANTDOC_TREE_URL = "https://api.github.com/repos/pratikkayal/PlantDoc-Dataset/git/trees/master?recursive=1"
PLANTDOC_RAW_ROOT = "https://raw.githubusercontent.com/pratikkayal/PlantDoc-Dataset/master/"
MENDELEY_PUBLIC_API = "https://data.mendeley.com/public-api/datasets/{dataset_id}"
MENDELEY_ARCHIVES = [
    {
        "dataset_id": "t9hgvk2h9p",
        "filename": "Cotton_Original_Dataset.zip",
        "source": "mendeley_cotton",
        "folder_map": {
            "Cotton_Original_Dataset/Alternaria Leaf Spot/": "cotton_alternaria_leaf_spot",
            "Cotton_Original_Dataset/Bacterial Blight/": "cotton_bacterial_blight",
            "Cotton_Original_Dataset/Fusarium Wilt/": "cotton_fusarium_wilt",
            "Cotton_Original_Dataset/Healthy Leaf/": "cotton_healthy",
            "Cotton_Original_Dataset/Verticillium Wilt/": "cotton_verticillium_wilt",
        },
    },
    {
        "dataset_id": "355y629ynj",
        "filename": "Healthy Leaves.zip",
        "source": "mendeley_sugarcane",
        "folder_map": {
            "Healthy Leaves/": "sugarcane_healthy",
        },
    },
    {
        "dataset_id": "355y629ynj",
        "filename": "BrownRust.zip",
        "source": "mendeley_sugarcane",
        "folder_map": {
            "BrownRust/": "sugarcane_brown_rust",
        },
    },
    {
        "dataset_id": "355y629ynj",
        "filename": "Pokkah Boeng.zip",
        "source": "mendeley_sugarcane",
        "folder_map": {
            "Pokkah Boeng/": "sugarcane_pokkah_boeng",
        },
    },
    {
        "dataset_id": "355y629ynj",
        "filename": "smut.zip",
        "source": "mendeley_sugarcane",
        "folder_map": {
            "smut/": "sugarcane_smut",
        },
    },
    {
        "dataset_id": "355y629ynj",
        "filename": "Viral Disease.zip",
        "source": "mendeley_sugarcane",
        "folder_map": {
            "Viral Disease/": "sugarcane_viral_disease",
        },
    },
    {
        "dataset_id": "355y629ynj",
        "filename": "Yellow Leaf.zip",
        "source": "mendeley_sugarcane",
        "folder_map": {
            "Yellow Leaf/": "sugarcane_yellow_leaf",
        },
    },
]
IMAGE_SIZE = (160, 160)
TARGET_CLASSES = list(DISEASE_CLASS_DETAILS)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the proposal-aligned disease model.")
    parser.add_argument("--max-plantvillage-per-class", type=int, default=220)
    parser.add_argument("--max-plantdoc-per-class", type=int, default=55)
    parser.add_argument("--max-mendeley-per-class", type=int, default=220)
    parser.add_argument("--head-epochs", type=int, default=3)
    parser.add_argument("--finetune-epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--refresh-plantdoc-tree", action="store_true")
    return parser.parse_args()


def ensure_directories() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    TFDS_DIR.mkdir(parents=True, exist_ok=True)


def preprocess_rgb_image(image_rgb: np.ndarray, image_size: tuple[int, int]) -> np.ndarray:
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    resized = cv2.resize(image_bgr, image_size, interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    enhanced = cv2.merge((l_channel, a_channel, b_channel))
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
    return enhanced.astype("float32")


def build_plantdoc_tree(refresh: bool) -> list[dict]:
    cache_path = RAW_DIR / "plantdoc_tree.json"
    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))["tree"]

    response = requests.get(PLANTDOC_TREE_URL, headers={"Accept": "application/vnd.github+json"}, timeout=90)
    response.raise_for_status()
    payload = response.json()
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload["tree"]


def safe_file_name(path: str) -> str:
    source_name = Path(path).name.replace("?", "_")
    digest = hashlib.md5(path.encode("utf-8")).hexdigest()[:8]
    return f"{Path(source_name).stem}_{digest}{Path(source_name).suffix or '.jpg'}"


def download_plantdoc_subset(max_per_class: int, refresh_tree: bool) -> tuple[list[np.ndarray], list[str], list[dict]]:
    tree = build_plantdoc_tree(refresh_tree)
    class_to_paths: dict[str, list[str]] = defaultdict(list)

    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item["path"]
        parts = path.split("/")
        if len(parts) < 3 or parts[0] not in {"train", "test"}:
            continue
        folder = parts[1]
        for canonical_label, folders in PLANTDOC_FOLDERS.items():
            if folder in folders:
                class_to_paths[canonical_label].append(path)

    images: list[np.ndarray] = []
    labels: list[str] = []
    manifest: list[dict] = []
    rng = random.Random(42)

    for canonical_label in TARGET_CLASSES:
        selected_paths = class_to_paths.get(canonical_label, [])
        if not selected_paths:
            continue
        rng.shuffle(selected_paths)
        selected_paths = selected_paths[:max_per_class]
        target_dir = RAW_DIR / "plantdoc" / canonical_label
        target_dir.mkdir(parents=True, exist_ok=True)

        for path in selected_paths:
            local_path = target_dir / safe_file_name(path)
            if not local_path.exists():
                raw_url = PLANTDOC_RAW_ROOT + urllib.parse.quote(path, safe="/")
                response = requests.get(raw_url, timeout=90)
                response.raise_for_status()
                local_path.write_bytes(response.content)

            image_bytes = np.frombuffer(local_path.read_bytes(), dtype=np.uint8)
            image_bgr = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
            if image_bgr is None:
                continue
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            images.append(preprocess_rgb_image(image_rgb, IMAGE_SIZE))
            labels.append(canonical_label)
            manifest.append(
                {
                    "source": "plantdoc",
                    "canonical_label": canonical_label,
                    "display_name": DISEASE_CLASS_DETAILS[canonical_label]["display_name"],
                    "file_path": str(local_path.relative_to(ROOT_DIR)),
                    "source_path": path,
                }
            )

    return images, labels, manifest


def resolve_mendeley_download_url(dataset_id: str, filename: str) -> str:
    response = requests.get(MENDELEY_PUBLIC_API.format(dataset_id=dataset_id), timeout=90)
    response.raise_for_status()
    payload = response.json()
    for file_info in payload.get("files", []):
        if file_info.get("filename") == filename:
            return file_info["content_details"]["download_url"]
    raise RuntimeError(f"Could not locate {filename} in Mendeley dataset {dataset_id}.")


def download_mendeley_subset(max_per_class: int) -> tuple[list[np.ndarray], list[str], list[dict]]:
    images: list[np.ndarray] = []
    labels: list[str] = []
    manifest: list[dict] = []
    rng = random.Random(42)
    archive_root = RAW_DIR / "mendeley_archives"
    archive_root.mkdir(parents=True, exist_ok=True)

    for spec in MENDELEY_ARCHIVES:
        archive_path = archive_root / spec["filename"]
        if not archive_path.exists():
            download_url = resolve_mendeley_download_url(spec["dataset_id"], spec["filename"])
            response = requests.get(download_url, timeout=240)
            response.raise_for_status()
            archive_path.write_bytes(response.content)

        with zipfile.ZipFile(archive_path) as archive:
            member_names = archive.namelist()
            for folder, canonical_label in spec["folder_map"].items():
                selected_members = [
                    member
                    for member in member_names
                    if member.startswith(folder) and Path(member).suffix.lower() in IMAGE_SUFFIXES
                ]
                if not selected_members:
                    continue
                rng.shuffle(selected_members)
                selected_members = selected_members[:max_per_class]
                target_dir = RAW_DIR / "mendeley" / canonical_label
                target_dir.mkdir(parents=True, exist_ok=True)

                for member in selected_members:
                    local_path = target_dir / safe_file_name(f"{spec['filename']}::{member}")
                    if not local_path.exists():
                        local_path.write_bytes(archive.read(member))

                    image_bytes = np.frombuffer(local_path.read_bytes(), dtype=np.uint8)
                    image_bgr = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
                    if image_bgr is None:
                        continue
                    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
                    images.append(preprocess_rgb_image(image_rgb, IMAGE_SIZE))
                    labels.append(canonical_label)
                    manifest.append(
                        {
                            "source": spec["source"],
                            "canonical_label": canonical_label,
                            "display_name": DISEASE_CLASS_DETAILS[canonical_label]["display_name"],
                            "file_path": str(local_path.relative_to(ROOT_DIR)),
                            "source_path": f"{spec['filename']}::{member}",
                        }
                    )

    return images, labels, manifest


def load_plantvillage_subset(max_per_class: int) -> tuple[list[np.ndarray], list[str], list[dict]]:
    root = resolve_plantvillage_root()
    images: list[np.ndarray] = []
    labels: list[str] = []
    manifest: list[dict] = []
    rng = random.Random(42)

    for canonical_label, raw_label in PLANTVILLAGE_LABELS.items():
        class_dir = root / raw_label
        if not class_dir.exists():
            continue
        files = sorted([path for path in class_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"}])
        rng.shuffle(files)
        for file_path in files[:max_per_class]:
            image_bgr = cv2.imread(str(file_path))
            if image_bgr is None:
                continue
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            images.append(preprocess_rgb_image(image_rgb, IMAGE_SIZE))
            labels.append(canonical_label)
            manifest.append(
                {
                    "source": "plant_village",
                    "canonical_label": canonical_label,
                    "display_name": DISEASE_CLASS_DETAILS[canonical_label]["display_name"],
                    "file_path": str(file_path.relative_to(ROOT_DIR)),
                    "source_path": raw_label,
                }
            )

    return images, labels, manifest


def resolve_plantvillage_root() -> Path:
    extracted_roots = list((TFDS_DIR / "downloads" / "extracted").glob("*/Plant_leave_diseases_dataset_without_augmentation"))
    if extracted_roots:
        return extracted_roots[0]

    zip_path = RAW_DIR / "plantvillage.zip"
    extract_root = RAW_DIR / "plantvillage_extracted"
    target_root = extract_root / "Plant_leave_diseases_dataset_without_augmentation"
    if target_root.exists():
        return target_root

    response = requests.get(PLANTVILLAGE_URL, timeout=180)
    response.raise_for_status()
    zip_path.write_bytes(response.content)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_root)
    return target_root


def save_manifest(manifest: list[dict]) -> None:
    manifest_path = PROCESSED_DIR / "disease_dataset_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source", "canonical_label", "display_name", "file_path", "source_path"],
        )
        writer.writeheader()
        writer.writerows(manifest)


def build_dataset(
    max_plantvillage_per_class: int,
    max_plantdoc_per_class: int,
    max_mendeley_per_class: int,
    refresh_tree: bool,
) -> tuple[np.ndarray, np.ndarray, list[dict], dict]:
    pv_images, pv_labels, pv_manifest = load_plantvillage_subset(max_plantvillage_per_class)
    pd_images, pd_labels, pd_manifest = download_plantdoc_subset(max_plantdoc_per_class, refresh_tree)
    md_images, md_labels, md_manifest = download_mendeley_subset(max_mendeley_per_class)

    combined_images = pv_images + pd_images + md_images
    combined_labels = pv_labels + pd_labels + md_labels
    manifest = pv_manifest + pd_manifest + md_manifest
    save_manifest(manifest)

    if not combined_images:
        raise RuntimeError("No disease images were collected from the configured public datasets.")

    missing_classes = sorted(set(TARGET_CLASSES) - set(combined_labels))
    if missing_classes:
        raise RuntimeError(f"Disease dataset is missing required classes: {', '.join(missing_classes)}")

    x = np.asarray(combined_images, dtype=np.float32)
    label_to_index = {label: index for index, label in enumerate(TARGET_CLASSES)}
    y_indices = np.asarray([label_to_index[label] for label in combined_labels], dtype=np.int32)
    y = tf.keras.utils.to_categorical(y_indices, num_classes=len(TARGET_CLASSES))

    counts_by_source: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in manifest:
        counts_by_source[item["source"]][item["canonical_label"]] += 1

    return x, y, manifest, {source: dict(values) for source, values in counts_by_source.items()}


def build_model(num_classes: int) -> tuple[tf.keras.Model, tf.keras.Model]:
    inputs = tf.keras.Input(shape=(*IMAGE_SIZE, 3))
    augmented = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.05),
            tf.keras.layers.RandomZoom(0.08),
        ],
        name="augmentation",
    )(inputs)
    preprocessed = tf.keras.applications.mobilenet_v2.preprocess_input(augmented)
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(*IMAGE_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )
    base_model.trainable = False
    x = base_model(preprocessed, training=False)
    x = tf.keras.layers.Conv2D(256, 1, activation="relu", name="gradcam_conv")(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    return model, base_model


def unfreeze_for_finetune(base_model: tf.keras.Model) -> None:
    base_model.trainable = True
    for layer in base_model.layers[:-30]:
        layer.trainable = False
    for layer in base_model.layers:
        if isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = False


def train() -> None:
    args = parse_args()
    ensure_directories()
    tf.keras.utils.set_random_seed(42)

    x, y, manifest, counts_by_source = build_dataset(
        max_plantvillage_per_class=args.max_plantvillage_per_class,
        max_plantdoc_per_class=args.max_plantdoc_per_class,
        max_mendeley_per_class=args.max_mendeley_per_class,
        refresh_tree=args.refresh_plantdoc_tree,
    )
    class_indices = np.argmax(y, axis=1)

    x_train, x_temp, y_train, y_temp = train_test_split(
        x,
        y,
        test_size=0.3,
        random_state=42,
        stratify=class_indices,
    )
    x_val, x_test, y_val, y_test = train_test_split(
        x_temp,
        y_temp,
        test_size=0.5,
        random_state=42,
        stratify=np.argmax(y_temp, axis=1),
    )

    model, base_model = build_model(len(TARGET_CLASSES))
    callbacks = [tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=2, restore_best_weights=True)]

    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3), loss="categorical_crossentropy", metrics=["accuracy"])
    head_history = model.fit(
        x_train,
        y_train,
        validation_data=(x_val, y_val),
        epochs=args.head_epochs,
        batch_size=args.batch_size,
        verbose=1,
        callbacks=callbacks,
    )

    unfreeze_for_finetune(base_model)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    finetune_history = model.fit(
        x_train,
        y_train,
        validation_data=(x_val, y_val),
        epochs=args.finetune_epochs,
        batch_size=args.batch_size,
        verbose=1,
        callbacks=callbacks,
    )

    test_loss, test_accuracy = model.evaluate(x_test, y_test, verbose=0)

    model_path = MODELS_DIR / "smart_crop_disease.keras"
    metadata_path = MODELS_DIR / "smart_crop_disease_metadata.json"
    model.save(model_path)

    class_counts: dict[str, dict[str, int]] = {}
    available_sources = sorted(counts_by_source)
    for canonical_label in TARGET_CLASSES:
        class_counts[canonical_label] = {
            source: int(counts_by_source.get(source, {}).get(canonical_label, 0))
            for source in available_sources
            if int(counts_by_source.get(source, {}).get(canonical_label, 0)) > 0
        }

    metadata = {
        "class_names": TARGET_CLASSES,
        "class_details": DISEASE_CLASS_DETAILS,
        "image_size": list(IMAGE_SIZE),
        "last_conv_layer": "gradcam_conv",
        "model_family": "MobileNetV2",
        "train_accuracy": round(float(head_history.history["accuracy"][-1]), 4),
        "val_accuracy": round(float(head_history.history["val_accuracy"][-1]), 4),
        "finetune_val_accuracy": round(float(finetune_history.history["val_accuracy"][-1]), 4),
        "test_accuracy": round(float(test_accuracy), 4),
        "test_loss": round(float(test_loss), 4),
        "manifest_rows": len(manifest),
        "class_counts": class_counts,
        "notes": (
            "Real-data TensorFlow disease baseline built from PlantVillage, PlantDoc, and crop-specific "
            "Mendeley disease datasets for cotton and sugarcane. MobileNetV2 is used for transfer learning, "
            "OpenCV handles preprocessing, and crop-aware filtering is applied at inference time."
        ),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Saved TensorFlow disease model to {model_path}")
    print(f"Saved metadata to {metadata_path}")
    print(f"Test accuracy: {test_accuracy:.4f}")


if __name__ == "__main__":
    train()
