"""CUE Digital — cuaderno de campo.

Arranque de la aplicación. El orden de los routers importa poco, pero el de las
decisiones sí: aquí se crean las tablas al arrancar (cómodo para el agricultor y
para los tests) y se documenta que en producción esto lo hará una migración.
"""

from __future__ import annotations

import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import catalogos
from .database import TextoQueNoCabe, crear_tablas
from .routers import (
    almacen_api,
    analiticas_api,
    borradores_api,
    contactos_api,
    cuenta,
    cuaderno,
    cuaderno_cyl_api,
    documentos_api,
    explotacion,
    facturas_api,
    fincas_api,
    firmas_api,
    gastos_api,
    interfaz,
    iuws_api,
    maestros,
    mapa,
    maquinaria_api,
    medidas_api,
    parcelas,
    planes_api,
    registros,
    semillas_api,
    ventas_api,
    versiones_api,
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

# En desarrollo, la interfaz corre en otro puerto. En producción va detrás del mismo
# dominio, así que esto se puede quitar sin más.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cuenta.router)
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
