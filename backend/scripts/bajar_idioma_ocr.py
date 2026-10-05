"""Descarga el idioma español para el lector de fotos (Tesseract).

## Por qué hace falta

El lector de fotos (Tesseract) **no sabe leer español de fábrica**: hay que instalarle el idioma.
En el ordenador donde se probó esto, el programa estaba instalado pero solo con el inglés, y eso se
nota: los números —cantidades, precios, NIF, fechas— se leen bien (los dígitos no son de ningún
idioma), pero las palabras con tilde o con eñe salen cambiadas: «PEÑARANDA» se lee «Pefiaranda».

La aplicación **funciona igual sin esto** (avisa de que el lector va en inglés y el agricultor
corrige lo que haga falta), pero con el idioma español las facturas se leen mucho mejor.

## De dónde sale y qué se guarda

Del repositorio oficial de Tesseract, que es de donde salen los idiomas:

```
https://github.com/tesseract-ocr/tessdata_fast/blob/main/spa.traineddata
https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/spa.traineddata
```

Se usa `tessdata_fast` (2,3 MB) y no `tessdata_best` (13,6 MB) porque es la que recomienda el propio
proyecto para leer documentos normales: la diferencia de precisión es pequeña y la de tamaño, seis
veces. El fichero se guarda en `data/ocr/tessdata/spa.traineddata` y `app/ocr.py` lo usa si está
ahí (poniendo `TESSDATA_PREFIX`), **sin tocar la instalación del sistema**.

## Cómo se lanza

```bash
cd backend
../.venv/Scripts/python.exe scripts/bajar_idioma_ocr.py
```

Si el fichero ya está y su huella coincide, no hace nada. Si no coincide, se para y lo dice: un
idioma cambiado sin querer haría que las lecturas salieran raras y nadie sabría por qué.
"""

from __future__ import annotations

import hashlib
import pathlib

import httpx

URL = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/spa.traineddata"
# La huella de la copia que se descargó y se comprobó. Si el repositorio de Tesseract publica otra
# versión, esto no cuadrará y el guion lo dirá: es la señal de que hay que mirar qué ha cambiado
# antes de dar el fichero por bueno.
HUELLA_ESPERADA = "6f2e04d02774a18f01bed44b1111f2cd7f3ba7ac9dc4373cd3f898a40ea6b464"

DESTINO = pathlib.Path(__file__).resolve().parents[2] / "data" / "ocr" / "tessdata" / "spa.traineddata"


def main() -> int:
    if DESTINO.exists() and HUELLA_ESPERADA:
        actual = hashlib.sha256(DESTINO.read_bytes()).hexdigest()
        if actual == HUELLA_ESPERADA:
            print(f"Ya está descargado y coincide: {DESTINO}")
            return 0
        print(f"El fichero que hay NO coincide con la huella esperada:\n  {actual}")
        print("Míralo antes de seguir: puede ser una versión nueva del idioma.")
        return 1

    print(f"Descargando {URL}")
    respuesta = httpx.get(URL, timeout=120.0, follow_redirects=True)
    respuesta.raise_for_status()
    contenido = respuesta.content
    huella = hashlib.sha256(contenido).hexdigest()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_bytes(contenido)
    print(f"Escrito {DESTINO} ({len(contenido):,} bytes)")
    print(f"SHA-256: {huella}")
    if HUELLA_ESPERADA and huella != HUELLA_ESPERADA:
        print("Ojo: la huella no coincide con la que había apuntada en este guion.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
