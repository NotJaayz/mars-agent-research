#!/usr/bin/env python
"""Entrena DeepLabV3 para segmentar roca / no-roca y evalúa la cobertura que deriva.

Diseño fijado ANTES de entrenar (y registrado en outputs/segmentacion_metricas.json):

1. Población elegible. Escenas de MSL NavCam con máscara de entrenamiento colaborativa,
   bandera ok / no_bigrock / no_rock y fracción etiquetada >= 0,20: por debajo, la pérdida
   se calcularía sobre muy pocos píxeles. Las máscaras de experto NO intervienen en ningún
   momento del entrenamiento ni de la selección.
2. Reparto por bloques temporales. Las escenas elegibles se ordenan por reloj de nave y se
   dividen en 30 bloques consecutivos de igual tamaño; los bloques se asignan al azar
   (semilla 0) a entrenamiento (20), validación (5) y prueba (5). Se descarta de validación y
   de prueba toda escena a menos de un sol de una escena de otra partición, de modo que dos
   tomas casi idénticas no pueden quedar a ambos lados del reparto.
3. Muestras. Dentro de cada partición se toma una muestra equilibrada entre escenas con
   roca (cobertura > 1 %) y sin roca: 2000 / 400 / 400. La prueba se repite además sobre
   TODAS las escenas elegibles de los bloques de prueba (distribución natural) y sobre las
   de esos bloques que la fracción etiquetada excluyó.
4. Punto de control. Seis épocas fijas; se conserva el modelo de la época con mayor mIoU de
   validación. La prueba se evalúa una sola vez, con ese modelo.

Salidas en outputs/: modelo_deeplab_binario.pt (no versionado; su SHA-256 queda en el
JSON), segmentacion_metricas.json, split_deeplab.json, split_deeplab_manifiesto.csv,
split_deeplab_clases.json, cobertura_modelo_vs_humano.csv (muestra equilibrada de prueba)
y cobertura_modelo_prueba_natural.csv.

Uso:
  python scripts/train_segmentation.py                         # configuración completa
  python scripts/train_segmentation.py --n-train 200 --epochs 1 --n-val 40 --n-test 40  # prueba rápida
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config, mask_utils as mu, segmentation as seg  # noqa: E402

SOL = 88775.244            # segundos por sol marciano
FRAC_VALID_MIN = 0.20
BANDERAS = ["ok", "no_bigrock", "no_rock"]
N_BLOQUES = {"train": 20, "val": 5, "test": 5}


def reparto_por_bloques(pool: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Asigna cada escena a un bloque temporal y a una partición, con margen de un sol."""
    p = pool.sort_values("sclk").reset_index(drop=True).copy()
    n_total = sum(N_BLOQUES.values())
    p["bloque"] = np.repeat(np.arange(n_total), np.diff(np.linspace(0, len(p), n_total + 1).astype(int)))
    orden = np.random.default_rng(seed).permutation(n_total)
    asign = {}
    i = 0
    for part, k in N_BLOQUES.items():
        for b in orden[i:i + k]:
            asign[int(b)] = part
        i += k
    p["particion"] = p.bloque.map(asign)
    # Margen: test lejos de train y val; val lejos de train.
    def lejos(part, de):
        ref = np.sort(p.loc[p.particion.isin(de), "sclk"].values.astype(float))
        s = p.loc[p.particion == part, "sclk"].values.astype(float)
        k = np.searchsorted(ref, s)
        d = np.minimum(np.abs(s - ref[np.clip(k - 1, 0, len(ref) - 1)]),
                       np.abs(s - ref[np.clip(k, 0, len(ref) - 1)]))
        return d >= SOL
    for part, de in (("val", ["train"]), ("test", ["train", "val"])):
        m = p.particion == part
        p.loc[m, "particion"] = np.where(lejos(part, de), part, "margen")
    return p


def muestra_equilibrada(df: pd.DataFrame, n: int, rng) -> list[str]:
    roca = df[df.roca].image_id.tolist(); otra = df[~df.roca].image_id.tolist()
    rng.shuffle(roca); rng.shuffle(otra)
    n_r = min(len(roca), n // 2); n_o = min(len(otra), n - n_r)
    ids = roca[:n_r] + otra[:n_o]
    rng.shuffle(ids)
    return ids


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-train", type=int, default=2000)
    ap.add_argument("--n-val", type=int, default=400)
    ap.add_argument("--n-test", type=int, default=400)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--img-size", type=int, default=512)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sin-natural", action="store_true",
                    help="omite la evaluación sobre la distribución natural (prueba rápida)")
    args = ap.parse_args()

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    torch.manual_seed(args.seed)
    print(f"device={device}  img={args.img_size}  épocas={args.epochs}", flush=True)

    # --- Población elegible y reparto -------------------------------------------------
    res = pd.read_csv("outputs/results.csv")
    cand = res[res.quality_flag.isin(BANDERAS)]
    pool = cand[cand.frac_valid >= FRAC_VALID_MIN].copy()
    excluidas = cand[cand.frac_valid < FRAC_VALID_MIN].copy()
    pool["roca"] = pool.rock_coverage_pct.fillna(0) > 1
    rep = reparto_por_bloques(pool, args.seed)
    rng = np.random.default_rng(args.seed)
    tr = muestra_equilibrada(rep[rep.particion == "train"], args.n_train, rng)
    va = muestra_equilibrada(rep[rep.particion == "val"], args.n_val, rng)
    te = muestra_equilibrada(rep[rep.particion == "test"], args.n_test, rng)
    natural = rep[rep.particion == "test"].image_id.tolist()
    # Escenas excluidas por fracción etiquetada que caen dentro de los bloques de prueba.
    lim = rep[rep.particion == "test"].groupby("bloque").sclk.agg(["min", "max"])
    exc_test = excluidas[excluidas.sclk.apply(
        lambda s: bool(((lim["min"] <= s) & (s <= lim["max"])).any()))].image_id.tolist()
    print(f"elegibles={len(pool)} (excluidas por fracción < {FRAC_VALID_MIN}: {len(excluidas)})  "
          f"particiones={rep.particion.value_counts().to_dict()}", flush=True)
    print(f"muestras: train={len(tr)} val={len(va)} test={len(te)}  "
          f"prueba natural={len(natural)}  excluidas en bloques de prueba={len(exc_test)}", flush=True)

    outdir = Path("outputs"); outdir.mkdir(exist_ok=True)
    sel = {**{i: "train" for i in tr}, **{i: "val" for i in va}, **{i: "test" for i in te}}
    man = rep[["image_id", "sclk", "bloque", "particion", "roca"]].copy()
    man["muestra"] = man.image_id.map(sel).fillna("")
    man.to_csv(outdir / "split_deeplab_manifiesto.csv", index=False)
    (outdir / "split_deeplab.json").write_text(json.dumps(
        {"train": tr, "val": va, "test": te, "test_natural": natural,
         "test_excluidas_fraccion": exc_test}, indent=1))

    # Distancia mínima, en soles, de cada escena de prueba a la de entrenamiento más próxima.
    T = np.sort(rep[rep.particion == "train"].sclk.values.astype(float))
    def dmin(ids):
        s = rep.set_index("image_id").loc[ids, "sclk"].values.astype(float)
        k = np.searchsorted(T, s)
        return np.minimum(np.abs(s - T[np.clip(k - 1, 0, len(T) - 1)]),
                          np.abs(s - T[np.clip(k, 0, len(T) - 1)])) / SOL

    # Distribución de clases por muestra (píxeles de roca y sin etiqueta).
    def clases(ids):
        roca = ign = tot = 0
        for i in ids:
            t = seg.to_binary_target(mu.read_mask(config.MSL_NCAM_LABELS_TRAIN / f"{i}.png"))
            roca += int((t == 1).sum()); ign += int((t == seg.IGNORE_INDEX).sum()); tot += t.size
        return {"n": len(ids), "pct_roca": 100 * roca / max(tot - ign, 1), "pct_ignorado": 100 * ign / tot}
    (outdir / "split_deeplab_clases.json").write_text(json.dumps(
        {"train": clases(tr), "val": clases(va), "test": clases(te)}, indent=2))

    # --- Entrenamiento ----------------------------------------------------------------
    mk = lambda s: seg.RockSegDataset(s, args.img_size, binary=True)
    train_dl = DataLoader(mk(tr), batch_size=args.batch, shuffle=True)
    val_dl = DataLoader(mk(va), batch_size=args.batch)

    model = seg.build_model(2, pretrained=True).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    crit = torch.nn.CrossEntropyLoss(ignore_index=seg.IGNORE_INDEX)

    @torch.no_grad()
    def eval_iou(dl):
        model.eval()
        inter = np.zeros(2); union = np.zeros(2)
        for xb, yb in dl:
            pred = model(xb.to(device))["out"].argmax(1).cpu()
            v = yb != seg.IGNORE_INDEX
            for c in range(2):
                p = (pred == c) & v; t = (yb == c) & v
                inter[c] += (p & t).sum().item(); union[c] += (p | t).sum().item()
        return [inter[c] / union[c] if union[c] else float("nan") for c in range(2)]

    out = {"config": vars(args) | {"device": device, "frac_valid_min": FRAC_VALID_MIN,
                                   "banderas": BANDERAS, "bloques": N_BLOQUES, "margen_soles": 1.0,
                                   "regla_punto_control": "mayor mIoU de validación entre las épocas fijadas"},
           "poblacion": {"candidatas": int(len(cand)), "elegibles": int(len(pool)),
                         "excluidas_fraccion": int(len(excluidas)),
                         "particiones": {k: int(v) for k, v in rep.particion.value_counts().items()}},
           "epochs": []}
    meta_path = outdir / "segmentacion_metricas.json"
    ckpt = outdir / "modelo_deeplab_binario.pt"
    mejor = -1.0

    for ep in range(args.epochs):
        model.train(); t0 = time.time(); running = 0.0
        for xb, yb in train_dl:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            o = model(xb)
            loss = crit(o["out"], yb) + 0.4 * crit(o["aux"], yb)
            loss.backward(); opt.step(); running += loss.item()
        ious = eval_iou(val_dl)
        rec = {"epoch": ep + 1, "loss": round(running / len(train_dl), 4),
               "iou_no_roca": round(ious[0], 4), "iou_roca": round(ious[1], 4),
               "miou": round(float(np.nanmean(ious)), 4), "seconds": round(time.time() - t0)}
        out["epochs"].append(rec)
        if rec["miou"] > mejor:
            mejor = rec["miou"]; out["epoca_elegida"] = rec["epoch"]
            torch.save(model.state_dict(), ckpt)
        print(f"época {rec['epoch']}/{args.epochs} loss={rec['loss']:.3f} "
              f"IoU=(no-roca {rec['iou_no_roca']:.3f}, roca {rec['iou_roca']:.3f}) "
              f"mIoU={rec['miou']:.3f} ({rec['seconds']}s)", flush=True)
        meta_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    # --- Prueba, una sola vez, con el punto de control elegido ---------------------------
    model.load_state_dict(torch.load(ckpt, map_location=device))
    out["sha256_modelo"] = sha256(ckpt)
    print(f"punto de control: época {out['epoca_elegida']}  sha256 {out['sha256_modelo'][:12]}…", flush=True)

    def evaluar(ids, nombre):
        filas = []; inter = np.zeros(2); union = np.zeros(2)
        for i in ids:
            mp = config.MSL_NCAM_LABELS_TRAIN / f"{i}.png"
            obj = seg.to_binary_target(mu.read_mask(mp))
            pred = seg.predict_mask(model, mu.mask_to_image_path(mp), args.img_size, device=device)
            v = obj != seg.IGNORE_INDEX
            for c in range(2):
                inter[c] += ((pred == c) & (obj == c) & v).sum(); union[c] += (((pred == c) | (obj == c)) & v).sum()
            nv = int(v.sum())
            filas.append({"image_id": i, "n_valid": nv,
                          "human_cov": 100 * ((obj == 1) & v).sum() / max(nv, 1),
                          "pred_cov": 100 * ((pred == 1) & v).sum() / max(nv, 1)})
        df = pd.DataFrame(filas); df["error"] = df.pred_cov - df.human_cov
        iou = [float(inter[c] / union[c]) if union[c] else float("nan") for c in range(2)]
        r = {"n": int(len(df)), "iou_no_roca": iou[0], "iou_roca": iou[1], "miou": float(np.nanmean(iou)),
             "r_cobertura": float(df.human_cov.corr(df.pred_cov)), "mae": float(df.error.abs().mean()),
             "error_medio": float(df.error.mean())}
        print(f"{nombre:28s} n={r['n']:5d}  mIoU={r['miou']:.3f}  r={r['r_cobertura']:.3f}  "
              f"MAE={r['mae']:.1f}  error medio={r['error_medio']:+.1f}", flush=True)
        return r, df

    out["test"], dft = evaluar(te, "prueba equilibrada")
    d = dmin(te)
    out["test"]["distancia_min_soles"] = float(d.min()); out["test"]["distancia_mediana_soles"] = float(np.median(d))
    dft.to_csv(outdir / "cobertura_modelo_vs_humano.csv", index=False)
    if not args.sin_natural:
        out["test_natural"], dfn = evaluar(natural, "prueba, distribución natural")
        dfn.to_csv(outdir / "cobertura_modelo_prueba_natural.csv", index=False)
        out["test_excluidas_fraccion"], _ = evaluar(exc_test, "prueba, excluidas por fracción")
    meta_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nOK -> {meta_path}", flush=True)


if __name__ == "__main__":
    main()
