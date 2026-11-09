"""CUE Digital — cuaderno de campo.

Arranque de la aplicación. El orden de los routers importa poco, pero el de las
decisiones sí: aquí se crean las tablas al arrancar (cómodo para el agricultor y
para los tests) y se documenta que en producción esto lo hará una migración.
"""

from __future__ import annotations

import mimetypes
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import catalogos, observabilidad
from .database import TextoQueNoCabe, crear_tablas
from .routers import (
    almacen_api,
    analiticas_api,
    # **La bandeja documental (T08, S10, 06/10/2026).** Va en su sitio por orden alfabético, como las
    # demás: lo que llega y hay que revisar.
    bandeja_api,
    borradores_api,
    # **La búsqueda global (07/10/2026).** Una caja en la cabecera que busca en lo del agricultor.
    buscar_api,
    contactos_api,
    cuenta,
    # **La ficha de la compra** (S11, 09/10/2026): facturado, recibido, pagado y pendiente en un sitio.
    compras_api,
    cuaderno,
    cuaderno_cyl_api,
    documentos_api,
    explotacion,
    extractos_api,
    facturas_api,
    # **La normativa** (T-normativa, 07/10/2026): las reglas de la matriz, tal cual.
    normativa_api,
    fincas_api,
    firmas_api,
    gastos_api,
    trabajos_api,
    interfaz,
    iuws_api,
    maestros,
    mapa,
    maquinaria_api,
    medidas_api,
    # **La observabilidad** (09/11/2026): el aviso de pantalla y el resumen de lo medido. Va
    # detrás de `medidas_api` por orden alfabético, y antes de montar `/` como todos.
    observabilidad_api,
    parcelas,
    planes_api,
    registros,
    semillas_api,
    ventas_api,
    versiones_api,
    # **Las próximas acciones** (Entrega 3, 13/10/2026): lo que hay que hacer, cruzando fichas.
    tareas_api,
    fusion_api,
    terceros_api,
    panel_api,
    pac_api,
    # **Las dos puertas del armazón nuevo** (`IMP-1`, 05/11/2026): la app que se sirve en `/nuevo/`
    # no lee la pantalla vieja y pide sus datos aquí.
    nuevo_api,
)

# Los tipos de fichero se declaran a mano A PROPÓSITO.
#
# En Windows, Python saca los tipos MIME del registro del sistema, y allí un .js
# puede aparecer como "text/plain". Un navegador que recibe un módulo JavaScript con
# tipo "text/plain" lo RECHAZA, la interfaz no arranca y el fallo no dice nada útil.
# Ha pasado tantas veces que merece la pena no depender del sistema operativo.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("image/svg+xml", ".svg")

# La interfaz son ficheros sueltos (HTML, CSS y JavaScript) que sirve el propio
# programa. No hay compilación a propósito: el servidor donde se instale esto no
# tiene por qué tener Node, y en un móvil con mala cobertura una página ligera se
# abre y una aplicación de medio megabyte, no.
RUTA_WEB = Path(__file__).resolve().parents[1] / "web"

DESCRIPCION = """
Cuaderno de campo digital.

Está centrado en lo que la ley obliga a registrar:

* **Productos aplicados**: el registro electrónico es obligatorio desde el 01/01/2027.
* **Abonos**: obligatorio desde el 01/01/2026.

El programa calcula solo lo que el agricultor no debe calcular (días de espera,
abono puro, cantidades totales) y no le deja apuntar algo que la ley no permite,
explicándole en castellano qué tiene que hacer.
"""


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # **Poner la base al día puede fallar, y cuando falla hay que decir por qué.** Desde el 02/10/2026
    # `crear_tablas` reconstruye tablas (para que ciertas columnas puedan decir «no se sabe») y **no lo hace
    # sin una copia válida**: si no se puede copiar, levanta un error y el programa no arranca. Una traza de
    # Python en la consola no le dice nada a quien lo ha puesto en marcha, así que se cuenta en cristiano
    # —qué ha pasado y qué hacer— y después se deja subir el error, porque seguir sin base no tiene sentido.
    try:
        crear_tablas()
    except RuntimeError as fallo:
        # **El consejo tiene que servir para el motor que se está usando** (02/10/2026). Aquí se decía
        # siempre «cierra otra ventana del cuaderno o un visor de SQLite», y eso no le dice nada a quien
        # tiene el programa sobre PostgreSQL, que es la base de producción: allí no hay ningún fichero
        # abierto que cerrar, y lo que hay que mirar es el servidor y sus permisos.
        from .database import url_base_datos

        if url_base_datos().startswith("sqlite"):
            arreglo = (
                "Cierra cualquier otro programa que esté usando la base (otra ventana del cuaderno, un "
                "visor de SQLite) y vuelve a empezar."
            )
        else:
            arreglo = (
                "Comprueba que el servidor de la base de datos está en marcha, que la dirección y las "
                "credenciales son las correctas y que esa cuenta puede crear tablas e índices, y vuelve "
                "a empezar."
            )
        print(
            "\nNo se ha podido preparar la base de datos:\n"
            f"  {fallo}\n"
            f"El programa no ha arrancado y la base se ha quedado como estaba. {arreglo}\n"
        )
        raise
    # **Quién puede entrar en cada finca** (ronda 89): las cuentas que ya existían antes de que hubiera
    # varias cuentas por finca se quedan con el acceso a la suya. Sin esto, al actualizar el programa
    # nadie podría entrar: el vale dice una finca y no habría permiso para ella.
    from . import accesos
    from .database import SessionLocal

    with SessionLocal() as sesion:
        puestos = accesos.asegurar_accesos(sesion)
    if puestos:
        print(f"Cuentas a las que se les ha puesto el acceso a su finca: {puestos}")
    # Se intenta cargar el listado oficial de zonas vulnerables. Si no está, el
    # programa sigue funcionando y preguntará al agricultor en vez de suponer.
    catalogos.cargar_zonas_vulnerables()
    yield


app = FastAPI(
    title="CUE Digital",
    description=DESCRIPCION,
    version="0.1.0",
    lifespan=ciclo_de_vida,
)


# **Un texto que no cabe en su columna es un dato mal mandado, no un fallo del programa** (02/10/2026).
#
# La comprobación vive en `database.TextoQueNoCabe` (justo antes de escribir, para que no se pueda
# olvidar en ningún sitio nuevo). Aquí se traduce a **422 con su frase**, que es lo que el contrato pide
# para un dato que no vale — y, sobre todo, **lo que evita el bucle**: `app.js` reintenta los 5xx para
# siempre, así que un 500 aquí dejaría a la cola del móvil dando vueltas con el mismo apunte.
@app.exception_handler(TextoQueNoCabe)
async def _texto_que_no_cabe(_peticion: Request, fallo: TextoQueNoCabe) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(fallo)})

# **Qué orígenes pueden llamar a la API desde otro sitio** (09/11/2026).
#
# La pantalla y la API pueden vivir en sitios distintos: el front estático en GitHub Pages
# llamando al servidor propio. Entonces el navegador manda el `Origin` del front y la API tiene
# que autorizarlo, o la pantalla se queda sin datos aunque el servidor esté bien.
#
# Los de desarrollo siguen valiendo. Los de fuera **se piden por variable** y no se abren a
# cualquiera: es una API con datos de agricultores. `*` se ignora a propósito (con `*` y
# credenciales, cualquier página podría leer un vale abierto). Lo comprueba
# `tests/test_origenes_de_la_pantalla.py`.
ORIGENES_DE_DESARROLLO = ("http://localhost:5173", "http://127.0.0.1:5173")


def origenes_permitidos() -> list[str]:
    """Los orígenes de desarrollo más los que se pidan en `CUEDIGITAL_CORS_ORIGENES`."""
    crudo = os.environ.get("CUEDIGITAL_CORS_ORIGENES", "")
    extra = [
        origen.strip()
        for origen in crudo.split(",")
        if origen.strip() and origen.strip() != "*"
    ]
    # Sin repetir y en orden: la lista se enseña en los registros y así se lee limpia.
    vistos: list[str] = []
    for origen in [*ORIGENES_DE_DESARROLLO, *extra]:
        if origen not in vistos:
            vistos.append(origen)
    return vistos


app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes_permitidos(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# **La observabilidad mide cada petición y no cambia ninguna** (09/11/2026).
#
# Es un middleware ASGI y no un `@app.middleware("http")` a propósito: así se ve **el mensaje**
# de la respuesta (`http.response.start`), que trae el código de estado de verdad, y no hay que
# envolver la respuesta en nada. No se toca el cuerpo, no se tocan las cabeceras y no se cambia
# el código: solo se lee lo que ya pasa.
#
# Dos reglas que se cumplen aquí y no son un detalle:
#
#  1. **Nunca lanza hacia la aplicación.** La llamada a la observabilidad va en un `try/except`
#     propio dentro del `finally`: si el registro revienta, la petición termina igual.
#  2. **Nunca se pierde un error.** Si la petición se va con una excepción (un 500 de verdad), se
#     apunta con su tipo y su mensaje corto antes de dejarla subir. **La excepción se vuelve a
#     lanzar**: aquí no se tapa nada; solo se mira.
class _MedirLaPeticion:
    """Mide una petición: duración, código de estado y, si es un 5xx, su error.

    Se mide por la **plantilla** de la ruta (sin identificadores), que es lo que hace que
    `/api/parcelas/17` y `/api/parcelas/2031` cuenten en la misma fila. Lo que se guarda es
    solo eso: método, plantilla, código y milisegundos. Ni el cuerpo, ni el vale, ni la IP.
    """

    def __init__(self, aplicacion) -> None:
        self.aplicacion = aplicacion

    async def __call__(self, alcance, recibir, enviar) -> None:
        if alcance.get("type") != "http":
            # Las conexiones de WebSocket y el ciclo de vida no son peticiones: no se miden.
            await self.aplicacion(alcance, recibir, enviar)
            return

        comienzo = time.perf_counter()
        codigo = 500
        fallo: BaseException | None = None

        async def enviar_midiendo(mensaje) -> None:
            nonlocal codigo
            if mensaje.get("type") == "http.response.start":
                codigo = int(mensaje.get("status", 500))
            # Se manda el mensaje **tal cual**: ni se copia ni se envuelve.
            await enviar(mensaje)

        try:
            await self.aplicacion(alcance, recibir, enviar_midiendo)
        except BaseException as error:  # noqa: BLE001 — se apunta y se deja subir
            fallo = error
            raise
        finally:
            try:
                observabilidad.registrar_peticion(
                    alcance.get("method", ""),
                    alcance.get("path", "/"),
                    codigo,
                    (time.perf_counter() - comienzo) * 1000.0,
                    tipo=type(fallo).__name__ if fallo is not None else None,
                    mensaje=str(fallo) if fallo is not None else None,
                )
            except Exception:  # noqa: BLE001 — una métrica rota no puede tumbar la petición
                pass


app.add_middleware(_MedirLaPeticion)

app.include_router(cuenta.router)
# **Las próximas acciones** (Entrega 3, 13/10/2026): lo que hay que hacer, cruzando fichas.
app.include_router(tareas_api.router)
app.include_router(fusion_api.router)
app.include_router(terceros_api.router)
# **La normativa**, con las demas puertas de consulta (07/10/2026).
app.include_router(normativa_api.router)
# Las fincas de una cuenta y quién entra en ellas (varias cuentas en la misma finca): va justo detrás de
# la cuenta, porque es lo primero que hace falta después de entrar.
app.include_router(fincas_api.router)
app.include_router(explotacion.router)
app.include_router(parcelas.router)
# El mapa: elegir la tierra tocándola. Va después de parcelas porque usa sus mismas reglas de
# alta, y antes de los maestros porque es lo primero que ve quien no sabe sus códigos.
app.include_router(mapa.router)
app.include_router(cuaderno_cyl_api.router)
app.include_router(facturas_api.router)
app.include_router(compras_api.router)
app.include_router(maestros.router)
# El almacén (T09): el albarán que llega, los lotes y el libro de movimientos. Va detrás de las
# facturas porque engancha la factura de un albarán, y detrás de los maestros porque el artículo se
# engancha a la ficha del producto o del abono.
app.include_router(almacen_api.router)
app.include_router(registros.router)
app.include_router(cuaderno.router)
app.include_router(interfaz.router)
app.include_router(borradores_api.router)
app.include_router(firmas_api.router)
app.include_router(planes_api.router)
app.include_router(analiticas_api.router)
app.include_router(medidas_api.router)
app.include_router(ventas_api.router)
app.include_router(documentos_api.router)
app.include_router(iuws_api.router)
# Las versiones del recinto (T05): qué era cada tierra en cada campaña, quién lo dijo y la
# importación repetible de un lote de recintos. Va detrás de parcelas porque las versiones cuelgan
# de las tierras, y detrás de explotacion porque cuelgan de la campaña.
app.include_router(versiones_api.router)
# Las semillas, las etiquetas y las siembras (T10). Va detrás del almacén —la semilla **es** un
# artículo del almacén y lo que se siembra sale por su puerta de salidas— y detrás de parcelas, porque
# una siembra se hace en una tierra.
app.include_router(semillas_api.router)
app.include_router(semillas_api.router_siembras)
# Las personas y las empresas (T11, 03/10/2026): la ficha de un contacto y los enlaces con los
# nombres que ya están escritos en las facturas, los albaranes, las ventas y los análisis. Va al final
# porque no depende de nadie: lo que hace es **apuntar a** lo que ya existe.
app.include_router(contactos_api.router)
# **La maquinaria de la finca (T14, E8, 03/10/2026):** el inventario de máquinas con sus cinco
# obligaciones separadas, sus inspecciones y sus averías. Va detrás de los maestros porque enlaza con
# los equipos de echar producto del cuaderno (hoja 1.3) y detrás de los papeles, porque una inspección
# puede apuntar al papel que la demuestra.
app.include_router(maquinaria_api.router)
# **Las cuentas de la explotación (T13, E7, 05/10/2026).** El router de los gastos, las inversiones,
# los repartos, los pagos y las ayudas. Va detrás del de las ventas porque comparte su vocabulario de
# formas de pago (`ventas.FORMAS_DE_COBRO`) y porque el orden de los routers no decide nada: cada uno
# tiene su prefijo (`/api/gastos`).
app.include_router(gastos_api.router)
# Los extractos de banco y la conciliación (T20, 05/10/2026): subir un fichero que el agricultor ha
# descargado de su banca, verlo antes de apuntarlo y cuadrarlo con las facturas y los cobros. Va detrás
# de ventas_api porque concilia contra sus facturas emitidas y sus cobros. **No se conecta ningún
# banco**: solo se lee el fichero que se sube.
app.include_router(extractos_api.router)
# **Los trabajos por tierra (T15, E9, 05/10/2026).** El previsto y el hecho, la historia de una tierra y
# el estado derivado. Va detrás de los gastos porque un trabajo puede costar dinero y detrás de la
# maquinaria porque dice con qué máquina se hizo.
app.include_router(trabajos_api.router)
# **La bandeja documental (T08, S10, 06/10/2026).** Lo que llega y hay que revisar: subir el papel tal y
# como llega, leerlo, confirmar lo que el agricultor acepta y decir con qué va. Va detrás de
# `documentos_api` porque el papel que guarda es el mismo (`documentos_anexos`) y usa sus puertas para
# el alta y para el fichero, y detrás de `extractos_api` porque un papel se puede enlazar con un
# movimiento conciliado.
app.include_router(bandeja_api.router)
# **La búsqueda global (07/10/2026, del encargo del rediseño).** Una caja en la cabecera para preguntar
# «¿dónde está esto?» sin saber antes en qué pantalla está. Va la última porque no depende de nadie: busca
# en lo que ya está guardado. Hoy busca en las tierras (por nombre y por referencia oficial); los gastos,
# los papeles, las personas y las máquinas son la vuelta siguiente (está dicho en su fichero).
app.include_router(buscar_api.router)

# **El panel** (CRM-11, 17/10/2026): *las metricas, con su fuente y su
# cobertura. Un numero que no puede decir de donde sale no se ensena.*
app.include_router(panel_api.router)

# **La preparacion de la PAC** (CRM-09): *el paquete por recinto, con lo que falta dicho.*
app.include_router(pac_api.router)

# **Las dos puertas del armazón nuevo** (`IMP-1`, 05/11/2026): la app que se sirve en `/nuevo/` no lee
# la pantalla vieja y pide sus datos aquí. Va antes del montaje de `/` porque un montaje en la raíz se
# come cualquier ruta registrada después (ver el aviso del final del fichero).
app.include_router(nuevo_api.router)

# **La observabilidad** (09/11/2026): el aviso de pantalla del móvil y el resumen de lo medido.
# Va aquí, antes del montaje de `/` y como todos los demás: un montaje en la raíz se come
# cualquier ruta registrada después.
app.include_router(observabilidad_api.router)


@app.get("/health", tags=["sistema"])
def health() -> dict:
    return {
        "estado": "ok",
        "zonas_vulnerables_cargadas": catalogos.hay_datos_zonas_vulnerables(),
    }


@app.get("/api", tags=["sistema"])
def raiz() -> dict:
    return {
        "nombre": "CUE Digital",
        "que_es": "El cuaderno de campo, en el móvil y en castellano.",
        "documentacion": "/docs",
        "empieza_por": "/api/cuenta/registro",
    }


# IMPORTANTE: esto va al FINAL. Un montaje en "/" se come cualquier ruta que se
# registre después, así que si algún día se añade un router debajo de esta línea,
# dejará de responder sin dar ningún error.
if RUTA_WEB.is_dir():
    app.mount("/", StaticFiles(directory=str(RUTA_WEB), html=True), name="web")
