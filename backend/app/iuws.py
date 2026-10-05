"""El Interfaz Único de Web Services (IUWS) de FEGA: el protocolo oficial de volcado.

Es el formato por el que un cuaderno comercial (esto) habla con el CUE de la Junta. Todo lo
que hay aquí sale del **Anexo VI. Interfaz Único Común v3.11.4** (FEGA)
y del **Anexo X. Procedimiento de autorización CUE** (`12_FEGA_ANEXO_X_...pdf`). Nada está
puesto a ojo.

## Lo que SÍ se puede hacer sin nada más, y está hecho

* **Las direcciones de todos los métodos**, tal y como las documenta el anexo.
* **El catálogo de mensajes** del interfaz: los 19 códigos de error con su significado
  oficial, para poder decirle al agricultor (y a quien integre) qué ha pasado en castellano.
* **La lectura de la respuesta**: `resultado.codigoResultado` (OK / PARCIAL / FALLO) y el
  detalle por actividad.
* **El identificador de cada actividad** (`IdAjena`), que **lo genera la herramienta** y que
  es la pieza que hace que una carga se pueda corregir en vez de duplicarse.
* **El sobre** del mensaje: `CUADERNO` con `CodigoSIEX`, `CAExplotacion`, `IdTitular`,
  `UnidadGestora` y `ActividadesExplotacion`, con los nombres del esquema oficial (ojo:
  `IdTitular`, no el `IDTitular` del ejemplo del anexo).
* **El contenido mínimo del CUE, campo por campo**, con la numeración del documento técnico
  SIEX v3.11 (ver `iuws_contenido.py`).

## Lo que NO se puede hacer, y por qué se dice en vez de inventarlo

El formato exacto de `ActividadesExplotacion` está en el descriptor y el esquema JSON
oficiales v3.11.4, conservados en `data/iuws_fuentes/`. Falta cotejar cada campo del
cuaderno con ellos y completar el mapeo y los códigos de catálogo antes de enviar datos.

Así que este módulo **no fabrica ese JSON**. Lo que hace es:

1. Exportar todo lo que sí está documentado, en el orden de campos del contenido mínimo.
2. Decir exactamente **qué falta** para poder generar el JSON del descriptor, y a quién
   pedírselo (`QUE_FALTA`, `GET /api/iuws/estado`).

Un volcado inventado no es un volcado: lo rechazaría el propio interfaz con
`ERROR_VALIDAR_CAMPO` (código 5), y habría quedado escrito en el repositorio un formato que
nadie ha comprobado. Es el mismo criterio que con el listado de zonas vulnerables y con los
límites de nitrógeno.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Versiones. La del descriptor es la que hay que casar con el fichero de la Junta.
# --------------------------------------------------------------------------

# El Anexo VI v3.11.4 (19/11/2025) incorpora el descriptor y su esquema JSON.
# Las copias extraídas del documento oficial están en data/iuws_fuentes/.
VERSION_DESCRIPTOR_CUE = "3.11.4"

# Versión del documento de diseño del interfaz que se ha seguido.
VERSION_DOCUMENTO_INTERFAZ = "3.11.4"

# --------------------------------------------------------------------------
# Dónde está el interfaz
#
# El anexo pone `https://servidor:puerto/IUWS/api/...` porque es un documento para todas las
# comunidades. Las direcciones de verdad están en el Anexo X, que las lista comunidad por
# comunidad. Estas tres son las que salen de ahí.
# --------------------------------------------------------------------------

ENTORNO_INTEGRACION = "https://sga.entornointegracion.es"

BASES_POR_CCAA = {
    "Castilla y León": "https://servicios.ayg.jcyl.es",
}

# La consola del entorno de integración, donde se puede probar cada método a mano antes de
# escribir una línea de código. Sale del anexo, apartado «Servicio REST y Swagger».
SWAGGER_INTEGRACION = "https://sga.entornointegracion.es/IUWS/swagger-ui.html"

# Los catálogos oficiales (los códigos de producto, unidad, justificación…). Es el servicio
# del que se sacan, y hace falta para poder rellenar el descriptor.
CATALOGOS_SIEX = "https://www3.sede.fega.gob.es/bdcsixpor/catalogos"

# A quién se le pide el acceso, según el formulario de Castilla y León.
CONTACTOS = {
    "fega": "soporte-integracioncue@fega.es",
    "castilla_y_leon": "comercialcuecyl@jcyl.es",
}


# --------------------------------------------------------------------------
# Lo que se ha comprobado contra el interfaz DE VERDAD
#
# Esto no sale de ningún documento: se llamó al interfaz de Castilla y León, que está en
# producción, y esto es lo que contestó. Se apunta aquí porque es la única prueba de que el
# camino existe, y porque cambia una decisión del programa: la llamada de la versión **no
# necesita certificado**, así que se puede comprobar hoy, antes de tener nada.
#
# El método `version` es el único que el anexo declara «no securizado», y la realidad lo
# confirma: contesta 200 sin certificado.
# --------------------------------------------------------------------------

VERSION_OBSERVADA = "3.11.4"
FECHA_DE_LA_COMPROBACION = "2026-09"
ESPERA_SEGUNDOS = 15.0

# Se comprobó la ruta pública de versión en producción. Los métodos autenticados de la
# versión actual siguen pendientes de probar con certificado y alta reales.
COMPROBADO_CONTRA_EL_INTERFAZ = {
    "/IUWS/api/version": "200 — no está securizado, contesta la versión 3.11.4",
    "/IUWS/api/comunicacion/{app}": (
        "con el certificado del titular puesto (desde Windows, que es donde vive su clave privada) "
        "el servidor sí habla, y lo que contesta es «Dominio del certificado no registrado en el "
        "sistema» (código 2): el certificado vale, pero la explotación no está dada de alta. Sin "
        "certificado NO se llega ni a hablar: el servidor corta en el saludo TLS "
        "(«sslv3 alert handshake failure»)"
    ),
}

# Comprobado el 27/09/2026 con `scripts/probar_iuws.py` (que hace dos llamadas por dirección y
# **ningún dato del agricultor**). Lo que se saca de aquí es lo que decide cómo se presenta el
# cuaderno, así que conviene tenerlo escrito:
#
#   · **El entorno de integración no pide certificado para hablar**: contesta 200 a la llamada del
#     token, y lo que dice es que no estamos autorizados (código 2, «No Autorizado»). Es decir: allí
#     el corte está en la aplicación, y se puede probar todo el flujo sin certificado hasta el final.
#   · **Producción sí lo pide para hablar**: sin certificado ni siquiera hay conexión. Eso significa
#     que presentar de verdad exige un certificado de cliente **de verdad**, y que no vale con
#     mandarlo en una cabecera.
#
# Y el 27/09/2026 se fue un paso más allá, con el certificado de David y desde este ordenador
# (`scripts/probar_iuws_con_certificado.ps1`): el servidor **sí habla** con él y la respuesta del
# interfaz es «Dominio del certificado no registrado en el sistema». O sea: el certificado se lee, la
# conexión se establece y lo que falta es que la explotación esté dada de alta en el sistema. **No se
# ha presentado nada** y no se va a decir que sí.
#
# **Y se volvió a comprobar el 28/09/2026**, por si el alta había llegado entre medias: las cuatro
# respuestas de abajo salieron **iguales** (versión 3.11.4 en las dos direcciones, «Dominio del
# certificado no registrado en el sistema» en producción y «No Autorizado» en integración) y la firma
# del NIF se volvió a verificar con la clave pública del certificado (`True`). O sea: **sigue sin
# haber nada presentado y lo único que falta sigue siendo el alta**. La fecha que se enseña en
# pantalla es esta, la de la última comprobación.
COMPROBADO_EL = "2026-09-28"
RESPUESTAS_OBSERVADAS = {
    "entorno_integracion": {
        "version": "200 · «Versión del descriptor : 3.11.4» (no está securizado)",
        "token_sin_certificado": (
            "200 · {\"resultado\":{\"codigoResultado\":\"FALLO\","
            "\"detalleImportacion\":[{\"codigo\":2,\"descripcion\":\"No Autorizado\"}]}}"
        ),
        # Con el certificado de David puesto, la respuesta es la misma: su certificado es de
        # producción y en el entorno de integración de FEGA no está dado de alta nadie. Se apunta
        # para que nadie pierda una tarde probando allí con su certificado de verdad.
        "token_con_el_certificado_del_titular": (
            "200 · {\"resultado\":{\"codigoResultado\":\"FALLO\","
            "\"detalleImportacion\":[{\"codigo\":2,\"descripcion\":\"No Autorizado\"}]}}"
        ),
    },
    "produccion_castilla_y_leon": {
        "version": "200 · {\"version\": \"3.11.4\"} (no está securizado)",
        "token_sin_certificado": (
            "sin respuesta: el saludo TLS se corta («sslv3 alert handshake failure»). El servidor "
            "exige certificado de cliente para hablar"
        ),
        # **Esto es lo que contesta de verdad, con el certificado de David, desde este ordenador.**
        # Se consiguió con `scripts/probar_iuws_con_certificado.ps1`, que usa el certificado **donde
        # vive** (el almacén de Windows): su clave privada está marcada como no exportable, así que
        # desde Python no se puede usar, pero Windows firma el saludo TLS por dentro y el programa
        # nunca ve la clave. Lleva el certificado, sí, pero **no se ha presentado nada**: el
        # interfaz dice que el dominio del certificado no está registrado, o sea que falta el alta.
        "token_con_el_certificado_del_titular": (
            "200 · {\"resultado\":{\"codigoResultado\":\"FALLO\",\"detalleImportacion\":"
            "[{\"codigo\":2,\"descripcion\":\"Dominio del certificado no registrado en el sistema\"}]}}"
        ),
    },
}

# El entorno de integración sí publica la ruta actual con `/api/`. El 404 previo era de
# la ruta obsoleta sin ese segmento, no una señal de falta de alta.
COMPROBADO_ENTORNO_INTEGRACION = {
    "/IUWS/api/version": "200 — contesta la versión del descriptor 3.11.4",
    "/IUWS/version": "404 — ruta antigua, sin /api/",
}

# Las direcciones que el programa puede probar por su cuenta cuando la configurada no contesta.
# Salen del Anexo X (una por comunidad) y de lo comprobado arriba.
BASES_CONOCIDAS = tuple(BASES_POR_CCAA.values())

# El formato del JSON de actividades que espera el interfaz. Solo se puede generar con el
# descriptor v3.11.4 mapeado; se nombra aquí para rechazar cualquier otra
# cosa antes de mandarla.
FORMATO_DESCRIPTOR = "descriptor-v3.11.4"


# --------------------------------------------------------------------------
# Las direcciones de cada método
#
# Están como funciones y no como cadenas montadas a mano para que los parámetros que
# van separados por guión bajo (`{explotación}_{CIF}`) no se puedan juntar mal.
# Ese detalle es el que hace que la llamada falle con «credenciales» en vez de con un error
# que diga qué pasa.
# --------------------------------------------------------------------------


def url_version(base: str) -> str:
    """`/IUWS/api/version`. No está securizado: sirve para saber con quién se habla."""
    return f"{_limpia(base)}/IUWS/api/version"


def url_comunicacion(base: str, nombre_app: str) -> str:
    """`/IUWS/api/comunicacion/{nombreAppCue}`. Devuelve el token JWT.

    El nombre del cuaderno comercial va en la dirección y no en el certificado: el anexo
    explica que no se puede usar el campo O del certificado para eso.
    """
    return f"{_limpia(base)}/IUWS/api/comunicacion/{_sin_barras(nombre_app)}"


def url_exportar_rea(base: str, nif_titular: str, cif_gestora: str | None = None) -> str:
    """`/IUWS/exportarREA/{NIF titular}_{CIF Gestora}`."""
    return f"{_limpia(base)}/IUWS/api/exportarREA/{_tres(nif_titular, cif_gestora)}"


def url_exportar_cue(base: str, explotacion: str, cif_gestora: str | None = None) -> str:
    """`/IUWS/api/exportar/{Nº explotación}_{CIF Gestora}`."""
    return f"{_limpia(base)}/IUWS/api/exportar/{_tres(explotacion, cif_gestora)}"


def url_crear(base: str) -> str:
    """`/IUWS/crear/`. Es un POST con el JSON del cuaderno."""
    return f"{_limpia(base)}/IUWS/api/crear/"


def url_comprobar_estado(base: str, id_peticion: str | int) -> str:
    """`/IUWS/comprobarEstado/{Id Petición}`."""
    return f"{_limpia(base)}/IUWS/api/comprobarEstado/{id_peticion}"


def _limpia(base: str) -> str:
    return (base or "").rstrip("/")


def _sin_barras(valor: str) -> str:
    """El nombre de la aplicación va en la dirección, así que no puede llevar barras."""
    return re.sub(r"[^A-Za-z0-9._-]", "", (valor or "").strip())


def _tres(*valores) -> str:
    """Une los parámetros con guión bajo, saltándose los que no estén.

    El orden importa y lo fija el anexo: explotación, cuaderno, CIF de la gestora. Lo que no
    se manda no deja un hueco vacío: `A__B` no es lo mismo que `A_B` para el interfaz.
    """
    return "_".join(str(valor) for valor in valores if valor not in (None, ""))


# --------------------------------------------------------------------------
# Los mensajes del interfaz, tal y como los publica el anexo
# --------------------------------------------------------------------------

# Resultados generales de una petición.
RESULTADOS = {
    "OK": "Ha ido bien.",
    "PARCIAL": "Algunas actividades no se han podido cargar; el resto sí.",
    "FALLO": "No se ha podido cargar ninguna actividad.",
    "ERROR": "El fichero o las credenciales no valen.",
    "ERROR_VALIDAR_ESTRUCTURA": "Los datos enviados no se ajustan al formato esperado.",
    "ERROR_VALIDAR_CREDENCIALES": "La llamada no está autorizada.",
    "ERROR_VALIDAR_OGESTOR": "No se ha podido validar el organismo pagador.",
}

# Los códigos del detalle, uno por uno. El número y el significado son los del anexo
# (Anexo 1, «Mensajes de detalle por cada actividad procesada»), más los tres generales.
MENSAJES = {
    1: ("ERROR_VALIDAR_ESTRUCTURA", "Los datos enviados no se ajustan al formato esperado."),
    2: ("ERROR_VALIDAR_CREDENCIALES", "La llamada no está autorizada."),
    3: ("EXITO", "Actividad grabada correctamente."),
    4: (
        "ERROR_EXP_NO_ASIGNADA",
        "La entidad no tiene asignada la explotación que se quiere cargar.",
    ),
    5: ("ERROR_VALIDAR_CAMPO", "Algún campo no cumple con los valores que se espera."),
    6: (
        "ERROR_VALIDAR_MAQUINARIA",
        "El número de inscripción de la maquinaria no se encuentra en ROMA.",
    ),
    7: ("ERROR_VALIDAR_ASESOR", "El código del asesor no se encuentra en ROPO."),
    8: (
        "ERROR_VALIDAR_TITULAR_EXPLOTACION",
        "El titular que manda el cuaderno no coincide con el titular del REA.",
    ),
    9: ("ERROR_VALIDAR_FALTAN_CAMPOS", "Faltan campos necesarios para la operación."),
    10: (
        "ERROR_VALIDAR_DGC_EXPLOTACION",
        "La superficie es mayor que la declarada en SIGPAC, o la DGC no existe.",
    ),
    11: ("ERROR_VALIDAR_CONTACTE_ADMINISTRADOR", "Error genérico: hay que contactar con el administrador."),
    12: (
        "ERROR_VALIDAR_REFERENCIA_SIGPAC1",
        "La codificación de los recintos SIGPAC no llega bien: alguno es nulo.",
    ),
    13: (
        "ERROR_VALIDAR_DCU_EXPLOTACION",
        "No se ha podido encontrar un cultivo con los datos que se mandan.",
    ),
    14: (
        "ERROR_VALIDAR_CERRADA",
        "La actividad que se intenta editar está cerrada o ya se envió a SIEX.",
    ),
    15: (
        "ERROR_VALIDAR_EGESTORA",
        "En el envío hay expedientes de varias empresas habilitadas: hay que hacer un envío por cada una.",
    ),
    16: ("ERROR_VALIDAR_OGESTOR", "No se ha podido validar el organismo pagador."),
    17: ("ERROR_NO_MODIFICAR", "No se puede modificar la actividad: está cerrada."),
    18: ("ERROR_NO_BORRAR", "No se puede borrar la actividad: está cerrada."),
    19: ("ERROR_IDCUE", "El identificador de cuaderno que se ha pasado es incorrecto."),
}


def mensaje_de_codigo(codigo) -> str:
    """Qué significa un código del detalle, en castellano. Sin código conocido, se dice."""
    try:
        numero = int(codigo)
    except (TypeError, ValueError):
        return "El interfaz ha contestado algo que no sabemos interpretar."
    if numero not in MENSAJES:
        return f"El interfaz ha contestado con el código {numero}, que no está en el manual."
    nombre, descripcion = MENSAJES[numero]
    return f"{descripcion} ({nombre})"


# --------------------------------------------------------------------------
# Leer la respuesta
# --------------------------------------------------------------------------


@dataclass
class Respuesta:
    """Lo que ha contestado el interfaz, ya en limpio.

    El formato lo fija el anexo: `resultado.codigoResultado` y `resultado.detalleImportacion`
    (una lista de `{codigo, descripcion}`). Para `comprobarEstado` puede venir además el
    `CUADERNO` cargado, y el `detalleOperacion` con el estado del proceso.
    """

    codigo: str = ""
    mensaje: str = ""
    detalles: list[dict] = field(default_factory=list)
    cuaderno: dict | None = None
    operacion: dict | None = None
    crudo: dict | None = None
    id_peticion: int | None = None

    @property
    def esta_ok(self) -> bool:
        return self.codigo == "OK"

    @property
    def es_parcial(self) -> bool:
        return self.codigo == "PARCIAL"

    @property
    def es_fallo(self) -> bool:
        return self.codigo in ("FALLO", "ERROR") or self.codigo.startswith("ERROR_")

    def actividades_fallidas(self) -> list[dict]:
        """Las actividades que no se han cargado, con el motivo ya escrito.

        Es lo que se le enseña al agricultor cuando una carga sale a medias: no «error 5»,
        sino qué actividad y por qué.
        """
        return [
            {**detalle, "explicacion": mensaje_de_codigo(detalle.get("codigo"))}
            for detalle in self.detalles
            if str(detalle.get("codigo")) not in ("3", "OK")
        ]


def leer_respuesta(cuerpo) -> Respuesta:
    """Interpreta lo que devuelve el interfaz, venga como venga.

    Decisión: **no se lanza una excepción por una respuesta rara.** Si el interfaz contesta
    algo que no se entiende, se devuelve una `Respuesta` con el código vacío y el texto
    crudo guardado, para poder enseñarlo tal cual. Reventar aquí dejaría al agricultor sin
    saber qué ha pasado y sin poder mandarlo a soporte.
    """
    if isinstance(cuerpo, str):
        try:
            cuerpo = json.loads(cuerpo)
        except (TypeError, ValueError):
            return Respuesta(crudo={"texto": cuerpo}, mensaje=cuerpo[:500])

    if not isinstance(cuerpo, dict):
        return Respuesta(crudo={"texto": str(cuerpo)})

    resultado = cuerpo.get("resultado") if isinstance(cuerpo.get("resultado"), dict) else cuerpo
    codigo = str(resultado.get("codigoResultado") or resultado.get("codigo") or "")

    detalles = resultado.get("detalleImportacion") or []
    if isinstance(detalles, dict):
        detalles = [detalles]
    detalles = [d for d in detalles if isinstance(d, dict)]

    operacion = resultado.get("detalleOperacion")
    if not isinstance(operacion, dict):
        operacion = None

    cuaderno = resultado.get("CUADERNO") or resultado.get("cuaderno")
    if not isinstance(cuaderno, dict):
        cuaderno = None

    # En la llamada a `crear`, el identificador de la petición viene en el `codigo` del
    # detalle cuando el resultado es OK. Es lo que después se le pasa a `comprobarEstado`.
    id_peticion = None
    if codigo == "OK":
        for detalle in detalles:
            try:
                id_peticion = int(detalle.get("codigo"))
                break
            except (TypeError, ValueError):
                continue

    mensaje = RESULTADOS.get(codigo, "")
    if not mensaje and detalles:
        mensaje = str(detalles[0].get("descripcion") or "")

    return Respuesta(
        codigo=codigo,
        mensaje=mensaje,
        detalles=detalles,
        cuaderno=cuaderno,
        operacion=operacion,
        crudo=cuerpo,
        id_peticion=id_peticion,
    )


# --------------------------------------------------------------------------
# El identificador de cada actividad: lo genera ESTA herramienta
#
# El anexo es explícito: «en el JSON se solicita un identificador único por cada actividad,
# generado por la herramienta que envía los datos al CUE», y sirve para tres cosas:
#
#   1. Saber qué actividad ha fallado en la carga.
#   2. **Corregirla**: si el identificador ya se ha mandado antes, el CUE entiende que es una
#      edición y actualiza, en vez de crear una actividad nueva.
#   3. Junto al campo «Borrar», borrarla.
#
# Decisión: el identificador se **calcula** a partir de la finca, el tipo de registro y el
# identificador interno, en vez de guardarse en una columna. Así es único, estable y no hay
# que migrar nada. Y **no se puede cambiar nunca**: si cambiara, el CUE de la Junta dejaría
# de reconocer lo ya cargado y lo duplicaría todo. Por eso la función está aquí, con este
# comentario, y hay un test que comprueba que sigue dando lo mismo.
# --------------------------------------------------------------------------

SIGLAS = {
    "tratamiento": "T",
    "fertilizacion": "F",
    "labor": "L",
    "venta": "V",
    "analitica": "A",
    "plan": "P",
    "instalacion": "I",
    "equipo": "Q",
    "parcela": "D",
    "medida": "M",
}

PREFIJO = "CD"


def id_ajeno(nif: str, tipo: str, id_interno: int) -> str:
    """El identificador **de la aplicación** para una actividad, para poder rastrearla.

    Formato: `CD-{NIF}-{sigla}-{id}`, por ejemplo `CD-70922320A-T-14`. Lleva el NIF porque
    las tablas de autorización del interfaz van por titular, y la sigla porque así el
    identificador dice de qué clase de actividad es sin tener que mirar la base de datos.

    **Ojo, y esto se descubrió tarde:** este **no** es el identificador que va en el campo
    `IdAjena…` del JSON oficial. Ese campo es un **número** (`integer`, hasta 10 dígitos), así
    que un texto como este lo rechaza el esquema; para el interfaz se manda el número de la
    fila, ver `iuws_mapeo.identificador_oficial`. Este `CD-…` se sigue usando para lo que sí
    sirve: que una persona pueda seguir una actividad en el cuaderno y en el volcado del
    contenido mínimo.
    """
    sigla = SIGLAS.get(tipo, "X")
    limpio = re.sub(r"[^A-Za-z0-9]", "", (nif or "").upper())
    return f"{PREFIJO}-{limpio}-{sigla}-{id_interno}"


# --------------------------------------------------------------------------
# El sobre del mensaje
# --------------------------------------------------------------------------


def sobre_del_cuaderno(
    *,
    codigo_siex: str | None,
    ca: str,
    nif_titular: str,
    unidad_gestora: str | None = None,
    codigo_rea: str | None = None,
    id_cuaderno: int | None = None,
    actividades: dict | None = None,
    datos_explotacion: dict | None = None,
) -> dict:
    """Arma el sobre `CUADERNO` con los nombres de campo **del descriptor oficial**.

    Los nombres son los del esquema JSON oficial v3.11.4 (`CodigoSIEX`, `CAExplotacion`,
    `IdTitular`, `UnidadGestora`, `CodigoRea`, `IdCuaderno`, `DatosExplotacion`,
    `ActividadesExplotacion`), que es el contrato que se valida antes de mandar.

    **Ojo con `IdTitular`, y por qué está escrito así:** el ejemplo del Anexo VI lo llama
    `IDTitular`, con las dos primeras letras en mayúscula, y el esquema oficial lo llama
    `IdTitular`. El que manda es el esquema: con `IDTitular` el sobre **no valida nunca**,
    porque el campo obligatorio `IdTitular` no estaría. Se descubrió cotejando el sobre con el
    esquema, y hay un test que lo fija para que nadie lo «arregle» de vuelta copiando el
    ejemplo.

    `CAExplotacion` es el código de comunidad autónoma: el 13 es Castilla y León.
    """
    sobre = {
        "CodigoSIEX": codigo_siex,
        "CAExplotacion": ca,
        "IdTitular": nif_titular,
    }
    if unidad_gestora:
        # El CIF de la empresa habilitada. Va también aquí porque el anexo pide que el
        # descriptor del cuaderno lleve la entidad habilitada cuando la herramienta da
        # servicio a varias.
        sobre["UnidadGestora"] = unidad_gestora
    if codigo_rea:
        sobre["CodigoRea"] = codigo_rea
    if id_cuaderno:
        sobre["IdCuaderno"] = id_cuaderno
    if datos_explotacion is not None:
        sobre["DatosExplotacion"] = datos_explotacion
    if actividades is not None:
        sobre["ActividadesExplotacion"] = actividades
    return sobre


CODIGOS_CA = {
    "Castilla y León": "13",
}


# --------------------------------------------------------------------------
# Qué falta para poder generar el volcado del descriptor
# --------------------------------------------------------------------------

# Los ocho datos que pide el formulario de acceso de Castilla y León, uno por uno. Están
# aquí para poder decirlos tal cual, porque son lo que bloquea la integración de verdad.
CAMPOS_DEL_FORMULARIO_CYL = (
    "Nombre de la Empresa desarrolladora",
    "NIF de la empresa desarrolladora",
    "Nombre del software comercial",
    "CN del certificado de dominio con el que se comunicará con el Servicio Web",
    "Nombre de la persona de contacto",
    "Teléfono de la persona de contacto",
    "Email de la persona de contacto",
    "URL página Web Empresa Desarrolladora",
)


@dataclass(frozen=True)
class LoQueFalta:
    """Una cosa que hace falta para poder integrarse, y de quién depende."""

    clave: str
    que: str
    por_que: str
    quien: str
    bloquea: bool


QUE_FALTA: tuple[LoQueFalta, ...] = (
    LoQueFalta(
        clave="descriptor",
        que="El mapeo de los bloques del cuaderno al descriptor oficial v3.11.4",
        por_que=(
            "El descriptor oficial y su esquema JSON ya están en data/iuws_fuentes, y el sobre "
            "del mensaje ya usa sus nombres de campo. Falta traducir cada bloque de "
            "actividades a los campos del descriptor, y el esquema no admite campos vacíos."
        ),
        quien="quien desarrolla la aplicación",
        bloquea=True,
    ),
    LoQueFalta(
        clave="catalogos",
        que="Los valores de los catálogos oficiales (servicio de catálogos de SIEX)",
        por_que=(
            "Los códigos no se inventan: producto, unidad de medida, justificación, estado "
            "fenológico y materia activa se mandan como código de catálogo. El portal público "
            "publica la ESTRUCTURA de los catálogos sin certificado, pero los datos de cada "
            "tabla están detrás de un captcha."
        ),
        quien="FEGA",
        bloquea=True,
    ),
    LoQueFalta(
        clave="nombre_comercial",
        que="El nombre comercial del software",
        por_que=(
            "Va en la dirección de la llamada de comunicación y tiene que estar registrado "
            "en el interfaz. Sin él no hay token, y sin token no hay ninguna llamada."
        ),
        quien="David: hay que rellenarlo en el formulario de CyL",
        bloquea=True,
    ),
    LoQueFalta(
        clave="dominio",
        que="El dominio y el CN del certificado de dominio",
        por_que=(
            "El interfaz autoriza por la terna (dominio del certificado, NIF de la empresa "
            "habilitada, cuaderno comercial). Sin el dominio registrado, la llamada se "
            "rechaza con ERROR_VALIDAR_CREDENCIALES. Lo que contesta hoy, comprobado con el "
            "certificado puesto el 28/09/2026, es: «Dominio del certificado no registrado en "
            "el sistema». Si sale ese mensaje, no es un fallo del programa ni del "
            "certificado: es que falta este alta."
        ),
        quien="David: hace falta el servidor y el certificado de dominio",
        bloquea=True,
    ),
    LoQueFalta(
        clave="certificado",
        que="El certificado de dominio (sello de entidad) con autenticación de cliente",
        por_que=(
            "Se necesita para obtener el token JWT en la llamada de comunicación. Las "
            "llamadas posteriores usan ese token y no vuelven a enviar el certificado."
        ),
        quien="David: se pide a una autoridad de certificación",
        bloquea=True,
    ),
    LoQueFalta(
        clave="empresa_habilitada",
        que="El CIF de la empresa habilitada y la autorización del titular",
        por_que=(
            "El interfaz solo deja cargar cuadernos de explotaciones autorizadas. El titular "
            "tiene que autorizar a la entidad habilitada (Anexo VIII/IX de SIEX)."
        ),
        quien="David y cada agricultor",
        bloquea=True,
    ),
    LoQueFalta(
        clave="alta_entorno",
        que="El alta en el entorno de integración",
        por_que=(
            "Hay que mandar el formulario de solicitud a los dos correos, firmado "
            "electrónicamente. Es lo que da usuario y acceso para poder probar."
        ),
        quien=f"David: {CONTACTOS['fega']} y {CONTACTOS['castilla_y_leon']}",
        bloquea=True,
    ),
    LoQueFalta(
        clave="codigo_siex",
        que="El código SIEX de cada explotación",
        por_que=(
            "Va en el sobre del mensaje. Se rellena en los datos de la finca, y si falta, el "
            "interfaz no sabe de qué explotación se le habla."
        ),
        quien="Cada agricultor, en «Mi finca»",
        bloquea=True,
    ),
)


def por_que_falta(clave: str) -> str:
    """Por qué hace falta una cosa de la lista, ya redactado. `""` si esa clave no existe.

    Lo usan el cliente y la pantalla para decir lo mismo con las mismas palabras: si el motivo
    se escribiera dos veces, con el tiempo dirían cosas distintas.
    """
    for falta in QUE_FALTA:
        if falta.clave == clave:
            return f"{falta.que}: {falta.por_que} Se lo tienes que pedir a {falta.quien}."
    return ""


def lo_que_falta(*, descriptor: bool, configurado: dict | None = None) -> list[LoQueFalta]:
    """La lista de lo que falta, quitando lo que ya esté resuelto.

    Se calcula en vez de escribirse a mano para que la pantalla diga siempre la verdad: en
    cuanto se cargue el descriptor, deja de aparecer en la lista.

    El mapeo del descriptor y los catálogos son tareas distintas. Tener el esquema JSON no
    demuestra que los códigos necesarios ya estén disponibles.
    """
    configurado = configurado or {}
    pendientes: list[LoQueFalta] = []
    for falta in QUE_FALTA:
        if falta.clave == "descriptor" and descriptor:
            continue
        if configurado.get(falta.clave):
            continue
        pendientes.append(falta)
    return pendientes


# --------------------------------------------------------------------------
# Configuración, por variables de entorno
#
# Decisión: NADA de esto va en el repositorio. El nombre comercial y el CIF identifican a la
# empresa, y el certificado es una clave privada: eso no se escribe en un fichero que se
# sube a git, ni siquiera en un fichero de ejemplo.
# --------------------------------------------------------------------------


def configuracion() -> dict:
    """Lo que hay configurado para hablar con el interfaz.

    `conectado` es lo que de verdad importa: mientras falte cualquier pieza, la aplicación
    **no intenta** llamar al interfaz. Hacer una llamada sin certificado solo sirve para que
    el agricultor vea un error que no puede arreglar.
    """
    base_integracion = os.environ.get("CUEDIGITAL_IUWS_BASE") or ENTORNO_INTEGRACION
    nombre_app = (os.environ.get("CUEDIGITAL_IUWS_APP") or "").strip()
    cif = (os.environ.get("CUEDIGITAL_IUWS_CIF") or "").strip()
    dominio = (os.environ.get("CUEDIGITAL_IUWS_DOMINIO") or "").strip()
    certificado = (os.environ.get("CUEDIGITAL_IUWS_CERTIFICADO") or "").strip()
    # El alta en el entorno de integración: aquí se apunta el usuario o la referencia que
    # devuelve la Junta cuando concede el acceso. Es la prueba de que el formulario se mandó
    # y se contestó, y sin ella no se puede llamar a nada.
    alta = (os.environ.get("CUEDIGITAL_IUWS_ALTA") or "").strip()

    puesto = {
        # Todavía no existe un mapeo completo de los catálogos de SIEX. No se puede
        # declarar conectado solo por haber recibido el descriptor.
        "catalogos": False,
        "nombre_comercial": bool(nombre_app),
        "dominio": bool(dominio),
        "certificado": bool(certificado),
        "empresa_habilitada": bool(cif),
        "alta_entorno": bool(alta),
    }
    return {
        "base": base_integracion,
        "nombre_comercial": nombre_app,
        "cif_empresa_habilitada": cif,
        "dominio": dominio,
        "certificado_configurado": bool(certificado),
        "alta_entorno": alta,
        "url_version": url_version(base_integracion),
        "url_comunicacion": url_comunicacion(base_integracion, nombre_app) if nombre_app else None,
        "url_crear": url_crear(base_integracion),
        "swagger": SWAGGER_INTEGRACION,
        "catalogos": CATALOGOS_SIEX,
        "version_descriptor": VERSION_DESCRIPTOR_CUE,
        "version_documento": VERSION_DOCUMENTO_INTERFAZ,
        "puesto": puesto,
        "conectado": all(puesto.values()) and descriptor_cargado(),
        "contactos": dict(CONTACTOS),
        "campos_del_formulario": list(CAMPOS_DEL_FORMULARIO_CYL),
    }


# --------------------------------------------------------------------------
# El descriptor, que se carga de un fichero que rellena el usuario
#
# Mismo patrón que el listado de zonas vulnerables: el fichero existe vacío, la aplicación
# funciona sin él, y mientras no esté se dice que falta en vez de suponer.
# --------------------------------------------------------------------------

_RUTA_DESCRIPTOR = Path(__file__).resolve().parents[2] / "data" / "iuws_descriptor_cue.json"
RUTA_ESQUEMA_OFICIAL = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "iuws_fuentes"
    / "BdcSix-DS-DisenoCUE_3.11.4.schema.json"
)

_descriptor: dict | None = None


def cargar_descriptor(ruta: Path | str | None = None) -> dict | None:
    """Lee el descriptor del cuaderno, si está.

    Se espera un JSON con `version` y `bloques`. Si el fichero no existe, o está vacío, o no
    se entiende, se devuelve `None`: la aplicación sigue funcionando y dice que falta, que es
    lo que tiene que pasar.
    """
    global _descriptor
    ruta = Path(ruta) if ruta else _RUTA_DESCRIPTOR
    if not ruta.exists():
        _descriptor = None
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        _descriptor = None
        return None
    if not isinstance(datos, dict) or not datos.get("bloques"):
        _descriptor = None
        return None
    _descriptor = datos
    return _descriptor


def descriptor_cargado() -> bool:
    if _descriptor is None:
        cargar_descriptor()
    return bool(_descriptor)


def descriptor() -> dict | None:
    if _descriptor is None:
        cargar_descriptor()
    return _descriptor


def olvidar_descriptor() -> None:
    """Vacía el descriptor cargado.

    Existe para los tests: uno que carga un descriptor de prueba no puede dejarlo puesto para
    el siguiente, o el orden de ejecución cambiaría los resultados. Un test que depende del
    orden no vale nada. Mismo motivo que en `catalogos.olvidar_zonas_vulnerables`.
    """
    global _descriptor
    _descriptor = None


# --------------------------------------------------------------------------
# El paquete que se manda
# --------------------------------------------------------------------------


def _id_de_cuaderno(campana) -> int | None:
    """El identificador del cuaderno, **como número**.

    El esquema oficial declara `IdCuaderno` de tipo `integer`, y la aplicación lo estaba
    mandando como texto (copiando el ejemplo del anexo, donde aparece entre comillas), así que
    el sobre no podía validar. Si el año no se puede convertir en número, se devuelve `None` y
    el campo no se manda: una cadena vacía tampoco cumpliría el esquema.
    """
    anio = getattr(campana, "anio", None)
    try:
        return int(anio)
    except (TypeError, ValueError):
        return None


def paquete(
    *,
    explotacion,
    campana,
    contenido: dict,
    config: dict | None = None,
) -> dict:
    """El sobre con el contenido, listo para revisar.

    Decisión importante: esto **no es** el JSON de importación del descriptor, y se dice en
    el propio paquete (`formato`, `aviso`). El sobre exterior ya lleva los nombres de campo
    **del esquema oficial** y por eso se puede validar contra él; lo que no está mapeado son
    las actividades, que van en el orden de campos del contenido mínimo del CUE, y faltan los
    códigos de los catálogos. Fabricar el resto sin ellos sería inventarse un formato y unos
    códigos, y el interfaz lo rechazaría.
    """
    config = config or configuracion()
    ca = CODIGOS_CA.get(getattr(explotacion, "ccaa", ""), "")
    sobre = sobre_del_cuaderno(
        codigo_siex=getattr(explotacion, "codigo_siex", None),
        ca=ca,
        nif_titular=getattr(explotacion, "nif", ""),
        unidad_gestora=config.get("cif_empresa_habilitada") or None,
        id_cuaderno=_id_de_cuaderno(campana),
        datos_explotacion=contenido.get("datos_explotacion") or None,
        actividades=contenido.get("actividades") or None,
    )
    return {
        "CUADERNO": [sobre],
        "formato": "sobre-documentado-con-contenido-minimo-siex",
        "aviso": (
            "El sobre (CodigoSIEX, CAExplotacion, IdTitular, UnidadGestora, IdCuaderno, "
            "DatosExplotacion, ActividadesExplotacion) sigue los nombres del descriptor "
            "oficial v3.11.4. Las actividades van en el orden de campos del contenido mínimo "
            f"del CUE, NO en el formato del descriptor v{VERSION_DESCRIPTOR_CUE}: falta el "
            "mapeo de cada bloque y faltan los códigos de los catálogos."
        ),
        "version_descriptor_esperada": VERSION_DESCRIPTOR_CUE,
        "descriptor_cargado": descriptor_cargado(),
        "generado_en": dt.datetime.now().isoformat(timespec="seconds"),
        "faltan": [
            {"clave": falta.clave, "que": falta.que, "quien": falta.quien}
            for falta in lo_que_falta(descriptor=descriptor_cargado(), configurado=config.get("puesto"))
        ],
    }
