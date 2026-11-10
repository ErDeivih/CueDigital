"""Saca de la finca de ejemplo todo lo que necesita la demo estática (10/11/2026).

La demo de GitHub Pages **no puede depender del servidor de casa** (ni del túnel, que cambia de
dirección). Así que se copia aquí lo que el servidor devuelve para las pantallas que se van a
poder enseñar: el vocabulario, la finca con sus cinco parcelas y sus anillos, la ficha de cada
tierra, el resumen, lo que falta, el calendario, los trabajos y la búsqueda del SIGPAC para el
alta por referencia.

Lo que se guarda es **copia literal** de lo que contesta el servidor: no se inventa nada.
"""

from __future__ import annotations

import json
import pathlib
import sys

import httpx

RAIZ = pathlib.Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "deploy" / "paginas_github" / "demo"
URL = (sys.argv[1] if len(sys.argv) > 1 else "").rstrip("/")
if not URL:
    raise SystemExit("Falta la URL: python deploy/paginas_github/sacar_datos_demo.py https://…")

# **Las referencias de las cinco parcelas del cliente**, sacadas del GeoPackage real (están en
# deploy/paginas_github/sembrar_finca_ejemplo.py). La respuesta de «tierras» no trae la
# referencia, así que se escriben aquí: son datos del cliente, no inventados.
REFERENCIAS = (
    "37-70-0-0-503-51-1",  # El Prado
    "37-70-0-0-501-84-1",  # El Alto
    "37-70-0-0-501-82-2",  # La Vega
    "37-70-0-0-501-80-1",  # Las Eras
    "37-70-0-0-501-80",    # El Visor (seis números, sin recinto)
)
# Y una que **no** está en la finca (la parcela real de dos recintos), para poder enseñar el alta
# de una tierra nueva en la demo. Y una de seis números.
PARA_EL_ALTA = ("37-2-0-0-502-1", "37-70-0-0-501-84")

cliente = httpx.Client(base_url=URL, timeout=120.0)
token = cliente.post(
    "/api/cuenta/entrar",
    json={"correo": "demo@cuedigital.local", "clave": "cuaderno-demo-2026"},
).json()["token"]
cabeceras = {"Authorization": f"Bearer {token}"}

SALIDA.mkdir(parents=True, exist_ok=True)
datos: dict[str, object] = {}

for clave, ruta in (
    ("interfaz", "/api/interfaz"),
    ("cuenta", "/api/cuenta/yo"),
    ("hoy", "/api/nuevo/hoy"),
    ("tierras", "/api/nuevo/tierras"),
    ("resumen", "/api/nuevo/resumen"),
    ("que_falta", "/api/nuevo/que-falta"),
    ("trabajos", "/api/nuevo/trabajos"),
    ("calendario", "/api/nuevo/calendario"),
    ("facturas", "/api/facturas"),
    ("documentos", "/api/documentos"),
):
    respuesta = cliente.get(ruta, headers=cabeceras)
    print(f"{ruta}: {respuesta.status_code}")
    if respuesta.status_code == 200:
        datos[clave] = respuesta.json()

tierras = (datos.get("tierras") or {}).get("tierras") or []
for tierra in tierras:
    ruta = f"/api/nuevo/tierra/{tierra['id']}"
    respuesta = cliente.get(ruta, headers=cabeceras)
    print(f"{ruta}: {respuesta.status_code}")
    if respuesta.status_code == 200:
        datos[f"tierra_{tierra['id']}"] = respuesta.json()

datos["referencias"] = list(REFERENCIAS)
busquedas: dict[str, object] = {}
for referencia in (*REFERENCIAS, *PARA_EL_ALTA):
    respuesta = cliente.post("/api/sigpac/buscar", headers=cabeceras, json={"referencia": referencia})
    print(f"buscar {referencia}: {respuesta.status_code}")
    if respuesta.status_code == 200:
        busquedas[referencia] = respuesta.json()
datos["busquedas"] = busquedas

(SALIDA / "datos.json").write_text(
    json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline=""
)
ruta_json = SALIDA / "datos.json"
print(f"\nGuardado {ruta_json} ({ruta_json.stat().st_size // 1024} KB)")
print("claves:", ", ".join(sorted(datos)))
