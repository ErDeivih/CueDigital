"""Comprobar que los datos oficiales que hay bajados **siguen siendo los oficiales de hoy**.

## Por qué existe esto

El programa trabaja con listas que **no son suyas**: los municipios en zona vulnerable a nitratos, el
listado de productos fitosanitarios, los documentos del FEGA, los códigos de municipio del INE… Todo
eso se bajó un día, con su dirección y su huella apuntadas en un `procedencia.json`.

Y ese es justo el problema: **un dato oficial bajado no se queda quieto**. La administración publica
una corrección, cambia un listado o añade municipios, y el programa sigue con la copia vieja **sin que
nadie se entere**. Peor: la documentación dice «la lista oficial tiene 387 municipios», y eso deja de
ser verdad sin que nada avise.

Esto lo comprueba: vuelve a pedir cada dirección apuntada y compara la huella con la que se guardó.
No interpreta nada ni actualiza nada: dice **si sigue igual o ha cambiado**, con las dos huellas
delante para poder comprobarlo a mano.

## Cómo se usa

```bash
cd backend
../.venv/Scripts/python.exe scripts/comprobar_fuentes_oficiales.py
```

- **Todo igual:** dice `OK` por cada fuente y termina con código 0.
- **Alguna ha cambiado:** lo dice con las dos huellas y **termina con código 1**, para que se note.
  Lo que hay que hacer entonces es volver a lanzar el guion de descarga de esa fuente
  (`bajar_zonas_vulnerables_cyl.py`, `bajar_catalogos_fega.py`…) y **mirar qué ha cambiado** antes de
  dar el dato por bueno: puede ser una corrección de la administración o una versión nueva.
- **No se ha podido llegar:** lo dice tal cual. «No lo sé» no es «ha cambiado».

Con `--solo <texto>` se comprueba solo lo que contenga ese texto (por ejemplo `--solo fega`).

Esto **no es un test**: los tests no tocan la red. Esto es una comprobación a mano, como `humo.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time

import httpx

RAIZ = pathlib.Path(__file__).resolve().parents[2]
DATOS = RAIZ / "data"

CABECERAS = {"User-Agent": "CueDigital/1.0 (comprobacion de datos oficiales publicos)"}
ESPERA = 90.0
# Se va despacio y con el cliente identificado: son servidores públicos y aquí se entra a comprobar.
SEGUNDOS_ENTRE_PETICIONES = 1.5

# Los ficheros de procedencia que se saben leer, con la forma de cada uno. Todos tienen dentro una
# lista de «ficheros» con `url` y `sha256`; el de las zonas vulnerables los llama de otra manera
# (`fuente_excel` / `fuente_excel_sha256`), y eso se respeta en vez de renombrarlo.
PROCEDENCIAS = [
    ("data/fega/procedencia.json", "ficheros"),
    ("data/zv_cyl_fuentes/procedencia.json", "suelto"),
    ("data/municipios_ine_fuentes/procedencia.json", "ficheros"),
]


def _fuentes() -> list[dict]:
    """Saca de los ficheros de procedencia la lista de direcciones con su huella esperada."""
    salida: list[dict] = []
    for ruta_relativa, forma in PROCEDENCIAS:
        fichero = RAIZ / ruta_relativa
        if not fichero.exists():
            salida.append({"nombre": ruta_relativa, "url": "", "sha256": "", "aviso": "no está el fichero de procedencia"})
            continue
        try:
            datos = json.loads(fichero.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            salida.append({"nombre": ruta_relativa, "url": "", "sha256": "", "aviso": "el fichero de procedencia no se puede leer"})
            continue

        if forma == "ficheros":
            for nombre, info in (datos.get("ficheros") or {}).items():
                if info.get("url") and info.get("sha256"):
                    salida.append(
                        {
                            "nombre": f"{ruta_relativa} · {nombre}",
                            "url": info["url"],
                            "sha256": info["sha256"],
                            "descargado_el": info.get("descargado_el", ""),
                            # Cómo se pidió (algunas fuentes son un POST con formulario) y qué se
                            # vio al bajarlo (las filas, por ejemplo): hace falta para poder
                            # comparar lo mismo dentro de un mes.
                            "peticion": info.get("peticion"),
                            "comprobado": info.get("comprobado", ""),
                        }
                    )
        else:
            # El de las zonas vulnerables: dos ficheros con nombres distintos.
            for url, huella, cuando in (
                (datos.get("fuente_excel"), datos.get("fuente_excel_sha256"), datos.get("descargado_el")),
                (datos.get("fuente_ine"), datos.get("fuente_ine_sha256"), datos.get("descargado_el")),
            ):
                if url and huella:
                    salida.append(
                        {
                            "nombre": f"{ruta_relativa} · {url.rsplit('/', 1)[-1]}",
                            "url": url,
                            "sha256": huella,
                            "descargado_el": cuando or "",
                        }
                    )
    return salida


def _filas_del_excel(contenido: bytes) -> int | None:
    """Cuenta las filas de la hoja más llena de un Excel. `None` si no se puede leer."""
    import io

    from openpyxl import load_workbook

    try:
        libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 — un fichero que no abre es «no lo sé», no un fallo
        return None
    cuantas = 0
    for nombre in libro.sheetnames:
        hoja = libro[nombre]
        cuantas = max(
            cuantas,
            sum(1 for fila in hoja.iter_rows(values_only=True) if any(c is not None for c in fila)),
        )
    return cuantas or None


def _filas_apuntadas(fuente: dict) -> int | None:
    """Las filas que se contaron al bajarlo, sacadas del texto que se guardó («124 filas en…»)."""
    import re

    encontrado = re.match(r"\s*(\d+)\s+filas", fuente.get("comprobado") or "")
    return int(encontrado.group(1)) if encontrado else None


def comprueba(cliente: httpx.Client, fuente: dict) -> dict:
    """Pide una dirección y compara su huella con la que se guardó."""
    if fuente.get("aviso"):
        return {**fuente, "resultado": "sin_datos"}
    time.sleep(SEGUNDOS_ENTRE_PETICIONES)

    # **No todo se pide con un GET.** Las tablas del MAPA son un POST con un formulario
    # (`tipoExportacion=Unidades`), y sin repetir la petición igual no se puede comprobar la huella:
    # la dirección sola contesta «método no permitido».
    peticion = fuente.get("peticion") or {}
    generado = bool(peticion)
    try:
        if (peticion.get("metodo") or "GET").upper() == "POST":
            respuesta = cliente.post(fuente["url"], data=peticion.get("datos") or {})
        else:
            respuesta = cliente.get(fuente["url"])
    except httpx.HTTPError as error:
        return {**fuente, "resultado": "no_se_pudo", "detalle": f"{type(error).__name__}: {error}"}
    if respuesta.status_code != 200:
        return {**fuente, "resultado": "no_se_pudo", "detalle": f"ha contestado {respuesta.status_code}"}

    comun = {
        **fuente,
        "huella_ahora": hashlib.sha256(respuesta.content).hexdigest(),
        "bytes": len(respuesta.content),
        "ultima_modificacion": respuesta.headers.get("last-modified", ""),
    }

    # Un listado que el servidor **genera cada vez** (las exportaciones del MAPA) lleva dentro la hora
    # a la que se generó: su huella cambia siempre aunque los datos sean los mismos. Ahí lo que se
    # compara es **cuántas filas trae**, que es lo que de verdad dice si el catálogo ha cambiado.
    if generado:
        filas_ahora = _filas_del_excel(respuesta.content)
        filas_antes = _filas_apuntadas(fuente)
        if filas_ahora is None or filas_antes is None:
            return {**comun, "resultado": "no_se_pudo", "detalle": "no se han podido contar las filas"}
        return {
            **comun,
            "resultado": "igual" if filas_ahora == filas_antes else "ha_cambiado",
            "filas_ahora": filas_ahora,
            "filas_antes": filas_antes,
        }

    return {**comun, "resultado": "igual" if comun["huella_ahora"] == fuente["sha256"] else "ha_cambiado"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Comprueba que los datos oficiales siguen igual.")
    parser.add_argument("--solo", default="", help="comprueba solo las fuentes que contengan este texto")
    argumentos = parser.parse_args()

    fuentes = _fuentes()
    if argumentos.solo:
        fuentes = [fuente for fuente in fuentes if argumentos.solo.lower() in fuente["nombre"].lower()]
    if not fuentes:
        print("No hay ninguna fuente que comprobar (¿falta algún procedencia.json?).")
        return 1

    print(f"Comprobando {len(fuentes)} fuentes oficiales contra lo que hay bajado.\n")
    resultados = []
    with httpx.Client(timeout=ESPERA, follow_redirects=True, headers=CABECERAS) as cliente:
        for fuente in fuentes:
            print(f"— {fuente['nombre']}")
            resultado = comprueba(cliente, fuente)
            resultados.append(resultado)
            if resultado["resultado"] == "igual":
                if resultado.get("filas_ahora"):
                    # Este listado lo genera el servidor cada vez: lo que se ha comparado es su
                    # contenido (las filas), no su huella, que cambia siempre.
                    print(
                        f"  OK        mismas filas ({resultado['filas_ahora']:,} filas; "
                        "la huella no se compara porque el fichero se genera al pedirlo)"
                    )
                else:
                    print(f"  OK        sigue igual ({resultado['bytes']:,} bytes)")
            elif resultado["resultado"] == "ha_cambiado":
                if resultado.get("filas_ahora"):
                    print("  CAMBIADO  el listado trae otras filas")
                    print(f"            se bajó con: {resultado['filas_antes']:,} filas")
                    print(f"            ahora:       {resultado['filas_ahora']:,} filas")
                else:
                    print("  CAMBIADO  la fuente ya no es la que se bajó")
                    print(f"            guardada: {resultado['sha256']}")
                    print(f"            ahora:    {resultado['huella_ahora']}")
                if resultado["ultima_modificacion"]:
                    print(f"            última modificación en el servidor: {resultado['ultima_modificacion']}")
            elif resultado["resultado"] == "no_se_pudo":
                print(f"  NO SÉ     no se ha podido comprobar: {resultado['detalle']}")
                print("            («no lo sé» no es «ha cambiado»)")
            else:
                print(f"  SIN DATOS {resultado.get('aviso')}")

    cambiadas = [r for r in resultados if r["resultado"] == "ha_cambiado"]
    no_sabidas = [r for r in resultados if r["resultado"] in ("no_se_pudo", "sin_datos")]

    print()
    if cambiadas:
        print(f"RESULTADO: {len(cambiadas)} fuentes han cambiado y hay que mirarlas")
        for fuente in cambiadas:
            print(f"  - {fuente['nombre']}")
        print("\nLo que hay que hacer: volver a lanzar el guion de descarga de esa fuente y mirar qué")
        print("ha cambiado ANTES de dar el dato por bueno. Y actualizar la documentación que dé cifras.")
        return 1
    if no_sabidas:
        print(f"RESULTADO: {len(resultados) - len(no_sabidas)} comprobadas y {len(no_sabidas)} sin poder comprobar")
        return 0
    print(f"RESULTADO: las {len(resultados)} fuentes siguen siendo las mismas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
