"""Pone el municipio a las parcelas de ejemplo y vuelve a traer los contornos (09/11/2026).

Las cinco parcelas se dieron de alta **solo con la referencia**, y el SIGPAC no dice el nombre del
municipio: por eso la lista enseñaba «Sin municipio». Se les pone el municipio real (el de su
código INE, 37070) y se vuelven a traer los contornos, porque actualizar una tierra puede dejar
la forma como estaba o vaciarla según el camino, y no se quiere adivinar.
"""

from __future__ import annotations

import sys

import httpx

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8090"
MUNICIPIO = "Calvarrasa de Arriba"
PROVINCIA = "Salamanca"

cliente = httpx.Client(base_url=URL.rstrip("/"), timeout=180.0)
token = cliente.post(
    "/api/cuenta/entrar",
    json={"correo": "demo@cuedigital.local", "clave": "cuaderno-demo-2026"},
).json()["token"]
cabeceras = {"Authorization": f"Bearer {token}"}

tierras = (cliente.get("/api/nuevo/tierras", headers=cabeceras).json().get("tierras")) or []
print(f"tierras: {len(tierras)}")
for tierra in tierras:
    cuerpo = {
        "alias": tierra.get("alias"),
        "ref_sigpac": tierra.get("ref_sigpac"),
        "municipio": MUNICIPIO,
        "provincia": PROVINCIA,
    }
    respuesta = cliente.put(f"/api/parcelas/{tierra['id']}", headers=cabeceras, json=cuerpo)
    estado = respuesta.status_code
    municipio = respuesta.json().get("municipio") if estado == 200 else respuesta.text[:120]
    print(f"  {tierra.get('alias')}: {estado} · municipio={municipio}")

contornos = cliente.post("/api/sigpac/cache/37/contornos?campana=2026", headers=cabeceras, timeout=300.0)
if contornos.status_code == 200:
    datos = contornos.json()
    print(
        "contornos: actualizadas={} sin_forma={} sin_codigos={}".format(
            len(datos.get("actualizadas") or []),
            len(datos.get("sin_forma") or []),
            len(datos.get("sin_codigos") or []),
        )
    )
else:
    print("contornos:", contornos.status_code, contornos.text[:200])

tierras = (cliente.get("/api/nuevo/tierras", headers=cabeceras).json().get("tierras")) or []
print("municipios:", sorted({(t.get("municipio") or "sin") for t in tierras}))
for tierra in tierras:
    foto = cliente.get(f"/api/mapa/tierra/{tierra['id']}.png", headers=cabeceras, timeout=120.0)
    forma = "PNG" if foto.status_code == 200 else f"{foto.status_code} sin forma"
    print(f"  {tierra.get('alias')} ({tierra.get('municipio')}): {forma}")
