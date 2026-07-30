#!/usr/bin/env python
"""Prueba rápida de Amazon Rekognition (DetectLabels) sobre imágenes de MSL NavCam.

NO entrena ningún modelo: llama a la API de detección de etiquetas genéricas para
ver *qué reconoce* Rekognition en el terreno marciano. Es un sondeo inicial (barato,
sin infraestructura) para decidir si vale la pena montar un modelo Custom Labels
entrenado (que sí podría detectar/contar rocas, pero requiere entrenamiento y costo).

Requisitos previos (los ejecutas TÚ en tu terminal, con tu cuenta AWS):
  1. Configurar credenciales:      aws configure
     (necesita permiso ``rekognition:DetectLabels``)
  2. Instalar boto3 si falta:      pip install boto3

Uso:
  python scripts/rekognition_test.py
  python scripts/rekognition_test.py --region us-east-1 --min-confidence 50

Nota de privacidad: las imágenes se envían a tu cuenta de AWS para su análisis.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Palabras que consideraríamos "relevantes" para el terreno/roca (para resaltar).
ROCK_HINTS = {"rock", "rocks", "boulder", "gravel", "stone", "pebble", "cliff",
              "soil", "sand", "ground", "terrain", "geology", "rubble", "mineral"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images-dir", default="outputs/rekognition_test/images")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--max-labels", type=int, default=20)
    ap.add_argument("--min-confidence", type=float, default=40.0)
    ap.add_argument("--out", default="outputs/rekognition_test/detect_labels_results.csv")
    args = ap.parse_args()

    try:
        import boto3
        from botocore.exceptions import (BotoCoreError, ClientError,
                                         NoCredentialsError)
    except ImportError:
        sys.exit("Falta boto3. Instálalo con:  pip install boto3")

    images = sorted(p for p in Path(args.images_dir).iterdir()
                    if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if not images:
        sys.exit(f"No hay imágenes en {args.images_dir}")

    client = boto3.client("rekognition", region_name=args.region)
    rows: list[dict] = []
    print(f"Analizando {len(images)} imágenes con Rekognition DetectLabels "
          f"(región {args.region})...\n")

    for img in images:
        data = img.read_bytes()
        try:
            resp = client.detect_labels(
                Image={"Bytes": data},
                MaxLabels=args.max_labels,
                MinConfidence=args.min_confidence,
            )
        except NoCredentialsError:
            sys.exit("Sin credenciales AWS. Ejecuta primero:  aws configure")
        except (ClientError, BotoCoreError) as e:
            sys.exit(f"Error de AWS: {e}\n(Revisa credenciales, región y permiso "
                     f"rekognition:DetectLabels.)")

        labels = resp.get("Labels", [])
        top = ", ".join(f"{l['Name']}({l['Confidence']:.0f}%)" for l in labels[:8])
        n_inst = sum(len(l.get("Instances", [])) for l in labels)
        hits = [l["Name"] for l in labels if l["Name"].lower() in ROCK_HINTS]
        flag = f"  <- relevante: {', '.join(hits)}" if hits else ""
        print(f"• {img.name}")
        print(f"    {top}")
        print(f"    objetos con bounding box: {n_inst}{flag}\n")

        for l in labels:
            rows.append({
                "file": img.name,
                "label": l["Name"],
                "confidence": round(l["Confidence"], 1),
                "instances": len(l.get("Instances", [])),
                "categories": "|".join(c["Name"] for c in l.get("Categories", [])),
            })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "label", "confidence",
                                          "instances", "categories"])
        w.writeheader()
        w.writerows(rows)
    print(f"Resultados detallados -> {out}")
    print("\nLectura: si Rekognition genérico NO devuelve etiquetas de roca útiles "
          "(o 0 bounding boxes de rocas), eso justifica pasar a Custom Labels "
          "entrenado con nuestras máscaras.")


if __name__ == "__main__":
    main()
