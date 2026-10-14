"""Los kilos y la superficie dan el kg/ha y los nutrientes (CRM-07, 14/10/2026).

**El caso del contrato, literal**: *«600 kg en 3 ha con N 15 % acreditado -> 200 kg/ha y 30 kg N/ha;
**P desconocido si falta**»*.

**Por que faltaba.** El abono pedia los **kilos por hectarea** a mano (`kg_ha_producto` obligatorio y
mayor que cero) y **multiplicaba** para sacar el total. Pero el agricultor no tiene delante el kg/ha:
tiene **los sacos** y **la parcela**. O sea: le obligabamos a hacer la division de cabeza —y una
division hecha a mano es una cuenta que puede estar mal— y ademas **nunca podia decir «no consta»**.

**Lo que se prueba aqui** es que diciendo lo que se sabe (los kilos y la superficie) **la cuenta sale
sola**, y que donde falta un dato se dice **«no consta»** (`None`) y no un cero: `P` no viene en la
etiqueta de este abono, asi que `uf_p_ha` **no puede ser 0.0** — un cero diria que ese abono no aporta
fosforo, y lo que pasa es que nadie lo ha declarado.

**La parcela es de 3 ha a proposito**: la de la casa mide 2,43 y no da los numeros redondos del
contrato. Se pide una de 3 con `crear_parcela(superficie_ha=3.0)`, que es una parcela de verdad.
"""

from __future__ import annotations

FECHA = "2026-05-05"
TRES_HECTAREAS = 3.0


def _un_abono(cliente, cuenta, **cambios):
    """Un abono del catalogo, con la composicion que diga la prueba."""
    cuerpo = {"nombre": "Nitrato amonico 15 %", "tipo": "mineral", "riqueza_n": 15.0}
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/fertilizantes", headers=cuenta["cabeceras"], json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _apuntar(cliente, cuenta, campana, parcela, abono, **cambios):
    cuerpo = {
        "campana_id": campana["id"],
        "fecha": FECHA,
        "parcela_id": parcela["id"],
        "superficie_ha": TRES_HECTAREAS,
        "fertilizante_id": abono["id"],
        "justificacion": "Abono de fondo antes de sembrar",
    }
    cuerpo.update(cambios)
    return cliente.post("/api/fertilizaciones", headers=cuenta["cabeceras"], json=cuerpo)


def test_los_kilos_y_la_superficie_dan_el_kg_ha_y_el_nitrogeno(
    cliente, cuenta, campana, crear_parcela
):
    parcela = crear_parcela(superficie_ha=TRES_HECTAREAS)
    abono = _un_abono(cliente, cuenta)
    respuesta = _apuntar(cliente, cuenta, campana, parcela, abono, cantidad_total_kg=600.0)
    assert respuesta.status_code == 201, respuesta.text
    guardado = respuesta.json()

    # 600 kg en 3 ha -> 200 kg/ha, y con N 15 % -> 30 kg de nitrogeno por hectarea.
    assert guardado["kg_ha_producto"] == 200.0, f"el kg/ha no se dedujo: {guardado['kg_ha_producto']}"
    assert guardado["cantidad_total_kg"] == 600.0
    assert guardado["uf_n_ha"] == 30.0, f"el nitrogeno por hectarea no cuadra: {guardado['uf_n_ha']}"


def test_el_fosforo_que_no_viene_en_la_etiqueta_no_es_cero(cliente, cuenta, campana, crear_parcela):
    # **La regla de la casa**: `P desconocido si falta`. La etiqueta de este abono no trae fosforo, asi
    # que el apunte dice **que no consta** — no un `0.0`, que afirmaria que ese abono no aporta fosforo.
    parcela = crear_parcela(superficie_ha=TRES_HECTAREAS)
    abono = _un_abono(cliente, cuenta)
    respuesta = _apuntar(cliente, cuenta, campana, parcela, abono, cantidad_total_kg=600.0)
    assert respuesta.status_code == 201, respuesta.text
    guardado = respuesta.json()
    assert guardado["uf_p_ha"] is None, (
        f"el fosforo que no consta tiene que ser None, y vino {guardado['uf_p_ha']!r}"
    )
    assert guardado["uf_k_ha"] is None


def test_el_kg_ha_a_mano_sigue_valiendo(cliente, cuenta, campana, crear_parcela):
    # **Y lo de siempre no se rompe** (CRM-07, 14/10/2026): quien prefiera escribir los kilos por
    # hectarea sigue pudiendo, y el total se calcula como se calculaba. Nada de lo ya guardado cambia.
    parcela = crear_parcela(superficie_ha=TRES_HECTAREAS)
    abono = _un_abono(cliente, cuenta)
    respuesta = _apuntar(cliente, cuenta, campana, parcela, abono, kg_ha_producto=200.0)
    assert respuesta.status_code == 201, respuesta.text
    guardado = respuesta.json()
    assert guardado["kg_ha_producto"] == 200.0
    assert guardado["cantidad_total_kg"] == 600.0, "el total tiene que salir de 200 kg/ha por 3 ha"


def test_sin_kilos_ni_kg_ha_la_puerta_lo_dice(cliente, cuenta, campana, crear_parcela):
    # Y si no viene ninguno de los dos, **no se guarda un abono que no consta**: lo dice la
    # comprobacion de la casa (`F1_sin_cantidad`), cuyo mensaje ofrece las dos formas.
    parcela = crear_parcela(superficie_ha=TRES_HECTAREAS)
    abono = _un_abono(cliente, cuenta)
    respuesta = _apuntar(cliente, cuenta, campana, parcela, abono)
    assert respuesta.status_code == 422, respuesta.text
    assert "kilos" in respuesta.text
