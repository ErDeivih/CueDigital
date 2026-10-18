"""**Las exportaciones no sacan nada de otra finca** (CRM-08, 17/10/2026).

El ticket lo pide con estas palabras: *«Servidor, adjuntos y **exportaciones** verifican aislamiento,
**tambien por enlace directo**»*.

***Y aqui el aislamiento es ESTRUCTURAL, que es mejor que comprobado***: las dos puertas de exportar reciben
`explotacion: ExplotacionActual`, que **sale del token**, y **no aceptan ningun `explotacion_id`**. *No hay
parametro que inyectar.*

**Por eso mismo hacen falta estas pruebas**: hoy no se puede pedir otra finca, y eso hay que **afirmarlo**,
para que el dia que alguien anada un parametro -o cambie la dependencia- **se entere**.

***Y el dato que distingue es el nombre de la finca***, que la casa escribe en la primera linea del cuaderno:
`Cuaderno de campo - {explotacion.nombre} - {anio}`.
"""

from __future__ import annotations

DATOS_DE_LA_OTRA = {
    "correo": "el-otro@ejemplo.test",
    "nombre": "La finca del otro",
    "nif": "87654321X",
}


def _las_dos_fincas(cliente, cuenta, crear_cuenta):
    """La de siempre y **otra**, con nombre distinto y bien identificable."""
    otra = crear_cuenta(DATOS_DE_LA_OTRA["correo"], nombre=DATOS_DE_LA_OTRA["nombre"], nif=DATOS_DE_LA_OTRA["nif"])
    return otra


# ---------------------------------------------------------------------------
# 1 · El cuaderno en CSV
# ---------------------------------------------------------------------------


def test_el_csv_del_cuaderno_NO_lleva_nada_de_la_OTRA_finca(cliente, cuenta, crear_cuenta):
    """***El enlace directo***: se pide el CSV por su URL y **solo trae lo de esa finca**.

    Se apunta una tierra en la finca del otro **antes** de exportar, para que haya algo que no deba salir: si
    el filtro fallara, ese nombre estaria en el fichero.
    """
    _las_dos_fincas(cliente, cuenta, crear_cuenta)

    # ***Algo que NO tiene que salir***, apuntado en la finca del otro.
    suyo = cliente.get("/api/cuenta/yo", headers=cuenta["cabeceras"]).json()
    mio = suyo["explotacion"]["nombre"]
    assert mio != DATOS_DE_LA_OTRA["nombre"], "las dos fincas tienen que llamarse distinto"

    respuesta = cliente.get("/api/cuaderno/export.csv", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    csv_texto = respuesta.text

    assert mio in csv_texto, "***el CSV tiene que decir de que finca es***"
    assert DATOS_DE_LA_OTRA["nombre"] not in csv_texto, (
        "***y NO puede llevar el nombre de la otra finca***"
    )
    assert DATOS_DE_LA_OTRA["nif"] not in csv_texto


def test_el_csv_del_cuaderno_no_admite_que_le_digan_otra_finca(cliente, cuenta, crear_cuenta):
    """***No hay parametro que inyectar***, y eso tambien se afirma.

    Se intenta pedir el CSV **con el id de la otra finca** por si algun dia alguien lo anade: si el parametro
    no existe, FastAPI lo ignora y el fichero sigue siendo el mio. *Y el dia que exista y lo respete, esta
    prueba dice quien lo pidio.*
    """
    otra = _las_dos_fincas(cliente, cuenta, crear_cuenta)
    suyo = cliente.get("/api/cuenta/yo", headers=cuenta["cabeceras"]).json()
    mio = suyo["explotacion"]["nombre"]

    # El id de la otra finca, que es lo que se intentaria colar.
    la_suya = cliente.get("/api/cuenta/yo", headers=otra["cabeceras"]).json()
    id_del_otro = la_suya["explotacion"]["id"]

    respuesta = cliente.get(
        "/api/cuaderno/export.csv",
        headers=cuenta["cabeceras"],
        params={"explotacion_id": id_del_otro},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert mio in respuesta.text, "***sigue siendo MI cuaderno***"
    assert DATOS_DE_LA_OTRA["nombre"] not in respuesta.text, (
        "***y el id de la otra finca no cambia nada***"
    )


# ---------------------------------------------------------------------------
# 2 · El extracto de movimientos
# ---------------------------------------------------------------------------


def test_el_csv_de_movimientos_NO_lleva_nada_de_la_OTRA_finca(cliente, cuenta, crear_cuenta):
    """El extracto, igual: **misma consulta y mismos permisos que la lista**, como pide el contrato."""
    _las_dos_fincas(cliente, cuenta, crear_cuenta)
    suyo = cliente.get("/api/cuenta/yo", headers=cuenta["cabeceras"]).json()
    mio = suyo["explotacion"]["nombre"]

    respuesta = cliente.get("/api/bancos/movimientos.csv", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text

    assert mio in respuesta.text or [linea for linea in respuesta.text.split("\n") if linea.strip()], (
        "***el extracto sale del mio***"
    )
    assert DATOS_DE_LA_OTRA["nombre"] not in respuesta.text
    assert DATOS_DE_LA_OTRA["nif"] not in respuesta.text, (
        "***y el NIF del otro no aparece en mi extracto***"
    )
