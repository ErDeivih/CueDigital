"""Rehace las tablas de nitrógeno de la Orden MAV/398/2022 desde el PDF del BOCyL.

Desde ``backend``::

    ../.venv/Scripts/python.exe scripts/bajar_nitratos_cyl.py

Para reproducir sin red con el PDF oficial guardado en el proyecto, ``--sin-descarga``.
No interpreta los periodos relativos como fechas de calendario ni rellena casillas vacías.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

import pdfplumber

FUENTE_URL = "https://bocyl.jcyl.es/boletines/2022/05/05/pdf/BOCYL-D-05052022-1.pdf"
RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "data" / "nitratos_cyl"
FUENTE_PDF = CARPETA / "Orden_MAV_398_2022.pdf"
SALIDA = CARPETA / "limites_y_periodos_mav_398_2022.json"


def _espacios(valor: str | None) -> str:
    return " ".join((valor or "").split())


def _maximo(celda: str | None) -> float | None:
    """Lee el resultado de la expresión impresa, conservando esta íntegra en `texto`."""
    texto = _espacios(celda)
    if not texto:
        return None
    cuenta = re.search(r"=\s*(\d+(?:[.,]\d+)?)", texto)
    primero = re.match(r"(\d+(?:[.,]\d+)?)\b", texto)
    encontrado = cuenta or primero
    if not encontrado:
        raise ValueError(f"No se reconoce la cifra del Anexo III: {texto!r}")
    return float(encontrado.group(1).replace(",", "."))


def extraer(pdf: Path, *, descargado_el: str) -> dict:
    bytes_pdf = pdf.read_bytes()
    if not bytes_pdf.startswith(b"%PDF"):
        raise ValueError("El fichero descargado no es un PDF")
    with pdfplumber.open(pdf) as documento:
        if len(documento.pages) < 25:
            raise ValueError("La orden no incluye las páginas de los anexos III y V")
        pagina_iii = documento.pages[22]
        pagina_v = documento.pages[24]
        texto_iii = pagina_iii.extract_text() or ""
        texto_v = pagina_v.extract_text() or ""
        if "ANEXO III" not in texto_iii or "ANEXO V" not in texto_v:
            raise ValueError("Las páginas de los anexos han cambiado; revisar el PDF")
        tablas_iii = pagina_iii.extract_tables()
        tablas_v = pagina_v.extract_tables()
        if len(tablas_iii) != 1 or len(tablas_v) != 1:
            raise ValueError("Ha cambiado la estructura de las tablas del BOCyL")
        filas_iii = tablas_iii[0]
        filas_v = tablas_v[0]
        if [_espacios(x) for x in filas_iii[1]] != ["Cultivo", "", "Secano", "Regadío"]:
            raise ValueError("Ha cambiado la cabecera de aportes máximos")
        if [_espacios(x) for x in filas_v[0]] != [
            "Tipo de cultivo", "Fertilizantes orgánicos", "Fertilizantes inorgánicos o minerales"
        ]:
            raise ValueError("Ha cambiado la cabecera de periodos")

        aportes = []
        grupo = ""
        for fila in filas_iii[2:]:
            if len(fila) != 4:
                raise ValueError(f"Fila inesperada en Anexo III: {fila!r}")
            grupo = _espacios(fila[0]) or grupo
            cultivo = _espacios(fila[1])
            if not cultivo:
                raise ValueError(f"Cultivo vacío en Anexo III: {fila!r}")
            secano = _espacios(fila[2])
            regadio = _espacios(fila[3])
            aportes.append({
                "grupo": grupo,
                "cultivo": cultivo,
                "secano": {"maximo_kg_n_ha": _maximo(secano), "texto": secano} if secano else None,
                "regadio": {"maximo_kg_n_ha": _maximo(regadio), "texto": regadio} if regadio else None,
                "fuente": "Anexo III, BOCyL p. 20895",
            })

        periodos = []
        for fila in filas_v[1:]:
            if len(fila) != 3:
                raise ValueError(f"Fila inesperada en Anexo V: {fila!r}")
            cultivo, organicos, minerales = map(_espacios, fila)
            if not all((cultivo, organicos, minerales)):
                raise ValueError(f"Periodo incompleto en Anexo V: {fila!r}")
            periodos.append({
                "grupo_cultivos": cultivo,
                "fertilizantes_organicos": organicos,
                "fertilizantes_inorganicos_o_minerales": minerales,
                "fuente": "Anexo V, BOCyL p. 20897",
            })

        # Son notas y definiciones del propio PDF; se conservan como texto para no
        # sustituir las condiciones legales por un cálculo nuestro.
        pagina_i = documento.pages[20].extract_text() or ""
        if "Tipo A:" not in pagina_i or "Tipo B:" not in pagina_i or "Tipo C:" not in pagina_i:
            raise ValueError("Faltan las definiciones de tipos A/B/C del Anexo I")
        tipos = {}
        for clave, siguiente in (("A", "B"), ("B", "C"), ("C", None)):
            inicio = pagina_i.index(f"Tipo {clave}:")
            fin = pagina_i.index(f"Tipo {siguiente}:", inicio) if siguiente else pagina_i.index("CV:", inicio)
            tipos[clave] = _espacios(pagina_i[inicio:fin])

    if len(aportes) != 22 or len(periodos) != 6:
        raise ValueError(f"Número inesperado de filas: {len(aportes)} aportes, {len(periodos)} periodos")
    return {
        "_leeme": "DERIVADO del PDF oficial por scripts/bajar_nitratos_cyl.py; no editar las cifras a mano.",
        "orden": "MAV/398/2022, de 29 de abril",
        "fuente_url": FUENTE_URL,
        "descargado_el": descargado_el,
        "fuente_sha256": hashlib.sha256(bytes_pdf).hexdigest(),
        "fuente_bytes": len(bytes_pdf),
        "aportes_maximos": aportes,
        "periodos_prohibidos": periodos,
        "tipos_fertilizante_organico": tipos,
        "advertencias": [
            "Una casilla vacía del Anexo III queda en null: no significa límite cero ni ausencia de límite.",
            "El Anexo III permite ajustar por cosecha esperada y remite a la guía MAPA para otros cultivos.",
            "El Anexo V contiene periodos relativos y excepciones; no se calculan fechas automáticamente.",
            "Estas tablas se aplican en zonas vulnerables; falta el listado municipal oficial verificable.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sin-descarga", action="store_true", help="Usar el PDF oficial ya guardado")
    argumentos = parser.parse_args()
    CARPETA.mkdir(parents=True, exist_ok=True)
    if not argumentos.sin_descarga:
        import httpx

        respuesta = httpx.get(FUENTE_URL, timeout=90, follow_redirects=True)
        respuesta.raise_for_status()
        if not respuesta.content.startswith(b"%PDF"):
            raise ValueError("La URL oficial no devolvió un PDF")
        FUENTE_PDF.write_bytes(respuesta.content)
    elif not FUENTE_PDF.is_file():
        raise FileNotFoundError(FUENTE_PDF)
    datos = extraer(FUENTE_PDF, descargado_el=dt.date.today().isoformat())
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Fuente: {FUENTE_URL}")
    print(f"SHA-256: {datos['fuente_sha256']}")
    print(f"Anexo III: {len(datos['aportes_maximos'])} cultivos; Anexo V: {len(datos['periodos_prohibidos'])} grupos")
    print(f"Guardado: {SALIDA}")


if __name__ == "__main__":
    main()
