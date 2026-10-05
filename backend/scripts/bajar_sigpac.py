r"""Baja los datos oficiales del SIGPAC que usa la aplicación.

Se guardan en `data/sigpac/` porque son datos oficiales que cambian poco (los recintos se
actualizan cada campaña y los códigos casi nunca) y porque **los tests no pueden depender de
que haya internet**. Lo que se baja aquí es lo que después leen los tests: así un test prueba
el parser contra una respuesta de verdad del SIGPAC, no contra una inventada.

Fuentes (públicas, sin autenticación, documentadas en
`F:\CuadernoCampo\06_FEGA_servicios_SIGPAC_nube.pdf`):

  * Consultas SIGPAC:  https://sigpac-hubcloud.es/servicioconsultassigpac/query/...
  * Listas de códigos: https://sigpac-hubcloud.es/codigossigpac/...
  * OGC API Features:  https://sigpac-hubcloud.es/ogcapi

Los cinco ficheros de códigos están bajo licencia Creative Commons BY 4.0 según el documento
del FEGA (Reglamento de Ejecución 2023/138, conjunto de datos de alto valor), así que se pueden
guardar y redistribuir diciendo de dónde salen.

Uso:
    python scripts/bajar_sigpac.py
"""

from __future__ import annotations

import json
import pathlib

import httpx

BASE_CONSULTAS = "https://sigpac-hubcloud.es/servicioconsultassigpac"
BASE_CODIGOS = "https://sigpac-hubcloud.es/codigossigpac"
BASE_OGC = "https://sigpac-hubcloud.es/ogcapi"

DESTINO = pathlib.Path(__file__).resolve().parents[2] / "data" / "sigpac"

# Los cinco listados de códigos que el servicio publica y que la aplicación usa.
CODIGOS = ("cod_uso_sigpac", "cod_producto", "cod_aprovechamiento", "cod_incidencia", "cod_region_2023")

# Un recinto de verdad para poder probar el parser sin internet: uno de Salamanca, en la zona
# donde el agricultor de las pruebas tiene la finca. Se busca por coordenadas con la OGC API,
# que es lo que permite encontrar uno sin inventarse la referencia.
#
# Es **tierra de labor** (uso TA, 2,7923 ha) y no un improductivo de 375 m², porque un ejemplo
# tiene que parecerse a lo que el agricultor va a traer de verdad. La referencia está fijada en
# los tests: si se cambia aquí, hay que cambiarla también allí.
CONSULTA_DE_EJEMPLO = "recinfo/37/22/0/0/501/427/1"

# Y una parcela de verdad con todos sus recintos, para probar sin internet la búsqueda que es
# lo que hace falta para dar de alta una parcela sin saberse el número del recinto. Esta es la
# parcela del agricultor: en el visor del SIGPAC sale como `37:70:0:0:503:51`, con un solo
# recinto de 4,9016 ha, pendiente 1 y altitud 837.
BUSQUEDA_DE_EJEMPLO = "collections/recintos/items?provincia=37&municipio=70&poligono=503&parcela=51&limit=50&f=json"

# El recinto concreto de esa misma parcela, para poder probar la búsqueda entera —la lista de
# trozos y los datos de cada uno— con las dos respuestas de verdad de la misma parcela.
RECINTO_DE_LA_BUSQUEDA = "recinfo/37/70/0/0/503/51/1"

# **Un punto de esa parcela.** Con él se prueban las dos consultas que hacen posible elegir la
# parcela tocando el mapa: las propiedades del recinto que contiene el punto y su referencia.
# El punto es el de la primera esquina del recinto que devuelve el SIGPAC, así que se sabe que
# cae dentro.
PUNTO_DE_EJEMPLO = ("4326", "-5.55470", "40.90730")

# **La parcela del agricultor**: con sus códigos se piden su referencia catastral (la del
# Catastro, que el contenido mínimo del CUE pide) y todos sus recintos.
PARCELA_DE_EJEMPLO = "37/70/0/0/503/51"

# **Un recinto que SÍ está en zona vulnerable a nitratos**, para poder probar una intersección
# con resultado positivo y no solo una vacía. Es uno de El Bohodón (Ávila), municipio que está
# en el listado oficial de zonas vulnerables (código INE 05036).
RECINTO_EN_NITRATOS = "5/36/0/0/6/5015/3"


def _guardar_json(cliente, url: str, destino, nombre: str) -> bool:
    respuesta = cliente.get(url)
    if respuesta.status_code != 200:
        print(f"FALLO  {nombre}: {respuesta.status_code}")
        return False
    destino.write_text(
        json.dumps(respuesta.json(), ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
    )
    print(f"OK     {nombre}, {destino.stat().st_size // 1024} KB")
    return True


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    cliente = httpx.Client(timeout=30.0, follow_redirects=True)

    print(f"Guardando en {DESTINO}\n")

    for nombre in CODIGOS:
        url = f"{BASE_CODIGOS}/{nombre}.json"
        respuesta = cliente.get(url)
        if respuesta.status_code != 200:
            print(f"FALLO  {nombre}: {respuesta.status_code}")
            continue
        datos = respuesta.json()
        cuantos = len(datos.get("codigos", []))
        ruta = DESTINO / f"{nombre}.json"
        ruta.write_text(
            json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
        )
        print(f"OK     {nombre}: {cuantos} códigos, {ruta.stat().st_size // 1024} KB")

    # Y un recinto de ejemplo, para que los tests prueben el parser contra una respuesta real.
    url = f"{BASE_CONSULTAS}/query/{CONSULTA_DE_EJEMPLO}.json"
    respuesta = cliente.get(url)
    if respuesta.status_code == 200:
        ruta = DESTINO / "recinto_de_ejemplo.json"
        ruta.write_text(
            json.dumps(respuesta.json(), ensure_ascii=False, indent=1),
            encoding="utf-8",
            newline="\n",
        )
        print(f"OK     recinto de ejemplo ({CONSULTA_DE_EJEMPLO}), {ruta.stat().st_size // 1024} KB")
    else:
        print(f"FALLO  el recinto de ejemplo: {respuesta.status_code}")

    # Y los recintos de una parcela entera, que es la consulta que permite enseñarle al
    # agricultor los trozos que hay en su parcela para que marque los suyos.
    url = f"{BASE_OGC}/{BUSQUEDA_DE_EJEMPLO}"
    respuesta = cliente.get(url)
    if respuesta.status_code == 200:
        datos = respuesta.json()
        ruta = DESTINO / "recintos_de_ejemplo.json"
        ruta.write_text(
            json.dumps(datos, ensure_ascii=False, indent=1),
            encoding="utf-8",
            newline="\n",
        )
        print(
            f"OK     recintos de ejemplo ({datos.get('numberReturned')} trozos), "
            f"{ruta.stat().st_size // 1024} KB"
        )
    else:
        print(f"FALLO  los recintos de ejemplo: {respuesta.status_code}")

    # Y el recinto concreto de esa parcela, para poder probar la búsqueda entera.
    url = f"{BASE_CONSULTAS}/query/{RECINTO_DE_LA_BUSQUEDA}.json"
    respuesta = cliente.get(url)
    if respuesta.status_code == 200:
        ruta = DESTINO / "recinto_de_ejemplo_503_51.json"
        ruta.write_text(
            json.dumps(respuesta.json(), ensure_ascii=False, indent=1),
            encoding="utf-8",
            newline="\n",
        )
        print(f"OK     recinto de la parcela 503/51, {ruta.stat().st_size // 1024} KB")
    else:
        print(f"FALLO  el recinto de la parcela 503/51: {respuesta.status_code}")

    # ---------------------------------------------------------------- el mapa y las fichas
    # Las consultas que hacen posible elegir la parcela tocando el mapa y rellenar su ficha sin
    # que el agricultor teclee nada. Todas comprobadas contra el servicio de verdad el 24/09/2026.
    srid, x, y = PUNTO_DE_EJEMPLO
    _guardar_json(
        cliente,
        f"{BASE_CONSULTAS}/query/recinfobypoint/{srid}/{x}/{y}.json",
        DESTINO / "recinto_de_un_punto.json",
        "recinto que contiene un punto (tocar el mapa)",
    )
    _guardar_json(
        cliente,
        f"{BASE_CONSULTAS}/query/refrecinbycoord/{srid}/{x}/{y}.json",
        DESTINO / "referencia_de_un_punto.json",
        "referencia del recinto de un punto",
    )
    _guardar_json(
        cliente,
        f"{BASE_CONSULTAS}/query/refcatparcela/{PARCELA_DE_EJEMPLO}.json",
        DESTINO / "referencia_catastral_de_la_parcela.json",
        "referencia catastral de la parcela 503/51",
    )
    _guardar_json(
        cliente,
        f"{BASE_CONSULTAS}/query/recinfoparc/{PARCELA_DE_EJEMPLO}.json",
        DESTINO / "recintos_de_la_parcela.json",
        "todos los recintos de la parcela 503/51",
    )
    _guardar_json(
        cliente,
        f"{BASE_CONSULTAS}/intersection/nitratos/{RECINTO_EN_NITRATOS}.json",
        DESTINO / "interseccion_nitratos_si.json",
        "intersección CON nitratos (ejemplo positivo)",
    )
    _guardar_json(
        cliente,
        f"{BASE_CONSULTAS}/intersection/nitratos/{RECINTO_DE_LA_BUSQUEDA.split('recinfo/')[1]}.json",
        DESTINO / "interseccion_nitratos_no.json",
        "intersección SIN nitratos (la parcela del agricultor)",
    )

    # Se deja escrito de dónde sale todo, para que nadie tenga que buscarlo.
    (DESTINO / "LEEME.md").write_text(
        "# Datos oficiales del SIGPAC\n\n"
        "Estos ficheros **no los ha escrito nadie a mano**: los baja "
        "`backend/scripts/bajar_sigpac.py` de los servicios públicos del SIGPAC.\n\n"
        "| Fichero | De dónde sale |\n|---|---|\n"
        f"| `cod_uso_sigpac.json` | `{BASE_CODIGOS}/cod_uso_sigpac.json` |\n"
        f"| `cod_producto.json` | `{BASE_CODIGOS}/cod_producto.json` |\n"
        f"| `cod_aprovechamiento.json` | `{BASE_CODIGOS}/cod_aprovechamiento.json` |\n"
        f"| `cod_incidencia.json` | `{BASE_CODIGOS}/cod_incidencia.json` |\n"
        f"| `cod_region_2023.json` | `{BASE_CODIGOS}/cod_region_2023.json` |\n"
        f"| `recinto_de_ejemplo.json` | `{BASE_CONSULTAS}/query/{CONSULTA_DE_EJEMPLO}.json` |\n"
        f"| `recintos_de_ejemplo.json` | `{BASE_OGC}/{BUSQUEDA_DE_EJEMPLO}` |\n"
        f"| `recinto_de_ejemplo_503_51.json` | `{BASE_CONSULTAS}/query/{RECINTO_DE_LA_BUSQUEDA}.json` |\n"
        f"| `recinto_de_un_punto.json` | `{BASE_CONSULTAS}/query/recinfobypoint/{PUNTO_DE_EJEMPLO[0]}/{PUNTO_DE_EJEMPLO[1]}/{PUNTO_DE_EJEMPLO[2]}.json` |\n"
        f"| `referencia_de_un_punto.json` | `{BASE_CONSULTAS}/query/refrecinbycoord/{PUNTO_DE_EJEMPLO[0]}/{PUNTO_DE_EJEMPLO[1]}/{PUNTO_DE_EJEMPLO[2]}.json` |\n"
        f"| `referencia_catastral_de_la_parcela.json` | `{BASE_CONSULTAS}/query/refcatparcela/{PARCELA_DE_EJEMPLO}.json` |\n"
        f"| `recintos_de_la_parcela.json` | `{BASE_CONSULTAS}/query/recinfoparc/{PARCELA_DE_EJEMPLO}.json` |\n"
        f"| `interseccion_nitratos_si.json` | `{BASE_CONSULTAS}/intersection/nitratos/{RECINTO_EN_NITRATOS}.json` |\n"
        f"| `interseccion_nitratos_no.json` | `{BASE_CONSULTAS}/intersection/nitratos/37/70/0/0/503/51/1.json` |\n\n"
        "Las once consultas del servicio están documentadas, con su dirección exacta, en\n"
        "`https://sigpac-hubcloud.es/html/csp/descServicio.html` (una página de ejemplo por\n"
        "consulta). El catálogo de servicios es `https://sigpac-hubcloud.es/`.\n\n"
        "Servicio de listas de códigos y de consultas de SIGPAC, del FEGA. Publicados bajo\n"
        "licencia Creative Commons BY 4.0 según el documento «Publicación de nuevos servicios\n"
        "SIGPAC de consulta y divulgación de datos del SIGC» (Reglamento de Ejecución\n"
        "2023/138, conjunto de datos de alto valor).\n\n"
        "Para actualizarlos: `python scripts/bajar_sigpac.py` desde `backend/`.\n",
        encoding="utf-8",
        newline="\n",
    )
    print("\nEscrito el LEEME.md con la procedencia de cada fichero.")
    cliente.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
