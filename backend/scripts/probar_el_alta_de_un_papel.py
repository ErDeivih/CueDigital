"""***Probar si se puede subir un papel a la bandeja*** (22/10/2026, D05).

*El cuarto recorrido empieza por un papel. Esto solo mira **si la puerta acepta uno** y que contesta, para saber si el
recorrido se puede andar sin proveedor de OCR o no.*

Uso:  python scripts/probar_el_alta_de_un_papel.py
"""

from __future__ import annotations

import base64
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from verificar_los_permisos_por_rol import _una_cuenta_nueva  # noqa: E402

# *Un PNG de 1x1, que es un fichero de verdad y no pesa nada.*
EL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def main() -> int:
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "papel@prueba.local", "una-clave-larga-y-facil", "Pa")
        el_vale = cuenta["token"]
        print(f"== Un papel en la bandeja  ({direccion}) ==")
        # *Multipart a mano: un campo `fichero` y los datos.*
        el_limite = "----prueba"
        los_datos = json.dumps({"titulo": "PAPEL DE LA PRUEBA"}).encode("utf-8")
        el_cuerpo = b"".join([
            f"--{el_limite}\r\n".encode(),
            b'Content-Disposition: form-data; name="datos"\r\n\r\n',
            los_datos,
            b"\r\n",
            f"--{el_limite}\r\n".encode(),
            b'Content-Disposition: form-data; name="fichero"; filename="papel.png"\r\n',
            b"Content-Type: image/png\r\n\r\n",
            EL_PNG,
            b"\r\n",
            f"--{el_limite}--\r\n".encode(),
        ])
        la_peticion = urllib.request.Request(
            f"{direccion}/api/bandeja",
            data=el_cuerpo,
            method="POST",
            headers={
                "Authorization": f"Bearer {el_vale}",
                "Content-Type": f"multipart/form-data; boundary={el_limite}",
            },
        )
        try:
            with urllib.request.urlopen(la_peticion, timeout=30) as la_respuesta:
                print(f"  codigo: {la_respuesta.status}")
                print(f"  contesta: {la_respuesta.read().decode('utf-8', 'replace')[:500]}")
        except urllib.error.HTTPError as el_error:
            print(f"  codigo: {el_error.code}")
            print(f"  contesta: {el_error.read().decode('utf-8', 'replace')[:500]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
