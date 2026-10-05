"""Baja la lista oficial de municipios del INE y saca los de Castilla y León.

**Por qué este fichero existe.** Hasta ahora, para dar de alta una parcela había que
escribir a mano el municipio y la provincia, y para traerla del SIGPAC había que saberse
los siete números de la referencia. El agricultor no tiene por qué saberse ningún código:
las aplicaciones oficiales del FEGA (SgaRex en Cantabria, SgaCap en Galicia) le piden
[Cód. Provincia], [Cód. Municipio], [Agregado], [Zona], [Cód. Polígono] y [Cód. Parcela]
en casillas y le enseñan los recintos para marcarlos. Para eso hacen falta las listas.

**De dónde sale.** Del diccionario que publica el INE, «Relación de municipios y sus
códigos por comunidades autónomas y provincias»:

    https://www.ine.es/daco/daco42/codmun/diccionario{anio}.xlsx

Ese fichero trae, para cada municipio de España, la comunidad (CODAUTO), la provincia
(CPRO), el municipio (CMUN), el dígito de control (DC) y el nombre (NOMBRE). El código
municipal de cinco cifras es **CPRO + CMUN**, que es el mismo que se usa en la referencia
SIGPAC y en la referencia catastral: Calvarrasa de Arriba es CPRO 37 y CMUN 070, o sea
37070, y en el visor del SIGPAC sale como «70 - CALVARRASA DE ARRIBA». Eso no se supone:
lo comprueba un test contra las referencias catastrales de ejemplo y contra el listado
municipal de IDECyL que ya estaba en el repositorio.

Uso:
    python scripts/bajar_municipios_ine.py
    python scripts/bajar_municipios_ine.py --sin-descarga   # desde la copia guardada
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import time
from pathlib import Path

import httpx
import openpyxl

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "data" / "municipios_ine_fuentes"
CSV = RAIZ / "data" / "municipios_cyl.csv"
PROCEDENCIA = CARPETA / "procedencia.json"
ZV_CSV = RAIZ / "data" / "zv_cyl.csv"

# Los códigos de provincia del INE en Castilla y León. Están escritos aquí porque son los
# nueve de la comunidad, y si el INE cambiara la numeración habría que enterarse: el script
# falla si no están todos.
PROVINCIAS_CYL = {"05", "09", "24", "34", "37", "40", "42", "47", "49"}

# Cuántos municipios tiene cada provincia de la comunidad. No es un adorno: si el INE
# cambia el fichero (otra hoja, otras columnas, otra numeración), estos números dejan de
# salir y el script se para en vez de escribir un listado a medias.
MUNICIPIOS_POR_PROVINCIA = {
    "05": 248,  # Ávila
    "09": 371,  # Burgos
    "24": 211,  # León
    "34": 191,  # Palencia
    "37": 362,  # Salamanca
    "40": 209,  # Segovia
    "42": 183,  # Soria
    "47": 225,  # Valladolid
    "49": 248,  # Zamora
}
TOTAL_CYL = sum(MUNICIPIOS_POR_PROVINCIA.values())  # 2248

CABECERAS = {"User-Agent": "Mozilla/5.0 (compatible; CUE-Digital/1.0)"}
HOJA = "dic"

# **Los años del diccionario que existen, comprobados a mano.** El INE publica uno al año
# (`diccionario2025.xlsx` y así). Cuando salga el siguiente, se añade aquí delante.
#
# No se tantean años a ciegas a propósito: el servidor del INE contesta 404 a los ficheros que
# no existen y **después bloquea un rato las peticiones siguientes**, de forma que una ronda
# de tanteo deja al script sin poder bajar ni el año que sí está publicado. Se comprobó a
# base de verlo fallar.
ANIOS_PUBLICADOS = (2025, 2024)


def url_del_anio(anio: int) -> str:
    return f"https://www.ine.es/daco/daco42/codmun/diccionario{anio}.xlsx"


def descargar(anios: list[int] | None = None, intentos: int = 4) -> tuple[bytes, int]:
    """Baja el diccionario del INE: el año más nuevo de los publicados.

    Se reintenta cuando el fallo es de red o del servidor, esperando un poco más cada vez.
    Un 404 no se reintenta: ese año no está publicado y se pasa al anterior.
    """
    for anio in anios or list(ANIOS_PUBLICADOS):
        for intento in range(1, intentos + 1):
            try:
                respuesta = httpx.get(
                    url_del_anio(anio), timeout=90, follow_redirects=True, headers=CABECERAS
                )
            except Exception:  # noqa: BLE001 — cualquier fallo de red se reintenta igual
                time.sleep(5 * intento)
                continue
            if respuesta.status_code == 200 and respuesta.content[:2] == b"PK":
                return respuesta.content, anio
            if respuesta.status_code == 404:
                break  # ese año no está publicado: se pasa al anterior
            time.sleep(5 * intento)
    raise RuntimeError(
        "No se ha podido bajar el diccionario de municipios del INE. Mira si el INE ha "
        "publicado un año nuevo y añádelo a ANIOS_PUBLICADOS, o usa --sin-descarga con la "
        "copia que ya está en data/municipios_ine_fuentes/."
    )


def leer_municipios(bytes_excel: bytes) -> list[tuple[str, str, str, str]]:
    """Saca los municipios de Castilla y León: (codigo_ine, municipio, provincia, codigo_municipio).

    El nombre de la provincia no viene en el fichero, solo su código. Los nombres son los
    mismos nueve de siempre y están en la lista de provincias de la comunidad.
    """
    libro = openpyxl.load_workbook(io.BytesIO(bytes_excel), read_only=True, data_only=True)
    hojas = [nombre for nombre in libro.sheetnames if nombre.startswith(HOJA)]
    if not hojas:
        raise ValueError(f"El diccionario del INE no trae la hoja esperada: {libro.sheetnames}")
    filas = libro[hojas[0]].values

    # La primera fila del fichero es el título («Relación de municipios y códigos ... a 1 de
    # enero de 2025») y la cabecera de verdad va debajo. Se busca la cabecera en vez de
    # suponer que está en la fila 2: así, si algún año añaden una línea más arriba, sigue
    # funcionando; y si cambian los nombres de las columnas, se para.
    cabecera_buscada = ("CODAUTO", "CPRO", "CMUN", "DC", "NOMBRE")
    for fila in filas:
        cabecera = tuple(str(celda or "").strip() for celda in fila)
        if cabecera[:5] == cabecera_buscada:
            break
    else:
        raise ValueError("El diccionario del INE no trae la cabecera esperada.")

    provincias = _nombres_de_provincia()
    municipios: list[tuple[str, str, str, str]] = []
    vistos: set[str] = set()
    for fila in filas:
        if not fila or fila[0] is None or fila[1] is None:
            continue
        provincia = str(fila[1]).strip().zfill(2)
        municipio = str(fila[2]).strip().zfill(3)
        nombre = str(fila[4] or "").strip()
        if provincia not in PROVINCIAS_CYL:
            continue
        if not nombre:
            raise ValueError(f"Municipio sin nombre en el diccionario: {provincia}/{municipio}")
        codigo_ine = provincia + municipio
        if codigo_ine in vistos:
            raise ValueError(f"Código municipal repetido en el diccionario: {codigo_ine}")
        vistos.add(codigo_ine)
        municipios.append((codigo_ine, nombre, provincias[provincia], municipio))
    libro.close()

    cuenta_por_provincia = {codigo: 0 for codigo in PROVINCIAS_CYL}
    for codigo_ine, _, _, _ in municipios:
        cuenta_por_provincia[codigo_ine[:2]] += 1
    if cuenta_por_provincia != MUNICIPIOS_POR_PROVINCIA:
        raise ValueError(
            "La fuente ha cambiado: municipios por provincia "
            f"{cuenta_por_provincia} en vez de {MUNICIPIOS_POR_PROVINCIA}"
        )
    if len(municipios) != TOTAL_CYL:
        raise ValueError(f"La fuente ha cambiado: {len(municipios)} municipios en vez de {TOTAL_CYL}")
    return sorted(municipios)


def _nombres_de_provincia() -> dict[str, str]:
    """Los nombres de las nueve provincias, leídos del listado que ya está en el repositorio.

    No se escriben a mano aquí para que no puedan decir una cosa en un sitio y otra en el
    otro: el listado de zonas vulnerables ya trae provincia y código, y de ahí salen.
    """
    if not ZV_CSV.exists():
        raise ValueError(f"Falta {ZV_CSV.name}: de ahí salen los nombres de las provincias")
    nombres: dict[str, str] = {}
    with ZV_CSV.open(encoding="utf-8", newline="") as fichero:
        for fila in csv.DictReader(fichero):
            codigo = str(fila["codigo_ine"]).strip()[:2]
            nombres.setdefault(codigo, str(fila["provincia"]).strip())
    faltan = PROVINCIAS_CYL - set(nombres)
    if faltan:
        raise ValueError(f"El listado de zonas vulnerables no cubre las provincias {sorted(faltan)}")
    return nombres


def cotejar_con_el_listado_de_zonas(municipios: list[tuple[str, str, str, str]]) -> int:
    """Comprueba que los 387 municipios del listado de IDECyL están aquí, y con el mismo código.

    Son dos fuentes oficiales distintas (el INE y la Junta) y tienen que coincidir. Si no
    coincidieran, la elección de municipio de la aplicación estaría usando una numeración
    que no es la de la otra, y eso se tiene que saber antes de dar de alta ninguna parcela.
    """
    if not ZV_CSV.exists():
        return 0
    conocidos = {codigo_ine for codigo_ine, _, _, _ in municipios}
    cotejados = 0
    with ZV_CSV.open(encoding="utf-8", newline="") as fichero:
        for fila in csv.DictReader(fichero):
            codigo = str(fila["codigo_ine"]).strip()
            if codigo not in conocidos:
                raise ValueError(f"El municipio {codigo} del listado de IDECyL no está en el INE")
            cotejados += 1
    return cotejados


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sin-descarga",
        action="store_true",
        help="Rehacer el CSV desde la copia oficial guardada, sin pedir nada a internet",
    )
    parser.add_argument(
        "--anio", type=int, default=None, help="Forzar un año concreto del diccionario del INE"
    )
    argumentos = parser.parse_args()

    CARPETA.mkdir(parents=True, exist_ok=True)
    if argumentos.sin_descarga:
        guardados = sorted(CARPETA.glob("diccionario*.xlsx"))
        if not guardados:
            raise SystemExit("No hay ninguna copia guardada del diccionario del INE.")
        fichero = guardados[-1]
        bytes_excel = fichero.read_bytes()
        anio = int("".join(caracter for caracter in fichero.stem if caracter.isdigit()))
        # La fecha de descarga se conserva de la vez que se bajó de verdad. Si todavía no hay
        # procedencia (primera vez desde una copia), se usa la del fichero guardado: es la
        # fecha en la que ese fichero llegó aquí, que es lo que se quiere dejar escrito.
        if PROCEDENCIA.exists():
            fecha = json.loads(PROCEDENCIA.read_text(encoding="utf-8"))["descargado_el"]
        else:
            fecha = dt.date.fromtimestamp(fichero.stat().st_mtime).isoformat()
    else:
        bytes_excel, anio = descargar([argumentos.anio] if argumentos.anio else None)
        fecha = dt.date.today().isoformat()
        (CARPETA / f"diccionario{anio}.xlsx").write_bytes(bytes_excel)

    municipios = leer_municipios(bytes_excel)
    cotejados = cotejar_con_el_listado_de_zonas(municipios)

    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(("codigo_ine", "municipio", "provincia", "codigo_provincia", "codigo_municipio"))
    for codigo_ine, nombre, provincia, codigo_municipio in municipios:
        escritor.writerow((codigo_ine, nombre, provincia, codigo_ine[:2], codigo_municipio))
    CSV.write_text(salida.getvalue(), encoding="utf-8", newline="")

    PROCEDENCIA.write_text(
        json.dumps(
            {
                "_leeme": "Derivado reproducible; no editar la lista de municipios a mano.",
                "fuente": f"INE, «Relación de municipios y sus códigos», {url_del_anio(anio)}",
                "url": url_del_anio(anio),
                "anio_del_diccionario": anio,
                "descargado_el": fecha,
                "sha256": hashlib.sha256(bytes_excel).hexdigest(),
                "municipios": len(municipios),
                "municipios_por_provincia": MUNICIPIOS_POR_PROVINCIA,
                "cotejados_con_el_listado_de_zonas_vulnerables": cotejados,
                "comose_usa": (
                    "codigo_ine (5 cifras) = codigo_provincia (2) + codigo_municipio (3). "
                    "El codigo_municipio es el mismo que sale en el visor del SIGPAC y el que "
                    "va en la referencia del recinto; el codigo_ine es con el que se comprueba "
                    "la zona vulnerable a nitratos."
                ),
                "licencia": (
                    "Datos del INE. La relación de municipios y sus códigos es información "
                    "pública; se guarda aquí para poder elegir el municipio sin teclear códigos."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    (CARPETA / "LEEME.md").write_text(
        "# Fuente oficial: municipios de Castilla y León\n\n"
        f"`diccionario{anio}.xlsx` es la **copia literal** del diccionario del INE\n"
        "«Relación de municipios y sus códigos por comunidades autónomas y provincias»:\n\n"
        f"- Dirección: {url_del_anio(anio)}\n"
        f"- Descargado el: {fecha}\n"
        f"- SHA-256: `{hashlib.sha256(bytes_excel).hexdigest()}`\n\n"
        "De ahí sale `data/municipios_cyl.csv`, que es lo que lee la aplicación para poder\n"
        "elegir el municipio **por su nombre** en vez de escribir códigos. El CSV se rehace\n"
        "con `python scripts/bajar_municipios_ine.py` y se puede rehacer sin internet con\n"
        "`--sin-descarga`, que usa esta copia.\n\n"
        "El código de cinco cifras es el de siempre: **dos de provincia y tres de municipio**.\n"
        f"Son {len(municipios)} municipios en las nueve provincias de la comunidad.\n",
        encoding="utf-8",
    )

    print(f"{len(municipios)} municipios de Castilla y León ({anio}) -> {CSV.name}")
    print(f"Cotejados con el listado de zonas vulnerables: {cotejados}")
    print(f"SHA-256 del diccionario: {hashlib.sha256(bytes_excel).hexdigest()}")


if __name__ == "__main__":
    main()
