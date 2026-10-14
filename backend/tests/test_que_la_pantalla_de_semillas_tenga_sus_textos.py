"""Que la pantalla de semillas y el servidor hablen del MISMO juego de textos (14/10/2026).

**POR QUE EXISTE.** El 14/10/2026 un subagente encontro un punto ciego de verdad: *ningun* test
comprobaba que cada rotulo que pide la pantalla (`frase(s.algo)` en `react/pantallas/semillas.js`)
exista en el diccionario que el servidor sirve (`textos.SEMILLAS`). El guardian de los textos
(`test_que_no_falte_ningun_texto`) no lo ve porque su expresion regular busca `t("x")` y
`mensaje("x")`, y la pantalla usa `s.<clave>`.

**Y no es teorico**: una clave que falta **no da error**, da un **rotulo en blanco** — un campo sin
nombre en la ficha, que es peor que un fallo, porque nadie se entera. Esto es lo mismo que le paso
a `papeles` en el envoltorio de la tierra (CRM-06): el dato estaba y la pantalla no lo ensenaba.

Este test cierra esa costura: **lo que la pantalla pide, el servidor lo tiene.**
"""

from __future__ import annotations

import pathlib
import re

from app import textos

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PANTALLA = RAIZ / "web" / "react" / "pantallas" / "semillas.js"


def _lo_que_pide_la_pantalla() -> set[str]:
    """Las claves que la pantalla de semillas lee del servidor, por su nombre (`s.<clave>`)."""
    fuente = PANTALLA.read_bytes().decode("utf-8")
    return set(re.findall(r"\bs\.([a-z_][a-z_0-9]*)", fuente))


def test_la_pantalla_de_semillas_pide_rotulos_y_el_servidor_los_tiene():
    pide = _lo_que_pide_la_pantalla()
    assert pide, "la pantalla no pide ningun rotulo: la expresion no esta mirando donde debe"
    faltan = sorted(c for c in pide if c not in textos.SEMILLAS)
    assert not faltan, (
        "la pantalla pide rotulos que el servidor NO sirve (saldrian en blanco, sin dar error): "
        + ", ".join(faltan)
    )


def test_y_ninguno_de_esos_rotulos_esta_vacio():
    # Un rotulo servido pero vacio es el mismo fallo con otro disfraz.
    pide = _lo_que_pide_la_pantalla()
    vacios = sorted(c for c in pide if not str(textos.SEMILLAS.get(c, "")).strip())
    assert not vacios, "rotulos vacios en el servidor: " + ", ".join(vacios)


def test_los_dos_campos_nuevos_tienen_su_rotulo_y_su_opcion_de_no_consta():
    # CRM-07 #2: los dos campos, con «No consta» como la opcion que dice que no se sabe.
    for clave in ("categoria_semilla", "procedencia"):
        assert textos.SEMILLAS.get(clave), f"falta el rotulo de {clave}"
        assert textos.SEMILLAS.get(f"{clave}_pista"), f"falta la pista de {clave}"
        assert textos.SEMILLAS.get(f"{clave}_no_consta"), f"falta el «No consta» de {clave}"
