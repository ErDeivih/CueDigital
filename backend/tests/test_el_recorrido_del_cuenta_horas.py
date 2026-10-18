"""**El cuenta-horas, andado desde la pantalla** (CRM-07 #8, 17/10/2026).

### ***Por que existe esta prueba***

`scripts/verificar_el_recorrido_del_cuenta_horas.py` **tiene 509 lineas** y cubre el encargo entero -los ocho
pasos, con el **formulario de verdad** y no la API-. Y **no lo corria nadie**: su nombre no aparecia en
ninguna prueba.

***Un guion que nadie ejecuta es una funcion que solo existe en el sitio donde se escribio.*** *El encargo lo
dice con esas palabras: «no declarar terminada una funcion que solo existe en servidor».*

***Y no se metio dentro de `test_el_recorrido_se_anda` a proposito***: *ese test acababa de empezar a pasar
despues de rondas en rojo, y anadirle un guion de 509 lineas encima el mismo dia **mezclaria dos causas** si
volvia a fallar.* **Este es su sitio: una prueba propia, con el mismo andamiaje prestado.**

***Los ayudantes se IMPORTAN, no se copian***: *`_un_puerto_libre`, `_esperar_al_servidor` y
`_lo_que_dijo_el_servidor` viven en el otro fichero y ya estan probados. Copiarlos seria tener dos versiones
de lo mismo, que es como acaban discrepando.*
"""

from __future__ import annotations

import pathlib
import subprocess
import tempfile

import pytest

from test_el_recorrido_se_anda import (  # noqa: E402  — el andamiaje, prestado
    BACKEND,
    PYTHON,
    _esperar_al_servidor,
    _hay_navegador,
    _lo_que_dijo_el_servidor,
    _un_puerto_libre,
)

EL_GUION = BACKEND / "scripts" / "verificar_el_recorrido_del_cuenta_horas.py"


@pytest.mark.skipif(not _hay_navegador(), reason="hace falta un navegador para andar la pantalla")
def test_el_cuenta_horas_se_anda_entero():
    """***Los ocho pasos del encargo, por los formularios.***

    *Una maquina sin lecturas → apuntar → segunda lectura → corregir → anular con su motivo → unidades que no
    son las mismas → el retroceso intermedio → y la recarga.* **Y el guion comprueba cada uno contra lo que
    se ve en la pantalla, no contra lo que el servidor dice que hay** -que es la diferencia entre una funcion
    y un campo.
    """
    assert EL_GUION.exists(), f"***falta el guion: {EL_GUION}***"
    puerto = _un_puerto_libre()
    direccion = f"http://127.0.0.1:{puerto}"
    with tempfile.TemporaryDirectory(
        prefix="cuedigital-cuenta-horas-",
        # ***Y el mismo motivo que en el otro test***: *en Windows, SQLite sigue con el fichero abierto un
        # instante despues de terminar el servidor, y borrar la carpeta fallaba **despues** de que el
        # recorrido hubiera pasado.*
        ignore_cleanup_errors=True,
    ) as temporal:
        base = pathlib.Path(temporal) / "prueba.db"
        entorno = dict(__import__("os").environ)
        entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"
        # ***Lo que dice el servidor, a un fichero***: *un fallo de arranque sin su causa no se puede
        # arreglar -y esta prueba se escribio justo despues de aprenderlo con la otra-.*
        log = pathlib.Path(temporal) / "servidor.log"
        salida_del_servidor = log.open("wb")
        servidor = subprocess.Popen(  # noqa: S603 — es el propio proyecto, no una orden de fuera
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(puerto)],
            cwd=str(BACKEND),
            env=entorno,
            stdout=salida_del_servidor,
            stderr=subprocess.STDOUT,
        )
        try:
            assert _esperar_al_servidor(direccion), (
                "el servidor de pruebas no ha arrancado. **Lo que dijo**:\n"
                + _lo_que_dijo_el_servidor(log)
            )
            recorrido = subprocess.run(  # noqa: S603
                [str(PYTHON), str(EL_GUION), direccion],
                cwd=str(BACKEND),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
            )
            assert recorrido.returncode == 0, (
                "***el cuenta-horas no se anda entero***:\n"
                + (recorrido.stdout or "")[-4000:]
                + (recorrido.stderr or "")[-1500:]
            )
            assert "Fallos: 0" in recorrido.stdout, (
                "el guion no dice que no haya fallos:\n" + (recorrido.stdout or "")[-1500:]
            )
        finally:
            servidor.terminate()
            salida_del_servidor.close()
            try:
                servidor.wait(timeout=15)
            except subprocess.TimeoutExpired:
                servidor.kill()


def test_el_guion_del_cuenta_horas_dice_lo_que_comprueba():
    """***Y el guion no se queda mudo.***

    *Un guion que anda y no dice cuantas cosas ha comprobado se puede quedar a medias sin que nadie lo note.
    La cabecera del fichero **enumera los ocho pasos**, y eso es lo que esta prueba defiende: que la lista
    siga estando. Si alguien anade un paso y no lo escribe, aqui no se entera; pero si alguien **quita** la
    lista -que es lo que paso con `apuntar_lectura`-, si.*
    """
    cabecera = EL_GUION.read_bytes().decode("utf-8")[:3000]

    assert "sin lecturas" in cabecera, "***el primer paso tiene que seguir contado***"
    assert "motivo" in cabecera, "***y el de anular, que es el que pide el contrato***"
    assert "formularios" in cabecera, (
        "***y que se anda por los formularios: es lo que el revisor dejo dicho***"
    )
