"""El registro oficial de productos fitosanitarios, para poder comprobar lo que se apunta.

## Por qué existe esto

El agricultor apunta en cada producto su **número de registro** («el nº que viene en la etiqueta»), y
ese número es lo que mira una inspección: si el producto no está autorizado, o el número no es el
suyo, el cuaderno tiene un problema. Hasta ahora el programa **se creía lo que le escribieran**.

Desde la ronda 29 se puede comprobar, porque el **listado oficial de productos registrados** está
bajado en `data/fega/mapa_productos_fitosanitarios.xlsx` (3.087 productos, con su `NumRegistro`,
`Nombre`, `Titular`, `Fabricante`, `Formulado` y **`Estado`**), con su procedencia apuntada en
`data/fega/procedencia.json`.

## Las tres reglas que sigue esto

1. **Si no está el fichero, no se dice nada.** Todas las funciones devuelven `None` («no lo sé»), y
   quien pregunta **no avisa de nada**. Un programa que dice «ese producto no existe» cuando en
   realidad no tiene la lista es peor que uno que se calla.
2. **Esto no bloquea nada.** Devuelve lo que ha visto para que la pantalla pueda **avisar**; el
   agricultor decide. La regla del proyecto es que un aviso nunca cierra la puerta.
3. **El número se compara tal cual, sin adornos.** El registro oficial los escribe como `ES-00849`;
   si alguien apunta `2400123` o `ES 00849`, eso **no es** el número oficial, y decirlo es la verdad.
   Lo único que se tolera es el espacio sobrante y las mayúsculas, que no cambian el número.

Los datos se leen **una vez** y se quedan en memoria: el fichero tiene 3.087 filas y abrirlo en cada
apunte sería absurdo.
"""

from __future__ import annotations

import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[2]
RUTA = RAIZ / "data" / "fega" / "mapa_productos_fitosanitarios.xlsx"
PROCEDENCIA = RAIZ / "data" / "fega" / "procedencia.json"

# La columna del número de registro en el fichero oficial. Está comprobada leyendo el fichero: la
# cabecera está en la fila 4 y la primera columna se llama `NumRegistro`.
COLUMNA_DEL_NUMERO = "NumRegistro"
COLUMNA_DEL_NOMBRE = "Nombre"
COLUMNA_DEL_ESTADO = "Estado"
FILA_DE_LA_CABECERA = 4

# El estado que significa «autorizado y en uso». Cualquier otro (retirado, cancelado, caducado…) se
# devuelve tal cual para que la pantalla lo pueda decir sin que este módulo interprete nada.
ESTADO_VIGENTE = "Vigente"

_productos: dict[str, dict] | None = None
_formas_relajadas: dict[str, str] | None = None
_leido = False


def normaliza_numero(numero: str | None) -> str:
    """El número de registro, sin espacios y en mayúsculas. No cambia el número, solo lo limpia."""
    return "".join((numero or "").split()).upper()


def sin_ceros_de_delante(numero: str) -> str:
    """El número sin los ceros de delante de su parte numérica: `ES-00849` → `ES-849`.

    **Esto no se usa para dar por bueno un número**, sino para poder decir la verdad completa: el
    registro oficial escribe los números con ceros de delante (`ES-00849`, `ES-02112`) y en la
    etiqueta de un envase o en una factura se ven escritos sin ellos. Decirle a un agricultor «ese
    número no existe» cuando lo que pasa es que le faltan dos ceros sería una alarma falsa, y una
    alarma falsa hace que se deje de hacer caso a las de verdad.
    """
    limpio = normaliza_numero(numero)
    if not limpio:
        return ""
    letras, _, cifras = limpio.rpartition("-")
    if not cifras:
        letras, cifras = "", limpio
    sin_ceros = cifras.lstrip("0") or "0"
    return f"{letras}-{sin_ceros}" if letras else sin_ceros


def cargar(ruta: pathlib.Path | str | None = None) -> dict | None:
    """Lee el listado oficial. Devuelve `None` si no está, y entonces no se comprueba nada.

    Mismo criterio que el resto de listas oficiales del programa (`catalogos_siex.py`,
    `nitratos_cyl.py`): si el fichero no está, el programa sigue funcionando y **dice que no lo
    tiene**, en vez de suponer.
    """
    global _productos, _formas_relajadas, _leido
    destino = pathlib.Path(ruta) if ruta else RUTA
    _leido = True
    _productos = None
    _formas_relajadas = None
    if not destino.exists():
        return None
    try:
        from openpyxl import load_workbook

        libro = load_workbook(destino, read_only=True, data_only=True)
        hoja = libro[libro.sheetnames[0]]
        filas = hoja.iter_rows(values_only=True)
        for _ in range(FILA_DE_LA_CABECERA - 1):
            next(filas, None)
        cabecera = [str(celda).strip() if celda is not None else "" for celda in next(filas, ())]
        if COLUMNA_DEL_NUMERO not in cabecera:
            libro.close()
            return None
        indice_numero = cabecera.index(COLUMNA_DEL_NUMERO)
        indice_nombre = cabecera.index(COLUMNA_DEL_NOMBRE) if COLUMNA_DEL_NOMBRE in cabecera else None
        indice_estado = cabecera.index(COLUMNA_DEL_ESTADO) if COLUMNA_DEL_ESTADO in cabecera else None

        leidos: dict[str, dict] = {}
        for fila in filas:
            if not fila or fila[indice_numero] is None:
                continue
            numero = normaliza_numero(str(fila[indice_numero]))
            if not numero:
                continue
            leidos[numero] = {
                "numero": numero,
                "nombre": str(fila[indice_nombre]).strip() if indice_nombre is not None and fila[indice_nombre] else "",
                "estado": str(fila[indice_estado]).strip() if indice_estado is not None and fila[indice_estado] else "",
            }
        libro.close()
    except Exception:  # noqa: BLE001 — un fichero que no se puede leer es «no lo sé», no un fallo
        return None

    if not leidos:
        return None
    _productos = leidos
    # El índice «sin ceros de delante», para poder decir cómo lo escribe el registro cuando alguien
    # lo ha escrito de otra forma. Solo se usa para **avisar mejor**, nunca para dar por bueno un
    # número que no está.
    _formas_relajadas = {}
    for numero in leidos:
        relajado = sin_ceros_de_delante(numero)
        if relajado != numero:
            _formas_relajadas.setdefault(relajado, numero)
    return _productos


def olvidar() -> None:
    """Vacía lo leído. Existe para los tests: uno que carga el suyo no puede dejarlo puesto para el
    siguiente, o el orden de ejecución cambiaría los resultados."""
    global _productos, _formas_relajadas, _leido
    _productos = None
    _formas_relajadas = None
    _leido = False


def cargado() -> bool:
    if not _leido:
        cargar()
    return _productos is not None


def cuantos() -> int:
    return len(_productos or {})


def ficha(numero: str | None) -> dict | None:
    """Lo que dice el registro oficial de un número de registro, o `None` si no está o no se sabe."""
    if not _leido:
        cargar()
    if _productos is None:
        return None
    return _productos.get(normaliza_numero(numero))


def esta_en_el_registro(numero: str | None) -> bool | None:
    """`True` si el número está en el registro oficial, `False` si no, y `None` si no se puede saber.

    **`None` no es `False`.** Es la diferencia entre «no lo sé» y «no está», y es justo la que hace
    que este programa no diga mentiras: sin la lista bajada, no se avisa de nada.
    """
    if not _leido:
        cargar()
    if _productos is None:
        return None
    limpio = normaliza_numero(numero)
    if not limpio:
        return None
    return limpio in _productos


def aviso_sobre_el_numero(numero: str | None) -> dict | None:
    """Lo que hay que avisarle al agricultor sobre un número de registro, o `None` si no hay nada.

    Devuelve tres cosas distintas, y a propósito **no las mezcla**:

    - `codigo`: `"no_esta_en_el_registro"` (el número no aparece en el listado oficial),
      `"no_vigente"` (aparece, pero su estado no es «Vigente») o `"escrito_de_otra_forma"` (está,
      pero el registro lo escribe con ceros de delante y aquí falta esa forma).
    - `numero`: el número tal y como lo ha escrito el agricultor (ya limpio).
    - `oficial`: cómo lo escribe el registro, cuando se sabe (para poder decírselo).
    - `ficha`: lo que dice el registro de ese producto (nombre y estado), cuando se sabe.

    Y devuelve `None` en tres casos que **no son un problema**: cuando no hay lista bajada, cuando el
    agricultor no ha puesto número (es opcional), y cuando el número está y está vigente.
    """
    if not _leido:
        cargar()
    if _productos is None:
        return None
    limpio = normaliza_numero(numero)
    if not limpio:
        return None

    ficha_del_producto = _productos.get(limpio)
    if ficha_del_producto is not None:
        if ficha_del_producto["estado"] and ficha_del_producto["estado"] != ESTADO_VIGENTE:
            return {"codigo": "no_vigente", "numero": limpio, "oficial": limpio, "ficha": ficha_del_producto}
        return None

    # No está escrito así, pero puede estar escrito de otra forma: el registro usa ceros de delante
    # (`ES-00849`) y en las etiquetas y las facturas se ve sin ellos (`ES-849`). Se dice cómo se
    # escribe, en vez de decir que no existe.
    relajado = sin_ceros_de_delante(limpio)
    oficial = (_formas_relajadas or {}).get(relajado)
    if oficial:
        return {
            "codigo": "escrito_de_otra_forma",
            "numero": limpio,
            "oficial": oficial,
            "ficha": _productos.get(oficial),
        }

    return {"codigo": "no_esta_en_el_registro", "numero": limpio, "oficial": None, "ficha": None}


def procedencia() -> dict:
    """De dónde sale el listado: dirección, fecha y huella. Vacío si no hay fichero bajado.

    Se lee del propio `procedencia.json` que escribe el guion de descarga, y no se escribe aquí a
    mano: una dirección copiada a mano es una dirección que un día deja de ser verdad.
    """
    import json

    if not PROCEDENCIA.exists():
        return {}
    try:
        datos = json.loads(PROCEDENCIA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dict(datos.get("ficheros", {}).get(RUTA.name, {}))


def resumen() -> dict:
    """Lo que se puede decir del registro oficial, contado. Para la pantalla de estado y la ayuda."""
    if not cargado():
        return {
            "cargado": False,
            "por_que_no": (
                "No está el listado oficial de productos fitosanitarios. Se baja con "
                "scripts/bajar_catalogos_fega.py."
            ),
            "productos": 0,
            "procedencia": {},
        }
    return {
        "cargado": True,
        "productos": cuantos(),
        "procedencia": procedencia(),
    }
