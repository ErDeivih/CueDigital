"""**El panel no ensena dinero a quien no puede verlo** (18/10/2026, revision independiente).

### ***El defecto, reproducido por la revision***

    Con una cuenta de prueba sin capacidad economica:
      · el saldo del contacto responde ***403***  -la restriccion esta activa-
      · y `/api/panel` respondia ***200*** con ***123,45 EUR*** de gastos dentro

***Es un fallo del SERVIDOR***: *esconder la cifra en la pantalla no lo resuelve, porque **el dinero ya ha
viajado por la red**.*

### ***Y lo que esta prueba fija, con el importe conocido***

  1. **El titular lo ve**: *la metrica `gastos`, con sus 123,45.*
  2. ***Sin la capacidad, la metrica NO EXISTE***: *no es un cero, no es un subtotal, no es una cobertura -es
     que **no se construye**-.*
  3. ***Y el importe no aparece EN NINGUNA PARTE de la respuesta***: *se mira el texto entero, no solo la
     metrica -porque un numero se puede colar en un total, en un aviso o en un enlace-.*
  4. **Y el panel agronomico se conserva**: *lo que no es dinero se sigue viendo. **El contrato quiere que la
     cuenta de consulta siga viendo su finca**, no que se quede sin panel.*
  5. **Y otra explotacion no ve este dinero.**

***El ayudante `_sin_capacidad` se IMPORTA, no se copia***: *vive en `test_los_permisos_por_materia.py` y ya
esta probado.*
"""

from __future__ import annotations

from test_los_permisos_por_materia import _sin_capacidad  # noqa: E402  — el andamiaje, prestado

EL_IMPORTE = "123.45"


def un_gasto(cliente, cuenta, campana, importe: str = EL_IMPORTE) -> dict:
    creado = cliente.post(
        "/api/gastos",
        headers=cuenta["cabeceras"],
        json={"campana_id": campana["id"], "concepto": "El gasoleo del panel", "importe": importe},
    )
    assert creado.status_code in (200, 201), creado.text
    return creado.json()


def la_metrica(datos: dict, clave: str) -> dict | None:
    return next((una for una in datos["las_metricas"] if una["clave"] == clave), None)


def test_el_titular_ve_su_dinero_en_el_panel(cliente, cuenta, campana):
    """*Lo primero: que la metrica **existe** y trae la cifra. Sin esto, la prueba de abajo pasaria por
    casualidad -un panel que no ensena gastos nunca-.*"""
    un_gasto(cliente, cuenta, campana)

    datos = cliente.get("/api/panel", headers=cuenta["cabeceras"]).json()
    los_gastos = la_metrica(datos, "gastos")

    assert los_gastos is not None, f"***el titular tiene que ver sus gastos***: {[m['clave'] for m in datos['las_metricas']]}"
    assert los_gastos["unidad"] == "EUR", los_gastos
    assert los_gastos["valor"] == 123.45, f"***y la cifra***: {los_gastos['valor']}"


def test_sin_capacidad_economica_el_dinero_NO_VIAJA(cliente, cuenta, campana, db_sesion):
    """***El defecto de la revision, fijado.***

    *Con la capacidad apagada: **el saldo da 403** -la restriccion esta activa- **y el panel no lleva el
    importe por ningun lado**.*
    """
    un_gasto(cliente, cuenta, campana)
    _sin_capacidad(db_sesion, cuenta, "puede_ver_lo_economico")

    respuesta = cliente.get("/api/panel", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, (
        f"***el panel agronomico se conserva***: {respuesta.status_code} {respuesta.text[:200]}"
    )
    datos = respuesta.json()

    # ***1 · la metrica no existe*** -ni cero, ni subtotal-.
    assert la_metrica(datos, "gastos") is None, (
        f"***la metrica de gastos NO puede venir***: {la_metrica(datos, 'gastos')}"
    )

    # ***2 · y la cifra no esta en NINGUNA parte del texto***: *ni en un total, ni en una cobertura, ni en un
    # aviso, ni en un enlace. Se mira la respuesta entera.*
    for forma in (EL_IMPORTE, "123,45", "123450"):
        assert forma not in respuesta.text, (
            f"***el importe «{forma}» no puede viajar***: {respuesta.text[:400]}"
        )
    # ***Y ni la unidad del dinero***: *las parejas que se confunden -`kg` con `EUR`- **tampoco viajan** sin la
    # capacidad, porque son una pista. La revision lo pide con esas palabras: «ni en respuestas alternativas».*
    assert "EUR" not in respuesta.text, (
        f"***ni la unidad del dinero***: {respuesta.text[:400]}"
    )

    # ***3 · y el panel agronomico se conserva***: *la cuenta de consulta sigue viendo su finca.*
    assert la_metrica(datos, "superficie") is not None, "la superficie tiene que seguir"
    assert la_metrica(datos, "trabajo") is not None, "y el trabajo"


def test_y_el_saldo_contesta_403_con_la_misma_cuenta(cliente, cuenta, db_sesion):
    """***El control de que la capacidad esta de verdad apagada.***

    *Sin esto, la prueba de arriba podria pasar porque la capacidad nunca llego a apagarse -o porque la puerta
    del panel no mira nada-.*
    """
    _sin_capacidad(db_sesion, cuenta, "puede_ver_lo_economico")

    el_saldo = cliente.get(f"/api/contactos/1/saldo", headers=cuenta["cabeceras"])
    # *404 si el contacto 1 no existe en esta finca; lo que **no** puede es dar 200.*
    assert el_saldo.status_code in (403, 404), (
        f"***el saldo tiene que negarse***: {el_saldo.status_code} {el_saldo.text[:200]}"
    )


def test_otra_explotacion_no_ve_este_dinero(cliente, cuenta, campana, crear_cuenta):
    """*Y el aislamiento por explotacion, que es la otra mitad.*"""
    un_gasto(cliente, cuenta, campana)
    la_otra = crear_cuenta("la-otra-finca@ejemplo.test")

    suyo = cliente.get("/api/panel", headers=la_otra["cabeceras"])
    assert suyo.status_code == 200, suyo.text
    assert EL_IMPORTE not in suyo.text and "123,45" not in suyo.text, (
        f"***el gasto de la otra finca no puede salir***: {suyo.text[:300]}"
    )
