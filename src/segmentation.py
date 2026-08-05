"""Segmentación de terreno con DeepLabV3 (transfer learning) — línea futura (E5).

Entrena un modelo que predice, a partir de la imagen NavCam, una máscara de terreno,
usando las máscaras de AI4Mars como etiquetas. Dos modos:
  - binario:    roca (bedrock+big rock) vs. no-roca  (balanceado; alimenta la cobertura)
  - multiclase: las 4 clases NAV (soil/bedrock/sand/big rock)
En ambos, el valor 255 (sin etiqueta) se ignora en la pérdida y en el IoU.

Las máscaras predichas pueden alimentarse a nuestro pipeline (cobertura/conteo) para
comparar "modelo aprendido vs. anotación humana". Requiere torch + torchvision; corre
en Apple Silicon con device="mps".
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision.models.segmentation import (DeepLabV3_ResNet50_Weights,
                                             deeplabv3_resnet50)
import torchvision.transforms.functional as TF

from . import config, mask_utils as mu

IGNORE_INDEX = 255
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]


def to_binary_target(mask: np.ndarray) -> np.ndarray:
    """roca (bedrock+big rock)=1, no-roca=0, sin etiqueta=255."""
    out = np.full(mask.shape, IGNORE_INDEX, dtype=np.uint8)
    valid = mask != config.NAV_NULL
    out[valid] = 0
    out[np.isin(mask, config.COVERAGE_CLASSES)] = 1
    return out


class RockSegDataset(Dataset):
    """Par (imagen NavCam, máscara de terreno) para segmentación.

    Devuelve (image_tensor [3,H,W] normalizada ImageNet, target [H,W] long).
    """

    def __init__(self, ids: Sequence[str], img_size: int = 512, binary: bool = True,
                 labels_dir: Path = config.MSL_NCAM_LABELS_TRAIN,
                 images_dir: Path = config.MSL_NCAM_IMAGES):
        self.ids = list(ids)
        self.img_size = img_size
        self.binary = binary
        self.labels_dir = Path(labels_dir)
        self.images_dir = Path(images_dir)

    def __len__(self) -> int:
        return len(self.ids)

    def __getitem__(self, i: int):
        iid = self.ids[i]
        mask_path = self.labels_dir / f"{iid}.png"
        img_path = mu.mask_to_image_path(mask_path, self.images_dir)

        img = Image.open(img_path).convert("RGB").resize(
            (self.img_size, self.img_size), Image.BILINEAR)
        mask = mask_path  # leer con PIL en modo L y redimensionar por vecino más cercano
        m = Image.open(mask).convert("L").resize(
            (self.img_size, self.img_size), Image.NEAREST)
        m = np.asarray(m, dtype=np.uint8)
        target = to_binary_target(m) if self.binary else m.copy()

        x = TF.normalize(TF.to_tensor(img), _IMAGENET_MEAN, _IMAGENET_STD)
        y = torch.from_numpy(target.astype(np.int64))
        return x, y


def build_model(num_classes: int, pretrained: bool = True) -> torch.nn.Module:
    """DeepLabV3-ResNet50 con la cabeza adaptada a num_classes.

    ``pretrained=True`` usa los pesos COCO/VOC (transfer learning; descarga ~160 MB la
    primera vez). ``pretrained=False`` inicializa aleatorio (offline / desde cero).
    """
    if pretrained:
        model = deeplabv3_resnet50(weights=DeepLabV3_ResNet50_Weights.DEFAULT, aux_loss=True)
    else:
        # sin descargas (offline / desde cero)
        model = deeplabv3_resnet50(weights=None, weights_backbone=None, aux_loss=True)
    model.classifier[-1] = torch.nn.Conv2d(256, num_classes, kernel_size=1)
    if model.aux_classifier is not None:
        model.aux_classifier[-1] = torch.nn.Conv2d(256, num_classes, kernel_size=1)
    return model


def iou_per_class(preds: torch.Tensor, targets: torch.Tensor,
                  num_classes: int) -> list[float]:
    """IoU por clase, ignorando los píxeles con valor 255."""
    ious = []
    valid = targets != IGNORE_INDEX
    for c in range(num_classes):
        p = (preds == c) & valid
        t = (targets == c) & valid
        inter = (p & t).sum().item()
        union = (p | t).sum().item()
        ious.append(inter / union if union > 0 else float("nan"))
    return ious


@torch.no_grad()
def predict_mask(model: torch.nn.Module, image_path, img_size: int = 512,
                 device: str = "mps") -> np.ndarray:
    """Predice la máscara de clases a resolución original (para el pipeline)."""
    model.eval()
    orig = Image.open(image_path).convert("RGB")
    W, H = orig.size
    img = orig.resize((img_size, img_size), Image.BILINEAR)
    x = TF.normalize(TF.to_tensor(img), _IMAGENET_MEAN, _IMAGENET_STD)[None].to(device)
    logits = model(x)["out"]
    pred = logits.argmax(1)[0].to("cpu").numpy().astype(np.uint8)
    return np.asarray(Image.fromarray(pred).resize((W, H), Image.NEAREST))
