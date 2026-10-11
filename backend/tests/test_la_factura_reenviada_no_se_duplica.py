"""El reenvío de una factura: que no se apunte dos veces, y que se distinga del duplicado (09/10/2026).

**Por qué existe.** El encargo lo pidió con estas palabras: *resolver el reenvío de factura en el
servidor, revisando antes los mecanismos que ya existen*, y probar el envío concurrente, la respuesta
perdida y el reintento, la misma clave con contenido distinto, y el reenvío después de la anulación.
La factura era **la única entidad del programa sin clave de reenvío**: todas sus hermanas la tienen
desde el principio (`Recepcion`, `MovimientoDeExistencias`, `Gasto`, `Cobro`, `VentaDeCosecha`…) y su
puerta, `POST /api/facturas`, **siempre insertaba**. Medido antes de tocar nada: dos envíos idénticos
contestaban `201`, `201`, y quedaban dos filas.

Esto ya no es un guion que alguien corre a mano —eso fue lo que dejó pasar el defecto—: son pruebas
obligatorias. Cada una se puso **roja antes** de arreglarlo.

**Las dos cosas que hay que no confundir**, porque son distintas y el agricultor tiene que poder
saber cuál es:

  · El **reenvío técnico**: el mismo comando otra vez (la misma clave de reenvío), que es lo que hace
    la cola del móvil cuando reintenta sin cobertura o cuando la respuesta se perdió por el camino.
    El contrato §2 lo dice literal: *«reenviar el mismo comando devuelve su resultado; no crea otro
    movimiento»*. Se contesta **200 con la factura que ya estaba**.
  · El **posible duplicado comercial**: otra petición, pero el mismo papel —mismo proveedor, mismo
    número, mismo año y mismo total—. Es el contrato §S10 (*«duplicado exacto por huella; posible
    duplicado por emisor/número/fecha/total»*). También se devuelve la que había, reconociéndolo por
    `numero_de_factura`, y **en la duda no se duplica**: es la misma decisión que ya tomaba la puerta
    de los albaranes.

Y aparte está el **conflicto claro**, que sí es un error: la misma clave de reenvío con datos
distintos. Una petición identifica un comando, y un comando no tiene dos cuerpos. Eso se contesta
**409** y que lo mire el agricultor, en vez de que el programa elija cuál de las dos facturas vale.
"""

from __future__ import annotations

import concurrent.futures
import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app import models, textos

# Una factura completa, como la manda la pantalla. Se escribe entera porque el alta acepta esto y
# nada más: si aquí se colara un campo que la API no tiene, la prueba estaría probando otra cosa.
UNA_FACTURA = {
    "fecha": "2026-03-15",
    "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
    "proveedor_nif": "F37012345",
    "numero_factura": "2026/00123",
    "base_imponible": 170.0,
    "cuota_iva": 35.70,
    "tipo_iva_pct": 21.0,
    "total": 205.70,
    "leida_por": "a mano",
    "lineas": [
        {
            "descripcion": "GLIFOSATO 36% SL 20 L",
            "cantidad": 5,
            "unidad": "L",
            "precio_unitario": 34.0,
            "importe": 170.0,
        }
    ],
}


def _cuerpo(**cambios) -> dict:
    cuerpo = json.loads(json.dumps(UNA_FACTURA))  # copia de verdad, para no pisar la de arriba
    cuerpo.update(cambios)
    return cuerpo


def _enviar(cliente, cabeceras, *, clave=None, **cambios):
    """Manda la factura como la manda la pantalla: `multipart` con el campo `datos`.

    **Y sin fichero**, que es el caso del reenvío: el móvil reintenta el mismo cuerpo, y el fichero
    tiene su propia puerta. Así esta prueba mide el reenvío del **comando**, no el de un adjunto.
    """
    cuerpo = _cuerpo(**cambios)
    if clave is not None:
        cuerpo["clave_de_reenvio"] = clave
    return cliente.post("/api/facturas", headers=cabeceras, data={"datos": json.dumps(cuerpo)})


def _cuantas_facturas(db) -> int:
    return db.scalar(select(func.count()).select_from(models.Factura))


def _la_de_id(db, factura_id: int) -> models.Factura:
    return db.get(models.Factura, factura_id)


def test_el_mismo_comando_dos_veces_apunta_una_sola_factura(cliente, cuenta, db_sesion):
    """El reenvío técnico: la misma clave, el mismo cuerpo. **Una fila y la misma respuesta.**"""
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-1")
    assert primera.status_code == 201, primera.text
    suya = primera.json()

    segunda = _enviar(cliente, cuenta["cabeceras"], clave="peticion-1")
    assert segunda.status_code == 200, segunda.text
    otra_vez = segunda.json()

    assert otra_vez["id"] == suya["id"], "se devuelve **la que ya estaba**, no una nueva"
    assert otra_vez["ya_estaba"] is True
    assert otra_vez["como_se_reconocio"] == "clave_de_reenvio"
    assert _cuantas_facturas(db_sesion) == 1, "el reenvío no puede dejar dos facturas"


def test_si_la_respuesta_se_perdio_y_el_movil_reintenta_tres_veces_sigue_habiendo_una(
    cliente, cuenta, db_sesion
):
    """La respuesta perdida y el reintento: es el caso que de verdad pasa en el campo.

    Sin cobertura, el móvil manda la petición, no le llega la respuesta y la vuelve a mandar. Aquí se
    reintenta **tres veces** y se exige lo mismo: una factura, y las tres veces la misma respuesta.
    """
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-perdida")
    assert primera.status_code == 201, primera.text
    ident = primera.json()["id"]

    for intento in range(3):
        repetida = _enviar(cliente, cuenta["cabeceras"], clave="peticion-perdida")
        assert repetida.status_code == 200, f"reintento {intento}: {repetida.text}"
        assert repetida.json()["id"] == ident
        assert repetida.json()["ya_estaba"] is True

    assert _cuantas_facturas(db_sesion) == 1


def test_dos_envios_a_la_vez_apuntan_una_sola_factura(cliente, cuenta, db_sesion):
    """El envío concurrente: los dos a la vez, y **no pueden salir dos facturas**.

    Se mandan dos peticiones en paralelo con la misma clave. La invariante que se exige vale tanto si
    de verdad se solapan como si el servidor las atiende una detrás de otra: **exactamente una fila, y
    como mucho un 201**. Y la garantía de que no pueden colarse las dos cuando se solapan de verdad no
    es del código, es **de la base**: el índice único parcial `uq_factura_reenvio` (ver la última
    prueba de este fichero), que es lo que hace que dos transacciones simultáneas no puedan confirmar
    la misma clave.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as a_la_vez:
        las_dos = list(
            a_la_vez.map(
                lambda _: _enviar(cliente, cuenta["cabeceras"], clave="peticion-a-la-vez"),
                range(2),
            )
        )

    codigos = sorted(respuesta.status_code for respuesta in las_dos)
    assert codigos in ([200, 201], [200, 200]), f"códigos inesperados: {codigos}"
    assert _cuantas_facturas(db_sesion) == 1, "dos envíos a la vez no pueden dejar dos facturas"


def test_la_misma_clave_con_otros_datos_es_un_conflicto_claro(cliente, cuenta, db_sesion):
    """Una petición no tiene dos cuerpos: **409**, y no se apunta ninguna de las dos versiones.

    Es el caso que el encargo pide separar del reenvío: aquí no se devuelve nada «como si ya
    estuviera», porque lo que llega **no es lo que se atendió**. El programa no elige: lo dice.
    """
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-2")
    assert primera.status_code == 201, primera.text
    ident = primera.json()["id"]

    con_otros_importes = _enviar(
        cliente, cuenta["cabeceras"], clave="peticion-2", total=999.99, base_imponible=826.44
    )

    assert con_otros_importes.status_code == 409, con_otros_importes.text
    assert textos.mensaje("AL26_la_misma_clave_con_otros_datos") in con_otros_importes.text
    assert _cuantas_facturas(db_sesion) == 1
    assert _la_de_id(db_sesion, ident).total == pytest.approx(205.70), "la que había no se toca"


def test_el_mismo_papel_con_otra_peticion_no_se_apunta_dos_veces(cliente, cuenta, db_sesion):
    """El **posible duplicado comercial**: otra petición, pero el mismo papel.

    Se reconoce por el número y el proveedor —no por la clave—, y se dice cuál de las dos cosas es,
    que es justo lo que el encargo pide no confundir.
    """
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-3")
    assert primera.status_code == 201, primera.text
    suya = primera.json()

    otra_peticion = _enviar(cliente, cuenta["cabeceras"], clave="peticion-4")
    assert otra_peticion.status_code == 200, otra_peticion.text
    de_vuelta = otra_peticion.json()

    assert de_vuelta["id"] == suya["id"]
    assert de_vuelta["ya_estaba"] is True
    assert de_vuelta["como_se_reconocio"] == "numero_de_factura"
    assert "no se ha contado dos veces" in " ".join(de_vuelta["avisos"])
    assert _cuantas_facturas(db_sesion) == 1


def test_el_mismo_papel_con_otros_importes_avisa_y_no_duplica(cliente, cuenta, db_sesion):
    """El mismo número, el mismo año y **el mismo total**, pero el detalle no dice lo mismo.

    Aquí está el caso que de verdad llega a este aviso, y se aprendió midiendo: el **total forma
    parte de lo que identifica al papel** —el contrato §S10 dice «emisor/número/fecha/total»—, así que
    dos facturas con el mismo número y **distinto total** no son el mismo papel para el programa (ver
    la prueba de abajo, que lo deja escrito). Lo que sí llega aquí es el mismo papel con el **detalle**
    mal: la base imponible o el IVA de una de las dos está equivocado. Entonces no se apunta la
    segunda —eso dejaría dos cifras del mismo papel— pero tampoco se calla: el aviso dice que hay que
    mirarlo.
    """
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-5")
    assert primera.status_code == 201, primera.text

    con_el_detalle_mal = _enviar(
        cliente,
        cuenta["cabeceras"],
        clave="peticion-6",
        base_imponible=160.0,  # el total no se toca: es lo que identifica el papel
        cuota_iva=45.70,
    )
    assert con_el_detalle_mal.status_code == 200, con_el_detalle_mal.text
    de_vuelta = con_el_detalle_mal.json()

    assert de_vuelta["ya_estaba"] is True
    assert de_vuelta["como_se_reconocio"] == "numero_de_factura"
    assert textos.mensaje("AL28_ese_numero_ya_esta_con_otros_importes") in de_vuelta["avisos"]
    assert _cuantas_facturas(db_sesion) == 1


def test_el_mismo_numero_con_otro_total_es_otra_factura(cliente, cuenta, db_sesion):
    """**El límite, escrito a propósito**: mismo número y otro total **sí** son dos facturas.

    Esto no es un descuido: el contrato (§S10) dice que el posible duplicado se reconoce por
    **emisor, número, fecha y total**, así que un total distinto es, para el programa, otro papel —y
    tratarlo como el mismo sería negarse a apuntar una factura de verdad—. Queda escrito aquí para
    que nadie lea la prueba de arriba como «cualquier cosa con el mismo número se rechaza»: lo que
    hace el programa es reconocer el **mismo papel**, no el mismo número a secas.
    """
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-10")
    assert primera.status_code == 201, primera.text

    con_otro_total = _enviar(
        cliente, cuenta["cabeceras"], clave="peticion-11", total=999.99, base_imponible=826.44
    )
    assert con_otro_total.status_code == 201, con_otro_total.text
    assert con_otro_total.json()["ya_estaba"] is False
    assert _cuantas_facturas(db_sesion) == 2


def test_un_reenvio_despues_de_anularla_la_vuelve_a_apuntar(cliente, cuenta, db_sesion):
    """El reenvío después de la anulación: **la anulada no ocupa su clave**, y se puede rehacer.

    Es la decisión que la casa ya tomó con los albaranes y con los movimientos, y está escrita en sus
    modelos: *«con un `UniqueConstraint` a secas, un albarán anulado seguía ocupando su clave y el
    agricultor no podía volver a apuntarlo desde el móvil —que reenvía con la misma clave—: le salía
    un error de la base. **Anular existe justo para poder apuntar la buena después**»*. Aquí se exige
    lo mismo para la factura: la anulada se queda anulada, con su motivo, y el reenvío crea la buena.
    """
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-7")
    assert primera.status_code == 201, primera.text
    ident = primera.json()["id"]

    anulada = cliente.post(
        f"/api/facturas/{ident}/anular",
        headers=cuenta["cabeceras"],
        json={"motivo": "me equivoqué de proveedor"},
    )
    assert anulada.status_code == 200, anulada.text
    assert anulada.json()["anulada"] is True

    # La misma petición otra vez: ahora **sí** tiene que apuntarse, porque la que había ya no vale.
    de_nuevo = _enviar(cliente, cuenta["cabeceras"], clave="peticion-7")
    assert de_nuevo.status_code == 201, de_nuevo.text
    assert de_nuevo.json()["id"] != ident, "la buena es una fila nueva, no la anulada resucitada"

    assert _cuantas_facturas(db_sesion) == 2, "la anulada se conserva con su motivo"
    la_vieja = _la_de_id(db_sesion, ident)
    assert la_vieja.anulada is True
    assert la_vieja.motivo_anulacion == "me equivoqué de proveedor"


def test_la_clave_de_reenvio_no_se_pisa_entre_explotaciones(cliente, cuenta, crear_cuenta, db_sesion):
    """El aislamiento: la misma clave en otra finca **es otra petición**, y no se estorban.

    Si la clave fuera única en toda la base, la primera finca que usara «peticion-8» le estaría
    gastando el nombre a las demás. El índice único es por explotación, y esto lo exige.
    """
    la_otra = crear_cuenta("otro@ejemplo.test", nombre="Otro agricultor", nif="12345678Z")

    mia = _enviar(cliente, cuenta["cabeceras"], clave="peticion-8")
    suya = _enviar(cliente, la_otra["cabeceras"], clave="peticion-8")

    assert mia.status_code == 201, mia.text
    assert suya.status_code == 201, suya.text
    assert mia.json()["id"] != suya.json()["id"]
    assert _cuantas_facturas(db_sesion) == 2


def test_una_factura_sin_numero_avisa_de_que_no_se_pudo_comprobar(cliente, cuenta, db_sesion):
    """Cuando no se puede saber, **se dice**: «no lo sé» no es un «no».

    Sin número de factura no hay forma de reconocer el papel, así que se apunta igual —lo que llegó,
    llegó— y la respuesta declara que no se ha podido comprobar. Es la misma mitad de la regla que en
    los albaranes (`AL5…`).
    """
    sin_numero = _enviar(cliente, cuenta["cabeceras"], clave="peticion-9", numero_factura=None)
    assert sin_numero.status_code == 201, sin_numero.text

    devuelta = sin_numero.json()
    assert textos.mensaje("AL27_no_se_pudo_comprobar_si_ya_estaba_la_factura") in devuelta["avisos"]
    assert devuelta["ya_estaba"] is False
    assert _cuantas_facturas(db_sesion) == 1


def test_la_base_no_deja_dos_veces_la_misma_clave(cliente, cuenta, db_sesion):
    """**La garantía de verdad del envío concurrente**: la base, no el código.

    Dos peticiones simultáneas pueden pasar las dos por la comprobación del código antes de que
    ninguna haya escrito —eso es una carrera, y ninguna comprobación en Python la cierra—. Lo que la
    cierra es el índice único parcial `uq_factura_reenvio`, y aquí se comprueba que está y que muerde:
    se intenta meter a mano una segunda factura con la misma clave de la misma finca y la base la
    rechaza. La prueba es contra la base a propósito: si alguien quitara el índice, el reenvío
    seguiría funcionando «casi siempre», que es la peor clase de funcionar.
    """
    from app.database import engine

    assert engine.dialect.name == "sqlite", "esta prueba habla del índice de SQLite"
    explotacion_id = db_sesion.scalar(select(models.Explotacion.id))

    db_sesion.add(
        models.Factura(explotacion_id=explotacion_id, clave_de_reenvio="la-misma", total=1.0)
    )
    db_sesion.commit()

    db_sesion.add(
        models.Factura(explotacion_id=explotacion_id, clave_de_reenvio="la-misma", total=2.0)
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()

    # Y **la anulada no ocupa la clave**, que es lo que permite volver a apuntarla: la misma clave,
    # pero con la primera anulada, sí entra.
    db_sesion.add(
        models.Factura(
            explotacion_id=explotacion_id, clave_de_reenvio="otra", anulada=True, total=1.0
        )
    )
    db_sesion.commit()
    db_sesion.add(
        models.Factura(explotacion_id=explotacion_id, clave_de_reenvio="otra", total=2.0)
    )
    db_sesion.commit()
