"""Corregir y borrar los papeles y las facturas (ronda 94).

LO QUE SE PRUEBA AQUÍ, Y POR QUÉ

David lo pidió con estas palabras: «recuerda también dejar borrar las cosas que introduzca porque
puede que me equivoque, o modificar también». La ronda 91 lo hizo para los apuntes del cuaderno, la
92 para las tierras y los grupos y la 93 para las fichas (productos, abonos, máquinas, campañas).
**Los papeles y las facturas se quedaron fuera**, y son justo los dos sitios donde el error de tecleo
es más probable, porque la mitad de las veces los datos los ha leído una foto o un PDF: el número de
factura que el lector ha entendido mal, la cantidad que era 5 y se apuntó 20, el papel que se subió a
la carpeta que no era.

Estas pruebas defienden las cinco cosas que hacen que corregir y borrar sean de fiar y no un agujero
por el que se cuela un cuaderno que dice lo que no es:

  1. **Corregir cambia esa cosa, no da de alta otra.** El identificador sigue siendo el mismo.
  2. **Lo que había no se pierde**: queda en la auditoría, campo por campo (`correcciones`), y en una
     factura también **sus líneas**, que es lo que se compró.
  3. **Las reglas son las mismas que al dar de alta**, porque son las mismas funciones: un tipo de
     papel que no existe o un producto de otra finca se rechazan igual en las dos puertas, y una
     corrección rechazada no deja nada a medias.
  4. **Un papel borrado se lleva su fichero del disco**, porque dejarlo ahí es basura que nadie va a
     limpiar nunca.
  5. **El almacén nunca dice una cosa y el cuaderno otra.** El almacén de este programa es una cuenta
     que se calcula (lo comprado por las facturas menos lo echado por los tratamientos), así que
     corregir una línea ya cambia la cuenta sola; y una factura **no se borra si con eso la cuenta se
     quedaría contando lo que se echó sin la compra que lo sostenía**. Ver `borrar_factura`.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select

from app import adjuntos, correcciones, models, servicios, textos

# Una factura completa y correcta, con una línea que cuadra (2 × 85 = 170). Es lo que manda la
# pantalla cuando el agricultor confirma lo que el lector ha entendido, y a partir de aquí cada
# prueba cambia lo suyo.
UNA_LINEA = {
    "descripcion": "GLIFOSATO 36% SL 20 L",
    "cantidad": 2,
    "unidad": "ud",
    "precio_unitario": 85.0,
    "importe": 170.0,
}


def _auditoria(db, entidad: str, entidad_id: int, accion: str):
    """El rastro que ha dejado una corrección o un borrado."""
    return list(
        db.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == entidad,
                models.Auditoria.entidad_id == entidad_id,
                models.Auditoria.accion == accion,
            )
        )
    )


@pytest.fixture
def carpeta_de_adjuntos(tmp_path, monkeypatch):
    """Una carpeta de adjuntos de mentira, para poder comprobar de verdad qué ficheros quedan.

    El `conftest` ya apunta `CUEDIGITAL_ADJUNTOS` a una carpeta temporal de la ejecución, pero esa
    carpeta la comparten **todos** los tests de la suite: para poder decir «aquí había un fichero y
    ya no está» hace falta una carpeta por prueba. Es el mismo montaje que usa `test_documentos.py`.
    """
    carpeta = tmp_path / "adjuntos"
    carpeta.mkdir()
    monkeypatch.setenv("CUEDIGITAL_ADJUNTOS", str(carpeta))
    return carpeta


def _ficheros(carpeta) -> list:
    return [f for f in carpeta.rglob("*") if f.is_file()]


# --------------------------------------------------------------------------
# Los papeles
# --------------------------------------------------------------------------


def _papel(cliente, cabeceras, **cambios) -> dict:
    """Apunta un papel, con lo mínimo que hace falta (`POST /api/documentos`)."""
    cuerpo = {
        "titulo": "Contrato de la finca del río",
        "tipo": "contrato",
        "carpeta": "Contratos",
    }
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/documentos", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _subir_el_papel(cliente, cabeceras, documento_id: int, contenido=b"%PDF-1.4 el contrato"):
    return cliente.post(
        f"/api/documentos/{documento_id}/fichero",
        headers=cabeceras,
        files={"fichero": ("contrato.pdf", contenido, "application/pdf")},
    )


def _los_papeles(cliente, cabeceras) -> list[dict]:
    return cliente.get("/api/documentos", headers=cabeceras).json()["documentos"]


class TestCorregirUnPapel:
    def test_cambia_lo_que_se_le_dice_y_sigue_siendo_el_mismo(self, cliente, cuenta):
        """El título, la carpeta, el tipo y las notas: lo que se corrige de un papel."""
        papel = _papel(cliente, cuenta["cabeceras"])

        respuesta = cliente.put(
            f"/api/documentos/{papel['id']}",
            headers=cuenta["cabeceras"],
            json={
                "titulo": "Contrato de la finca del río (el bueno)",
                "tipo": "factura",
                "carpeta": "Facturas",
                "notas": "Es la factura del abono, no un contrato",
            },
        )

        assert respuesta.status_code == 200, respuesta.text
        corregido = respuesta.json()
        assert corregido["id"] == papel["id"], "es el mismo papel, no otro"
        assert corregido["titulo"] == "Contrato de la finca del río (el bueno)"
        assert corregido["carpeta"] == "Facturas"
        assert corregido["tipo"] == "factura"
        assert corregido["etiqueta_tipo"] == "Una factura"
        assert corregido["notas"] == "Es la factura del abono, no un contrato"

    def test_corregir_no_apunta_otro_papel(self, cliente, cuenta):
        papel = _papel(cliente, cuenta["cabeceras"])

        cliente.put(
            f"/api/documentos/{papel['id']}",
            headers=cuenta["cabeceras"],
            json={"titulo": "Otro nombre", "tipo": "contrato", "carpeta": "Contratos"},
        )

        papeles = _los_papeles(cliente, cuenta["cabeceras"])
        assert [p["id"] for p in papeles] == [papel["id"]]
        assert papeles[0]["titulo"] == "Otro nombre"

    def test_lo_que_habia_queda_en_el_rastro(self, cliente, cuenta, db_sesion):
        papel = _papel(cliente, cuenta["cabeceras"])

        cliente.put(
            f"/api/documentos/{papel['id']}",
            headers=cuenta["cabeceras"],
            json={"titulo": "El nombre bueno", "tipo": "contrato", "carpeta": "Facturas"},
        )

        rastro = _auditoria(db_sesion, "documento", papel["id"], "corregir")
        assert len(rastro) == 1
        assert rastro[0].datos["titulo"] == ["Contrato de la finca del río", "El nombre bueno"]
        assert rastro[0].datos["carpeta"] == ["Contratos", "Facturas"]
        assert rastro[0].fecha is not None

    def test_corregir_no_deja_el_papel_sin_su_fichero(self, cliente, cuenta, carpeta_de_adjuntos):
        """El formulario no manda el fichero, así que copiarlo del formulario lo borraría.

        Es el mismo fallo que se arregló con la máquina de la cosecha y con el dibujo de la tierra:
        ponerle el nombre bueno a un papel **no puede dejarlo sin el contrato**.
        """
        papel = _papel(cliente, cuenta["cabeceras"])
        _subir_el_papel(cliente, cuenta["cabeceras"], papel["id"], contenido=b"el contrato de verdad")

        corregido = cliente.put(
            f"/api/documentos/{papel['id']}",
            headers=cuenta["cabeceras"],
            json={"titulo": "El nombre bueno", "tipo": "contrato", "carpeta": "Contratos"},
        ).json()

        assert corregido["tiene_fichero"] is True
        assert corregido["nombre_del_fichero"] == "contrato.pdf"
        descarga = cliente.get(
            f"/api/documentos/{papel['id']}/fichero", headers=cuenta["cabeceras"]
        )
        assert descarga.status_code == 200
        assert descarga.content == b"el contrato de verdad"
        assert len(_ficheros(carpeta_de_adjuntos)) == 1, "y el fichero sigue en el disco"

    def test_un_tipo_que_no_existe_se_rechaza_con_lo_mismo_que_el_alta(self, cliente, cuenta):
        """Corregir no puede ser la puerta de atrás para meter lo que el alta no deja."""
        papel = _papel(cliente, cuenta["cabeceras"])
        cuerpo = {"titulo": "Lo que sea", "tipo": "lo_que_sea", "carpeta": "Contratos"}

        alta = cliente.post("/api/documentos", headers=cuenta["cabeceras"], json=cuerpo)
        correccion = cliente.put(
            f"/api/documentos/{papel['id']}", headers=cuenta["cabeceras"], json=cuerpo
        )

        assert alta.status_code == 422
        assert correccion.status_code == 422
        assert alta.json()["detail"] == correccion.json()["detail"], "el mismo mensaje que el alta"
        # Y el papel sigue como estaba: una corrección rechazada no lo deja a medias.
        guardado = _los_papeles(cliente, cuenta["cabeceras"])[0]
        assert guardado["titulo"] == "Contrato de la finca del río"
        assert guardado["tipo"] == "contrato"

    def test_la_carpeta_vacia_vuelve_a_otros_como_en_el_alta(self, cliente, cuenta):
        papel = _papel(cliente, cuenta["cabeceras"])

        corregido = cliente.put(
            f"/api/documentos/{papel['id']}",
            headers=cuenta["cabeceras"],
            json={"titulo": papel["titulo"], "tipo": "contrato", "carpeta": "   "},
        ).json()

        assert corregido["carpeta"] == "Otros"

    def test_el_papel_de_otra_finca_no_se_toca(self, cliente, cuenta, crear_cuenta):
        """La finca de otro contesta 404, nunca 403: no se filtra si ese identificador existe."""
        papel = _papel(cliente, cuenta["cabeceras"])
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")

        respuesta = cliente.put(
            f"/api/documentos/{papel['id']}",
            headers=otra["cabeceras"],
            json={"titulo": "Mío", "tipo": "contrato", "carpeta": "Contratos"},
        )

        assert respuesta.status_code == 404
        assert _los_papeles(cliente, cuenta["cabeceras"])[0]["titulo"] == (
            "Contrato de la finca del río"
        )

    def test_sin_entrar_no_se_corrige(self, cliente, cuenta):
        papel = _papel(cliente, cuenta["cabeceras"])

        respuesta = cliente.put(
            f"/api/documentos/{papel['id']}",
            json={"titulo": "Mío", "tipo": "contrato", "carpeta": "Contratos"},
        )

        assert respuesta.status_code == 401


class TestBorrarUnPapel:
    def test_se_borra_y_su_fichero_tambien_se_borra_del_disco(
        self, cliente, cuenta, carpeta_de_adjuntos
    ):
        """Dejar el fichero ahí es basura que nadie va a limpiar nunca.

        Ninguna pantalla lo va a volver a enseñar y el agricultor no tiene acceso a esa carpeta: si
        el papel se borra de verdad, su foto o su PDF se van con él.
        """
        papel = _papel(cliente, cuenta["cabeceras"])
        _subir_el_papel(cliente, cuenta["cabeceras"], papel["id"], contenido=b"el contrato")
        assert len(_ficheros(carpeta_de_adjuntos)) == 1, "el fichero está en el disco"

        respuesta = cliente.delete(
            f"/api/documentos/{papel['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json() == {"borrado": True, "id": papel["id"], "fichero_borrado": True}
        assert _ficheros(carpeta_de_adjuntos) == [], "el fichero se ha ido con el papel"
        assert _los_papeles(cliente, cuenta["cabeceras"]) == []

    def test_un_papel_sin_fichero_se_borra_igual(self, cliente, cuenta):
        papel = _papel(cliente, cuenta["cabeceras"])

        respuesta = cliente.delete(
            f"/api/documentos/{papel['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["fichero_borrado"] is False
        assert _los_papeles(cliente, cuenta["cabeceras"]) == []

    def test_lo_borrado_queda_escrito_en_el_rastro(self, cliente, cuenta, db_sesion):
        """El cuaderno no lo enseña y el programa sí sabe qué había y qué día se borró."""
        papel = _papel(cliente, cuenta["cabeceras"], notas="el del cajón de arriba")

        cliente.delete(f"/api/documentos/{papel['id']}", headers=cuenta["cabeceras"])

        rastro = _auditoria(db_sesion, "documento", papel["id"], "borrar")
        assert len(rastro) == 1
        assert rastro[0].datos["titulo"] == "Contrato de la finca del río"
        assert rastro[0].datos["carpeta"] == "Contratos"
        assert rastro[0].datos["notas"] == "el del cajón de arriba"
        assert rastro[0].fecha is not None

    def test_borrar_dos_veces_da_404_la_segunda(self, cliente, cuenta):
        papel = _papel(cliente, cuenta["cabeceras"])

        primera = cliente.delete(f"/api/documentos/{papel['id']}", headers=cuenta["cabeceras"])
        segunda = cliente.delete(f"/api/documentos/{papel['id']}", headers=cuenta["cabeceras"])

        assert primera.status_code == 200
        assert segunda.status_code == 404

    def test_el_papel_de_otra_finca_no_se_borra(
        self, cliente, cuenta, crear_cuenta, carpeta_de_adjuntos
    ):
        papel = _papel(cliente, cuenta["cabeceras"])
        _subir_el_papel(cliente, cuenta["cabeceras"], papel["id"])
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")

        respuesta = cliente.delete(
            f"/api/documentos/{papel['id']}", headers=otra["cabeceras"]
        )

        assert respuesta.status_code == 404
        assert len(_los_papeles(cliente, cuenta["cabeceras"])) == 1
        assert len(_ficheros(carpeta_de_adjuntos)) == 1, "tampoco se lleva su fichero"

    def test_sin_entrar_no_se_borra(self, cliente, cuenta):
        papel = _papel(cliente, cuenta["cabeceras"])

        assert cliente.delete(f"/api/documentos/{papel['id']}").status_code == 401
        assert len(_los_papeles(cliente, cuenta["cabeceras"])) == 1

    def test_el_nombre_del_fichero_nunca_decide_que_se_borra(
        self, cliente, cuenta, carpeta_de_adjuntos
    ):
        """La ruta la decide el programa, no el nombre que manda el navegador (`adjuntos`).

        Si el borrado usara el nombre del navegador, un papel subido como `../../main.py` podría
        borrar un fichero del programa. Aquí se sube con ese nombre y se comprueba que lo que se
        borra es el fichero del papel —y que el único fichero de la carpeta era ese—.
        """
        papel = _papel(cliente, cuenta["cabeceras"])
        cliente.post(
            f"/api/documentos/{papel['id']}/fichero",
            headers=cuenta["cabeceras"],
            files={"fichero": ("../../main.py", b"%PDF-1.4 el papel", "application/pdf")},
        )
        de_disco = _ficheros(carpeta_de_adjuntos)
        assert len(de_disco) == 1
        assert de_disco[0].name.startswith("documento-"), "el nombre lo pone el programa"

        cliente.delete(f"/api/documentos/{papel['id']}", headers=cuenta["cabeceras"])

        assert _ficheros(carpeta_de_adjuntos) == []


# --------------------------------------------------------------------------
# Las facturas
# --------------------------------------------------------------------------


def _cuerpo_de_factura(**cambios) -> dict:
    """Una factura completa y correcta, tal y como la manda la pantalla.

    Se escribe entera porque la corrección necesita **el cuerpo entero**: `PUT /api/facturas/{id}`
    acepta exactamente el mismo esquema que el alta (`FacturaEntrada`), y esa es la gracia.
    """
    cuerpo = {
        "fecha": "2026-03-15",
        "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
        "proveedor_nif": "F37012345",
        "numero_factura": "2026/00123",
        "base_imponible": 170.0,
        "cuota_iva": 35.70,
        "tipo_iva_pct": 21.0,
        "total": 205.70,
        "leida_por": "pdf",
        "lineas": [dict(UNA_LINEA)],
    }
    cuerpo.update(cambios)
    return cuerpo


def _guardar_factura(cliente, cabeceras, *, con_fichero=True, **cambios) -> dict:
    """Guarda una factura como lo hace la pantalla: los datos y el fichero en la misma petición."""
    respuesta = _guardar_factura_crudo(cliente, cabeceras, con_fichero=con_fichero, **cambios)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _guardar_factura_crudo(cliente, cabeceras, *, con_fichero=True, **cambios):
    cuerpo = _cuerpo_de_factura(**cambios)
    if con_fichero:
        return cliente.post(
            "/api/facturas",
            headers=cabeceras,
            data={"datos": json.dumps(cuerpo)},
            files={"fichero": ("factura.pdf", b"%PDF-1.4 la factura", "application/pdf")},
        )
    return cliente.post(
        "/api/facturas", headers=cabeceras, data={"datos": json.dumps(cuerpo)}
    )


def _corregir_factura(cliente, cabeceras, factura_id: int, **cambios):
    """Corrige una factura como lo haría la pantalla: el cuerpo entero con lo que se cambia."""
    return cliente.put(
        f"/api/facturas/{factura_id}", headers=cabeceras, json=_cuerpo_de_factura(**cambios)
    )


def _las_facturas(cliente, cabeceras) -> list[dict]:
    return cliente.get("/api/facturas", headers=cabeceras).json()


def _un_producto(cliente, cabeceras, **cambios) -> dict:
    """Un producto de la cesta, con dosis y unidad de compra: sin eso no hay cuenta que comprobar."""
    datos = {
        "nombre_comercial": "Glifosato 36 SL",
        "numero_registro": "24.123",
        "dosis_maxima": 4,
        "unidad_dosis": "L/ha",
        "unidad_compra": "L",
        "plazo_seguridad_dias": 21,
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/productos", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _se_echa(cliente, cabeceras, campana, parcela, producto, dosis) -> dict:
    """Apunta un tratamiento que gasta producto: dosis × hectáreas."""
    respuesta = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-01",
            "parcela_id": parcela["id"],
            "superficie_tratada_ha": 2.43,
            "cultivo": "Trigo blando",
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto["id"],
            "dosis": dosis,
            "franja_seguridad_respetada": True,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _la_cesta(cliente, cabeceras, producto_id: int) -> dict:
    """La fila de ese producto en la cesta del almacén, que es la que dice el cuadre."""
    cesta = cliente.get("/api/productos/cesta/situacion", headers=cabeceras).json()
    filas = [f for f in cesta["productos"] if f["producto_id"] == producto_id]
    assert filas, "el producto no sale en la cesta"
    return filas[0]


class TestCorregirUnaFactura:
    def test_cambia_lo_que_se_le_dice_y_sigue_siendo_la_misma(self, cliente, cuenta):
        """Los datos del papel: el proveedor, su NIF, el número, la fecha, la base, el IVA y el total.

        Es lo que hace falta de verdad: lo que se guarda es lo que el agricultor da por bueno de lo
        que ha leído el programa, y ahí se equivoca uno.
        """
        factura = _guardar_factura(cliente, cuenta["cabeceras"])

        respuesta = _corregir_factura(
            cliente,
            cuenta["cabeceras"],
            factura["id"],
            proveedor="Ferretería del pueblo",
            proveedor_nif="12345678Z",
            numero_factura="F-77",
            fecha="2026-04-01",
            base_imponible=100.0,
            cuota_iva=21.0,
            total=121.0,
        )

        assert respuesta.status_code == 200, respuesta.text
        corregida = respuesta.json()
        assert corregida["id"] == factura["id"], "es la misma factura, no otra"
        assert corregida["proveedor"] == "Ferretería del pueblo"
        assert corregida["proveedor_nif"] == "12345678Z"
        assert corregida["numero_factura"] == "F-77"
        assert corregida["fecha"] == "2026-04-01"
        assert corregida["base_imponible"] == 100.0
        assert corregida["total"] == 121.0
        assert len(_las_facturas(cliente, cuenta["cabeceras"])) == 1

    def test_las_lineas_se_pueden_cambiar(self, cliente, cuenta):
        """Lo que se compró: de 20 L a 5 L, y el importe que le toca."""
        factura = _guardar_factura(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 20 L",
                    "cantidad": 20,
                    "unidad": "L",
                    "precio_unitario": 4.25,
                    "importe": 85.0,
                }
            ],
        )

        corregida = _corregir_factura(
            cliente,
            cuenta["cabeceras"],
            factura["id"],
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 20 L",
                    "cantidad": 5,
                    "unidad": "L",
                    "precio_unitario": 4.25,
                    "importe": 21.25,
                },
                {
                    "descripcion": "UNAS BOTAS DE GOMA",
                    "cantidad": 1,
                    "unidad": "ud",
                    "precio_unitario": 30.0,
                    "importe": 30.0,
                },
            ],
        ).json()

        assert [linea["cantidad"] for linea in corregida["lineas"]] == [5.0, 1.0]
        assert [linea["descripcion"] for linea in corregida["lineas"]] == [
            "GLIFOSATO 36% SL 20 L",
            "UNAS BOTAS DE GOMA",
        ], "las líneas viejas no se quedan colgando"
        # Y en la base de datos tampoco quedan: se rehacen enteras, no se parchean.
        listado = _las_facturas(cliente, cuenta["cabeceras"])
        assert len(listado) == 1
        assert len(listado[0]["lineas"]) == 2

    def test_quitar_todas_las_lineas_deja_la_factura_sin_lineas(self, cliente, cuenta):
        """Una factura sin líneas es una factura apuntada a mano: se puede dejar así."""
        factura = _guardar_factura(cliente, cuenta["cabeceras"])

        corregida = _corregir_factura(
            cliente, cuenta["cabeceras"], factura["id"], lineas=[]
        ).json()

        assert corregida["lineas"] == []

    def test_las_cuentas_de_la_linea_se_vuelven_a_comprobar(self, cliente, cuenta):
        """cantidad × precio = importe **se calcula al devolverla** (`_cuadra`), no se guarda.

        Es lo que hace que la cuenta siga siendo verdad después de corregir un número: si se
        guardara el «cuadra» del alta, una línea corregida seguiría diciendo que cuadra cuando ya no.
        """
        factura = _guardar_factura(cliente, cuenta["cabeceras"])
        assert factura["lineas"][0]["cuadra"] is True

        corregida = _corregir_factura(
            cliente,
            cuenta["cabeceras"],
            factura["id"],
            lineas=[{**UNA_LINEA, "cantidad": 5}],  # 5 × 85 = 425, y el importe sigue siendo 170
        ).json()

        assert corregida["lineas"][0]["cantidad"] == 5.0
        assert corregida["lineas"][0]["importe"] == 170.0
        assert corregida["lineas"][0]["cuadra"] is False, "la cuenta se ha vuelto a hacer"

    def test_una_correccion_que_el_alta_no_acepta_se_rechaza_con_lo_mismo(
        self, cliente, cuenta, crear_cuenta
    ):
        """Un producto de otra finca contesta 404 en las dos puertas, con el mismo mensaje.

        Y la factura se queda **como estaba**, con sus números y sus líneas: una corrección
        rechazada no puede dejarla a medias.
        """
        factura = _guardar_factura(cliente, cuenta["cabeceras"])
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")
        ajeno = _un_producto(cliente, otra["cabeceras"], nombre_comercial="El suyo", numero_registro=None)
        lineas = [{**UNA_LINEA, "producto_id": ajeno["id"]}]

        alta = _guardar_factura_crudo(
            cliente, cuenta["cabeceras"], numero_factura="X-1", lineas=lineas
        )
        correccion = _corregir_factura(
            cliente, cuenta["cabeceras"], factura["id"], lineas=lineas
        )

        assert alta.status_code == 404
        assert correccion.status_code == 404
        assert alta.json()["detail"] == correccion.json()["detail"], "el mismo mensaje que el alta"

        guardada = _las_facturas(cliente, cuenta["cabeceras"])[0]
        assert guardada["numero_factura"] == "2026/00123"
        assert guardada["lineas"][0]["producto_id"] is None
        assert guardada["lineas"][0]["cantidad"] == 2.0

    def test_una_correccion_con_un_numero_imposible_no_deja_la_factura_a_medias(
        self, cliente, cuenta
    ):
        factura = _guardar_factura(cliente, cuenta["cabeceras"])

        respuesta = _corregir_factura(
            cliente,
            cuenta["cabeceras"],
            factura["id"],
            proveedor="Otro proveedor",
            lineas=[{**UNA_LINEA, "cantidad": -5}],
        )

        assert respuesta.status_code == 422
        guardada = _las_facturas(cliente, cuenta["cabeceras"])[0]
        assert guardada["proveedor"] == "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L."
        assert guardada["lineas"][0]["cantidad"] == 2.0

    def test_una_correccion_rechazada_no_deja_productos_sueltos_en_la_cesta(
        self, cliente, cuenta, crear_cuenta
    ):
        """Lo que se prepara antes de fallar **tampoco** se queda.

        El alta da de alta el producto de una línea cuando el agricultor dice «no lo tengo apuntado»
        (`crear_producto`). Al corregir eso pasa antes de tocar la factura, así que si después una
        línea no vale, no puede quedarse un producto a medias en la cesta: la corrección entera se
        cae.
        """
        factura = _guardar_factura(cliente, cuenta["cabeceras"])
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")
        ajeno = _un_producto(
            cliente, otra["cabeceras"], nombre_comercial="El suyo", numero_registro=None
        )

        respuesta = _corregir_factura(
            cliente,
            cuenta["cabeceras"],
            factura["id"],
            lineas=[
                {
                    "descripcion": "UN PRODUCTO QUE NO TENÍA APUNTADO",
                    "cantidad": 1,
                    "unidad": "L",
                    "importe": 10.0,
                    "crear_producto": True,
                },
                {**UNA_LINEA, "producto_id": ajeno["id"]},
            ],
        )

        assert respuesta.status_code == 404
        assert (
            cliente.get(
                "/api/productos/cesta/situacion", headers=cuenta["cabeceras"]
            ).json()["productos"]
            == []
        ), "no queda un producto suelto en la cesta"
        assert (
            _las_facturas(cliente, cuenta["cabeceras"])[0]["lineas"][0]["descripcion"]
            == "GLIFOSATO 36% SL 20 L"
        )

    def test_lo_que_habia_queda_en_el_rastro_y_las_lineas_tambien(
        self, cliente, cuenta, db_sesion
    ):
        """Lo que se compró es la factura: perder las líneas sería perder el dato que importa."""
        factura = _guardar_factura(cliente, cuenta["cabeceras"])

        _corregir_factura(
            cliente,
            cuenta["cabeceras"],
            factura["id"],
            numero_factura="2026/00124",
            lineas=[{**UNA_LINEA, "cantidad": 5}],
        )

        rastro = _auditoria(db_sesion, "factura", factura["id"], "corregir")
        assert len(rastro) == 1
        assert rastro[0].datos["numero_factura"] == ["2026/00123", "2026/00124"]
        assert rastro[0].fecha is not None

        lineas = _auditoria(db_sesion, "factura", factura["id"], "corregir_lineas")
        assert len(lineas) == 1
        assert lineas[0].datos["antes"][0]["cantidad"] == 2.0
        assert lineas[0].datos["ahora"][0]["cantidad"] == 5.0

    def test_el_fichero_del_justificante_no_se_toca(
        self, cliente, cuenta, db_sesion, carpeta_de_adjuntos
    ):
        """Corregir un número no puede dejar la factura sin el papel que la demuestra."""
        factura = _guardar_factura(cliente, cuenta["cabeceras"])
        db_sesion.expire_all()
        huella = db_sesion.get(models.Factura, factura["id"]).huella

        corregida = _corregir_factura(
            cliente, cuenta["cabeceras"], factura["id"], numero_factura="2026/00124"
        ).json()

        assert corregida["tiene_fichero"] is True
        assert corregida["nombre_del_fichero"] == "factura.pdf"
        assert len(_ficheros(carpeta_de_adjuntos)) == 1
        assert cliente.get(
            f"/api/facturas/{factura['id']}/fichero", headers=cuenta["cabeceras"]
        ).status_code == 200
        db_sesion.expire_all()
        assert db_sesion.get(models.Factura, factura["id"]).huella == huella

    def test_la_campana_se_vuelve_a_calcular_con_la_fecha_corregida(self, cliente, cuenta):
        """La campaña sale del **año del papel** (`_la_campana`), así que corregir la fecha la cambia.

        Es el mismo caso que la zona de nitratos de una tierra: **lo que el alta calcula sola se
        vuelve a calcular al corregir**. Si la corrección copiara la campaña que ya había, una factura
        de diciembre apuntada en enero se quedaría en la campaña que no es para siempre.
        """
        de_2025 = cliente.post(
            "/api/campanas",
            headers=cuenta["cabeceras"],
            json={"anio": 2025, "fecha_inicio": "2025-01-01", "fecha_fin": "2025-12-31"},
        ).json()
        factura = _guardar_factura(cliente, cuenta["cabeceras"], fecha="2026-03-15")
        assert factura["campana_id"] != de_2025["id"]

        corregida = _corregir_factura(
            cliente, cuenta["cabeceras"], factura["id"], fecha="2025-12-30"
        ).json()

        assert corregida["campana_id"] == de_2025["id"], "es la campaña del año del papel"

    def test_el_almacen_dice_la_verdad_al_corregir_una_linea(self, cliente, cuenta):
        """De 20 L a 5 L: lo que la cesta dice de lo comprado tiene que ser 5.

        Y sale solo, porque el almacén de este programa **es una cuenta que se calcula** y no un
        depósito: lo comprado se suma de las líneas de las facturas cada vez que se mira. Lo que
        había que probar es justo eso: que no se queda un número guardado diciendo lo de antes.
        """
        producto = _un_producto(cliente, cuenta["cabeceras"])
        factura = _guardar_factura(
            cliente,
            cuenta["cabeceras"],
            lineas=[{**UNA_LINEA, "cantidad": 20, "unidad": "L", "producto_id": producto["id"]}],
        )
        assert _la_cesta(cliente, cuenta["cabeceras"], producto["id"])["comprado"] == 20.0

        _corregir_factura(
            cliente,
            cuenta["cabeceras"],
            factura["id"],
            lineas=[{**UNA_LINEA, "cantidad": 5, "unidad": "L", "producto_id": producto["id"]}],
        )

        fila = _la_cesta(cliente, cuenta["cabeceras"], producto["id"])
        assert fila["comprado"] == 5.0
        assert fila["comprado_de_donde"] == "facturas"
        assert fila["compras"][0]["cantidad"] == 5.0

    def test_corregir_no_resucita_una_factura_anulada(self, cliente, cuenta):
        """El estado de anulación no es un dato que el formulario pueda mandar (`correcciones`)."""
        factura = _guardar_factura(cliente, cuenta["cabeceras"])
        cliente.post(
            f"/api/facturas/{factura['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Estaba repetida"},
        )

        corregida = _corregir_factura(
            cliente, cuenta["cabeceras"], factura["id"], numero_factura="2026/00124"
        ).json()

        assert corregida["numero_factura"] == "2026/00124"
        assert corregida["anulada"] is True
        assert corregida["motivo_anulacion"] == "Estaba repetida"

    def test_la_factura_de_otra_finca_no_se_toca(self, cliente, cuenta, crear_cuenta):
        factura = _guardar_factura(cliente, cuenta["cabeceras"])
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")

        respuesta = _corregir_factura(
            cliente, otra["cabeceras"], factura["id"], numero_factura="Mía"
        )

        assert respuesta.status_code == 404
        assert _las_facturas(cliente, cuenta["cabeceras"])[0]["numero_factura"] == "2026/00123"

    def test_sin_entrar_no_se_corrige(self, cliente, cuenta):
        factura = _guardar_factura(cliente, cuenta["cabeceras"])

        respuesta = cliente.put(
            f"/api/facturas/{factura['id']}", json=_cuerpo_de_factura(numero_factura="Mía")
        )

        assert respuesta.status_code == 401


class TestBorrarUnaFactura:
    """La decisión difícil: qué pasa con lo que la factura metió en el almacén.

    El almacén de este programa **no es un depósito, es una cuenta**: lo comprado sale de las líneas
    de las facturas no anuladas y lo echado de los tratamientos (`servicios.situacion_de_la_cesta`).
    Así que borrar una factura **ya** quita del almacén lo que metió, sola —y eso es lo que se
    comprueba abajo—, y lo único que hay que decidir es **cuándo se puede borrar**: cuando con lo que
    queda comprado todavía se sostiene lo que se ha echado. Si no, la cesta diría «has gastado más de
    lo que has comprado» de algo que sí se compró, y eso es el cuaderno diciendo una cosa y el
    almacén otra. El razonamiento entero está en `facturas_api.borrar_factura`.
    """

    def test_se_borra_cuando_no_deja_la_cuenta_mintiendo(
        self, cliente, cuenta, db_sesion, carpeta_de_adjuntos
    ):
        factura = _guardar_factura(cliente, cuenta["cabeceras"])

        respuesta = cliente.delete(
            f"/api/facturas/{factura['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json() == {
            "borrado": True,
            "id": factura["id"],
            "lineas_borradas": 1,
            "fichero_borrado": True,
        }
        assert _las_facturas(cliente, cuenta["cabeceras"]) == []
        assert _ficheros(carpeta_de_adjuntos) == [], "el justificante se va con la factura"
        # Las líneas se van en cascada, no se quedan apuntando a una factura que ya no está.
        db_sesion.expire_all()
        assert db_sesion.scalar(select(func.count()).select_from(models.LineaDeFactura)) == 0

    def test_lo_que_habia_queda_en_el_rastro_y_las_lineas_tambien(
        self, cliente, cuenta, db_sesion
    ):
        """De una factura, lo que hay que poder volver a leer es **qué se compró**."""
        factura = _guardar_factura(cliente, cuenta["cabeceras"])

        cliente.delete(f"/api/facturas/{factura['id']}", headers=cuenta["cabeceras"])

        rastro = _auditoria(db_sesion, "factura", factura["id"], "borrar")
        assert len(rastro) == 1
        assert rastro[0].datos["numero_factura"] == "2026/00123"
        assert rastro[0].datos["total"] == 205.70
        assert rastro[0].fecha is not None

        lineas = _auditoria(db_sesion, "factura", factura["id"], "borrar_lineas")
        assert len(lineas) == 1
        assert lineas[0].datos["lineas"][0]["descripcion"] == "GLIFOSATO 36% SL 20 L"
        assert lineas[0].datos["lineas"][0]["cantidad"] == 2.0

    def test_una_factura_sin_fichero_tambien_se_borra(self, cliente, cuenta):
        factura = _guardar_factura(cliente, cuenta["cabeceras"], con_fichero=False)
        assert factura["tiene_fichero"] is False

        respuesta = cliente.delete(
            f"/api/facturas/{factura['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["fichero_borrado"] is False

    def test_al_borrarla_el_almacen_se_queda_sin_lo_que_metio(self, cliente, cuenta):
        """Lo que metió en el almacén se va con ella, y sale solo: la cesta es una cuenta."""
        producto = _un_producto(cliente, cuenta["cabeceras"])
        factura = _guardar_factura(
            cliente,
            cuenta["cabeceras"],
            lineas=[{**UNA_LINEA, "cantidad": 20, "unidad": "L", "producto_id": producto["id"]}],
        )
        assert _la_cesta(cliente, cuenta["cabeceras"], producto["id"])["comprado"] == 20.0

        cliente.delete(f"/api/facturas/{factura['id']}", headers=cuenta["cabeceras"])

        fila = _la_cesta(cliente, cuenta["cabeceras"], producto["id"])
        assert fila["comprado"] is None
        assert fila["compras"] == []
        assert cliente.get("/api/facturas/resumen", headers=cuenta["cabeceras"]).json() == []

    def test_se_borra_la_factura_repetida_aunque_el_producto_ya_se_haya_echado(
        self, cliente, cuenta, campana, parcela
    ):
        """Es el caso que rompe la regla fácil («no se borra si su producto ya se ha usado»).

        El agricultor sube dos veces la misma factura, que es lo que hace todo el mundo: se compró
        una vez y hay dos apuntes. El producto **sí se ha echado**, pero la otra factura sigue ahí y
        la cuenta cuadra, así que borrar la repetida es lo correcto —y negarse lo dejaría con una
        factura falsa dentro, que es justo lo que pidió arreglar—.
        """
        producto = _un_producto(cliente, cuenta["cabeceras"])
        una = _guardar_factura(
            cliente,
            cuenta["cabeceras"],
            numero_factura="2026/00123",
            lineas=[{**UNA_LINEA, "cantidad": 5, "unidad": "L", "producto_id": producto["id"]}],
        )
        _guardar_factura(
            cliente,
            cuenta["cabeceras"],
            numero_factura="2026/00123",
            lineas=[{**UNA_LINEA, "cantidad": 5, "unidad": "L", "producto_id": producto["id"]}],
        )
        _se_echa(cliente, cuenta["cabeceras"], campana, parcela, producto, dosis=2)
        # Se han echado 4,86 L y hay 10 L comprados: con una de las dos facturas, todavía cuadra.
        assert _la_cesta(cliente, cuenta["cabeceras"], producto["id"])["queda"] == pytest.approx(
            5.14, abs=0.01
        )

        respuesta = cliente.delete(f"/api/facturas/{una['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 200, respuesta.text
        fila = _la_cesta(cliente, cuenta["cabeceras"], producto["id"])
        assert fila["comprado"] == 5.0
        assert fila["queda"] == pytest.approx(0.14, abs=0.01)

    def test_no_se_borra_cuando_dejaria_la_cuenta_diciendo_que_se_echo_mas(
        self, cliente, cuenta, campana, parcela, db_sesion, carpeta_de_adjuntos
    ):
        """Aquí está el no: borrarla dejaría el cuadre contando lo echado sin la compra.

        Se compran 5 L en una factura y 6 L en otra, y se echan 9,72 L: cuadra. Si se borra la de
        5 L, la cesta diría que se han echado 9,72 L de un producto del que solo se compraron 6, y
        eso es mentira: el cuaderno dice que se echó y el almacén que no se compró.
        """
        producto = _un_producto(cliente, cuenta["cabeceras"])
        cinco = _guardar_factura(
            cliente,
            cuenta["cabeceras"],
            numero_factura="2026/00123",
            lineas=[{**UNA_LINEA, "cantidad": 5, "unidad": "L", "producto_id": producto["id"]}],
        )
        _guardar_factura(
            cliente,
            cuenta["cabeceras"],
            numero_factura="2026/00124",
            lineas=[{**UNA_LINEA, "cantidad": 6, "unidad": "L", "producto_id": producto["id"]}],
        )
        _se_echa(cliente, cuenta["cabeceras"], campana, parcela, producto, dosis=4)
        antes = _la_cesta(cliente, cuenta["cabeceras"], producto["id"])
        assert antes["comprado"] == 11.0
        assert antes["gastado"] == pytest.approx(9.72, abs=0.01)
        assert antes["queda"] == pytest.approx(1.28, abs=0.01), "ahora mismo cuadra"

        respuesta = cliente.delete(f"/api/facturas/{cinco['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 409, respuesta.text
        assert respuesta.json()["detail"] == textos.mensaje_con_cuenta("B5_en_uso", 1)
        assert "1 apunte" in respuesta.json()["detail"], "dice cuántos apuntes se quedarían sin compra"
        # Y no se ha borrado nada: ni la factura, ni sus líneas, ni su justificante.
        assert len(_las_facturas(cliente, cuenta["cabeceras"])) == 2
        assert len(_ficheros(carpeta_de_adjuntos)) == 2
        db_sesion.expire_all()
        assert db_sesion.scalar(select(func.count()).select_from(models.LineaDeFactura)) == 2
        assert _la_cesta(cliente, cuenta["cabeceras"], producto["id"])["comprado"] == 11.0

    def test_el_mensaje_cuenta_los_apuntes_que_se_quedarian_sin_compra(
        self, cliente, cuenta, campana, parcela
    ):
        """Con dos tratamientos, el mensaje va en plural y con el número: «2 apuntes».

        Se echan 4,86 L dos veces (9,72 L) de 11 L comprados: cuadra. Sin la factura de 5 L quedarían
        6 L para 9,72 echados, y **los dos** apuntes se quedan sin compra que los explique.
        """
        producto = _un_producto(cliente, cuenta["cabeceras"])
        cinco = _guardar_factura(
            cliente,
            cuenta["cabeceras"],
            numero_factura="2026/00123",
            lineas=[{**UNA_LINEA, "cantidad": 5, "unidad": "L", "producto_id": producto["id"]}],
        )
        _guardar_factura(
            cliente,
            cuenta["cabeceras"],
            numero_factura="2026/00124",
            lineas=[{**UNA_LINEA, "cantidad": 6, "unidad": "L", "producto_id": producto["id"]}],
        )
        for _ in range(2):
            _se_echa(cliente, cuenta["cabeceras"], campana, parcela, producto, dosis=2)
        assert _la_cesta(cliente, cuenta["cabeceras"], producto["id"])["queda"] == pytest.approx(
            1.28, abs=0.01
        ), "con las dos facturas, cuadra"

        respuesta = cliente.delete(f"/api/facturas/{cinco['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == textos.mensaje_con_cuenta("B5_en_uso", 2)
        assert "2 apuntes" in respuesta.json()["detail"]

    def test_una_factura_anulada_se_borra_siempre(self, cliente, cuenta, campana, parcela):
        """Anular es el camino para deshacerse de una factura sin dejar el cuadre mintiendo.

        El producto tiene **1 L apuntado en su ficha**, así que la cesta, sin la factura, diría que se
        han echado 4,86 L de un producto del que solo hay 1: por eso tal cual no se puede borrar. Y
        una vez **anulada** sí: el «comprado» de la cesta ya deja fuera las anuladas, así que la
        cuenta es exactamente la misma con la fila y sin ella —el cuadre ya venía descuadrado y el
        borrado no le añade ninguna mentira nueva—.
        """
        producto = _un_producto(cliente, cuenta["cabeceras"], cantidad_comprada=1)
        factura = _guardar_factura(
            cliente,
            cuenta["cabeceras"],
            lineas=[{**UNA_LINEA, "cantidad": 5, "unidad": "L", "producto_id": producto["id"]}],
        )
        _se_echa(cliente, cuenta["cabeceras"], campana, parcela, producto, dosis=2)
        assert _la_cesta(cliente, cuenta["cabeceras"], producto["id"])["queda"] == pytest.approx(
            0.14, abs=0.01
        ), "con la factura, cuadra"

        tal_cual = cliente.delete(
            f"/api/facturas/{factura['id']}", headers=cuenta["cabeceras"]
        )
        assert tal_cual.status_code == 409, tal_cual.text
        cliente.post(
            f"/api/facturas/{factura['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Estaba repetida"},
        )

        respuesta = cliente.delete(
            f"/api/facturas/{factura['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 200, respuesta.text
        assert _las_facturas(cliente, cuenta["cabeceras"]) == []

    def test_un_abono_que_salio_de_la_factura_no_la_deja_borrar(
        self, cliente, cuenta, campana, parcela, fertilizante, nueva_fertilizacion
    ):
        """`Fertilizacion.factura_id` es una dependencia de verdad, no un adorno.

        Es lo que permite contestar «¿de qué compra salió este abono?» en una inspección: sin la
        factura, el abono se queda sin decir de dónde salió. Se cuenta como todo lo que está en uso y
        contesta 409, igual que una tierra con apuntes encima.
        """
        factura = _guardar_factura(cliente, cuenta["cabeceras"])
        abono = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(factura_id=factura["id"]),
        )
        assert abono.status_code == 201, abono.text
        assert abono.json()["factura_id"] == factura["id"]

        respuesta = cliente.delete(
            f"/api/facturas/{factura['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 409, respuesta.text
        assert respuesta.json()["detail"] == textos.mensaje_con_cuenta("B5_en_uso", 1)
        # Y la factura sigue donde estaba, con su abono apuntando a ella.
        assert len(_las_facturas(cliente, cuenta["cabeceras"])) == 1
        assert cliente.get("/api/fertilizaciones", headers=cuenta["cabeceras"]).json()[0][
            "factura_id"
        ] == factura["id"]

    def test_borrar_dos_veces_da_404_la_segunda(self, cliente, cuenta):
        factura = _guardar_factura(cliente, cuenta["cabeceras"])

        primera = cliente.delete(f"/api/facturas/{factura['id']}", headers=cuenta["cabeceras"])
        segunda = cliente.delete(f"/api/facturas/{factura['id']}", headers=cuenta["cabeceras"])

        assert primera.status_code == 200
        assert segunda.status_code == 404

    def test_la_factura_de_otra_finca_no_se_borra(
        self, cliente, cuenta, crear_cuenta, carpeta_de_adjuntos
    ):
        factura = _guardar_factura(cliente, cuenta["cabeceras"])
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")

        respuesta = cliente.delete(f"/api/facturas/{factura['id']}", headers=otra["cabeceras"])

        assert respuesta.status_code == 404
        assert len(_las_facturas(cliente, cuenta["cabeceras"])) == 1
        assert len(_ficheros(carpeta_de_adjuntos)) == 1, "tampoco se lleva su justificante"

    def test_sin_entrar_no_se_borra(self, cliente, cuenta):
        factura = _guardar_factura(cliente, cuenta["cabeceras"])

        assert cliente.delete(f"/api/facturas/{factura['id']}").status_code == 401
        assert len(_las_facturas(cliente, cuenta["cabeceras"])) == 1


class TestLoQueSeCuentaAntesDeBorrar:
    """Las cuentas que deciden si algo se puede borrar, comprobadas contra la base de datos."""

    def test_lo_que_apunta_a_una_factura_se_cuenta_quitando_sus_propias_lineas(self):
        """Hoy apuntan a una factura **tres** tablas, y la diferencia entre ellas es la decisión.

        Se mira la cuenta de verdad (`correcciones.tablas_que_apuntan_a`), no una lista escrita a
        mano, y esa cuenta es la que usa el borrado:

          · **`lineas_de_factura`**: las líneas **son parte de la factura** y se van con ella en
            cascada. Contarlas como dependencia bloquearía **todos** los borrados, así que se quedan
            fuera; lo que se cuenta en su lugar es la cesta
            (`_apuntes_que_se_quedarian_sin_compra`).
          · **`fertilizaciones`**: un abono puede decir de qué factura salió, y eso sí es una
            dependencia de verdad: sin la factura, el abono se queda sin decir de dónde salió (y la
            base de datos no admitiría la fila). Contesta 409.
          · **`recepciones`** (T09, 03/10/2026): el albarán que llegó con la mercancía dice **de qué
            factura es** (caso A15 del contrato). También es una dependencia de verdad, por lo mismo:
            sin la factura, el albarán se quedaría sin decir de qué compra salió. Contesta 409 — y lo
            que sí se puede hacer siempre es **anular** la factura, que no toca el albarán ni la
            mercancía que entró: la factura no es lo que metía la mercancía en el almacén.
          · **`gastos`** y **`inversiones_de_la_finca`** (T13, E7, 05/10/2026), que entran por el
            mismo motivo que la fertilización: el gasto del gasóleo o la reparación dice **de qué
            factura salió** (`factura_id`), y la inversión también. Son dependencias de verdad —sin la
            factura, la fila se queda sin decir con qué papel se justifica, y la base de datos no la
            admitiría—, así que contestan 409 igual que el abono. Y lo que **no** se hace es crear un
            gasto desde una factura: el gasto la *apunta*, y contar el coste por los dos lados sería
            contar la compra dos veces.

        Esta prueba obliga a decidir el día que aparezca otra tabla que apunte a una factura.
        """
        from app.routers import facturas_api

        assert [
            modelo.__tablename__ for modelo in correcciones.tablas_que_apuntan_a("factura_id")
        ] == ["fertilizaciones", "gastos", "inversiones_de_la_finca", "lineas_de_factura", "recepciones"]
        assert [
            modelo.__tablename__
            for modelo in facturas_api._tablas_que_apuntan_a_una_factura()
        ] == ["fertilizaciones", "gastos", "inversiones_de_la_finca", "recepciones"]

    def test_lo_que_apunta_a_un_papel_es_la_inspeccion_de_una_maquina(self):
        """**Desde el T14 (03/10/2026) hay una tabla que apunta a un papel, y es la que había que decidir.**

        Esta prueba decía antes `assert correcciones.tablas_que_apuntan_a("documento_id") == []` y su
        propio comentario pedía lo que ha pasado: «Si mañana la hay, esta prueba falla y obliga a decidir:
        o cuenta como dependencia, o hay que escribir por qué no».

        **Decisión: cuenta como dependencia** (el borrado ya la mira, `documentos_api.py:320`, y contesta
        409). El motivo es el mismo que con las líneas de una factura, al revés: la inspección de una
        máquina guarda su fecha, su resultado y su próxima fecha por su cuenta —así que el papel no es lo
        que sostiene el dato—, pero un certificado de inspección es **justo el papel que la ley obliga a
        poder enseñar tres años** (`LO_QUE_OBLIGA_LA_LEY.md`, artículo 16.3 del RD 1311/2012). Borrarlo
        dejando una inspección que dice «esto lo demuestra este papel» sería dejar el cuaderno apuntando a
        un papel que ya no está; lo que sí se puede hacer siempre es **anular** el papel, que lo deja con
        su motivo y con su fichero.

        Y ojo con lo que **no** cuenta: el decreto de la máquina no es una dependencia de esta tabla (va
        por `maquina_id`), y una inspección sin papel no apunta a ningún documento.

        **Y desde el T20 (05/10/2026) hay una segunda: `conciliaciones_de_movimiento`.** El agricultor
        puede decir «este dinero del banco va contra este papel», y esa decisión queda apuntada con el
        papel al que se refiere. Es una dependencia de verdad por el mismo motivo que la inspección:
        borrar el papel dejaría la conciliación diciendo contra qué se cuadró sin que exista. Contesta
        409, y lo que sí se puede hacer siempre es **anular el papel** (que lo deja con su motivo y con
        su fichero) o **deshacer la conciliación**, que es una puerta del propio T20 y deja todo como
        estaba.
        """
        assert [
            modelo.__tablename__ for modelo in correcciones.tablas_que_apuntan_a("documento_id")
        ] == ["conciliaciones_de_movimiento", "inspecciones_de_maquina"]

    def test_lo_que_una_correccion_no_toca_es_lo_que_el_formulario_no_manda(self):
        """La regla de la corrección, escrita y con nombre, para el papel **y** para la factura.

        **Solo se cambia lo que la API acepta al dar de alta y devuelve al leer**, porque el
        formulario de corregir se rellena con lo que devuelve la API. En las dos, lo que se queda
        quieto es el fichero: el nombre de disco, la ruta, el tipo y los bytes **no se mandan** al dar
        de alta (el fichero tiene su propia puerta), así que copiarlos del formulario dejaría el papel
        sin su contrato. En la factura se queda quieto además **su huella** (es del fichero) y la
        fecha en que se apuntó y el estado de anulación, que se llaman `creada_en` y `anulada` —en
        femenino, como «la factura»— y por eso se les escapan a la lista de `correcciones`.
        """
        from app.schemas import DocumentoEntrada, DocumentoSalida, FacturaEntrada, FacturaSalida

        assert servicios.columnas_que_una_correccion_no_toca(
            models.DocumentoAnexo, DocumentoEntrada, DocumentoSalida
        ) == ["fichero_nombre", "fichero_ruta", "fichero_tipo", "fichero_bytes"]
        assert sorted(
            servicios.columnas_que_una_correccion_no_toca(
                models.Factura, FacturaEntrada, FacturaSalida
            )
        ) == ["anulada", "campana_id", "creada_en", "fichero_bytes", "fichero_nombre",
              "fichero_ruta", "fichero_tipo", "huella"]

        # Y se quedan fuera por el motivo que dice la regla, no por casualidad.
        assert "fichero_estado" not in DocumentoEntrada.model_fields
        assert "fichero_ruta" not in DocumentoEntrada.model_fields
        assert "huella" not in FacturaEntrada.model_fields
        assert "anulada" not in FacturaEntrada.model_fields
        # La campaña es el caso especial: no se acepta al dar de alta porque **la calcula el alta**
        # del año del papel, y por eso la corrección la vuelve a calcular (ver `corregir_factura`).
        assert "campana_id" not in FacturaEntrada.model_fields
        assert "campana_id" in FacturaSalida.model_fields


class TestLaListaDeRutasNoSeHaRoto:
    """Corregir y borrar **se añaden**: nada de lo que ya había puede desaparecer por el camino."""

    def test_las_rutas_de_siempre_siguen_ahi(self):
        from app.main import app

        publicadas = {
            (metodo.upper(), ruta)
            for ruta, metodos in app.openapi()["paths"].items()
            for metodo in metodos
        }
        de_siempre = {
            ("GET", "/api/documentos"),
            ("POST", "/api/documentos"),
            ("POST", "/api/documentos/{documento_id}/fichero"),
            ("GET", "/api/documentos/{documento_id}/fichero"),
            ("POST", "/api/documentos/{documento_id}/anular"),
            ("GET", "/api/documentos/listado"),
            ("POST", "/api/facturas"),
            ("POST", "/api/facturas/leer"),
            ("GET", "/api/facturas"),
            ("GET", "/api/facturas/estado"),
            ("GET", "/api/facturas/resumen"),
            ("GET", "/api/facturas/{factura_id}"),
            ("POST", "/api/facturas/{factura_id}/fichero"),
            ("GET", "/api/facturas/{factura_id}/fichero"),
            ("POST", "/api/facturas/{factura_id}/anular"),
        }
        assert de_siempre <= publicadas, f"faltan rutas de antes: {sorted(de_siempre - publicadas)}"

        assert {
            ("PUT", "/api/documentos/{documento_id}"),
            ("DELETE", "/api/documentos/{documento_id}"),
            ("PUT", "/api/facturas/{factura_id}"),
            ("DELETE", "/api/facturas/{factura_id}"),
        } <= publicadas, "faltan las rutas nuevas"

    def test_anular_sigue_siendo_lo_que_era(self, cliente, cuenta, carpeta_de_adjuntos):
        """Anular no se ha tocado: el papel se anula y **su fichero se queda**, que es su sentido.

        Es la diferencia con borrar, y hay que poder hacer las dos: anular es «esto no era lo que yo
        pensaba» y el papel sigue siendo la prueba; borrar es «esto no debería estar aquí».
        """
        papel = _papel(cliente, cuenta["cabeceras"])
        _subir_el_papel(cliente, cuenta["cabeceras"], papel["id"], contenido=b"el papel")

        anulado = cliente.post(
            f"/api/documentos/{papel['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "no era lo que yo pensaba"},
        ).json()

        assert anulado["anulado"] is True
        assert _los_papeles(cliente, cuenta["cabeceras"]) == []
        assert len(_ficheros(carpeta_de_adjuntos)) == 1, "el fichero de un papel anulado se queda"
