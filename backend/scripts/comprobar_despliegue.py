"""Comprobar un despliegue de CUE Digital, en local o en la URL pública de verdad.

**Para qué existe.** El despliegue no se puede dar por bueno porque los contenedores estén
arriba: hay que recorrer lo que hace un agricultor y lo que mira quien mantiene el programa.
Este guion hace ese recorrido con `httpx` y contesta con **código 0 o 1**, así que sirve igual
para mirarlo a mano que para pegarlo en una comprobación.

Uso (desde `backend/`):

    ../.venv/Scripts/python.exe scripts/comprobar_despliegue.py http://127.0.0.1:8090
    ../.venv/Scripts/python.exe scripts/comprobar_despliegue.py https://cuaderno.tu-dominio.es

Qué recorre, en orden, y por qué cada cosa:

1. **`/health`** — que el proceso atiende (ojo: `/health` **no** consulta la base, ver
   `docs/DESPLIEGUE.md`).
2. **La pantalla** — `/`, `app.js` y `estilos.css` con su tipo MIME. Un `.js` servido como
   `text/plain` deja la pantalla en blanco sin decir por qué (es la trampa de Windows que ya
   está documentada en `AGENTS.md`).
3. **Alta de cuenta** (o entrar si ya existe) y `GET /api/cuenta/yo` con el vale.
4. **Dos tierras, con las dos formas de referencia que usa el agricultor**:
   - la del visor del SIGPAC, **seis números**: `37-70-0-0-503-51`;
   - la completa, **con recinto**: `37-70-0-0-503-51-1`.
   Se comprueba que los códigos (INE, polígono, parcela, recinto) salen de la propia
   referencia: es lo que hace que después el mapa pueda poner el contorno (IMP-25).
5. **El contorno y la foto de la tierra** — se rellena la forma con el GeoPackage cacheado
   (`POST /api/sigpac/cache/37/contornos?campana=2026`, si está descargado) y se pide
   `GET /api/mapa/tierra/{id}.png`. Se aceptan las dos respuestas honestas: **200 con un PNG
   de 800×600**, o **409 con su motivo** (la tierra no tiene forma guardada). Un **503** es
   un fallo: significa que el servidor no ha podido traer la ortofoto.
6. **La observabilidad** — `POST /api/observabilidad/pantalla` (204), y
   `GET /api/observabilidad/resumen`:
   - con `CUEDIGITAL_OBSERVABILIDAD_TOKEN` en el entorno de quien lanza esto, se pide con la
     cabecera `X-Observabilidad: <token>` y se exige **200**; sin cabecera y con una cabecera
     mala, **403**;
   - sin esa variable en el entorno, se exige **404** (la puerta no existe, que es lo correcto
     cuando el servidor no la ha configurado).
   El resumen tiene que traer **errores, pantallas y embudo**, y el embudo tiene que medirse
   entero: eso es lo que demuestra que hay SQL de verdad contra PostgreSQL.

**Lo que NO comprueba, y se dice para no dar una falsa seguridad:** las subidas de ficheros,
el OCR, el IUWS y la firma. Eso tiene su recorrido en `scripts/humo.py`, que necesita una base
de datos limpia.

Sin dependencias nuevas: `httpx` ya está en `backend/requirements.txt`.
"""

from __future__ import annotations

import datetime as dt
import os
import struct
import sys
import time

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8090").rstrip("/")

# Las cuentas de la comprobación. Se pueden cambiar por entorno para no reutilizar siempre la
# misma; los valores por defecto son de prueba y no son de nadie.
CORREO = os.environ.get("CUEDIGITAL_PRUEBA_CORREO", "comprobacion@despliegue.test")
CLAVE = os.environ.get("CUEDIGITAL_PRUEBA_CLAVE", "una-clave-larga-de-verdad")
NIF = os.environ.get("CUEDIGITAL_PRUEBA_NIF", "00000000T")
EXPLOTACION = os.environ.get("CUEDIGITAL_PRUEBA_EXPLOTACION", "La prueba del despliegue")

# La referencia del recinto real de Salamanca que usa el proyecto (está en los datos del
# SIGPAC y en la documentación): seis números en el visor y siete con el recinto.
REFERENCIA_DEL_VISOR = "37-70-0-0-503-51"
REFERENCIA_CON_RECINTO = "37-70-0-0-503-51-1"
PROVINCIA_DEL_MAPA = 37
CAMPANA_DEL_MAPA = 2026

# La cabecera de la observabilidad (la misma que `app/observabilidad.py`).
CABECERA_DEL_RESUMEN = "X-Observabilidad"
VARIABLE_DEL_TOKEN = "CUEDIGITAL_OBSERVABILIDAD_TOKEN"

FALLOS: list[str] = []
AVISOS: list[str] = []


def comprobar(condicion: bool, descripcion: str, detalle: str = "") -> bool:
    """Apunta el resultado de una comprobación y lo imprime en castellano."""
    marca = "OK  " if condicion else "FALLO"
    linea = f"  [{marca}] {descripcion}"
    if detalle and not condicion:
        linea += f" — {detalle}"
    print(linea)
    if not condicion:
        FALLOS.append(f"{descripcion}{f' — {detalle}' if detalle else ''}")
    return condicion


def aviso(texto: str) -> None:
    """Algo que no es un fallo pero que hay que leer."""
    print(f"  [AVISO] {texto}")
    AVISOS.append(texto)


def _detalle(respuesta: httpx.Response) -> str:
    """El motivo que ha dado el servidor, corto y en una línea."""
    try:
        cuerpo = respuesta.json()
    except ValueError:
        return (respuesta.text or "").strip()[:200]
    if isinstance(cuerpo, dict):
        return str(cuerpo.get("detail") or cuerpo)[:300]
    return str(cuerpo)[:300]


def _medidas_del_png(contenido: bytes) -> tuple[int, int] | None:
    """Ancho y alto de un PNG, leyendo su cabecera (sin Pillow ni nada que instalar).

    La firma son ocho bytes fijos y la primera parte (IHDR) lleva el ancho y el alto en dos
    enteros de cuatro bytes, en orden de red. Si no es un PNG, `None`.
    """
    if len(contenido) < 24 or not contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    if contenido[12:16] != b"IHDR":
        return None
    ancho, alto = struct.unpack(">II", contenido[16:24])
    return ancho, alto


def _esperar_a_que_atienda(cliente: httpx.Client, segundos: int = 90) -> bool:
    """Espera a que `/health` conteste. En un despliegue recién arrancado tarda."""
    limite = dt.datetime.now() + dt.timedelta(seconds=segundos)
    while dt.datetime.now() < limite:
        try:
            if cliente.get("/health").status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(2)
    return False


def _alta_o_entrada(cliente: httpx.Client) -> str | None:
    """Da de alta la cuenta de la comprobación, o entra si ya existe. Devuelve el vale."""
    alta = cliente.post(
        "/api/cuenta/registro",
        json={
            "explotacion": {"nombre": EXPLOTACION, "nif": NIF},
            "nombre": "Comprobación del despliegue",
            "correo": CORREO,
            "clave": CLAVE,
        },
    )
    if alta.status_code == 409:
        # La cuenta ya está de una comprobación anterior: se entra, que es lo mismo que hará
        # quien repita el recorrido.
        alta = cliente.post("/api/cuenta/entrar", json={"correo": CORREO, "clave": CLAVE})
    comprobar(
        alta.status_code in (200, 201),
        "la cuenta se da de alta (o se entra en la que ya existe)",
        f"{alta.status_code} {_detalle(alta)}",
    )
    if alta.status_code not in (200, 201):
        return None
    vale = alta.json().get("token")
    comprobar(bool(vale), "la respuesta trae el vale de la sesión")
    return vale


def _crear_tierra(cliente: httpx.Client, cabeceras: dict, alias: str, referencia: str) -> dict | None:
    """Da de alta una tierra solo con su referencia y devuelve lo que ha contestado el servidor."""
    respuesta = cliente.post(
        "/api/parcelas",
        headers=cabeceras,
        json={"alias": alias, "ref_sigpac": referencia},
    )
    comprobar(
        respuesta.status_code == 201,
        f"se da de alta la tierra «{alias}» con la referencia {referencia}",
        f"{respuesta.status_code} {_detalle(respuesta)}",
    )
    return respuesta.json() if respuesta.status_code == 201 else None


def _comprobar_la_foto(
    cliente: httpx.Client, cabeceras: dict, tierra: dict | None, etiqueta: str
) -> None:
    """Pide la foto de una tierra y acepta las dos respuestas honestas: PNG 800×600 o 409."""
    if not tierra:
        return
    respuesta = cliente.get(f"/api/mapa/tierra/{tierra['id']}.png", headers=cabeceras)
    if respuesta.status_code == 200:
        tipo = respuesta.headers.get("content-type", "")
        comprobar("image/png" in tipo, f"{etiqueta}: la foto de una tierra es un PNG", tipo)
        medidas = _medidas_del_png(respuesta.content)
        comprobar(
            medidas == (800, 600),
            f"{etiqueta}: la foto es de 800×600",
            f"medidas leídas: {medidas}",
        )
    elif respuesta.status_code == 409:
        motivo = _detalle(respuesta)
        comprobar(bool(motivo), f"{etiqueta}: sin forma, y el 409 dice el motivo", motivo)
        print(f"           motivo del 409: {motivo}")
    elif respuesta.status_code == 503:
        comprobar(False, f"{etiqueta}: el servidor no ha podido traer la ortofoto (503)", _detalle(respuesta))
    else:
        comprobar(False, f"{etiqueta}: la foto de la tierra contesta algo que no se espera",
                  f"{respuesta.status_code} {_detalle(respuesta)}")


def _rellenar_los_contornos(cliente: httpx.Client, cabeceras: dict) -> set[int]:
    """Rellena las formas con el GeoPackage cacheado. Devuelve los ids que se han actualizado.

    Si la caché del SIGPAC no está descargada en el servidor, esto **no es un fallo**: es una
    descarga de 628 MB que se hace aparte. Se avisa y se sigue, porque la comprobación de la
    foto ya acepta el 409 con su motivo.
    """
    respuesta = cliente.post(
        f"/api/sigpac/cache/{PROVINCIA_DEL_MAPA}/contornos",
        headers=cabeceras,
        params={"campana": CAMPANA_DEL_MAPA},
    )
    if respuesta.status_code != 200:
        aviso(
            "no se han podido rellenar los contornos desde el mapa del SIGPAC "
            f"({respuesta.status_code}: {_detalle(respuesta)}). La comprobación de la foto "
            "sigue, y el 409 con su motivo también vale."
        )
        return set()
    datos = respuesta.json()
    print(
        "           contornos: "
        f"{len(datos.get('actualizadas', []))} con forma, "
        f"{len(datos.get('sin_forma', []))} sin forma, "
        f"{len(datos.get('no_encontradas', []))} no encontradas, "
        f"{len(datos.get('sin_codigos', []))} sin códigos"
    )
    for fila in datos.get("sin_codigos", []):
        print(f"           · «{fila.get('alias')}»: {fila.get('motivo')}")
    return {fila["id"] for fila in datos.get("actualizadas", []) if "id" in fila}


def _comprobar_la_observabilidad(cliente: httpx.Client) -> None:
    """El aviso de pantalla y el resumen: 204, 200 con token, 403 con cabecera mala / 404 sin token."""
    print("\n6. La observabilidad")
    aviso_de_pantalla = cliente.post("/api/observabilidad/pantalla", json={"pantalla": "hoy"})
    comprobar(
        aviso_de_pantalla.status_code == 204,
        "el aviso de pantalla contesta 204",
        f"{aviso_de_pantalla.status_code}",
    )
    # Un cuerpo roto tampoco puede contestar 5xx: es un aviso de un móvil, no una petición.
    basura = cliente.post(
        "/api/observabilidad/pantalla",
        content=b"esto no es un aviso",
        headers={"Content-Type": "application/json"},
    )
    comprobar(
        basura.status_code == 204,
        "un aviso con el cuerpo roto sigue contestando 204",
        f"{basura.status_code} {_detalle(basura)}",
    )

    token = os.environ.get(VARIABLE_DEL_TOKEN, "").strip()
    if not token:
        respuesta = cliente.get("/api/observabilidad/resumen")
        comprobar(
            respuesta.status_code == 404,
            "sin token configurado en el servidor, el resumen no existe (404)",
            f"{respuesta.status_code} {_detalle(respuesta)}",
        )
        aviso(
            "no se ha comprobado el resumen con token porque no está "
            f"{VARIABLE_DEL_TOKEN} en el entorno de quien lanza esto."
        )
        return

    cabecera_buena = {CABECERA_DEL_RESUMEN: token}
    respuesta = cliente.get("/api/observabilidad/resumen", headers=cabecera_buena)
    if not comprobar(
        respuesta.status_code == 200,
        "el resumen se lee con la cabecera buena (200)",
        f"{respuesta.status_code} {_detalle(respuesta)}",
    ):
        return
    datos = respuesta.json()
    for clave in ("errores_recientes", "pantallas", "rutas", "embudo", "memoria"):
        comprobar(clave in datos, f"el resumen trae «{clave}»")

    # El aviso de pantalla que se acaba de mandar tiene que estar contado. En un servidor con
    # un solo proceso uvicorn (lo que despliega `deploy/docker-compose.yml`) es el mismo
    # proceso que lo atendió; si algún día se pusieran varios, esto podría no cuadrar.
    pantallas = datos.get("pantallas") or []
    vistas = [fila for fila in pantallas if fila.get("pantalla") == "hoy"]
    comprobar(
        bool(vistas) and (vistas[0].get("veces") or 0) >= 1,
        "el aviso de pantalla «hoy» está contado en el resumen",
        f"pantallas: {pantallas}",
    )

    embudo = datos.get("embudo") or {}
    etapas = embudo.get("etapas") or []
    fallos = embudo.get("fallos") or []
    comprobar(
        len(etapas) == 5,
        "el embudo trae sus cinco etapas",
        f"etapas: {len(etapas)}",
    )
    comprobar(
        not fallos,
        "el embudo se ha medido entero contra la base de datos (ninguna etapa en «no se sabe»)",
        f"fallos: {fallos}",
    )
    if etapas:
        print("           embudo (fincas distintas por etapa):")
        for etapa in etapas:
            print(f"           · {etapa.get('que_es')}: {etapa.get('cuenta')}")

    errores = datos.get("errores_recientes") or []
    rutas = datos.get("rutas") or []
    print(
        f"           errores guardados: {len(errores)} · "
        f"rutas medidas: {len(rutas)} · "
        f"pantallas contadas: {len(pantallas)}"
    )
    if rutas:
        la_mas_usada = rutas[0]
        print(
            f"           ruta más usada: {la_mas_usada.get('ruta')} "
            f"({la_mas_usada.get('peticiones')} peticiones, "
            f"p95 {la_mas_usada.get('p95_ms')} ms)"
        )

    # La puerta sin llave: 403. Y con una cabecera que no vale, también.
    sin_cabecera = cliente.get("/api/observabilidad/resumen")
    comprobar(
        sin_cabecera.status_code == 403,
        "el resumen sin cabecera contesta 403",
        f"{sin_cabecera.status_code} {_detalle(sin_cabecera)}",
    )
    cabecera_mala = {CABECERA_DEL_RESUMEN: token + "-esto-no-vale"}
    con_cabecera_mala = cliente.get("/api/observabilidad/resumen", headers=cabecera_mala)
    comprobar(
        con_cabecera_mala.status_code == 403,
        "el resumen con una cabecera mala contesta 403",
        f"{con_cabecera_mala.status_code} {_detalle(con_cabecera_mala)}",
    )


def main() -> int:
    print(f"Comprobación del despliegue de CUE Digital contra {BASE}")
    print(f"Fecha: {dt.datetime.now():%d/%m/%Y %H:%M:%S}")
    cliente = httpx.Client(base_url=BASE, timeout=60.0)

    print("\n1. El servidor está en pie")
    if not comprobar(_esperar_a_que_atienda(cliente), "GET /health contesta 200"):
        print("\nEl servidor no ha contestado. No se puede seguir.")
        return 1
    salud = cliente.get("/health").json()
    comprobar(salud.get("estado") == "ok", "el estado es ok", str(salud))
    comprobar(
        salud.get("zonas_vulnerables_cargadas") is True,
        "el listado oficial de zonas vulnerables está cargado",
    )

    print("\n2. La pantalla del agricultor")
    portada = cliente.get("/")
    comprobar(portada.status_code == 200, "la portada se sirve")
    comprobar("text/html" in portada.headers.get("content-type", ""), "la portada es HTML")
    for fichero, tipo in (("app.js", "javascript"), ("estilos.css", "text/css")):
        respuesta = cliente.get(f"/{fichero}")
        comprobar(
            respuesta.status_code == 200 and tipo in respuesta.headers.get("content-type", ""),
            f"{fichero} se sirve como {tipo}",
            f"{respuesta.status_code} {respuesta.headers.get('content-type')}",
        )

    print("\n3. La cuenta y la sesión")
    vale = _alta_o_entrada(cliente)
    if not vale:
        print("\nSin cuenta no se puede seguir. No se puede comprobar el resto.")
        return 1
    cabeceras = {"Authorization": f"Bearer {vale}"}
    yo = cliente.get("/api/cuenta/yo", headers=cabeceras)
    comprobar(yo.status_code == 200, "el vale sirve para leer la cuenta (GET /api/cuenta/yo)",
              f"{yo.status_code} {_detalle(yo)}")

    print("\n4. Dos tierras, con las dos formas de referencia")
    marca_de_tiempo = dt.datetime.now().strftime("%H:%M:%S")
    tierra_visor = _crear_tierra(
        cliente, cabeceras, f"Comprobación seis números ({marca_de_tiempo})", REFERENCIA_DEL_VISOR
    )
    if tierra_visor:
        comprobar(
            tierra_visor.get("codigo_ine") == "37070",
            "de la referencia de seis números salen los códigos del municipio (37070)",
            f"codigo_ine: {tierra_visor.get('codigo_ine')}",
        )
        comprobar(
            tierra_visor.get("poligono") == 503 and tierra_visor.get("numero_parcela") == 51,
            "de la referencia salen el polígono (503) y la parcela (51)",
            f"polígono: {tierra_visor.get('poligono')}, parcela: {tierra_visor.get('numero_parcela')}",
        )
        comprobar(
            tierra_visor.get("numero_recinto") is None,
            "la referencia de seis números no inventa el recinto (se queda en «no lo sé»)",
            f"numero_recinto: {tierra_visor.get('numero_recinto')}",
        )

    tierra_completa = _crear_tierra(
        cliente, cabeceras, f"Comprobación con recinto ({marca_de_tiempo})", REFERENCIA_CON_RECINTO
    )
    if tierra_completa:
        comprobar(
            tierra_completa.get("numero_recinto") == 1,
            "de la referencia completa sale el recinto (1)",
            f"numero_recinto: {tierra_completa.get('numero_recinto')}",
        )
        comprobar(
            tierra_completa.get("codigo_ine") == "37070",
            "y también los códigos del municipio (37070)",
            f"codigo_ine: {tierra_completa.get('codigo_ine')}",
        )

    print("\n5. El contorno y la foto de la tierra")
    con_forma = _rellenar_los_contornos(cliente, cabeceras)
    if tierra_completa and tierra_completa["id"] in con_forma:
        print("           la tierra con recinto ha recibido su forma del GeoPackage")
    _comprobar_la_foto(cliente, cabeceras, tierra_completa, "tierra con recinto")
    # La de seis números: si esa parcela tiene un solo recinto, también recibe forma; si tiene
    # varios, el servidor dice que hay que elegir y la foto contesta 409. Las dos cosas valen.
    _comprobar_la_foto(cliente, cabeceras, tierra_visor, "tierra de seis números")

    _comprobar_la_observabilidad(cliente)

    print("\n" + "=" * 72)
    if AVISOS:
        print(f"Avisos ({len(AVISOS)}), que no son fallos:")
        for texto in AVISOS:
            print(f"  · {texto}")
    if FALLOS:
        print(f"RESULTADO: {len(FALLOS)} comprobación(es) han fallado:")
        for texto in FALLOS:
            print(f"  · {texto}")
        return 1
    print("RESULTADO: todo lo comprobado ha ido bien.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
