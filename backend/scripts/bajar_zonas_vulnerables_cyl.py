"""Deriva el CSV municipal del Excel oficial de IDECyL y la tabla de provincias INE."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
import io
import json
import re
from pathlib import Path

import httpx
import openpyxl

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "data" / "zv_cyl_fuentes"
EXCEL = CARPETA / "coad_cyl_vulnerab_nitrat.xlsx"
INE = CARPETA / "cod_provincia.htm"
CSV = RAIZ / "data" / "zv_cyl.csv"
PROCEDENCIA = CARPETA / "procedencia.json"
REGISTRO = "https://idecyl.jcyl.es/geonetwork/static/api/records/spagobcylsoscoavulnitz20"
URL_EXCEL = "https://opendata.jcyl.es/ficheros/carto/medioambiente/sostenibilidad/coad_cyl_vulnerab_nitrat.xlsx"
URL_INE = "https://www.ine.es/daco/daco42/codmun/cod_provincia.htm"
CODIGOS_CYL = {"05", "09", "24", "34", "37", "40", "42", "47", "49"}


def provincias_del_ine(pagina: bytes) -> dict[str, str]:
    texto = pagina.decode("utf-8", errors="replace")
    parejas = re.findall(
        r"<tr>\s*<td>\s*(\d{2})\s*</td>\s*<td>\s*([^<]+?)\s*</td>",
        texto, flags=re.I | re.S,
    )
    provincias = {codigo: html.unescape(nombre).strip() for codigo, nombre in parejas}
    if set(provincias) < CODIGOS_CYL:
        raise ValueError("La tabla INE no contiene todas las provincias de Castilla y León")
    return {codigo: provincias[codigo] for codigo in CODIGOS_CYL}


def extraer(excel: bytes, pagina_ine: bytes) -> tuple[str, tuple[str, ...]]:
    if not excel.startswith(b"PK"):
        raise ValueError("El fichero de IDECyL no es un libro Excel")
    provincias = provincias_del_ine(pagina_ine)
    libro = openpyxl.load_workbook(io.BytesIO(excel), read_only=True, data_only=True)
    if libro.sheetnames != ["zonas_vulnerables_2020"]:
        raise ValueError("Han cambiado las hojas del libro oficial")
    filas = libro.active.values
    if tuple(next(filas)) != ("cod_municipal", "municipio", "zona_vulnerable", "superficie_m2"):
        raise ValueError("Han cambiado las columnas del libro oficial")

    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(("municipio", "provincia", "codigo_ine", "zona_vulnerable"))
    vistos: set[str] = set()
    zonas: set[str] = set()
    for codigo, municipio, zona, superficie in filas:
        codigo = str(codigo or "").strip()
        municipio = str(municipio or "").strip()
        zona = str(zona or "").strip()
        if not re.fullmatch(r"\d{5}", codigo) or codigo[:2] not in provincias:
            raise ValueError(f"Código municipal inesperado: {codigo!r}")
        if codigo in vistos or not municipio or not zona or not isinstance(superficie, (int, float)):
            raise ValueError(f"Fila incompleta o duplicada: {codigo!r}")
        vistos.add(codigo)
        zonas.add(zona)
        escritor.writerow((municipio, provincias[codigo[:2]], codigo, zona))
    libro.close()
    if len(vistos) != 387 or len(zonas) != 24:
        raise ValueError(f"La fuente ha cambiado: {len(vistos)} municipios y {len(zonas)} zonas")
    return salida.getvalue(), tuple(sorted(zonas))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sin-descarga", action="store_true", help="Rehacer desde las copias oficiales conservadas")
    argumentos = parser.parse_args()
    CARPETA.mkdir(parents=True, exist_ok=True)
    if not argumentos.sin_descarga:
        excel = httpx.get(URL_EXCEL, timeout=60, follow_redirects=True)
        excel.raise_for_status()
        ine = httpx.get(URL_INE, timeout=60, follow_redirects=True)
        ine.raise_for_status()
        EXCEL.write_bytes(excel.content)
        INE.write_bytes(ine.content)
        fecha = dt.date.today().isoformat()
    else:
        fecha = json.loads(PROCEDENCIA.read_text(encoding="utf-8"))["descargado_el"]
    bytes_excel = EXCEL.read_bytes()
    bytes_ine = INE.read_bytes()
    csv_derivado, zonas = extraer(bytes_excel, bytes_ine)
    CSV.write_text(csv_derivado, encoding="utf-8", newline="")
    PROCEDENCIA.write_text(json.dumps({
        "_leeme": "Derivado reproducible; no editar el listado municipal a mano.",
        "registro_fuente": REGISTRO,
        "fuente_excel": URL_EXCEL,
        "fuente_ine": URL_INE,
        "descargado_el": fecha,
        "fuente_excel_sha256": hashlib.sha256(bytes_excel).hexdigest(),
        "fuente_ine_sha256": hashlib.sha256(bytes_ine).hexdigest(),
        "municipios": 387,
        "zonas": len(zonas),
        "zonas_nombres": zonas,
        "marco": "Decreto 5/2020; metadatos de IDECyL revisados el 10/02/2026",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("387 municipios y 24 zonas extraídos del Excel de IDECyL")
    print(f"SHA-256 del Excel: {hashlib.sha256(bytes_excel).hexdigest()}")


if __name__ == "__main__":
    main()
