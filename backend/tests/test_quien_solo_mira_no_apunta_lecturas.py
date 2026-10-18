"""**Quien solo mira no apunta lecturas** (CRM-07 #8, 17/10/2026).

### ***El defecto que esto cierra***

`app/deps.py` tenia desde el 13/10 dos dependencias -`PuedeModificar` y `PuedeVerLoEconomico`- **con su 403
escrito**, y ***ninguna puerta de la maquinaria las usaba***. *O sea: la pantalla le escondia el boton a una
cuenta de solo lectura, y **la puerta dejaba pasar igual**.*

***Y el propio docstring de `deps.py` dice por que eso no vale***:

    «***POR QUE ESTO NO ES UN BOTON ESCONDIDO.*** … *«ocultar un boton no [es] autorizacion»* …
    ***la puerta [es quien] autoriza***: se comprueba aqui, en el servidor, y ***da igual que se llegue
    por la pantalla, por la URL [o poniendo el] identificador a mano***.»

### ***Y por que esto no puede romper nada***

**Las capacidades nacen en `True`** -lo dice `accesos.py` y lo repite la prueba hermana-: *una cuenta que ya
existe **puede** modificar, asi que anadir la comprobacion **no le cambia la vida**.* **Lo unico que cambia
es que una cuenta a la que alguien le apague `puede_modificar` deje de poder escribir de verdad.**

### ***Lo que se prueba, y de la misma forma que la casa***

*Por **el identificador directo** -que es el caso que el encargo pide-, y mirando **la base**, no la
respuesta: una puerta que contesta 403 y escribe igual seria lo peor de los dos mundos.*
"""

from __future__ import annotations

from sqlalchemy import select

from app import models


def _sin_capacidad(db_sesion, cuenta, cual: str) -> None:
    """Le quita una capacidad a esa cuenta, en su acceso a la finca.

    *Igual que en `test_los_permisos_por_materia.py`: se hace en la base y no por una puerta a proposito,
    porque **hoy no hay pantalla para repartir capacidades** y esta prueba es del servidor.*
    """
    db_sesion.expire_all()
    acceso = db_sesion.scalar(
        select(models.AccesoAFinca).where(
            models.AccesoAFinca.usuario_id == cuenta["usuario_id"],
            models.AccesoAFinca.explotacion_id == cuenta["explotacion_id"],
        )
    )
    assert acceso is not None, "la cuenta tiene que tener su acceso a la finca"
    setattr(acceso, cual, False)
    db_sesion.commit()


def _una_maquina(cliente, cuenta, crear_parcela) -> dict:
    """Una maquina de la finca, para colgarle lecturas."""
    respuesta = cliente.post(
        "/api/maquinaria",
        headers=cuenta["cabeceras"],
        # ***Las cuatro que la puerta pide***: *`nombre` y `clase` no bastan -`propiedad` y
        # `disponibilidad` son preguntas obligatorias, y sin ellas la puerta contesta 422 con
        # ««» no es una de las respuestas que se pueden elegir». Se copian del ayudante del T14, que es
        # donde esta escrito como se crea una maquina.*
        json={
            "nombre": "Tractor de las lecturas",
            "clase": "tractor",
            "propiedad": "propia",
            "disponibilidad": "disponible",
        },
    )
    assert respuesta.status_code in (200, 201), respuesta.text
    return respuesta.json()


def _una_lectura(cliente, cuenta, maquina_id: int) -> dict:
    respuesta = cliente.post(
        f"/api/maquinaria/{maquina_id}/lecturas",
        headers=cuenta["cabeceras"],
        json={"fecha": "2026-01-01", "valor": "1000", "unidad": "horas"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# ---------------------------------------------------------------------------
# 1 · Con la capacidad puesta, todo sigue funcionando
# ---------------------------------------------------------------------------


def test_con_poder_modificar_las_lecturas_se_apuntan_corrigen_y_anulan(cliente, cuenta, crear_parcela):
    """***Lo primero: que con las capacidades de siempre no se rompa nada.***

    *Si esto fallara, no habria nada que probar: significaria que la comprobacion nueva deja fuera a quien
    tiene que poder.* **Y es el caso de todas las cuentas que ya existen** -las capacidades nacen en
    `True`-.
    """
    maquina = _una_maquina(cliente, cuenta, crear_parcela)
    lectura = _una_lectura(cliente, cuenta, maquina["id"])

    corregir = cliente.put(
        f"/api/maquinaria/{maquina['id']}/lecturas/{lectura['id']}",
        headers=cuenta["cabeceras"],
        json={"fecha": "2026-01-01", "valor": "1100", "unidad": "horas"},
    )
    assert corregir.status_code == 200, corregir.text

    anular = cliente.post(
        f"/api/maquinaria/{maquina['id']}/lecturas/{lectura['id']}/anular",
        headers=cuenta["cabeceras"],
        json={"motivo": "Me equivoque de maquina"},
    )
    assert anular.status_code == 200, anular.text


# ---------------------------------------------------------------------------
# 2 · Sin poder modificar: 403, y NADA escrito
# ---------------------------------------------------------------------------


def test_sin_poder_modificar_no_se_apunta_ninguna_lectura(cliente, cuenta, db_sesion, crear_parcela):
    """***403, y la base sin una fila mas.***

    *Se comprueba **por identificador directo** -el caso que el encargo pide-, y se mira **la base**: la
    respuesta podria mentir; lo que hay guardado, no.*
    """
    maquina = _una_maquina(cliente, cuenta, crear_parcela)
    antes = len(list(db_sesion.scalars(select(models.LecturaDeContador))))

    _sin_capacidad(db_sesion, cuenta, "puede_modificar")

    respuesta = cliente.post(
        f"/api/maquinaria/{maquina['id']}/lecturas",
        headers=cuenta["cabeceras"],
        json={"fecha": "2026-01-01", "valor": "1000", "unidad": "horas"},
    )
    assert respuesta.status_code == 403, f"tiene que dar 403 y da {respuesta.status_code}: {respuesta.text}"

    db_sesion.expire_all()
    despues = len(list(db_sesion.scalars(select(models.LecturaDeContador))))
    assert despues == antes, "***una puerta que contesta 403 y escribe seria lo peor de los dos mundos***"


def test_sin_poder_modificar_no_se_corrige_ni_se_anula(cliente, cuenta, db_sesion, crear_parcela):
    """***Y lo mismo para corregir y anular.***

    *Corregir cambia el acumulado del cuenta-horas y anular lo hace bajar: **las dos son escribir**, aunque
    una se llame «corregir» y la otra «anular» -que suena a deshacer, y no lo es: deja una lectura tachada
    que sigue en el cuaderno-.*
    """
    maquina = _una_maquina(cliente, cuenta, crear_parcela)
    lectura = _una_lectura(cliente, cuenta, maquina["id"])

    _sin_capacidad(db_sesion, cuenta, "puede_modificar")

    corregir = cliente.put(
        f"/api/maquinaria/{maquina['id']}/lecturas/{lectura['id']}",
        headers=cuenta["cabeceras"],
        json={"fecha": "2026-01-01", "valor": "9999", "unidad": "horas"},
    )
    assert corregir.status_code == 403, f"corregir tiene que dar 403 y da {corregir.status_code}"

    anular = cliente.post(
        f"/api/maquinaria/{maquina['id']}/lecturas/{lectura['id']}/anular",
        headers=cuenta["cabeceras"],
        json={"motivo": "No deberia poder"},
    )
    assert anular.status_code == 403, f"anular tiene que dar 403 y da {anular.status_code}"

    # ***Y la lectura sigue como estaba***: ni corregida ni anulada.
    db_sesion.expire_all()
    la_suya = db_sesion.scalar(
        select(models.LecturaDeContador).where(models.LecturaDeContador.id == lectura["id"])
    )
    assert la_suya is not None
    assert str(la_suya.valor) != "9999", "***no se ha corregido***"
    assert not la_suya.anulado, "***y no se ha anulado***"


# ---------------------------------------------------------------------------
# 3 · Y la capacidad de ver el dinero NO tiene que ver con esto
# ---------------------------------------------------------------------------


def test_solo_mira_el_dinero_no_impide_apuntar_una_lectura(cliente, cuenta, db_sesion, crear_parcela):
    """***Las dos capacidades son distintas, y hay que probarlo.***

    *Hay cuentas -un ayudante- que **si pueden trabajar** y **no deben ver las cuentas de la finca**. Si el
    permiso de las lecturas se hubiera puesto con la comprobacion del dinero, ese ayudante no podria apuntar
    sus horas, y eso seria un defecto nuevo tapando el viejo.*
    """
    maquina = _una_maquina(cliente, cuenta, crear_parcela)

    _sin_capacidad(db_sesion, cuenta, "puede_ver_lo_economico")

    respuesta = cliente.post(
        f"/api/maquinaria/{maquina['id']}/lecturas",
        headers=cuenta["cabeceras"],
        json={"fecha": "2026-01-01", "valor": "1000", "unidad": "horas"},
    )
    assert respuesta.status_code == 201, (
        f"***sin ver el dinero se sigue apuntando: da {respuesta.status_code}: {respuesta.text}***"
    )
