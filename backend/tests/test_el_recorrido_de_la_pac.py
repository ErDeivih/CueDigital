"""**La preparacion de la PAC, andada desde la pantalla** (CRM-09, 17/10/2026).

### ***Por que existe esta prueba***

*El paquete tenia puerta -con sus cinco pruebas de Python- **y no tenia pantalla**. Se le hizo la pantalla
(`web/react/pantallas/pac.js`, con sus seis pruebas de JS)... **y faltaba lo de siempre: que alguien la ande**.*

***Un guion que nadie ejecuta es una funcion que solo existe en el sitio donde se escribio.***

***Y hay una cosa que solo se puede comprobar asi***: *que **el aviso de que no hay fuente legal se lea ANTES
del resumen**. En el componente se puede mirar el orden de las cadenas; en la pantalla, despues de pintar, se
mira **el texto que ve el agricultor** -y ahi es donde importa-.*

***Los ayudantes se IMPORTAN, no se copian***: *`_un_puerto_libre`, `_esperar_al_servidor` y
`_lo_que_dijo_el_servidor` viven en `test_el_recorrido_se_anda`.*
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

EL_GUION = BACKEND / "scripts" / "verificar_el_recorrido_de_la_pac.py"


@pytest.mark.skipif(not _hay_navegador(), reason="hace falta un navegador para andar la pantalla")
def test_la_preparacion_de_la_pac_se_anda_desde_la_pantalla():
    """***El paquete, por su pantalla, y contrastado con su puerta.***

    *Lo primero: el aviso de que no se puede decir si algo es elegible. **Lo segundo: el porcentaje con su
    numerador y su denominador** -o que no se sabe, nunca un cero-. **Y al pie, siempre**: que no es la
    declaracion.*
    """
    assert EL_GUION.exists(), f"***falta el guion: {EL_GUION}***"
    puerto = _un_puerto_libre()
    direccion = f"http://127.0.0.1:{puerto}"
    with tempfile.TemporaryDirectory(
        prefix="cuedigital-pac-",
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
                "***la preparacion de la PAC no se anda entera***:\n"
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


def test_el_guion_de_la_pac_dice_lo_que_comprueba():
    """***Y el guion no se queda mudo.***

    *La cabecera enumera los cinco pasos, y la frase que no puede desaparecer es la de la cola: **«no envio
    directo ni garantia de elegibilidad»**, porque es la que dice que esto **no es la declaracion**.*
    """
    cabecera = EL_GUION.read_bytes().decode("utf-8")[:3000]

    # ***Se busca en minusculas***: *la cabecera lo escribe con mayuscula -«No envio directo…»-, y buscar la
    # forma exacta es buscar una cadena que no esta -el fallo era de la prueba-.*
    assert "no envio directo ni garantia de elegibilidad" in cabecera.lower(), (
        "***la frase de la cola tiene que seguir contada***"
    )
    assert "numerador" in cabecera and "denominador" in cabecera, (
        "***y los porcentajes con numerador y denominador, que es lo que pide el contrato***"
    )
    assert "incompleto" in cabecera, "***y lo que falta, que es lo que hace incompleto el paquete***"
