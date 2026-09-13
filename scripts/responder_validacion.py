#!/usr/bin/env python
"""Interfaz para completar la validación manual por bandas (§8.9).

Muestra una a una las escenas de ``outputs/validacion_manual/imagenes/`` y registra la
banda elegida en ``plantilla.csv``. Sustituye la edición a mano del CSV; el criterio sigue
siendo enteramente de la persona que responde.

Salvaguardas del diseño de la validación:

- El conteo automático (``clave.csv``) **no se lee en ningún momento**, de modo que no
  puede influir en la respuesta.
- No hay navegación hacia atrás, según la indicación de responder de corrido. Se admite
  deshacer únicamente la última respuesta, para corregir una pulsación errónea.
- Cada respuesta se escribe en el CSV al momento, así que el progreso sobrevive a un
  cierre accidental y la sesión puede retomarse donde quedó.

Uso:  python scripts/responder_validacion.py
"""
from __future__ import annotations

import argparse
import csv
import sys
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk

RAIZ = Path(__file__).resolve().parent.parent

# Paleta institucional de la NASA, la misma de app.py.
AZUL, ROJO = "#0B3D91", "#FC3D21"
FONDO, TARJETA, TEXTO, TENUE = "#0f1319", "#171d29", "#e8eaf0", "#8b93a7"

# Bandas de respuesta. El kit v2 subdivide la banda superior: con "10+" abierta, un
# método que contaba 84 rocas donde el observador veía una decena puntuaba como acierto
# exacto, lo que favorecía a los métodos que sobreestiman.
BANDAS_V1 = [
    ("0",    "ninguna"),
    ("1-3",  "entre 1 y 3"),
    ("4-9",  "entre 4 y 9"),
    ("10+",  "10 o más"),
]
BANDAS_V2 = [
    ("0",     "ninguna"),
    ("1-3",   "entre 1 y 3"),
    ("4-9",   "entre 4 y 9"),
    ("10-24", "entre 10 y 24"),
    ("25-49", "entre 25 y 49"),
    ("50+",   "50 o más"),
]


def leer_plantilla(plantilla: Path) -> list[dict[str, str]]:
    with plantilla.open(newline="") as f:
        return list(csv.DictReader(f))


def guardar_plantilla(filas: list[dict[str, str]], plantilla: Path) -> None:
    with plantilla.open("w", newline="") as f:
        # lineterminator explícito: el valor por defecto es CRLF y cambiaría los
        # finales de línea del archivo original, ensuciando el diff.
        w = csv.DictWriter(f, fieldnames=["id", "banda"], lineterminator="\n")
        w.writeheader()
        w.writerows(filas)


class App(tk.Tk):
    def __init__(self, filas: list[dict[str, str]], bandas, plantilla: Path,
                 dir_img: Path) -> None:
        super().__init__()
        self.filas = filas
        self.bandas = bandas
        self.plantilla = plantilla
        self.dir_img = dir_img
        self.historial: list[int] = []      # índices respondidos en esta sesión
        self._img_tk: ImageTk.PhotoImage | None = None

        self.title("Validación manual por bandas — AI4Mars")
        self.configure(bg=FONDO)
        self.resizable(False, False)

        cab = tk.Frame(self, bg=FONDO)
        cab.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(cab, text="¿Cuántas rocas distingues DENTRO de la zona resaltada?",
                 bg=FONDO, fg=TEXTO, font=("Helvetica", 15, "bold")).pack(anchor="w")
        tk.Label(cab, text=f"Responde de corrido, sin volver atrás. "
                            f"Teclas 1 a {len(self.bandas)}.",
                 bg=FONDO, fg=TENUE, font=("Helvetica", 11)).pack(anchor="w")

        self.lbl_img = tk.Label(self, bg=TARJETA, bd=0)
        self.lbl_img.pack(padx=20, pady=10)

        self.lbl_prog = tk.Label(self, text="", bg=FONDO, fg=TENUE,
                                 font=("Helvetica", 12))
        self.lbl_prog.pack(pady=(0, 8))

        botones = tk.Frame(self, bg=FONDO)
        botones.pack(pady=(0, 6))
        ancho = max(9, 15 - len(self.bandas))
        for i, (banda, ayuda) in enumerate(self.bandas):
            b = tk.Frame(botones, bg=FONDO)
            b.grid(row=0, column=i, padx=5)
            # El número de tecla va en una línea aparte: pegado a la banda se leía
            # como parte de la respuesta ("4   10+" parecía significar cuatro).
            tk.Button(b, text=banda, width=ancho, bd=0,
                      bg=AZUL, fg="white", activebackground=ROJO,
                      activeforeground="white", font=("Helvetica", 14, "bold"),
                      command=lambda x=banda: self.responder(x)).pack()
            tk.Label(b, text=ayuda, bg=FONDO, fg=TEXTO,
                     font=("Helvetica", 10)).pack(pady=(3, 0))
            tk.Label(b, text=f"tecla {i+1}", bg=FONDO, fg=TENUE,
                     font=("Helvetica", 8)).pack()

        pie = tk.Frame(self, bg=FONDO)
        pie.pack(pady=(4, 14))
        self.btn_undo = tk.Button(pie, text="Deshacer la última", bd=0, bg=TARJETA,
                                  fg=TENUE, activebackground=TARJETA,
                                  font=("Helvetica", 10), command=self.deshacer)
        self.btn_undo.pack(side="left", padx=6)
        tk.Button(pie, text="Guardar y salir", bd=0, bg=TARJETA, fg=TENUE,
                  activebackground=TARJETA, font=("Helvetica", 10),
                  command=self.destroy).pack(side="left", padx=6)

        for k, (banda, _) in enumerate(self.bandas, start=1):
            self.bind(str(k), lambda _e, x=banda: self.responder(x))
        self.bind("<BackSpace>", lambda _e: self.deshacer())

        self.mostrar()

    # --- lógica ---

    def pendiente(self) -> int | None:
        """Índice de la primera fila sin responder, o None si ya están todas."""
        for i, f in enumerate(self.filas):
            if not (f.get("banda") or "").strip():
                return i
        return None

    def mostrar(self) -> None:
        i = self.pendiente()
        n_ok = sum(1 for f in self.filas if (f.get("banda") or "").strip())
        self.btn_undo.config(state="normal" if self.historial else "disabled")

        if i is None:
            self.lbl_img.config(image="", text="Completado\n\nYa puedes cerrar la ventana.",
                                fg=TEXTO, font=("Helvetica", 18, "bold"),
                                width=60, height=18)
            self.lbl_prog.config(text=f"{n_ok} de {len(self.filas)} respondidas")
            return

        ruta = self.dir_img / f"{self.filas[i]['id']}.png"
        if not ruta.exists():
            self.lbl_img.config(image="", text=f"No se encuentra {ruta.name}", fg=ROJO)
            return
        with Image.open(ruta) as im:
            self._img_tk = ImageTk.PhotoImage(im.convert("RGB"))
        self.lbl_img.config(image=self._img_tk, text="", width=0, height=0)
        self.lbl_prog.config(text=f"Escena {n_ok + 1} de {len(self.filas)}")

    def responder(self, banda: str) -> None:
        i = self.pendiente()
        if i is None:
            return
        self.filas[i]["banda"] = banda
        self.historial.append(i)
        guardar_plantilla(self.filas, self.plantilla)
        self.mostrar()

    def deshacer(self) -> None:
        if not self.historial:
            return
        i = self.historial.pop()
        self.filas[i]["banda"] = ""
        guardar_plantilla(self.filas, self.plantilla)
        self.mostrar()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="outputs/validacion_manual",
                    help="directorio del kit a responder")
    args = ap.parse_args()

    dir_val = (RAIZ / args.dir) if not Path(args.dir).is_absolute() else Path(args.dir)
    plantilla, dir_img = dir_val / "plantilla.csv", dir_val / "imagenes"
    if not plantilla.exists():
        sys.exit(f"Falta {plantilla}. Genera el kit con make_validation_kit2.py")

    # El kit v2 se reconoce por sus identificadores (W01, W02, ...).
    filas = leer_plantilla(plantilla)
    bandas = BANDAS_V2 if filas and filas[0]["id"].startswith("W") else BANDAS_V1

    faltan = sum(1 for f in filas if not (f.get("banda") or "").strip())
    print(f"{len(filas) - faltan} de {len(filas)} ya respondidas; faltan {faltan}.")
    print(f"bandas: {', '.join(b for b, _ in bandas)}")
    App(filas, bandas, plantilla, dir_img).mainloop()
    filas = leer_plantilla(plantilla)
    faltan = sum(1 for f in filas if not (f.get("banda") or "").strip())
    if faltan:
        print(f"Guardado. Faltan {faltan}; al volver a ejecutar continúa donde quedó.")
    else:
        print(f"Completado. Evalúa con: "
              f"python scripts/eval_validation.py --dir {args.dir}")


if __name__ == "__main__":
    main()
