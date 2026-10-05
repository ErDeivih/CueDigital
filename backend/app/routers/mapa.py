"""El mapa: elegir la tierra tocándola.

**Por qué existe.** El agricultor no se sabe sus códigos, pero sabe dónde está su tierra: la
reconoce en una foto aérea de un vistazo. Aquí está la puerta que hace eso posible:

* `GET /api/mapa/estado` — qué servicios de mapa hay y qué se necesita para usarlos.
* `GET /api/mapa/imagen` — la imagen del mapa (la foto del campo, los linderos o el cultivo
  declarado) para la zona que se está mirando.
* `POST /api/mapa/punto` — **el toque**: qué parcela del SIGPAC hay en ese punto, con todo lo que
  el SIGPAC sabe de ella (superficie, uso, pendiente, dibujo, referencia catastral y si está en
  zona de nitratos).

**El navegador no llama al SIGPAC ni al IGN: llama a su propio programa.** Las direcciones
oficiales viven en `app/sigpac.py`, en un solo sitio. Así, si el servicio se cae, el agricultor
recibe un mensaje en castellano en vez de una imagen rota; y la aplicación sigue sabiendo lo que
sabe sin depender de que el navegador pueda hablar con un servicio de fuera.

**Lo que el mapa no va a hacer nunca: decidir por él.** Cuando el punto cae en una linde, el
SIGPAC devuelve el recinto que lo contiene, que puede ser el de al lado (está comprobado en los
tests con un punto de verdad). Por eso la pantalla enseña **qué trozo ha encontrado y cuántas
hectáreas tiene** antes de apuntarlo, y el agricultor confirma o lo intenta otra vez.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response, status

from .. import catalogos, sigpac, textos
from ..deps import UsuarioActual

router = APIRouter(prefix="/api/mapa", tags=["mapa"])

# El tamaño de imagen que se le pide al servicio oficial cuando no se dice otro. 900×600 se ve
# bien en un móvil y en un ordenador sin gastar datos de más.
ANCHO_POR_DEFECTO = 900
ALTO_POR_DEFECTO = 600

# Cuánto se puede acercar y alejar, en grados de la caja. El tope está para que nadie pida el
# mapa de media España en una imagen (el servicio no lo daría bien) y para que un error de
# cálculo no pida una caja imposible.
LADO_MINIMO_GRADOS = 0.0008  # unos 90 metros: lo más cerca que tiene sentido para una parcela
LADO_MAXIMO_GRADOS = 0.5  # unos 55 km: una comarca entera


@router.get("/estado")
def estado_del_mapa() -> dict:
    """Qué hay detrás del mapa, y de dónde sale. Sin sesión: no lleva datos de nadie.

    **Lo que se ha añadido en T06 (03/10/2026), y por qué.** La pantalla de las tierras enseña el
    mapa de la finca con la capa que el agricultor elija, y el contrato pide que el cambio de capa
    lleve «su leyenda y su fecha». Aquí van las tres cosas, y **ninguna inventada**:

      · `leyenda` — qué enseña esa capa, en una frase. Es lo que hace que una leyenda sea una
        leyenda y no un adorno.
      · `fecha` — **vacía, y con su motivo escrito en `fecha_texto`**. Los dos servicios que dan las
        imágenes (el WMS del IGN para la ortofoto y el del FEGA para los linderos y el cultivo) **no
        publican de qué día es la imagen**: se comprobó con su `GetCapabilities` el 03/10/2026 y los
        dos contestan sin ninguna dimensión de tiempo. Poner la fecha de hoy —o dejar el hueco en
        blanco— sería afirmar algo que nadie ha dicho, y el contrato prohíbe justo eso («no dejar una
        fotografía vieja sin fecha»). Lo que se hace es decirlo.
      · `se_puede_ocultar` — verdadero en las tres: el contrato pide que el usuario pueda quitar
        capas, y una capa que no se puede quitar no cumple.

    Y `capa_avisos_no_esta` dice, en la pantalla, por qué no hay capa de avisos: el SIGPAC no publica
    ningún servicio que la dé. Prometer un botón que no enseñaría nada es peor que no tenerlo.
    """
    leyendas = textos.TIERRA_Y_MAPA
    fecha_texto = leyendas["fecha_sin_saber"]
    return {
        "textos": textos.MAPA,
        "capas": {
            "foto": {
                "titulo": textos.MAPA["la_foto"],
                "servicio": "IGN (PNOA)",
                "leyenda": leyendas["leyenda_foto"],
                # Vacía a propósito: ver el docstring. `None` es «no se sabe», nunca «hoy».
                "fecha": None,
                "fecha_texto": fecha_texto,
                "se_puede_ocultar": True,
            },
            "linderos": {
                "titulo": textos.MAPA["los_linderos"],
                "servicio": "SIGPAC (FEGA)",
                "leyenda": leyendas["leyenda_linderos"],
                "fecha": None,
                "fecha_texto": fecha_texto,
                "se_puede_ocultar": True,
            },
            "cultivo": {
                "titulo": textos.MAPA["el_cultivo"],
                "servicio": "SIGPAC (FEGA)",
                "leyenda": leyendas["leyenda_cultivo"],
                "fecha": None,
                "fecha_texto": fecha_texto,
                "se_puede_ocultar": True,
            },
        },
        "leyenda_de_mis_tierras": leyendas["leyenda_mis_tierras"],
        "capa_avisos_no_esta": leyendas["capa_avisos_no_esta"],
        # Lo que pasa cuando una imagen no llega, dicho entero: no se borran los linderos, no se deja
        # una foto vieja sin fecha y la lista sigue funcionando. Es el texto que enseña la pantalla
        # cuando el `<img>` de una capa falla.
        "si_no_llega_una_imagen": leyendas["imagen_no_llega"],
        "necesita_conexion": True,
        "mensaje_sin_conexion": textos.MAPA["sin_conexion"],
        "limites": {
            "lado_minimo_grados": LADO_MINIMO_GRADOS,
            "lado_maximo_grados": LADO_MAXIMO_GRADOS,
            "ancho_por_defecto": ANCHO_POR_DEFECTO,
            "alto_por_defecto": ALTO_POR_DEFECTO,
        },
        "licencia": (
            "Ortofoto del IGN (PNOA) y cartografía del SIGPAC (FEGA), publicados bajo licencia "
            "Creative Commons BY 4.0. Las direcciones de los servicios y qué devuelve cada uno "
            "están en docs/SERVICIOS_DEL_SIGPAC.md."
        ),
    }


@router.get("/imagen")
def la_imagen_del_mapa(
    capa: str = Query(default="foto"),
    oeste: float = Query(...),
    sur: float = Query(...),
    este: float = Query(...),
    norte: float = Query(...),
    ancho: int = Query(default=ANCHO_POR_DEFECTO),
    alto: int = Query(default=ALTO_POR_DEFECTO),
) -> Response:
    """La imagen del mapa para una zona: la trae el programa y la sirve él.

    Se comprueba la caja antes de pedirla: si viene al revés (el sur por encima del norte, o el
    oeste por encima del este) o si es absurdamente grande o pequeña, se dice con un mensaje en
    castellano. Sin esa comprobación, una caja mal calculada acabaría pidiendo el mapa de otra
    provincia y el agricultor vería una foto que no es la suya sin saber por qué.
    """
    if capa not in sigpac.CAPAS_DEL_MAPA:
        raise HTTPException(status_code=422, detail=textos.MAPA["sin_conexion"])

    if not (sur < norte and oeste < este):
        raise HTTPException(
            status_code=422,
            detail=(
                "La zona del mapa está al revés: el sur tiene que ser menor que el norte y el "
                "oeste menor que el este."
            ),
        )
    lado = max(norte - sur, este - oeste)
    if lado < LADO_MINIMO_GRADOS or lado > LADO_MAXIMO_GRADOS:
        raise HTTPException(
            status_code=422,
            detail=(
                "Esa zona del mapa no tiene un tamaño que se pueda enseñar: acércala o aléjala."
            ),
        )

    try:
        contenido, tipo = sigpac.pedir_imagen_del_mapa(capa, oeste, sur, este, norte, ancho, alto)
    except sigpac.SigpacNoContesta:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=textos.MAPA["sin_conexion"],
        ) from None

    # Se puede guardar un ratito en el navegador: la foto del campo no cambia de un minuto a otro,
    # y así mover el mapa no vuelve a pedir lo mismo al IGN.
    return Response(
        content=contenido,
        media_type=tipo,
        headers={"Cache-Control": "public, max-age=600"},
    )


@router.post("/punto")
def que_hay_en_este_punto(datos: dict, _: UsuarioActual) -> dict:
    """**El toque en el mapa**: qué parcela del SIGPAC hay en ese punto, y todo lo que se sabe.

    Devuelve lo que hace falta para que el agricultor diga «sí, es mía» con conocimiento: la
    referencia, la superficie, el uso, la pendiente, el dibujo para pintarla encima del mapa, la
    referencia catastral y si está en zona de nitratos.

    La zona de nitratos se pregunta a la capa oficial y **puede quedar sin saber**: si el servicio
    no contesta o contesta algo que no se entiende, se devuelve `null` y la pantalla lo dice. Lo
    que no se hace es poner un «no» que no está comprobado, porque de eso dependen las reglas de
    abono que se le aplican a esa tierra.

    Va con un diccionario y se comprueban las coordenadas a mano, y no con un esquema de Pydantic
    como el resto de la API, por una razón concreta: si el navegador manda algo raro, el mensaje
    que vería el agricultor sería el de Pydantic («Input should be a valid number»), y esto es un
    mapa que se toca con el dedo. El mensaje se escribe aquí, en castellano.

    **Pide sesión desde el 03/10/2026, y antes no la pedía.** Lo dejó apuntado la revisión de
    rutas sin sesión (`docs/T01_REVISION_RUTAS_SIN_SESION.md`, §3.16) y no se había hecho. El
    motivo no es que devuelva datos de nadie —devuelve lo que hay en un punto del mapa, que es
    público— sino **a quién hace llamar**: cada toque son hasta **tres llamadas de salida** (al
    SIGPAC y al Catastro, 10 s de espera cada una) y no había ni límite ni caché, así que
    cualquiera con la dirección podía usar esta instalación de repetidor contra dos servicios
    públicos. El que paga esa factura, si al FEGA o al Catastro les molesta el tráfico, es el
    agricultor. La propia revisión dice que cerrarla «es barato», y lo es: **la única pantalla que
    la llama ya manda su vale** (`app.js:6771`, por `apiJson`, que siempre pone el vale).

    Pide `UsuarioActual` y no `ExplotacionActual`: la respuesta no depende de ninguna finca, lo
    que hay que saber es **quién** pregunta. (Y es la puerta por la que se podrá poner el límite
    de peticiones por cuenta que pide el §5.2 de esa misma revisión.)
    """
    try:
        x = float(datos.get("x"))
        y = float(datos.get("y"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=422,
            detail="No se ha entendido dónde has tocado en el mapa. Prueba otra vez.",
        ) from None

    if not (-180 <= x <= 180 and -90 <= y <= 90):
        raise HTTPException(
            status_code=422,
            detail="Esas coordenadas no son de ningún sitio del mundo. Prueba otra vez.",
        )

    try:
        recinto = sigpac.pedir_recinto_por_punto(x, y)
    except sigpac.SigpacNoContesta:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=textos.MAPA["sin_conexion"],
        ) from None

    if recinto is None or not recinto.ref_sigpac:
        return {
            "textos": textos.MAPA,
            "encontrado": False,
            "mensaje": textos.MAPA["no_hay_nada"],
        }

    referencia = recinto.referencia
    municipio = catalogos.municipio_por_codigo_ine(
        f"{recinto.provincia:02d}{recinto.municipio:03d}"
        if recinto.provincia is not None and recinto.municipio is not None
        else None
    )

    # La referencia catastral y la zona de nitratos: las dos se preguntan, y las dos pueden no
    # saberse. Ninguna de las dos puede impedir que se enseñe la parcela.
    referencia_catastral: str | None = None
    if referencia is not None:
        try:
            referencia_catastral = sigpac.pedir_referencia_catastral(
                sigpac.Busqueda(
                    provincia=referencia.provincia,
                    municipio=referencia.municipio,
                    agregado=referencia.agregado,
                    zona=referencia.zona,
                    poligono=referencia.poligono,
                    parcela=referencia.parcela,
                )
            )
        except sigpac.SigpacNoContesta:
            referencia_catastral = None

    en_zona: bool | None = None
    porcentaje: float | None = None
    if referencia is not None:
        try:
            respuesta_nitratos = sigpac.zona_de_nitratos(referencia)
        except sigpac.SigpacNoContesta:
            respuesta_nitratos = None
        if respuesta_nitratos is not None:
            en_zona, porcentaje = respuesta_nitratos

    return {
        "textos": textos.MAPA,
        "encontrado": True,
        "referencia": recinto.ref_sigpac,
        "recinto": recinto.recinto,
        "superficie_ha": recinto.superficie,
        "uso_sigpac": recinto.uso_sigpac,
        "uso": sigpac.etiqueta_uso(recinto.uso_sigpac),
        "pendiente_pct": recinto.pendiente_media,
        "altitud": recinto.altitud,
        # Los vértices de la parcela, en coordenadas de verdad, para pintarla encima del mapa y
        # que el agricultor confirme que es la suya. Se mandan los puntos y no el WKT: la pantalla
        # solo tiene que colocar cada punto en su sitio, y así no hay dos maneras de leerlo.
        "puntos": puntos_de_la_parcela(recinto.wkt),
        "municipio": (
            {
                "nombre": municipio.nombre,
                "provincia": municipio.provincia,
                "codigo_ine": municipio.codigo_ine,
            }
            if municipio
            else None
        ),
        "referencia_catastral": referencia_catastral,
        "en_zona_de_nitratos": en_zona,
        "zona_de_nitratos_porcentaje": porcentaje,
    }


def puntos_de_la_parcela(wkt: str | None) -> list[list[float]]:
    """Los vértices del trozo, listos para que la pantalla los coloque en el mapa.

    Se reutiliza lo que ya hace el programa para dibujar cada parcela en *Mis cosas*: una sola
    forma de leer un trozo de tierra en toda la aplicación, y no dos que se puedan separar.
    """
    if not wkt:
        return []
    from .. import geo

    return [[lon, lat] for lon, lat in geo.puntos_de_un_wkt(wkt)]
