#!/usr/bin/env python
"""Genera tesis/references.bib a partir de los metadatos oficiales de cada DOI.

La fuente de verdad es tesis/referencias.json: una clave por referencia con su DOI (o la
entrada completa si no tiene DOI). Para cada DOI se consulta Crossref o, si no lo registra
(Zenodo, arXiv), DataCite, y se construye la entrada BibTeX con autores, título, revista,
volumen, número, páginas y año tal como figuran en el registro oficial. Así la bibliografía
no depende de transcripciones manuales, y la auditoría se puede repetir en cualquier momento.

Los títulos se protegen para el formato APA 7 de biblatex-apa, que los pasa a minúscula
inicial: se encierran entre llaves los acrónimos, los nombres propios de misiones y lugares
y las palabras con mayúsculas internas.

Uso:  python scripts/generar_bibliografia.py [--cache outputs/bib_cache.json]
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

H = {"User-Agent": "thesis-bibliography/1.0 (mailto:noreply@example.org)"}

# Nombres propios de una sola palabra que deben conservar la mayúscula en APA.
PROPIOS = {
    "Mars", "Martian", "Moon", "Earth", "Curiosity", "Spirit", "Opportunity", "Perseverance",
    "Zhurong", "InSight", "Viking", "Gusev", "Gale", "Arequipa", "Peru", "Serengeti", "Mastcam",
    "Python", "NumPy", "SciPy", "Tianwen-1", "Chang'E-3", "Chang’E-3", "Chang'e-3", "Jackknife",
    "Oasis", "Kappa", "U-Net", "RSU-Net",
}
# Nombres propios de varias palabras (misiones, instrumentos, proyectos, lugares).
FRASES = [
    "Mars Science Laboratory", "Mars Exploration Rovers", "Mars Exploration Rover",
    "Navigation and Terrain Cameras", "Navigation and Terrain Camera", "Sloan Digital Sky Survey",
    "Galaxy Zoo", "Segment Anything", "Home Plate", "Winter Haven", "Utopia Planitia",
    "Meridiani Planum", "Mechanical Turk", "Mars Hand Lens Imager",
]


def _get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30))


def crossref(doi):
    return _get("https://api.crossref.org/works/" + urllib.parse.quote(doi))["message"]


def datacite(doi):
    return _get("https://api.datacite.org/dois/" + urllib.parse.quote(doi))["data"]["attributes"]


def limpiar(t):
    t = html.unescape(re.sub(r"<[^>]+>", "", t or ""))
    t = re.sub(r"[\u2600-\u27BF]", "", t)        # símbolos decorativos del registro (p. ej. ★)
    t = t.replace("‐", "-").replace("‑", "-").replace("–", "--").replace("—", "---")
    return re.sub(r"\s+", " ", t).strip()


def proteger(titulo):
    """Encierra entre llaves lo que no debe pasar a minúscula en APA."""
    letras = [c for c in titulo if c.isalpha()]
    if letras and sum(c.isupper() for c in letras) / len(letras) > 0.8:
        titulo = titulo.capitalize()          # título entero en mayúsculas en el origen
    titulo = titulo.rstrip(".")
    marcas = {}
    for i, f in enumerate(sorted(FRASES, key=len, reverse=True)):
        if re.search(re.escape(f), titulo, flags=re.I):
            marcas[f"@@{i}@@"] = "{" + f + "}"
            titulo = re.sub(re.escape(f), f"@@{i}@@", titulo, flags=re.I)

    def parte(w):
        if not w or w.startswith("@@"):
            return False
        acronimo = sum(c.isupper() for c in w) >= 2 or (any(c.isdigit() for c in w) and any(c.isupper() for c in w))
        return w in PROPIOS or acronimo or any(c.isupper() for c in w[1:])

    def una(p):
        nucleo = p.strip(".,:;()?!\"'")
        if not nucleo or nucleo.startswith("@@"):
            return p
        if nucleo in PROPIOS:
            return p.replace(nucleo, "{" + nucleo + "}", 1)
        if "-" in nucleo:
            # Palabras compuestas: se protege cada parte por separado, de modo que
            # "Mars-Like" quede "{Mars}-like" y "U-Shaped" conserve la U.
            partes = nucleo.split("-")
            nuevas = ["{" + x + "}" if parte(x) or (len(x) == 1 and x.isupper()) else x
                      for x in partes]
            return p.replace(nucleo, "-".join(nuevas), 1)
        if parte(nucleo):
            return p.replace(nucleo, "{" + nucleo + "}", 1)
        return p
    out = " ".join(una(p) for p in titulo.split(" "))
    for k, v in marcas.items():
        out = out.replace(k, v)
    return out


def escapar(s):
    return s.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")


def autores_cr(m):
    out = []
    for a in m.get("author", []):
        if "family" in a:
            out.append(f"{a['family']}, {a.get('given', '')}".strip().rstrip(","))
        elif "name" in a:
            out.append("{" + a["name"] + "}")
    return " and ".join(out)


TIPO_CR = {"journal-article": "article", "proceedings-article": "inproceedings",
           "book-chapter": "incollection", "book": "book", "posted-content": "online"}


def entrada(clave, spec):
    if "manual" in spec:
        m = dict(spec["manual"]); tipo = m.pop("tipo")
        campos = {k: v for k, v in m.items()}
        return tipo, campos, "manual"
    doi = spec["doi"]
    try:
        m = crossref(doi); fuente = "Crossref"
        tipo = spec.get("tipo") or TIPO_CR.get(m.get("type"), "article")
        if tipo == "preprint":
            tipo = "online"
        campos = {"author": autores_cr(m), "title": proteger(escapar(limpiar((m.get("title") or [""])[0]))),
                  "year": str(m["issued"]["date-parts"][0][0])}
        cont = limpiar((m.get("container-title") or [""])[0])
        if tipo == "article":
            campos["journal"] = escapar(cont)
        elif tipo in ("inproceedings", "incollection"):
            campos["booktitle"] = escapar(cont)
        if tipo == "book" and m.get("publisher"):
            campos["publisher"] = m["publisher"]
        for k_cr, k_bib in (("volume", "volume"), ("issue", "number")):
            if m.get(k_cr):
                campos[k_bib] = m[k_cr]
        pag = m.get("page") or m.get("article-number")
        if pag:
            campos["pages"] = pag.replace("-", "--") if "-" in pag and "--" not in pag else pag
    except urllib.error.HTTPError:
        a = datacite(doi); fuente = "DataCite"
        tipo = {"dataset": "dataset", "preprint": "online"}.get(spec.get("tipo"), "online")
        campos = {"author": " and ".join(c.get("name", "") for c in a["creators"]),
                  "title": proteger(escapar(limpiar(a["titles"][0]["title"]))),
                  "year": str(a["publicationYear"])}
        if a.get("publisher"):
            campos["publisher"] = a["publisher"] if isinstance(a["publisher"], str) else a["publisher"].get("name", "")
        if a.get("version"):
            campos["version"] = a["version"]
        if "arxiv" in doi.lower():
            campos["eprint"] = doi.split("arXiv.")[-1]; campos["eprinttype"] = "arXiv"
    campos["doi"] = doi
    campos.update(spec.get("corregir", {}))
    campos = {k: v for k, v in campos.items() if v is not None}   # null en "corregir" elimina el campo
    return tipo, campos, fuente


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fuente", default="tesis/referencias.json")
    ap.add_argument("--out", default="tesis/references.bib")
    args = ap.parse_args()
    refs = {k: v for k, v in json.load(open(args.fuente)).items() if not k.startswith("_")}
    bloques, informe = [], []
    for clave, spec in refs.items():
        tipo, campos, fuente = entrada(clave, spec)
        campos.setdefault("langid", "english" if fuente != "manual" else "spanish")
        orden = ["author", "title", "titleaddon", "journal", "booktitle", "publisher", "edition",
                 "version", "volume", "number", "pages", "year", "eprint", "eprinttype", "doi",
                 "url", "urldate", "langid"]
        cuerpo = ",\n".join(f"  {k:<10s} = {{{campos[k]}}}" for k in orden if k in campos)
        bloques.append(f"@{tipo}{{{clave},\n{cuerpo}\n}}")
        n_aut = len(campos.get("author", "").split(" and ")) if campos.get("author") else 0
        informe.append((clave, fuente, tipo, campos.get("year"), n_aut))
        time.sleep(0.3)
    cab = ("% =============================================================\n"
           "% ARCHIVO GENERADO — no editar a mano.\n"
           "% Fuente: tesis/referencias.json · Generador: scripts/generar_bibliografia.py\n"
           "% Metadatos tomados de Crossref y DataCite a partir de cada DOI.\n"
           "% =============================================================\n\n")
    Path(args.out).write_text(cab + "\n\n".join(bloques) + "\n")
    for clave, fuente, tipo, year, n in informe:
        print(f"  {clave:28s} {fuente:9s} {tipo:14s} {year}  {n} autores")
    print(f"-> {args.out}  ({len(bloques)} entradas)")


if __name__ == "__main__":
    main()
