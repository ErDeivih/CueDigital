"""Bajar las capturas de los diseños que generó Stitch, para poder mirarlos sin abrir el navegador.

Los ficheros de `docs/stitch/` guardan lo que contestó Stitch: además del HTML de cada pantalla, la
**dirección de su captura**. Esto la descarga y la deja al lado, en `docs/stitch/`, con el nombre de
la pantalla: así se pueden mirar (y enseñárselas al agricultor) sin depender de que la dirección siga
viva, que es de Google y caduca.

No toca ningún diseño ni genera nada nuevo: solo trae la imagen que Stitch ya hizo.
"""

from __future__ import annotations

import json
import pathlib

import httpx

CARPETA = pathlib.Path(__file__).resolve().parents[2] / "docs" / "stitch"


def main() -> int:
    fallos: list[str] = []
    for ruta in sorted(CARPETA.glob("pantalla_*.json")):
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        for componente in datos.get("outputComponents") or []:
            for pantalla in (componente.get("design") or {}).get("screens") or []:
                captura = (pantalla.get("screenshot") or {}).get("downloadUrl")
                titulo = pantalla.get("title") or pantalla.get("id") or "pantalla"
                if not captura:
                    fallos.append(f"{ruta.name}: sin captura")
                    continue
                destino = CARPETA / f"{ruta.stem}.png"
                if destino.exists():
                    print(f"Ya está: {destino.name}")
                    continue
                try:
                    respuesta = httpx.get(captura, timeout=120.0, follow_redirects=True)
                    respuesta.raise_for_status()
                except httpx.HTTPError as error:
                    fallos.append(f"{ruta.name} ({titulo}): {type(error).__name__}")
                    continue
                if respuesta.content[:8] != b"\x89PNG\r\n\x1a\n":
                    fallos.append(f"{ruta.name}: lo que ha llegado no es un PNG")
                    continue
                destino.write_bytes(respuesta.content)
                print(f"Guardada {destino.name} ({len(respuesta.content):,} bytes) — {titulo}")

    if fallos:
        print("\nNo se han podido bajar todas:")
        for fallo in fallos:
            print(f"  - {fallo}")
        return 1
    print(f"\nTodas las capturas están en {CARPETA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
