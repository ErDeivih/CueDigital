"""Las tres puertas nuevas del armazón: importar el cuaderno, el resumen y lo que falta (IMP-4).

Lo que se comprueba aquí, y por qué cada cosa:

  · **Importar el cuaderno de la Junta con la finca**: en una sola llamada se lee el fichero, se
    rellenan los huecos del titular y se apuntan las tierras. Y **subirlo dos veces no duplica
    nada** — es la prueba de que el emparejamiento por referencia del SIGPAC está bien hecho.
  · **Los huecos del titular se rellenan y no se pisan**: lo que el agricultor ya había escrito
    manda; lo que estaba en blanco se rellena con lo que dice el papel.
  · **El orden de las puertas**: sin sesión, `401`; sin permiso de modificar, `403` **antes de leer
    el fichero** (por eso el 403 se prueba con un fichero que ni siquiera es un cuaderno); con un
    fichero que no es el cuaderno, `422` y un mensaje que se entiende.
  · **El resumen no inventa**: sin gastos el total es `0` (de verdad no se ha gastado nada); y una
    cifra que no se puede saber va como `None`, no como un cero que parecería completa.
  · **«Qué falta» dice dónde se arregla** y si bloquea, y sus números cuadran con los del resumen.

El cuaderno de prueba es `tests/datos/cuaderno_cyl_de_ejemplo.xlsx`, fabricado con datos inventados
(ver `tests/datos/LEEME.md`): los de verdad llevan el NIF y las tierras de una persona.
"""

from __future__ import annotations

from pathlib import Path

from app import models
from test_los_permisos_por_materia import _sin_capacidad  # noqa: E402 — el andamiaje, prestado

FICHERO_DE_EJEMPLO = Path(__file__).resolve().parent / "datos" / "cuaderno_cyl_de_ejemplo.xlsx"

# Lo que trae el fichero de ejemplo en su hoja 1.1 (lo comprueba `test_cuaderno_cyl.py`).
NOMBRE_DEL_PAPEL = "EXPLOTACIÓN DE EJEMPLO"
NIF_DEL_PAPEL = "12345678Z"
REGISTRO_DEL_PAPEL = "9999999999"

LAS_TRES = ("/api/nuevo/importar-cuaderno", "/api/nuevo/resumen", "/api/nuevo/que-falta")


def _subir(
    cliente,
    cabeceras,
    *,
    ruta: str = "/api/nuevo/importar-cuaderno",
    nombre: str = "CuadernoExplotacion_12345678Z.xlsx",
    contenido: bytes | None = None,
):
    """Sube el cuaderno de ejemplo, como lo haría el navegador (multipart)."""
    return cliente.post(
        ruta,
        headers=cabeceras,
        files={
            "fichero": (
                nombre,
                FICHERO_DE_EJEMPLO.read_bytes() if contenido is None else contenido,
            )
        },
    )


def _finca(db_sesion, cuenta) -> models.Explotacion:
    db_sesion.expire_all()
    return db_sesion.get(models.Explotacion, cuenta["explotacion_id"])


def _un_gasto(cliente, cuenta, campana, **cambios) -> dict:
    datos = {
        "campana_id": campana["id"],
        "fecha": "2026-03-04",
        "concepto": "Gasóleo",
        "categoria": "gasoleo",
        "importe": "100.00",
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/gastos", headers=cuenta["cabeceras"], json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["gasto"]


# --------------------------------------------------------------------------- sin sesión


def test_sin_sesion_las_tres_puertas_contestan_401(cliente):
    """La puerta es la que autoriza: sin vale no se ve ni se importa nada."""
    for ruta in LAS_TRES:
        if ruta == LAS_TRES[0]:
            respuesta = _subir(cliente, {}, ruta=ruta)
        else:
            respuesta = cliente.get(ruta)
        assert respuesta.status_code == 401, (ruta, respuesta.text)


# --------------------------------------------------------------------------- importar


def test_importar_apunta_las_tierras_y_las_cuenta_en_una_respuesta(cliente, cuenta):
    respuesta = _subir(cliente, cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    # Las cinco partes del contrato, en una sola respuesta.
    assert set(datos) == {"leido", "importado", "finca_actualizada", "que_falta", "tierras"}
    assert datos["leido"]["anio"] == 2026
    assert datos["leido"]["titular"] == NOMBRE_DEL_PAPEL
    assert datos["leido"]["nif"] == NIF_DEL_PAPEL
    # `leido` es un resumen: no lleva el listado de las 54 líneas.
    assert "lineas" not in datos["leido"]

    importado = datos["importado"]
    assert importado["anio"] == 2026
    assert isinstance(importado["campana_id"], int)
    assert importado["creadas"] >= 1
    assert importado["ya_estaban"] == 0
    # Todas las líneas del papel están contadas: las que se apuntaron, las que ya estaban y las que
    # no se pudieron identificar (el fichero de ejemplo trae una sin recinto, a propósito).
    assert importado["lineas_leidas"] == (
        importado["creadas"] + importado["con_cultivo"] + importado["ya_estaban"] + importado["sin_apuntar"]
    )
    assert importado["sin_apuntar"] >= 1

    # Las tierras que dice la respuesta son las que han quedado de verdad en la finca.
    assert datos["tierras"]["n"] == importado["creadas"] + importado["con_cultivo"]
    assert len(cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()) == datos["tierras"]["n"]

    # Y lo que falta del cuaderno viene resumido, con sus ejemplos.
    assert datos["que_falta"]["faltan"] >= 1
    assert datos["que_falta"]["ejemplos"]


def test_subir_el_mismo_cuaderno_dos_veces_no_duplica_nada(cliente, cuenta):
    primera = _subir(cliente, cuenta["cabeceras"]).json()
    tierras_tras_la_primera = len(cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json())

    segunda = _subir(cliente, cuenta["cabeceras"])
    assert segunda.status_code == 200, segunda.text
    datos = segunda.json()

    assert datos["importado"]["creadas"] == 0
    assert datos["importado"]["con_cultivo"] == 0
    assert datos["importado"]["ya_estaban"] == primera["importado"]["lineas_leidas"] - primera[
        "importado"
    ]["sin_apuntar"]
    assert len(cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()) == tierras_tras_la_primera
    # Tampoco se duplica la campaña: la del cuaderno es una sola.
    assert datos["importado"]["anio"] == primera["importado"]["anio"]


def test_rellena_los_huecos_del_titular_y_no_pisa_lo_que_ya_habia(
    cliente, cuenta, db_sesion
):
    """Dos casos en el mismo test, porque son la misma regla: el hueco se rellena, lo escrito no."""
    finca = _finca(db_sesion, cuenta)
    finca.nombre = ""
    finca.nif = ""
    finca.registro_autonomico = ""
    db_sesion.commit()

    datos = _subir(cliente, cuenta["cabeceras"]).json()

    finca = _finca(db_sesion, cuenta)
    assert finca.nombre == NOMBRE_DEL_PAPEL
    assert finca.nif == NIF_DEL_PAPEL
    assert finca.registro_autonomico == REGISTRO_DEL_PAPEL
    # Y se dice qué se ha rellenado, para poder enseñarlo en la pantalla.
    for campo in ("nombre", "NIF", "nº de registro de la explotación"):
        assert campo in datos["finca_actualizada"], (campo, datos["finca_actualizada"])

    # **Lo que ya estaba escrito no se pisa.**
    finca = _finca(db_sesion, cuenta)
    finca.nombre = "La finca de casa"
    finca.nif = "11111111H"
    db_sesion.commit()

    segunda = _subir(cliente, cuenta["cabeceras"]).json()
    finca = _finca(db_sesion, cuenta)
    assert finca.nombre == "La finca de casa"
    assert finca.nif == "11111111H"
    assert "nombre" not in segunda["finca_actualizada"]
    assert "NIF" not in segunda["finca_actualizada"]


def test_sin_permiso_de_modificar_contesta_403_antes_de_leer(cliente, cuenta, db_sesion):
    """**403 y antes de leer**: se sube un fichero que no es un cuaderno y aun así contesta 403.

    Si el orden estuviera al revés, este test recibiría un 422 del lector: el permiso se comprueba
    en la puerta, no después de haber abierto el fichero del agricultor.
    """
    _sin_capacidad(db_sesion, cuenta, "puede_modificar")

    respuesta = _subir(cliente, cuenta["cabeceras"], contenido=b"esto no es un libro de calculo")
    assert respuesta.status_code == 403, respuesta.text
    # Y no ha escrito nada.
    assert cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json() == []


def test_un_fichero_que_no_es_el_cuaderno_contesta_422(cliente, cuenta):
    """Lo que no es el cuaderno se dice, y no se apunta nada."""
    basura = _subir(cliente, cuenta["cabeceras"], contenido=b"no soy un libro de calculo")
    assert basura.status_code == 422, basura.text
    assert basura.json()["detail"]

    # Y un PDF (la extensión que no es) tampoco se intenta leer.
    pdf = _subir(cliente, cuenta["cabeceras"], nombre="cuaderno.pdf")
    assert pdf.status_code == 422, pdf.text

    assert cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json() == []


# --------------------------------------------------------------------------- resumen


def test_resumen_de_una_finca_sin_datos(cliente, cuenta):
    """Sin gastos ni ventas, **cero es la verdad**: no se ha gastado ni cobrado nada."""
    respuesta = cliente.get("/api/nuevo/resumen", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    assert set(datos) == {"gastos", "ventas", "cuaderno", "facturas"}
    # Cero de verdad: la suma de ninguna factura es cero, no «no se sabe».
    assert datos["gastos"] == {"total": 0.0, "pendiente": 0.0}
    assert datos["ventas"] == {"total": 0.0, "cobrado": 0.0, "pendiente": 0.0}
    assert datos["facturas"] == {"n": 0}
    # El cuaderno de una finca recién creada está vacío: falta todo, y se dice.
    assert datos["cuaderno"]["faltan"] >= 1
    assert isinstance(datos["cuaderno"]["ejemplos"], list)


def test_resumen_con_un_gasto_y_una_venta(cliente, cuenta, campana, crear_venta):
    """Los dos lados del dinero, cada uno por su cuenta y sin mezclarse."""
    _un_gasto(cliente, cuenta, campana, importe="100.00")
    crear_venta(importe="250.00")

    datos = cliente.get("/api/nuevo/resumen", headers=cuenta["cabeceras"]).json()

    # El gasto no está pagado: se debe entero.
    assert datos["gastos"]["total"] == 100.0
    assert datos["gastos"]["pendiente"] == 100.0
    # La entrega tiene importe pero no está facturada: no se debe nada todavía.
    assert datos["ventas"]["total"] == 250.0
    assert datos["ventas"]["cobrado"] == 0.0
    assert datos["ventas"]["pendiente"] == 0.0


def test_resumen_si_un_gasto_no_dice_lo_que_costo_el_total_no_se_sabe(cliente, cuenta, campana):
    """Un gasto sin importe: el total **no se puede saber**, y va como `None`.

    Sumar solo los que se conocen daría una cifra más pequeña que la de verdad, y en las cuentas de
    una explotación eso no es un redondeo: es un número falso.
    """
    _un_gasto(cliente, cuenta, campana, concepto="Sin papel", importe=None)
    _un_gasto(cliente, cuenta, campana, concepto="Con papel", importe="40.00")

    datos = cliente.get("/api/nuevo/resumen", headers=cuenta["cabeceras"]).json()
    assert datos["gastos"]["total"] is None
    assert datos["gastos"]["pendiente"] is None


# --------------------------------------------------------------------------- qué falta


def test_que_falta_dice_que_falta_donde_se_arregla_y_si_bloquea(cliente, cuenta):
    respuesta = cliente.get("/api/nuevo/que-falta", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    assert set(datos) == {"faltan", "items"}
    assert datos["faltan"] == len(datos["items"])
    assert datos["faltan"] >= 1
    for item in datos["items"]:
        assert set(item) == {"que", "donde", "bloquea"}
        assert item["que"], item
        assert item["donde"], item
        assert isinstance(item["bloquea"], bool)
    # Lo del volcado oficial a la Junta **bloquea** (sin certificado y sin alta no se presenta):
    # tiene que estar en la lista, y marcado como lo que es.
    assert any(item["bloquea"] for item in datos["items"])


def test_que_falta_y_el_resumen_dicen_el_mismo_numero(cliente, cuenta):
    """Un número que sale en dos pantallas se calcula una vez, o un día dicen cosas distintas."""
    que_falta = cliente.get("/api/nuevo/que-falta", headers=cuenta["cabeceras"]).json()
    resumen = cliente.get("/api/nuevo/resumen", headers=cuenta["cabeceras"]).json()
    assert resumen["cuaderno"]["faltan"] == que_falta["faltan"]
    # Y los ejemplos del resumen son de la misma lista, no una lista escrita aparte.
    assert resumen["cuaderno"]["ejemplos"] == [item["que"] for item in que_falta["items"][:3]]


# --------------------------------------------------------------------------- aislamiento


def test_lo_importado_en_una_finca_no_se_ve_en_otra(cliente, cuenta, crear_cuenta):
    """Dos agricultores: el cuaderno de uno no aparece en la finca del otro."""
    _subir(cliente, cuenta["cabeceras"])
    assert len(cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()) >= 1

    otro = crear_cuenta("otro@ejemplo.test")
    assert cliente.get("/api/parcelas", headers=otro["cabeceras"]).json() == []
    su_resumen = cliente.get("/api/nuevo/resumen", headers=otro["cabeceras"]).json()
    assert su_resumen["gastos"] == {"total": 0.0, "pendiente": 0.0}
    assert su_resumen["ventas"] == {"total": 0.0, "cobrado": 0.0, "pendiente": 0.0}
    assert cliente.get("/api/nuevo/tierras", headers=otro["cabeceras"]).json()["totales"]["n"] == 0
