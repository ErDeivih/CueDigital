"""**El piloto de la edicion concurrente: la factura** (CRM-08, 17/10/2026).

El ticket lo pide asi: *«Piloto en formulario de **trabajo** y **factura**»*. Esto es la factura:
`PUT /api/facturas/{id}`, que es la puerta que la corrige.

***Y aqui hay algo que no tiene el tratamiento***: la factura se manda **en `multipart`**, con el campo
`datos`, porque puede llevar un fichero adjunto. Asi que la version viaja **dentro del JSON**, como todo lo
demas.
"""

from __future__ import annotations

import json

UNA_FACTURA = {
    "fecha": "2026-03-15",
    "proveedor": "COOPERATIVA AGRICOLA DE PENARANDA S.C.L.",
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
    cuerpo = json.loads(json.dumps(UNA_FACTURA))
    cuerpo.update(cambios)
    return cuerpo


def _la_factura(cliente, cuenta, **cambios) -> dict:
    """Se da de alta **como la manda la pantalla**: `multipart` con el campo `datos`."""
    respuesta = cliente.post(
        "/api/facturas",
        headers=cuenta["cabeceras"],
        data={"datos": json.dumps(_cuerpo(**cambios))},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _corregir(cliente, cuenta, factura_id, **cambios):
    """***Y se corrige en JSON, no en `multipart`.***

    El **alta** lleva fichero adjunto y por eso es `multipart` -y por eso `_la_factura` usa `data`-, pero la
    **correccion** no: su puerta declara `datos: FacturaEntrada`, o sea un cuerpo JSON.

    *Medido: con `data=` contestaba `model_attributes_type` con `loc: ["body"]`, que es FastAPI diciendo «eso
    no es un cuerpo».*
    """
    return cliente.put(
        f"/api/facturas/{factura_id}",
        headers=cuenta["cabeceras"],
        json=_cuerpo(**cambios),
    )


# ---------------------------------------------------------------------------
# 1 · La version, que viene en la respuesta
# ---------------------------------------------------------------------------


def test_la_factura_recien_creada_trae_su_version(cliente, cuenta):
    """***Un apunte recien creado ya tiene historia***: el alta deja su fila en la auditoria.

    Asi que su version **no es cero**, y el formulario la tiene para mandarla de vuelta.
    """
    suya = _la_factura(cliente, cuenta)

    assert suya.get("version") is not None, "***la respuesta tiene que traer la version***"
    assert suya["version"] > 0, "***y la de una factura dada de alta no es cero***"


# ---------------------------------------------------------------------------
# 2 · Sin version: como siempre
# ---------------------------------------------------------------------------


def test_sin_version_esperada_se_corrige_como_siempre(cliente, cuenta):
    """***La compatibilidad***: un formulario que no manda version sigue funcionando igual."""
    suya = _la_factura(cliente, cuenta)

    respuesta = _corregir(cliente, cuenta, suya["id"], proveedor="PROVEEDOR SIN VERSION S.L.")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["proveedor"] == "PROVEEDOR SIN VERSION S.L."


# ---------------------------------------------------------------------------
# 3 · Con la buena, y con la mala
# ---------------------------------------------------------------------------


def test_con_la_version_BUENA_se_corrige(cliente, cuenta):
    suya = _la_factura(cliente, cuenta)

    respuesta = _corregir(
        cliente, cuenta, suya["id"], proveedor="PROVEEDOR CON LA BUENA S.L.", version_esperada=suya["version"]
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["proveedor"] == "PROVEEDOR CON LA BUENA S.L."


def test_con_la_version_MALA_contesta_409_Y_NO_se_escribe_nada(cliente, cuenta):
    """***«No ultimo escritor silencioso»***, y en una factura menos que en nada.

    Se corrige una vez -para que tenga historia-, y luego se intenta corregir **con la version del alta**,
    que es lo que le pasaria a quien tuviera el formulario abierto de antes.
    """
    suya = _la_factura(cliente, cuenta)
    la_del_alta = suya["version"]

    primera = _corregir(cliente, cuenta, suya["id"], proveedor="PROVEEDOR DEL QUE LLEGO ANTES S.L.")
    assert primera.status_code == 200, primera.text
    assert primera.json()["proveedor"] == "PROVEEDOR DEL QUE LLEGO ANTES S.L."

    choque = _corregir(
        cliente,
        cuenta,
        suya["id"],
        proveedor="PROVEEDOR DEL QUE LLEGO TARDE S.L.",
        version_esperada=la_del_alta,
    )

    assert choque.status_code == 409, choque.text
    assert "ha cambiado" in choque.json()["detail"], choque.json()["detail"]

    # ***Y lo que importa: lo del que llego tarde NO se ha escrito.***
    despues = cliente.get(f"/api/facturas/{suya['id']}", headers=cuenta["cabeceras"])
    assert despues.status_code == 200, despues.text
    assert despues.json()["proveedor"] == "PROVEEDOR DEL QUE LLEGO ANTES S.L.", (
        f"***se ha escrito lo del que llego tarde***: {despues.json()['proveedor']}"
    )
