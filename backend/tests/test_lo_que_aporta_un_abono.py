"""**Lo que aporta un abono, con su unidad y su base** (CRM-07, 17/10/2026).

Los tres casos son **los del criterio, literales**:

    - 600 kg en 3 ha, N 15 % m/m: 200 kg de producto/ha y 30 kg N/ha.
    - 20 L a 100 g N/L en 2 ha: 2 kg N totales y 1 kg N/ha.
    - 20 L a 15 % m/m: **sin densidad no calcular kg N; mostrar el dato que falta**.

Y lo demas que el criterio manda, que es donde se rompen estas cosas:

  * **No confundir** concentracion, cantidad comprada, cantidad aplicada y dosis por hectarea.
  * **Conservar N, P2O5 y K2O con su especie quimica declarada**; no llamarlos P y K sin conversion.
  * **«No consta» no es cero**: un abono del que nadie ha declarado el fosforo **no tiene 0 de fosforo**.
"""

from __future__ import annotations

from app import nutrientes


# ---------------------------------------------------------------------------
# 1 · Los tres casos del criterio, literales
# ---------------------------------------------------------------------------


def test_600_kg_en_3_ha_con_N_15_por_ciento():
    """***El caso del contrato***: 200 kg de producto/ha y **30 kg N/ha**."""
    suyo = nutrientes.el_aporte(
        cantidad=600.0,
        unidad=nutrientes.KILOS,
        riquezas={"n": 15.0},
        base=nutrientes.PORCENTAJE_EN_MASA,
        superficie_ha=3.0,
    )

    assert suyo["producto"]["por_hectarea"] == 200.0
    assert suyo["nutrientes"]["n"]["total_kg"] == 90.0
    assert suyo["nutrientes"]["n"]["por_hectarea_kg"] == 30.0
    assert suyo["lo_que_falta"] == []


def test_20_litros_a_100_g_por_litro_en_2_ha():
    """***El caso de los liquidos***: 2 kg N totales y **1 kg N/ha**.

    100 g/L son 0,1 kg por litro, asi que 20 L llevan 2 kg de nitrogeno. Aqui **no hace falta densidad**:
    la etiqueta ya viene en masa por volumen.
    """
    suyo = nutrientes.el_aporte(
        cantidad=20.0,
        unidad=nutrientes.LITROS,
        riquezas={"n": 100.0},
        base=nutrientes.GRAMOS_POR_LITRO,
        superficie_ha=2.0,
    )

    assert suyo["nutrientes"]["n"]["total_kg"] == 2.0
    assert suyo["nutrientes"]["n"]["por_hectarea_kg"] == 1.0
    assert suyo["lo_que_falta"] == []


def test_20_litros_al_15_por_ciento_SIN_DENSIDAD_no_se_calcula():
    """***«Sin densidad no calcular kg N; mostrar el dato que falta»***, que es lo que dice el criterio.

    Un litro de un producto al 15 % m/m **no pesa un kilo**: pesa lo que diga su densidad. Dar un numero
    aqui seria inventarselo, y callarlo seria peor todavia.
    """
    suyo = nutrientes.el_aporte(
        cantidad=20.0,
        unidad=nutrientes.LITROS,
        riquezas={"n": 15.0},
        base=nutrientes.PORCENTAJE_EN_MASA,
        superficie_ha=2.0,
    )

    assert suyo["nutrientes"]["n"]["total_kg"] is None, "***sin densidad NO se calcula***"
    assert suyo["nutrientes"]["n"]["por_hectarea_kg"] is None
    assert nutrientes.FALTA_LA_DENSIDAD in suyo["lo_que_falta"], "***y se dice QUE falta***"
    # La dosis de **producto** si se sabe, y se da: lo que no se sabe es el nutriente.
    assert suyo["producto"]["por_hectarea"] == 10.0


def test_y_CON_la_densidad_si_se_calcula():
    """El complemento del anterior: en cuanto consta la densidad, la cuenta sale."""
    suyo = nutrientes.el_aporte(
        cantidad=20.0,
        unidad=nutrientes.LITROS,
        riquezas={"n": 15.0},
        base=nutrientes.PORCENTAJE_EN_MASA,
        superficie_ha=2.0,
        densidad_kg_por_litro=1.2,
    )

    # 20 L * 1,2 kg/L = 24 kg de producto; 15 % de 24 = 3,6 kg de N; entre 2 ha, 1,8 kg N/ha.
    assert suyo["nutrientes"]["n"]["total_kg"] == 3.6
    assert suyo["nutrientes"]["n"]["por_hectarea_kg"] == 1.8
    assert suyo["lo_que_falta"] == []


def test_los_kg_por_hectolitro_tambien_valen():
    """El anexo II del BOE contempla `kg/hl` ademas de `g/L`. 1 hl son 100 L."""
    suyo = nutrientes.el_aporte(
        cantidad=100.0,
        unidad=nutrientes.LITROS,
        riquezas={"n": 2.0},
        base=nutrientes.KILOGRAMOS_POR_HECTOLITRO,
        superficie_ha=2.0,
    )

    # 2 kg/hl son 0,02 kg por litro; 100 L son 2 kg de N.
    assert suyo["nutrientes"]["n"]["total_kg"] == 2.0


# ---------------------------------------------------------------------------
# 2 · La especie quimica, y «no consta» frente a cero
# ---------------------------------------------------------------------------


def test_los_nutrientes_van_con_su_ESPECIE_QUIMICA():
    """***«No llamarlos P y K sin conversion»***: en la etiqueta el fosforo va como **P2O5**."""
    assert nutrientes.LOS_NUTRIENTES == ("n", "p2o5", "k2o")
    assert nutrientes.LOS_NOMBRES["p2o5"] == "P2O5"
    assert nutrientes.LOS_NOMBRES["k2o"] == "K2O"
    assert "p" not in nutrientes.LOS_NUTRIENTES, "***ni `p` ni `k` a secas***"


def test_un_nutriente_que_NO_CONSTA_no_es_un_cero():
    """***La diferencia que costo un defecto de produccion*** (A6 de T02).

    Un abono del que nadie ha declarado el fosforo **no tiene 0 de fosforo**: tiene «no consta». Y uno que
    **si** dice cero -un nitrato amonico no lleva potasio- tiene un cero de verdad.
    """
    sin_declarar = nutrientes.el_aporte(
        cantidad=100.0,
        unidad=nutrientes.KILOS,
        riquezas={"n": 33.5},
        base=nutrientes.PORCENTAJE_EN_MASA,
        superficie_ha=1.0,
    )
    con_cero = nutrientes.el_aporte(
        cantidad=100.0,
        unidad=nutrientes.KILOS,
        riquezas={"n": 33.5, "k2o": 0.0},
        base=nutrientes.PORCENTAJE_EN_MASA,
        superficie_ha=1.0,
    )

    assert sin_declarar["nutrientes"]["k2o"]["total_kg"] is None, "***«no consta» NO es cero***"
    assert con_cero["nutrientes"]["k2o"]["total_kg"] == 0.0, "y un cero declarado SI es cero"
    assert sin_declarar["nutrientes"]["n"]["total_kg"] == 33.5


def test_sin_superficie_la_dosis_es_DESCONOCIDA_y_no_cero():
    """***«2 L en 4 ha -> 0,5 L/ha, sin area -> desconocido»***, del caso de aceptacion del COLA."""
    suyo = nutrientes.el_aporte(
        cantidad=2.0,
        unidad=nutrientes.LITROS,
        riquezas={"n": 100.0},
        base=nutrientes.GRAMOS_POR_LITRO,
        superficie_ha=None,
    )

    assert suyo["producto"]["por_hectarea"] is None, "***desconocido, no cero***"
    assert suyo["nutrientes"]["n"]["total_kg"] == 0.2, "pero el total SI se sabe"
    assert suyo["nutrientes"]["n"]["por_hectarea_kg"] is None
    assert nutrientes.FALTA_LA_SUPERFICIE in suyo["lo_que_falta"]


# ---------------------------------------------------------------------------
# 3 · Lo que no vale, dicho
# ---------------------------------------------------------------------------


def test_una_base_de_masa_por_volumen_no_vale_para_un_SOLIDO():
    """Los g/L son masa **por volumen**: en un solido no significan nada, y se dice en vez de inventarse
    una densidad que nadie ha medido."""
    suyo = nutrientes.el_aporte(
        cantidad=100.0,
        unidad=nutrientes.KILOS,
        riquezas={"n": 100.0},
        base=nutrientes.GRAMOS_POR_LITRO,
        superficie_ha=1.0,
    )

    assert suyo["nutrientes"]["n"]["total_kg"] is None
    assert nutrientes.LA_BASE_NO_VALE_PARA_ESA_UNIDAD in suyo["lo_que_falta"]


def test_una_unidad_o_una_base_que_no_existen_se_dicen():
    suyo = nutrientes.el_aporte(
        cantidad=1.0,
        unidad="fanegas",
        riquezas={"n": 10.0},
        base="por_cien_de_lo_que_sea",
        superficie_ha=1.0,
    )

    assert nutrientes.LA_UNIDAD_DEL_PRODUCTO_NO_ES_DE_LAS_QUE_HAY in suyo["lo_que_falta"]
    assert nutrientes.LA_BASE_NO_ES_DE_LAS_QUE_HAY in suyo["lo_que_falta"]
    assert suyo["nutrientes"]["n"]["total_kg"] is None


# ---------------------------------------------------------------------------
# 4 · Y las columnas antiguas, que no se reinterpretan
# ---------------------------------------------------------------------------


def test_las_columnas_antiguas_se_leen_como_lo_que_SON():
    """***«Mantener las columnas antiguas porcentuales compatibles. No reinterpretar registros firmados.»***

    `riqueza_n` no dice su base porque es de antes. Lo que **siempre** significo es % m/m, asi que se lee
    asi: no se reinterpreta nada, se dice lo que era.
    """
    suyo = nutrientes.el_aporte_de_la_riqueza_porcentual(
        cantidad=600.0, unidad=nutrientes.KILOS, superficie_ha=3.0, riquezas={"n": 15.0}
    )

    assert suyo["la_base"] == nutrientes.PORCENTAJE_EN_MASA
    assert suyo["nutrientes"]["n"]["por_hectarea_kg"] == 30.0, "***el mismo 30 kg N/ha de siempre***"


# ---------------------------------------------------------------------------
# 5 · El caso de los LIQUIDOS, **por la puerta**, y el defecto que arregla
# ---------------------------------------------------------------------------
#
# ***Aqui estaba el defecto de verdad*** (CRM-07, 17/10/2026). `servicios.py` calculaba los nutrientes con
# `legal.unidades_fertilizantes(cantidad_total_kg, riqueza_pct)`, que da por hecho **dos** cosas que no
# siempre son verdad: que la riqueza es un **porcentaje en masa** y que el producto son **kilos**.
#
# Con un liquido a **100 g/L** y **20 L** multiplicaba `20 x 100/100 = 20 kg de nitrogeno` **donde se
# echaron 2**: diez veces mas. Y eso no se queda en una pantalla: entra en el documento que se firma y en el
# plan de abono del ano. Es, literalmente, el caso que el criterio pone como ejemplo.
#
# Las pruebas **puras** de estos mismos numeros ya estan arriba; estas dos andan **la puerta entera**, que es
# donde vivia la cuenta equivocada.


def _un_liquido(cliente, cuenta, **cambios):
    cuerpo = {
        "nombre": "Liquido 100 g N/L",
        "tipo": "mineral",
        "riqueza_n": 100.0,
        "base_de_la_riqueza": "gramos_por_litro",
    }
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/fertilizantes", headers=cuenta["cabeceras"], json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _apuntar_los_litros(cliente, cuenta, campana, parcela, abono, **cambios):
    cuerpo = {
        "campana_id": campana["id"],
        "fecha": "2026-05-05",
        "parcela_id": parcela["id"],
        "superficie_ha": 2.0,
        "fertilizante_id": abono["id"],
        "cantidad_total_kg": 20.0,
        "unidad_del_producto": "L",
        "base_de_la_riqueza": "gramos_por_litro",
    }
    cuerpo.update(cambios)
    return cliente.post("/api/fertilizaciones", headers=cuenta["cabeceras"], json=cuerpo)


def test_el_caso_de_los_litros_POR_LA_PUERTA(cliente, cuenta, campana, crear_parcela):
    """***«20 L a 100 g N/L en 2 ha: 2 kg N totales y 1 kg N/ha»***, con la puerta entera.

    ***Antes daba 20.*** Con la cuenta vieja -porcentaje sobre kilos- salian **diez veces mas** kilos de
    nitrogeno de los que se echaron.
    """
    parcela = crear_parcela(superficie_ha=2.0)
    abono = _un_liquido(cliente, cuenta)

    respuesta = _apuntar_los_litros(cliente, cuenta, campana, parcela, abono)

    assert respuesta.status_code == 201, respuesta.text
    guardado = respuesta.json()
    assert guardado["uf_n_total"] == 2.0, f"***2 kg de nitrogeno, no 20***: {guardado['uf_n_total']}"
    assert guardado["uf_n_ha"] == 1.0, f"***1 kg N/ha***: {guardado['uf_n_ha']}"
    # Y se guarda **en que se conto**, que es parte del dato.
    assert guardado["unidad_del_producto"] == "L"
    assert guardado["base_de_la_riqueza"] == "gramos_por_litro"


def test_los_litros_al_15_por_ciento_SIN_densidad_no_se_calculan_POR_LA_PUERTA(
    cliente, cuenta, campana, crear_parcela
):
    """***«Sin densidad no calcular kg N; mostrar el dato que falta»***, tambien por la puerta.

    Un liquido al 15 % **en masa** necesita la densidad para pasar de litros a kilos. Sin ella, el apunte se
    guarda **sin cifra de nitrogeno** -no con un cero, que diria que ese abono no aporta nada-.
    """
    parcela = crear_parcela(superficie_ha=2.0)
    abono = _un_liquido(cliente, cuenta, nombre="Liquido 15 %", riqueza_n=15.0)

    respuesta = _apuntar_los_litros(
        cliente, cuenta, campana, parcela, abono, base_de_la_riqueza="porcentaje_masa"
    )

    assert respuesta.status_code == 201, respuesta.text
    guardado = respuesta.json()
    assert guardado["uf_n_total"] is None, (
        f"***sin densidad NO se calcula, y NO es cero***: {guardado['uf_n_total']}"
    )
    assert guardado["uf_n_ha"] is None
    # **Y el producto si se sabe**: lo que no consta es el nutriente, no los litros.
    assert guardado["cantidad_total_kg"] == 20.0


# ---------------------------------------------------------------------------
# 6 · La migracion, ensayada SOBRE UNA COPIA
# ---------------------------------------------------------------------------
#
# El criterio lo manda con estas palabras: *«Mantener las columnas antiguas porcentuales compatibles. Anadir
# estructura/migracion **solo tras inventariar las unidades que hoy existen**. ***No reinterpretar registros
# firmados***»*.
#
# El inventario esta hecho -y de el sale que las riquezas guardadas **siempre fueron % en masa**-, asi que
# ahora se ensaya la migracion. **Sobre una copia**, que es donde se puede repetir.


def test_las_columnas_del_nutriente_se_anaden_SIN_reinterpretar_lo_guardado(tmp_path):
    """***Una instalacion que ya venia arrancada recibe las columnas, y su cuaderno no cambia de sentido.***

    Se coge una base **con el esquema de antes** -sin las columnas nuevas-, se le mete un abono con su
    composicion, se hace **una copia** y se le pasa `asegurar_columnas`, que es lo que corre al arrancar.

    Lo que tiene que pasar: las columnas **entran**, y la fila vieja **sigue diciendo lo mismo**. Y lo que
    dicen las columnas nuevas sobre ella es **lo que siempre fue** -`porcentaje_masa`-, no una suposicion
    nueva: *no se reinterpreta nada, se dice lo que era*.
    """
    import shutil

    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from app import models
    from app.database import asegurar_columnas, crear_engine

    LAS_NUEVAS = (
        "base_de_la_riqueza",
        "densidad_kg_por_litro",
        "fuente_de_la_riqueza",
        "riqueza_p2o5",
        "riqueza_k2o",
    )

    original = tmp_path / "el-catalogo-viejo.db"
    motor = crear_engine("sqlite:///" + str(original).replace("\\", "/"))
    models.Base.metadata.create_all(motor)

    # ***PRIMERO EL ESQUEMA DE ANTES***, y despues la fila: al reves no se puede, porque con el esquema de
    # hoy `base_de_la_riqueza` es obligatoria y el `INSERT` de una fila vieja -que no la lleva- falla. Ese
    # fallo, en la prueba, es la prueba de que la columna **es** obligatoria y de que la migracion tiene que
    # ponerle un valor.
    for columna in LAS_NUEVAS:
        with motor.begin() as conexion:
            conexion.execute(text(f"ALTER TABLE fertilizantes DROP COLUMN {columna}"))

    # ***La finca primero***, porque las claves ajenas estan activas -la casa las activa con un evento- y un
    # abono sin explotacion no entra. Se crea **con el modelo**, no con SQL a mano: asi los campos
    # obligatorios los pone quien los conoce.
    with Session(motor) as sesion:
        sesion.add(models.Explotacion(nombre="La finca de la migracion", nif="12345678Z"))
        sesion.commit()

    # **Un abono de los de antes**: con su nitrogeno a 15 y su fosforo declarado a cero. El cero es un dato
    # -ese abono no lleva fosforo-, y tiene que seguir siendo un cero despues de migrar.
    with motor.begin() as conexion:
        conexion.execute(
            text(
                "INSERT INTO fertilizantes (id, explotacion_id, nombre, tipo, riqueza_n, riqueza_p,"
                " riqueza_k) VALUES (1, 1, 'Nitrato amonico 15 %', 'mineral', 15.0, 0.0, NULL)"
            )
        )

    with motor.connect() as conexion:
        quedan = {f[1] for f in conexion.execute(text("PRAGMA table_info(fertilizantes)"))}
    assert not (quedan & set(LAS_NUEVAS)), "***la base de partida NO tiene que tener las columnas nuevas***"

    # **Sobre una COPIA**, que es lo que se ensaya.
    copia = tmp_path / "la-copia.db"
    shutil.copyfile(original, copia)
    motor_copia = crear_engine("sqlite:///" + str(copia).replace("\\", "/"))

    anadidas, imposibles = asegurar_columnas(motor_copia)

    for columna in LAS_NUEVAS:
        assert any(columna in dicha for dicha in anadidas), (
            f"***el arranque tiene que anadir `{columna}`; ha anadido: {anadidas!r}***"
        )
    assert imposibles == [], f"***y ninguna se puede quedar sin poner: {imposibles!r}***"

    # ***Y LA FILA VIEJA SIGUE DICIENDO LO MISMO.***
    with Session(motor_copia) as sesion:
        fila = sesion.execute(
            text(
                "SELECT nombre, riqueza_n, riqueza_p, riqueza_k, base_de_la_riqueza,"
                " riqueza_p2o5, densidad_kg_por_litro"
                " FROM fertilizantes WHERE id = 1"
            )
        ).fetchone()

    assert fila[0] == "Nitrato amonico 15 %", "el abono sigue siendo el mismo"
    assert fila[1] == 15.0, "***su nitrogeno no se ha tocado***"
    assert fila[2] == 0.0, "***y su cero de fosforo sigue siendo un cero declarado, no un hueco***"
    assert fila[3] is None, "y el potasio sigue sin constar"
    assert fila[4] == "porcentaje_masa", "***la base dice lo que SIEMPRE fue: % en masa***"
    assert fila[5] is None and fila[6] is None, "y lo que no consta, no consta"
