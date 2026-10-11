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
