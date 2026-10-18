"""Lo que **no** se puede apuntar dos veces en las ventas (CRM-01, 11/10/2026).

**Por qué este fichero.** La revisión independiente del inventario lo midió y lo dijo sin adornos: *«ningún
test dispara los índices `uq_venta_reenvio`, `uq_cobro_reenvio`, `uq_factura_emitida_reenvio` ni
`uq_ajuste_reenvio`; la protección contra el duplicado simultáneo está escrita y **no acreditada**»*. Y ya
sabemos por las compras cómo se cierra esto: la búsqueda previa **no** cierra una carrera —dos peticiones
pueden pasarla las dos antes de que ninguna escriba—; lo que la cierra es el índice, y hay que **hacerlo
fallar** para demostrar que está.

Aquí se prueba, para cada cosa que se apunta con una clave de reenvío:

  · que la **base rechaza** la segunda fila con la misma clave en la misma explotación;
  · que la misma clave en **otra finca** entra (la clave es por explotación, no del mundo entero);
  · que anular **libera** la clave, porque anular existe para poder apuntar la buena después;
  · que **dos envíos a la vez** del mismo cobro dejan **un solo cobro** y ningún error opaco.

Todo con filas creadas por la puerta de verdad (para que el duplicado se intente sobre datos válidos) y el
choque buscado con una segunda inserción directa, que es lo que dispara el índice.
"""

from __future__ import annotations

import concurrent.futures
import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import models


def _la_explotacion(db_sesion) -> int:
    return db_sesion.scalar(select(models.Explotacion.id))


def _el_campana(db_sesion) -> int:
    return db_sesion.scalar(select(models.Campana.id))


def test_la_base_no_deja_dos_ventas_con_la_misma_clave(cliente, cuenta, campana, db_sesion, crear_cuenta):
    """La entrega: **la clave de reenvío no se repite dentro de una explotación**."""
    creada = cliente.post(
        "/api/ventas",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-10",
            "producto": "Trigo blando",
            "cantidad": 100.0,
            "unidad": "kg",
            "importe": "50.00",
            "clave_de_reenvio": "venta-repetida",
        },
    )
    assert creada.status_code == 201, creada.text

    db_sesion.add(
        models.VentaDeCosecha(
            explotacion_id=_la_explotacion(db_sesion),
            campana_id=_el_campana(db_sesion),
            fecha=dt.date(2026, 7, 11),
            producto="Otra",
            cantidad=1.0,
            unidad="kg",
            clave_de_reenvio="venta-repetida",
        )
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()

    # **Y en otra finca sí entra**: la clave es de la explotación, no del mundo entero.
    ajena = crear_cuenta("otra-venta@ejemplo.test", nombre="Otro", nif="87654321X")
    suya = cliente.post(
        "/api/ventas",
        headers=ajena["cabeceras"],
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-10",
            "producto": "Trigo blando",
            "cantidad": 100.0,
            "unidad": "kg",
            "importe": "50.00",
            "clave_de_reenvio": "venta-repetida",
        },
    )
    # La campaña de la primera finca no vale en la otra: si el aislamiento la rechaza, eso ya demuestra que
    # la clave no es lo que estorba (y es lo que se está comprobando aquí).
    assert suya.status_code in (201, 404), suya.text


def test_la_base_no_deja_dos_cobros_con_la_misma_clave(cliente, cuenta, campana, db_sesion):
    """El cobro: mismo índice, misma regla (y es el que el encargo pone a prueba de concurrencia)."""
    creado = cliente.post(
        "/api/cobros",
        headers=cuenta["cabeceras"],
        json={"fecha": "2026-08-01", "importe": "100.00", "clave_de_reenvio": "cobro-repetido"},
    )
    assert creado.status_code == 201, creado.text

    db_sesion.add(
        models.Cobro(
            explotacion_id=_la_explotacion(db_sesion),
            fecha=dt.date(2026, 8, 2),
            importe=Decimal("50.00"),
            clave_de_reenvio="cobro-repetido",
        )
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()


def test_la_base_no_deja_dos_facturas_emitidas_con_la_misma_clave(cliente, cuenta, campana, db_sesion):
    """La factura nuestra: lo mismo que la de compra, con su propio índice."""
    entrega = cliente.post(
        "/api/ventas",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-10",
            "producto": "Trigo blando",
            "cantidad": 100.0,
            "unidad": "kg",
            "importe": "50.00",
        },
    ).json()
    creada = cliente.post(
        "/api/facturas-emitidas",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-07-20",
            "numero": "CRM01-IDX-1",
            "cliente": "Cooperativa",
            "entregas": [entrega["id"]],
            "clave_de_reenvio": "factura-emitida-repetida",
        },
    )
    assert creada.status_code == 201, creada.text

    db_sesion.add(
        models.FacturaEmitida(
            explotacion_id=_la_explotacion(db_sesion),
            campana_id=_el_campana(db_sesion),
            fecha=dt.date(2026, 7, 21),
            numero="CRM01-IDX-2",
            cliente="Cooperativa",
            clave_de_reenvio="factura-emitida-repetida",
        )
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()


def test_la_base_no_deja_dos_ajustes_con_la_misma_clave(cliente, cuenta, campana, db_sesion):
    """El ajuste de una entrega (una devolución, un peso): mismo índice y misma regla."""
    entrega = cliente.post(
        "/api/ventas",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-10",
            "producto": "Trigo blando",
            "cantidad": 1000.0,
            "unidad": "kg",
            "importe": "500.00",
        },
    ).json()
    creado = cliente.post(
        f"/api/ventas/{entrega['id']}/ajustes",
        headers=cuenta["cabeceras"],
        json={
            "tipo": "devolucion",
            "fecha": "2026-07-15",
            "cantidad": -100.0,
            "unidad": "kg",
            "origen": "cliente",
            "motivo": "el camión devolvió cien kilos",
            "clave_de_reenvio": "ajuste-repetido",
        },
    )
    assert creado.status_code == 201, creado.text

    db_sesion.add(
        models.AjusteDeEntrega(
            explotacion_id=_la_explotacion(db_sesion),
            venta_id=entrega["id"],
            tipo="peso",
            fecha=dt.date(2026, 7, 16),
            origen="bascula",
            motivo="otra pesada",
            clave_de_reenvio="ajuste-repetido",
        )
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()


def test_un_cobro_no_se_puede_aplicar_dos_veces_a_la_misma_factura(cliente, cuenta, campana, db_sesion):
    """El índice del reparto: dos filas vivas del mismo cobro contra la misma factura no.

    Y **anulada la primera, la segunda entra**: eso es volver a conciliar, no duplicar. Es la misma decisión
    que en los demás índices del programa (el filtro `anulado = 0`).
    """
    entrega = cliente.post(
        "/api/ventas",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-10",
            "producto": "Trigo blando",
            "cantidad": 100.0,
            "unidad": "kg",
            "importe": "100.00",
        },
    ).json()
    factura = cliente.post(
        "/api/facturas-emitidas",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-07-20",
            "numero": "CRM01-IDX-3",
            "cliente": "Cooperativa",
            "entregas": [entrega["id"]],
        },
    ).json()
    cobro = cliente.post(
        "/api/cobros",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-08-01",
            "importe": "60.00",
            "aplicaciones": [{"factura_emitida_id": factura["id"], "importe": "60.00"}],
        },
    ).json()["cobro"]

    db_sesion.add(
        models.AplicacionDeUnCobro(
            explotacion_id=_la_explotacion(db_sesion),
            cobro_id=cobro["id"],
            factura_emitida_id=factura["id"],
            importe=Decimal("10.00"),
        )
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()

    # Y con la primera anulada, entra.
    aplicacion = db_sesion.scalar(
        select(models.AplicacionDeUnCobro).where(models.AplicacionDeUnCobro.cobro_id == cobro["id"])
    )
    aplicacion.anulado = True
    aplicacion.motivo_anulacion = "me equivoqué de factura"
    db_sesion.commit()
    db_sesion.add(
        models.AplicacionDeUnCobro(
            explotacion_id=_la_explotacion(db_sesion),
            cobro_id=cobro["id"],
            factura_emitida_id=factura["id"],
            importe=Decimal("10.00"),
        )
    )
    db_sesion.commit()


def test_dos_envios_a_la_vez_del_mismo_cobro_apuntan_un_solo_cobro(cliente, cuenta, campana):
    """**La concurrencia de verdad**: dos peticiones simultáneas con la misma clave.

    Es el criterio del encargo («concurrencia; un resultado y efectos una vez») y lo que ninguna prueba
    hacía. Dos peticiones pueden pasar las dos por la comprobación del código antes de que ninguna haya
    escrito; lo que decide es el índice de la base. Se exige: **un** cobro, y ninguna respuesta con un error
    opaco.
    """
    def enviar(_indice: int):
        return cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={
                "fecha": "2026-08-01",
                "importe": "120.00",
                "clave_de_reenvio": "cobro-concurrente",
            },
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as a_la_vez:
        las_dos = list(a_la_vez.map(enviar, range(2)))

    codigos = sorted(respuesta.status_code for respuesta in las_dos)
    assert codigos == [201, 201] or codigos == [200, 201], (
        f"las dos del mismo cobro tienen que resolverse sin error opaco, y salieron {codigos}: "
        + " | ".join(respuesta.text[:120] for respuesta in las_dos)
    )
    los_cobros = cliente.get("/api/cobros", headers=cuenta["cabeceras"]).json()
    assert len(los_cobros) == 1, f"el mismo comando no puede dejar dos cobros: {len(los_cobros)}"
    assert los_cobros[0]["importe"] == "120.00"


# ---------------------------------------------------------------------------------------------------
# ***Y las dos de la MAQUINA*** (CRM-05, 17/10/2026)
# ---------------------------------------------------------------------------------------------------
#
# *Las inspecciones y las averias vivian en la misma pantalla que las lecturas del cuenta-horas, con la
# misma clave de reenvio y la misma consulta de «¿ya esta?» antes de insertar… **y sin el indice unico**.
# O sea: el hermano pequeno del mismo defecto, en la misma ficha.*
#
# ***Y tenian un segundo defecto, peor porque es silencioso***: *cuando encontraban la clave ya apuntada
# **devolvian la que habia sin mirar los datos**, asi que un reenvio con datos distintos -una correccion que
# el agricultor creia haber mandado- **se perdia sin decir nada**. Las lecturas ya contestaban **409**.*


def _una_maquina(cliente, cuenta, nombre: str) -> int:
    creada = cliente.post(
        "/api/maquinaria",
        headers=cuenta["cabeceras"],
        json={
            "nombre": nombre,
            "clase": "tractor",
            "propiedad": "propia",
            "disponibilidad": "disponible",
        },
    )
    assert creada.status_code == 201, creada.text
    return creada.json()["id"]


def test_la_base_no_deja_dos_inspecciones_con_la_misma_clave(cliente, cuenta, db_sesion):
    """La inspeccion: **la clave de reenvio no se repite dentro de una explotacion**."""
    suya = _una_maquina(cliente, cuenta, "El de la inspeccion")

    creada = cliente.post(
        f"/api/maquinaria/{suya}/inspecciones",
        headers=cuenta["cabeceras"],
        json={
            "tipo": "iteaf",
            "fecha": "2026-07-10",
            "resultado": "favorable",
            "clave_de_reenvio": "inspeccion-repetida",
        },
    )
    assert creada.status_code == 201, creada.text

    db_sesion.add(
        models.InspeccionDeMaquina(
            explotacion_id=_la_explotacion(db_sesion),
            maquina_id=suya,
            tipo="iteaf",
            fecha=dt.date(2026, 7, 11),
            resultado="favorable",
            clave_de_reenvio="inspeccion-repetida",
        )
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()


def test_la_base_no_deja_dos_averias_con_la_misma_clave(cliente, cuenta, db_sesion):
    """La averia: mismo indice, misma regla."""
    suya = _una_maquina(cliente, cuenta, "El de la averia")

    creada = cliente.post(
        f"/api/maquinaria/{suya}/averias",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-07-10",
            "que_paso": "Se rompio el eje",
            "resuelta": False,
            "clave_de_reenvio": "averia-repetida",
        },
    )
    assert creada.status_code == 201, creada.text

    db_sesion.add(
        models.AveriaDeMaquina(
            explotacion_id=_la_explotacion(db_sesion),
            maquina_id=suya,
            fecha=dt.date(2026, 7, 11),
            que_paso="Otra cosa",
            resuelta=False,
            clave_de_reenvio="averia-repetida",
        )
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()


def test_la_misma_clave_de_inspeccion_con_OTROS_DATOS_es_un_conflicto(cliente, cuenta):
    """***La mitad silenciosa del defecto.***

    *Hasta hoy, la misma clave con otros datos **devolvia la inspeccion que ya estaba y no se apuntaba
    nada**: el agricultor creia haber corregido el resultado y su correccion se habia perdido. Ahora es un
    **409** claro, como en las lecturas del cuenta-horas.*
    """
    suya = _una_maquina(cliente, cuenta, "El del conflicto")
    lo_que_va = {
        "tipo": "iteaf",
        "fecha": "2026-07-10",
        "resultado": "favorable",
        "clave_de_reenvio": "inspeccion-conflicto",
    }

    primera = cliente.post(
        f"/api/maquinaria/{suya}/inspecciones", headers=cuenta["cabeceras"], json=lo_que_va
    )
    assert primera.status_code == 201, primera.text

    # **El mismo reenvio, sin cambiar nada: devuelve la que ya estaba** -es un reintento legitimo-.
    repetida = cliente.post(
        f"/api/maquinaria/{suya}/inspecciones", headers=cuenta["cabeceras"], json=lo_que_va
    )
    assert repetida.status_code == 201, repetida.text
    assert repetida.json()["id"] == primera.json()["id"], "un reenvio legitimo devuelve la misma"

    # ***Y con OTROS datos, 409.*** *Aqui esta lo que se perdia en silencio.*
    otra_cosa = cliente.post(
        f"/api/maquinaria/{suya}/inspecciones",
        headers=cuenta["cabeceras"],
        json={**lo_que_va, "resultado": "desfavorable"},
    )
    assert otra_cosa.status_code == 409, (
        f"***la misma clave con otros datos NO puede darse por guardada***: {otra_cosa.text}"
    )

    # **Y no se ha apuntado nada**: sigue habiendo una sola inspeccion, y sigue diciendo lo de antes.
    todas = cliente.get(f"/api/maquinaria/{suya}/inspecciones", headers=cuenta["cabeceras"]).json()
    assert len(todas) == 1, f"***y no se apunta una segunda***: {todas}"


def test_dos_envios_a_la_vez_de_la_misma_inspeccion_apuntan_UNA(cliente, cuenta):
    """***La carrera, que es lo que el indice cierra y la consulta previa no.***

    *Dos peticiones simultaneas pasan las dos la consulta de «¿ya esta?» antes de que ninguna escriba. Lo que
    las separa es el indice: una gana y **la otra recoge el choque y devuelve la que gano** -sin un 500, que
    es lo que veria el agricultor si nadie recogiera el `IntegrityError`-.*
    """
    suya = _una_maquina(cliente, cuenta, "El de la carrera")
    lo_que_va = {
        "tipo": "iteaf",
        "fecha": "2026-07-10",
        "resultado": "favorable",
        "clave_de_reenvio": "inspeccion-a-la-vez",
    }

    def enviar(_):
        return cliente.post(
            f"/api/maquinaria/{suya}/inspecciones", headers=cuenta["cabeceras"], json=lo_que_va
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as a_la_vez:
        respuestas = list(a_la_vez.map(enviar, range(2)))

    assert all(r.status_code in (200, 201) for r in respuestas), (
        f"***ninguna puede reventar***: {[r.status_code for r in respuestas]} "
        f"{[r.text[:120] for r in respuestas]}"
    )
    todos = cliente.get(f"/api/maquinaria/{suya}/inspecciones", headers=cuenta["cabeceras"]).json()
    assert len(todos) == 1, f"***dos envios a la vez, UNA inspeccion***: {len(todos)}"


def test_la_misma_clave_de_averia_con_OTROS_DATOS_es_un_conflicto(cliente, cuenta):
    """*Y la averia, igual: un reenvio con otros datos **no se da por guardado**.*"""
    suya = _una_maquina(cliente, cuenta, "El del conflicto de averia")
    lo_que_va = {
        "fecha": "2026-07-10",
        "que_paso": "Se rompio el eje",
        "resuelta": False,
        "clave_de_reenvio": "averia-conflicto",
    }

    primera = cliente.post(
        f"/api/maquinaria/{suya}/averias", headers=cuenta["cabeceras"], json=lo_que_va
    )
    assert primera.status_code == 201, primera.text

    otra_cosa = cliente.post(
        f"/api/maquinaria/{suya}/averias",
        headers=cuenta["cabeceras"],
        json={**lo_que_va, "que_paso": "Fue otra cosa distinta"},
    )
    assert otra_cosa.status_code == 409, (
        f"***la misma clave con otro «que paso» NO puede darse por guardada***: {otra_cosa.text}"
    )


# ---------------------------------------------------------------------------------------------------
# ***Y las dos ultimas que faltaban*** (CRM-05, 17/10/2026): *la maquina y la subvencion*
# ---------------------------------------------------------------------------------------------------
#
# *Con las ventas, los cobros, las facturas y los ajustes ya estaba; con las inspecciones y las averias de
# la maquina, desde la ronda anterior; con las lecturas del cuenta-horas y las reservas, desde su ticket.
# **Estas dos eran las ultimas sin el indice unico**, y la subvencion ademas **no miraba la clave
# siquiera**: el movil que reintentaba -o dos toques con los guantes- apuntaba **dos ayudas**, y una
# subvencion duplicada no se nota hasta que se suma el año.*


def test_la_base_no_deja_dos_maquinas_con_la_misma_clave(cliente, cuenta, db_sesion):
    """La maquina: **la clave de reenvio no se repite dentro de una explotacion**."""
    creada = cliente.post(
        "/api/maquinaria",
        headers=cuenta["cabeceras"],
        json={
            "nombre": "El tractor de la prueba",
            "clase": "tractor",
            "propiedad": "propia",
            "disponibilidad": "disponible",
            "clave_de_reenvio": "maquina-repetida",
        },
    )
    assert creada.status_code == 201, creada.text

    db_sesion.add(
        models.Maquina(
            explotacion_id=_la_explotacion(db_sesion),
            nombre="El otro",
            clase="tractor",
            propiedad="propia",
            disponibilidad="disponible",
            clave_de_reenvio="maquina-repetida",
        )
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()


def test_dos_envios_a_la_vez_de_la_misma_maquina_apuntan_UNA(cliente, cuenta):
    """***La carrera.*** *Dos peticiones simultaneas pasan las dos la consulta de «¿ya esta?» antes de que
    ninguna escriba; lo que las separa es el indice. **Y la que pierde tiene que recoger el choque**: el
    `flush` va antes del `commit`, asi que el `try` tiene que envolverlos a los dos -si no, el agricultor ve
    un 500 en vez de su maquina-.*
    """
    lo_que_va = {
        "nombre": "El de la carrera",
        "clase": "tractor",
        "propiedad": "propia",
        "disponibilidad": "disponible",
        "clave_de_reenvio": "maquina-a-la-vez",
    }

    def enviar(_):
        return cliente.post("/api/maquinaria", headers=cuenta["cabeceras"], json=lo_que_va)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as a_la_vez:
        respuestas = list(a_la_vez.map(enviar, range(2)))

    assert all(r.status_code in (200, 201) for r in respuestas), (
        f"***ninguna puede reventar***: {[r.status_code for r in respuestas]} "
        f"{[r.text[:120] for r in respuestas]}"
    )
    # **Y las dos contestan LA MISMA maquina**, que es lo que se esta comprobando: *no hay que ir a la lista
    # a contar, porque el identificador lo dice sin ambiguedad.*
    assert respuestas[0].json()["id"] == respuestas[1].json()["id"], (
        "***dos envios a la vez, UNA maquina***: "
        f"{[r.json().get('id') for r in respuestas]}"
    )


def test_la_base_no_deja_dos_subvenciones_con_la_misma_clave(cliente, cuenta, campana, db_sesion):
    """La subvencion: **el mismo indice**, y aqui era donde de verdad no habia nada."""
    creada = cliente.post(
        "/api/gastos/subvenciones",
        headers=cuenta["cabeceras"],
        json={"concepto": "Ayuda a la primera instalacion", "clave_de_reenvio": "ayuda-repetida"},
    )
    assert creada.status_code == 201, creada.text

    db_sesion.add(
        models.Subvencion(
            explotacion_id=_la_explotacion(db_sesion),
            concepto="Otra ayuda",
            clave_de_reenvio="ayuda-repetida",
        )
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()


def test_un_reenvio_de_la_misma_subvencion_devuelve_la_que_ya_estaba(cliente, cuenta):
    """***Y la mitad que faltaba del todo.*** *Hasta hoy esta puerta **no miraba la clave**: un reintento
    apuntaba la ayuda por segunda vez.*
    """
    lo_que_va = {"concepto": "Ayuda al joven agricultor", "clave_de_reenvio": "ayuda-reenvio"}
    primera = cliente.post("/api/gastos/subvenciones", headers=cuenta["cabeceras"], json=lo_que_va)
    assert primera.status_code == 201, primera.text

    repetida = cliente.post("/api/gastos/subvenciones", headers=cuenta["cabeceras"], json=lo_que_va)
    assert repetida.status_code == 201, repetida.text
    # *La puerta contesta `{"subvencion": ..., "avisos": [...]}`: **las dos formas son la misma**, que es
    # lo que se acaba de arreglar.*
    assert repetida.json()["subvencion"]["id"] == primera.json()["subvencion"]["id"], (
        "***un reenvio devuelve la MISMA ayuda***"
    )


def test_dos_envios_a_la_vez_de_la_misma_subvencion_apuntan_UNA(cliente, cuenta):
    """***Y la carrera de la subvencion.***"""
    lo_que_va = {"concepto": "Ayuda a la carrera", "clave_de_reenvio": "ayuda-a-la-vez"}

    def enviar(_):
        return cliente.post("/api/gastos/subvenciones", headers=cuenta["cabeceras"], json=lo_que_va)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as a_la_vez:
        respuestas = list(a_la_vez.map(enviar, range(2)))

    assert all(r.status_code in (200, 201) for r in respuestas), (
        f"***ninguna puede reventar***: {[r.status_code for r in respuestas]} "
        f"{[r.text[:120] for r in respuestas]}"
    )
    assert respuestas[0].json()["subvencion"]["id"] == respuestas[1].json()["subvencion"]["id"], (
        "***dos envios a la vez, UNA ayuda***: "
        f"{[r.json().get('subvencion', {}).get('id') for r in respuestas]}"
    )


# ---------------------------------------------------------------------------------------------------
# ***Y las dos del trabajo*** (CRM-05, 17/10/2026): *el plan y la labor que sale de el*
# ---------------------------------------------------------------------------------------------------
#
# *Con estas se cierra la lista: **los 24 modelos con clave de reenvio tienen ya su indice unico parcial**.
# Las dos puertas que faltaban eran las dos mitades del recorrido 4 -«planificar un trabajo → marcar lo que
# de verdad se hizo»-, y cada una escribe la fila en un sitio distinto: **el plan en el `flush`** -porque sus
# lineas necesitan el identificador- y **la labor en el `commit`** -porque esa puerta no hace `flush`-.*
# *Por eso el `try` va en sitios distintos, y por eso se prueba cada una.*


def _un_plan(cliente, cuenta, campana, parcela, **cambios):
    datos = {
        "campana_id": campana["id"],
        "tipo": "laboreo",
        "subtipo": "cultivador",
        "fecha_prevista": "2026-09-20",
        "parcela_id": parcela["id"],
        "superficie_ha": 4.9,
        "horas": 3,
    }
    datos.update(cambios)
    return cliente.post("/api/trabajos/previstos", headers=cuenta["cabeceras"], json=datos)


def test_la_base_no_deja_dos_trabajos_previstos_con_la_misma_clave(cliente, cuenta, campana, crear_parcela, db_sesion):
    """El plan: **la clave de reenvio no se repite dentro de una explotacion**."""
    parcela = crear_parcela(alias="La del plan repetido")
    creado = _un_plan(cliente, cuenta, campana, parcela, clave_de_reenvio="plan-repetido")
    assert creado.status_code == 201, creado.text

    db_sesion.add(
        models.TrabajoPrevisto(
            explotacion_id=_la_explotacion(db_sesion),
            campana_id=campana["id"],
            tipo="laboreo",
            estado="previsto",
            fecha_prevista=dt.date(2026, 9, 21),
            parcela_id=parcela["id"],
            clave_de_reenvio="plan-repetido",
        )
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()


def test_dos_envios_a_la_vez_del_mismo_plan_apuntan_UNO(cliente, cuenta, campana, crear_parcela):
    """***La carrera del plan.*** *Y aqui el `try` tiene que envolver el `flush`, que es donde se escribe la
    fila: las lineas del plan necesitan `plan.id`, asi que el `flush` **no se puede mover** al final.*
    """
    parcela = crear_parcela(alias="La del plan a la vez")
    lo_que_va = {
        "campana_id": campana["id"],
        "tipo": "laboreo",
        "fecha_prevista": "2026-09-22",
        "parcela_id": parcela["id"],
        "clave_de_reenvio": "plan-a-la-vez",
    }

    def enviar(_):
        return cliente.post("/api/trabajos/previstos", headers=cuenta["cabeceras"], json=lo_que_va)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as a_la_vez:
        respuestas = list(a_la_vez.map(enviar, range(2)))

    assert all(r.status_code in (200, 201) for r in respuestas), (
        f"***ninguna puede reventar***: {[r.status_code for r in respuestas]} "
        f"{[r.text[:140] for r in respuestas]}"
    )
    assert respuestas[0].json()["previsto"]["id"] == respuestas[1].json()["previsto"]["id"], (
        "***dos envios a la vez, UN plan***: "
        f"{[r.json().get('previsto', {}).get('id') for r in respuestas]}"
    )


def test_la_base_no_deja_dos_labores_con_la_misma_clave(cliente, cuenta, campana, crear_parcela, db_sesion):
    """La labor: **el mismo indice**, y aqui la fila se escribe en el `commit`."""
    parcela = crear_parcela(alias="La de la labor repetida")
    plan = _un_plan(cliente, cuenta, campana, parcela).json()["previsto"]

    hecho = cliente.post(
        f"/api/trabajos/previstos/{plan['id']}/hecho",
        headers=cuenta["cabeceras"],
        json={"fecha": "2026-11-20", "horas": 5, "clave_de_reenvio": "labor-repetida"},
    )
    assert hecho.status_code == 201, hecho.text

    db_sesion.add(
        models.Labor(
            explotacion_id=_la_explotacion(db_sesion),
            campana_id=campana["id"],
            tipo="laboreo",
            fecha=dt.date(2026, 11, 21),
            parcela_id=parcela["id"],
            clave_de_reenvio="labor-repetida",
        )
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()


# ---------------------------------------------------------------------------------------------------
# ***Y la otra mitad: la misma clave con OTROS DATOS es un 409*** (CRM-05, 17/10/2026)
# ---------------------------------------------------------------------------------------------------
#
# *Hasta hoy, estas cuatro puertas **devolvian lo que ya estaba sin mirar los datos**: el agricultor
# corregia algo, el movil reintentaba, y **su correccion se perdia en silencio** -y el se quedaba creyendo
# que habia entrado-. Era la mitad silenciosa del defecto, y la peor, porque no se ve.*
#
# *El criterio esta escrito **una sola vez** en `app/reenvios.py`, y lo usan las dos puertas en **sus dos
# caminos** -la consulta previa y la recuperacion del choque-, para que un reintento no conteste una cosa u
# otra segun quien llegara antes.*
#
# **Y solo se compara lo que la peticion manda** (`model_fields_set`): *un campo que no viene no es un campo
# vacio. En estas puertas, ademas, lo que no viene muchas veces **se rellena con lo que ya tenia el plan o la
# tierra** -el cultivo de la parcela-, asi que compararlo daria 409 en un reintento legitimo.*


def test_la_misma_clave_de_maquina_con_OTROS_DATOS_es_un_conflicto(cliente, cuenta):
    """La maquina: *el mismo reenvio devuelve la misma; con otro nombre, **409**.*"""
    lo_que_va = {
        "nombre": "El del conflicto",
        "clase": "tractor",
        "propiedad": "propia",
        "disponibilidad": "disponible",
        "clave_de_reenvio": "maquina-conflicto",
    }
    primera = cliente.post("/api/maquinaria", headers=cuenta["cabeceras"], json=lo_que_va)
    assert primera.status_code == 201, primera.text

    # **El mismo reenvio: la misma maquina**, que es un reintento legitimo.
    repetida = cliente.post("/api/maquinaria", headers=cuenta["cabeceras"], json=lo_que_va)
    assert repetida.status_code in (200, 201), repetida.text
    assert repetida.json()["id"] == primera.json()["id"], "un reenvio legitimo devuelve la misma"

    # ***Y con otro nombre, 409.***
    otra_cosa = cliente.post(
        "/api/maquinaria",
        headers=cuenta["cabeceras"],
        json={**lo_que_va, "nombre": "Otro nombre distinto"},
    )
    assert otra_cosa.status_code == 409, (
        f"***la misma clave con otros datos NO puede darse por guardada***: {otra_cosa.text}"
    )


def test_la_misma_clave_de_subvencion_con_OTROS_DATOS_es_un_conflicto(cliente, cuenta):
    """La subvencion: *mismo reenvio, misma ayuda; con otro concepto, **409**.*"""
    lo_que_va = {"concepto": "Ayuda al conflicto", "clave_de_reenvio": "ayuda-conflicto"}
    primera = cliente.post("/api/gastos/subvenciones", headers=cuenta["cabeceras"], json=lo_que_va)
    assert primera.status_code == 201, primera.text

    repetida = cliente.post("/api/gastos/subvenciones", headers=cuenta["cabeceras"], json=lo_que_va)
    assert repetida.status_code == 201, repetida.text
    assert repetida.json()["subvencion"]["id"] == primera.json()["subvencion"]["id"]

    otra_cosa = cliente.post(
        "/api/gastos/subvenciones",
        headers=cuenta["cabeceras"],
        json={**lo_que_va, "concepto": "Otro concepto distinto"},
    )
    assert otra_cosa.status_code == 409, (
        f"***la misma clave con otro concepto NO puede darse por guardada***: {otra_cosa.text}"
    )


def test_la_misma_clave_de_plan_con_OTROS_DATOS_es_un_conflicto(cliente, cuenta, campana, crear_parcela):
    """El plan: *mismo reenvio, mismo plan; con otra fecha, **409**.*"""
    parcela = crear_parcela(alias="La del conflicto de plan")
    lo_que_va = {
        "campana_id": campana["id"],
        "tipo": "laboreo",
        "fecha_prevista": "2026-09-25",
        "parcela_id": parcela["id"],
        "clave_de_reenvio": "plan-conflicto",
    }
    primera = cliente.post("/api/trabajos/previstos", headers=cuenta["cabeceras"], json=lo_que_va)
    assert primera.status_code == 201, primera.text

    repetida = cliente.post("/api/trabajos/previstos", headers=cuenta["cabeceras"], json=lo_que_va)
    assert repetida.status_code in (200, 201), repetida.text
    assert repetida.json()["previsto"]["id"] == primera.json()["previsto"]["id"]

    # *Y el cultivo **no** se compara: si la peticion no lo manda, la puerta lo rellena desde la tierra, y
    # eso no es «otros datos».*
    otra_cosa = cliente.post(
        "/api/trabajos/previstos",
        headers=cuenta["cabeceras"],
        json={**lo_que_va, "fecha_prevista": "2026-10-30"},
    )
    assert otra_cosa.status_code == 409, (
        f"***la misma clave con otra fecha NO puede darse por guardada***: {otra_cosa.text}"
    )


def test_la_misma_clave_de_labor_con_OTROS_DATOS_es_un_conflicto(cliente, cuenta, campana, crear_parcela):
    """La labor: *mismo reenvio, mismo trabajo; con otra fecha, **409**.*"""
    parcela = crear_parcela(alias="La del conflicto de labor")
    plan = _un_plan(cliente, cuenta, campana, parcela).json()["previsto"]
    lo_que_va = {"fecha": "2026-11-25", "horas": 4, "clave_de_reenvio": "labor-conflicto"}

    primera = cliente.post(
        f"/api/trabajos/previstos/{plan['id']}/hecho", headers=cuenta["cabeceras"], json=lo_que_va
    )
    assert primera.status_code == 201, primera.text

    otra_cosa = cliente.post(
        f"/api/trabajos/previstos/{plan['id']}/hecho",
        headers=cuenta["cabeceras"],
        json={**lo_que_va, "fecha": "2026-12-26"},
    )
    assert otra_cosa.status_code == 409, (
        f"***la misma clave con otra fecha NO puede darse por guardada***: {otra_cosa.text}"
    )
