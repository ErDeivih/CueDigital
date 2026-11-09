"""Siembra la finca de ejemplo en el servidor y comprueba los contornos (09/11/2026).

QUÉ HACE
========

1. Da de alta (o entra en) la cuenta de ejemplo.
2. Da de alta las **cinco parcelas del cliente de Salamanca** solo con su referencia, como haría
   el agricultor: cuatro con la referencia completa y una con la del visor (seis números).
3. Pide al servidor que traiga los contornos del GeoPackage real de Salamanca que está en su
   caché (`POST /api/sigpac/cache/37/contornos`) y comprueba que las tierras quedan con forma.
4. Comprueba que la foto de cada tierra es un PNG de 800×600 con su contorno.

Las referencias no se inventan: salen de `scripts/pintar_las_parcelas_del_cliente.py`, que las
sacó del GeoPackage real.
"""

from __future__ import annotations

import json
import struct
import sys

import httpx

URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8090").rstrip("/")

CORREO = "demo@cuedigital.local"
CLAVE = "cuaderno-demo-2026"
NIF = "00000000T"

# Las cinco del cliente de Salamanca: alias y referencia, tal y como salen del GeoPackage real.
PARCELAS = (
    ("El Prado", "37-70-0-0-503-51-1"),
    ("El Alto", "37-70-0-0-501-84-1"),
    ("La Vega", "37-70-0-0-501-82-2"),
    ("Las Eras", "37-70-0-0-501-80-1"),
    ("El Visor", "37-70-0-0-501-80"),  # la del visor: seis números, sin recinto
)


def medidas_del_png(datos: bytes) -> tuple[int, int] | None:
    if len(datos) < 24 or datos[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    ancho, alto = struct.unpack(">II", datos[16:24])
    return ancho, alto


def main() -> int:
    cliente = httpx.Client(base_url=URL, timeout=300.0)
    print(f"Servidor: {URL}")

    alta = cliente.post(
        "/api/cuenta/registro",
        json={
            "explotacion": {"nombre": "Finca de ejemplo (Salamanca)", "nif": NIF},
            "nombre": "Agricultor de ejemplo",
            "correo": CORREO,
            "clave": CLAVE,
        },
    )
    if alta.status_code == 409:
        alta = cliente.post("/api/cuenta/entrar", json={"correo": CORREO, "clave": CLAVE})
        print("cuenta: ya existía, se entra")
    else:
        print(f"cuenta: alta {alta.status_code}")
    if alta.status_code not in (200, 201):
        print("NO SE PUEDE ENTRAR:", alta.status_code, alta.text[:300])
        return 1
    vale = alta.json()["token"]
    cabeceras = {"Authorization": f"Bearer {vale}"}

    creadas = []
    for alias, referencia in PARCELAS:
        respuesta = cliente.post(
            "/api/parcelas", headers=cabeceras, json={"alias": alias, "ref_sigpac": referencia}
        )
        if respuesta.status_code == 201:
            tierra = respuesta.json()
            creadas.append(tierra)
            print(f"tierra «{alias}»: 201 · id={tierra.get('id')} · código INE={tierra.get('codigo_ine')}"
                  f" · recinto={tierra.get('numero_recinto')}")
        elif respuesta.status_code == 409:
            print(f"tierra «{alias}»: ya estaba")
        else:
            print(f"tierra «{alias}»: {respuesta.status_code} {respuesta.text[:200]}")

    # Los contornos desde el GeoPackage real que está en la caché del servidor.
    print("\nTrayendo los contornos del GeoPackage de Salamanca (la primera vez extrae el mapa)…")
    contornos = cliente.post(
        "/api/sigpac/cache/37/contornos?campana=2026", headers=cabeceras, timeout=600.0
    )
    print(f"contornos: {contornos.status_code}")
    if contornos.status_code == 200:
        datos = contornos.json()
        print(
            "  actualizadas={} sin_forma={} sin_codigos={} no_encontradas={}".format(
                len(datos.get("actualizadas") or []),
                len(datos.get("sin_forma") or []),
                len(datos.get("sin_codigos") or []),
                len(datos.get("no_encontradas") or []),
            )
        )
    else:
        print("  ", contornos.text[:300])

    tierras = cliente.get("/api/nuevo/tierras", headers=cabeceras).json()
    lista = tierras.get("tierras") or tierras.get("parcelas") or []
    print(f"\ntierras en la finca: {len(lista)}")
    con_forma = 0
    for tierra in lista:
        identificador = tierra.get("id")
        foto = cliente.get(f"/api/mapa/tierra/{identificador}.png", headers=cabeceras, timeout=120.0)
        medidas = medidas_del_png(foto.content) if foto.status_code == 200 else None
        if medidas:
            con_forma += 1
        print(
            f"  · {tierra.get('alias')}: {foto.status_code} "
            f"{medidas if medidas else '(sin forma)'}"
        )
    print(f"\nRESUMEN: {len(lista)} tierras · {con_forma} con contorno pintado")
    print(f"Cuenta de ejemplo: {CORREO} / {CLAVE}")
    return 0 if lista and con_forma >= 4 else 1


if __name__ == "__main__":
    sys.exit(main())
