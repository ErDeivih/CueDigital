"""Regenera la copia de los textos de la maquinaria que usa `tests_js/maquinaria.test.js`.

POR QUE HACE FALTA, Y POR QUE CON UN GUION Y NO A MANO

El test del movil (`tests_js/maquinaria.test.js`) no puede pedirle los textos al servidor: corre sin
servidor. Asi que lleva una **copia** de `textos.MAQUINARIA_DE_LA_FINCA`, y la revision del ticket
comprobo que estaba **abreviada**: 35 de sus 172 textos decian otra cosa que lo que sirve `/api/interfaz`,
y entre ellos estaban justo los tres que explican que **el programa no calcula la fecha**.

Todas las pantallas del proyecto tienen su prueba de que la copia dice lo mismo (`test_interfaz.py`), y
escribir 172 frases a mano es la forma de que vuelva a pasar. Esto las copia **del diccionario de verdad**,
en su orden, con `json.dumps` (que produce literales validos en JavaScript para texto).

Uso:

    python scripts/copiar_textos_t14.py [--comprobar]

Sin argumentos reescribe el bloque. Con `--comprobar` solo dice si esta al dia.
"""

from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
EL_TEST = RAIZ / "tests_js" / "maquinaria.test.js"
PRINCIPIO = "const MAQUINARIA = {"
FINAL = "\n};\n"


def bloque_generado() -> str:
    sys.path.insert(0, str(RAIZ))
    from app import textos

    lineas = [PRINCIPIO]
    lineas.append(
        "  // **Copia literal de `textos.MAQUINARIA_DE_LA_FINCA`.** Se rehace con"
    )
    lineas.append("  // `backend/scripts/copiar_textos_t14.py`, y la prueba de la revisión")
    lineas.append("  // (`tests/test_revision_t14.py`) exige que diga lo mismo que el servidor.")
    for clave, valor in textos.MAQUINARIA_DE_LA_FINCA.items():
        lineas.append(f"  {clave}: {json.dumps(valor, ensure_ascii=False)},")
    return "\n".join(lineas)


def main() -> int:
    solo_comprobar = "--comprobar" in sys.argv
    original = EL_TEST.read_text(encoding="utf-8")
    if PRINCIPIO not in original:
        print(f"no encuentro `{PRINCIPIO}` en {EL_TEST}")
        return 2
    antes, resto = original.split(PRINCIPIO, 1)
    _, despues = resto.split(FINAL, 1)
    nuevo = antes + bloque_generado() + FINAL + despues
    if nuevo == original:
        print("la copia ya esta al dia")
        return 0
    if solo_comprobar:
        print("la copia NO esta al dia")
        return 1
    EL_TEST.write_text(nuevo, encoding="utf-8")
    print(f"copiada en {EL_TEST} ({len(nuevo)} caracteres)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
