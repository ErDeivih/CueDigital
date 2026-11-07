"""**Probar el lector de GeoPackage con el fichero de verdad de una provincia** (IMP-18, 07/11/2026).

No es un test de la suite: es la prueba que se lanza a mano contra el SIGPAC de verdad, porque la
suite no puede salir a internet. Lo que hace, en este orden:

1. **Deja el mapa de una provincia en la caché** con la descarga de siempre
   (`sigpac_cache.descargar_provincia`), midiendo lo que tarda y lo que ocupa.
2. **Lo abre con el lector** (`geopackage_sigpac.abrir_recintos`) y cuenta lo que hay dentro: qué
   tabla y qué columna de geometría ha encontrado, **los nombres reales de las columnas**, cuántos
   recintos y qué índices trae.
3. **Busca un recinto** por sus códigos (`buscar`), con y sin número de recinto, midiendo tiempos y
   la memoria que gasta.
4. **Compara la forma** que devuelve el fichero con la que devolvió el servicio del SIGPAC (el
   ejemplo guardado en `data/sigpac/`, o preguntándosela al servicio si el recinto no está a mano):
   número de puntos, centro, caja y superficie. Así se sabe si el GeoPackage y el servicio dicen lo
   mismo del mismo trozo.
5. **Prueba `contornos_de_las_parcelas`** con tres parcelas de ejemplo: la que casa, una que no está
   en el mapa y una sin códigos. Es lo que hace la puerta `/api/sigpac/cache/{provincia}/contornos`.

Sale con **código 0 solo si todo cuadra** (el recinto aparece, la forma coincide y una parcela casa).
Si algo no cuadra, lo dice con el número y sale con 1; si no se puede ni descargar, sale con 2.

## Lo que se ha aprendido midiendo (para que no se pierda)

- **La descarga ya no carga el ZIP entero en memoria**: `sigpac_cache.stream_http` lo escribe por
  trozos en un temporal (1 MB por iteración) y solo después se renombra. Con Salamanca ya no hay
  628 MB de RAM en un tirón; el script mide el pico de memoria de todas formas.
- **El ZIP se extrae a una carpeta temporal** cada vez que se abre (`abrir_recintos`), así que hay
  **628 MB de ZIP en la caché + otros ~1 GB de `.gpkg` en el temporal** mientras dura la prueba, y
  **cada** `contornos_de_las_parcelas` vuelve a extraerlo. Se mide y se dice; cambiarlo (guardar el
  `.gpkg` extraído, o leer el ZIP por trozos) es otra tarea.
- **El listado del FEGA se lee antes de bajar**, así que el tamaño se sabe antes de gastar memoria:
  el script lo comprueba con una petición `HEAD` y avisa.

Uso:

    ..\\.venv\\Scripts\\python.exe scripts/probar_geopackage_real.py
    ..\\.venv\\Scripts\\python.exe scripts/probar_geopackage_real.py --provincia 47 --campana 2026
    ..\\.venv\\Scripts\\python.exe scripts/probar_geopackage_real.py --alternativa 47 --limite-mb 400
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import pathlib
import sys
import tempfile
import time
import tracemalloc
from types import SimpleNamespace

RAIZ = pathlib.Path(__file__).resolve().parents[1]  # backend/
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app import geopackage_sigpac, sigpac, sigpac_cache  # noqa: E402

PROVINCIA_POR_DEFECTO = 37  # Salamanca: la del recinto de ejemplo 37:70:0:0:503:51
CAMPANA_POR_DEFECTO = 2026
# La provincia a la que se pasa si la pedida no se puede bajar (por tamaño, memoria o red).
ALTERNATIVA_POR_DEFECTO = 47  # Valladolid, 295 MB
# El recinto del ejemplo guardado: provincia, municipio, agregado, polígono, parcela, recinto.
RECINTO_DE_EJEMPLO = (37, 70, 0, 503, 51, 1)
# La referencia del visor del mismo trozo, tal y como se escribe en el programa.
SU_REFERENCIA_EN_EL_VISOR = "37:70:0:0:503:51"
EJEMPLO_GUARDADO = RAIZ.parent / "data" / "sigpac" / "recinto_de_ejemplo_503_51.json"

# Cuánto se admite de diferencia entre el GeoPackage y el servicio para dar la forma por buena. El
# GeoPackage y el servicio salen de la misma captura del FEGA, así que lo normal es 0 m; se deja un
# metro de margen porque los dos pueden redondear distinto el último decimal.
TOLERANCIA_METROS = 1.0
TOLERANCIA_SUPERFICIE = 0.005  # medio por ciento


# --------------------------------------------------------------------------- utilidades de consola


def _linea(titulo: str = "") -> None:
    print()
    if titulo:
        print(f"== {titulo} ==")


def _mb(bytes_: float | int | None) -> str:
    if bytes_ is None:
        return "—"
    return f"{bytes_ / (1024 * 1024):,.1f} MB".replace(",", ".")


def _segundos(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:,.2f} s".replace(",", ".")


def _duracion(valor: float | None) -> str:
    """Un tiempo legible: en segundos si pasa de 0,1 s y en milisegundos si no.

    Hace falta porque la diferencia que se mide aquí (abrir descomprimiendo contra abrir el `.gpkg`
    guardado) cae de segundos a milisegundos, y «0,00 s» esconde justo lo que se quiere enseñar.
    """
    if valor is None:
        return "—"
    if valor >= 0.1:
        return _segundos(valor)
    return f"{valor * 1000:,.1f} ms".replace(",", ".")


def _tabla(filas: list[tuple[str, str]]) -> None:
    ancho = max(len(etiqueta) for etiqueta, _ in filas) if filas else 0
    for etiqueta, valor in filas:
        print(f"  {etiqueta.ljust(ancho)}  {valor}")


def _memoria_del_proceso_mb() -> tuple[float, float] | None:
    """`(memoria ahora, pico que ha tenido el proceso)` en MB, por la API de Windows.

    `tracemalloc` solo ve lo que reserva Python: **no ve el ZIP que la descarga carga entero en
    memoria** ni lo que se lleva sqlite. Esto sí, y sin añadir ninguna dependencia.
    """
    if os.name != "nt":
        return None

    class Contadores(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    contadores = Contadores()
    contadores.cb = ctypes.sizeof(Contadores)
    # `psapi.GetProcessMemoryInfo` va por una DLL que en Windows 11 contesta 0 (falla en silencio);
    # la buena es `K32GetProcessMemoryInfo`, que exporta el propio kernel32.
    kernel32 = ctypes.WinDLL("kernel32.dll")
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    funcion = kernel32.K32GetProcessMemoryInfo
    funcion.argtypes = [ctypes.c_void_p, ctypes.POINTER(Contadores), ctypes.c_ulong]
    funcion.restype = ctypes.c_int
    if not funcion(kernel32.GetCurrentProcess(), ctypes.byref(contadores), contadores.cb):
        return None
    return (
        contadores.WorkingSetSize / (1024 * 1024),
        contadores.PeakWorkingSetSize / (1024 * 1024),
    )


def _memoria_libre_mb() -> float | None:
    """La memoria física libre, en MB. En Windows se pregunta al sistema; fuera, no se sabe."""
    if os.name != "nt":
        return None

    class EstadoDeMemoria(ctypes.Structure):
        _fields_ = [
            ("longitud", ctypes.c_ulong),
            ("carga", ctypes.c_ulong),
            ("total", ctypes.c_ulonglong),
            ("libre", ctypes.c_ulonglong),
            ("total_pagina", ctypes.c_ulonglong),
            ("libre_pagina", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong),
            ("libre_virtual", ctypes.c_ulonglong),
            ("libre_extendida", ctypes.c_ulonglong),
        ]

    estado = EstadoDeMemoria()
    estado.longitud = ctypes.sizeof(EstadoDeMemoria)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado)):
        return None
    return estado.libre / (1024 * 1024)


def _tamano_anunciado(provincia: int, campana: int) -> int | None:
    """Lo que ocupa el ZIP según el servidor, **antes de bajarlo** (petición `HEAD`)."""
    import httpx

    entradas = sigpac_cache.entradas_del_listado(
        httpx.get(sigpac_cache.url_del_listado(campana), timeout=30, follow_redirects=True).text,
        campana,
    )
    elegido = sigpac_cache.busca_el_de_la_provincia(entradas, provincia)
    if elegido is None:
        return None
    url = sigpac_cache.url_del_listado(campana) + elegido["href"].rsplit("/", 1)[-1]
    respuesta = httpx.head(url, timeout=30, follow_redirects=True)
    if respuesta.status_code != 200:
        return None
    return int(respuesta.headers.get("content-length") or 0) or None


# --------------------------------------------------------------------------- la forma: comparar WKT


def _metros_entre(dos: tuple[float, float], otros: tuple[float, float]) -> float:
    """Distancia aproximada en metros entre dos puntos en longitud/latitud (a esta escala, sobra)."""
    latitud = math.radians((dos[1] + otros[1]) / 2)
    dx = (dos[0] - otros[0]) * 111_320 * math.cos(latitud)
    dy = (dos[1] - otros[1]) * 111_320
    return math.hypot(dx, dy)


def _la_forma(wkt: str) -> dict:
    """Lo que se compara de una forma: puntos, caja, centro y superficie en hectáreas."""
    anillos = geo_anillos(wkt)
    puntos = anillos[0] if anillos else []
    if not puntos:
        return {"puntos": 0, "caja": None, "centro": None, "hectareas": None}
    xs = [x for x, _ in puntos]
    ys = [y for _, y in puntos]
    latitud = math.radians(sum(ys) / len(ys))
    # Superficie por la fórmula del zapatero, con los grados pasados a metros.
    area = 0.0
    for (x1, y1), (x2, y2) in zip(puntos, puntos[1:] + puntos[:1]):
        area += (x1 * 111_320 * math.cos(latitud)) * (y2 * 111_320) - (
            x2 * 111_320 * math.cos(latitud)
        ) * (y1 * 111_320)
    return {
        "puntos": len(puntos),
        "caja": (min(xs), min(ys), max(xs), max(ys)),
        "centro": (sum(xs) / len(xs), sum(ys) / len(ys)),
        "hectareas": abs(area) / 2 / 10_000,
    }


def geo_anillos(wkt: str) -> list[list[tuple[float, float]]]:
    """Los anillos de un WKT, sin depender de `shapely`: `POLYGON(...)` o `MULTIPOLYGON(...)`."""
    from app import geo

    puntos = geo.puntos_del_wkt(wkt) or []
    return [list(puntos)] if puntos else []


def _comparar_dos_formas(nuestra: str, suya: str) -> dict:
    """Compara dos formas por lo que significa: puntos, caja, centro y superficie."""
    una, otra = _la_forma(nuestra), _la_forma(suya)
    salida = {"nuestra": una, "suya": otra, "desvio_centro_m": None, "desvio_caja_m": None,
              "desvio_superficie_pct": None, "coincide": False}
    if not (una["centro"] and otra["centro"]):
        return salida
    salida["desvio_centro_m"] = _metros_entre(una["centro"], otra["centro"])
    esquinas = [
        _metros_entre((una["caja"][0], una["caja"][1]), (otra["caja"][0], otra["caja"][1])),
        _metros_entre((una["caja"][2], una["caja"][3]), (otra["caja"][2], otra["caja"][3])),
    ]
    salida["desvio_caja_m"] = max(esquinas)
    if una["hectareas"] and otra["hectareas"]:
        salida["desvio_superficie_pct"] = (
            abs(una["hectareas"] - otra["hectareas"]) / otra["hectareas"] * 100
        )
    salida["coincide"] = (
        salida["desvio_centro_m"] <= TOLERANCIA_METROS
        and salida["desvio_caja_m"] <= TOLERANCIA_METROS
        and (salida["desvio_superficie_pct"] or 0) <= TOLERANCIA_SUPERFICIE * 100
    )
    return salida


def _recortar(wkt: str, cuantos: int = 110) -> str:
    return wkt if len(wkt) <= cuantos else wkt[:cuantos] + "…"


# --------------------------------------------------------------------------- las tres pruebas


def _la_descarga(provincia: int, campana: int, limite_mb: int | None) -> tuple[dict, float | None, bool]:
    """Deja el mapa en la caché. Devuelve `(ficha, segundos, si_se_ha_bajado_ahora)`."""
    ya = sigpac_cache.ficha_guardada(provincia, campana)
    if ya is not None:
        print(f"  Ya estaba en la caché: {ya['fichero']} ({_mb(ya['bytes'])})")
        return ya, None, False

    tamano = _tamano_anunciado(provincia, campana)
    libre = _memoria_libre_mb()
    print(f"  Tamaño anunciado por el FEGA: {_mb(tamano)}; memoria libre: {libre and f'{libre:,.0f} MB'}")
    if tamano and libre and tamano / (1024 * 1024) > libre * 0.6:
        print(
            "  AVISO: el ZIP es grande para la memoria libre que hay. La descarga de esta casa "
            "carga el fichero entero en memoria; si falla, se probará con otra provincia."
        )
    if limite_mb and tamano and tamano / (1024 * 1024) > limite_mb:
        raise RuntimeError(
            f"El mapa de esa provincia ocupa {_mb(tamano)} y el límite puesto es {limite_mb} MB."
        )

    print("  Bajando del SIGPAC (esto es lo que tarda)…", flush=True)
    empezado = time.perf_counter()
    ficha = sigpac_cache.descargar_provincia(provincia, campana)
    segundos = time.perf_counter() - empezado
    ficha["descargado"] = True
    print(f"  Bajado en {_segundos(segundos)} ({_mb(ficha['bytes'] / segundos)}/s)", flush=True)
    memoria = _memoria_del_proceso_mb()
    if memoria is not None:
        print(
            f"  Memoria del proceso al acabar la descarga: {memoria[0]:,.0f} MB "
            f"(pico {memoria[1]:,.0f} MB)".replace(",", ".")
        )
    return ficha, segundos, True


def _el_mapa_guardado(ruta_zip: pathlib.Path) -> tuple[pathlib.Path, str, int]:
    """Dónde deja el lector el `.gpkg` sacado, cómo se llama el miembro y lo que ocupa."""
    miembro, tamano = geopackage_sigpac._el_miembro_del_mapa(ruta_zip)
    return geopackage_sigpac._la_ruta_del_gpkg_guardado(ruta_zip, miembro), miembro, tamano


def _medir_aperturas(ruta_zip: pathlib.Path, resultado: dict) -> dict:
    """**Antes y después**: cuánto tarda abrir descomprimiendo y cuánto abriendo el `.gpkg` guardado.

    Se mide con el fichero de verdad, en este orden:

      1. Si ya hay un `.gpkg` guardado (de una ejecución anterior), lo que tarda abrirlo.
      2. Se tira ese `.gpkg` y se mide la apertura que **extrae** (la primera).
      3. Tres aperturas más con el mapa ya guardado.

    Todo son aperturas de verdad; lo que se compara es el mismo trabajo con y sin descomprimir.
    """
    guardado, miembro, tamano = _el_mapa_guardado(ruta_zip)
    tiempos: dict = {"guardado": guardado, "miembro": miembro, "tamano_miembro": tamano}
    print(f"  .gpkg dentro del ZIP: {miembro} ({_mb(tamano)})")
    print(f"  .gpkg guardado al lado: {guardado.name}")

    if guardado.exists() and guardado.stat().st_size == tamano:
        empezado = time.perf_counter()
        with geopackage_sigpac.abrir_recintos(ruta_zip) as lector:
            tiempos["con_guardado_previo"] = time.perf_counter() - empezado
            tiempos["con_guardado_previo_cacheado"] = lector.cacheado
    else:
        tiempos["con_guardado_previo"] = None

    # Y ahora la primera apertura de verdad: sin nada guardado, descomprimiendo 1 GB.
    guardado.unlink(missing_ok=True)
    empezado = time.perf_counter()
    with geopackage_sigpac.abrir_recintos(ruta_zip) as lector:
        tiempos["primera_sin_guardado"] = time.perf_counter() - empezado
        tiempos["primera_cacheado"] = lector.cacheado
        provincia, municipio, _, poligono, parcela, recinto = RECINTO_DE_EJEMPLO
        tiempos["primera_recintos"] = len(
            lector.buscar(provincia, municipio, poligono, parcela, recinto)
        )
    tiempos["se_guardo"] = guardado.is_file()
    tiempos["tamano_guardado"] = guardado.stat().st_size if guardado.is_file() else None

    # Tres aperturas más: ya con el mapa sacado al lado.
    siguientes = []
    for _ in range(3):
        empezado = time.perf_counter()
        with geopackage_sigpac.abrir_recintos(ruta_zip) as lector:
            siguientes.append(time.perf_counter() - empezado)
            tiempos["siguientes_cacheado"] = lector.cacheado
    tiempos["siguientes"] = siguientes

    resultado["aperturas"] = tiempos
    ahorro = ""
    if tiempos["primera_sin_guardado"] and siguientes:
        medio = sum(siguientes) / len(siguientes)
        if medio >= 0.002:
            ahorro = (
                f"  (×{tiempos['primera_sin_guardado'] / medio:,.0f} más rápido)".replace(",", ".")
            )
        else:
            ahorro = "  (cientos de veces más rápido)"
    _tabla([
        ("con el mapa ya guardado", _duracion(tiempos["con_guardado_previo"]) + " (de una vez anterior)"),
        ("1ª apertura: extrae 1 GB y lo guarda",
         _duracion(tiempos["primera_sin_guardado"]) + f"  → guardado: {_mb(tiempos['tamano_guardado'])}"),
        ("2ª, 3ª y 4ª: abren el guardado",
         " / ".join(_duracion(uno) for uno in siguientes) + ahorro),
        ("¿se ha descomprimido en las siguientes?", "NO" if tiempos["siguientes_cacheado"] else "SÍ (mal)"),
        ("¿se ha guardado el mapa al lado?", "SÍ" if tiempos["se_guardo"] else "NO (¿carpeta sin permiso?)"),
    ])
    return tiempos


def _la_inspeccion(lector, segundos_de_apertura: float) -> dict:
    """Cuenta lo que hay dentro del fichero real: tabla, columnas, filas e índices."""
    tabla, columna = lector.tabla, lector.columna
    filas = lector.conexion.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
    indices = [
        fila[1]
        for fila in lector.conexion.execute(f'PRAGMA index_list("{tabla}")').fetchall()
    ]
    # **Por qué columnas indexa**, no cómo se llama el índice: el del SIGPAC se llama
    # `ix_recinto_ref` y va por (polígono, parcela), que es lo que hace rápida la búsqueda.
    columnas_indexadas = {}
    for indice in indices:
        columnas_indexadas[indice] = [
            fila[2] for fila in lector.conexion.execute(f'PRAGMA index_info("{indice}")').fetchall()
        ]
    return {
        "tabla": tabla,
        "columna": columna,
        "srs": lector.srs,
        "columnas": lector.columnas,
        "filas": filas,
        "indices": indices,
        "columnas_indexadas": columnas_indexadas,
        "segundos_de_apertura": segundos_de_apertura,
    }


def _la_busqueda(lector, *, con_recinto: bool) -> tuple[list[dict], float, dict]:
    """Busca el recinto de ejemplo midiendo tiempo y memoria de lo que se lee."""
    provincia, municipio, _, poligono, parcela, recinto = RECINTO_DE_EJEMPLO
    tracemalloc.start()
    empezado = time.perf_counter()
    encontrados = lector.buscar(
        provincia, municipio, poligono, parcela, recinto if con_recinto else None
    )
    segundos = time.perf_counter() - empezado
    actual, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return encontrados, segundos, {"actual": actual, "pico": pico}


def _las_parcelas_de_mentira(recinto_real: dict) -> list[SimpleNamespace]:
    """Tres parcelas: la que casa con el mapa, una que no está y una sin códigos.

    Son objetos ligeros porque `contornos_de_las_parcelas` solo lee de ellos los campos de la
    referencia y el alias: no hace falta base de datos para probar la lectura.
    """
    def _una(**cambios):
        datos = {
            "id": 1,
            "alias": "El Prado",
            "ref_sigpac": None,
            "codigo_ine": f"{recinto_real['provincia']:02d}{recinto_real['municipio']:03d}",
            "provincia": "Salamanca",
            "municipio": "Calvarrasa de Arriba",
            "poligono": recinto_real["poligono"],
            "numero_parcela": recinto_real["parcela"],
            "numero_recinto": recinto_real["recinto"],
        }
        datos.update(cambios)
        return SimpleNamespace(**datos)

    return [
        _una(id=1, alias="El Prado"),
        _una(id=2, alias="La Era", numero_recinto=(recinto_real["recinto"] or 1) + 500),
        _una(id=3, alias="Sin pueblo", codigo_ine=None, municipio="PUEBLO QUE NO EXISTE",
             provincia="Salamanca"),
    ]


def _el_recinto_del_servicio(provincia: int, municipio: int, agregado: int, poligono: int,
                             parcela: int, recinto: int):
    """Le pregunta al servicio del SIGPAC por el mismo recinto (con red, es el contraste)."""
    referencia = sigpac.Referencia(
        provincia=provincia, municipio=municipio, agregado=agregado, zona=0,
        poligono=poligono, parcela=parcela, recinto=recinto,
    )
    try:
        return sigpac.pedir_recinto(referencia)
    except sigpac.SigpacNoContesta as error:
        print(f"  El servicio no ha contestado: {error}")
        return None


def _un_recinto_del_fichero(lector) -> dict | None:
    """El primer recinto con forma del fichero, para poder compararlo con el servicio."""
    campos = ", ".join(f'"{lector.columnas[clave]}"' for clave in
                       ("provincia", "municipio", "poligono", "parcela", "recinto")
                       if clave in lector.columnas)
    consulta = (
        f'SELECT {campos}, "{lector.columna}" FROM "{lector.tabla}" '
        f'WHERE "{lector.columna}" IS NOT NULL LIMIT 1'
    )
    fila = lector.conexion.execute(consulta).fetchone()
    if fila is None:
        return None
    claves = [clave for clave in ("provincia", "municipio", "poligono", "parcela", "recinto")
              if clave in lector.columnas]
    recinto = dict(zip(claves, fila[: len(claves)]))
    wkt, _ = geopackage_sigpac.leer_geometria(fila[-1])
    recinto["wkt"] = wkt
    return recinto


# --------------------------------------------------------------------------- el programa


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prueba el lector de GeoPackage contra el fichero de verdad de una provincia."
    )
    parser.add_argument("--provincia", type=int, default=PROVINCIA_POR_DEFECTO)
    parser.add_argument("--campana", type=int, default=CAMPANA_POR_DEFECTO)
    parser.add_argument(
        "--alternativa",
        type=int,
        default=ALTERNATIVA_POR_DEFECTO,
        help="Provincia a la que se pasa si la pedida no se puede bajar (0 = no probar otra).",
    )
    parser.add_argument(
        "--limite-mb", type=int, default=None,
        help="No bajar mapas anunciados por encima de este tamaño.",
    )
    parser.add_argument(
        "--temporal", type=str, default=None,
        help="Carpeta para el .gpkg extraído (por defecto, la del sistema).",
    )
    argumentos = parser.parse_args(argv)
    empezado_el_script = time.perf_counter()

    if argumentos.temporal:
        carpeta = pathlib.Path(argumentos.temporal)
        carpeta.mkdir(parents=True, exist_ok=True)
        tempfile.tempdir = str(carpeta)
    print(f"Temporal para el .gpkg extraído: {tempfile.gettempdir()}")

    resultado: dict = {"provincia": None, "problemas": []}
    provincia = argumentos.provincia
    ficha = None

    for intento in (0, 1):
        if intento == 0:
            provincia = argumentos.provincia
        else:
            if not argumentos.alternativa or argumentos.alternativa == argumentos.provincia:
                raise SystemExit(2)
            print(
                f"\nNo se ha podido con la provincia {argumentos.provincia}; se prueba con la "
                f"{argumentos.alternativa} (más pequeña). **Se dirá en el informe.**"
            )
            provincia = argumentos.alternativa
        try:
            _linea(f"1) La descarga: provincia {provincia}, campaña {argumentos.campana}")
            ficha, segundos_descarga, bajado_ahora = _la_descarga(
                provincia, argumentos.campana, argumentos.limite_mb
            )
            break
        except Exception as error:  # noqa: BLE001 — cualquier fallo de la descarga se cuenta
            print(f"  FALLO: {type(error).__name__}: {error}")
            resultado["problemas"].append(f"descarga {provincia}: {error}")
            ficha = None
    if ficha is None:
        print("\nNo se ha podido descargar ningún mapa. No se ha probado nada.")
        return 2

    ruta = sigpac_cache.carpeta_de_cache() / str(ficha["fichero"])
    resultado["provincia"] = provincia
    resultado["ficha"] = ficha
    resultado["descarga_segundos"] = segundos_descarga
    print()
    _tabla([
        ("provincia", f"{provincia:02d} {ficha.get('nombre_provincia') or ''}".strip()),
        ("campaña", str(ficha["campana"])),
        ("fecha de validez", str(ficha.get("fecha_validez"))),
        ("fichero", str(ficha["fichero"])),
        ("tamaño del ZIP", _mb(ficha["bytes"])),
        ("descarga", _segundos(segundos_descarga) + ("" if bajado_ahora else " (ya estaba en caché)")),
        ("licencia", str(ficha.get("licencia"))),
    ])

    # --- 2) abrir el lector: antes y después de guardar el mapa -----------------
    _linea("2) Abrir el GeoPackage: descomprimiendo contra abriendo el guardado")
    try:
        _medir_aperturas(ruta, resultado)
    except Exception as error:  # noqa: BLE001 — si no se puede medir, se dice y se sigue
        print(f"  FALLO al medir las aperturas: {type(error).__name__}: {error}")
        resultado["problemas"].append(f"medición de aperturas: {error}")

    # --- 3) abrir el lector para mirar dentro ----------------------------------
    _linea("3) Abrir el GeoPackage de verdad")
    libre_antes = _memoria_libre_mb()
    empezado = time.perf_counter()
    try:
        lector_abierto = geopackage_sigpac.abrir_recintos(ruta)
        lector = lector_abierto.__enter__()
        apertura = time.perf_counter() - empezado
    except Exception as error:  # noqa: BLE001 — un fichero que no se lee es el resultado
        print(f"  FALLO al abrir: {type(error).__name__}: {error}")
        return 1

    try:
        inspeccion = _la_inspeccion(lector, apertura)
        resultado["inspeccion"] = inspeccion
        _tabla([
            ("abrir para mirar dentro", _duracion(apertura) + (
                " (abre el .gpkg guardado)" if lector.cacheado else " (ha descomprimido el ZIP)"
            )),
            ("tabla / columna", f"{inspeccion['tabla']} / {inspeccion['columna']}"),
            ("sistema de coordenadas", str(inspeccion["srs"])),
            ("columnas encontradas", ", ".join(f"{k}={v}" for k, v in inspeccion["columnas"].items())),
            ("columnas sin encontrar", ", ".join(
                clave for clave in geopackage_sigpac.COLUMNAS if clave not in inspeccion["columnas"]
            ) or "ninguna"),
            ("recintos en el fichero", f"{inspeccion['filas']:,}".replace(",", ".")),
            ("índices de la tabla", ", ".join(
                f"{nombre} ({', '.join(columnas)})"
                for nombre, columnas in inspeccion["columnas_indexadas"].items()
            ) or "ninguno"),
            ("carpeta temporal", tempfile.gettempdir()),
        ])
        indexadas = {
            columna
            for columnas in inspeccion["columnas_indexadas"].values()
            for columna in columnas
        }
        if not ({"provincia", "poligono", "parcela"} & indexadas):
            print(
                "  AVISO: la tabla no trae índice por provincia/polígono/parcela: cada búsqueda "
                "recorrerá la tabla entera."
            )

        # --- 3) la búsqueda del recinto de ejemplo --------------------------
        _linea(f"4) Buscar el recinto {'-'.join(str(n) for n in RECINTO_DE_EJEMPLO)}")
        encontrados, segundos, memoria = _la_busqueda(lector, con_recinto=True)
        sin_recinto, segundos_sin, memoria_sin = _la_busqueda(lector, con_recinto=False)
        # **Y diez búsquedas más con el fichero ya caliente**, que es lo que se parece a rellenar una
        # finca entera: la primera paga la lectura del disco y las demás van sobre lo ya leído.
        claves = ", ".join(
            f'"{lector.columnas[clave]}"'
            for clave in ("provincia", "municipio", "poligono", "parcela", "recinto")
            if clave in lector.columnas
        )
        muestras = lector.conexion.execute(
            f'SELECT {claves} FROM "{lector.tabla}" LIMIT 10'
        ).fetchall()
        empezado = time.perf_counter()
        cuantos = 0
        for muestra in muestras:
            cuantos += len(
                lector.buscar(muestra[0], muestra[1], muestra[2], muestra[3], muestra[4])
            )
        segundos_caliente = (time.perf_counter() - empezado) / max(len(muestras), 1)
        resultado["busqueda"] = {"con_recinto": segundos, "sin_recinto": segundos_sin,
                                 "en_caliente": segundos_caliente,
                                 "memoria_pico": memoria["pico"]}
        _tabla([
            ("buscar(…, recinto=1)", f"{_duracion(segundos)} → {len(encontrados)} recinto(s)"),
            ("buscar(…, sin recinto)", f"{_duracion(segundos_sin)} → {len(sin_recinto)} recinto(s) "
                                       "(los trozos de esa parcela)"),
            ("búsqueda en caliente (media de 10)",
             f"{segundos_caliente * 1000:,.1f} ms → {cuantos} recinto(s)".replace(",", ".")),
            ("memoria del lector (pico)", _mb(memoria["pico"]) + " (lo que ocupa el .gpkg no entra aquí)"),
            ("memoria libre del sistema", f"{libre_antes:,.0f} MB" if libre_antes else "—"),
        ])
        if not encontrados:
            resultado["problemas"].append("el recinto de ejemplo no está en el mapa")
            print("  FALLO: el recinto no aparece en el fichero.")

        # --- 4) el WKT contra el del servicio ------------------------------
        _linea("5) La forma: GeoPackage contra el SIGPAC")
        nuestro = encontrados[0]["wkt"] if encontrados else None
        superficie_nuestra = encontrados[0]["superficie_ha"] if encontrados else None
        suyo = None
        superficie_suya = None
        fuente = "ejemplo guardado"
        if provincia == RECINTO_DE_EJEMPLO[0] and EJEMPLO_GUARDADO.is_file():
            guardado = json.loads(EJEMPLO_GUARDADO.read_text(encoding="utf-8"))
            recinto_guardado = sigpac.lee_recinto(json.dumps(guardado))
            if recinto_guardado is not None:
                suyo = recinto_guardado.wkt
                superficie_suya = recinto_guardado.superficie
        if suyo is None:
            fuente = "servicio del SIGPAC (preguntado ahora)"
            if provincia == RECINTO_DE_EJEMPLO[0]:
                del_servicio = _el_recinto_del_servicio(*RECINTO_DE_EJEMPLO)
            else:
                otro = _un_recinto_del_fichero(lector)
                if otro and otro.get("wkt"):
                    nuestro = otro["wkt"]
                    del_servicio = _el_recinto_del_servicio(
                        otro["provincia"], otro["municipio"], 0, otro["poligono"],
                        otro["parcela"], otro["recinto"],
                    )
                else:
                    del_servicio = None
            if del_servicio is not None:
                suyo = del_servicio.wkt
                superficie_suya = del_servicio.superficie
        if not nuestro or not suyo:
            print("  No hay las dos formas para comparar; no se puede juzgar la igualdad.")
            resultado["problemas"].append("no se han podido comparar las formas")
        else:
            comparacion = _comparar_dos_formas(nuestro, suyo)
            resultado["comparacion"] = comparacion
            _tabla([
                ("contraste", fuente),
                ("nuestro WKT", _recortar(nuestro)),
                ("el suyo", _recortar(suyo)),
                ("puntos", f"{comparacion['nuestra']['puntos']} / {comparacion['suya']['puntos']}"),
                ("desvío del centro", f"{comparacion['desvio_centro_m']:.3f} m"),
                ("desvío de la caja", f"{comparacion['desvio_caja_m']:.3f} m"),
                ("desvío de superficie", f"{comparacion['desvio_superficie_pct']:.4f} %"),
                ("superficie", f"{comparacion['nuestra']['hectareas']:.4f} ha / "
                               f"{comparacion['suya']['hectareas']:.4f} ha"),
                ("¿coincide?", "SÍ" if comparacion["coincide"] else "NO"),
            ])
            if not comparacion["coincide"]:
                resultado["problemas"].append("la forma del GeoPackage no coincide con la del SIGPAC")
            # **La superficie es lo que delató un fallo de unidades**: el fichero la da en metros
            # cuadrados (`dn_surface`) y el servicio en hectáreas. Si alguien vuelve a equivocarse,
            # esta línea lo canta: 49.015 ha no es «un poco más» que 4,9016 ha.
            if superficie_nuestra is not None and superficie_suya:
                desvio = abs(superficie_nuestra - superficie_suya) / superficie_suya * 100
                _tabla([
                    ("superficie del recinto", f"{superficie_nuestra:.4f} ha en el fichero / "
                                               f"{superficie_suya:.4f} ha en el SIGPAC "
                                               f"({desvio:.4f} % de desvío)"),
                ])
                if desvio > TOLERANCIA_SUPERFICIE * 100:
                    resultado["problemas"].append(
                        f"la superficie del recinto no cuadra: {superficie_nuestra} ha contra "
                        f"{superficie_suya} ha (¿unidades?)"
                    )

        # --- 5) los contornos de varias parcelas --------------------------
        _linea("6) contornos_de_las_parcelas (lo que hace la puerta de la API)")
        base = encontrados[0] if encontrados else {
            "provincia": provincia, "municipio": 0, "poligono": 0, "parcela": 0, "recinto": 0
        }
        parcelas = _las_parcelas_de_mentira(base)
        empezado = time.perf_counter()
        contornos = geopackage_sigpac.contornos_de_las_parcelas(parcelas, ruta)
        segundos = time.perf_counter() - empezado
        resultado["contornos"] = {
            "segundos": segundos,
            "n": contornos["n"],
            "actualizadas": len(contornos["actualizadas"]),
            "no_encontradas": len(contornos["no_encontradas"]),
            "sin_codigos": len(contornos["sin_codigos"]),
            "sin_forma": len(contornos["sin_forma"]),
        }
        _tabla([
            ("tiempo (abre el mapa, ya sin descomprimir)", _duracion(segundos)),
            ("parcelas miradas", str(contornos["n"])),
            ("actualizadas", str(len(contornos["actualizadas"]))),
            ("no encontradas", str(len(contornos["no_encontradas"]))),
            ("sin códigos", str(len(contornos["sin_codigos"]))),
            ("sin forma", str(len(contornos["sin_forma"]))),
        ])
        if contornos["actualizadas"]:
            print(f"  La que casa: {contornos['actualizadas'][0]['alias']} → "
                  f"{_recortar(contornos['actualizadas'][0]['wkt'], 90)}")
        if len(contornos["actualizadas"]) != 1 or len(contornos["no_encontradas"]) != 1:
            resultado["problemas"].append("los contornos no han casado como se esperaba")
    finally:
        lector_abierto.__exit__(None, None, None)

    # --- el veredicto ------------------------------------------------------
    _linea("VEREDICTO")
    print(f"  Tiempo total del script: {_segundos(time.perf_counter() - empezado_el_script)}")
    memoria = _memoria_del_proceso_mb()
    if memoria is not None:
        print(
            f"  Memoria del proceso: {memoria[0]:,.0f} MB ahora, pico {memoria[1]:,.0f} MB".replace(
                ",", "."
            )
        )
    if resultado["problemas"]:
        for problema in resultado["problemas"]:
            print(f"  FALLA: {problema}")
        print(f"\nCódigo de salida: 1 ({len(resultado['problemas'])} problema(s))")
        return 1
    print("  OK: el fichero real se abre, el recinto aparece, la forma coincide y las parcelas casan.")
    print("\nCódigo de salida: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
