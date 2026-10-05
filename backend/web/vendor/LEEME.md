# Los ficheros de React que usa la interfaz

Esta carpeta **no se escribe a mano**: son los ficheros oficiales de React y de `htm`, tal y como los
publica su fabricante, descargados una vez y guardados aquí para que la aplicación funcione **sin
cobertura** y sin necesidad de compilar nada.

| Fichero | Qué es | De dónde sale | SHA-256 |
|---|---|---|---|
| `react.production.min.js` | React 18.3.1 (el núcleo) | <https://unpkg.com/react@18.3.1/umd/react.production.min.js> | `d949f1c3687aedadcedac85261865f29b17cd273997e7f6b2bfc53b2f9d4c4dd` |
| `react-dom.production.min.js` | React 18.3.1 (el que pinta en la página) | <https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js> | `35f4f974f4b2bcd44da73963347f8952e341f83909e4498227d4e26b98f66f0d` |
| `htm.umd.js` | `htm` 3.1.1, para escribir la pantalla sin compilar | <https://unpkg.com/htm@3.1.1/dist/htm.umd.js> | `7a31776e04bd4afde0d4308177d26f377716fcf7e4bd70be590746d6aa594f08` |
| `react-dom-server-legacy.browser.production.min.js` | React 18.3.1, la parte que convierte un componente en HTML **sin navegador**. La usan **las pruebas**, no la aplicación | <https://unpkg.com/react-dom@18.3.1/umd/react-dom-server-legacy.browser.production.min.js> | `829b2f17da148d9bc5b635c329b67068e67e4bf7d6a5bb64e49e9e92483deee5` |

> **Por qué el último fichero es el «legacy».** El normal (`react-dom-server.browser`) de React 18
> solo sabe generar HTML por trozos (`renderToReadableStream`); el que trae
> `renderToStaticMarkup`, que es el que hace falta para comprobar lo que se ve, es este. Comprobado
> a mano: el otro no trae esa función.

- **Fecha de descarga de esta copia:** 26/09/2026.
- **Licencia:** las dos permiten copiar y distribuir. **React** (y su parte de pintar en la página)
  es **MIT**; **`htm` es Apache 2.0**. Está comprobado en el `package.json` que publica cada
  paquete, no supuesto. Se guardan los dos textos de licencia en esta carpeta
  (`LICENSE-React.txt` y `LICENSE-htm.txt`), que es lo único que las licencias piden.

## Cómo se regenera

```bash
cd backend
../.venv/Scripts/python.exe scripts/bajar_react.py
```

Si los ficheros ya están y sus huellas coinciden, el guion no hace nada y **no toca la red**.

## Por qué están aquí y no se compilan

David decidió que la interfaz se rehace en React. Lo normal sería montar un proyecto con npm y
compilarlo, pero eso rompe dos cosas de este proyecto:

1. **La aplicación tiene que funcionar sin cobertura**, sirviéndose como ficheros estáticos desde el
   propio servidor. Si la interfaz pidiera React a un servicio de internet, en el campo (que es donde
   se usa esto) no habría pantalla.
2. **En el ordenador donde corre esto no hay Node**, así que no se puede compilar ahí. Y compilar en
   otro sitio y subir el resultado es justo el tipo de paso que se olvida un día y deja al agricultor
   con una pantalla rota.

Con los ficheros ya compilados, lo que hay en el repositorio **es** exactamente lo que ejecuta el
agricultor. Se pierde el JSX (por eso está `htm`) y no se pierde nada más.

## Por qué la versión 18 y no la última

React 19 **ya no publica ficheros UMD**, que son los que se cargan con una etiqueta `<script>` y
dejan `window.React`. La 18.3.1 sí, es la última de esa familia y está mantenida. Cuando React saque
otra versión que se pueda cargar así, se cambia aquí, se actualizan las huellas y se vuelven a pasar
todas las pruebas.

## Ojo: esto no se toca a mano

Si alguien edita estos ficheros para «arreglar» algo, la huella dejará de coincidir y el guion se
parará —que es lo que tiene que hacer—. Cualquier cambio de versión se hace cambiando la URL y la
huella **esperada** en `backend/scripts/bajar_react.py`, y volviendo a lanzarlo.
