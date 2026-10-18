"""**El panel de la finca, andado desde la pantalla** (CRM-11, 17/10/2026).

### ***Por que existe esta prueba***

*El panel tenia puerta -con sus seis pruebas de Python-, pantalla (`LasMetricas` en el inicio, con sus cuatro
pruebas de JS)... **y faltaba lo de siempre: que alguien la ande**.*

***Un guion que nadie ejecuta es una funcion que solo existe en el sitio donde se escribio.***

***Y hay una cosa que solo se comprueba asi***: *que **las metricas se piden aparte** al abrir el inicio y
**llegan despues** de que la pantalla se pinte. En el componente se puede mirar el HTML; en la pantalla se mira
**lo que ve el agricultor cuando llega**, que es lo que importa -y si la peticion no se hiciera, la seccion no
saldria nunca y ninguna prueba de unidad lo notaria-.*

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

EL_GUION = BACKEND / "scripts" / "verificar_el_recorrido_del_panel.py"


@pytest.mark.skipif(not _hay_navegador(), reason="hace falta un navegador para andar la pantalla")
def test_las_metricas_del_panel_se_ven_en_el_inicio():
    """***Las metricas, en el inicio, con lo que hace falta para creerselas.***

    *Cada una dice **en que se mide**, **de donde sale** y **cuanto ha mirado**; lo que no se sabe se dice con
    su palabra -y nunca con un cero-; y se avisa de que **las cifras no se suman**.*
    """
    assert EL_GUION.exists(), f"***falta el guion: {EL_GUION}***"
    puerto = _un_puerto_libre()
    direccion = f"http://127.0.0.1:{puerto}"
    with tempfile.TemporaryDirectory(
        prefix="cuedigital-panel-",
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
                "***las metricas del panel no se ven en el inicio***:\n"
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


def test_el_guion_del_panel_dice_lo_que_comprueba():
    """***Y el guion no se queda mudo.***

    *La cabecera enumera los cinco pasos, y las frases que no pueden desaparecer son las del contrato: **la
    unidad, la fuente y la cobertura** -lo que hace que un numero se pueda defender-, y **que las cifras no se
    suman**.*
    """
    cabecera = EL_GUION.read_bytes().decode("utf-8")[:3000].lower()

    assert "unidad" in cabecera and "fuente" in cabecera, (
        "***«un numero que no puede decir su fuente no se puede discutir»***"
    )
    assert "cobertura" in cabecera, "***y cuanto ha mirado, que es lo que impide un total que parece completo***"
    assert "no se suman" in cabecera, (
        "***y que las que contestan a preguntas distintas no se suman***"
    )
