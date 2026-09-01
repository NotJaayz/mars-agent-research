#!/usr/bin/env python
"""Panel de análisis de terreno marciano — aplicación de escritorio.

Producto final del trabajo: interfaz gráfica que reúne los indicadores por imagen, el
sistema de alertas de riesgo y el explorador de escenas, sin necesidad de ejecutar código
ni de conocer el detalle del procedimiento.

Se ejecuta con:

    python app.py

No requiere instalar dependencias adicionales: emplea Tkinter, incluido en la biblioteca
estándar de Python, y matplotlib, que ya utiliza el proyecto.

Paleta institucional de la NASA: azul #0B3D91 y rojo #FC3D21.
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

# --- Paleta institucional --------------------------------------------------------------
AZUL = "#0B3D91"        # NASA blue
ROJO = "#FC3D21"        # NASA red
AZUL_OSC = "#072a66"
GRIS = "#f4f6fa"
GRIS_LN = "#d8dde8"
TINTA = "#16181d"
TENUE = "#5b6270"
NIVEL_COLOR = {"alto": ROJO, "medio": "#e08214", "bajo": "#c9a227", "sin_alerta": "#3d8b5f"}
NIVEL_TXT = {"alto": "Alto", "medio": "Medio", "bajo": "Bajo", "sin_alerta": "Sin alerta"}


def _falta(nombre: str) -> str:
    return (f"No se encontró {nombre}.\n\n"
            "Genera los resultados antes de abrir la aplicación:\n"
            "    python scripts/run_pipeline.py\n"
            "    python scripts/run_alerts.py")


class Panel(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Panel de análisis de terreno marciano — AI4Mars")
        self.geometry("1240x820")
        self.minsize(1040, 700)
        self.configure(bg=GRIS)

        self._cargar_datos()
        self._estilos()
        self._encabezado()

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=16, pady=(8, 4))
        self._tab_resumen()
        self._tab_alertas()
        self._tab_explorador()
        self._tab_geologia()
        self._pie()

    # ---------------------------------------------------------------- datos
    def _cargar_datos(self) -> None:
        import pandas as pd
        ruta = RAIZ / "outputs" / "alertas.csv"
        if not ruta.exists():
            messagebox.showerror("Faltan datos", _falta("outputs/alertas.csv"))
            self.destroy(); sys.exit(1)
        self.df = pd.read_csv(ruta)
        self.df["alertas"] = self.df.alertas.fillna("")

        from src import alerts
        self.catalogo = alerts.catalogo()
        self.titulos = dict(zip(self.catalogo.clave, self.catalogo.titulo))

        geo = RAIZ / "outputs" / "geologia_m2020.csv"
        self.geo = pd.read_csv(geo) if geo.exists() else None

    # ---------------------------------------------------------------- estilo
    def _estilos(self) -> None:
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("TNotebook", background=GRIS, borderwidth=0)
        s.configure("TNotebook.Tab", padding=(20, 10), font=("Helvetica", 12))
        s.map("TNotebook.Tab", background=[("selected", "#ffffff")],
              foreground=[("selected", AZUL)])
        s.configure("TFrame", background="#ffffff")
        s.configure("Fondo.TFrame", background=GRIS)
        s.configure("TLabel", background="#ffffff", foreground=TINTA)
        s.configure("Tenue.TLabel", foreground=TENUE, font=("Helvetica", 11))
        s.configure("H2.TLabel", foreground=AZUL, font=("Helvetica", 15, "bold"))
        s.configure("KPI.TLabel", foreground=AZUL, font=("Helvetica", 26, "bold"))
        s.configure("Treeview.Heading", font=("Helvetica", 11, "bold"),
                    background="#e8ecf5", foreground=AZUL)
        s.configure("Treeview", rowheight=25, fieldbackground="#ffffff",
                    font=("Helvetica", 11))
        s.configure("TButton", font=("Helvetica", 11), padding=6)

    def _encabezado(self) -> None:
        barra = tk.Frame(self, bg=AZUL, height=86)
        barra.pack(fill="x"); barra.pack_propagate(False)
        izq = tk.Frame(barra, bg=AZUL); izq.pack(side="left", padx=20, pady=10)

        self._logos = []           # evita que el recolector libere las imágenes
        hay_logo = False
        for archivo in ("logo_externado.png", "logo_nasa.png"):
            p = RAIZ / "assets" / archivo
            if not p.exists():
                continue
            try:
                from PIL import Image, ImageTk
                im = Image.open(p).convert("RGBA")
                h = 56
                im = im.resize((max(1, int(im.width * h / im.height)), h), Image.LANCZOS)
                ph = ImageTk.PhotoImage(im)
                self._logos.append(ph)
                tk.Label(izq, image=ph, bg=AZUL).pack(side="left", padx=(0, 14))
                hay_logo = True
            except Exception:
                pass
        if not hay_logo:
            tk.Label(izq, text="Universidad Externado de Colombia\nMatemáticas — Ciencia de Datos",
                     bg=AZUL, fg="#ffffff", font=("Helvetica", 10), justify="left"
                     ).pack(side="left", padx=(0, 14))

        txt = tk.Frame(barra, bg=AZUL); txt.pack(side="left", padx=6)
        tk.Label(txt, text="Panel de análisis de terreno marciano", bg=AZUL, fg="#ffffff",
                 font=("Helvetica", 18, "bold")).pack(anchor="w")
        tk.Label(txt, text="Cobertura de roca, conteo de bloques y alertas de riesgo · Dataset AI4Mars",
                 bg=AZUL, fg="#c8d4ef", font=("Helvetica", 11)).pack(anchor="w")

    def _pie(self) -> None:
        pie = tk.Frame(self, bg=GRIS); pie.pack(fill="x", padx=18, pady=(0, 10))
        tk.Label(pie, bg=GRIS, fg=TENUE, font=("Helvetica", 9), justify="left",
                 text=("Datos: AI4Mars — Swan et al. (2021) · Imágenes: NASA/JPL-Caltech.   "
                       "Material académico: no constituye un producto oficial de la NASA "
                       "ni implica su respaldo.")).pack(anchor="w")

    # ---------------------------------------------------------------- utilidades
    def _tarjeta_kpi(self, padre, valor, etiqueta):
        c = tk.Frame(padre, bg="#ffffff", highlightbackground=GRIS_LN, highlightthickness=1)
        tk.Label(c, text=valor, bg="#ffffff", fg=AZUL,
                 font=("Helvetica", 24, "bold")).pack(padx=18, pady=(12, 0), anchor="w")
        tk.Label(c, text=etiqueta, bg="#ffffff", fg=TENUE,
                 font=("Helvetica", 10)).pack(padx=18, pady=(0, 12), anchor="w")
        return c

    def _lienzo(self, padre, figura):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        cv = FigureCanvasTkAgg(figura, master=padre)
        cv.draw()
        w = cv.get_tk_widget()
        w.configure(highlightthickness=1, highlightbackground=GRIS_LN)
        return w

    # ---------------------------------------------------------------- pestañas
    def _tab_resumen(self) -> None:
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt

        f = ttk.Frame(self.nb); self.nb.add(f, text="  Resumen  ")
        df, ok = self.df, self.df[self.df.quality_flag == "ok"]
        rb = df[df.rock_coverage_pct.fillna(0) > 0]

        fila = ttk.Frame(f); fila.pack(fill="x", padx=18, pady=(16, 6))
        kpis = [(f"{len(df):,}".replace(",", "."), "imágenes analizadas"),
                (f"{len(rb):,}".replace(",", "."), "con roca visible"),
                (f"{int(df.n_rocks.sum()):,}".replace(",", "."), "rocas contadas"),
                (f"{int((df.nivel_riesgo != 'sin_alerta').sum()):,}".replace(",", "."), "con alguna alerta"),
                (f"{int((df.nivel_riesgo == 'alto').sum()):,}", "en riesgo alto")]
        for v, e in kpis:
            self._tarjeta_kpi(fila, v, e).pack(side="left", expand=True, fill="both", padx=5)

        fig, ax = plt.subplots(1, 3, figsize=(12.4, 3.5), dpi=96)
        fig.patch.set_facecolor("#ffffff")
        ax[0].hist(rb.rock_coverage_pct.dropna(), bins=20, color=ROJO, alpha=.85)
        ax[0].set(title="Cobertura de roca (%)", ylabel="imágenes")
        esc = df[df.frac_valid > 0].scene_type.value_counts()
        ax[1].bar(esc.index, esc.values, color=AZUL, alpha=.85)
        ax[1].set(title="Tipología de escenas")
        ax[1].tick_params(axis="x", rotation=20)
        tam = [int(ok.n_small.sum()), int(ok.n_medium.sum()), int(ok.n_large.sum())]
        ax[2].bar(["Pequeña", "Mediana", "Grande"], tam, color=["#f2a08e", "#e8654a", ROJO])
        ax[2].set(title="Tamaño–frecuencia de rocas")
        for a in ax:
            a.spines[["top", "right"]].set_visible(False)
            a.grid(alpha=.25)
            a.title.set_fontsize(10)
        fig.tight_layout()
        self._lienzo(f, fig).pack(fill="both", expand=True, padx=18, pady=12)

    def _tab_alertas(self) -> None:
        import matplotlib.pyplot as plt
        f = ttk.Frame(self.nb); self.nb.add(f, text="  Alertas  ")
        df = self.df

        izq = ttk.Frame(f); izq.pack(side="left", fill="both", expand=True, padx=(18, 8), pady=14)
        ttk.Label(izq, text="Distribución de alertas", style="H2.TLabel").pack(anchor="w")

        fig, ax = plt.subplots(2, 1, figsize=(6.0, 5.6), dpi=96)
        fig.patch.set_facecolor("#ffffff")
        niv = df.nivel_riesgo.value_counts()
        ax[0].barh([NIVEL_TXT.get(k, k) for k in niv.index][::-1], niv.values[::-1],
                   color=[NIVEL_COLOR.get(k, AZUL) for k in niv.index][::-1])
        ax[0].set_title("Escenas por nivel de riesgo", fontsize=10)
        cnt = {self.titulos.get(c, c): int(df.alertas.str.contains(c).sum())
               for c in self.catalogo.clave}
        cnt = dict(sorted(cnt.items(), key=lambda x: x[1]))
        ax[1].barh(list(cnt), list(cnt.values()), color=ROJO, alpha=.85)
        ax[1].set_title("Alertas emitidas por tipo", fontsize=10)
        for a in ax:
            a.spines[["top", "right"]].set_visible(False)
            a.grid(axis="x", alpha=.25); a.tick_params(labelsize=8)
        fig.tight_layout()
        self._lienzo(izq, fig).pack(fill="both", expand=True, pady=8)

        der = ttk.Frame(f); der.pack(side="left", fill="both", expand=True, padx=(8, 18), pady=14)
        ttk.Label(der, text="Catálogo de reglas", style="H2.TLabel").pack(anchor="w")
        ttk.Label(der, style="Tenue.TLabel", wraplength=520, justify="left",
                  text=("Cada regla declara el umbral que la activa y el motivo que la "
                        "justifica, de modo que el criterio pueda discutirse y ajustarse.")
                  ).pack(anchor="w", pady=(2, 8))
        cont = tk.Frame(der, bg="#ffffff"); cont.pack(fill="both", expand=True)
        cv = tk.Canvas(cont, bg="#ffffff", highlightthickness=0)
        sb = ttk.Scrollbar(cont, orient="vertical", command=cv.yview)
        interior = tk.Frame(cv, bg="#ffffff")
        interior.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=interior, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        for _, r in self.catalogo.iterrows():
            b = tk.Frame(interior, bg="#ffffff", highlightbackground=GRIS_LN,
                         highlightthickness=1)
            b.pack(fill="x", pady=4, padx=2)
            cab = tk.Frame(b, bg="#ffffff"); cab.pack(fill="x", padx=12, pady=(9, 0))
            tk.Label(cab, text=r.titulo, bg="#ffffff", fg=AZUL,
                     font=("Helvetica", 11, "bold")).pack(side="left")
            sev = {3: ROJO, 2: "#e08214", 1: TENUE}[r.severidad]
            tk.Label(cab, text=f"severidad {r.severidad}/3", bg=sev, fg="#fff",
                     font=("Helvetica", 8, "bold"), padx=7).pack(side="right")
            tk.Label(b, text=f"Criterio: {r.criterio}", bg="#ffffff", fg=TINTA,
                     font=("Helvetica", 10), wraplength=470, justify="left"
                     ).pack(anchor="w", padx=12, pady=(4, 0))
            tk.Label(b, text=r.motivo, bg="#ffffff", fg=TENUE, font=("Helvetica", 9),
                     wraplength=470, justify="left").pack(anchor="w", padx=12, pady=(2, 10))

    def _tab_explorador(self) -> None:
        f = ttk.Frame(self.nb); self.nb.add(f, text="  Explorador de escenas  ")

        barra = ttk.Frame(f); barra.pack(fill="x", padx=18, pady=(14, 6))
        ttk.Label(barra, text="Nivel:", style="Tenue.TLabel").pack(side="left")
        self.filtro = tk.StringVar(value="alto")
        for n in ("alto", "medio", "bajo", "todos"):
            ttk.Radiobutton(barra, text=NIVEL_TXT.get(n, "Todos"), value=n,
                            variable=self.filtro, command=self._llenar_lista
                            ).pack(side="left", padx=6)
        ttk.Label(barra, style="Tenue.TLabel",
                  text="   Selecciona una escena para ver la imagen y sus indicadores."
                  ).pack(side="left")

        cuerpo = ttk.Frame(f); cuerpo.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        izq = ttk.Frame(cuerpo); izq.pack(side="left", fill="both", padx=(0, 12))
        cols = ("id", "nivel", "n")
        self.tabla = ttk.Treeview(izq, columns=cols, show="headings", height=24)
        for c, t, w in (("id", "Imagen", 250), ("nivel", "Nivel", 80), ("n", "Alertas", 65)):
            self.tabla.heading(c, text=t); self.tabla.column(c, width=w, anchor="w")
        sb = ttk.Scrollbar(izq, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        self.tabla.pack(side="left", fill="y"); sb.pack(side="left", fill="y")
        self.tabla.bind("<<TreeviewSelect>>", self._mostrar_escena)
        for niv, col in NIVEL_COLOR.items():
            self.tabla.tag_configure(niv, foreground=col)

        self.detalle = ttk.Frame(cuerpo); self.detalle.pack(side="left", fill="both", expand=True)
        self.msg = ttk.Label(self.detalle, style="Tenue.TLabel",
                             text="Selecciona una escena de la lista.")
        self.msg.pack(pady=40)
        self._lienzo_escena = None
        self._llenar_lista()

    def _llenar_lista(self) -> None:
        self.tabla.delete(*self.tabla.get_children())
        d = self.df[self.df.nivel_riesgo != "sin_alerta"]
        if self.filtro.get() != "todos":
            d = d[d.nivel_riesgo == self.filtro.get()]
        d = d.sort_values("n_alertas", ascending=False).head(400)
        for _, r in d.iterrows():
            self.tabla.insert("", "end", values=(r.image_id, NIVEL_TXT[r.nivel_riesgo],
                                                 r.n_alertas), tags=(r.nivel_riesgo,))

    def _mostrar_escena(self, _evt=None) -> None:
        sel = self.tabla.selection()
        if not sel:
            return
        image_id = self.tabla.item(sel[0])["values"][0]
        fila = self.df[self.df.image_id == image_id].iloc[0]

        for w in self.detalle.winfo_children():
            w.destroy()

        import numpy as np
        import matplotlib.pyplot as plt
        from src import config, mask_utils as mu, rock_count as rc

        cab = ttk.Frame(self.detalle); cab.pack(fill="x", pady=(4, 6))
        ttk.Label(cab, text=str(image_id), font=("Helvetica", 11, "bold")).pack(anchor="w")
        alertas = [self.titulos.get(a, a) for a in str(fila.alertas).split("|") if a]
        tk.Label(cab, text="  ·  ".join(alertas) or "—", bg="#ffffff",
                 fg=NIVEL_COLOR.get(fila.nivel_riesgo, TINTA), font=("Helvetica", 10, "bold"),
                 wraplength=640, justify="left").pack(anchor="w", pady=(2, 0))
        ind = (f"Cobertura {fila.rock_coverage_pct:.0f} %   ·   {int(fila.n_rocks)} rocas   ·   "
               f"roca mayor {fila.largest_rock_pct:.1f} %   ·   arena {fila.pct_sand:.0f} %   ·   "
               f"escena {fila.scene_type}")
        ttk.Label(cab, text=ind, style="Tenue.TLabel").pack(anchor="w", pady=(4, 0))

        mp = config.MSL_NCAM_LABELS_TRAIN / f"{image_id}.png"
        ip = mu.mask_to_image_path(mp)
        if ip is None or not mp.exists():
            ttk.Label(self.detalle, style="Tenue.TLabel",
                      text="No se encontró la imagen original; comprueba AI4MARS_ROOT."
                      ).pack(pady=20)
            return

        from PIL import Image
        gris = np.asarray(Image.open(ip).convert("L"))
        m = mu.read_mask(mp)
        rock = mu.big_rock_mask(m)
        s = rc.compute_stages(rock)
        kept = np.isin(s["labels_ws"], s["kept_ids"]) if s["kept_ids"] else np.zeros_like(rock)

        fig, ax = plt.subplots(1, 3, figsize=(11.2, 3.9), dpi=94)
        fig.patch.set_facecolor("#ffffff")
        ax[0].imshow(gris, cmap="gray"); ax[0].set_title("Imagen", fontsize=10)
        from src import viz
        ax[1].imshow(viz.mask_to_rgb(m)); ax[1].set_title("Anotación del terreno", fontsize=10)
        ax[2].imshow(gris, cmap="gray")
        ov = np.zeros((*rock.shape, 4)); ov[kept] = [1.0, .24, .13, .55]
        ax[2].imshow(ov)
        ax[2].set_title(f"Rocas detectadas: {int(fila.n_rocks)}", fontsize=10)
        for a in ax:
            a.axis("off")
        fig.tight_layout()
        self._lienzo(self.detalle, fig).pack(fill="both", expand=True)

    def _tab_geologia(self) -> None:
        f = ttk.Frame(self.nb); self.nb.add(f, text="  Geología (Perseverance)  ")
        if self.geo is None:
            ttk.Label(f, style="Tenue.TLabel", wraplength=700, justify="left",
                      text=("El análisis geológico no se ha ejecutado todavía.\n\n"
                            "Ejecuta:  python scripts/scan_geology.py")
                      ).pack(padx=30, pady=40, anchor="w")
            return
        import matplotlib.pyplot as plt
        g = self.geo
        con_veta = int(g.tiene_veta.sum())

        fila = ttk.Frame(f); fila.pack(fill="x", padx=18, pady=(16, 6))
        for v, e in [(f"{len(g):,}".replace(",", "."), "escenas analizadas"),
                     (f"{con_veta:,}".replace(",", "."), f"con vetas ({100*con_veta/len(g):.1f} %)"),
                     (f"{int((g.alerta_veta == 'veta_destacada').sum()):,}", "con veta destacada"),
                     (f"{int((g.pct_float_rock > 0).sum()):,}".replace(",", "."), "con bloques sueltos")]:
            self._tarjeta_kpi(fila, v, e).pack(side="left", expand=True, fill="both", padx=5)

        ttk.Label(f, style="Tenue.TLabel", wraplength=1100, justify="left",
                  text=("Las vetas son depósitos minerales precipitados por circulación de agua, "
                        "de modo que su presencia señala interés científico. Aparecen en una "
                        "fracción reducida de las escenas, lo que es esperable y no una "
                        "deficiencia: una alerta útil es, por definición, poco frecuente. Este "
                        "conjunto queda fuera del subconjunto declarado en la metodología y se "
                        "reporta como demostración de la extensibilidad del procedimiento.")
                  ).pack(anchor="w", padx=20, pady=(6, 4))

        fig, ax = plt.subplots(1, 2, figsize=(11.5, 3.4), dpi=96)
        fig.patch.set_facecolor("#ffffff")
        conveta = g[g.tiene_veta]
        if len(conveta):
            ax[0].hist(conveta.pct_veta, bins=30, color=AZUL, alpha=.85)
            ax[0].set(title="Extensión de la veta en las escenas que la contienen (%)",
                      ylabel="escenas")
        pres = {"Guijarros": int((g.pct_guijarros > 0).sum()),
                "Bloques sueltos": int((g.pct_float_rock > 0).sum()),
                "Lecho rocoso": int((g.pct_bedrock > 0).sum()),
                "Colinas": int((g.pct_colina > 0).sum()),
                "Vetas": con_veta}
        pres = dict(sorted(pres.items(), key=lambda x: x[1]))
        ax[1].barh(list(pres), list(pres.values()), color=ROJO, alpha=.85)
        ax[1].set_title("Presencia de rasgos geológicos", fontsize=10)
        for a in ax:
            a.spines[["top", "right"]].set_visible(False)
            a.grid(alpha=.25); a.title.set_fontsize(10); a.tick_params(labelsize=9)
        fig.tight_layout()
        self._lienzo(f, fig).pack(fill="both", expand=True, padx=18, pady=10)


if __name__ == "__main__":
    Panel().mainloop()
