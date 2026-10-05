"""Descarga React y `htm` para la interfaz, y los deja dentro del programa.

## Por qué hace falta

David decidió que **la interfaz se rehace en React** («rehaz toda la ui con react aunque haya que
rehacer pruebas»). React, para funcionar en un navegador, son ficheros de JavaScript: o se compilan
con una herramienta (npm, Vite, webpack) o se usan ya compilados.

Aquí se usan **ya compilados**, y no es un atajo: es una regla del proyecto. La aplicación tiene que
seguir funcionando **sin cobertura** y sirviéndose como ficheros estáticos del propio servidor, y en
el ordenador donde corre esto no hay Node ni se puede instalar nada. Con una herramienta de
compilación haría falta compilar en otro sitio y acordarse de subir el resultado; con los ficheros
compilados, lo que hay en el repositorio **es** lo que ejecuta el agricultor.

## Por qué React 18.3.1 y no la última

React 19 **ya no publica ficheros UMD** (los que se cargan con una etiqueta `<script>` y dejan
`window.React`). La 18.3.1 sí, y es la última de esa familia: está mantenida, es la que usan
millones de aplicaciones y se puede cargar sin compilar nada. Cuando React publique otra versión con
ficheros para `<script>`, se cambia aquí y se vuelve a comprobar todo.

`htm` es el que permite escribir la interfaz con una sintaxis parecida a JSX **sin compilar**:

```js
import { html } from "./vendor/htm.umd.js";
const saludo = html`<p>Hola, ${nombre}</p>`;
```

Pesa 1,4 KB. Sin él habría que escribir `React.createElement("p", null, "Hola")` en cada línea, y
una interfaz de 7.000 líneas así no la mantiene nadie.

## De dónde sale y qué se guarda

De `unpkg`, que es el espejo de descarga del registro oficial de paquetes de JavaScript (npm):

```
https://unpkg.com/react@18.3.1/umd/react.production.min.js
https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js
https://unpkg.com/htm@3.1.1/dist/htm.umd.js
```

Se guardan en `backend/web/vendor/`, que es una carpeta que el servidor sirve como ficheros
estáticos. Cada uno se comprueba con su **huella SHA-256**: si el fichero que llega no es el mismo
que se revisó, el guion se para y lo dice. Un React cambiado a espaldas nuestras podría hacer
cualquier cosa en el navegador del agricultor, así que la huella no es un adorno.

## Cómo se lanza

```bash
cd backend
../.venv/Scripts/python.exe scripts/bajar_react.py
```

Si los ficheros ya están y sus huellas coinciden, no hace nada (y no toca la red).
"""

from __future__ import annotations

import hashlib
import pathlib

import httpx

# Nombre con el que se guarda, URL de donde sale y huella de la copia que se descargó y se revisó.
# Se usan las versiones `production.min`: las de desarrollo traen avisos y comprobaciones que aquí
# solo hacen la aplicación más pesada en un móvil.
FICHEROS: dict[str, tuple[str, str]] = {
    "react.production.min.js": (
        "https://unpkg.com/react@18.3.1/umd/react.production.min.js",
        "d949f1c3687aedadcedac85261865f29b17cd273997e7f6b2bfc53b2f9d4c4dd",
    ),
    "react-dom.production.min.js": (
        "https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js",
        "35f4f974f4b2bcd44da73963347f8952e341f83909e4498227d4e26b98f66f0d",
    ),
    "htm.umd.js": (
        "https://unpkg.com/htm@3.1.1/dist/htm.umd.js",
        "7a31776e04bd4afde0d4308177d26f377716fcf7e4bd70be590746d6aa594f08",
    ),
    # Este no lo usa la aplicación: lo usan **las pruebas**. Es la parte de React que convierte un
    # componente en HTML sin navegador, y gracias a eso las pruebas de la interfaz comprueban lo que
    # se ve (el HTML) sin inventarse un navegador de mentira que siempre se queda corto.
    #
    # Es el «legacy» y no el normal a propósito: el fichero `react-dom-server.browser` de React 18
    # solo sabe generar por trozos (`renderToReadableStream`), y lo que hace falta aquí es
    # `renderToStaticMarkup`, que está en este. Comprobado: el otro no trae esa función.
    "react-dom-server-legacy.browser.production.min.js": (
        "https://unpkg.com/react-dom@18.3.1/umd/react-dom-server-legacy.browser.production.min.js",
        "829b2f17da148d9bc5b635c329b67068e67e4bf7d6a5bb64e49e9e92483deee5",
    ),
}

DESTINO = pathlib.Path(__file__).resolve().parents[1] / "web" / "vendor"


def esta_descargado() -> bool:
    """Dice si los tres ficheros están y son los que se revisaron.

    Lo usa el propio guion y también las pruebas, que **no tocan la red**: comprueban lo que hay en
    el disco contra las huellas escritas aquí.
    """
    for nombre, (_url, huella) in FICHEROS.items():
        fichero = DESTINO / nombre
        if not fichero.exists():
            return False
        if hashlib.sha256(fichero.read_bytes()).hexdigest() != huella:
            return False
    return True


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    problema = False

    for nombre, (url, huella_esperada) in FICHEROS.items():
        fichero = DESTINO / nombre

        if fichero.exists():
            actual = hashlib.sha256(fichero.read_bytes()).hexdigest()
            if actual == huella_esperada:
                print(f"Ya está y coincide: {nombre}")
                continue
            print(f"El fichero que hay NO coincide con la huella esperada: {nombre}")
            print(f"  esperada: {huella_esperada}")
            print(f"  la que hay: {actual}")
            print("Míralo antes de seguir: puede ser una versión nueva del programa.")
            problema = True
            continue

        print(f"Descargando {url}")
        respuesta = httpx.get(url, timeout=120.0, follow_redirects=True)
        respuesta.raise_for_status()
        contenido = respuesta.content
        huella = hashlib.sha256(contenido).hexdigest()

        if huella != huella_esperada:
            print(f"La huella NO coincide, no se guarda nada: {nombre}")
            print(f"  esperada: {huella_esperada}")
            print(f"  la que ha llegado: {huella}")
            problema = True
            continue

        fichero.write_bytes(contenido)
        print(f"Escrito {fichero} ({len(contenido):,} bytes)")
        print(f"  SHA-256: {huella}")

    if problema:
        print("\nHay ficheros que no cuadran. No se da nada por bueno hasta mirarlo.")
        return 1
    print(f"\nTodo listo en {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
