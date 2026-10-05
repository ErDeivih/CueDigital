"""Probar el interfaz de la Junta (IUWS) con llamadas de verdad, y contar lo que contesta.

## Para qué sirve esto

La tarea pendiente más importante del cuaderno digital es **presentarlo por el interfaz de la Junta**.
Antes de montar nada hace falta saber **qué contesta el interfaz de verdad** en cada llamada, y sobre
todo **dónde se corta**: si el corte está en la conexión (el servidor exige un certificado para
siquiera hablar) o en la aplicación (la conexión va y contesta que no estás autorizado). No es lo
mismo:

* Si es **en la conexión**, el programa no puede presentar nada por su cuenta con el certificado que
  está en el almacén de Windows: la clave privada no se puede sacar de ahí, y `httpx` (que va con
  OpenSSL) no sabe usar una clave que vive en el almacén. Habría que presentarlo desde Windows.
* Si es **en la aplicación** (401/403 con el certificado en la cabecera), entonces el camino es
  mandar el certificado y el dato firmado, y el corte está solo en la firma.

Y esto **no se puede deducir de un documento**: se pregunta y se apunta lo que conteste.

## Qué hace exactamente, y qué NO hace

Hace **dos llamadas por dirección**: la de la versión (que el anexo declara abierta) y la del token
sin certificado. **No manda ni un dato del agricultor**: no se llama a `crear`, ni a `exportar`, ni a
`exportarREA`, que son las que llevan su NIF y sus parcelas. Tampoco se intenta ninguna firma.

Se ejecuta así:

```bash
cd backend
../.venv/Scripts/python.exe scripts/probar_iuws.py
```

Con `CUEDIGITAL_IUWS_BASE` se prueba además la dirección que esté configurada. Esto **no es un test**:
los tests no tocan la red. Esto es una comprobación a mano, como `humo.py`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402  (va después de ajustar la ruta, a propósito)

from app import iuws  # noqa: E402


def _resumen_de_la_respuesta(respuesta: httpx.Response) -> str:
    cuerpo = respuesta.text.strip().replace("\n", " ")[:160]
    return f"{respuesta.status_code} {respuesta.headers.get('content-type', '')} {cuerpo}".strip()


def _prueba(nombre: str, url: str) -> dict:
    """Una llamada de verdad, sin certificado, y lo que contesta."""
    print(f"\n{nombre}\n  {url}")
    try:
        with httpx.Client(timeout=iuws.ESPERA_SEGUNDOS) as cliente:
            respuesta = cliente.get(url)
    except Exception as error:  # noqa: BLE001 — aquí interesa hasta el tipo de fallo
        # Un fallo de la conexión NO es lo mismo que un «no autorizado»: si el servidor exige
        # certificado para hablar, aquí es donde se ve, y sale con el nombre del error.
        print(f"  NO SE HA PODIDO HABLAR: {type(error).__name__}: {error}")
        return {"url": url, "corta_en_la_conexion": True, "error": f"{type(error).__name__}: {error}"}

    print(f"  CONTESTA: {_resumen_de_la_respuesta(respuesta)}")
    autenticacion = respuesta.headers.get("www-authenticate")
    if autenticacion:
        print(f"  PIDE AUTENTICACIÓN: {autenticacion}")
    return {
        "url": url,
        "corta_en_la_conexion": False,
        "codigo": respuesta.status_code,
        "autenticacion": autenticacion,
        "cuerpo": respuesta.text.strip()[:300],
    }


def main() -> int:
    bases: list[tuple[str, str]] = [("entorno de integración", iuws.ENTORNO_INTEGRACION)]
    for nombre, base in iuws.BASES_POR_CCAA.items():
        bases.append((f"producción · {nombre}", base))
    configurada = (os.environ.get("CUEDIGITAL_IUWS_BASE") or "").strip()
    if configurada and all(configurada != base for _n, base in bases):
        bases.append(("la que está configurada en este ordenador", configurada))

    print("Probando el interfaz de la Junta (IUWS) con llamadas de verdad, sin certificado.")
    print("Solo se llama a la versión y al token: no se manda ningún dato del agricultor.")

    resultados = []
    for nombre, base in bases:
        print(f"\n=== {nombre}: {base}")
        resultados.append(_prueba("1. La versión (el anexo dice que no está securizada)", iuws.url_version(base)))
        resultados.append(
            _prueba(
                "2. El token, sin certificado (aquí se ve dónde se corta)",
                iuws.url_comunicacion(base, "PRUEBA"),
            )
        )

    print("\n--- Resumen")
    for resultado in resultados:
        if resultado["corta_en_la_conexion"]:
            print(f"  · {resultado['url']}\n      corta en la CONEXIÓN: {resultado['error']}")
        else:
            print(f"  · {resultado['url']}\n      contesta {resultado['codigo']}")

    print(
        "\nLo que se saque de aquí **no se inventa**: se apunta en `app/iuws.py` (lo comprobado\n"
        "contra el interfaz) y en `docs/INTEGRACION_IUWS.md`, con la fecha."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
