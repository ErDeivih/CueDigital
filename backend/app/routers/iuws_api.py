"""El volcado oficial a la Junta (IUWS): estado, contenido y prueba de conexión.

Este router **no tiene pantalla de agricultor**: quien lo usa es quien hace la integración
(una vez, para dejar el sistema conectado) o el técnico que comprueba si ya está conectado.
Por eso los textos de aquí van en el idioma de la integración —«interfaz», «credenciales»,
«descriptor»— y no en el del pueblo: son los nombres oficiales, y cambiarlos por paráfrasis
haría imposible seguir el manual de FEGA. Está explicado en `textos.IUWS`.

Lo que hace, y por qué eso es todo lo que se puede hacer hoy:

1. **`/api/iuws/estado`** — dice la verdad de la situación: qué está configurado, qué falta,
   quién tiene que darlo y a qué correo se pide. Es lo primero que hay que mirar.
2. **`/api/iuws/contenido`** — el contenido mínimo del CUE campo por campo, con su número de
   campo del documento técnico y sus bloques. Es lo que se puede cotejar con el papel.
3. **`/api/iuws/paquete`** — el sobre documentado con ese contenido dentro, con el
   identificador ajeno de cada actividad, que es lo que permite corregir una carga en vez de
   duplicarla.
4. **`/api/iuws/version`** — prueba de conexión contra el interfaz. Se puede hacer **ya**, sin
   tener nada configurado, porque el método de versión es el único que el interfaz deja
   abierto. Solo llama cuando se le pide (`?llamar=1`): una pantalla que va pinchando al
   servidor de la Junta cada vez que se abre es molestar por molestar. Sin `llamar`, informa
   de lo que hay y de lo que se ha comprobado, y no toca la red. Cuando se le pide, prueba la
   dirección configurada y, si no responde, la de la comunidad. En la versión 3.11.4,
   el entorno de integración responde en `/IUWS/api/version`.
5. **`/api/iuws/comprobar-de-verdad`** — qué métodos se han llamado de verdad y qué contestó
   cada uno, en las dos direcciones. Es la prueba de que el camino existe.
6. **`/api/iuws/leer-respuesta`** — traduce lo que contesta el interfaz: convierte «código 5»
   en «Algún campo no cumple con los valores que se espera (ERROR_VALIDAR_CAMPO)». Sirve para
   pegarlo tal cual en un correo a soporte.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from .. import (
    catalogos_siex,
    iuws,
    iuws_cliente,
    iuws_contenido,
    iuws_descriptor,
    iuws_mapeo,
    models,
    textos,
)
from ..deps import Db, ExplotacionActual, obtener_de_la_explotacion

router = APIRouter(prefix="/api/iuws", tags=["volcado oficial (IUWS)"])


def _campana(db, explotacion, campana_id: int | None) -> models.Campana:
    if campana_id is not None:
        return obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion.id)
    campana = db.scalar(
        select(models.Campana)
        .where(models.Campana.explotacion_id == explotacion.id)
        .order_by(models.Campana.anio.desc())
        .limit(1)
    )
    if campana is None:
        raise HTTPException(status_code=404, detail="Todavía no hay ningún año creado.")
    return campana


@router.get("/estado")
def estado(explotacion: ExplotacionActual, db: Db) -> dict:
    """La verdad de la situación: qué hay, qué falta y quién lo tiene que dar.

    Se calcula cada vez y no se guarda, para que en cuanto se configure una pieza deje de
    aparecer como pendiente. Una pantalla de estado que miente es peor que no tenerla.
    """
    config = iuws.configuracion()
    cargado = iuws.descriptor_cargado()
    # El código SIEX de la finca es lo único de la lista que el agricultor puede resolver
    # solo, así que se comprueba de verdad en vez de darlo por hecho.
    tiene_codigo_siex = bool((explotacion.codigo_siex or "").strip())
    puesto = {**config["puesto"], "codigo_siex": tiene_codigo_siex}
    falta = iuws.lo_que_falta(descriptor=cargado, configurado=puesto)

    return {
        "textos": textos.IUWS,
        "conectado": all(puesto.values()) and cargado,
        "configurado": config["puesto"],
        "codigo_siex_puesto": tiene_codigo_siex,
        "descriptor_cargado": cargado,
        # La tabla de campos del descriptor oficial: qué pide cada campo y de qué catálogo
        # sale. Es **derivada** del Excel oficial, y se dice de dónde viene, para que nadie la
        # confunda con un documento oficial. Es lo que permite decir qué falta **con nombre y
        # apellidos** en vez de «faltan códigos».
        "descriptor": iuws_descriptor.resumen(),
        # El mapeo del bloque de tratamientos al formato oficial: qué se puede mandar ya, qué
        # espera a un catálogo de FEGA y qué falta porque el cuaderno no lo pregunta. Es la
        # diferencia entre tener que escribir a FEGA y tener que escribir una pantalla.
        "mapeo_del_tratamiento": iuws_mapeo.resumen_del_tratamiento(),
        # Y todos los bloques que ya están mapeados a mano, con el total delante y **los que
        # faltan por su nombre**: que tres estén hechos no puede parecer que están los dieciocho.
        "mapeo_de_los_bloques": iuws_mapeo.resumen_de_los_bloques_mapeados(),
        # El cruce con los catálogos que publica SIEX: para los que coinciden **exactamente** de
        # nombre, dice qué tabla es y si es pública. Los que no coinciden se quedan sin emparejar
        # y se dicen: emparejarlos por parecido sería inventar. Esto es lo que hay que pedirle a
        # FEGA, con nombre y apellidos.
        "catalogos_de_siex": catalogos_siex.resumen(),
        # El mapa del cuaderno ENTERO: qué pide la Junta en cada uno de los 18 bloques y con qué
        # catálogo. Sale de los dos documentos oficiales cada vez que se pregunta, así que no se
        # puede quedar viejo. Es la lista de la compra: los 19 catálogos que hacen falta para los
        # campos obligatorios, con la tabla de SIEX de los que ya se sabe cuál es.
        "mapa_del_cuaderno": iuws_mapeo.resumen_del_cuaderno(),
        "version_descriptor_esperada": iuws.VERSION_DESCRIPTOR_CUE,
        "version_documento": iuws.VERSION_DOCUMENTO_INTERFAZ,
        # Lo que contestó el interfaz de verdad cuando se llamó. Va aquí porque cambia una
        # decisión: la prueba de versión se puede hacer hoy, sin tener nada configurado.
        "version_observada": iuws.VERSION_OBSERVADA,
        "fecha_de_la_comprobacion": iuws.FECHA_DE_LA_COMPROBACION,
        "comprobado_contra_el_interfaz": dict(iuws.COMPROBADO_CONTRA_EL_INTERFAZ),
        "base": config["base"],
        "url_version": config["url_version"],
        "url_comunicacion": config["url_comunicacion"],
        "url_crear": config["url_crear"],
        "swagger": config["swagger"],
        "catalogos": config["catalogos"],
        "contactos": config["contactos"],
        "campos_del_formulario": config["campos_del_formulario"],
        "codigo_siex": explotacion.codigo_siex,
        "faltan": [
            {
                "clave": f.clave,
                "que": f.que,
                "por_que": f.por_que,
                "quien": f.quien,
                "bloquea": f.bloquea,
            }
            for f in falta
        ],
        "cuantas_faltan": len(falta),
        "resumen": textos.IUWS["resumen_sin_conectar" if not config["conectado"] else "resumen_conectado"],
    }


@router.get("/contenido")
def contenido_declarado(explotacion: ExplotacionActual) -> dict:
    """Los bloques del contenido mínimo y sus campos, con el número del documento técnico.

    Esto no lleva datos de nadie: es la declaración de qué se vuelca y con qué nombre, para
    poder cotejarlo con el Anexo II del documento técnico de SIEX sin tener que leer código.
    """
    return {
        "textos": textos.IUWS,
        "bloques": iuws_contenido.resumen_de_bloques(),
        "campos_por_bloque": {
            clave: [
                {
                    "numero": campo.numero,
                    "nombre": campo.nombre,
                    "de": campo.de,
                    "tipo": campo.tipo,
                    "catalogo": campo.catalogo,
                    "obligatorio": campo.obligatorio,
                }
                for campo in campos
            ]
            for clave, (_nombre, _nivel, campos) in iuws_contenido.BLOQUES.items()
        },
        "parametros_del_suelo": [
            {"numero": numero, "nombre": nombre, "clave": clave}
            for numero, nombre, clave in iuws_contenido.PARAMETROS_SUELO_NUMERADOS
        ],
        "campos_de_catalogo": iuws_contenido.campos_de_catalogo(),
        "fuente": textos.IUWS["fuente_del_contenido"],
    }


@router.get("/paquete")
def paquete(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> dict:
    """El sobre documentado con el contenido del cuaderno dentro, listo para revisar."""
    campana = _campana(db, explotacion, campana_id)
    contenido = iuws_contenido.contenido_de_la_finca(db, explotacion=explotacion, campana=campana)
    armado = iuws.paquete(explotacion=explotacion, campana=campana, contenido=contenido)
    armado["resumen"] = contenido["resumen"]
    armado["catalogos_que_faltan"] = contenido["catalogos_que_faltan"]
    return armado


@router.get("/paquete.json")
def paquete_descargable(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> Response:
    """El mismo paquete, como fichero, para poder pasárselo a quien haga la integración."""
    import json

    campana = _campana(db, explotacion, campana_id)
    contenido = iuws_contenido.contenido_de_la_finca(db, explotacion=explotacion, campana=campana)
    armado = iuws.paquete(explotacion=explotacion, campana=campana, contenido=contenido)
    armado["resumen"] = contenido["resumen"]
    cuerpo = json.dumps(armado, ensure_ascii=False, indent=2, default=str)
    nombre = f"iuws_{campana.anio}.json"
    return Response(
        content=cuerpo.encode("utf-8"),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/version")
def probar_conexion(llamar: bool = False) -> dict:
    """Pregunta al interfaz con qué versión trabaja.

    `/IUWS/api/version` es el único método que **no está securizado**, así que se puede llamar sin
    certificado, sin nombre comercial y sin estar dado de alta. Comprobado contra el interfaz
    de Castilla y León: contesta `200 {"version": "3.11.4"}`. Por eso esta prueba se puede
    hacer **hoy**, y sirve para separar dos problemas que se confunden todo el tiempo: «no hay
    camino hasta la Junta» y «la Junta no me reconoce». Si contesta 200, el camino está bien y
    lo que falta son las credenciales.

    Decisión: **solo se llama cuando se pide** (`?llamar=1`). Sin eso se informa de lo que hay
    sin tocar la red, por dos motivos: una pantalla que pincha al servidor de la Junta cada vez
    que se abre molesta sin necesidad, y los tests de este proyecto no salen a internet.
    """
    config = iuws.configuracion()
    falta = iuws.lo_que_falta(descriptor=iuws.descriptor_cargado(), configurado=config["puesto"])
    comun = {
        "url": config["url_version"],
        "se_puede_probar_ya": True,
        "explica": textos.IUWS["version_se_puede_probar_sin_nada"],
        "version_observada": iuws.VERSION_OBSERVADA,
        "fecha_de_la_comprobacion": iuws.FECHA_DE_LA_COMPROBACION,
        "faltan": [{"clave": f.clave, "que": f.que, "quien": f.quien} for f in falta],
    }

    if not llamar:
        return {
            **comun,
            "probado": False,
            "conectado": False,
            "direcciones_conocidas": {
                "texto": textos.IUWS["direcciones_conocidas"],
                "por_comunidad": dict(iuws.BASES_POR_CCAA),
            },
            "mensaje": (
                textos.IUWS["version_se_puede_probar_sin_nada"]
                + " Pide la prueba con ?llamar=1 cuando quieras que se llame de verdad."
            ),
        }

    # Se prueba primero la dirección configurada y luego la de la comunidad si hace falta.
    prueba = iuws_cliente.comprobar_donde_contesta(config["base"])
    buena = prueba["buena"]
    return {
        **comun,
        "probado": True,
        "conectado": buena is not None,
        "codigo": buena["codigo"] if buena else (prueba["probadas"][-1]["codigo"] if prueba["probadas"] else None),
        "mensaje": prueba["mensaje"],
        "respuesta": f'{{"version": "{buena["version"]}"}}' if buena else "",
        "donde_contesta": buena["base"] if buena else None,
        "por_comunidad": dict(iuws.BASES_POR_CCAA),
        "probadas": [
            {
                "base": fila["base"],
                "url": fila["url"],
                "codigo": fila["codigo"],
                "version": fila["version"],
            }
            for fila in prueba["probadas"]
        ],
        "ojo_con_la_direccion_por_defecto": textos.IUWS["entorno_de_integracion_no_publica"],
    }


@router.get("/comprobar-de-verdad")
def lo_comprobado() -> dict:
    """Qué métodos del interfaz se han llamado de verdad y qué contestó cada uno.

    Existe porque es la única prueba de que el camino existe, y porque de ahí sale una decisión
    del programa: la ruta pública de versión v3.11.4 contesta en ambos entornos. El resto
    requiere una prueba autenticada para saber qué responde en esta versión.
    """
    return {
        "textos": textos.IUWS,
        "base": iuws.configuracion()["base"],
        "version_observada": iuws.VERSION_OBSERVADA,
        "fecha_de_la_comprobacion": iuws.FECHA_DE_LA_COMPROBACION,
        "explica": textos.IUWS["comprobado_de_verdad"],
        "donde": {
            "por_comunidad": dict(iuws.BASES_POR_CCAA),
            "entorno_de_integracion": iuws.ENTORNO_INTEGRACION,
            "ojo": textos.IUWS["entorno_de_integracion_no_publica"],
        },
        "metodos": [
            {"metodo": metodo, "que_contesto": que}
            for metodo, que in iuws.COMPROBADO_CONTRA_EL_INTERFAZ.items()
        ],
        "en_el_entorno_de_integracion": [
            {"metodo": metodo, "que_contesto": que}
            for metodo, que in iuws.COMPROBADO_ENTORNO_INTEGRACION.items()
        ],
        "que_significa_un_401": (
            "Que el método existe y pide credenciales: un 401 no es «no existe», es «no me has "
            "dicho quién eres». Un 404 sí significaría que la dirección está mal. En la "
            "dirección de la comunidad los siete contestaron 401 (o cortaron la conexión "
            "pidiendo el certificado) y ninguno contestó 404."
        ),
        "y_el_200_tambien_engaña": (
            "Ojo con la otra cara de lo mismo: el interfaz contesta 200 aunque el resultado sea "
            "un error. El código bueno va en el cuerpo (codigoResultado). Mirar solo el 200 es "
            "lo que hace decir «todo bien» cuando ha contestado ERROR_VALIDAR_CREDENCIALES."
        ),
        "por_que_no_se_prueba_lo_demas": (
            "Porque el servidor de la Junta corta la conexión antes de llegar al programa si no "
            "se le presenta el certificado de cliente. Insistir daría un error que no se puede "
            "arreglar desde aquí."
        ),
    }


@router.post("/leer-respuesta")
def leer_respuesta(datos: dict) -> dict:
    """Traduce lo que contesta el interfaz, para poder pegarlo en un correo a soporte.

    Se le pasa el texto tal cual lo devolvió el interfaz —o el JSON— y devuelve qué significa
    cada código. Es lo que evita que una incidencia se convierta en «me da un error».
    """
    cuerpo = (datos or {}).get("respuesta")
    if cuerpo is None:
        raise HTTPException(
            status_code=422,
            detail=textos.IUWS["falta_la_respuesta"],
        )
    leida = iuws.leer_respuesta(cuerpo)
    return {
        "codigo": leida.codigo,
        "mensaje": leida.mensaje,
        "esta_ok": leida.esta_ok,
        "es_parcial": leida.es_parcial,
        "es_fallo": leida.es_fallo,
        "id_peticion": leida.id_peticion,
        "detalles": leida.detalles,
        "actividades_fallidas": leida.actividades_fallidas(),
        "operacion": leida.operacion,
        "crudo": leida.crudo,
    }


@router.get("/mensajes")
def mensajes() -> dict:
    """El catálogo de mensajes del interfaz, traducido. Para tenerlo a mano al integrar."""
    return {
        "textos": textos.IUWS,
        "resultados": iuws.RESULTADOS,
        "mensajes": [
            {"codigo": codigo, "nombre": nombre, "significado": significado, "explicacion": iuws.mensaje_de_codigo(codigo)}
            for codigo, (nombre, significado) in sorted(iuws.MENSAJES.items())
        ],
    }
