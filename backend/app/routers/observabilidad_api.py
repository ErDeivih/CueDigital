"""**Las dos puertas de la observabilidad** (09/11/2026).

La medida vive en `app/observabilidad.py`, que es un módulo puro: no sabe de FastAPI ni de
SQLAlchemy y se puede probar sin levantar el servidor. Aquí solo se ponen las dos puertas:

* `POST /api/observabilidad/pantalla` — el aviso que manda la pantalla del móvil al cambiar de
  vista. **Contesta siempre 204**, incluso con un cuerpo roto o vacío: es un aviso de un
  agricultor en una parcela, y un aviso que no se entiende no puede convertirse en un error que
  él no ha provocado. El cuerpo se lee como mucho hasta `MAXIMO_DEL_CUERPO_DEL_AVISO` bytes, se
  valida y, si no vale, se descarta. No se guarda el cuerpo en ningún sitio.
* `GET /api/observabilidad/resumen` — lo medido, para quien mantiene el programa. **No es una
  puerta para el agricultor y no lleva datos suyos**: contadores, plantillas de ruta y el
  embudo. Se protege con la cabecera `X-Observabilidad`, comparada **en tiempo constante**
  (`hmac.compare_digest`) con `CUEDIGITAL_OBSERVABILIDAD_TOKEN`.

POR QUÉ 404 Y NO 401/403 SIN TOKEN CONFIGURADO
==============================================

Sin `CUEDIGITAL_OBSERVABILIDAD_TOKEN` la ruta **no existe** (404), que es lo que pide el
contrato: que no esté ahí para nadie, ni siquiera para quien sepa la dirección. Poner un 401
sería decir «aquí hay algo, pero no entras», y eso ya es información. Con el token configurado
y la cabecera mal, la respuesta es 403: la puerta existe y se ha llamado sin llave.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from .. import observabilidad
from ..deps import Db

router = APIRouter(prefix="/api/observabilidad", tags=["sistema"])


async def _leer_el_cuerpo_del_aviso(peticion: Request) -> bytes | None:
    """Lee el aviso **hasta un tope**, sin cargar en memoria un cuerpo enorme.

    Un aviso de pantalla son cuarenta bytes. Si llega algo más grande que el tope, no es un
    aviso: se descarta sin leerlo entero. Se hace trozo a trozo a propósito: `await
    peticion.body()` se traga el cuerpo entero antes de que nadie pueda decir «esto sobra».
    """
    try:
        trozos: list[bytes] = []
        total = 0
        async for trozo in peticion.stream():
            total += len(trozo)
            if total > observabilidad.MAXIMO_DEL_CUERPO_DEL_AVISO:
                return None
            trozos.append(trozo)
        return b"".join(trozos)
    except Exception:  # noqa: BLE001 — el aviso no puede romper nada
        return None


def _la_pantalla_del_cuerpo(cuerpo: bytes | None) -> str | None:
    """Saca la clave de pantalla del aviso, o `None` si lo que ha llegado no vale.

    Se aceptan dos formas, porque el móvil puede mandar cualquiera de las dos: un objeto
    `{"pantalla": "hoy"}` o la clave suelta (`"hoy"`). Todo lo demás —un número, una lista, un
    texto con espacios, basura— se descarta. **No se guarda el cuerpo**: solo la clave.
    """
    if not cuerpo:
        return None
    try:
        datos = json.loads(cuerpo.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    try:
        if isinstance(datos, dict):
            return observabilidad.clave_de_pantalla(datos.get("pantalla"))
        return observabilidad.clave_de_pantalla(datos)
    except Exception:  # noqa: BLE001
        return None


@router.post("/pantalla", status_code=204, response_class=Response)
async def anotar_la_pantalla(peticion: Request) -> Response:
    """Apunta que se ha abierto una pantalla. **Siempre 204, y nunca un 5xx.**

    Es el aviso que manda `web/nuevo/app.js` con `navigator.sendBeacon`. No pide sesión: el
    aviso se manda al cambiar de pantalla, y puede llegar sin vale (la pantalla de entrar
    también es una pantalla del programa). Lo que se guarda es **solo** el nombre de la vista:
    ni la finca, ni el vale, ni un dato del cuaderno.

    Todo va envuelto: un cuerpo roto, un JSON que no es un objeto, una clave inventada o un
    fallo del propio registro se quedan en nada y el móvil recibe su 204 igual. El motivo es el
    de siempre: **la observabilidad no puede romper la aplicación**.
    """
    try:
        cuerpo = await _leer_el_cuerpo_del_aviso(peticion)
        clave = _la_pantalla_del_cuerpo(cuerpo)
        if clave is not None:
            observabilidad.registrar_pantalla(clave)
    except Exception:  # noqa: BLE001 — el aviso no puede contestar un 5xx
        pass
    return Response(status_code=204)


@router.get("/resumen")
def el_resumen(peticion: Request, db: Db) -> JSONResponse:
    """Lo medido en este proceso: errores, uso por pantalla, rutas y embudo.

    **404 si no hay token configurado** (la herramienta no existe), **403 si la cabecera falta
    o no coincide**, 200 si coincide. La comparación es en tiempo constante.

    El resumen de memoria y el embudo van juntos porque es lo que se lee de una vez, pero se
    calculan por separado: el primero no toca la base de datos y el segundo la consulta. Si la
    consulta del embudo fallara, se devuelve lo demás con la etapa en «no se sabe» (lo resuelve
    `observabilidad.embudo`), nunca un cero inventado.
    """
    if observabilidad.token_configurado() is None:
        raise HTTPException(status_code=404, detail="No hay nada que mirar aquí.")
    cabecera = peticion.headers.get(observabilidad.CABECERA_DEL_RESUMEN)
    if not observabilidad.token_es_valido(cabecera):
        raise HTTPException(status_code=403, detail="Esa cabecera no vale.")
    try:
        datos = observabilidad.resumen()
        datos["embudo"] = observabilidad.embudo(db)
        return JSONResponse(datos)
    except Exception:  # noqa: BLE001
        # Es una herramienta interna: si no puede preparar el resumen, se dice. Lo que **no**
        # puede pasar es que un fallo de aquí se lleve por delante la aplicación: la aplicación
        # no depende de esta puerta para nada.
        return JSONResponse(
            status_code=500,
            content={"detail": "No se ha podido preparar el resumen de lo medido."},
        )
