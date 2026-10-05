"""Baja los catálogos oficiales que **sí se pueden bajar**, y dice los que no.

## Por qué hace falta

El cuaderno digital tiene campos que se rellenan con **códigos oficiales**: la unidad de medida, el
tipo de producto, la justificación de la aplicación, la eficacia del tratamiento… El programa no se
los puede inventar —sería el peor de los fallos posibles en un cuaderno que va a una inspección—, así
que se bajan de donde los publica la administración, **con su dirección, su fecha y su huella**.

## Lo que sí se baja (comprobado el 27/09/2026, sin captcha y sin registro)

**Del FEGA** (Fondo Español de Garantía Agraria), que es quien publica el diseño del cuaderno:

| Qué | De dónde |
|---|---|
| Documento Técnico SIEX 3.11 | `fega.gob.es/es/siex/documentacion-tecnica-agricola-siex/documento-tecnico-311` |
| Anexo V — definición de variables (REA y CUE) | `…/anexo-v-definicion-de-variables-311` |
| Anexo VI — Interfaz Único Común v3.11.4 | `…/anexo-vi-interfaz-unico-comun-3111` |
| Anexo VIII, Anexo IX y Anexo X | Los modelos de autorización, en `fega.gob.es/sites/default/files/…` |

**Del MAPA**, del buscador del Registro de Productos Fitosanitarios (`servicio.mapa.gob.es/regfiweb`):
las **tablas de codificación** (unidades, prudencias, clasificaciones, riesgos, utilizaciones,
ámbitos, funciones, preparados, tipos de usuario, sistemas de cultivo, coformulantes, acciones,
translocaciones, métodos de aplicación y tipos de sustancias), el **listado de productos** y los
ficheros publicados de **plagas** y **jerarquía de especies**.

Ese buscador **no tiene captcha ni hace falta entrar**: lo único que se hace aquí es la **misma
petición** que hace su propia página cuando alguien pulsa el botón de exportar (leído de su
`site.min.js`: un `POST` a `/regfiweb/Exportaciones/ExportExcel`). Se va **despacio** (una petición
cada dos segundos), con un cliente que **se identifica**, y **no se modifica nada** en el servidor: solo
se descargan ficheros.

## Lo que NO se baja, y por qué (esto es lo importante)

1. **Los valores de los catálogos de SIEX** —incluida la tabla `UNIDADES_MEDIDA`— están detrás de un
   **captcha de Google (reCAPTCHA)** en `https://www3.sede.fega.gob.es/bdcsixpor/catalogos`. **No se
   intenta pasar**: saltarse un captcha es saltarse la norma de una web, y este programa no lo hace. Se
   guarda la **estructura** de esos catálogos (nombres y columnas), que sí es pública, y se dice que
   **los valores no están**. Lo que hay que hacer es pedirlos (ver `docs/CORREO_LISTO_PARA_ENVIAR.md`).
2. **Nada del interfaz IUWS/REA/CUE**: eso exige **certificado digital** y alta como empresa. Se prueba
   aparte, a mano, con `scripts/probar_iuws.py`.
3. **El fichero de autorizaciones excepcionales** (`.xls` de 33 MB): es un Excel antiguo, y este
   proyecto solo sabe leer los modernos (`.xlsx`). Se dice en el LEEME; **no se guarda un fichero que
   no se puede ni abrir**.
4. **El buscador interno del FEGA** (`/search/site`): su `robots.txt` lo prohíbe. No se usa.

> **No se mezclan dos catálogos que se llaman parecido.** La tabla `Unidades` del MAPA (del registro de
> fitosanitarios) **no es** la tabla `UNIDADES_MEDIDA` de SIEX (del cuaderno). Una viene del MAPA y la
> otra del FEGA, y «parecerse no es ser». El LEEME lo avisa en su primera línea porque es el error caro.

## Cómo se lanza

```bash
cd backend
../.venv/Scripts/python.exe scripts/bajar_catalogos_fega.py
../.venv/Scripts/python.exe scripts/bajar_catalogos_fega.py --sin-descarga   # rehace el LEEME sin red
```

Si un fichero no llega, **se para y lo dice con su dirección y su código HTTP**: nunca se guarda un
valor de relleno ni una página de error con la forma de un catálogo.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import pathlib
import time

import httpx

RAIZ = pathlib.Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "data" / "fega"

# Se identifica y se va despacio: es la casa de todos, y aquí se entra a pedir un favor.
CABECERAS = {
    "User-Agent": "CueDigital/1.0 (cuaderno de campo; descarga de datos oficiales publicos)",
    "Accept": "*/*",
}
SEGUNDOS_ENTRE_PETICIONES = 2.0
ESPERA = 90.0

FEGA_DOCS = "https://www.fega.gob.es/es/siex/documentacion-tecnica-agricola-siex"

# La huella del Anexo VI que ya estaba comprobada en `data/iuws_fuentes/LEEME.md`. Es la base del
# descriptor del cuaderno: si el FEGA publica otro documento, hay que mirarlo antes de seguir, no
# sustituirlo en silencio.
HUELLA_ANEXO_VI = "8acd60aca62e002533ac8c4aa45d2ffb820fa94c849f72d11bff63474f418d5d"

# **Cómo se llega al fichero de cada documento, y por qué así.** El FEGA no publica la dirección del
# PDF ni del Excel: publica una **página** de cada anexo, y el fichero está enlazado dentro. Poner aquí
# la dirección del fichero a mano funcionaría hoy y dejaría de funcionar el día que publiquen una
# corrección (que es justo lo que han hecho: los nombres llevan la fecha de la corrección). Así que se
# lee la página y se coge el enlace que hay dentro. Es el mismo criterio que con los ficheros del MAPA:
# **se descubre, no se adivina**.
FICHEROS_FEGA: dict[str, dict] = {
    "documento_tecnico_siex_3.11.pdf": {
        "pagina": f"{FEGA_DOCS}/documento-tecnico-311",
        "que_es": "Documento Técnico SIEX 3.11 (el diseño del cuaderno y de los catálogos)",
        "comprobacion": "pdf",
        "licencia": "FEGA: se autoriza la reproducción citando el origen y sin alterar el contenido",
    },
    "anexo_v_definicion_de_variables_3.11.xlsx": {
        "pagina": f"{FEGA_DOCS}/anexo-v-definicion-de-variables-311",
        "que_es": "Anexo V: definición de las variables de REA y del cuaderno (hojas REA y CUE)",
        "comprobacion": "xlsx",
        "licencia": "FEGA: se autoriza la reproducción citando el origen y sin alterar el contenido",
    },
    "anexo_vi_interfaz_unico_comun_3.11.4.docx": {
        "pagina": f"{FEGA_DOCS}/anexo-vi-interfaz-unico-comun-3111",
        "que_es": "Anexo VI: el interfaz único común (v3.11.4), con los métodos y las cabeceras",
        "comprobacion": "docx",
        "huella_conocida": HUELLA_ANEXO_VI,
        "licencia": "FEGA: se autoriza la reproducción citando el origen y sin alterar el contenido",
    },
    "anexo_viii_autorizacion_representacion.docx": {
        "url": (
            "https://www.fega.gob.es/sites/default/files/files/document/"
            "2023.11.10-ANEXO%20VIII.%20Modelo_autorizacion_representaci%C3%B3n_PUBLICADO.docx"
        ),
        "que_es": "Anexo VIII: modelo de autorización de representación (lo firma el titular)",
        "comprobacion": "docx",
        "licencia": "FEGA: se autoriza la reproducción citando el origen y sin alterar el contenido",
    },
    "anexo_ix_autorizacion_acceso_rea_cue.docx": {
        "url": (
            "https://www.fega.gob.es/sites/default/files/files/document/"
            "2023.11.10-ANEXO%20IX.Modelo_autorizaci%C3%B3n_acceso_REA_CUE_PUBLICADO.docx"
        ),
        "que_es": "Anexo IX: modelo de autorización de acceso a REA y al cuaderno",
        "comprobacion": "docx",
        "licencia": "FEGA: se autoriza la reproducción citando el origen y sin alterar el contenido",
    },
    "anexo_x_procedimiento_autorizacion_cue.pdf": {
        "pagina": "https://www.fega.gob.es/es/documentos_fega/siex/anexo_X",
        "que_es": "Anexo X: procedimiento de autorización y las direcciones del interfaz por comunidad",
        "comprobacion": "pdf",
        "licencia": "FEGA: se autoriza la reproducción citando el origen y sin alterar el contenido",
    },
}

# Las tablas de codificación del buscador de fitosanitarios del MAPA. Se piden **igual que lo hace su
# propia web**: un POST con el nombre de la exportación. `filas_esperadas` es lo que traía el fichero
# el día que se comprobó; si un día trae otras, se apunta el cambio en el LEEME en vez de callarlo
# (un catálogo de productos crece, y crecer no es un error).
EXPORTACIONES_MAPA: dict[str, dict] = {
    "Unidades": {"fichero": "mapa_unidades.xlsx", "que_es": "Unidades de medida del registro de fitosanitarios", "filas_esperadas": 124},
    "Prudencias": {"fichero": "mapa_prudencias.xlsx", "que_es": "Frases de prudencia (las «P» de las etiquetas)", "filas_esperadas": 237},
    "Clasificaciones": {"fichero": "mapa_clasificaciones.xlsx", "que_es": "Clasificaciones y etiquetado", "filas_esperadas": 179},
    "Riesgos": {"fichero": "mapa_riesgos.xlsx", "que_es": "Riesgos (las «H» y las «EUH»)"},
    "Utilizaciones": {"fichero": "mapa_utilizaciones.xlsx", "que_es": "Utilizaciones"},
    "Ambitos": {"fichero": "mapa_ambitos.xlsx", "que_es": "Ámbitos de aplicación"},
    "Funciones": {"fichero": "mapa_funciones.xlsx", "que_es": "Funciones del producto"},
    "Preparados": {"fichero": "mapa_preparados.xlsx", "que_es": "Tipos de preparado (formulación)"},
    "TipoUsuarios": {"fichero": "mapa_tipos_usuario.xlsx", "que_es": "Tipos de usuario"},
    "SistemasCultivos": {"fichero": "mapa_sistemas_cultivo.xlsx", "que_es": "Sistemas de cultivo"},
    "Coformulantes": {"fichero": "mapa_coformulantes.xlsx", "que_es": "Coformulantes"},
    "Acciones": {"fichero": "mapa_acciones.xlsx", "que_es": "Acciones del producto sobre el organismo"},
    "Translocaciones": {"fichero": "mapa_translocaciones.xlsx", "que_es": "Translocación en la planta"},
    "MetodosAplicacion": {"fichero": "mapa_metodos_aplicacion.xlsx", "que_es": "Métodos de aplicación"},
    "TipoSustancias": {"fichero": "mapa_tipos_sustancia.xlsx", "que_es": "Tipos de sustancia activa"},
}

EXPORTADOR_MAPA = "https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel"

# El listado de productos: el fichero oficial más pequeño de los dos que publica el buscador (el JSON
# trae 49 campos y pesa 14 MB; este es el Excel oficial, con 28 columnas). Se guarda el Excel.
LISTADO_DE_PRODUCTOS = {
    "fichero": "mapa_productos_fitosanitarios.xlsx",
    "url": "https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcelFiltroProducto",
    "que_es": "Listado completo de productos fitosanitarios registrados (el registro oficial)",
    # Esta exportación se pide con POST y **sin filtros** (el buscador manda un formulario vacío).
    # Con GET contesta 405 —«método no permitido»—, que es lo que pasó la primera vez que se probó.
    "metodo": "post",
}

# Los ficheros que el MAPA publica para descarga directa y que **se descubren en su propia página**:
# no se escriben a mano aquí para no inventarse una ruta que puede cambiar. Ver `_del_dam`.
PAGINA_DEL_REGISTRO = (
    "https://www.mapa.gob.es/es/agricultura/temas/sanidad-vegetal/productos-fitosanitarios/registro-productos/"
)
DEL_DAM = {
    "plagas.xlsx": "Clasificación oficial de plagas",
    "jerarquia.xlsx": "Jerarquía de especies vegetales (el nombre oficial de cada cultivo)",
}

# Lo que NO se baja, con el motivo escrito. Sale publicado en el LEEME, y hay una prueba que impide
# que alguien meta estas direcciones dentro del guion más adelante.
NO_SE_DESCARGA = [
    {
        "url": "https://www3.sede.fega.gob.es/bdcsixpor/catalogos",
        "que_es": "Los VALORES de los catálogos de SIEX (incluida la tabla UNIDADES_MEDIDA)",
        "por_que_no": (
            "está detrás de un captcha de Google (reCAPTCHA). No se pasa: saltarse un captcha es "
            "saltarse la norma de una web. Hay que pedirlos (docs/CORREO_LISTO_PARA_ENVIAR.md)"
        ),
    },
    {
        "url": "https://www11.fega.es/bdcsix/login/portal",
        "que_es": "El acceso identificado al portal de SIEX",
        "por_que_no": "exige usuario y contraseña, y este programa no entra en ninguna cuenta",
    },
    {
        "url": "https://www.fega.gob.es/search/site",
        "que_es": "El buscador interno del FEGA",
        "por_que_no": "su robots.txt lo prohíbe expresamente: no se usa",
    },
    {
        "url": (
            "https://www.mapa.gob.es/dam/…/registro-productos-fitosanitarios/"
            "autorizaciones_excepcionales.xls"
        ),
        "que_es": "Las autorizaciones excepcionales (33 MB)",
        "por_que_no": (
            "es un Excel antiguo (.xls) y este proyecto solo sabe leer los modernos (.xlsx). "
            "No se guarda un fichero que no se puede ni abrir"
        ),
    },
]


# --------------------------------------------------------------------------
# Comprobaciones
# --------------------------------------------------------------------------


def _abre_xlsx(contenido: bytes) -> tuple[bool, str]:
    """Dice si el fichero es un Excel de verdad, qué hojas trae y cuántas filas la más llena."""
    from openpyxl import load_workbook

    try:
        libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as error:  # noqa: BLE001 — un fichero que no abre es un fichero que no vale
        return False, f"no se puede abrir como Excel ({type(error).__name__})"
    nombres = libro.sheetnames
    if not nombres:
        return False, "el Excel no tiene ninguna hoja"
    # **Se cuentan todas las hojas, y se dice la que más tiene.** Contar solo la primera engaña: el
    # fichero de plagas trae delante una hoja de «Nota explicativa» con una sola fila, y mirando esa
    # parecería un fichero vacío.
    cuantas = {}
    for nombre in nombres:
        hoja = libro[nombre]
        cuantas[nombre] = sum(
            1 for fila in hoja.iter_rows(values_only=True) if any(celda is not None for celda in fila)
        )
    la_que_mas = max(cuantas, key=lambda nombre: cuantas[nombre])
    detalle = ", ".join(f"{nombre}: {numero}" for nombre, numero in cuantas.items())
    cuantas_hojas = f"{len(nombres)} hoja" + ("" if len(nombres) == 1 else "s")
    return True, f"{cuantas[la_que_mas]} filas en «{la_que_mas}» ({cuantas_hojas}: {detalle})"


def comprobar(contenido: bytes, como: str) -> tuple[bool, str]:
    """Comprueba que lo que ha llegado es lo que se ha pedido, y devuelve qué se ha visto.

    Esto es lo que evita el dato inventado: si el servidor contesta con una página de error o con un
    captcha, el fichero **no se guarda**, aunque llegue con un 200.
    """
    if como == "xlsx":
        if contenido[:2] != b"PK":
            return False, "no es un Excel (no empieza como un ZIP): puede ser una página de error"
        return _abre_xlsx(contenido)
    if como == "pdf":
        if contenido[:5] != b"%PDF-":
            return False, "no es un PDF"
        return True, f"{len(contenido):,} bytes"
    if como == "docx":
        if contenido[:2] != b"PK":
            return False, "no es un .docx (no empieza como un ZIP)"
        return True, f"{len(contenido):,} bytes"
    if como == "json":
        try:
            json.loads(contenido)
        except Exception as error:  # noqa: BLE001
            return False, f"no es JSON válido ({type(error).__name__})"
        return True, f"{len(contenido):,} bytes"
    return False, f"no se sabe comprobar «{como}»"


# --------------------------------------------------------------------------
# Descarga
# --------------------------------------------------------------------------


def _trae(cliente: httpx.Client, url: str, datos: dict | None = None) -> tuple[bytes | None, str]:
    """Trae un fichero. Devuelve `(contenido, explicación)`, y `(None, motivo)` si no se pudo."""
    time.sleep(SEGUNDOS_ENTRE_PETICIONES)
    try:
        if datos is None:
            respuesta = cliente.get(url)
        else:
            respuesta = cliente.post(url, data=datos)
    except httpx.HTTPError as error:
        return None, f"no se ha podido llegar ({type(error).__name__}: {error})"
    if respuesta.status_code != 200:
        return None, f"ha contestado {respuesta.status_code}"
    tipo = (respuesta.headers.get("content-type") or "").split(";")[0].strip()
    # **No se mira aquí si lo que llega es un fichero o una página**: de eso se encarga `comprobar`,
    # que es quien sabe qué se estaba pidiendo. Esta función solo trae bytes y dice lo que ha visto.
    # (Un `text/html` con un 200 en una dirección de fichero es la firma de un captcha o de un error
    # del servidor, y `comprobar` lo rechaza.)
    return respuesta.content, f"200 · {tipo or 'sin tipo'}"


def _del_dam(cliente: httpx.Client) -> dict[str, str]:
    """Los ficheros que el MAPA publica para descargar: se **descubren** en su propia página.

    Se descubren y no se escriben a mano porque una ruta escrita a mano es una ruta que un día deja de
    existir sin que nadie se entere. Si un año el MAPA cambia una, aquí se ve.
    """
    import re

    contenido, explicacion = _trae(cliente, PAGINA_DEL_REGISTRO)
    if contenido is None:
        print(f"  FALLO  la página del registro del MAPA: {explicacion}")
        return {}
    enlaces = re.findall(r'href="([^"]+\.xlsx?)"', contenido.decode("utf-8", errors="replace"))
    encontrados: dict[str, str] = {}
    for enlace in enlaces:
        nombre = enlace.rsplit("/", 1)[-1].lower()
        for buscado in DEL_DAM:
            if buscado in nombre:
                encontrados[buscado] = enlace if enlace.startswith("http") else f"https://www.mapa.gob.es{enlace}"
    return encontrados


def _fichero_de_una_pagina(cliente: httpx.Client, url_pagina: str, sufijos: tuple[str, ...]) -> tuple[str | None, str]:
    """Saca de una página oficial el enlace al fichero que busca.

    El FEGA no publica la dirección del PDF: publica una página y el fichero está dentro. Leer el
    enlace es lo que hace que esto siga funcionando cuando publiquen una corrección (los nombres de
    los ficheros llevan la fecha de la corrección, así que cambian).
    """
    import re

    contenido, explicacion = _trae(cliente, url_pagina)
    if contenido is None:
        return None, f"no se ha podido leer la página ({explicacion})"
    texto = contenido.decode("utf-8", errors="replace")
    for enlace in re.findall(r'href="([^"]+)"', texto):
        limpio = enlace.split("?")[0].lower()
        if limpio.endswith(sufijos):
            return (enlace if enlace.startswith("http") else f"https://www.fega.gob.es{enlace}"), explicacion
    return None, f"en la página no hay ningún enlace a {sufijos} (¿habrá cambiado?)"


def baja_todo(cliente: httpx.Client) -> tuple[dict, list[str]]:
    """Baja todo lo permitido. Devuelve la procedencia de cada fichero y la lista de fallos."""
    DESTINO.mkdir(parents=True, exist_ok=True)
    procedencia: dict[str, dict] = {}
    fallos: list[str] = []
    hoy = dt.date.today().isoformat()

    def guarda(
        nombre: str,
        contenido: bytes,
        url: str,
        que_es: str,
        licencia: str,
        visto: str,
        peticion: dict | None = None,
    ) -> None:
        fichero = DESTINO / nombre
        # Se escribe en un temporal y se renombra: si se corta la luz a mitad, no queda un fichero a
        # medias que luego parezca bueno.
        temporal = fichero.with_suffix(fichero.suffix + ".tmp")
        temporal.write_bytes(contenido)
        temporal.replace(fichero)
        procedencia[nombre] = {
            "url": url,
            "que_es": que_es,
            "descargado_el": hoy,
            "bytes": len(contenido),
            "sha256": hashlib.sha256(contenido).hexdigest(),
            "comprobado": visto,
            "licencia": licencia,
        }
        if peticion:
            # **Cómo se pidió, para poder repetirlo.** Las tablas del MAPA no se piden con un GET a
            # una dirección: son un POST con un formulario (`tipoExportacion=Unidades`). Sin esto
            # apuntado, la procedencia no sirve para volver a comprobar la huella mañana —que es
            # justo para lo que está—: `comprobar_fuentes_oficiales.py` necesita saber cómo pedirlo.
            procedencia[nombre]["peticion"] = peticion
        print(f"  OK     {nombre}  ({len(contenido):,} bytes · {visto})")

    print("\n1. Los documentos del FEGA (el diseño del cuaderno)")
    for nombre, datos in FICHEROS_FEGA.items():
        if datos.get("pagina"):
            url, explicacion = _fichero_de_una_pagina(
                cliente, datos["pagina"], (".pdf", ".xlsx", ".docx")
            )
            if url is None:
                print(f"  FALLO  {nombre}: {explicacion}  ({datos['pagina']})")
                fallos.append(f"{nombre}: {explicacion} ({datos['pagina']})")
                continue
        else:
            url = datos["url"]

        contenido, explicacion = _trae(cliente, url)
        if contenido is None:
            print(f"  FALLO  {nombre}: {explicacion}  ({url})")
            fallos.append(f"{nombre}: {explicacion} ({url})")
            continue
        bien, visto = comprobar(contenido, datos["comprobacion"])
        if not bien:
            print(f"  FALLO  {nombre}: {visto}  ({url})")
            fallos.append(f"{nombre}: {visto} ({url})")
            continue
        huella = hashlib.sha256(contenido).hexdigest()
        conocida = datos.get("huella_conocida")
        if conocida and huella != conocida:
            # Este documento es la base del descriptor del cuaderno: si cambia, hay que mirarlo.
            print(f"  FALLO  {nombre}: el FEGA ha publicado otra versión")
            print(f"         esperada {conocida}")
            print(f"         la que hay {huella}")
            fallos.append(f"{nombre}: ha cambiado el documento oficial (huella distinta)")
            continue
        guarda(nombre, contenido, url, datos["que_es"], datos["licencia"], visto)

    print("\n2. Las tablas de codificación del MAPA (buscador de fitosanitarios)")
    for tipo, datos in EXPORTACIONES_MAPA.items():
        contenido, explicacion = _trae(
            cliente, EXPORTADOR_MAPA, {"tipoExportacion": tipo, "dataDto": "{}", "filtros": "{}"}
        )
        if contenido is None:
            print(f"  FALLO  {datos['fichero']}: {explicacion}")
            fallos.append(f"{datos['fichero']}: {explicacion} ({EXPORTADOR_MAPA} {tipo})")
            continue
        bien, visto = comprobar(contenido, "xlsx")
        if not bien:
            print(f"  FALLO  {datos['fichero']}: {visto}")
            fallos.append(f"{datos['fichero']}: {visto}")
            continue
        esperadas = datos.get("filas_esperadas")
        if esperadas is not None and f"{esperadas} filas" not in visto:
            # No es un error: un catálogo puede crecer. Pero tiene que verse, no pasar en silencio.
            print(f"  OJO    {datos['fichero']}: {visto} (el día que se comprobó traía {esperadas})")
        guarda(
            datos["fichero"],
            contenido,
            EXPORTADOR_MAPA,
            datos["que_es"],
            "MAPA. Su aviso legal cita la Ley 37/2007 de reutilización; no declara una licencia concreta",
            visto,
            peticion={"metodo": "POST", "datos": {"tipoExportacion": tipo, "dataDto": "{}", "filtros": "{}"}},
        )

    print("\n3. El listado de productos fitosanitarios registrados")
    contenido, explicacion = _trae(cliente, LISTADO_DE_PRODUCTOS["url"], datos={})
    if contenido is None:
        print(f"  FALLO  {LISTADO_DE_PRODUCTOS['fichero']}: {explicacion}")
        fallos.append(f"{LISTADO_DE_PRODUCTOS['fichero']}: {explicacion} ({LISTADO_DE_PRODUCTOS['url']})")
    else:
        bien, visto = comprobar(contenido, "xlsx")
        if not bien:
            print(f"  FALLO  {LISTADO_DE_PRODUCTOS['fichero']}: {visto}")
            fallos.append(f"{LISTADO_DE_PRODUCTOS['fichero']}: {visto}")
        else:
            guarda(
                LISTADO_DE_PRODUCTOS["fichero"],
                contenido,
                LISTADO_DE_PRODUCTOS["url"],
                LISTADO_DE_PRODUCTOS["que_es"],
                "MAPA. Su aviso legal cita la Ley 37/2007 de reutilización; no declara una licencia concreta",
                visto,
                peticion={"metodo": "POST", "datos": {}},
            )

    print("\n4. Los ficheros que el MAPA publica para descargar (se descubren en su página)")
    for nombre, url in sorted(_del_dam(cliente).items()):
        contenido, explicacion = _trae(cliente, url)
        if contenido is None:
            print(f"  FALLO  {nombre}: {explicacion}  ({url})")
            fallos.append(f"{nombre}: {explicacion} ({url})")
            continue
        bien, visto = comprobar(contenido, "xlsx")
        if not bien:
            print(f"  FALLO  {nombre}: {visto}")
            fallos.append(f"{nombre}: {visto}")
            continue
        guarda(
            f"mapa_{nombre}",
            contenido,
            url,
            DEL_DAM[nombre],
            "MAPA. Su aviso legal cita la Ley 37/2007 de reutilización; no declara una licencia concreta",
            visto,
        )

    return procedencia, fallos


# --------------------------------------------------------------------------
# El LEEME y la procedencia
# --------------------------------------------------------------------------


def escribe_el_leeme(procedencia: dict) -> None:
    """Escribe el LEEME y el JSON de procedencia.

    El LEEME lo escribe el propio guion, y no a mano, por el mismo motivo que en el SIGPAC: si se
    escribe a mano, un día se baja otra cosa y el LEEME sigue contando la anterior.
    """
    (DESTINO / "procedencia.json").write_text(
        json.dumps(
            {
                "_leeme": (
                    "PROCEDENCIA de los ficheros oficiales de esta carpeta. Lo escribe "
                    "scripts/bajar_catalogos_fega.py. No se toca a mano."
                ),
                "descargado_el": dt.date.today().isoformat(),
                "ficheros": dict(sorted(procedencia.items())),
                "no_se_descarga": NO_SE_DESCARGA,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )

    lineas = [
        "# Los catálogos oficiales del cuaderno",
        "",
        "> **Ojo con dos catálogos que se llaman parecido.** La tabla `Unidades` del MAPA (la de esta",
        "> carpeta, del registro de fitosanitarios) **no es** la tabla `UNIDADES_MEDIDA` de SIEX (del",
        "> cuaderno). Una viene del MAPA y la otra del FEGA, y **sus valores no son los mismos**.",
        "",
        "Esta carpeta **no se escribe a mano**: la llena `backend/scripts/bajar_catalogos_fega.py`, que",
        "baja los ficheros oficiales tal y como los publica la administración, comprueba que son lo que",
        "dicen ser y apunta de dónde salen, cuándo y con qué huella. Los tests **no salen a internet**:",
        "leen estos ficheros.",
        "",
        f"**Fecha de la última descarga:** {dt.date.today().strftime('%d/%m/%Y')}.",
        "",
        "## Lo que hay aquí",
        "",
        "| Fichero | Qué es | De dónde sale | Comprobado | SHA-256 |",
        "|---|---|---|---|---|",
    ]
    for nombre, datos in sorted(procedencia.items()):
        lineas.append(
            f"| `{nombre}` | {datos['que_es']} | <{datos['url']}> | {datos['comprobado']} | "
            f"`{datos['sha256']}` |"
        )

    lineas += [
        "",
        "## Lo que NO está aquí, y por qué",
        "",
        "Esto es lo más importante de este documento: **lo que falta se dice, no se rellena**.",
        "",
        "| Dirección | Qué es | Por qué no está |",
        "|---|---|---|",
    ]
    for bloqueado in NO_SE_DESCARGA:
        lineas.append(f"| <{bloqueado['url']}> | {bloqueado['que_es']} | {bloqueado['por_que_no']} |")

    lineas += [
        "",
        "### Los valores de los catálogos de SIEX: pedidos, no saltados",
        "",
        "Los **valores** de los catálogos de SIEX (entre ellos la tabla `UNIDADES_MEDIDA`, que es la que",
        "hace falta para el cuaderno) están detrás de un **captcha de Google** en el portal del FEGA.",
        "**No se pasa**: saltarse un captcha es saltarse la norma de una web, y eso este programa no lo",
        "hace. Lo que sí se tiene es la **estructura** de esos catálogos (los nombres y las columnas de",
        "las 287 tablas), que se baja con `scripts/bajar_catalogos_siex.py` en `data/siex_catalogos.json`.",
        "",
        "Para pedirlos hay un correo ya redactado en [`docs/CORREO_LISTO_PARA_ENVIAR.md`](../../docs/CORREO_LISTO_PARA_ENVIAR.md).",
        "",
        "## Cómo se regenera",
        "",
        "```bash",
        "cd backend",
        "../.venv/Scripts/python.exe scripts/bajar_catalogos_fega.py",
        "```",
        "",
        "Se va **despacio** (una petición cada dos segundos) y con un cliente que se identifica. Si un",
        "fichero no llega, el guion **se para y lo dice** con su dirección y su código HTTP: nunca deja",
        "un fichero de relleno. Con `--sin-descarga` se rehace este LEEME sin tocar la red.",
        "",
        "## Las condiciones de uso de cada fuente",
        "",
        "- **FEGA:** su aviso legal autoriza la reproducción *«siempre que se cite su origen y se difunda",
        "  sin alterar su contenido»*, y añade que si el FEGA exige autorización previa esa autorización",
        "  general no vale. Aquí se cita el origen en cada fila de la tabla de arriba.",
        "- **MAPA:** su aviso legal cita la Ley 37/2007 de reutilización de la información del sector",
        "  público, pero **no declara una licencia concreta**. Se apunta tal cual, sin suponer lo que no",
        "  dice, y se ha preguntado por el ritmo y el permiso a `sgmpagri@mapa.es` (ver el correo).",
        "- **`robots.txt`:** se comprobó el de los tres dominios antes de bajar nada, y ninguna de estas",
        "  direcciones está prohibida. El buscador interno del FEGA (`/search/site`) sí lo está, y **no",
        "  se usa**.",
        "",
    ]
    (DESTINO / "LEEME.md").write_text("\n".join(lineas), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Baja los catálogos oficiales que se pueden bajar.")
    parser.add_argument(
        "--sin-descarga",
        action="store_true",
        help="rehace el LEEME con lo que ya está bajado, sin tocar la red",
    )
    argumentos = parser.parse_args()

    if argumentos.sin_descarga:
        ficheros = sorted(ruta for ruta in DESTINO.glob("*") if ruta.suffix not in (".md", ".json"))
        if not ficheros:
            print(f"No hay nada bajado en {DESTINO}: no se puede rehacer el LEEME.")
            return 1
        procedencia = json.loads((DESTINO / "procedencia.json").read_text(encoding="utf-8"))["ficheros"]
        escribe_el_leeme(procedencia)
        print(f"LEEME rehecho con {len(procedencia)} ficheros, sin tocar la red.")
        return 0

    print(f"Bajando los catálogos oficiales a {DESTINO}")
    with httpx.Client(timeout=ESPERA, follow_redirects=True, headers=CABECERAS) as cliente:
        procedencia, fallos = baja_todo(cliente)

    if procedencia:
        escribe_el_leeme(procedencia)
        print(f"\nApuntados {len(procedencia)} ficheros en procedencia.json y LEEME.md")

    if fallos:
        print(f"\nRESULTADO: {len(fallos)} fuentes no se han podido bajar")
        for fallo in fallos:
            print(f"  - {fallo}")
        return 1
    print("\nRESULTADO: todo lo que se puede bajar, bajado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
