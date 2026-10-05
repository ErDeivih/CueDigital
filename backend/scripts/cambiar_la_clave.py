"""Cambiar la clave de una cuenta desde este ordenador, para cuando no se puede entrar.

## Por qué existe esto

Este programa **no manda correos**: es un programa que vive en el ordenador del agricultor (o en su
servidor), y no hay ningún servicio de correo detrás. Eso quiere decir que, si algún día **se olvida
de la clave**, no hay un «he olvidado mi contraseña» que le mande un enlace: se quedaría fuera de su
propio cuaderno, que es justo lo que no puede pasar.

La salida es esta: **cambiar la clave desde el propio ordenador donde está el programa**, con acceso
al fichero de la base de datos. Quien puede ejecutar esto ya tiene el cuaderno entero en su mano, así
que no abre ninguna puerta que no estuviera abierta: lo único que hace es volver a poner una clave.

## Cómo se usa

```bash
cd backend
# Ver qué cuentas hay (correo y nombre; nunca la clave ni su huella)
../.venv/Scripts/python.exe scripts/cambiar_la_clave.py --listar

# Cambiar la clave de una cuenta (la pide por teclado, sin dejarla escrita en el historial)
../.venv/Scripts/python.exe scripts/cambiar_la_clave.py --correo david@ejemplo.es

# O darla en el momento (ojo: queda en el historial de la consola)
../.venv/Scripts/python.exe scripts/cambiar_la_clave.py --correo david@ejemplo.es --clave "la-nueva"
```

Se usa **la misma función que usa el programa** para guardar las claves (`security.hash_clave`), así
que la clave nueva queda tan protegida como la que se puso al registrarse. Y **no se puede bajar de 8
caracteres**, porque es la misma regla que aplica el alta.

## Qué NO hace

- **No borra ni cambia nada más**: ni las parcelas, ni los apuntes, ni el correo.
- **No dice la clave vieja**: no se puede, está guardada como huella (que es como tiene que estar).
- **No inventa un correo**: si el correo que le das no existe, lo dice y no toca nada.
"""

from __future__ import annotations

import argparse
import getpass
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402  (va después de ajustar la ruta, a propósito)

from app import database, models, security  # noqa: E402


def _cuentas(sesion) -> list[models.Usuario]:
    return list(sesion.scalars(select(models.Usuario).order_by(models.Usuario.id)))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cambia la clave de una cuenta desde este ordenador."
    )
    parser.add_argument("--correo", default="", help="el correo de la cuenta")
    parser.add_argument("--clave", default="", help="la clave nueva (si no se pasa, se pide)")
    parser.add_argument("--listar", action="store_true", help="solo enseña las cuentas que hay")
    argumentos = parser.parse_args()

    url = database.url_base_datos()
    print(f"Base de datos: {url}")
    if url.startswith("sqlite"):
        ruta = pathlib.Path(url.replace("sqlite:///", "").replace("sqlite://", ""))
        if ruta and not ruta.exists() and ruta.name:
            print(f"No encuentro la base de datos en {ruta}.")
            print("Comprueba desde qué carpeta lo lanzas, o pon CUEDIGITAL_DATABASE_URL.")
            return 1

    motor = database.crear_engine()
    with database.SessionLocal(bind=motor) as sesion:
        cuentas = _cuentas(sesion)
        if not cuentas:
            print("No hay ninguna cuenta en esta base de datos.")
            return 1

        if argumentos.listar or not argumentos.correo:
            print(f"\nHay {len(cuentas)} cuenta(s):")
            for cuenta in cuentas:
                print(f"  · {cuenta.correo}  ({cuenta.nombre})")
            if not argumentos.correo:
                print("\nPara cambiar una clave: --correo <el correo de la cuenta>")
            return 0

        buscada = argumentos.correo.strip().lower()
        cuenta = next((u for u in cuentas if (u.correo or "").lower() == buscada), None)
        if cuenta is None:
            print(f"\nNo hay ninguna cuenta con el correo «{argumentos.correo}».")
            print("Míralas con --listar. No se ha tocado nada.")
            return 1

        clave = argumentos.clave
        if not clave:
            # Se pide dos veces y sin enseñarla en pantalla: es la forma de que no acabe en el
            # historial de la consola ni en una captura de pantalla.
            clave = getpass.getpass(f"Clave nueva para {cuenta.correo}: ")
            repetida = getpass.getpass("Repítela: ")
            if clave != repetida:
                print("Las dos claves no son iguales. No se ha cambiado nada.")
                return 1

        if len(clave) < security.LONGITUD_CLAVE_MINIMA:
            print(
                f"La clave tiene que tener al menos {security.LONGITUD_CLAVE_MINIMA} caracteres "
                "(es la misma regla que aplica el alta). No se ha cambiado nada."
            )
            return 1

        cuenta.clave_hash = security.hash_clave(clave)
        sesion.commit()
        print(f"\nHecho: la clave de {cuenta.correo} es la nueva.")
        print("Ya puedes entrar con ella. Lo demás no se ha tocado.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
