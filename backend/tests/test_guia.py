"""El cuaderno guiado: qué toca hacer y a partir de cuándo (10/11/2026).

Lo que se comprueba aquí es **solo la cuenta**, con fechas fijas: no hay servidor, ni base de
datos, ni depende de qué día se ejecute. Las reglas que se atan:

- un plazo que termina **hoy** no es lo mismo que uno que terminó ayer (y los dos se dicen);
- **tres días o menos es aviso**, y eso está en una constante para no tenerlo escrito en tres sitios;
- **nada se inventa**: sin plazo apuntado no hay aviso, y sin cultivo se dice pero **sin fecha**;
- el orden pone delante lo que corre prisa.
"""

from __future__ import annotations

import datetime as dt

import pytest

from app import guia


HOY = dt.date(2026, 11, 10)


def un_tratamiento(
    *,
    fecha: dt.date = HOY - dt.timedelta(days=2),
    seguridad: int | None = 15,
    reentrada: int | None = 2,
) -> dict:
    return {
        "fecha": fecha,
        "plazo_seguridad_dias": seguridad,
        "plazo_reentrada_dias": reentrada,
    }


def estados(tareas: list[dict]) -> dict[str, dict]:
    return {tarea["codigo"]: tarea for tarea in tareas}


class TestElPlazoDeCosecha:
    def test_un_tratamiento_de_hace_dos_dias_con_quince_de_plazo_no_deja_cosechar(self):
        tareas = estados(guia.lo_que_toca(hoy=HOY, tratamientos=[un_tratamiento()], tiene_cultivo=True))
        assert "cosecha" in tareas
        # 15 días desde el 08/11 = 23/11, quedan 13 días.
        assert tareas["cosecha"]["fecha"] == "2026-11-23"
        assert tareas["cosecha"]["dias"] == 13
        assert tareas["cosecha"]["estado"] == guia.ABIERTO

    def test_a_tres_dias_del_final_ya_es_aviso(self):
        tareas = estados(
            guia.lo_que_toca(
                hoy=HOY, tratamientos=[un_tratamiento(fecha=HOY - dt.timedelta(days=12))], tiene_cultivo=True
            )
        )
        assert tareas["cosecha"]["estado"] == guia.PROXIMO
        assert tareas["cosecha"]["dias"] == 3

    def test_el_ultimo_dia_es_hoy(self):
        tareas = estados(
            guia.lo_que_toca(
                hoy=HOY, tratamientos=[un_tratamiento(fecha=HOY - dt.timedelta(days=15))], tiene_cultivo=True
            )
        )
        assert tareas["cosecha"]["estado"] == guia.HOY
        assert tareas["cosecha"]["dias"] == 0

    def test_un_plazo_que_ya_termino_no_se_confunde_con_no_saber(self):
        tareas = estados(
            guia.lo_que_toca(
                hoy=HOY, tratamientos=[un_tratamiento(fecha=HOY - dt.timedelta(days=40))], tiene_cultivo=True
            )
        )
        assert tareas["cosecha"]["estado"] == guia.VENCIDO
        assert tareas["cosecha"]["dias"] < 0

    def test_sin_plazo_de_seguridad_no_hay_aviso_de_cosecha(self):
        tareas = estados(
            guia.lo_que_toca(hoy=HOY, tratamientos=[un_tratamiento(seguridad=None)], tiene_cultivo=True)
        )
        assert "cosecha" not in tareas

    def test_sin_tratamientos_no_hay_ningun_aviso_de_plazo(self):
        tareas = guia.lo_que_toca(hoy=HOY, tratamientos=[], tiene_cultivo=True)
        assert tareas == []


class TestElPlazoDeReentrada:
    def test_la_reentrada_tiene_su_fecha_y_su_estado(self):
        tareas = estados(guia.lo_que_toca(hoy=HOY, tratamientos=[un_tratamiento()], tiene_cultivo=True))
        # 2 días desde el 08/11 = 10/11, o sea hoy.
        assert tareas["reentrada"]["fecha"] == "2026-11-10"
        assert tareas["reentrada"]["estado"] == guia.HOY

    def test_cosecha_y_reentrada_son_avisos_distintos(self):
        tareas = guia.lo_que_toca(hoy=HOY, tratamientos=[un_tratamiento()], tiene_cultivo=True)
        assert {tarea["codigo"] for tarea in tareas} == {"cosecha", "reentrada"}

    def test_sin_plazo_de_reentrada_no_se_inventa(self):
        tareas = estados(
            guia.lo_que_toca(hoy=HOY, tratamientos=[un_tratamiento(reentrada=None)], tiene_cultivo=True)
        )
        assert "reentrada" not in tareas


class TestElCultivoQueFalta:
    def test_sin_cultivo_se_dice_pero_sin_fecha(self):
        tareas = estados(guia.lo_que_toca(hoy=HOY, tratamientos=[], tiene_cultivo=False))
        assert tareas["cultivo"]["fecha"] is None
        assert tareas["cultivo"]["estado"] == guia.SIN_FECHA
        assert tareas["cultivo"]["dias"] is None

    def test_con_cultivo_no_se_dice(self):
        tareas = estados(guia.lo_que_toca(hoy=HOY, tratamientos=[], tiene_cultivo=True))
        assert "cultivo" not in tareas


class TestElOrdenYElResumen:
    def test_lo_que_corre_prisa_va_primero(self):
        # Un tratamiento del 08/11 (reentrada hoy) y otro del 01/01 (todo vencido).
        tareas = guia.lo_que_toca(
            hoy=HOY,
            tratamientos=[
                un_tratamiento(fecha=HOY - dt.timedelta(days=2)),
                un_tratamiento(fecha=dt.date(2026, 1, 1)),
            ],
            tiene_cultivo=True,
        )
        # El más nuevo es el que manda: la reentrada de hoy y la cosecha del 23/11.
        assert tareas[0]["codigo"] == "reentrada"
        assert tareas[0]["estado"] == guia.HOY

    def test_sin_avisos_el_resumen_dice_nada(self):
        assert guia.resumen_de_la_tierra([]) == "nada"

    def test_el_resumen_cuenta_los_que_corren_prisa(self):
        tareas = guia.lo_que_toca(hoy=HOY, tratamientos=[un_tratamiento()], tiene_cultivo=True)
        assert guia.resumen_de_la_tierra(tareas) == "una-prisa"

    def test_el_resumen_distingue_tranquila_de_prisa(self):
        tareas = guia.lo_que_toca(
            hoy=HOY,
            tratamientos=[un_tratamiento(fecha=HOY, seguridad=90, reentrada=60)],
            tiene_cultivo=True,
        )
        assert guia.resumen_de_la_tierra(tareas) == "tranquila"


class TestLoQueNoSeInventa:
    def test_los_tres_estados_del_plazo_estan_en_una_constante(self):
        assert guia.DIAS_DE_AVISO == 3

    def test_un_tratamiento_sin_fecha_no_cuenta(self):
        tareas = guia.lo_que_toca(
            hoy=HOY,
            tratamientos=[{"fecha": None, "plazo_seguridad_dias": 15, "plazo_reentrada_dias": 2}],
            tiene_cultivo=True,
        )
        assert tareas == []

    @pytest.mark.parametrize("dias,esperado", [(4, guia.ABIERTO), (3, guia.PROXIMO), (0, guia.HOY), (-1, guia.VENCIDO)])
    def test_la_frontera_del_aviso(self, dias, esperado):
        estado, contados = guia._estado_de_un_plazo(HOY + dt.timedelta(days=dias), HOY)
        assert estado == esperado
        assert contados == dias
