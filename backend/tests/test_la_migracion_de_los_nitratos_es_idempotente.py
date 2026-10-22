"""***La migracion de los nitratos, pasada dos veces*** (22/10/2026, D06).

*El encargo pide «migracion **idempotente** ensayada». La suite de aceptacion prueba que el **esquema** se puede
reconstruir dos veces sin cambiar nada; **lo que no estaba probado es que pasar la migracion de datos dos veces deje
los datos iguales**.*

***Y no vale con una base nueva***: *en una base nueva la columna que la migracion arregla **ya esta bien**. Hay que
partir del **esquema de una instalacion vieja** -con la columna `NOT NULL` y los «no» inventados dentro-, que es
justo lo que construye `test_aceptacion_copia_y_migracion.py`. **Se reutiliza, no se copia.***
"""

from __future__ import annotations

import importlib.util
import pathlib
import sqlite3
import subprocess
import sys

import pytest

RAIZ_BACKEND = pathlib.Path(__file__).resolve().parent.parent
EL_GUION = RAIZ_BACKEND / "scripts" / "migrar_zona_de_nitratos.py"
LA_ACEPTACION = RAIZ_BACKEND / "tests" / "test_aceptacion_copia_y_migracion.py"


def _la_aceptacion():
    """*Las herramientas de la suite de aceptacion, cargadas como modulo.*"""
    especificacion = importlib.util.spec_from_file_location("la_aceptacion_para_las_pruebas", LA_ACEPTACION)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def _las_zonas(ruta: pathlib.Path) -> list[tuple]:
    """***Lo que se compara***: el «si o no» de cada apunte, en orden.

    *La columna se llama **`en_zona_vulnerable`** -lo dice `COLUMNA` en el guion-, no `zona_vulnerable_nitratos`,
    que es la de la **tierra**. Se supo porque la primera version devolvia la lista vacia: **la consulta fallaba y el
    `except` se la tragaba**.*
    """
    conexion = sqlite3.connect(ruta)
    try:
        las_filas = []
        for tabla in ("tratamientos", "fertilizaciones"):
            try:
                las_filas += [
                    (tabla, fila[0], fila[1])
                    for fila in conexion.execute(
                        f"SELECT id, en_zona_vulnerable FROM {tabla} ORDER BY id"
                    )
                ]
            except sqlite3.OperationalError:
                continue
        return las_filas
    finally:
        conexion.close()


def _migrar(ruta: pathlib.Path) -> int:
    """*Se pasa la migracion de verdad, como la pasaria quien la usara.*"""
    return subprocess.run(  # noqa: S603
        [sys.executable, str(EL_GUION), "--base", str(ruta), "--migrar"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).returncode


def test_la_migracion_de_los_nitratos_pasada_dos_veces_deja_lo_mismo(tmp_path):
    la_aceptacion = _la_aceptacion()
    la_ruta = tmp_path / "cuedigital.db"
    # ***El esquema de una instalacion vieja***: *la columna `NOT NULL` y el «no» que puso el programa.*
    el_motor = la_aceptacion._motor_con_las_columnas_todavia_obligatorias(la_ruta)
    # ***La tierra NO sabe si esta en zona de nitratos***: *ese es el caso que la migracion arregla. Con la tierra
    # diciendo «no» -`False`-, el «no» del tratamiento **es legitimo** y la migracion no lo toca: se probo, y no
    # movia ninguna fila. **El defecto existia cuando el «no» lo puso el programa, no el agricultor.***
    la_aceptacion._meter_una_finca_de_verdad(el_motor, la_tierra_sabe_si_esta_en_zona=None)
    el_motor.dispose()

    las_antes = _las_zonas(la_ruta)
    assert las_antes, f"la prueba necesita apuntes que migrar: {las_antes}"
    assert any(fila[2] in (0, "0", False) for fila in las_antes), (
        f"y tiene que haber alguno que diga «no»: {las_antes}"
    )

    # ---- la primera pasada: cambia lo que tiene que cambiar ----
    assert _migrar(la_ruta) == 0, "la primera pasada tiene que terminar bien"
    las_tras_la_primera = _las_zonas(la_ruta)
    assert las_tras_la_primera != las_antes, "la primera pasada tiene que mover el «no» inventado"

    # ---- ***la segunda: NO puede cambiar nada*** ----
    assert _migrar(la_ruta) == 0, "la segunda pasada tiene que terminar bien"
    las_tras_la_segunda = _las_zonas(la_ruta)
    assert las_tras_la_segunda == las_tras_la_primera, (
        f"***la migracion tiene que ser IDEMPOTENTE***: paso de {las_tras_la_primera} "
        f"a {las_tras_la_segunda}"
    )
