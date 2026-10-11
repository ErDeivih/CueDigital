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


def test_el_mismo_papel_con_otro_detalle_no_se_descarta_en_silencio(cliente, cuenta, db_sesion):
    """El mismo papel que **dice otra cosa**: **409**, y con el que había delante para decidir.

    **Esto cambió el 09/10/2026, a petición de David.** Antes se contestaba 200 con un aviso: la factura
    que había se devolvía y **lo que acababa de escribir el agricultor se perdía en silencio** —un aviso
    que nadie lee y unos datos que no se guardan—. Lo que él pidió es que un posible duplicado comercial
    con diferencias **no se descarte callando**: se para, se dice qué factura es la que ya está (con su
    número, su fecha y su total) y que decida: corregir la que había, o apuntar esta con su número.

    Aquí está el caso que llega a este aviso, y se aprendió midiendo: el **total forma parte de lo que
    identifica al papel** —el contrato §S10 dice «emisor/número/fecha/total»—, así que dos facturas con el
    mismo número y **distinto total** no son el mismo papel (ver la prueba de abajo, que lo deja escrito).
    Lo que sí llega es el mismo papel con el **detalle** mal: la base imponible o el IVA de una de las dos
    está equivocado.
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
    assert con_el_detalle_mal.status_code == 409, (
        f"un documento con diferencias no se puede descartar en silencio: {con_el_detalle_mal.text}"
    )
    assert "dice otra cosa" in con_el_detalle_mal.text
    # Y se dice **cuál** es la que ya está, que es lo que permite decidir sin buscar entre los papeles.
    assert "2026/00123" in con_el_detalle_mal.text
    assert "205,70" in con_el_detalle_mal.text
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


def test_un_reenvio_despues_de_anularla_no_crea_otra_factura(cliente, cuenta, db_sesion):
    """El reenvío de un comando **ya anulado**: se devuelve su estado, y **no se crea otra factura**.

    **Esto cambió el 09/10/2026, y a petición expresa.** Antes la anulada no ocupaba su clave —era la
    decisión que la casa había tomado con los albaranes y los movimientos— y el reenvío creaba una
    factura nueva. El problema, que señaló David al revisar esto: así **no se distingue una alta nueva
    deliberada de un reintento viejo que llega tarde**. Un móvil sin cobertura que reintenta el comando
    de ayer, después de que alguien anulara aquella factura, no está pidiendo «apunta esta otra»: está
    pidiendo lo mismo de siempre, y recibía una factura nueva sin saberlo.

    Ahora la clave **no se puede reutilizar nunca** (el índice único ya no excluye las anuladas), y el
    reenvío del comando original contesta **200 con la factura anulada y su motivo**, diciendo que para
    darla de alta otra vez hace falta **una petición nueva**.
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

    # El mismo comando otra vez: **el estado, no una factura nueva**.
    de_nuevo = _enviar(cliente, cuenta["cabeceras"], clave="peticion-7")
    assert de_nuevo.status_code == 200, de_nuevo.text
    devuelta = de_nuevo.json()
    assert devuelta["id"] == ident, "es la misma factura, la anulada, no una nueva"
    assert devuelta["anulada"] is True
    assert devuelta["motivo_anulacion"] == "me equivoqué de proveedor"
    assert "anulada" in " ".join(devuelta["avisos"]).lower(), devuelta["avisos"]
    assert _cuantas_facturas(db_sesion) == 1, "el reenvío de un comando anulado no crea otra factura"

    # **Y la misma clave con otro contenido sigue siendo un conflicto**, aunque esté anulada: la clave
    # identifica un comando, y ese comando no se puede reciclar para otra cosa.
    otro_contenido = _enviar(cliente, cuenta["cabeceras"], clave="peticion-7", total=999.99)
    assert otro_contenido.status_code == 409, otro_contenido.text
    assert _cuantas_facturas(db_sesion) == 1

    # **La alta nueva deliberada se hace con una clave nueva**, y entonces sí entra.
    la_buena = _enviar(cliente, cuenta["cabeceras"], clave="peticion-7-bis", total=999.99)
    assert la_buena.status_code == 201, la_buena.text
    assert la_buena.json()["id"] != ident
    assert _cuantas_facturas(db_sesion) == 2, "la anulada se conserva con su motivo, y la nueva entra"
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


def test_la_misma_clave_con_otras_notas_o_otro_iva_tambien_es_un_conflicto(cliente, cuenta, db_sesion):
    """El 409 cubría solo los importes: con otras notas o otro IVA los datos nuevos **se tiraban**.

    Lo encontró el revisor: la misma clave con `tipo_iva_pct` distinto o con otras notas contestaba 200
    «ya estaba» y **lo que llegaba se perdía en silencio**, sin decir nada. Una petición identifica un
    comando: si el cuerpo no es el mismo, no es el mismo comando.
    """
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-12")
    assert primera.status_code == 201, primera.text

    con_otro_iva = _enviar(cliente, cuenta["cabeceras"], clave="peticion-12", tipo_iva_pct=10.0)
    assert con_otro_iva.status_code == 409, con_otro_iva.text
    assert textos.mensaje("AL26_la_misma_clave_con_otros_datos") in con_otro_iva.text

    con_otras_notas = _enviar(
        cliente, cuenta["cabeceras"], clave="peticion-12", notas="esto no lo había dicho"
    )
    assert con_otras_notas.status_code == 409, con_otras_notas.text
    assert _cuantas_facturas(db_sesion) == 1


def test_reintentar_despues_de_corregir_la_factura_no_es_un_conflicto(cliente, cuenta, db_sesion):
    """El móvil que reintenta después de una corrección: **200 con la factura como está hoy**.

    Lo encontró el revisor: apuntar con la clave K, corregir la factura y volver a mandar **el mismo
    cuerpo de antes** contestaba 409 «esa petición ya se atendió, pero con otros datos». No es un
    conflicto: el comando se atendió y su resultado cambió **porque el agricultor lo cambió él**. A un
    móvil que reintenta sin cobertura no se le puede presentar eso como un error.
    """
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-13")
    assert primera.status_code == 201, primera.text
    ident = primera.json()["id"]

    correccion = cliente.put(
        f"/api/facturas/{ident}",
        headers=cuenta["cabeceras"],
        json=_cuerpo(
            numero_factura="2026/00123",
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 20 L (corregido)",
                    "cantidad": 5,
                    "unidad": "L",
                    "precio_unitario": 34.0,
                    "importe": 170.0,
                }
            ],
        ),
    )
    assert correccion.status_code == 200, correccion.text

    reintento = _enviar(cliente, cuenta["cabeceras"], clave="peticion-13")

    assert reintento.status_code == 200, (
        f"reintentar el mismo comando después de corregir no puede ser un {reintento.status_code}: "
        f"{reintento.text}"
    )
    assert reintento.json()["id"] == ident, "se devuelve la factura de esa petición, no otra"
    assert reintento.json()["ya_estaba"] is True
    assert reintento.json()["lineas"][0]["descripcion"].endswith("(corregido)"), (
        "y se devuelve **como está hoy**, con la corrección dentro"
    )
    assert any("se corrigió después" in aviso for aviso in reintento.json()["avisos"]), (
        "y se dice por qué no coincide: " + str(reintento.json()["avisos"])
    )
    assert _cuantas_facturas(db_sesion) == 1


def test_la_misma_clave_con_otro_contenido_es_conflicto_aunque_haya_correcciones(
    cliente, cuenta, db_sesion
):
    """**El otro contenido no se puede colar por haber una corrección** (09/10/2026).

    Aquí estaba el agujero que señaló David al revisar esto: para no dar un 409 falso al móvil que
    reintenta después de una corrección, la puerta miraba **solo que hubiera habido una corrección**, sin
    distinguir *el reenvío del comando original* de *otra petición distinta con la misma clave*. Así que
    después de corregir una factura, **cualquier cuerpo con aquella clave recibía un 200** y sus datos se
    perdían en silencio: exactamente lo que la clave de reenvío existe para impedir.

    La solución es **guardar la huella del comando original** (`huella_de_la_peticion`): si lo que llega
    tiene esa huella, es el reenvío de siempre y se contesta con el registro actual; si no la tiene, es
    otra cosa y es un **409**, haya correcciones o no.
    """
    original = _cuerpo()
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-14")
    assert primera.status_code == 201, primera.text
    ident = primera.json()["id"]

    correccion = cliente.put(
        f"/api/facturas/{ident}",
        headers=cuenta["cabeceras"],
        json=_cuerpo(
            numero_factura="2026/00123",
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 20 L (corregido)",
                    "cantidad": 5,
                    "unidad": "L",
                    "precio_unitario": 34.0,
                    "importe": 170.0,
                }
            ],
        ),
    )
    assert correccion.status_code == 200, correccion.text

    # El comando ORIGINAL, tal cual **y con su clave**: es un reenvío, y se contesta con el registro
    # actual. (Sin la clave no sería el mismo comando: sería otra petición hablando del mismo papel.)
    el_de_siempre = cliente.post(
        "/api/facturas",
        headers=cuenta["cabeceras"],
        data={"datos": json.dumps({**original, "clave_de_reenvio": "peticion-14"})},
    )
    assert el_de_siempre.status_code == 200, el_de_siempre.text
    assert el_de_siempre.json()["id"] == ident

    # Y **otro** cuerpo con la misma clave, después de la corrección: conflicto.
    otro = _enviar(cliente, cuenta["cabeceras"], clave="peticion-14", notas="esto no lo había dicho")
    assert otro.status_code == 409, (
        f"otro contenido con la misma clave no puede contestar {otro.status_code}: {otro.text}"
    )
    assert textos.mensaje("AL26_la_misma_clave_con_otros_datos") in otro.text
    assert _cuantas_facturas(db_sesion) == 1


def test_una_factura_legada_sin_huella_no_inventa_su_comando_original(cliente, cuenta, db_sesion):
    """Una factura de **antes de que hubiera huella**: se dice qué se puede comprobar y qué no.

    **Lo pidió el revisor** (11/10/2026): *«Migración de huellas históricas. Se calcula con el contenido
    actual, que puede ser ya corregido. No describirla como prueba recuperada del comando original.
    Añadir caso legado corregido y explicitar qué reenvíos pueden verificarse y cuáles requieren revisión;
    no inventar la petición perdida»*.

    La migración rellena la huella con **lo que la factura dice hoy**, así que:

      · el reenvío de **ese** contenido se reconoce —y eso es lo que se puede afirmar: *este comando ya se
        atendió*—;
      · el de **otro** contenido es un **conflicto**, y eso es lo prudente: **no se sabe** si es el comando
        original (la factura pudo corregirse antes de que existiera la huella) o una petición distinta, y en
        la duda el programa **no acepta en silencio** algo que no puede comprobar. Queda para revisión
        humana, no se resuelve inventando la petición perdida.

    Aquí se reproduce el caso legado **por el camino de verdad**: se apunta la factura y luego se le borra
    la huella a mano, que es exactamente como queda una factura de antes en la base migrada.
    """
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-legada")
    assert primera.status_code == 201, primera.text
    ident = primera.json()["id"]

    # La migración de una instalación antigua rellena la huella con lo que la factura dice; aquí se simula
    # el estado **de antes de la migración**: con clave y sin huella.
    la_factura = _la_de_id(db_sesion, ident)
    la_factura.huella_de_la_peticion = None
    db_sesion.commit()
    assert _la_de_id(db_sesion, ident).huella_de_la_peticion is None

    # **Lo que sí se puede afirmar**: el mismo contenido es el comando que se atendió.
    el_de_siempre = _enviar(cliente, cuenta["cabeceras"], clave="peticion-legada")
    assert el_de_siempre.status_code == 200, el_de_siempre.text
    assert el_de_siempre.json()["id"] == ident
    assert _cuantas_facturas(db_sesion) == 1

    # **Lo que no**: otro contenido con la misma clave no se puede dar por bueno —no se sabe si es el
    # comando original de una factura corregida— y se contesta conflicto, sin tocar nada.
    otro = _enviar(cliente, cuenta["cabeceras"], clave="peticion-legada", notas="otra cosa distinta")
    assert otro.status_code == 409, (
        f"con una huella que no se puede comprobar no se puede contestar {otro.status_code}: {otro.text}"
    )
    assert textos.mensaje("AL26_la_misma_clave_con_otros_datos") in otro.text
    assert _cuantas_facturas(db_sesion) == 1, "y no se ha apuntado nada"


def test_el_mismo_papel_con_otro_total_se_apunta_pero_no_en_silencio(cliente, cuenta, db_sesion):
    """Mismo emisor, número y año con **otro total**: se apunta, y **se dice cuál es la otra**.

    **Lo pidió el revisor** (CRM-00, 11/10/2026): *«revisar sin ampliar alcance el cambio de clave de papel
    ante variaciones de total y proveedor. Identidad del documento no es solo igualdad de importe. Incluir
    mismo emisor/número/año con total corregido»*.

    El **tratamiento**, que es lo que este caso documenta:

      · La decisión **no cambia**: el contrato §S10 reconoce el papel por emisor, número, fecha **y total**,
        así que un total distinto es otro documento y se apunta (hay una prueba por encima que lo exige).
      · Lo que cambia es que **deja de ser mudo**. Antes se creaba la segunda sin decir nada, y el caso que
        llega de verdad no es «dos facturas del mismo número»: es un número o un importe **tecleado mal**
        (663 por 636). Con el aviso, el agricultor ve que tiene dos y cuál era la otra.
      · Y no se convierte en un **409** a propósito: bloquearlo dejaría sin salida a las dos facturas
        legítimas del mismo número y año, y el programa no puede decidir cuál de las dos sobra.
    """
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-20")
    assert primera.status_code == 201, primera.text
    assert primera.json()["avisos"] == [], "la primera no tiene nada que avisar"

    # El mismo número y el mismo año, con las cifras bailadas (el caso real: 663 tecleado como 636).
    con_otro_total = _enviar(
        cliente, cuenta["cabeceras"], clave="peticion-21", total=636.0, base_imponible=636.0
    )
    assert con_otro_total.status_code == 201, con_otro_total.text
    avisos = con_otro_total.json()["avisos"]
    assert any("otro importe" in aviso for aviso in avisos), (
        f"apuntar la segunda sin decir que ya había otra por otro importe es lo que había que quitar: {avisos}"
    )
    # Y el aviso **nombra la otra**, que es lo que permite encontrarla: su número y su fecha.
    assert "2026/00123" in " ".join(avisos)
    assert "15/03/2026" in " ".join(avisos)
    assert _cuantas_facturas(db_sesion) == 2, "las dos están: la decisión del contrato no cambia"


def test_el_mismo_numero_en_otro_ano_es_otro_documento_y_no_avisa(cliente, cuenta, db_sesion):
    """El mismo número en **otro año** es otro documento, y no hay nada que avisar.

    Es la otra mitad de la decisión: las numeraciones se reinician cada año, así que «2026/00123» y
    «2025/00123» del mismo proveedor son dos papeles distintos —y el aviso de «ya tienes otra con ese
    número» sería un ruido que aparecería siempre—. Se deja escrito para que nadie lo «arregle» metiendo
    el año fuera de la comparación.
    """
    del_2026 = _enviar(cliente, cuenta["cabeceras"], clave="peticion-22")
    assert del_2026.status_code == 201, del_2026.text

    del_2025 = _enviar(cliente, cuenta["cabeceras"], clave="peticion-23", fecha="2025-03-15")
    assert del_2025.status_code == 201, del_2025.text
    assert del_2025.json()["avisos"] == [], (
        "el mismo número de otro año no es el mismo papel: avisar aquí sería ruido en cada factura"
    )
    assert _cuantas_facturas(db_sesion) == 2


def test_sin_importe_en_la_que_llega_no_se_afirma_que_sea_otro_dinero(cliente, cuenta, db_sesion):
    """Datos incompletos: si a la que **llega** le falta el importe, no se afirma que sea otro dinero.

    La regla del «no lo sé» aplicada a este aviso: no se puede decir «esa otra es por otro importe» cuando
    el que llega no trae importe. El papel es el mismo número y el mismo año, así que se contesta con **la
    que había** (`AL25…`) y no se apunta otra vez: **no se pierde nada de lo que él ha escrito**, porque no
    ha escrito ningún importe. Lo que no se hace es inventar una diferencia que no consta.
    """
    con_importe = _enviar(cliente, cuenta["cabeceras"], clave="peticion-24")
    assert con_importe.status_code == 201, con_importe.text

    sin_importe = _enviar(cliente, cuenta["cabeceras"], clave="peticion-25", total=None)
    assert sin_importe.status_code == 200, sin_importe.text
    los_avisos = " ".join(sin_importe.json()["avisos"])
    assert "otro importe" not in los_avisos, (
        f"no se puede afirmar que sea otro dinero si el que llega no trae importe: {los_avisos}"
    )
    assert "ya la tenías apuntada" in los_avisos, f"y hay que decir qué pasa con ese número: {los_avisos}"
    assert _cuantas_facturas(db_sesion) == 1, "el mismo papel no se apunta dos veces"


def test_si_la_que_hay_no_dice_el_importe_y_esta_si_el_importe_no_se_tira(cliente, cuenta, db_sesion):
    """**El caso que sí perdía un dato**: la que hay sin importe, y esta con él.

    Es la otra mitad de los datos incompletos, y la única en la que se podía perder algo de verdad: el
    agricultor apunta la factura sin el total —no lo tenía a mano— y días después la vuelve a mandar **con**
    el total. El papel es el mismo (mismo número, mismo año), así que no se apunta otra vez; pero contestar
    solo «ya estaba» dejaba su importe **sin guardar y sin decirlo**.

    El tratamiento es decirle dónde ponerlo: corrigiendo la factura que ya está (`AL49…`). No se inventa un
    segundo documento para meter el importe, que dejaría dos facturas del mismo papel.
    """
    sin_importe = _enviar(cliente, cuenta["cabeceras"], clave="peticion-26", total=None)
    assert sin_importe.status_code == 201, sin_importe.text
    ident = sin_importe.json()["id"]

    con_importe = _enviar(cliente, cuenta["cabeceras"], clave="peticion-27")
    assert con_importe.status_code == 200, con_importe.text
    assert con_importe.json()["id"] == ident, "se contesta la que ya estaba, no otra"
    los_avisos = " ".join(con_importe.json()["avisos"])
    assert "sin el importe" in los_avisos, (
        f"el importe que acaba de escribir no se puede tirar sin decirlo: {los_avisos}"
    )
    assert _cuantas_facturas(db_sesion) == 1, "y no se ha creado un segundo documento del mismo papel"


def test_corregir_el_numero_cambia_el_papel(cliente, cuenta, db_sesion):
    """Corregir el número (o el total) **cambia el papel**, y la clave del papel se recalcula.

    Sin esto, la corrección dejaría el **documento nuevo sin proteger** y el **viejo ocupado para
    siempre**: apuntar por error el número que se acaba de corregir no encontraría nada, y apuntar el
    número nuevo chocaría con una clave que ya no le corresponde a nadie. Se recalcula en la misma
    preparación que el alta (como la campaña), así que las dos puertas dicen lo mismo.
    """
    primera = _enviar(cliente, cuenta["cabeceras"], clave="peticion-15")
    assert primera.status_code == 201, primera.text
    ident = primera.json()["id"]

    correccion = cliente.put(
        f"/api/facturas/{ident}",
        headers=cuenta["cabeceras"],
        json=_cuerpo(numero_factura="2026/00124"),
    )
    assert correccion.status_code == 200, correccion.text

    # **El papel viejo queda libre**: apuntarlo otra vez es una factura nueva de verdad.
    el_viejo = _enviar(cliente, cuenta["cabeceras"], clave="peticion-16", numero_factura="2026/00123")
    assert el_viejo.status_code == 201, el_viejo.text
    assert _cuantas_facturas(db_sesion) == 2

    # **Y el papel nuevo está ocupado** por la factura corregida: otro envío del mismo documento no entra.
    el_nuevo = _enviar(
        cliente, cuenta["cabeceras"], clave="peticion-17", numero_factura="2026/00124"
    )
    assert el_nuevo.status_code in (200, 409), el_nuevo.text
    assert _cuantas_facturas(db_sesion) == 2, "el papel corregido sigue ocupado, y no por dos"


# **Aqui habia un guardian de texto y ya no esta** (CRM-00, 11/10/2026). Comprobaba, leyendo el fuente
# de `web/app.js`, que el alta de una factura mandara la clave de reenvio y que la soltara al guardar. La
# guia del perfil lo pide justo al reves: *«no ampliar la suite con guardianes de texto que sustituyan
# comprobaciones de comportamiento»*. Ahora se comprueba **por comportamiento** en
# `tests_js/interfaz.test.js`, que ya sabia pulsar «GUARDAR» de verdad:
#
#   - «al confirmar se guarda lo que esta en la pantalla» mira **lo que sale por la puerta** -el cuerpo
#     `FormData` del alta- y exige que lleve su `clave_de_reenvio`;
#   - «la factura siguiente lleva su propia clave de reenvio» apunta **dos** facturas y exige que las
#     claves sean distintas, que es lo que impide que la segunda viaje como un reenvio de la primera.
#
# Para poder mirarlo, el arnes de JavaScript tuvo que aprender a leer el `FormData` (antes lo registraba
# como `null`, asi que **ninguna** prueba veia lo que salia por ese camino).


def test_dos_envios_a_la_vez_del_mismo_papel_apuntan_una_sola_factura(cliente, cuenta, db_sesion):
    """El posible duplicado comercial, **con garantía de verdad** (09/10/2026).

    Lo dijo el revisor con estas palabras: *«80 intentos sin duplicar no constituyen una garantía»*. Y
    tenía razón: la búsqueda previa **no cierra la carrera** —las dos peticiones pueden pasar por ella
    antes de que ninguna escriba—. Lo que la cierra es el **índice único del papel** (`uq_factura_papel`),
    y aquí se exige lo que eso tiene que dar: **una sola fila** y ninguna petición con un error opaco.

    Los dos envíos son **peticiones distintas** (cada una con su clave) del mismo documento, que es como
    llega el caso de verdad: dos pantallas abiertas, o un móvil que no sabía que el otro ya lo había
    mandado.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as a_la_vez:
        las_dos = list(
            a_la_vez.map(
                lambda indice: _enviar(
                    cliente, cuenta["cabeceras"], clave=f"papel-{indice}"
                ),
                range(2),
            )
        )

    codigos = sorted(respuesta.status_code for respuesta in las_dos)
    assert codigos in ([200, 201], [200, 200]), (
        f"las dos del mismo papel tienen que resolverse sin error opaco, y salieron {codigos}: "
        + " | ".join(respuesta.text[:120] for respuesta in las_dos)
    )
    assert _cuantas_facturas(db_sesion) == 1, (
        "el mismo documento no puede quedar dos veces, ni con dos envíos a la vez"
    )


def test_la_base_no_deja_dos_veces_el_mismo_papel(cliente, cuenta, db_sesion):
    """**La garantía, en la base**: el índice único del papel muerde, y una anulada no lo ocupa.

    Es la prueba contra la base a propósito: si alguien quitara el índice, el duplicado comercial
    volvería a depender de que la búsqueda llegara a tiempo, que es la clase de protección que falla
    justo cuando hay prisa (dos envíos a la vez).
    """
    from sqlalchemy.exc import IntegrityError

    from app.database import engine

    assert engine.dialect.name == "sqlite", "esta prueba habla del índice de SQLite"
    explotacion_id = db_sesion.scalar(select(models.Explotacion.id))

    db_sesion.add(
        models.Factura(
            explotacion_id=explotacion_id, clave_del_papel="PROVEEDOR|B-1|2026|121.00", total=121.0
        )
    )
    db_sesion.commit()

    db_sesion.add(
        models.Factura(
            explotacion_id=explotacion_id, clave_del_papel="PROVEEDOR|B-1|2026|121.00", total=121.0
        )
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()

    # Y **una anulada no ocupa el papel**: si el agricultor anuló aquella factura porque estaba mal,
    # tiene que poder apuntar ese mismo documento otra vez (es la parte de la regla vieja que sigue
    # valiendo, porque habla del papel y no de la petición).
    db_sesion.add(
        models.Factura(
            explotacion_id=explotacion_id,
            clave_del_papel="PROVEEDOR|B-2|2026|50.00",
            total=50.0,
            anulada=True,
        )
    )
    db_sesion.commit()
    db_sesion.add(
        models.Factura(
            explotacion_id=explotacion_id, clave_del_papel="PROVEEDOR|B-2|2026|50.00", total=50.0
        )
    )
    db_sesion.commit()


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

    # **Y la anulada también ocupa la clave** (09/10/2026, a petición de David): es lo que hace que el
    # reenvío de un comando anulado conteste con su estado en vez de crear una factura nueva. Antes esta
    # prueba exigía lo contrario —«la anulada no ocupa la clave»—, que era la regla de los albaranes; para
    # la factura se cambió porque no distinguía un alta nueva deliberada de un reintento viejo que llega
    # tarde. Las altas nuevas se hacen con una clave nueva.
    db_sesion.add(
        models.Factura(
            explotacion_id=explotacion_id, clave_de_reenvio="otra", anulada=True, total=1.0
        )
    )
    db_sesion.commit()
    db_sesion.add(
        models.Factura(explotacion_id=explotacion_id, clave_de_reenvio="otra", total=2.0)
    )
    with pytest.raises(IntegrityError):
        db_sesion.commit()
    db_sesion.rollback()

    # Y con una clave **nueva** sí entra: es la forma de dar de alta otra factura de verdad.
    db_sesion.add(
        models.Factura(explotacion_id=explotacion_id, clave_de_reenvio="otra-nueva", total=2.0)
    )
    db_sesion.commit()
