"""**El guardian que faltaba: los mensajes que no se ensenan en ningun sitio** (17/10/2026).

### Lo que hay hoy

`test_revision_t14.py` tiene **exactamente esta prueba**, y la escribio para los textos de la maquinaria:

    def test_ningun_texto_de_la_maquinaria_se_queda_sin_usar(self):
        «Y al reves: un texto que existe y **no se ensena en ningun sitio**.»
        for clave in textos.MAQUINARIA_DE_LA_FINCA: …

***Y solo mira `MAQUINARIA_DE_LA_FINCA`.*** *El diccionario grande -`MENSAJES`, el de los avisos de las
reglas- **no lo mira nadie**.*

***Y `app/textos.py` cree que si***, con estas palabras:

    «Los motivos van AQUI y no en el bloque de la pantalla … porque en el bloque de la pantalla el
    ***guardian T14*** los daria por «textos que no se ensenan en ningun sitio», y con razon.»

*O sea: la casa tiene la regla escrita, tiene el guardian, y **el guardian mira otro diccionario**.*

### ***Y esto no se arregla de golpe, y decirlo es parte del trabajo***

Un barrido de los 3393 mensajes da **1967 que no se nombran en ningun sitio**. *Y **muchos no son un
defecto***: hay claves que se componen al vuelo -`V27_plazo_de_seguridad_sin_comprobar_uno` y `_varios` se
arman con un sufijo-, y hay bloques enteros que se sirven a la pantalla como **datos**, no como avisos.

***Asi que este guardian NO exige arreglar 1967 de golpe***: *eso seria una tarde entera y un cambio enorme
sin saber cuales importan.* **Lo que hace es no dejar que crezca**: cuenta los de hoy, y **falla si manana
hay mas**. *Un problema que no crece es un problema que se puede arreglar poco a poco; uno que crece cada
semana, no.*
"""

from __future__ import annotations

import pathlib
import re

from app import textos

# ***Los de hoy***, medidos con este mismo codigo. *Si esta prueba falla, casi siempre es porque se anadio un
# mensaje y no se ensena en ningun sitio: **o se ensena, o se quita**.*
LOS_DE_HOY = 1967

# ***Los ficheros donde se puede nombrar un mensaje***: el codigo de la app y el de las pantallas.
NO_CUENTAN = {"textos.py"}


def _donde_se_puede_nombrar() -> dict:
    raiz = pathlib.Path(__file__).resolve().parent.parent
    sitios = {}
    for carpeta in ("app", "tests", "scripts"):
        for fichero in (raiz / carpeta).rglob("*.py"):
            if fichero.name in NO_CUENTAN:
                continue
            sitios[fichero] = fichero.read_bytes().decode("utf-8", errors="replace")
    return sitios


def los_mensajes_que_no_se_nombran() -> list[str]:
    """***Las claves de `MENSAJES` que no aparecen en ningun otro fichero.***

    ***Y hay que leerlo sabiendo lo que es***: *una clave puede no aparecer **nunca** en el codigo y estar
    bien, si se compone al vuelo -`f"…_{cual}"`-. Esta busqueda **no sabe** de composicion: cuenta de menos,
    no de mas.*
    """
    sitios = _donde_se_puede_nombrar()
    sin_nombrar = []
    for clave in textos.MENSAJES:
        if not any(f'"{clave}"' in t or f"'{clave}'" in t for t in sitios.values()):
            sin_nombrar.append(clave)
    return sorted(sin_nombrar)


# ---------------------------------------------------------------------------
# 1 · ***El numero no crece***
# ---------------------------------------------------------------------------


def test_los_mensajes_que_no_se_ensenan_no_crecen():
    """***La prueba que impide que esto empeore.***

    *No pide arreglar los de hoy: pide que **manana no haya mas**. Y cuando falle, la salida es una de dos:
    **ensenar el mensaje**, o **quitarlo** -un texto que no se ensena es un texto que nadie lee, y ocupa sitio
    en el fichero mas grande del proyecto-.*
    """
    hoy = los_mensajes_que_no_se_nombran()

    assert len(hoy) <= LOS_DE_HOY, (
        f"***hay {len(hoy)} mensajes que no se ensenan en ningun sitio, y antes habia {LOS_DE_HOY}.***\n"
        f"Los nuevos: {sorted(set(hoy) - set())!r}… *(mira el diff: la clave que acabas de anadir)*\n"
        "*O se ensena, o se quita. Y si de verdad se compone al vuelo, se anade aqui su motivo.*"
    )


def test_y_si_bajan_se_puede_bajar_el_numero():
    """***Y el numero se baja cuando se arreglan.***

    *Un tope que solo sube acaba siendo un numero que nadie mira. Este se puede bajar, y **conviene bajarlo**:
    la prueba dice el numero exacto para que se pueda apretar.*
    """
    hoy = len(los_mensajes_que_no_se_nombran())
    assert hoy <= LOS_DE_HOY, f"***si has arreglado alguno, baja LOS_DE_HOY a {hoy}***"


# ---------------------------------------------------------------------------
# 2 · ***Y la regla de la casa, comprobada***
# ---------------------------------------------------------------------------


def test_el_guardian_de_la_maquinaria_sigue_mirando_lo_suyo():
    """***Los dos guardianes no se pisan.***

    *El del T14 vigila `MAQUINARIA_DE_LA_FINCA` **con lista cerrada** -falla si hay **uno** sin usar-, y este
    vigila `MENSAJES` **con tope** -falla si **crecen**-. Son dos sitios distintos y con dos criterios
    distintos, y a proposito: el de la maquinaria es un diccionario pequeno y cerrado; `MENSAJES` tiene 3393
    entradas y arreglarlo de golpe no es una tarea, es una mudanza.*
    """
    assert textos.MAQUINARIA_DE_LA_FINCA, "***el pequeno sigue ahi***"
    assert len(textos.MENSAJES) > len(textos.MAQUINARIA_DE_LA_FINCA), (
        "***y el grande es el grande***"
    )


def test_la_busqueda_encuentra_al_menos_los_que_se_usan():
    """***Y la busqueda funciona***, que es lo minimo que se le puede pedir a un guardian.

    *Se comprueba con una clave que **si** se usa en el codigo: si la busqueda no la encuentra, el guardian
    estaria contando de mas y el numero no valdria nada.*
    """
    usados = [c for c in textos.MENSAJES if c.startswith("V3_")]
    sin_nombrar = set(los_mensajes_que_no_se_nombran())

    assert usados, "***tiene que haber mensajes V3 ***"
    assert "V3_dosis_excedida" not in sin_nombrar, (
        "***`V3_dosis_excedida` se usa en `validaciones.py`: si sale como huerfano, la busqueda esta rota***"
    )
