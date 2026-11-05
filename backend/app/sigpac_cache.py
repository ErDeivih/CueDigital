"""La caché de la descarga oficial del SIGPAC, **una provincia por fichero y campaña**.

### Qué problema resuelve

El programa ya sabe pedir **un recinto** al SIGPAC por sus siete códigos (`app/sigpac.py`) y eso
es lo que usa el alta de una parcela. Para traer **las cuarenta de una vez** no sirve pedirlas de
una en una: el FEGA publica el SIGPAC entero en **GeoPackage**, por provincia y por campaña, y
descargarlo una vez y guardarlo en el servidor es lo que evita hacer una llamada por cada punto.

### De dónde salen la dirección y el nombre del fichero (no está inventado)

Está verificado el 04/11/2026 contra el servidor del FEGA y documentado en
`docs/INVESTIGACION-AGRICOLA.md`, apartado 1.2:

* El listado de una campaña es `https://sigpac-hubcloud.es/geopackages/{CAMPAÑA}/recintos/`.
* El fichero real de Salamanca 2026 es `37_SALAMANCA_rec_2026_20251215_gpkg.zip`, **628 MB**.
* El patrón es `{PROVINCIA}_{NOMBRE}_rec_{CAMPAÑA}_{AAAAMMDD}_gpkg.zip`, donde `AAAAMMDD` es la
  **fecha de validez** de los datos y cambia con cada actualización.

**Por eso la fecha no se adivina y el nombre de la provincia tampoco**: el programa **lee el
listado** de la campaña y busca el enlace cuyo nombre empieza por el código de la provincia. Si
construyera el nombre «a ojo» con una fecha supuesta, pediría un fichero que no existe (o, peor,
uno viejo creyendo que es el nuevo). Si el listado no trae esa provincia, se dice y no se descarga
nada.

### Licencia

Los recintos del SIGPAC del FEGA son **CC BY 4.0**: permiten uso comercial, copia, caché y
redistribución **citando** la fuente. La cita viaja en la ficha de cada descarga
(`LICENCIA`/`ATRIBUCION`), no en un comentario que se pierde: al distribuir la capa de recintos
hay que citar además a la **Dirección General del Catastro**. Ver `docs/INVESTIGACION-AGRICOLA.md`
§1.5.

### Lo que este módulo NO hace todavía (dicho aquí y en el informe)

1. **No abre el GeoPackage**: no lee los recintos de dentro ni los cruza con las parcelas del
   agricultor. Eso es lo siguiente (AGR-3, segunda mitad) y necesita `sqlite3`/GDAL sobre el
   `.gpkg`; hoy lo que se entrega es la descarga fiable, verificada y cacheada.
2. **La descarga se trae el fichero a memoria** antes de escribirlo (`fetch` devuelve `bytes`).
   Con 628 MB por provincia eso pide un servidor con holgura; lo correcto es bajarlo por trozos a
   un fichero temporal. Se deja dicho para no fingir que está resuelto.
3. **No hay purga ni límite de tamaño**: se guarda una provincia por campaña y se queda ahí. La
   carpeta está en el `.gitignore` y se cambia de sitio con `CUEDIGITAL_SIGPAC_CACHE`.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import os
import re
import zipfile
from pathlib import Path
from urllib.parse import urljoin

# --------------------------------------------------------------------------
# Las direcciones y la licencia
# --------------------------------------------------------------------------

# El listado oficial de la descarga. La campaña y la carpeta `recintos` se añaden después:
#   https://sigpac-hubcloud.es/geopackages/2026/recintos/
# Comprobado el 04/11/2026 (`docs/INVESTIGACION-AGRICOLA.md` §1.2).
BASE_DESCARGA = "https://sigpac-hubcloud.es/geopackages"

# Un listado son unos kilobytes; un GeoPackage de provincia son cientos de megas.
ESPERA_LISTADO_SEGUNDOS = 30.0
ESPERA_DESCARGA_SEGUNDOS = 300.0

# La licencia, tal y como la publica el FEGA. Se guarda en cada ficha porque CC BY exige citar, y
# una cita que solo vive en el código no viaja con el dato.
LICENCIA = "CC BY 4.0 — FEGA"
ATRIBUCION = (
    "Fuente de los datos: FONDO ESPAÑOL DE GARANTÍA AGRARIA O.A. "
    "Al distribuir la capa de recintos hay que citar además a la Dirección General del Catastro."
)

# El nombre oficial del fichero, leído del listado del servidor:
#   37_SALAMANCA_rec_2026_20251215_gpkg.zip
PATRON_DEL_FICHERO = re.compile(
    r"^(?P<provincia>\d{2})_(?P<nombre>[A-Za-z0-9_\-]+)_rec_"
    r"(?P<campana>\d{4})_(?P<fecha>\d{8})_gpkg\.zip$"
)

# Las claves que se publican de una ficha. Es una lista blanca a propósito: así no se cuela por la
# API ninguna ruta del servidor (el mismo defecto que se quitó de `GET /api/sigpac/estado` el
# 03/10/2026, `docs/T01_REVISION_RUTAS_SIN_SESION.md` §3.13).
CAMPOS_DE_LA_FICHA = (
    "provincia",
    "nombre_provincia",
    "campana",
    "fecha_validez",
    "fichero",
    "bytes",
    "sha256",
    "url",
    "licencia",
    "atribucion",
    "descargado_en",
)


class SigpacCacheError(RuntimeError):
    """No se ha podido dejar el mapa de esa provincia en la caché.

    Hay tres motivos distintos y no se pueden tratar igual: no hay red, el listado no trae ese
    fichero, o lo que ha llegado no es un mapa. Cada uno tiene su excepción debajo.
    """


class SinRed(SigpacCacheError):
    """No se ha podido llegar al servidor del SIGPAC (o ha contestado un error suyo)."""


class SinFichero(SigpacCacheError):
    """El listado de esa campaña no trae el fichero de esa provincia.

    Puede ser que la campaña todavía no esté publicada, o que la provincia no exista. **No se
    rellena con otro fichero ni con una fecha supuesta**: se dice y se para.
    """


class FicheroNoValido(SigpacCacheError):
    """Lo que ha llegado no es un ZIP con un GeoPackage dentro. No se guarda nada."""


# --------------------------------------------------------------------------
# La carpeta y la descarga de red
# --------------------------------------------------------------------------


def carpeta_de_cache() -> Path:
    """Dónde se guardan los mapas. `CUEDIGITAL_SIGPAC_CACHE` o `datos/sigpac_cache`.

    Se lee en cada llamada, no al importar: así los tests pueden apuntarla a una carpeta temporal
    y una instalación puede cambiarla sin tocar el código.
    """
    configurada = os.environ.get("CUEDIGITAL_SIGPAC_CACHE")
    if configurada:
        return Path(configurada)
    return Path(__file__).resolve().parents[2] / "datos" / "sigpac_cache"


def fetch_http(url: str) -> bytes:
    """La descarga de verdad. **Es lo único que sale a internet en este módulo.**

    Es una función aparte y no un `httpx.get` suelto dentro de `descargar_provincia` porque los
    tests la sustituyen: un test que depende de que el FEGA esté disponible es una lotería, y una
    lotería no es un test.
    """
    import httpx

    espera = ESPERA_LISTADO_SEGUNDOS if url.endswith("/") else ESPERA_DESCARGA_SEGUNDOS
    try:
        respuesta = httpx.get(url, timeout=espera, follow_redirects=True)
    except Exception as error:  # noqa: BLE001 — cualquier fallo de red es el mismo caso
        raise SinRed(
            "No se ha podido llegar al servidor del SIGPAC "
            f"({type(error).__name__}). Comprueba la conexión y vuelve a intentarlo."
        ) from None
    if respuesta.status_code != 200:
        raise SinRed(
            f"El servidor del SIGPAC ha contestado HTTP {respuesta.status_code}. "
            "No se ha descargado nada."
        )
    cuerpo = respuesta.content
    if not cuerpo:
        raise SinRed("El servidor del SIGPAC ha contestado vacío. No se ha descargado nada.")
    return cuerpo


# --------------------------------------------------------------------------
# El listado de la campaña
# --------------------------------------------------------------------------


def url_del_listado(campana: int, url_base: str | None = None) -> str:
    """La dirección del listado de ficheros de una campaña."""
    base = (
        url_base
        or os.environ.get("CUEDIGITAL_SIGPAC_DESCARGA")
        or BASE_DESCARGA
    ).rstrip("/")
    return f"{base}/{int(campana)}/recintos/"


def fecha_de_validez(nombre: str) -> str | None:
    """La fecha de validez que lleva el nombre del fichero, en `AAAA-MM-DD`.

    Sale del nombre porque **es el único sitio donde el FEGA la publica**: no hay un campo aparte
    ni una cabecera que la diga. Devuelve `None` si el nombre no es del SIGPAC, en vez de inventar
    una fecha.
    """
    encontrado = PATRON_DEL_FICHERO.match(str(nombre or ""))
    if not encontrado:
        return None
    fecha = encontrado.group("fecha")
    return f"{fecha[0:4]}-{fecha[4:6]}-{fecha[6:8]}"


def entradas_del_listado(texto: str, campana: int) -> list[dict]:
    """Los ficheros de esa campaña que aparecen en el listado, leídos de sus enlaces.

    Se leen los `href` y se queda solo lo que tiene la forma del fichero del SIGPAC y la campaña
    pedida: el listado trae también `../`, enlaces a otras campañas y ficheros de otros años, y
    colarlos sería descargar lo que no es.
    """
    salida: list[dict] = []
    for enlace in re.findall(r"""href\s*=\s*["']([^"']+)["']""", texto, flags=re.IGNORECASE):
        nombre = enlace.split("?")[0].split("#")[0].rstrip("/").rsplit("/", 1)[-1]
        encontrado = PATRON_DEL_FICHERO.match(nombre)
        if not encontrado:
            continue
        if int(encontrado.group("campana")) != int(campana):
            continue
        salida.append(
            {
                "provincia": int(encontrado.group("provincia")),
                "nombre_provincia": encontrado.group("nombre").upper(),
                "campana": int(campana),
                "fecha_validez": fecha_de_validez(nombre),
                "fichero": nombre,
                "href": enlace,
            }
        )
    return salida


def listado_de_la_campana(
    campana: int, *, fetch=None, url_base: str | None = None
) -> list[dict]:
    """Pide el listado de una campaña y devuelve los ficheros de provincia que anuncia."""
    url = url_del_listado(campana, url_base)
    cuerpo = _pedir(fetch, url)
    texto = (
        cuerpo.decode("utf-8", errors="replace")
        if isinstance(cuerpo, (bytes, bytearray))
        else str(cuerpo)
    )
    return entradas_del_listado(texto, campana)


def _pedir(fetch, url: str) -> bytes:
    """Hace la petición con el `fetch` que haya, y traduce sus fallos a los de esta casa."""
    if fetch is None:
        fetch = fetch_http
    try:
        return fetch(url)
    except SigpacCacheError:
        raise
    except Exception as error:  # noqa: BLE001 — un fallo de red es un fallo de red
        raise SinRed(
            "No se ha podido llegar al servidor del SIGPAC "
            f"({type(error).__name__}). Comprueba la conexión y vuelve a intentarlo."
        ) from None


def busca_el_de_la_provincia(entradas: list[dict], provincia: int) -> dict | None:
    """El fichero de esa provincia, y si hay varios, el de la fecha de validez más nueva.

    El listado puede contener más de una actualización de la misma campaña. Se queda la última
    (la fecha del nombre, que es la de validez), no la primera que aparezca.
    """
    suyos = [entrada for entrada in entradas if entrada["provincia"] == int(provincia)]
    if not suyos:
        return None
    return max(suyos, key=lambda entrada: (entrada["fecha_validez"] or "", entrada["fichero"]))


# --------------------------------------------------------------------------
# El fichero: comprobarlo y guardarlo
# --------------------------------------------------------------------------


def comprueba_que_es_un_mapa(contenido: bytes, fichero: str) -> None:
    """Comprueba que lo descargado es un ZIP **con un GeoPackage dentro**. Si no, no se guarda.

    Se mira por dentro y no solo el nombre: un servidor en mantenimiento puede contestar un HTML
    con un 200, y guardarlo como si fuera el mapa daría un fichero que después no se puede abrir y
    nadie sabría por qué. Y se descomprime un trozo del `.gpkg` (no solo se mira que el nombre esté
    en el índice) porque un ZIP con la cabecera bien y el contenido roto pasaría la primera prueba.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as paquete:
            nombres = paquete.namelist()
            mapas = [nombre for nombre in nombres if nombre.lower().endswith(".gpkg")]
            if not mapas:
                raise FicheroNoValido(
                    f"El fichero «{fichero}» que ha publicado el SIGPAC no lleva dentro ningún "
                    "mapa (.gpkg). No se ha guardado nada."
                )
            with paquete.open(mapas[0]) as mapa:
                mapa.read(1024)
    except FicheroNoValido:
        raise
    except zipfile.BadZipFile:
        raise FicheroNoValido(
            f"Lo que ha contestado el SIGPAC para «{fichero}» no es un ZIP válido. "
            "No se ha guardado nada."
        ) from None
    except Exception:  # noqa: BLE001 — un ZIP roto puede fallar de varias maneras
        raise FicheroNoValido(
            f"El fichero «{fichero}» del SIGPAC está dañado y no se puede leer. "
            "No se ha guardado nada."
        ) from None


def _nombre_de_la_ficha(provincia: int, campana: int) -> str:
    return f"{int(provincia):02d}_{int(campana)}.json"


def ficha_guardada(provincia: int, campana: int) -> dict | None:
    """La ficha de una descarga anterior, si **el fichero sigue estando y con su tamaño**.

    Es lo que hace que la segunda descarga no vuelva a bajar 628 MB. Se comprueba el tamaño y no
    el sha256 en cada llamada a propósito: recalcular la huella de 628 MB cada vez que se mira el
    estado costaría más que volver a leer el listado. La huella queda guardada en la ficha para
    poder comprobar el fichero cuando haga falta.
    """
    carpeta = carpeta_de_cache()
    ruta = carpeta / _nombre_de_la_ficha(provincia, campana)
    if not ruta.is_file():
        return None
    try:
        ficha = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(ficha, dict) or not ficha.get("fichero"):
        return None
    descargado = carpeta / str(ficha["fichero"])
    if not descargado.is_file():
        return None
    if descargado.stat().st_size != ficha.get("bytes"):
        return None
    return ficha


def descargar_provincia(
    provincia: int,
    campana: int,
    *,
    fetch=None,
    url_base: str | None = None,
) -> dict:
    """Deja en la caché el mapa de una provincia y devuelve su ficha.

    Los pasos, en este orden y no en otro:

    1. Si ya está descargado (y el fichero sigue con su tamaño), se devuelve la ficha y **no se
       llama a nadie**: `{"descargado": False}`.
    2. Se lee el **listado de la campaña** y se busca el enlace de esa provincia.
    3. Se descarga, se comprueba que es un ZIP con un `.gpkg` y se calcula su sha256.
    4. Se guarda con su nombre oficial y una ficha JSON al lado.

    `fetch` es la descarga inyectable (`fetch(url) -> bytes`): los tests le pasan un servidor de
    mentira y así no se baja nada de internet. Si no se pasa, se usa `fetch_http`.

    Lanza `SinRed`, `SinFichero` o `FicheroNoValido` (todas `SigpacCacheError`) y en los tres casos
    **no deja nada a medias en la carpeta**.
    """
    provincia = int(provincia)
    campana = int(campana)
    if not 1 <= provincia <= 52:
        raise ValueError(
            f"Esa provincia no existe: {provincia}. Los códigos del SIGPAC van del 1 al 52."
        )
    if not 2000 <= campana <= 2100:
        raise ValueError(f"Esa campaña no tiene sentido: {campana}.")

    guardada = ficha_guardada(provincia, campana)
    if guardada is not None:
        return {**guardada, "descargado": False}

    carpeta = carpeta_de_cache()
    carpeta.mkdir(parents=True, exist_ok=True)

    entradas = listado_de_la_campana(campana, fetch=fetch, url_base=url_base)
    elegido = busca_el_de_la_provincia(entradas, provincia)
    if elegido is None:
        raise SinFichero(
            f"El listado del SIGPAC de la campaña {campana} no trae el mapa de la provincia "
            f"{provincia}. No se ha descargado nada: puede que esa campaña todavía no esté "
            "publicada para esa provincia."
        )

    url = urljoin(url_del_listado(campana, url_base), elegido["href"])
    contenido = _pedir(fetch, url)
    if not isinstance(contenido, (bytes, bytearray)) or not contenido:
        raise SinRed("La descarga del SIGPAC ha llegado vacía. No se ha guardado nada.")
    contenido = bytes(contenido)
    comprueba_que_es_un_mapa(contenido, elegido["fichero"])

    sha256 = hashlib.sha256(contenido).hexdigest()
    destino = carpeta / elegido["fichero"]
    # Se escribe primero a un temporal y se renombra: si el proceso se corta a mitad, en la carpeta
    # no queda un ZIP a medias que después parezca bueno.
    temporal = carpeta / f"{elegido['fichero']}.descargando"
    try:
        temporal.write_bytes(contenido)
        os.replace(temporal, destino)
    finally:
        temporal.unlink(missing_ok=True)

    ficha = {
        "provincia": provincia,
        "nombre_provincia": elegido["nombre_provincia"],
        "campana": campana,
        "fecha_validez": elegido["fecha_validez"],
        "fichero": elegido["fichero"],
        "bytes": len(contenido),
        "sha256": sha256,
        "url": url,
        "licencia": LICENCIA,
        "atribucion": ATRIBUCION,
        "descargado_en": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    (carpeta / _nombre_de_la_ficha(provincia, campana)).write_text(
        json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {**ficha, "descargado": True}


# --------------------------------------------------------------------------
# El estado de la caché
# --------------------------------------------------------------------------


def estado_cache() -> dict:
    """Qué provincias hay descargadas, con su campaña, su fecha de validez y su huella.

    **No dice dónde está la carpeta**: la ruta absoluta de una instalación no le sirve al
    agricultor y sí a quien busque por dónde entrar (el defecto que se quitó de
    `GET /api/sigpac/estado` en la revisión de rutas sin sesión).
    """
    carpeta = carpeta_de_cache()
    provincias: list[dict] = []
    if carpeta.is_dir():
        for ruta in sorted(carpeta.glob("*.json")):
            try:
                ficha = json.loads(ruta.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                # Una ficha a medio escribir no puede tumbar el estado: se ignora y se puede
                # volver a descargar.
                continue
            if not isinstance(ficha, dict) or "provincia" not in ficha:
                continue
            # **La ficha sin su fichero no cuenta como descarga**: se puede haber borrado a mano o
            # haberse quedado a medias, y decir «está» cuando no está es mentir en el estado.
            if not (carpeta / str(ficha.get("fichero") or "")).is_file():
                continue
            provincias.append({clave: ficha.get(clave) for clave in CAMPOS_DE_LA_FICHA})
    provincias.sort(key=lambda ficha: (ficha.get("campana") or 0, ficha.get("provincia") or 0))
    return {
        "licencia": LICENCIA,
        "atribucion": ATRIBUCION,
        "cuantas": len(provincias),
        "provincias": provincias,
        "campanas": sorted({ficha["campana"] for ficha in provincias if ficha.get("campana")}),
        "como_descargar": "POST /api/sigpac/cache/{provincia}?campana=…",
    }
