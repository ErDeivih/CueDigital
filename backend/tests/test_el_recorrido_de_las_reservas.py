"""**Las reservas, andadas desde la pantalla** (CRM-07 #9, 17/10/2026).

### ***Por que existe esta prueba***

`scripts/verificar_el_recorrido_de_las_reservas.py` **tiene 267 lineas** y cubre el encargo entero -los ocho
pasos, con el **formulario de verdad** y no la API-. Y **no lo correria nadie**: su nombre no apareceria en
ninguna prueba.

***Un guion que nadie ejecuta es una funcion que solo existe en el sitio donde se escribio.*** *El encargo lo
dice con esas palabras: «no declarar terminada una funcion que solo existe en servidor», y una reserva que
solo se puede apuntar por la API **es exactamente eso**.*

***Y hay una comprobacion que solo se puede hacer asi***: *que **anular una reserva de verdad libera la
maquina**. No basta con que el estado diga «anulada» -eso ya lo prueba `test_las_reservas_por_las_puertas`-:
lo que hay que ver es que **el mismo tramo se puede volver a reservar**. Eso, desde la pantalla, es esta
prueba.*

***Los ayudantes se IMPORTAN, no se copian***: *`_un_puerto_libre`, `_esperar_al_servidor` y
`_lo_que_dijo_el_servidor` viven en `test_el_recorrido_se_anda` y ya estan probados.*
"""

from __future__ import annotations

import os
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

EL_GUION = BACKEND / "scripts" / "verificar_el_recorrido_de_las_reservas.py"


@pytest.mark.skipif(not _hay_navegador(), reason="hace falta un navegador para andar la pantalla")
def test_las_reservas_se_andan_enteras():
    """***Los ocho pasos, por los formularios.***

    *Sin reservas → reservar → **el solape lo para el servidor** → otra maquina si se puede → corregir →
    anular con su motivo → **y el mismo tramo se puede reservar otra vez** → y la recarga.*
    **El guion comprueba cada cosa contra lo que se ve en la pantalla**, no contra lo que el servidor dice
    que hay -que es la diferencia entre una funcion y un campo-.
    """
    assert EL_GUION.exists(), f"***falta el guion: {EL_GUION}***"
    puerto = _un_puerto_libre()
    direccion = f"http://127.0.0.1:{puerto}"
    with tempfile.TemporaryDirectory(
        prefix="cuedigital-reservas-",
        # *En Windows, SQLite sigue con el fichero abierto un instante despues de terminar el servidor.*
        ignore_cleanup_errors=True,
    ) as temporal:
        base = pathlib.Path(temporal) / "prueba.db"
        entorno = dict(os.environ)
        entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"
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
                "***las reservas no se andan enteras***:\n"
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


def test_el_guion_de_las_reservas_dice_lo_que_comprueba():
    """***Y el guion no se queda mudo.***

    *La cabecera **enumera los ocho pasos**, y eso es lo que esta prueba defiende: que la lista siga
    estando.* **Y la frase que no puede desaparecer es la de la cola** -«Reserva para planificar no es
    consumo»-, porque es la que dice **que un apunte de planificacion no es un gasto**.
    """
    cabecera = EL_GUION.read_bytes().decode("utf-8")[:3000]

    assert "no es consumo" in cabecera, "***la frase de la cola tiene que seguir contada***"
    assert "solape" in cabecera, "***y el solape, que es lo que el encargo pide que pare el servidor***"
    assert "formularios" in cabecera, (
        "***y que se anda por los formularios: es lo que el revisor dejo dicho***"
    )
