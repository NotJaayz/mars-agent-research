#!/usr/bin/env python
"""Panel de análisis de terreno marciano — aplicación de escritorio.

Producto final del trabajo: interfaz gráfica que reúne los indicadores por imagen, el
sistema de alertas de riesgo y un explorador de escenas, sin necesidad de ejecutar código
ni de conocer el detalle del procedimiento.

Se ejecuta con:

    python app.py

Requiere ``customtkinter`` (``pip install customtkinter``); el resto —matplotlib, pandas,
Pillow— ya lo utiliza el proyecto.

Paleta institucional de la NASA: azul #0B3D91 y rojo #FC3D21, sobre fondo oscuro.
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

try:
    import customtkinter as ctk
except ImportError:
    print("Falta customtkinter. Instálalo con:\n    pip install customtkinter")
    sys.exit(1)

# --- Paleta ---------------------------------------------------------------------------
AZUL = "#0B3D91"          # azul institucional de la NASA
AZUL_CLARO = "#5b8ede"
ROJO = "#FC3D21"          # rojo institucional de la NASA
FONDO = "#0f1319"
TARJETA = "#171d29"
BORDE = "#252d3d"
TEXTO = "#e8eaf0"
TENUE = "#98a1b3"
NIVEL_COLOR = {"alto": ROJO, "medio": "#e8963c", "bajo": "#d4b13f", "sin_alerta": "#4aa06b"}
NIVEL_TXT = {"alto": "Alto", "medio": "Medio", "bajo": "Bajo", "sin_alerta": "Sin alerta"}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


def _miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


class Panel(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Panel de análisis de terreno marciano — AI4Mars")
        self.geometry("1320x860")
        self.minsize(1120, 740)
        self.configure(fg_color=FONDO)

        self._cargar_datos()
        self._estilo_tabla()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._barra_lateral()

        self.contenido = ctk.CTkFrame(self, fg_color=FONDO, corner_radius=0)
        self.contenido.grid(row=0, column=1, sticky="nsew", padx=(0, 18), pady=18)
        self.contenido.grid_columnconfigure(0, weight=1)
        self.contenido.grid_rowconfigure(0, weight=1)

        self._vistas: dict[str, ctk.CTkFrame] = {}
        self._mostrar("resumen")
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    def _cerrar(self) -> None:
        """Cierre ordenado: libera las figuras antes de destruir la ventana."""
        try:
            import matplotlib.pyplot as plt
            plt.close("all")
        except Exception:
            pass
        self.quit()
        self.destroy()

    # ---------------------------------------------------------------- datos
    def _cargar_datos(self) -> None:
        import pandas as pd
        ruta = RAIZ / "outputs" / "alertas.csv"
        if not ruta.exists():
            messagebox.showerror(
                "Faltan datos",
                "No se encontró outputs/alertas.csv.\n\nGenera los resultados antes:\n"
                "    python scripts/run_pipeline.py\n    python scripts/run_alerts.py")
            self.destroy(); sys.exit(1)
        self.df = pd.read_csv(ruta)
        self.df["alertas"] = self.df.alertas.fillna("")

        from src import alerts
        self.catalogo = alerts.catalogo()
        self.titulos = dict(zip(self.catalogo.clave, self.catalogo.titulo))

        geo = RAIZ / "outputs" / "geologia_m2020.csv"
        self.geo = pd.read_csv(geo) if geo.exists() else None

    def _estilo_tabla(self) -> None:
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Oscuro.Treeview", background=TARJETA, fieldbackground=TARJETA,
                    foreground=TEXTO, rowheight=27, borderwidth=0,
                    font=("Helvetica", 11))
        s.configure("Oscuro.Treeview.Heading", background="#1f2736", foreground=AZUL_CLARO,
                    font=("Helvetica", 11, "bold"), borderwidth=0)
        s.map("Oscuro.Treeview", background=[("selected", AZUL)],
              foreground=[("selected", "#ffffff")])

    # ---------------------------------------------------------------- navegación
    def _barra_lateral(self) -> None:
        lat = ctk.CTkFrame(self, width=232, corner_radius=0, fg_color="#0a0d13")
        lat.grid(row=0, column=0, sticky="nsew")
        lat.grid_propagate(False)

        logo = RAIZ / "assets" / "logo_nasa.png"
        if logo.exists():
            try:
                from PIL import Image
                im = Image.open(logo)
                h = 74
                self._logo = ctk.CTkImage(light_image=im, dark_image=im,
                                          size=(round(im.width * h / im.height), h))
                ctk.CTkLabel(lat, image=self._logo, text="").pack(pady=(26, 10))
            except Exception:
                pass

        ctk.CTkLabel(lat, text="Análisis de terreno\nmarciano", text_color=TEXTO,
                     font=ctk.CTkFont(size=16, weight="bold"), justify="center"
                     ).pack(pady=(2, 2))
        ctk.CTkLabel(lat, text="Dataset AI4Mars", text_color=TENUE,
                     font=ctk.CTkFont(size=11)).pack(pady=(0, 22))

        self._botones = {}
        for clave, texto in [("resumen", "Resumen"), ("alertas", "Alertas"),
                             ("explorador", "Explorador de escenas"),
                             ("geologia", "Geología")]:
            b = ctk.CTkButton(lat, text=texto, anchor="w", height=40, corner_radius=8,
                              fg_color="transparent", text_color=TEXTO,
                              hover_color="#16203a", font=ctk.CTkFont(size=13),
                              command=lambda c=clave: self._mostrar(c))
            b.pack(fill="x", padx=14, pady=3)
            self._botones[clave] = b

        pie = ctk.CTkLabel(
            lat, text=("Universidad Externado\nde Colombia\nMatemáticas — Ciencia de Datos\n\n"
                       "Datos: AI4Mars\nNASA/JPL-Caltech\n\n"
                       "Material académico: no es\nun producto oficial de la\nNASA ni implica su respaldo."),
            text_color=TENUE, font=ctk.CTkFont(size=9), justify="left")
        pie.pack(side="bottom", pady=18, padx=14, anchor="w")

    def _mostrar(self, clave: str) -> None:
        for c, b in self._botones.items():
            b.configure(fg_color=AZUL if c == clave else "transparent")
        for v in self._vistas.values():
            v.grid_forget()
        if clave not in self._vistas:
            constructor = {"resumen": self._vista_resumen, "alertas": self._vista_alertas,
                           "explorador": self._vista_explorador,
                           "geologia": self._vista_geologia}[clave]
            self._vistas[clave] = constructor()
        self._vistas[clave].grid(row=0, column=0, sticky="nsew")

    # ---------------------------------------------------------------- utilidades
    def _titulo(self, padre, texto, sub=None) -> None:
        ctk.CTkLabel(padre, text=texto, text_color=TEXTO,
                     font=ctk.CTkFont(size=21, weight="bold")).pack(anchor="w", pady=(0, 2))
        if sub:
            ctk.CTkLabel(padre, text=sub, text_color=TENUE, font=ctk.CTkFont(size=12),
                         justify="left", wraplength=880).pack(anchor="w", pady=(0, 14))

    def _kpi(self, padre, valor, etiqueta):
        c = ctk.CTkFrame(padre, fg_color=TARJETA, corner_radius=12,
                         border_width=1, border_color=BORDE)
        ctk.CTkLabel(c, text=valor, text_color=AZUL_CLARO,
                     font=ctk.CTkFont(size=27, weight="bold")).pack(padx=20, pady=(14, 0), anchor="w")
        ctk.CTkLabel(c, text=etiqueta, text_color=TENUE,
                     font=ctk.CTkFont(size=11)).pack(padx=20, pady=(0, 14), anchor="w")
        return c

    def _figura(self, ancho, alto, filas=1, cols=1):
        """Crea una figura de matplotlib con el estilo oscuro de la interfaz."""
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(filas, cols, figsize=(ancho, alto), dpi=96)
        fig.patch.set_facecolor(TARJETA)
        ejes = ax if isinstance(ax, (list, tuple)) else (ax.ravel() if hasattr(ax, "ravel") else [ax])
        for a in ejes:
            a.set_facecolor(TARJETA)
            a.tick_params(colors=TENUE, labelsize=8.5)
            for lado in ("bottom", "left"):
                a.spines[lado].set_color(BORDE)
            a.spines[["top", "right"]].set_visible(False)
            a.grid(alpha=.14, color=TENUE)
            a.title.set_color(TEXTO); a.title.set_fontsize(10)
            a.xaxis.label.set_color(TENUE); a.yaxis.label.set_color(TENUE)
        return fig, ax

    def _lienzo(self, padre, fig):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        cv = FigureCanvasTkAgg(fig, master=padre)
        cv.draw()
        return cv.get_tk_widget()

    # ---------------------------------------------------------------- vistas
    def _vista_resumen(self):
        v = ctk.CTkScrollableFrame(self.contenido, fg_color=FONDO)
        self._titulo(v, "Resumen",
                     "Indicadores derivados de las anotaciones por píxel de la cámara de "
                     "navegación del rover Curiosity.")
        df, ok = self.df, self.df[self.df.quality_flag == "ok"]
        rb = df[df.rock_coverage_pct.fillna(0) > 0]

        fila = ctk.CTkFrame(v, fg_color=FONDO); fila.pack(fill="x", pady=(0, 16))
        for val, et in [(_miles(len(df)), "imágenes analizadas"),
                        (_miles(len(rb)), "con roca visible"),
                        (_miles(int(df.n_rocks.sum())), "rocas contadas"),
                        (_miles(int((df.nivel_riesgo != "sin_alerta").sum())), "con alguna alerta"),
                        (str(int((df.nivel_riesgo == "alto").sum())), "en riesgo alto")]:
            self._kpi(fila, val, et).pack(side="left", expand=True, fill="both", padx=4)

        fig, ax = self._figura(12.6, 3.4, 1, 3)
        ax[0].hist(rb.rock_coverage_pct.dropna(), bins=20, color=ROJO, alpha=.9)
        ax[0].set(title="Cobertura de roca (%)", ylabel="imágenes")
        esc = df[df.frac_valid > 0].scene_type.value_counts()
        ax[1].bar(esc.index, esc.values, color=AZUL_CLARO, alpha=.9)
        ax[1].set(title="Tipología de escenas"); ax[1].tick_params(axis="x", rotation=18)
        ax[2].bar(["Pequeña", "Mediana", "Grande"],
                  [int(ok.n_small.sum()), int(ok.n_medium.sum()), int(ok.n_large.sum())],
                  color=["#f0907c", "#e8654a", ROJO])
        ax[2].set(title="Tamaño–frecuencia de rocas")
        fig.tight_layout()
        self._lienzo(v, fig).pack(fill="x", pady=6)
        return v

    def _vista_alertas(self):
        v = ctk.CTkScrollableFrame(self.contenido, fg_color=FONDO)
        self._titulo(v, "Alertas de riesgo",
                     "Avisos operativos derivados de los indicadores. Cada regla declara el "
                     "umbral que la activa y el motivo que la justifica, de modo que el "
                     "criterio pueda discutirse y ajustarse.")
        df = self.df
        fig, ax = self._figura(12.6, 4.4, 1, 2)
        niv = df.nivel_riesgo.value_counts()
        ax[0].barh([NIVEL_TXT.get(k, k) for k in niv.index][::-1], niv.values[::-1],
                   color=[NIVEL_COLOR.get(k, AZUL_CLARO) for k in niv.index][::-1])
        ax[0].set_title("Escenas por nivel de riesgo")
        cnt = {self.titulos.get(c, c): int(df.alertas.str.contains(c).sum())
               for c in self.catalogo.clave}
        cnt = dict(sorted(cnt.items(), key=lambda x: x[1]))
        ax[1].barh(list(cnt), list(cnt.values()), color=ROJO, alpha=.9)
        ax[1].set_title("Alertas emitidas por tipo")
        fig.tight_layout()
        self._lienzo(v, fig).pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(v, text="Catálogo de reglas", text_color=TEXTO,
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(4, 8))
        for _, r in self.catalogo.iterrows():
            t = ctk.CTkFrame(v, fg_color=TARJETA, corner_radius=10,
                             border_width=1, border_color=BORDE)
            t.pack(fill="x", pady=4)
            cab = ctk.CTkFrame(t, fg_color="transparent"); cab.pack(fill="x", padx=16, pady=(11, 0))
            ctk.CTkLabel(cab, text=r.titulo, text_color=AZUL_CLARO,
                         font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
            col = {3: ROJO, 2: "#e8963c", 1: TENUE}[r.severidad]
            ctk.CTkLabel(cab, text=f" severidad {r.severidad}/3 ", fg_color=col,
                         text_color="#ffffff", corner_radius=6,
                         font=ctk.CTkFont(size=10, weight="bold")).pack(side="right")
            ctk.CTkLabel(t, text=f"Criterio: {r.criterio}", text_color=TEXTO,
                         font=ctk.CTkFont(size=11), justify="left", wraplength=880
                         ).pack(anchor="w", padx=16, pady=(6, 0))
            ctk.CTkLabel(t, text=r.motivo, text_color=TENUE, font=ctk.CTkFont(size=11),
                         justify="left", wraplength=880).pack(anchor="w", padx=16, pady=(3, 12))
        return v

    def _vista_explorador(self):
        v = ctk.CTkFrame(self.contenido, fg_color=FONDO)
        cab = ctk.CTkFrame(v, fg_color=FONDO); cab.pack(fill="x")
        self._titulo(cab, "Explorador de escenas",
                     "Selecciona una escena señalada para ver la imagen original, la "
                     "anotación del terreno y las rocas detectadas.")

        barra = ctk.CTkFrame(v, fg_color=FONDO); barra.pack(fill="x", pady=(0, 10))
        self.filtro = ctk.StringVar(value="alto")
        seg = ctk.CTkSegmentedButton(
            barra, values=["Alto", "Medio", "Bajo", "Todos"],
            command=self._cambiar_filtro, fg_color=TARJETA, selected_color=AZUL,
            selected_hover_color=AZUL_CLARO, unselected_color=TARJETA,
            text_color=TEXTO, font=ctk.CTkFont(size=12))
        seg.set("Alto"); seg.pack(side="left")
        self.contador = ctk.CTkLabel(barra, text="", text_color=TENUE,
                                     font=ctk.CTkFont(size=11))
        self.contador.pack(side="left", padx=14)

        cuerpo = ctk.CTkFrame(v, fg_color=FONDO); cuerpo.pack(fill="both", expand=True)
        izq = ctk.CTkFrame(cuerpo, fg_color=TARJETA, corner_radius=10,
                           border_width=1, border_color=BORDE, width=360)
        izq.pack(side="left", fill="y", padx=(0, 12)); izq.pack_propagate(False)
        self.tabla = ttk.Treeview(izq, columns=("id", "niv", "n"), show="headings",
                                  style="Oscuro.Treeview", height=26)
        for c, t, w in (("id", "Imagen", 214), ("niv", "Nivel", 74), ("n", "Alertas", 58)):
            self.tabla.heading(c, text=t); self.tabla.column(c, width=w, anchor="w")
        sb = ttk.Scrollbar(izq, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        self.tabla.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb.pack(side="right", fill="y", pady=8)
        self.tabla.bind("<<TreeviewSelect>>", self._mostrar_escena)
        for niv, col in NIVEL_COLOR.items():
            self.tabla.tag_configure(niv, foreground=col)

        self.detalle = ctk.CTkFrame(cuerpo, fg_color=TARJETA, corner_radius=10,
                                    border_width=1, border_color=BORDE)
        self.detalle.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(self.detalle, text="Selecciona una escena de la lista",
                     text_color=TENUE, font=ctk.CTkFont(size=13)).pack(pady=50)
        self._llenar_lista()
        return v

    def _cambiar_filtro(self, valor: str) -> None:
        self.filtro.set({"Alto": "alto", "Medio": "medio", "Bajo": "bajo",
                         "Todos": "todos"}[valor])
        self._llenar_lista()

    def _llenar_lista(self) -> None:
        self.tabla.delete(*self.tabla.get_children())
        d = self.df[self.df.nivel_riesgo != "sin_alerta"]
        if self.filtro.get() != "todos":
            d = d[d.nivel_riesgo == self.filtro.get()]
        total = len(d)
        d = d.sort_values("n_alertas", ascending=False).head(400)
        for _, r in d.iterrows():
            self.tabla.insert("", "end", tags=(r.nivel_riesgo,),
                              values=(r.image_id, NIVEL_TXT[r.nivel_riesgo], r.n_alertas))
        self.contador.configure(
            text=f"{_miles(total)} escenas" + (f" · se muestran las 400 primeras"
                                               if total > 400 else ""))

    def _mostrar_escena(self, _evt=None) -> None:
        sel = self.tabla.selection()
        if not sel:
            return
        image_id = self.tabla.item(sel[0])["values"][0]
        fila = self.df[self.df.image_id == image_id].iloc[0]
        for w in self.detalle.winfo_children():
            w.destroy()

        import numpy as np
        from src import config, mask_utils as mu, rock_count as rc, viz

        ctk.CTkLabel(self.detalle, text=str(image_id), text_color=TEXTO,
                     font=ctk.CTkFont(size=13, weight="bold")
                     ).pack(anchor="w", padx=16, pady=(12, 2))
        alertas = [self.titulos.get(a, a) for a in str(fila.alertas).split("|") if a]
        chips = ctk.CTkFrame(self.detalle, fg_color="transparent")
        chips.pack(anchor="w", padx=16, pady=(0, 4))
        for a in alertas:
            ctk.CTkLabel(chips, text=f" {a} ", fg_color=NIVEL_COLOR.get(fila.nivel_riesgo, AZUL),
                         text_color="#fff", corner_radius=6,
                         font=ctk.CTkFont(size=10, weight="bold")).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(self.detalle, text_color=TENUE, font=ctk.CTkFont(size=11),
                     text=(f"Cobertura {fila.rock_coverage_pct:.0f} %   ·   "
                           f"{int(fila.n_rocks)} rocas   ·   roca mayor "
                           f"{fila.largest_rock_pct:.1f} %   ·   arena {fila.pct_sand:.0f} %   ·   "
                           f"escena {fila.scene_type}")).pack(anchor="w", padx=16, pady=(2, 6))

        mp = config.MSL_NCAM_LABELS_TRAIN / f"{image_id}.png"
        ip = mu.mask_to_image_path(mp)
        if ip is None or not mp.exists():
            ctk.CTkLabel(self.detalle, text_color=TENUE, font=ctk.CTkFont(size=12),
                         text="No se encontró la imagen original; comprueba AI4MARS_ROOT."
                         ).pack(pady=24)
            return

        from PIL import Image
        gris = np.asarray(Image.open(ip).convert("L"))
        m = mu.read_mask(mp)
        rock = mu.big_rock_mask(m)
        s = rc.compute_stages(rock)
        kept = np.isin(s["labels_ws"], s["kept_ids"]) if s["kept_ids"] else np.zeros_like(rock)

        fig, ax = self._figura(10.6, 3.8, 1, 3)
        ax[0].imshow(gris, cmap="gray"); ax[0].set_title("Imagen")
        ax[1].imshow(viz.mask_to_rgb(m)); ax[1].set_title("Anotación del terreno")
        ax[2].imshow(gris, cmap="gray")
        ov = np.zeros((*rock.shape, 4)); ov[kept] = [0.99, .24, .13, .58]
        ax[2].imshow(ov); ax[2].set_title(f"Rocas detectadas: {int(fila.n_rocks)}")
        for a in ax:
            a.axis("off")
        fig.tight_layout()
        self._lienzo(self.detalle, fig).pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _vista_geologia(self):
        v = ctk.CTkScrollableFrame(self.contenido, fg_color=FONDO)
        self._titulo(v, "Rasgos geológicos — Perseverance",
                     "Extensión al conjunto Mars 2020, cuya taxonomía distingue rasgos que "
                     "la escala de navegación no recoge, entre ellos las vetas minerales.")
        if self.geo is None:
            ctk.CTkLabel(v, text_color=TENUE, justify="left", font=ctk.CTkFont(size=12),
                         text=("El análisis geológico no se ha ejecutado todavía.\n\n"
                               "Ejecuta:   python scripts/scan_geology.py")).pack(anchor="w")
            return v

        g = self.geo
        con_veta = int(g.tiene_veta.sum())
        fila = ctk.CTkFrame(v, fg_color=FONDO); fila.pack(fill="x", pady=(0, 14))
        for val, et in [(_miles(len(g)), "escenas analizadas"),
                        (_miles(con_veta), f"con vetas ({100*con_veta/len(g):.1f} %)"),
                        (str(int((g.alerta_veta == "veta_destacada").sum())), "con veta destacada"),
                        (_miles(int((g.pct_float_rock > 0).sum())), "con bloques sueltos")]:
            self._kpi(fila, val, et).pack(side="left", expand=True, fill="both", padx=4)

        nota = ctk.CTkFrame(v, fg_color="#1b2333", corner_radius=10,
                            border_width=1, border_color=AZUL)
        nota.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(nota, text_color=TEXTO, justify="left", wraplength=900,
                     font=ctk.CTkFont(size=11),
                     text=("Las vetas son depósitos minerales precipitados por circulación de "
                           "agua, de modo que su presencia señala interés científico. Aparecen "
                           "en una fracción reducida de las escenas, lo que es esperable y no "
                           "una deficiencia: una alerta útil es, por definición, poco frecuente. "
                           "Este conjunto queda fuera del subconjunto declarado en la "
                           "metodología y se reporta como demostración de extensibilidad.")
                     ).pack(anchor="w", padx=16, pady=12)

        fig, ax = self._figura(12.6, 3.4, 1, 2)
        cv = g[g.tiene_veta]
        if len(cv):
            ax[0].hist(cv.pct_veta, bins=30, color=AZUL_CLARO, alpha=.9)
            ax[0].set(title="Extensión de la veta donde aparece (% del área)", ylabel="escenas")
        pres = {"Guijarros": int((g.pct_guijarros > 0).sum()),
                "Bloques sueltos": int((g.pct_float_rock > 0).sum()),
                "Lecho rocoso": int((g.pct_bedrock > 0).sum()),
                "Colinas": int((g.pct_colina > 0).sum()), "Vetas": con_veta}
        pres = dict(sorted(pres.items(), key=lambda x: x[1]))
        ax[1].barh(list(pres), list(pres.values()), color=ROJO, alpha=.9)
        ax[1].set_title("Presencia de rasgos geológicos")
        fig.tight_layout()
        self._lienzo(v, fig).pack(fill="x", pady=4)
        return v


if __name__ == "__main__":
    Panel().mainloop()
