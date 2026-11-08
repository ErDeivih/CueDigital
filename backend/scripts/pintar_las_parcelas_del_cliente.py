"""**Un cliente con parcelas de verdad: sus contornos del SIGPAC y su mapa** (IMP-23, 08/11/2026).

Lo que prueba, y por qué hacía falta: hasta ahora el GeoPackage real se había probado con recintos
sueltos y con la finca de ejemplo, que **no tiene los códigos del SIGPAC completos** (sus 21 tierras
salen en «sin códigos»). Lo que David pide es la escena de verdad: **un cliente con sus referencias,
sus tierras y su mapa**.

Este script lo monta entero y sin servidores ni internet:

1. **Crea una base de datos temporal** (no toca la del proyecto) y da de alta un cliente con **tres
   parcelas cuyas referencias existen**: la conocida `37-70-0-0-503-51-1` y otras dos **sacadas del
   GeoPackage real de Salamanca** (`37-70-0-0-501-84-1` y `37-70-0-0-501-82-2`). Nada inventado: los
   códigos, la forma y la superficie salen del fichero del FEGA que ya está en la caché.
2. **Llama a `POST /api/sigpac/cache/37/contornos`** y comprueba que las tres casan, que la geometría
   queda escrita y que es **exactamente** la que devuelve el lector del GeoPackage.
3. **Pide el mapa de cada tierra** (`GET /api/mapa/tierra/{id}.png`). Ese endpoint necesita la
   ortofoto del IGN; por eso el script, **por defecto, no sale a internet**: se le hace al programa
   creer que no hay cobertura (igual que en los tests y como en el campo, sin datos), el endpoint
   contesta **503** y el script lo dice. En ese caso compone la imagen con **el contorno real dibujado
   por el propio programa** (`mapa_de_una_tierra.dibujar_el_contorno`, el mismo que usa la ficha de la
   tierra) sobre un fondo neutro, para que se puedan ver las formas igualmente. Con `--con-red` sí se
   piden las ortofotos de verdad y el montaje las lleva.
4. **Guarda el montaje** en `docs/capturas-nuevo/` y saca una tabla. El nombre del fichero dice de
   qué es: `cliente-contornos-sin-red.png` (contornos sobre fondo neutro) o `cliente-contornos.png`
   (ortofoto con el contorno encima).

## Códigos de salida (para que no haya dudas de qué ha pasado)

  · **0** — las tres parcelas casan, el WKT es el del lector y **hay imagen** (la del servidor, o el
    montaje de contornos si no hay red).
  · **1** — alguna parcela no casa o su geometría no es la del lector. Es un fallo de verdad.
  · **2** — no está el GeoPackage en la caché: no se ha podido probar nada.
  · **3** — las parcelas están bien pero no se ha podido componer ninguna imagen.

Uso:

    ..\\.venv\\Scripts\\python.exe scripts/pintar_las_parcelas_del_cliente.py
    ..\\.venv\\Scripts\\python.exe scripts/pintar_las_parcelas_del_cliente.py --con-red
"""

from __future__ import annotations

import argparse
import io
import math
import os
import pathlib
import sys
import tempfile
import time

RAIZ = pathlib.Path(__file__).resolve().parents[1]  # backend/
PROYECTO = RAIZ.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# **La base de datos y los adjuntos van a una carpeta temporal, siempre**: este script da de alta un
# cliente y no puede escribir en la base del proyecto. La caché del SIGPAC **no** se toca: se usa la
# de verdad (`datos/sigpac_cache`), que es el fichero que se quiere probar.
TEMPORAL = pathlib.Path(tempfile.mkdtemp(prefix="cliente_contornos_"))
os.environ["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{(TEMPORAL / 'cliente.db').as_posix()}"
os.environ["CUEDIGITAL_ADJUNTOS"] = str(TEMPORAL / "adjuntos")
os.environ["CUEDIGITAL_SECRETO"] = "secreto-solo-para-esta-prueba-1234567890"
os.environ["CUEDIGITAL_ZV_CYL_RUTA"] = str(TEMPORAL / "zv_no_cargado.csv")
os.environ["CUEDIGITAL_ENTORNO"] = "pruebas"
os.environ["CUEDIGITAL_ITERACIONES_PBKDF2"] = "1000"

from fastapi.testclient import TestClient  # noqa: E402

from app import geopackage_sigpac, mapa_de_una_tierra, models, sigpac, sigpac_cache  # noqa: E402
from app.database import SessionLocal, crear_tablas  # noqa: E402
from app.main import app  # noqa: E402

PROVINCIA = 37
MUNICIPIO = 70  # Calvarrasa de Arriba
CAMPANA = 2026
# La conocida (está en `data/sigpac/recinto_de_ejemplo_503_51.json`) y tres sacadas del GeoPackage
# real de Salamanca, copiadas de la tabla `recinto` del fichero. **No son inventadas.**
# La última se da de alta **solo con la referencia**, como haría el agricultor que copia el papel:
# es la prueba de IMP-25 (antes se quedaba sin códigos y sin contorno).
RECINTOS = [
    {"poligono": 503, "parcela": 51, "recinto": 1, "alias": "El Prado"},
    {"poligono": 501, "parcela": 84, "recinto": 1, "alias": "El Alto"},
    {"poligono": 501, "parcela": 82, "recinto": 2, "alias": "La Vega"},
    {"poligono": 501, "parcela": 80, "recinto": 1, "alias": "Las Eras", "solo_referencia": True},
]
SALIDA_CON_RED = PROYECTO / "docs" / "capturas-nuevo" / "cliente-contornos.png"
SALIDA_SIN_RED = PROYECTO / "docs" / "capturas-nuevo" / "cliente-contornos-sin-red.png"
ANCHO, ALTO = 480, 360
MARGEN = 14
COLOR_FONDO = (247, 245, 238)
COLOR_TEXTO = (44, 44, 40)
COLOR_SUAVE = (120, 116, 106)
COLOR_CABECERA = (255, 255, 255)


# --------------------------------------------------------------------------- utilidades


def _referencia(recinto: dict) -> str:
    """La referencia como la escribe el SIGPAC y como la guarda la parcela: siete números con guiones."""
    return f"{PROVINCIA}-{MUNICIPIO}-0-0-{recinto['poligono']}-{recinto['parcela']}-{recinto['recinto']}"


def _referencia_del_visor(recinto: dict) -> str:
    return f"{PROVINCIA}:{MUNICIPIO}:0:0:{recinto['poligono']}:{recinto['parcela']}"


def _para(titulo: str = "") -> None:
    print()
    if titulo:
        print(f"== {titulo} ==")


def _tabla(filas: list[tuple[str, str]]) -> None:
    ancho = max(len(etiqueta) for etiqueta, _ in filas) if filas else 0
    for etiqueta, valor in filas:
        print(f"  {etiqueta.ljust(ancho)}  {valor}")


def _metros_entre(dos: tuple[float, float], otros: tuple[float, float]) -> float:
    latitud = math.radians((dos[1] + otros[1]) / 2)
    dx = (dos[0] - otros[0]) * 111_320 * math.cos(latitud)
    dy = (dos[1] - otros[1]) * 111_320
    return math.hypot(dx, dy)


def _la_forma(wkt: str | None) -> dict:
    """Puntos, centro y superficie de un WKT, para compararlo con otro sin adivinar."""
    from app import geo

    anillos = [anillo for anillo in geo.anillos_de_un_wkt(wkt) if len(anillo) >= 3] if wkt else []
    puntos = anillos[0] if anillos else []
    if not puntos:
        return {"puntos": 0, "centro": None, "hectareas": None}
    xs = [x for x, _ in puntos]
    ys = [y for _, y in puntos]
    latitud = math.radians(sum(ys) / len(ys))
    area = 0.0
    for (x1, y1), (x2, y2) in zip(puntos, puntos[1:] + puntos[:1]):
        area += (x1 * 111_320 * math.cos(latitud)) * (y2 * 111_320) - (
            x2 * 111_320 * math.cos(latitud)
        ) * (y1 * 111_320)
    return {
        "puntos": len(puntos),
        "centro": (sum(xs) / len(xs), sum(ys) / len(ys)),
        "hectareas": abs(area) / 2 / 10_000,
    }


def _comparar_wkt(nuestro: str | None, suyo: str | None) -> dict:
    """¿El WKT de la parcela es el del lector? Primero a lo bruto y, si no, por forma."""
    if nuestro == suyo:
        return {"igual": True, "exacto": True, "puntos": _la_forma(suyo)["puntos"], "desvio_m": 0.0}
    una, otra = _la_forma(nuestro), _la_forma(suyo)
    if not (una["centro"] and otra["centro"]):
        return {"igual": False, "exacto": False, "puntos": una["puntos"], "desvio_m": None}
    desvio = _metros_entre(una["centro"], otra["centro"])
    return {
        "igual": desvio <= 0.01 and una["puntos"] == otra["puntos"],
        "exacto": False,
        "puntos": una["puntos"],
        "desvio_m": desvio,
    }


def _fuente(tamano: int):
    """Una letra legible para las etiquetas, si el sistema tiene alguna."""
    from PIL import ImageFont

    for ruta in (
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if pathlib.Path(ruta).is_file():
            try:
                return ImageFont.truetype(ruta, tamano)
            except OSError:  # noqa: PERF203 — si esa no vale, se prueba la siguiente
                continue
    return ImageFont.load_default(size=max(tamano - 4, 8))


def _el_fondo_neutro(ancho: int, alto: int) -> bytes:
    """Un fondo claro con una rejilla suave, para dibujar el contorno cuando no hay ortofoto."""
    from PIL import Image, ImageDraw

    imagen = Image.new("RGB", (ancho, alto), COLOR_FONDO)
    dibujo = ImageDraw.Draw(imagen)
    for x in range(0, ancho, 40):
        dibujo.line([(x, 0), (x, alto)], fill=(233, 230, 220))
    for y in range(0, alto, 40):
        dibujo.line([(0, y), (ancho, y)], fill=(233, 230, 220))
    memoria = io.BytesIO()
    imagen.save(memoria, format="PNG")
    return memoria.getvalue()


def _el_mapa_del_programa(geometria: str, ancho: int, alto: int) -> bytes:
    """El contorno de la tierra dibujado **por el propio programa** sobre un fondo neutro.

    Se usa `mapa_de_una_tierra.dibujar_el_contorno`, que es el que compone la imagen de la ficha: lo
    único que falta es la ortofoto (que se pide a internet). Así la forma que se ve es la de verdad y
    la dibuja el mismo código que la dibujará en producción.
    """
    anillos = mapa_de_una_tierra._puntos_de_la_tierra(geometria)
    caja = mapa_de_una_tierra.caja_de_la_tierra(geometria, ancho, alto)
    return mapa_de_una_tierra.dibujar_el_contorno(
        _el_fondo_neutro(ancho, alto), anillos, caja, ancho, alto
    )


# --------------------------------------------------------------------------- el montaje


def _envolver(dibujo, texto: str, fuente, ancho_max: float) -> list[str]:
    """Parte un texto en las líneas que caben a lo ancho, sin cortar palabras por la mitad."""
    lineas: list[str] = []
    actual = ""
    for palabra in str(texto).split():
        prueba = f"{actual} {palabra}".strip()
        if actual and dibujo.textlength(prueba, font=fuente) > ancho_max:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    if actual:
        lineas.append(actual)
    return lineas


def _el_montaje(paneles: list[dict], *, con_ortofoto: bool, con_degradacion: bool) -> bytes:
    """Una imagen con una fila por parcela: su nombre, su referencia y su mapa."""
    from PIL import Image, ImageDraw

    titulo = "Contornos del SIGPAC · Salamanca (37) · Calvarrasa de Arriba (70)"
    if con_ortofoto:
        subtitulo = "Ortofoto del IGN con el contorno de cada tierra (GET /api/mapa/tierra/{id}.png)"
    else:
        subtitulo = (
            "Sin ortofoto: el mapa pide la foto del IGN y esta prueba no sale a internet (503). "
            "El contorno lo dibuja el propio programa sobre un fondo neutro."
        )
    pie = "Datos: FEGA (SIGPAC), CC BY 4.0 · geometrías leídas del GeoPackage real de Salamanca"

    fuente_titulo = _fuente(20)
    fuente_panel = _fuente(15)
    fuente_pie = _fuente(13)
    ancho_total = ANCHO + 2 * MARGEN
    ancho_util = ancho_total - 2 * MARGEN

    # Se mide el texto antes de crear la imagen: así cabecera y pie tienen el alto que necesitan y no
    # se corta nada (la primera versión cortaba el título por la derecha).
    sonda = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    lineas_titulo = _envolver(sonda, titulo, fuente_titulo, ancho_util)
    lineas_subtitulo = _envolver(sonda, subtitulo, fuente_pie, ancho_util) if con_degradacion else []
    lineas_pie = _envolver(sonda, pie, fuente_pie, ancho_util)
    alto_cabecera = 10 + 25 * len(lineas_titulo) + 18 * len(lineas_subtitulo) + 8
    alto_pie = 10 + 17 * len(lineas_pie)
    alto_paneles = len(paneles) * (34 + ALTO + MARGEN)
    alto_total = alto_cabecera + alto_paneles + alto_pie

    imagen = Image.new("RGB", (ancho_total, alto_total), COLOR_CABECERA)
    dibujo = ImageDraw.Draw(imagen)

    y = 10
    for linea in lineas_titulo:
        dibujo.text((MARGEN, y), linea, font=fuente_titulo, fill=COLOR_TEXTO)
        y += 25
    for linea in lineas_subtitulo:
        dibujo.text((MARGEN, y), linea, font=fuente_pie, fill=COLOR_SUAVE)
        y += 18

    y = alto_cabecera
    for numero, panel in enumerate(paneles, start=1):
        dibujo.rectangle([MARGEN, y, MARGEN + ANCHO, y + 32], fill=COLOR_FONDO)
        linea_uno = f"{numero}. {panel['alias']} · {panel['referencia']}"
        linea_dos = f"{panel['hectareas']:.4f} ha · {panel['puntos']} puntos · {panel['fuente']}"
        dibujo.text((MARGEN + 8, y + 2), linea_uno, font=fuente_panel, fill=COLOR_TEXTO)
        dibujo.text((MARGEN + 8, y + 17), linea_dos, font=fuente_pie, fill=COLOR_SUAVE)
        y += 34
        try:
            foto = Image.open(io.BytesIO(panel["imagen"])).convert("RGB")
            if foto.size != (ANCHO, ALTO):
                foto = foto.resize((ANCHO, ALTO), Image.LANCZOS)
            imagen.paste(foto, (MARGEN, y))
        except (OSError, ValueError):
            dibujo.rectangle([MARGEN, y, MARGEN + ANCHO, y + ALTO], outline=COLOR_SUAVE)
            dibujo.text((MARGEN + 20, y + ALTO // 2), "sin imagen", font=fuente_panel, fill=COLOR_SUAVE)
        y += ALTO + MARGEN

    y = alto_total - alto_pie + 4
    for linea in lineas_pie:
        dibujo.text((MARGEN, y), linea, font=fuente_pie, fill=COLOR_SUAVE)
        y += 17

    memoria = io.BytesIO()
    imagen.save(memoria, format="PNG")
    return memoria.getvalue()


# --------------------------------------------------------------------------- el programa


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pinta las parcelas de un cliente con el contorno del SIGPAC real de Salamanca."
    )
    parser.add_argument(
        "--con-red",
        action="store_true",
        help=(
            "Pide la ortofoto de verdad al IGN. Sin esta opción (por defecto) se hace como en el "
            "campo sin cobertura: el mapa contesta 503 y se monta el contorno sobre fondo neutro."
        ),
    )
    parser.add_argument(
        "--salida",
        type=str,
        default=None,
        help="Dónde se guarda el montaje (por defecto, docs/capturas-nuevo/cliente-contornos*.png).",
    )
    argumentos = parser.parse_args(argv)
    salida = pathlib.Path(
        argumentos.salida or (SALIDA_CON_RED if argumentos.con_red else SALIDA_SIN_RED)
    )
    empezado = time.perf_counter()

    # **Sin red de verdad**: al programa se le dice que el mapa no contesta. Es el mismo camino que
    # usa la suite (`sigpac.pedir_imagen_del_mapa` sustituido) y el que vive el agricultor sin
    # cobertura. Con `--con-red` se deja el de verdad.
    if not argumentos.con_red:
        def _sin_cobertura(*args, **kwargs):
            raise sigpac.SigpacNoContesta("sin cobertura (esta prueba no sale a internet)")

        sigpac.pedir_imagen_del_mapa = _sin_cobertura
        print("Sin red: el mapa del servidor contestará 503 (como en el campo sin cobertura).")

    _para("1) El mapa real del SIGPAC")
    ficha = sigpac_cache.ficha_guardada(PROVINCIA, CAMPANA)
    if ficha is None:
        print(f"  FALTA el GeoPackage de la provincia {PROVINCIA} de {CAMPANA} en la caché.")
        print(f"  Se busca en: {sigpac_cache.carpeta_de_cache()}")
        print("  Descárgalo antes (POST /api/sigpac/cache/37) y vuelve a ejecutar esto.")
        return 2
    ruta_zip = sigpac_cache.carpeta_de_cache() / str(ficha["fichero"])
    _tabla([
        ("fichero", str(ficha["fichero"])),
        ("tamaño", f"{ficha['bytes'] / 2 ** 20:,.1f} MB".replace(",", ".")),
        ("campaña", str(ficha["campana"])),
        ("validez", str(ficha.get("fecha_validez"))),
        ("licencia", str(ficha.get("licencia"))),
    ])

    # La forma oficial de cada recinto, leída del fichero (esto es contra lo que se compara después).
    _para("2) Los tres recintos, leídos del GeoPackage")
    oficiales: dict[str, dict] = {}
    empezado_lectura = time.perf_counter()
    with geopackage_sigpac.abrir_recintos(ruta_zip) as lector:
        print(f"  abrir el lector: {time.perf_counter() - empezado_lectura:.3f} s "
              f"(¿sin descomprimir? {'sí' if lector.cacheado else 'no'})")
        for recinto in RECINTOS:
            encontrados = lector.buscar(
                PROVINCIA, MUNICIPIO, recinto["poligono"], recinto["parcela"], recinto["recinto"]
            )
            if not encontrados:
                print(f"  FALLO: el recinto {_referencia(recinto)} no está en el fichero")
                return 1
            hallado = encontrados[0]
            oficiales[_referencia(recinto)] = {
                **recinto,
                "referencia": _referencia(recinto),
                "wkt": hallado["wkt"],
                "superficie_ha": hallado["superficie_ha"],
                "uso_sigpac": hallado["uso_sigpac"],
            }
            print(f"  {_referencia(recinto)}  uso {hallado['uso_sigpac']}  "
                  f"{hallado['superficie_ha']:.4f} ha  {len(hallado['puntos'])} puntos")

    # --- el cliente y sus tierras, por la API -----------------------------
    _para("3) El cliente y sus tierras")
    crear_tablas()
    with TestClient(app) as cliente:
        alta = cliente.post(
            "/api/cuenta/registro",
            json={
                "explotacion": {
                    "nombre": "Explotación de prueba (Salamanca)",
                    "nif": "70922320A",
                    "provincia": "Salamanca",
                    "municipio": "Calvarrasa de Arriba",
                },
                "nombre": "Cliente de prueba",
                "correo": "cliente.prueba@ejemplo.test",
                "clave": "una-clave-larga-de-verdad",
            },
        )
        if alta.status_code != 201:
            print(f"  FALLO dando de alta al cliente: {alta.status_code} {alta.text}")
            return 1
        cabeceras = {"Authorization": f"Bearer {alta.json()['token']}"}

        tierras: list[dict] = []
        fallos_alta: list[str] = []
        for referencia, oficial in oficiales.items():
            alta = {
                "alias": oficial["alias"],
                "superficie_ha": oficial["superficie_ha"],
                # **La última se da de alta solo con la referencia** (IMP-25): los códigos tienen
                # que salir de ella. Antes se guardaba con todo en blanco y se quedaba sin contorno.
                "ref_sigpac": referencia,
            }
            if not oficial.get("solo_referencia"):
                alta.update({
                    "provincia": "Salamanca",
                    "municipio": "Calvarrasa de Arriba",
                    "codigo_ine": f"{PROVINCIA:02d}{MUNICIPIO:03d}",
                    "poligono": oficial["poligono"],
                    "numero_parcela": oficial["parcela"],
                    "numero_recinto": oficial["recinto"],
                    "uso_sigpac": oficial["uso_sigpac"],
                })
            respuesta = cliente.post("/api/parcelas", headers=cabeceras, json=alta)
            if respuesta.status_code != 201:
                print(f"  FALLO dando de alta la tierra {referencia}: "
                      f"{respuesta.status_code} {respuesta.text}")
                return 1
            creada = respuesta.json()
            tierras.append(creada)
            if oficial.get("solo_referencia"):
                codigos = (creada["codigo_ine"], creada["poligono"],
                           creada["numero_parcela"], creada["numero_recinto"])
                print(f"  {oficial['alias']}: {referencia} → tierra {creada['id']} "
                      f"**solo con la referencia**")
                print(f"      el alta ha rellenado: codigo_ine={codigos[0]!r}, poligono={codigos[1]}, "
                      f"numero_parcela={codigos[2]}, numero_recinto={codigos[3]}")
                if None in codigos:
                    fallos_alta.append(
                        f"{referencia}: el alta no ha sacado los códigos de la referencia → {codigos}"
                    )
            else:
                print(f"  {oficial['alias']}: {referencia} → tierra {creada['id']}")

        # --- 4) los contornos del GeoPackage real ------------------------
        _para("4) POST /api/sigpac/cache/37/contornos")
        empezado_contornos = time.perf_counter()
        respuesta = cliente.post(f"/api/sigpac/cache/{PROVINCIA}/contornos", headers=cabeceras)
        segundos_contornos = time.perf_counter() - empezado_contornos
        print(f"  {respuesta.status_code} en {segundos_contornos:.3f} s")
        if respuesta.status_code != 200:
            print(f"  FALLO: {respuesta.text}")
            return 1
        contornos = respuesta.json()
        _tabla([
            ("parcelas miradas", str(contornos["n"])),
            ("actualizadas", str(len(contornos["actualizadas"]))),
            ("no encontradas", str(len(contornos["no_encontradas"]))),
            ("sin códigos", str(len(contornos["sin_codigos"]))),
            ("sin forma", str(len(contornos["sin_forma"]))),
        ])
        if len(contornos["actualizadas"]) != len(RECINTOS):
            print("  FALLO: no han casado todas las parcelas del cliente.")
            return 1

        # --- 5) la geometría escrita y el mapa de cada tierra ------------
        _para("5) La geometría y el mapa de cada tierra")
        paneles: list[dict] = []
        fallos: list[str] = list(fallos_alta)
        with SessionLocal() as sesion:
            for tierra in tierras:
                parcela = sesion.get(models.Parcela, tierra["id"])
                oficial = oficiales[parcela.ref_sigpac]
                comparacion = _comparar_wkt(parcela.geometria, oficial["wkt"])
                if not comparacion["igual"]:
                    fallos.append(
                        f"{parcela.ref_sigpac}: el WKT guardado no es el del lector "
                        f"({comparacion['puntos']} puntos, desvío {comparacion['desvio_m']})"
                    )
                dibujo = parcela.dibujo or ""
                empezado_png = time.perf_counter()
                respuesta_png = cliente.get(
                    f"/api/mapa/tierra/{parcela.id}.png",
                    headers=cabeceras,
                    params={"ancho": ANCHO, "alto": ALTO},
                )
                segundos_png = time.perf_counter() - empezado_png
                from_server = respuesta_png.status_code == 200
                if from_server:
                    imagen = respuesta_png.content
                    fuente = f"mapa del servidor en {segundos_png * 1000:.0f} ms"
                else:
                    # Sin red no hay ortofoto: se dibuja el contorno real con el código del programa.
                    try:
                        imagen = _el_mapa_del_programa(parcela.geometria or "", ANCHO, ALTO)
                    except Exception as error:  # noqa: BLE001 — se dice en la tabla y se sigue
                        imagen = b""
                        fallos.append(f"{parcela.ref_sigpac}: no se pudo dibujar ({error})")
                    fuente = (
                        f"contorno dibujado por el programa ({respuesta_png.status_code} del servidor)"
                    )
                paneles.append(
                    {
                        "alias": parcela.alias,
                        "referencia": parcela.ref_sigpac,
                        "hectareas": parcela.superficie_sigpac_ha or parcela.superficie_ha or 0.0,
                        "puntos": comparacion["puntos"],
                        "imagen": imagen,
                        "fuente": fuente,
                        "usada": not from_server,
                    }
                )
                print(f"  {parcela.alias:<10} {parcela.ref_sigpac}  "
                      f"WKT {'idéntico' if comparacion['exacto'] else 'por forma'}, "
                      f"{comparacion['puntos']} puntos, dibujo {'sí' if dibujo else 'NO'}, "
                      f"mapa {'200' if from_server else respuesta_png.status_code} "
                      f"({segundos_png * 1000:.0f} ms) → {fuente}")
                if not from_server:
                    try:
                        detalle = respuesta_png.json().get("detail")
                        print(f"      el servidor dice: {detalle}")
                    except ValueError:
                        pass
                if not dibujo:
                    fallos.append(f"{parcela.ref_sigpac}: la parcela no tiene dibujo calculado")

    # --- 6) el montaje ----------------------------------------------------
    _para("6) La imagen del cliente")
    if not any(panel["imagen"] for panel in paneles):
        print("  No hay ninguna imagen que montar.")
        return 3
    con_ortofoto = not any(panel["usada"] for panel in paneles)
    montaje = _el_montaje(paneles, con_ortofoto=con_ortofoto, con_degradacion=not con_ortofoto)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_bytes(montaje)
    print(f"  {salida}  ({len(montaje) / 1024:,.0f} kB)".replace(",", "."))
    if not con_ortofoto:
        print("  Sin ortofoto (no hay red en esta prueba): se ha montado el contorno real de cada")
        print("  tierra, dibujado por el mismo código que compone la imagen de la ficha.")
        print("  Con `--con-red` se piden las ortofotos de verdad al IGN.")

    # --- veredicto --------------------------------------------------------
    _para("VEREDICTO")
    print(f"  Tiempo total: {time.perf_counter() - empezado:.2f} s")
    if fallos:
        for fallo in fallos:
            print(f"  FALLA: {fallo}")
        return 1
    print(f"  OK: las {len(RECINTOS)} parcelas del cliente casan con el GeoPackage real, su")
    print("  geometría es la del lector, todas tienen dibujo y la imagen está guardada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
