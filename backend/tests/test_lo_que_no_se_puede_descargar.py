"""Lo que vive **al lado** de la carpeta web no se puede descargar por HTTP.

POR QUÉ EXISTE ESTE FICHERO (03/10/2026)
========================================

La aplicación sirve la interfaz montando una carpeta estática en la raíz:

    app.mount("/", StaticFiles(directory=str(RUTA_WEB), html=True), name="web")   # main.py:225
    RUTA_WEB = Path(__file__).resolve().parents[1] / "web"                        # main.py:63

Es decir: **`backend/web` se sirve entera y sin pedir sesión**, que es lo correcto (el que entra
tiene que poder ver la pantalla de entrar). Pero **una carpeta al lado de esa** es `backend/`, y en
`backend/` están:

* `cuedigital.db` — **los datos reales del agricultor**: sus tierras, sus contactos con NIF, su
  cuaderno, sus facturas.
* las copias de seguridad de esa base, que se dejan ahí al migrar.
* el código del servidor (`app/`), las pruebas (`tests/`) y los guiones (`scripts/`).

Hoy **nada de eso se sirve**, y es fácil comprobarlo a mano. Lo que **no había** es nada que lo
exija: el día que alguien cambie esa línea —para servir un fichero de descarga, para probar algo,
para arreglar una ruta— y apunte a `backend/` en vez de a `backend/web`, la base de datos del
agricultor pasa a ser **descargable desde internet con una sola petición**, y **ninguna prueba
existente se pondría roja**. Este fichero es esa prueba.

LO QUE ESTE FICHERO **NO** HACE
===============================

**No lee `cuedigital.db`.** Ni su contenido, ni su tamaño, ni una cabecera: sobre los ficheros
reales **solo se mira el código de estado** de la respuesta, y aun así el cuerpo no se guarda
(`leer_cuerpo=False`). Si algún día uno de estos casos devolviera un 200, esta prueba se pone roja
**sin haber copiado ni un byte de los datos del agricultor** a ningún sitio. Los únicos bytes que
se comparan son los de una base de datos **inventada** dentro de una carpeta temporal.

Y **no sustituye a la comprobación de verdad contra un servidor de verdad**: aquí se llama a la
aplicación ASGI directamente, sin uvicorn por medio. Lo que se prueba es la ruta y el montaje —que
es donde estaría el fallo—, no el servidor completo. Eso se mira con
`scripts/comprobar_en_un_navegador.py` y `scripts/humo.py`.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import main

# `backend/`, que es la carpeta que hay que mantener fuera de internet: ahí viven la base de datos
# del agricultor y su código.
RAIZ_DEL_BACKEND = Path(main.__file__).resolve().parents[1]

# Lo primero que escribe un fichero SQLite. Si estos bytes salen en el cuerpo de una respuesta, lo
# que se ha servido es una base de datos.
CABECERA_DE_UN_SQLITE = b"SQLite format 3\x00"

# Rutas escritas **a mano y en crudo**, sin dejar que nadie las normalice antes: son las formas en
# las que se intenta salir de una carpeta por HTTP. Se prueban todas porque un servidor puede
# decidir normalizar `%2e%2e` y otro no, y la respuesta tiene que ser la misma en los dos casos:
# nada.
RUTAS_DE_SALIDA = [
    "/../cuedigital.db",
    "/..%2Fcuedigital.db",
    "/%2e%2e%2Fcuedigital.db",
    "/%2e%2e/cuedigital.db",
    "/web/../cuedigital.db",
    "/web/../../cuedigital.db",
    "/./../cuedigital.db",
    "//../cuedigital.db",
    "/..%5Ccuedigital.db",
]


def _pedir_al_asgi(app, ruta: str, *, leer_cuerpo: bool = True) -> tuple[int, bytes]:
    """Pide `ruta` **tal cual** a la aplicación ASGI y devuelve `(estado, cuerpo)`.

    Se llama a la aplicación a pelo, y no con un cliente HTTP, por un motivo concreto: **los
    clientes normales normalizan la ruta** (quitan los `..` siguiendo la norma de las URLs) antes
    de mandarla. Si se usara uno, `/../cuedigital.db` llegaría al servidor convertido en
    `/cuedigital.db`, y esta prueba estaría comprobando una petición distinta de la que dice
    comprobar. Aquí se construye el mensaje ASGI a mano para que la ruta llegue **como se escribió**.

    `leer_cuerpo=False` **no acumula el cuerpo**: es lo que se usa con las rutas reales, para que
    ni siquiera en el caso de un fallo se copien a memoria datos del agricultor.
    """
    mensajes: list[dict] = []
    trozos = bytearray()

    async def recibir() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def enviar(mensaje: dict) -> None:
        mensajes.append(mensaje)
        if leer_cuerpo and mensaje["type"] == "http.response.body":
            trozos.extend(mensaje.get("body", b""))

    alcance = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        # `raw_path` va en crudo a propósito: es el que usan los servidores de verdad.
        "path": ruta,
        "raw_path": ruta.encode("utf-8"),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"prueba.local")],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 80),
    }

    asyncio.run(app(alcance, recibir, enviar))

    arranques = [m for m in mensajes if m["type"] == "http.response.start"]
    assert arranques, f"la aplicación no contestó nada a {ruta!r}"
    return arranques[0]["status"], bytes(trozos)


@pytest.mark.parametrize("ruta", RUTAS_DE_SALIDA)
def test_no_se_puede_salir_de_la_carpeta_web_por_la_ruta(ruta: str) -> None:
    """Ni con `..`, ni con `%2e%2e`, ni con barras dobles: no se sale de `web`."""
    estado, _ = _pedir_al_asgi(main.app, ruta, leer_cuerpo=False)
    assert estado in (403, 404), (
        f"{ruta!r} ha contestado {estado}. Una ruta con `..` no puede llegar a un fichero de fuera "
        f"de la carpeta de la interfaz."
    )


def test_las_paginas_de_la_interfaz_si_se_sirven() -> None:
    """**El control, y sin él lo de arriba no valdría nada.**

    Si el montaje de la carpeta web no existiera —porque la carpeta no está, porque el montaje se
    ha movido o porque algo lo ha roto—, **todas** las rutas de arriba contestarían 404 y las
    pruebas pasarían igual de verdes. Esta prueba exige que la interfaz **sí** se esté sirviendo,
    para que el 404 de las otras signifique «no está ahí» y no «no hay nada montado».
    """
    estado, cuerpo = _pedir_al_asgi(main.app, "/index.html")
    assert estado == 200, "la carpeta de la interfaz no se está sirviendo: los 404 no probarían nada"
    assert b"<" in cuerpo, "lo servido en /index.html no parece una página"

    # Y el JavaScript, que es el otro fichero del que depende que la aplicación arranque.
    estado_js, _ = _pedir_al_asgi(main.app, "/app.js", leer_cuerpo=False)
    assert estado_js == 200, "app.js no se sirve"


def test_ningun_fichero_de_al_lado_de_la_web_se_sirve() -> None:
    """**El guardián de verdad**: todo lo que hay en `backend/` deja de ser alcanzable por HTTP.

    Se hace **recorriendo la carpeta**, no con una lista escrita a mano: así, el día que alguien
    deje ahí otra copia de la base de datos —o un volcado, o un fichero de claves—, **la prueba se
    pone roja sola**, sin que nadie se acuerde de añadirlo a una lista.

    Y se prueban también las carpetas del código (`app/`, `tests/`, `scripts/`): servir el código
    del servidor no es tan grave como servir la base de datos, pero tampoco se sirve.
    """
    assert RAIZ_DEL_BACKEND.is_dir(), "no se encuentra la carpeta del backend"

    sospechosos: list[str] = []

    # (a) los ficheros sueltos de `backend/`: la base de datos, sus copias y todo lo demás.
    for fichero in sorted(RAIZ_DEL_BACKEND.iterdir()):
        if fichero.is_file():
            sospechosos.append("/" + fichero.name)

    # (b) una muestra de las carpetas del código, que no están dentro de `web`.
    for ruta_de_codigo in ("/app/main.py", "/app/models.py", "/tests/conftest.py", "/scripts/humo.py"):
        if (RAIZ_DEL_BACKEND / ruta_de_codigo.lstrip("/")).is_file():
            sospechosos.append(ruta_de_codigo)

    assert sospechosos, "no se ha encontrado nada que comprobar: la prueba no estaría probando nada"

    servidos = []
    for ruta in sospechosos:
        estado, _ = _pedir_al_asgi(main.app, ruta, leer_cuerpo=False)
        if estado == 200:
            servidos.append((ruta, estado))

    assert not servidos, (
        "hay ficheros de `backend/` que se están sirviendo por HTTP: "
        + ", ".join(f"{ruta} -> {estado}" for ruta, estado in servidos)
        + ". La base de datos del agricultor y el código del servidor no pueden estar detrás de una "
        "URL pública."
    )


def test_el_montaje_equivocado_si_serviria_la_base_de_datos(tmp_path: Path) -> None:
    """Prueba que lo de arriba **no es una prueba que pasa sola**.

    Aquí se monta la misma aplicación dos veces, con **dos carpetas distintas y ningún dato real**:

    1. como está de verdad —montando `web`—, y el fichero de al lado **no** se sirve;
    2. con el fallo que se teme —montando la carpeta **de arriba**, que es `backend/`—, y el mismo
       fichero **sí** se sirve, con su cabecera de SQLite y todo.

    Es la diferencia entre las dos lo que demuestra que el 404 del caso bueno es una propiedad del
    programa y no un descuido de la prueba. Si alguien cambia la línea del montaje, esta prueba
    sigue verde (prueba el mecanismo, no el fichero) pero **la de arriba se pone roja**, que es lo
    que tiene que pasar.
    """
    raiz = tmp_path / "backend_de_mentira"
    web = raiz / "web"
    web.mkdir(parents=True)
    (web / "index.html").write_text("<html>la interfaz</html>", encoding="utf-8")
    # Una base de datos inventada: los únicos bytes que esta prueba compara.
    (raiz / "cuedigital.db").write_bytes(CABECERA_DE_UN_SQLITE + b"datos inventados, de mentira")

    def _montaje(directorio: Path) -> FastAPI:
        una = FastAPI()
        una.mount("/", StaticFiles(directory=str(directorio), html=True), name="web")
        return una

    # 1. Como está el programa de verdad: la carpeta de la interfaz. Lo de al lado, no se sirve.
    estado_bueno, _ = _pedir_al_asgi(_montaje(web), "/cuedigital.db", leer_cuerpo=False)
    assert estado_bueno == 404, "montando la carpeta web no se puede servir un fichero de al lado"
    estado_pagina, cuerpo_pagina = _pedir_al_asgi(_montaje(web), "/index.html")
    assert estado_pagina == 200 and b"la interfaz" in cuerpo_pagina

    # 2. El fallo que se teme: montar la carpeta de arriba. Entonces sí sale, y sale la base entera.
    estado_malo, cuerpo_malo = _pedir_al_asgi(_montaje(raiz), "/cuedigital.db")
    assert estado_malo == 200, (
        "montando la carpeta de arriba, un fichero de al lado tendría que servirse: si esto no "
        "pasa, la prueba de arriba no demuestra nada"
    )
    assert cuerpo_malo.startswith(CABECERA_DE_UN_SQLITE), (
        "lo servido con el montaje equivocado no parece una base de datos de SQLite"
    )


def test_lo_que_sirve_la_web_no_es_una_base_de_datos() -> None:
    """Y una comprobación que no depende de nombres: **ninguna** respuesta es un SQLite.

    Recorre unas cuantas rutas —las de la interfaz y las de al lado— y exige que ninguna empiece
    por la cabecera de SQLite. Es una red de seguridad por si algún día se sirve la base con otro
    nombre o desde otra ruta que hoy no se le ocurre a nadie.
    """
    for ruta in ["/", "/index.html", "/app.js", "/cuedigital.db", "/../cuedigital.db"]:
        _, cuerpo = _pedir_al_asgi(main.app, ruta)
        assert not cuerpo.startswith(CABECERA_DE_UN_SQLITE), (
            f"lo que se sirve en {ruta!r} es una base de datos de SQLite"
        )
