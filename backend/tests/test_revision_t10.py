"""Revisión independiente del T10: semillas, foto de etiqueta y asignación a siembra.

## Qué es este fichero

No es la suite del ticket: es **el intento de romperla**. Cada prueba de aquí dice qué contrato del
encargo está atacando y qué se espera del programa; las que están marcadas como `DEFECTO` fallan
mientras el defecto exista, y llevan escrito **qué le pasaría al agricultor**.

Está escrito contra la foto del árbol que se apunta abajo. Si algo que aquí falla ya no falla cuando
se lea esto, hay que mirar la hora: el árbol se movía mientras se revisaba.

## Foto del árbol (medida el 02/10/2026 a las 19:13–19:19, hora local)

| Fichero | Tamaño | Hora | sha256 (16 primeros) |
|---|---|---|---|
| `backend/app/routers/semillas_api.py` | 46801 | 18:34:25 | `077F987F3AD50CE1` |
| `backend/app/semillas.py` | 27562 | 18:32:38 | `2DC5C02C9AB9EAD1` |
| `backend/app/models.py` | 115531 | 18:21:36 | `20A89059E1226179` |
| `backend/app/schemas.py` | 101112 | 18:37:35 | `58FC56DDCB972403` |
| `backend/app/textos.py` | 312131 | 18:56:00 | `3137CE11981B2D1B` |
| `backend/app/servicios.py` | 106666 | 18:25:09 | `93C9BD8D789F9111` |
| `backend/app/routers/almacen_api.py` | 66192 | 17:08:01 | `405A4498A5A66DA4` |
| `backend/tests/test_semillas.py` | 49684 | 18:33:52 | `AA5EAC00E11BF1F9` |
| `backend/web/react/pantallas/semillas.js` | 14752 | 18:55:09 | `8EA6297681414D1F` |
| `backend/web/react/pantallas/siembras.js` | 13025 | 18:55:34 | `17307898C35421F5` |
| `backend/web/app.js` | 669656 | **19:17:22** | `E17FAF2F4BB9AF7B` |

> `app.js` se estaba escribiendo a las 19:17, después de empezar esta revisión: lo que aquí se dice de
> la pantalla es de esa foto, no de lo que haya ahora.

## Cómo se ejecuta

```bash
cd backend
../.venv/Scripts/python.exe -m pytest tests/test_revision_t10.py -q --junit-xml=$env:TEMP\rev10.xml
```

## Datos sintéticos

Los datos son de test: en la finca real no hay ni una semilla ni un albarán de semilla, así que el
almacén, la etiqueta y la siembra se montan con las puertas de verdad de la API (albarán → semilla →
siembra), no escribiendo filas a mano.
"""

from __future__ import annotations

import io
import pathlib
import re

import pytest
from sqlalchemy import select

from app import models, semillas, textos

# --------------------------------------------------------------------------
# Ayudantes (los del ticket, copiados tal cual para no depender de su fichero)
# --------------------------------------------------------------------------

FECHA_SIEMBRA = "2026-03-01"


def _etiqueta_en_pdf(lineas: list[str]) -> bytes:
    """El papel, como un PDF con las letras dentro (que es como lo manda una casa de semillas)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    lienzo = canvas.Canvas(buffer, pagesize=A4)
    alto = 800
    for linea in lineas:
        lienzo.drawString(50, alto, linea)
        alto -= 16
    lienzo.save()
    return buffer.getvalue()


def _subir_etiqueta(cliente, cabeceras, contenido: bytes | None = None):
    if contenido is None:
        contenido = _etiqueta_en_pdf(["ESPECIE: VEZA COMUN", "DOSIS RECOMENDADA: 120 kg/ha"])
    return cliente.post(
        "/api/semillas/etiqueta",
        headers=cabeceras,
        files={"fichero": ("etiqueta.pdf", contenido, "application/pdf")},
    )


def _parcela(cliente, cabeceras, alias: str = "El Prado", **cambios) -> dict:
    datos = {
        "alias": alias,
        "ref_sigpac": "37-455-12-3",
        "superficie_ha": 2.43,
        "superficie_oficial": True,
        "sistema": "secano",
        "uso_sigpac": "Labor secano",
        "municipio": "Peñaranda de Bracamonte",
        "provincia": "Salamanca",
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/parcelas", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _almacen(
    cliente,
    cabeceras,
    *,
    cantidad: float | None = 500.0,
    unidad: str = "kg",
    nombre: str = "Veza común Villalobos",
    numero_lote: str = "4471-A",
    numero_albaran: str = "ALB-2026-77",
    fecha_caducidad: str = "2028-01-12",
) -> dict:
    """Un albarán con semilla dentro, por la puerta de verdad del almacén."""
    linea = {
        "nombre": nombre,
        "categoria": "semilla",
        "numero_lote": numero_lote,
        "fecha_caducidad": fecha_caducidad,
        "presentacion": "saco",
        "contenido_por_envase": 25.0,
    }
    if cantidad is not None:
        linea["cantidad"] = cantidad
        linea["unidad_de_la_cantidad"] = unidad
    respuesta = cliente.post(
        "/api/almacen/recepciones",
        headers=cabeceras,
        json={
            "fecha": "2026-01-20",
            "proveedor": "Cooperativa Agrícola de Peñaranda",
            "numero_albaran": numero_albaran,
            "lineas": [linea],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    existencias = cliente.get("/api/almacen/existencias", headers=cabeceras).json()
    articulo = next(fila for fila in existencias["articulos"] if fila["nombre"] == nombre)
    lote = next(fila for fila in articulo["lotes"] if fila["numero_lote"] == numero_lote)
    return {
        "articulo_id": articulo["articulo_id"],
        "lote_id": lote["lote_id"],
        "cantidad": cantidad,
        "unidad": unidad,
    }


def _dar_de_alta_la_semilla(cliente, cabeceras, almacen, **cambios) -> dict:
    datos = {
        "articulo_id": almacen["articulo_id"],
        "unidad": almacen["unidad"],
        "especie": "Veza común",
        "variedad": "Villalobos",
        "casa_comercial": "Semillas del Duero",
        "proveedor": "Cooperativa Agrícola de Peñaranda",
        "numero_lote_proveedor": "4471-A",
        "dosis_recomendada_por_ha": 120.0,
        "unidad_dosis": "kg/ha",
        "fecha_envasado": "2026-01-12",
        "fecha_caducidad": "2028-01-12",
        "poder_germinativo_pct": 92.0,
        "pureza_pct": 99.2,
        "tratada": False,
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/semillas", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _siembra(semilla_id: int, parcela_id: int, **cambios) -> dict:
    datos = {
        "semilla_id": semilla_id,
        "parcela_id": parcela_id,
        "lote_id": None,
        "fecha": FECHA_SIEMBRA,
        "superficie_ha": 1.0,
        "dosis_por_ha": 200.0,
        "unidad_dosis": "kg/ha",
        "cantidad_total": 200.0,
        "unidad_cantidad": "kg",
        "clave_de_reenvio": "siembra-de-la-revision-1",
    }
    datos.update(cambios)
    return datos


def _sembrar(cliente, cabeceras, datos: dict):
    return cliente.post("/api/siembras", headers=cabeceras, json=datos)


def _queda(cliente, cabeceras, articulo_id: int) -> dict:
    existencias = cliente.get("/api/almacen/existencias", headers=cabeceras).json()
    return next(fila for fila in existencias["articulos"] if fila["articulo_id"] == articulo_id)


def _salidas_del_apunte(db_sesion, siembra_id: int) -> list[models.MovimientoDeExistencias]:
    """Las salidas del libro que apuntan a esta siembra, vivas y anuladas."""
    db_sesion.rollback()  # que se lea lo que ha quedado escrito, no lo que esta sesión tenía cargado
    return list(
        db_sesion.scalars(
            select(models.MovimientoDeExistencias)
            .where(
                models.MovimientoDeExistencias.origen_tipo == "siembra",
                models.MovimientoDeExistencias.origen_id == siembra_id,
            )
            .order_by(models.MovimientoDeExistencias.id)
        )
    )


def _cuerpo_de_la_funcion(codigo_js: str, nombre: str) -> str:
    """El cuerpo de una función de `app.js`, para poder mirar qué hace con lo que le llega.

    Las funciones de arriba del fichero empiezan en la columna 0 y acaban con una llave en la columna
    0, así que se corta ahí. Si algún día dejan de estar así, esto revienta y hay que rehacerlo: es
    preferible a dar por bueno un trozo cortado por otro sitio.
    """
    inicio = codigo_js.index(f"function {nombre}(")
    fin = codigo_js.index("\n}\n", inicio)
    return codigo_js[inicio:fin]


@pytest.fixture
def montado(cliente, cuenta, crear_parcela):
    """Una finca con un albarán de semilla, su etiqueta y una tierra: lo mínimo para sembrar."""
    almacen = _almacen(cliente, cuenta["cabeceras"])
    semilla = _dar_de_alta_la_semilla(cliente, cuenta["cabeceras"], almacen)
    tierra = crear_parcela()
    return {"almacen": almacen, "semilla": semilla, "tierra": tierra}


# ==========================================================================
# CONTRATO 1 · La cantidad total NO es la dosis por hectárea
# ==========================================================================


class TestContrato1_LaCantidadNoEsLaDosis:
    def test_si_solo_dan_la_dosis_y_no_hay_superficie_no_se_inventa_un_total(
        self, cliente, cuenta, montado
    ):
        """Sin hectáreas no se puede multiplicar: el total tiene que quedar **vacío** y pedirse."""
        respuesta = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                superficie_ha=None,
                cantidad_total=None,
                unidad_cantidad=None,
            ),
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["dosis_por_ha"] == 200.0, "la dosis que le he dado no se toca"
        assert datos["cantidad_total"] is None, (
            "sin superficie no se puede calcular el total: tiene que quedar vacío y pedirse, "
            f"no inventarse. Ha salido: {datos['cantidad_total']!r}"
        )
        assert datos["cantidad_total_calculada"] is False
        assert datos["descuenta"] is False
        assert _queda(cliente, cuenta["cabeceras"], montado["almacen"]["articulo_id"])[
            "saldo"
        ] == 500.0, "no se puede sacar del almacén una cantidad que no se sabe"

    def test_el_total_calculado_se_dice_con_la_cuenta_entera(self, cliente, cuenta, montado):
        """`dosis × hectáreas = total`: se calcula **y se dice**, con los tres números."""
        respuesta = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                superficie_ha=2.5,
                dosis_por_ha=120.0,
                unidad_dosis="kg/ha",
                cantidad_total=None,
                unidad_cantidad=None,
            ),
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["cantidad_total"] == 300.0
        assert datos["cantidad_total_calculada"] is True
        assert datos["unidad_cantidad"] == "kg", "la unidad sale del numerador de la dosis"
        avisos = " ".join(datos["avisos"])
        for cifra in ("120", "2,5", "300"):
            assert cifra in avisos, f"el aviso tiene que enseñar la cuenta entera: {avisos!r}"

    def test_los_dos_numeros_van_a_columnas_distintas_y_no_se_cruzan(
        self, cliente, cuenta, montado
    ):
        respuesta = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                superficie_ha=4.0,
                dosis_por_ha=0.5,
                unidad_dosis="kg/ha",
                cantidad_total=2.0,
                unidad_cantidad="kg",
            ),
        )
        assert respuesta.status_code == 201, respuesta.text
        guardada = cliente.get(
            f"/api/siembras/{respuesta.json()['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert guardada["dosis_por_ha"] == 0.5, "2 kg en 4 ha son 0,5 kg por hectárea"
        assert guardada["cantidad_total"] == 2.0, "el total no se convierte en la dosis"
        assert guardada["unidad_dosis"] == "kg/ha"
        assert guardada["unidad_cantidad"] == "kg"

    def test_los_litros_no_se_convierten_en_kilos_ni_de_broma(self, cliente, cuenta, montado):
        """Una cifra en litros y otra en kilos por hectárea: se dice que no se comparan."""
        respuesta = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                superficie_ha=4.0,
                dosis_por_ha=5.0,
                unidad_dosis="kg/ha",
                cantidad_total=2.0,
                unidad_cantidad="L",
            ),
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        avisos = " ".join(datos["avisos"])
        assert "no se pueden comparar" in avisos, (
            "litros con kilos no se comparan sin la densidad, y eso tiene que decirse: "
            f"{avisos!r}"
        )
        assert datos["cantidad_total"] == 2.0, "y no se convierte nada"
        assert datos["dosis_por_ha"] == 5.0

    def test_redondear_no_hace_que_las_dos_cifras_dejen_de_cuadrar(
        self, cliente, cuenta, montado
    ):
        """Guardar lo que el propio programa calculó no puede sacar un «no cuadran» falso."""
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                superficie_ha=3.0,
                dosis_por_ha=1 / 3,
                unidad_dosis="kg/ha",
                cantidad_total=None,
                unidad_cantidad=None,
            ),
        )
        assert primera.status_code == 201, primera.text
        calculada = primera.json()

        # Se devuelven los dos números tal y como los guardó el programa (es lo que hace la pantalla
        # al corregir cualquier otra cosa).
        respuesta = cliente.put(
            f"/api/siembras/{calculada['id']}",
            headers=cuenta["cabeceras"],
            json=_siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                superficie_ha=calculada["superficie_ha"],
                dosis_por_ha=calculada["dosis_por_ha"],
                unidad_dosis=calculada["unidad_dosis"],
                cantidad_total=calculada["cantidad_total"],
                unidad_cantidad=calculada["unidad_cantidad"],
                notas="le he puesto una nota",
            ),
        )
        assert respuesta.status_code == 200, respuesta.text
        avisos = " ".join(respuesta.json()["avisos"])
        assert "no cuadran" not in avisos, (
            f"el redondeo del propio programa no puede producir un aviso de descuadre: {avisos!r}"
        )

    def test_una_cantidad_negativa_no_se_guarda(self, cliente, cuenta, montado):
        respuesta = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                cantidad_total=-5.0,
            ),
        )
        assert respuesta.status_code == 422, "una cantidad negativa no se apunta"


# ==========================================================================
# CONTRATO 2 · La semilla sale del almacén, y sale UNA sola vez
# ==========================================================================


class TestContrato2_LaSemillaSaleUnaVez:
    def test_la_salida_va_por_la_puerta_del_almacen_y_se_ve_en_el_libro(
        self, cliente, cuenta, montado, db_sesion
    ):
        respuesta = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
            ),
        )
        assert respuesta.status_code == 201, respuesta.text
        siembra = respuesta.json()
        assert siembra["descuenta"] is True
        assert _queda(cliente, cuenta["cabeceras"], montado["almacen"]["articulo_id"])[
            "saldo"
        ] == 300.0

        salidas = _salidas_del_apunte(db_sesion, siembra["id"])
        assert len(salidas) == 1, "una siembra y un envase: una sola salida"
        assert salidas[0].origen_tipo == "siembra"
        assert salidas[0].tipo == "salida"
        assert salidas[0].cantidad == 200.0
        assert salidas[0].unidad == "kg"

    def test_a_mano_no_se_puede_decir_que_un_movimiento_viene_de_una_siembra(
        self, cliente, cuenta, montado
    ):
        """`siembra` no está en `ORIGENES_DE_UN_MOVIMIENTO`: es lo que impide una segunda vía."""
        respuesta = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "articulo_id": montado["almacen"]["articulo_id"],
                "lote_id": montado["almacen"]["lote_id"],
                "tipo": "salida",
                "cantidad": 10.0,
                "unidad": "kg",
                "origen_tipo": "siembra",
                "origen_id": 1,
                "motivo": "es que viene de una siembra",
            },
        )
        assert respuesta.status_code == 400, (
            "apuntar a mano una salida diciendo que viene de una siembra es la segunda forma de "
            f"restar que el ticket prohíbe: {respuesta.status_code} {respuesta.text}"
        )

    def test_reenviar_la_misma_siembra_no_descuenta_dos_veces(self, cliente, cuenta, montado):
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                clave_de_reenvio="cola-de-la-revision",
            ),
        )
        assert primera.status_code == 201, primera.text
        segunda = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                clave_de_reenvio="cola-de-la-revision",
            ),
        )
        assert segunda.json()["id"] == primera.json()["id"]
        assert _queda(cliente, cuenta["cabeceras"], montado["almacen"]["articulo_id"])[
            "saldo"
        ] == 300.0

    def test_corregir_sin_cambiar_lo_que_salio_no_apunta_una_segunda_salida(
        self, cliente, cuenta, montado, db_sesion
    ):
        """Una corrección de las notas no puede dejar dos descuentos vivos."""
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
            ),
        ).json()
        respuesta = cliente.put(
            f"/api/siembras/{primera['id']}",
            headers=cuenta["cabeceras"],
            json=_siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                notas="corregido sin tocar la cantidad",
            ),
        )
        assert respuesta.status_code == 200, respuesta.text
        salidas = _salidas_del_apunte(db_sesion, primera["id"])
        vivas = [movimiento for movimiento in salidas if not movimiento.anulado]
        assert len(vivas) == 1, f"dos salidas vivas para la misma siembra: {len(vivas)}"
        assert _queda(cliente, cuenta["cabeceras"], montado["almacen"]["articulo_id"])[
            "saldo"
        ] == 300.0, "500 − 200: la corrección no cambia la cantidad"

    def test_corregir_la_cantidad_deja_una_sola_salida_viva(
        self, cliente, cuenta, montado, db_sesion
    ):
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
            ),
        ).json()
        respuesta = cliente.put(
            f"/api/siembras/{primera['id']}",
            headers=cuenta["cabeceras"],
            json=_siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                cantidad_total=60.0,
            ),
        )
        assert respuesta.status_code == 200, respuesta.text
        salidas = _salidas_del_apunte(db_sesion, primera["id"])
        assert sum(1 for movimiento in salidas if not movimiento.anulado) == 1
        assert sum(1 for movimiento in salidas if movimiento.anulado) == 1, (
            "la salida vieja se queda en el libro, tachada"
        )
        assert _queda(cliente, cuenta["cabeceras"], montado["almacen"]["articulo_id"])[
            "saldo"
        ] == 440.0, "500 − 60"

    def test_los_litros_y_los_kilos_no_se_suman_donde_queda_la_semilla(
        self, cliente, cuenta
    ):
        """Dos envases del mismo artículo en unidades distintas: se dice, no se suma."""
        _almacen(cliente, cuenta["cabeceras"], cantidad=500.0, unidad="kg")
        _almacen(
            cliente,
            cuenta["cabeceras"],
            cantidad=3.0,
            unidad="L",
            numero_lote="4471-L",
            numero_albaran="ALB-2026-L",
        )
        existencias = cliente.get("/api/almacen/existencias", headers=cuenta["cabeceras"]).json()
        articulo = existencias["articulos"][0]
        semilla = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={"articulo_id": articulo["articulo_id"]},
        ).json()
        assert semilla["queda"]["saldo"] is None, (
            "kilos y litros no se suman: el saldo no puede ser un número, tiene que decirse"
        )
        assert semilla["queda"]["motivo"], "y con el motivo escrito"

    def test_DEFECTO_anular_y_volver_a_apuntar_la_misma_peticion_vuelve_a_descontar(
        self, cliente, cuenta, montado, db_sesion
    ):
        """DEFECTO 1 · Anular una siembra y volver a mandar la MISMA petición de la cola.

        El documento dice (§3.5 y el índice de la tabla `siembras`): «una siembra anulada deja volver a
        apuntarla (anular existe justo para eso)». Al volver a apuntarla, la semilla **tiene que volver
        a salir del almacén** (si no, el libro dice que sigue todo en la nave mientras el agricultor la
        ha sembrado).

        Lo que pasa de verdad: la siembra se crea (201), pero su salida **no**, porque el programa
        encuentra la salida VIEJA —que sigue viva, solo que su siembra está anulada— por su clave de
        reenvío `«…:salida»` y la da por buena. El almacén no se mueve y la respuesta dice que no
        descuenta **«porque no se sabe de qué envase sale»**, con el envase elegido y su número de lote
        escrito en la misma respuesta.
        """
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                clave_de_reenvio="la-cola-1",
            ),
        )
        assert primera.status_code == 201, primera.text
        assert primera.json()["descuenta"] is True
        assert _queda(cliente, cuenta["cabeceras"], montado["almacen"]["articulo_id"])[
            "saldo"
        ] == 300.0

        anulada = cliente.post(
            f"/api/siembras/{primera.json()['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me equivoqué de tierra"},
        )
        assert anulada.status_code == 200, anulada.text
        assert _queda(cliente, cuenta["cabeceras"], montado["almacen"]["articulo_id"])[
            "saldo"
        ] == 500.0, "al anular, la semilla vuelve al almacén"

        # La cola del móvil reenvía la misma petición, con la misma clave (es lo que hace la cola).
        otra = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                clave_de_reenvio="la-cola-1",
            ),
        )
        assert otra.status_code == 201, otra.text
        datos = otra.json()
        assert datos["id"] != primera.json()["id"], "es una siembra nueva, no la anulada"
        assert datos["lote_id"] == montado["almacen"]["lote_id"]
        assert datos["descuenta"] is True, (
            "la siembra nueva no ha sacado la semilla del almacén; dice que no descuenta por "
            f"«{datos['no_descuenta_porque']}» con el envase elegido"
        )
        vivas = [
            movimiento
            for movimiento in _salidas_del_apunte(db_sesion, datos["id"])
            if not movimiento.anulado
        ]
        assert len(vivas) == 1, f"la siembra nueva no tiene su propia salida: {len(vivas)}"
        assert _queda(cliente, cuenta["cabeceras"], montado["almacen"]["articulo_id"])[
            "saldo"
        ] == 300.0, "y el almacén tiene que haber bajado otra vez"

    def test_anular_y_volver_a_apuntar_con_otra_clave_si_vuelve_a_descontar(
        self, cliente, cuenta, montado
    ):
        """Control del defecto 1: con otra clave —es decir, sin chocar con la salida vieja— va bien.

        Sirve para localizar la causa: no es que «no se pueda volver a apuntar una siembra anulada»,
        es que la salida vieja (viva, pero con su siembra anulada) se encuentra **por su clave**.
        """
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                clave_de_reenvio="la-cola-2",
            ),
        ).json()
        cliente.post(
            f"/api/siembras/{primera['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me equivoqué de tierra"},
        )
        otra = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                clave_de_reenvio="otra-clave-distinta",
            ),
        )
        assert otra.status_code == 201, otra.text
        assert otra.json()["descuenta"] is True
        assert _queda(cliente, cuenta["cabeceras"], montado["almacen"]["articulo_id"])[
            "saldo"
        ] == 300.0

    def test_una_segunda_salida_para_el_mismo_envase_no_descuenta_dos_veces(
        self, cliente, cuenta, montado, db_sesion
    ):
        """El control del defecto 2: **con el mismo envase** la puerta sí sabe que ya estaba."""
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
            ),
        ).json()
        respuesta = cliente.post(
            "/api/almacen/salidas",
            headers=cuenta["cabeceras"],
            json={
                "apunte_tipo": "siembra",
                "apunte_id": primera["id"],
                "lote_id": montado["almacen"]["lote_id"],
                "cantidad": 200.0,
                "unidad": "kg",
            },
        )
        salidas = [
            movimiento
            for movimiento in _salidas_del_apunte(db_sesion, primera["id"])
            if not movimiento.anulado
        ]
        assert len(salidas) == 1, f"la misma siembra y el mismo saco: una salida ({respuesta.status_code})"
        assert _queda(cliente, cuenta["cabeceras"], montado["almacen"]["articulo_id"])[
            "saldo"
        ] == 300.0

    def test_DEFECTO_una_segunda_salida_a_mano_para_la_misma_siembra_descuenta_dos_veces(
        self, cliente, cuenta, montado, db_sesion
    ):
        """DEFECTO 2 · La puerta de las salidas deja sacar **dos veces** lo mismo para una siembra.

        El encargo pide que la semilla «salga UNA sola vez», y el propio fichero del ticket dice que
        «nunca quedan dos vivas». Pero `POST /api/almacen/salidas` acepta `apunte_tipo="siembra"` para
        cualquiera que lo llame, y su comprobación de «ya estaba» es **por apunte y ENVASE**: con un
        segundo envase del mismo artículo, la misma siembra descuenta dos veces y el libro se queda con
        dos salidas vivas que nadie puede cuadrar.

        No se alcanza desde las pantallas de hoy (no hay ningún sitio que ofrezca «siembra» como
        apunte), sí desde la API del propio programa.
        """
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
            ),
        ).json()
        assert primera["descuenta"] is True

        # Un segundo saco de la misma semilla (otro envase del mismo artículo).
        segundo = _almacen(
            cliente,
            cuenta["cabeceras"],
            numero_lote="4471-B",
            numero_albaran="ALB-2026-78",
        )
        assert segundo["articulo_id"] == montado["almacen"]["articulo_id"]

        respuesta = cliente.post(
            "/api/almacen/salidas",
            headers=cuenta["cabeceras"],
            json={
                "apunte_tipo": "siembra",
                "apunte_id": primera["id"],
                "lote_id": segundo["lote_id"],
                "cantidad": 200.0,
                "unidad": "kg",
            },
        )
        salidas = [
            movimiento
            for movimiento in _salidas_del_apunte(db_sesion, primera["id"])
            if not movimiento.anulado
        ]
        assert len(salidas) == 1, (
            f"la misma siembra ha descontado {len(salidas)} veces del almacén "
            f"(respuesta {respuesta.status_code}); el total de la siembra es 200 kg, una sola vez"
        )


# ==========================================================================
# CONTRATO 3 · La foto de la etiqueta propone, no afirma
# ==========================================================================


class TestContrato3_LaFotoPropone:
    def test_leer_una_etiqueta_no_escribe_ni_un_fichero_ni_una_semilla(
        self, cliente, cuenta, tmp_path
    ):
        import os

        carpeta = pathlib.Path(os.environ["CUEDIGITAL_ADJUNTOS"])
        antes = sorted(p.name for p in carpeta.rglob("*")) if carpeta.exists() else []

        respuesta = _subir_etiqueta(cliente, cuenta["cabeceras"])
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["guardado"] is False
        assert respuesta.json()["campos_leidos"], "tiene que decir qué ha leído"

        assert cliente.get("/api/semillas", headers=cuenta["cabeceras"]).json() == []
        existencias = cliente.get("/api/almacen/existencias", headers=cuenta["cabeceras"]).json()
        assert existencias["articulos"] == []
        despues = sorted(p.name for p in carpeta.rglob("*")) if carpeta.exists() else []
        assert despues == antes, "leer la etiqueta no puede dejar el papel en el disco"

    def test_lo_que_no_viene_se_queda_vacio_y_no_se_convierte_en_no_tratada(self, cliente, cuenta):
        """`tratada` tiene tres respuestas, y un hueco no es un «no»."""
        semilla = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={"nombre": "Semilla sin papel", "unidad": "kg"},
        )
        assert semilla.status_code == 201, semilla.text
        datos = semilla.json()
        assert datos["tratada"] is None
        assert datos["poder_germinativo_pct"] is None
        assert datos["pureza_pct"] is None
        assert datos["fecha_caducidad"] is None

    def test_una_etiqueta_que_no_habla_del_tratamiento_no_dice_ni_si_ni_no(self):
        leida = semillas.lo_que_dice_la_etiqueta(
            semillas.EtiquetaLeida(), "ESPECIE: TRIGO BLANDO\nVARIEDAD: CRAKLIN"
        )
        assert leida.tratada is None, "«no lo dice» no es «no viene tratada»"

    def test_DEFECTO_sin_tratamiento_se_lee_como_tratada(self):
        """DEFECTO 3 · «SEMILLA SIN TRATAMIENTO» se lee al revés.

        El módulo dice en su cabecera que «la lectura de la etiqueta busca primero la negación»
        porque leerla al revés «sería un dato grave». La negación que busca es `sin tratar`, que **no**
        encaja en `sin tratamiento` (hay letras de más), así que la frase más normal que se escribe en
        un saco —«SEMILLA SIN TRATAMIENTO»— acaba marcando la semilla como **tratada**.

        Al agricultor: la ficha y la pantalla dicen que la semilla viene tratada cuando el papel dice
        lo contrario, y la semilla tratada tiene sus propias reglas de manejo. Y lo dice el programa,
        no él.
        """
        # Los dos casos que el ticket sí cubre, para que se vea que la prueba no falla por gusto.
        assert (
            semillas.lo_que_dice_la_etiqueta(
                semillas.EtiquetaLeida(), "SEMILLA NO TRATADA"
            ).tratada
            is False
        )
        assert (
            semillas.lo_que_dice_la_etiqueta(
                semillas.EtiquetaLeida(), "SEMILLA TRATADA CON FUNGICIDA"
            ).tratada
            is True
        )

        for papel in (
            "SEMILLA SIN TRATAMIENTO",
            "NO LLEVA TRATAMIENTO",
            "NO SE HA APLICADO NINGÚN TRATAMIENTO",
        ):
            leida = semillas.lo_que_dice_la_etiqueta(semillas.EtiquetaLeida(), papel)
            assert leida.tratada is False, (
                f"«{papel}» dice que NO viene tratada y el programa la marca como "
                f"{leida.tratada!r}"
            )

    def test_DEFECTO_la_unidad_leida_no_es_la_que_ofrece_el_programa(self):
        """DEFECTO 9 · «2 L/ha» se lee `l/ha`, y la pantalla ofrece `L/ha`.

        Es lo que queda del defecto 4 después de arreglarlo (03/10/2026, 19:35): el arreglo traduce
        cada trozo de la unidad con `_UNIDADES_EN_SU_FORMA_CORTA` (`semillas.py:497-520`), pero esa
        tabla tiene `litro` y `litros` y no tiene `l` —ni `kg`, `g`, `ml`—, así que la forma corta que
        escriben las etiquetas de verdad se queda como venía del papel en minúsculas: `l/ha`. Y la
        lista que ofrece el programa es `("kg/ha", "g/ha", "ud/ha", "L/ha")` (`semillas.py:63`).

        Al agricultor: la misma unidad escrita de dos maneras —«2 L/ha» y «2 litros/ha»— da dos textos
        distintos, y el desplegable de la dosis de la pantalla se queda sin su opción y elige «sin
        decir». Las cuentas del almacén no se rompen (comparan las unidades sin mirar mayúsculas,
        `servicios.se_pueden_sumar`), así que esto se queda en la pantalla; por eso es pequeño.
        """
        for papel in ("DOSIS: 2 L/ha", "DOSIS: 2 l/ha", "DOSIS: 2 litros/ha", "DOSIS: 250 g/ha"):
            leida = semillas.lo_que_dice_la_etiqueta(semillas.EtiquetaLeida(), papel)
            assert leida.unidad_dosis in semillas.UNIDADES_DE_DOSIS, (
                f"«{papel}» se lee como {leida.unidad_dosis!r}, que no está entre las que ofrece la "
                f"pantalla {semillas.UNIDADES_DE_DOSIS}: el desplegable se queda sin su opción"
            )

    def test_DEFECTO_la_unidad_de_la_dosis_se_guarda_como_una_palabra_pegada(self):
        """DEFECTO 4 · «120 kg por hectárea» se guarda con la unidad `kgporhectarea`.

        `_unidad_de` devuelve «la unidad que va detrás del número, tal cual (`kg/ha`, `kg`, `ud/ha`)»,
        pero pega el «por hectárea» dentro de la unidad. Es la forma en que media España escribe una
        dosis en la etiqueta y en el catálogo (más normal que `kg/ha`), y lo que se guarda no es una
        unidad: es una palabra.

        Al agricultor: en la ficha de la semilla lee «120 kgporhectarea», y ese texto es el que
        pre-rellena el desplegable de la dosis al sembrar (que solo ofrece `kg/ha`, `g/ha`, `ud/ha` y
        `L/ha`), así que el desplegable se queda sin su opción y la siembra puede acabar sin unidad.
        """
        assert semillas._unidad_de("120 kg/ha") == "kg/ha"
        assert semillas._unidad_de("120 kg") == "kg"

        leida = semillas.lo_que_dice_la_etiqueta(
            semillas.EtiquetaLeida(), "DOSIS RECOMENDADA: 120 kg por hectárea"
        )
        assert leida.dosis_recomendada_por_ha == 120.0
        assert leida.unidad_dosis == "kg/ha", (
            f"la unidad guardada es {leida.unidad_dosis!r}, y eso no es una unidad"
        )


# ==========================================================================
# CONTRATO 4 · Un dato ausente no es cero
# ==========================================================================


class TestContrato4_UnDatoAusenteNoEsCero:
    def test_una_semilla_sin_papel_no_rellena_ninguna_cifra(self, cliente, cuenta):
        semilla = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={"nombre": "Semilla guardada del año pasado", "unidad": "kg"},
        ).json()
        for campo in (
            "dosis_recomendada_por_ha",
            "fecha_envasado",
            "fecha_caducidad",
            "poder_germinativo_pct",
            "pureza_pct",
            "tratada",
        ):
            assert semilla[campo] is None, f"`{campo}` tiene que quedarse vacío, no en {semilla[campo]!r}"

    def test_la_caducidad_que_no_se_sabe_no_es_una_caducidad_buena(self, cliente, cuenta, montado):
        envase = montado["semilla"]["envases"][0]
        assert envase["caducado"] is False
        # Y un envase del que no consta la caducidad: ni sí ni no.
        almacen = _almacen(
            cliente,
            cuenta["cabeceras"],
            nombre="Semilla sin caducidad",
            numero_lote="SIN-FECHA",
            numero_albaran="ALB-2026-79",
            fecha_caducidad=None,
        )
        asociada = _dar_de_alta_la_semilla(
            cliente, cuenta["cabeceras"], almacen, numero_lote_proveedor=None
        )
        assert asociada["envases"][0]["caducado"] is None, (
            "«no se sabe cuándo caduca» no es «está en fecha»"
        )

    def test_DEFECTO_una_semilla_sin_ninguna_entrada_dice_que_queda_cero(self, cliente, cuenta):
        """DEFECTO 5 · Una semilla dada de alta a mano dice «queda 0».

        El documento (§1.4) promete: «el saldo con su unidad y, cuando no se puede saber, “No se puede
        saber lo que queda” con su motivo. **Nunca un cero**». Una semilla recién dada de alta —sin
        albarán— tiene un artículo sin ningún movimiento y **sin unidad**, y la respuesta trae
        `saldo: 0.0` con `unidad: null`: la pantalla escribe «Te queda 0», sin unidad.

        Al agricultor: compra la semilla, hace la foto de la etiqueta y la confirma —el camino que el
        propio ticket describe— y la lista le dice que no le queda nada, cuando el saco está en la
        nave. Un cero ahí es una afirmación, y el programa no la puede sostener.
        """
        semilla = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={"nombre": "Veza que compré sin albarán", "unidad": "kg"},
        ).json()
        assert semilla["queda"] is not None
        assert semilla["queda"]["saldo"] is None, (
            "sin ningún movimiento no se puede contar nada: tiene que ser «no se puede saber» con su "
            f"motivo, no {semilla['queda']['saldo']!r}"
        )
        assert semilla["queda"]["motivo"], "y tiene que decir por qué"


# ==========================================================================
# CONTRATO 5 · Aislamiento entre explotaciones (404, no 403)
# ==========================================================================


@pytest.fixture
def dos_fincas(cliente, cuenta, crear_cuenta, crear_parcela):
    """Mi finca con una semilla sembrada, y otra finca con lo suyo."""
    almacen = _almacen(cliente, cuenta["cabeceras"])
    semilla = _dar_de_alta_la_semilla(cliente, cuenta["cabeceras"], almacen)
    tierra = crear_parcela()
    siembra = _sembrar(
        cliente,
        cuenta["cabeceras"],
        _siembra(semilla["id"], tierra["id"], lote_id=almacen["lote_id"]),
    ).json()

    otro = crear_cuenta("vecino@ejemplo.test", "El vecino", "12345678Z")
    otra_tierra = _parcela(cliente, otro["cabeceras"], alias="La del vecino")
    otro_almacen = _almacen(
        cliente,
        otro["cabeceras"],
        nombre="Semilla del vecino",
        numero_lote="V-1",
        numero_albaran="ALB-VECINO-1",
    )
    otra_semilla = _dar_de_alta_la_semilla(
        cliente,
        otro["cabeceras"],
        otro_almacen,
        nombre="Semilla del vecino",
        numero_lote_proveedor="V-1",
    )
    return {
        "almacen": almacen,
        "semilla": semilla,
        "tierra": tierra,
        "siembra": siembra,
        "otro": otro,
        "otra_tierra": otra_tierra,
        "otro_almacen": otro_almacen,
        "otra_semilla": otra_semilla,
    }


class TestContrato5_DeOtraFincaNoSeVeNada:
    def test_no_se_puede_corregir_una_siembra_de_otra_finca(
        self, cliente, dos_fincas
    ):
        vecino = dos_fincas["otro"]
        respuesta = cliente.put(
            f"/api/siembras/{dos_fincas['siembra']['id']}",
            headers=vecino["cabeceras"],
            json=_siembra(
                dos_fincas["semilla"]["id"], dos_fincas["tierra"]["id"], lote_id=None
            ),
        )
        assert respuesta.status_code == 404, (
            f"corregir la siembra de otra finca tiene que dar 404 (y no 403): {respuesta.status_code}"
        )

    def test_no_se_puede_subir_una_foto_a_la_semilla_de_otra_finca(self, cliente, dos_fincas):
        vecino = dos_fincas["otro"]
        respuesta = cliente.post(
            f"/api/semillas/{dos_fincas['semilla']['id']}/etiqueta",
            headers=vecino["cabeceras"],
            files={"fichero": ("etiqueta.pdf", _etiqueta_en_pdf(["ESPECIE: TRIGO"]), "application/pdf")},
        )
        assert respuesta.status_code == 404, respuesta.text
        mía = cliente.get(
            f"/api/semillas/{dos_fincas['semilla']['id']}", headers=vecino["cabeceras"]
        )
        assert mía.status_code == 404

    def test_no_se_puede_sembrar_en_una_tierra_de_otra_finca(self, cliente, dos_fincas):
        vecino = dos_fincas["otro"]
        respuesta = _sembrar(
            cliente,
            vecino["cabeceras"],
            _siembra(
                dos_fincas["otra_semilla"]["id"],
                dos_fincas["tierra"]["id"],  # mi tierra, desde la cuenta del vecino
                lote_id=dos_fincas["otro_almacen"]["lote_id"],
            ),
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_no_se_puede_colgar_una_etiqueta_a_un_articulo_de_otra_finca(
        self, cliente, dos_fincas
    ):
        vecino = dos_fincas["otro"]
        respuesta = cliente.post(
            "/api/semillas",
            headers=vecino["cabeceras"],
            json={
                "articulo_id": dos_fincas["almacen"]["articulo_id"],
                "nombre": "La semilla del vecino de al lado",
            },
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_no_se_puede_descontar_de_un_envase_de_otra_finca(self, cliente, dos_fincas):
        vecino = dos_fincas["otro"]
        respuesta = _sembrar(
            cliente,
            vecino["cabeceras"],
            _siembra(
                dos_fincas["otra_semilla"]["id"],
                dos_fincas["otra_tierra"]["id"],
                lote_id=dos_fincas["almacen"]["lote_id"],  # mi saco
            ),
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_preguntar_por_la_tierra_de_otra_finca_no_da_sus_siembras(self, cliente, dos_fincas):
        vecino = dos_fincas["otro"]
        respuesta = cliente.get(
            f"/api/siembras?parcela_id={dos_fincas['tierra']['id']}",
            headers=vecino["cabeceras"],
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_la_finca_del_vecino_no_aparece_en_ninguna_lista(self, cliente, dos_fincas):
        vecino = dos_fincas["otro"]
        mias = cliente.get("/api/semillas", headers=vecino["cabeceras"]).json()
        assert [semilla["id"] for semilla in mias] == [dos_fincas["otra_semilla"]["id"]]
        assert cliente.get("/api/siembras", headers=vecino["cabeceras"]).json() == []


# ==========================================================================
# CONTRATO 6 · Corregir y anular sin duplicar
# ==========================================================================


class TestContrato6_CorregirYAnular:
    def test_la_secuencia_entera_apuntar_corregir_anular_volver_a_apuntar_y_reenviar(
        self, cliente, cuenta, montado, db_sesion
    ):
        """El recorrido del encargo, de punta a punta y con el almacén a la vista en cada paso."""
        cabeceras = cuenta["cabeceras"]
        articulo = montado["almacen"]["articulo_id"]
        lote = montado["almacen"]["lote_id"]

        primera = _sembrar(
            cliente,
            cabeceras,
            _siembra(montado["semilla"]["id"], montado["tierra"]["id"], lote_id=lote,
                     cantidad_total=200.0, clave_de_reenvio="paso-1"),
        ).json()
        assert primera["descuenta"] is True
        assert _queda(cliente, cabeceras, articulo)["saldo"] == 300.0

        corregida = cliente.put(
            f"/api/siembras/{primera['id']}",
            headers=cabeceras,
            json=_siembra(montado["semilla"]["id"], montado["tierra"]["id"], lote_id=lote,
                          cantidad_total=150.0),
        ).json()
        assert corregida["cantidad_total"] == 150.0
        assert _queda(cliente, cabeceras, articulo)["saldo"] == 350.0
        vivas = [m for m in _salidas_del_apunte(db_sesion, primera["id"]) if not m.anulado]
        assert len(vivas) == 1

        cliente.post(f"/api/siembras/{primera['id']}/anular", headers=cabeceras,
                     json={"motivo": "esa tierra no era"})
        assert _queda(cliente, cabeceras, articulo)["saldo"] == 500.0

        segunda = _sembrar(
            cliente,
            cabeceras,
            _siembra(montado["semilla"]["id"], montado["tierra"]["id"], lote_id=lote,
                     cantidad_total=150.0, clave_de_reenvio="paso-2"),
        )
        assert segunda.status_code == 201, segunda.text
        assert segunda.json()["descuenta"] is True, segunda.text
        assert _queda(cliente, cabeceras, articulo)["saldo"] == 350.0

        # Y la cola del móvil reenvía esa última petición: la misma, no otra.
        reenvio = _sembrar(
            cliente,
            cabeceras,
            _siembra(montado["semilla"]["id"], montado["tierra"]["id"], lote_id=lote,
                     cantidad_total=150.0, clave_de_reenvio="paso-2"),
        )
        assert reenvio.json()["id"] == segunda.json()["id"]
        assert _queda(cliente, cabeceras, articulo)["saldo"] == 350.0
        siembras = cliente.get("/api/siembras", headers=cabeceras).json()
        assert len(siembras) == 2, "la anulada sigue en la lista, tachada"
        assert sum(1 for siembra in siembras if siembra["anulada"]) == 1

    def test_una_siembra_corregida_no_queda_dos_veces(self, cliente, cuenta, montado):
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
            ),
        ).json()
        cliente.put(
            f"/api/siembras/{primera['id']}",
            headers=cuenta["cabeceras"],
            json=_siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                cantidad_total=150.0,
                notas="era 150",
            ),
        )
        siembras = cliente.get("/api/siembras", headers=cuenta["cabeceras"]).json()
        assert len(siembras) == 1, "corregir no puede apuntar una segunda siembra"
        assert siembras[0]["cantidad_total"] == 150.0

    def test_anular_devuelve_al_almacen_sin_tocar_el_libro(
        self, cliente, cuenta, montado, db_sesion
    ):
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
            ),
        ).json()
        antes = _salidas_del_apunte(db_sesion, primera["id"])[0]

        respuesta = cliente.post(
            f"/api/siembras/{primera['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "no era esa tierra"},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["descuenta"] is False
        assert _queda(cliente, cuenta["cabeceras"], montado["almacen"]["articulo_id"])[
            "saldo"
        ] == 500.0

        despues = _salidas_del_apunte(db_sesion, primera["id"])[0]
        assert despues.id == antes.id
        assert despues.anulado is False, "el libro no se toca: se apunta que la siembra está anulada"
        assert despues.cantidad == 200.0
        assert despues.fecha == antes.fecha

    def test_una_siembra_anulada_no_se_corrige_y_se_dice(self, cliente, cuenta, montado):
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
            ),
        ).json()
        cliente.post(
            f"/api/siembras/{primera['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me equivoqué"},
        )
        respuesta = cliente.put(
            f"/api/siembras/{primera['id']}",
            headers=cuenta["cabeceras"],
            json=_siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                cantidad_total=100.0,
            ),
        )
        assert respuesta.status_code == 409, respuesta.text
        assert respuesta.json()["detail"], "y tiene que decir qué hacer"

    def test_anular_dos_veces_no_vale(self, cliente, cuenta, montado):
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
            ),
        ).json()
        for _ in range(2):
            respuesta = cliente.post(
                f"/api/siembras/{primera['id']}/anular",
                headers=cuenta["cabeceras"],
                json={"motivo": "me equivoqué"},
            )
        assert respuesta.status_code == 409, "anular dos veces no puede devolver dos veces la semilla"
        assert _queda(cliente, cuenta["cabeceras"], montado["almacen"]["articulo_id"])[
            "saldo"
        ] == 500.0

    def test_DEFECTO_una_correccion_parcial_le_borra_la_fecha_a_la_siembra(
        self, cliente, cuenta, montado
    ):
        """DEFECTO 6 · Corregir sin mandar la fecha deja la siembra **sin fecha**.

        El propio fichero del ticket deja escrito el principio para el envase: «**Una corrección
        parcial no puede dejar la siembra sin descuento.** Si la petición no manda `lote_id` … el
        envase que ya constaba se mantiene … lo que no se pregunta tiene que viajar igual». Con la
        fecha no se cumple: cualquier corrección que no la traiga apunta la siembra **sin el día en que
        se sembró** (y la salida del almacén se queda con la fecha vieja, así que el libro y el apunte
        dicen cosas distintas del mismo hecho).

        Al agricultor: corrige la cantidad desde una pantalla que no pregunte la fecha y el cuaderno
        pierde el día de la siembra, que es lo que se enseña en una inspección.
        """
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                fecha=FECHA_SIEMBRA,
            ),
        ).json()
        assert primera["fecha"] == FECHA_SIEMBRA

        sin_fecha = _siembra(
            montado["semilla"]["id"],
            montado["tierra"]["id"],
            lote_id=montado["almacen"]["lote_id"],
            cantidad_total=150.0,
        )
        sin_fecha.pop("fecha")
        respuesta = cliente.put(
            f"/api/siembras/{primera['id']}", headers=cuenta["cabeceras"], json=sin_fecha
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["fecha"] == FECHA_SIEMBRA, (
            "la fecha que ya constaba no puede desaparecer por no volver a mandarla"
        )

    def test_DEFECTO_cambiar_la_semilla_de_una_siembra_se_hace_en_silencio(
        self, cliente, cuenta, montado, db_sesion
    ):
        """DEFECTO 7 · El documento dice que cambiar la semilla «no se puede y se dice por qué».

        `docs/T10_SEMILLAS.md` §6.3: «Cambiar la semilla de una siembra guardada **no se puede** y se
        dice por qué: la salida del almacén pertenece a un artículo, así que para cambiar de semilla
        hay que anular y apuntar la nueva». En el código sí se puede: el `PUT` cambia `semilla_id` y,
        como el envase que constaba era de la otra semilla, **anula el descuento sin decir nada**, así
        que la siembra se queda apuntada con la semilla nueva, sin descuento y con el envase en blanco.

        Al agricultor que llame desde fuera o desde una pantalla futura: la semilla que había sembrado
        vuelve al almacén sola y la siembra pasa a decir que sembró otra cosa, sin un solo aviso.
        """
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
            ),
        ).json()
        otra_almacen = _almacen(
            cliente,
            cuenta["cabeceras"],
            nombre="Trigo Craklin",
            numero_lote="T-1",
            numero_albaran="ALB-2026-80",
        )
        otra = _dar_de_alta_la_semilla(
            cliente, cuenta["cabeceras"], otra_almacen, nombre="Trigo Craklin"
        )

        respuesta = cliente.put(
            f"/api/siembras/{primera['id']}",
            headers=cuenta["cabeceras"],
            json=_siembra(otra["id"], montado["tierra"]["id"], lote_id=None),
        )
        if respuesta.status_code == 200:
            datos = respuesta.json()
            assert datos["semilla_id"] == primera["semilla_id"], (
                "la semilla de una siembra guardada no se cambia: se anula y se apunta la nueva "
                f"(la respuesta ha cambiado la semilla a {datos['semilla_id']}, sin descuento "
                f"({datos['descuenta']}) y con el envase en {datos['lote_id']})"
            )
        else:
            assert respuesta.status_code in (400, 409), respuesta.text
            assert respuesta.json()["detail"], "y tiene que decir por qué"


# ==========================================================================
# CONTRATO 7 · Los textos viven en `textos.py` y ninguno lleva jerga
# ==========================================================================


class TestContrato7_LosTextos:
    def test_el_servidor_sirve_los_textos_de_las_semillas(self, cliente):
        interfaz = cliente.get("/api/interfaz").json()
        assert interfaz["semillas"], "la pantalla sin cobertura necesita estos textos"
        assert interfaz["unidades_dosis_semilla"]
        assert interfaz["unidades_cantidad_semilla"]
        for clave, valor in interfaz["semillas"].items():
            assert str(valor).strip(), f"el texto `{clave}` va vacío"

    def test_ninguna_palabra_de_las_semillas_es_jerga(self):
        revisados = 0
        for clave, valor in {**textos.SEMILLAS, **textos.MENSAJES_DE_LAS_SEMILLAS}.items():
            encontradas = textos.palabras_prohibidas_encontradas(str(valor))
            assert not encontradas, f"`{clave}` lleva jerga ({encontradas}): {valor!r}"
            revisados += 1
        assert revisados >= 40, "tienen que ser los textos de la semilla, no dos"

    def test_todos_los_mensajes_que_usa_el_router_existen(self):
        codigo = (
            pathlib.Path(__file__).resolve().parents[1] / "app" / "routers" / "semillas_api.py"
        ).read_text(encoding="utf-8")
        usados = set(re.findall(r'textos\.MENSAJES\["([A-Za-z0-9_]+)"\]', codigo))
        usados |= set(re.findall(r'textos\.mensaje\("([A-Za-z0-9_]+)"\)', codigo))
        assert usados, "no he encontrado ni un mensaje en el router: ¿ha cambiado de forma?"
        for codigo_mensaje in sorted(usados):
            assert codigo_mensaje in textos.MENSAJES, (
                f"el router usa `{codigo_mensaje}`, que no está en `textos.py`: al agricultor le "
                "llegaría un hueco en vez de una frase"
            )

    def test_los_mensajes_que_la_pantalla_usa_los_da_el_servidor(self, cliente):
        """Sin cobertura, la pantalla solo tiene lo que le ha mandado `/api/interfaz`.

        `app.js` escribe sus avisos con `mensaje("SM22_falta_la_tierra")`, que busca la frase en
        `mensajes.<código>` de lo que se descargó al arrancar. Si un código de las semillas no
        estuviera ahí, el agricultor vería **un hueco** en el momento en que le falta un dato, que es
        justo cuando está de pie en la parcela. Este guardián saca la lista del propio `app.js`, no de
        una lista escrita a mano.
        """
        raiz = pathlib.Path(__file__).resolve().parents[2]
        codigo_js = (raiz / "backend" / "web" / "app.js").read_text(encoding="utf-8")
        usados = {
            codigo_mensaje
            for codigo_mensaje in re.findall(r'mensaje\("([A-Za-z0-9_]+)"', codigo_js)
            if codigo_mensaje.startswith("SM")
        }
        assert usados, "la pantalla no usa ni un mensaje de las semillas: ¿ha cambiado de forma?"
        servidos = cliente.get("/api/interfaz").json()["mensajes"]
        for codigo_mensaje in sorted(usados):
            assert codigo_mensaje in servidos, (
                f"la pantalla pide `{codigo_mensaje}` y `/api/interfaz` no lo sirve: sin cobertura "
                "saliría en blanco"
            )
            assert servidos[codigo_mensaje].strip()


# ==========================================================================
# CONTRATO 8 · Nada de cifras inventadas
# ==========================================================================


class TestContrato8_LaPantallaNoCalcula:
    """Lo que la pantalla pinta tiene que venir contado del servidor (T10 §3.7 y T09)."""

    PATRONES = (
        r"dosis_por_ha\s*[*/\-+]",
        r"[*/\-+]\s*dosis_por_ha",
        r"superficie_ha\s*\*",
        r"\*\s*superficie_ha",
        r"cantidad_total\s*\*",
        r"\*\s*cantidad_total",
    )

    def test_las_pantallas_de_las_semillas_no_hacen_la_cuenta_de_la_dosis(self):
        raiz = pathlib.Path(__file__).resolve().parents[2]
        ficheros = [
            raiz / "backend" / "web" / "react" / "pantallas" / "semillas.js",
            raiz / "backend" / "web" / "react" / "pantallas" / "siembras.js",
        ]
        assert all(fichero.is_file() for fichero in ficheros), "no están las pantallas del T10"
        for fichero in ficheros:
            codigo = fichero.read_text(encoding="utf-8")
            for patron in self.PATRONES:
                encontrado = re.search(patron, codigo)
                assert not encontrado, (
                    f"{fichero.name} hace una cuenta con las cifras de la siembra "
                    f"({encontrado.group(0)!r}): la dosis y el total se cuentan una sola vez, "
                    "en el servidor"
                )

    def test_el_aviso_de_lo_calculado_solo_vive_en_la_respuesta_de_guardar(
        self, cliente, cuenta, montado
    ):
        """Prueba de apoyo del defecto 8: el aviso **solo** viene en la respuesta de guardar.

        Al volver a leer la siembra —que es lo que hace la pantalla justo después de guardar— ya no
        hay ningún aviso, así que si la pantalla lo tira, no hay otra copia de dónde sacarlo.
        """
        creada = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
                superficie_ha=2.5,
                dosis_por_ha=120.0,
                cantidad_total=None,
                unidad_cantidad=None,
            ),
        ).json()
        assert creada["cantidad_total_calculada"] is True
        assert creada["avisos"], "el servidor sí lo dice al guardar"
        leida = cliente.get(
            f"/api/siembras/{creada['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert leida["avisos"] == [], "al volver a leerla, el aviso ya no está en ninguna parte"

    def test_DEFECTO_la_cuenta_que_hace_el_servidor_no_llega_a_la_pantalla(self):
        """DEFECTO 8 · El número que calcula el programa se enseña **sin decir que lo ha calculado**.

        `docs/T10_SEMILLAS.md` §1.5: «Si falta una de las dos y hay hectáreas, el servidor la calcula
        **y lo dice**», y §3.2.3: «un aviso con la cuenta entera … Un número calculado se puede
        revisar; uno inventado, no». En `app.js`, `guardarLaSiembra` guarda la frase del servidor en
        `suyo.calculado` y **la pone a nulo tres líneas después, antes de pintar** la lista de lo
        sembrado; el cuadro «Lo ha calculado el programa» solo se pinta en el formulario, que ya no
        vuelve a salir. La cuenta no se lee en ningún sitio: el agricultor ve «300,00 kg» como si lo
        hubiera escrito él.

        La prueba es de lectura del código (no tengo navegador aquí), y por eso se apoya en la prueba
        de arriba: el aviso **solo** existe en la respuesta de guardar, así que tirarlo es tirarlo del
        todo. Compárese con la salida del almacén del T09, que sí hace `salida.avisos = cuerpo.avisos`
        y los pinta.
        """
        raiz = pathlib.Path(__file__).resolve().parents[2]
        codigo = (raiz / "backend" / "web" / "app.js").read_text(encoding="utf-8")
        cuerpo = _cuerpo_de_la_funcion(codigo, "guardarLaSiembra")
        assert "loQueHaCalculadoElServidor(resultado.datos)" in cuerpo, (
            "`guardarLaSiembra` ha cambiado de forma: hay que rehacer esta prueba"
        )
        assert "suyo.calculado = null;" not in cuerpo, (
            "la cuenta que ha hecho el servidor se descarta antes de pintar: el agricultor nunca lee "
            "que el total o la dosis los ha calculado el programa, y no puede revisarlos"
        )
        assert "avisos" in cuerpo, (
            "y los avisos del servidor (`resultado.datos.avisos`) tampoco se guardan para enseñarlos"
        )

    def test_las_tarjetas_enseñan_las_cifras_del_servidor_con_su_unidad(self):
        raiz = pathlib.Path(__file__).resolve().parents[2]
        codigo = (raiz / "backend" / "web" / "app.js").read_text(encoding="utf-8")
        trozo = codigo[codigo.index("function tarjetaDeUnaSiembra") :][:2600]
        assert "siembra.dosis_por_ha" in trozo and "siembra.cantidad_total" in trozo
        assert "siembra.unidad_dosis" in trozo and "siembra.unidad_cantidad" in trozo
        assert "no_descuenta_porque" in trozo, (
            "la tarjeta tiene que decir si descontó del almacén y por qué, o el agricultor no "
            "entiende por qué no ha bajado lo que queda"
        )


# ==========================================================================
# CONTRATO 9 · Firmas y auditoría intactas
# ==========================================================================


class TestContrato9_FirmasYAuditoria:
    def test_una_siembra_no_invalida_la_firma_del_cuaderno(self, cliente, cuenta, montado):
        antes = cliente.get("/api/firmas/estado", headers=cuenta["cabeceras"]).json()
        _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
            ),
        )
        despues = cliente.get("/api/firmas/estado", headers=cuenta["cabeceras"]).json()
        assert despues["huella"] == antes["huella"], (
            "apuntar una siembra y mover el almacén no puede cambiar la huella de lo que ya se firmó"
        )
        assert despues["estado"] == antes["estado"]
        assert despues["mensaje"] == antes["mensaje"]

    def test_apuntar_y_anular_una_siembra_deja_rastro(self, cliente, cuenta, montado, db_sesion):
        primera = _sembrar(
            cliente,
            cuenta["cabeceras"],
            _siembra(
                montado["semilla"]["id"],
                montado["tierra"]["id"],
                lote_id=montado["almacen"]["lote_id"],
            ),
        ).json()
        cliente.post(
            f"/api/siembras/{primera['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "no era esa tierra"},
        )
        db_sesion.rollback()
        anotaciones = list(
            db_sesion.scalars(
                select(models.Auditoria)
                .where(models.Auditoria.entidad == "siembra")
                .order_by(models.Auditoria.id)
            )
        )
        acciones = [anotacion.accion for anotacion in anotaciones]
        assert "crear" in acciones
        assert "anular" in acciones, "anular sin rastro no sirve en una inspección"
        ultima = anotaciones[-1]
        assert ultima.datos.get("motivo"), "y el motivo tiene que quedar escrito"
