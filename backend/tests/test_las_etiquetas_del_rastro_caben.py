"""Lo que se escribe en el rastro de auditoría tiene que **caber** en su columna.

POR QUÉ EXISTE ESTE FICHERO (02/10/2026) — y es un defecto de producción de verdad.

`auditoria.accion` estaba declarada `String(30)`, y el programa escribe etiquetas **más largas**:
`traer_tierras_del_cuaderno_de_la_junta` y `rellenar_desde_el_cuaderno_de_la_junta` (38),
`crear_desde_el_cuaderno_de_la_junta` (35) y `crear_desde_un_lote_de_recintos` (31).

**SQLite no comprueba la longitud de un `VARCHAR`**, así que en el ordenador del agricultor no pasaba
nada y todo el mundo estaba tranquilo. **PostgreSQL sí**, y como la fila del rastro se escribe **en la
misma transacción** que la operación, lo que fallaba entero era **la operación**:

    DataError: (psycopg.errors.StringDataRightTruncation) value too long for type character varying(30)

Es decir: **traer las tierras del cuaderno de la Junta, rellenar desde él, crear desde un lote de
recintos y crear desde ese cuaderno no se podían hacer en producción**, y en local sí. Lo destapó la
suite entera corriendo contra PostgreSQL: **67 pruebas en rojo**, todas por esto.

**CÓMO SE LEE EL CÓDIGO, Y POR QUÉ ASÍ** (02/10/2026, segunda vuelta, y esto lo encontró el agente de
T12 revisándome a mí). La primera versión buscaba las etiquetas con una **expresión regular** sobre el
texto del fichero, y tenía **dos agujeros**, los dos medidos:

1. **Una etiqueta escondida en una expresión**: `accion="conciliar" if factura else "desconciliar"` — la
   expresión regular veía la primera y **la segunda se quedaba sin vigilar** (y era la más larga).
2. **Una etiqueta dentro de un comentario o un docstring**: al leer el texto entero, un ejemplo escrito
   entre comillas dobles **contaba como etiqueta de verdad**: podía hacer saltar la prueba por algo que no
   es código, o **tapar** una etiqueta real que se pasara.

Ahora se lee el **árbol del parser** (`ast`), que es lo que el programa *es* y no lo que el fichero
*parece*: los comentarios no existen ahí, y cada `accion=` se mira por lo que de verdad vale. **Una
etiqueta tiene que ser un texto fijo**: si alguien la esconde en una decisión, esta prueba lo dice en vez
de mirar la mitad. Se admite una excepción, explícita: un ayudante que recibe la etiqueta de quien le
llama (`accion=accion`), porque entonces el texto fijo está en quien llama y **también se mira**.

**Lo que esta prueba NO comprueba, y se dice:** que la base de datos que se esté usando tenga ese ancho.
Si algún día hay una instalación de PostgreSQL creada cuando la columna medía 30, habrá que ensancharla a
mano (`ALTER TABLE auditoria ALTER COLUMN accion TYPE varchar(80)`), porque `asegurar_columnas` sabe
**añadir** columnas que faltan, no **ensanchar** una que ya está. Hoy no hay ninguna instalación así.
"""

from __future__ import annotations

import ast
from pathlib import Path

from app import models

RAIZ = Path(__file__).resolve().parents[2]
APLICACION = RAIZ / "backend" / "app"

# Las dos columnas del rastro que se rellenan con textos fijos, con **el nombre del parámetro** con el
# que se escriben. `entidad` solo se mira en las filas del rastro (hay otra columna `entidad` en `firmas`
# que mide menos, y compararla con esta sería un error).
COLUMNAS = {
    "accion": "auditoria.accion",
    "entidad": "auditoria.entidad",
}

# Cuántas etiquetas hay hoy (67 sitios en 32 formas distintas). No se exige un número exacto —eso
# obligaría a tocar esta prueba cada vez que se añade una acción—, pero sí un mínimo: si la lectura
# dejara de encontrar nada, la prueba pasaría sin comprobar nada, y eso sería peor que fallar.
MINIMO_DE_ETIQUETAS = 60


class Etiqueta:
    """Una etiqueta del rastro, con dónde está escrita."""

    def __init__(self, fichero: str, linea: int, columna: str, texto: str):
        self.fichero = fichero
        self.linea = linea
        self.columna = columna
        self.texto = texto

    def __repr__(self) -> str:
        return f"{self.texto!r} ({len(self.texto)}), en {self.fichero}:{self.linea}"


def _es_una_fila_del_rastro(llamada: ast.Call) -> bool:
    """Si esa llamada es `models.Auditoria(...)` (o `Auditoria(...)`), que es donde va el rastro."""
    funcion = llamada.func
    if isinstance(funcion, ast.Attribute):
        return funcion.attr == "Auditoria"
    return isinstance(funcion, ast.Name) and funcion.id == "Auditoria"


def _lo_que_se_escribe_en_esta_llamada(
    llamada: ast.Call, fichero: str, quejas: list[str]
) -> list[Etiqueta]:
    """Las etiquetas de una llamada, o una queja si alguna no es un texto fijo."""
    encontradas: list[Etiqueta] = []
    del_rastro = _es_una_fila_del_rastro(llamada)
    for palabra in llamada.keywords:
        if palabra.arg not in COLUMNAS:
            continue
        # `entidad` solo cuenta en las filas del rastro: hay otra columna `entidad` en `firmas`.
        if palabra.arg == "entidad" and not del_rastro:
            continue
        valor = palabra.value
        if isinstance(valor, ast.Constant) and isinstance(valor.value, str):
            encontradas.append(
                Etiqueta(fichero, palabra.value.lineno, palabra.arg, valor.value)
            )
            continue
        # Un ayudante que recibe la etiqueta de quien le llama: el texto fijo está en quien llama, y esa
        # llamada también se mira (esta lectura recorre **todas** las llamadas del programa).
        if isinstance(valor, ast.Name) and valor.id == palabra.arg:
            continue
        quejas.append(
            f"{fichero}:{palabra.value.lineno}: `{palabra.arg}` no es un texto fijo, sino "
            f"`{ast.unparse(valor)}`. Una etiqueta del rastro tiene que ser un texto fijo: así se puede "
            "comprobar que cabe en su columna, y no cambia sola. Si depende de un caso, escribe la "
            "etiqueta entera en cada sitio."
        )
    return encontradas


def _las_etiquetas_del_codigo() -> tuple[list[Etiqueta], list[str]]:
    """Todas las etiquetas del rastro del programa, y las quejas por las que no son texto fijo."""
    encontradas: list[Etiqueta] = []
    quejas: list[str] = []
    for fichero in sorted(APLICACION.rglob("*.py")):
        arbol = ast.parse(fichero.read_text(encoding="utf-8"), filename=str(fichero))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Call):
                encontradas.extend(
                    _lo_que_se_escribe_en_esta_llamada(nodo, fichero.name, quejas)
                )
    return encontradas, quejas


def _el_ancho(nombre_de_la_columna: str) -> int:
    columna = models.Auditoria.__table__.columns[nombre_de_la_columna]
    ancho = getattr(columna.type, "length", None)
    assert ancho, f"la columna `{COLUMNAS[nombre_de_la_columna]}` no dice cuánto mide: {columna.type!r}"
    return int(ancho)


class TestLoQueSeEscribeEnElRastroCabe:
    def test_se_leen_las_etiquetas_de_verdad(self):
        """Sin esto, un cambio en la forma de escribir las etiquetas dejaría la prueba mirando el vacío."""
        etiquetas, _ = _las_etiquetas_del_codigo()
        assert len(etiquetas) >= MINIMO_DE_ETIQUETAS, (
            f"solo se han leído {len(etiquetas)} etiquetas del rastro: ¿ha cambiado la forma de "
            f"escribirlas? (se esperan al menos {MINIMO_DE_ETIQUETAS}, y hoy hay 67 en 32 formas)"
        )
        assert len({etiqueta.texto for etiqueta in etiquetas}) >= 25, "se esperaban al menos 25 distintas"

    def test_ninguna_etiqueta_se_esconde_en_una_decision(self):
        """**El primer agujero que encontró T12.** Una etiqueta dentro de una expresión se leía a medias.

        Con una expresión regular solo se veía la primera rama: `accion="conciliar" if factura else
        "desconciliar"` dejaba **`desconciliar` sin vigilar**. Ahora se lee el árbol del parser y una
        etiqueta que no sea un texto fijo se dice aquí.
        """
        _, quejas = _las_etiquetas_del_codigo()
        assert not quejas, "\n".join(quejas)

    def test_ninguna_etiqueta_se_pasa_del_ancho_de_su_columna(self):
        """**La prueba del defecto.** Con la columna en 30, esta prueba tenía cuatro rojos.

        Y leer el árbol del parser arregla el segundo agujero: los comentarios y los docstrings no están
        ahí, así que un ejemplo escrito entre comillas dobles **no cuenta** como etiqueta (antes podía
        hacer saltar la prueba por nada, o tapar una de verdad).
        """
        etiquetas, _ = _las_etiquetas_del_codigo()
        largas = []
        for etiqueta in etiquetas:
            ancho = _el_ancho(etiqueta.columna)
            if len(etiqueta.texto) > ancho:
                largas.append((etiqueta, ancho))
        assert not largas, (
            "hay etiquetas del rastro que no caben en su columna:\n  "
            + "\n  ".join(f"{e} no cabe en {COLUMNAS[e.columna]} ({ancho})" for e, ancho in largas)
            + "\nEn SQLite no se nota —no comprueba la longitud de un VARCHAR—, pero **en PostgreSQL "
            "falla la operación entera**, porque la fila del rastro va en la misma transacción. "
            "Acorta la etiqueta o ensancha la columna."
        )

    def test_la_columna_es_mas_ancha_que_la_etiqueta_que_rompio_produccion(self):
        """La más larga que se encontró medía 38 y la columna tenía 30.

        Se comprueba aparte para que quede escrito **cuánto hizo falta**, y para que bajar el ancho por
        debajo de eso no pueda pasar sin que alguien lo lea.
        """
        ancho = _el_ancho("accion")
        etiquetas, _ = _las_etiquetas_del_codigo()
        mas_larga = max(len(e.texto) for e in etiquetas if e.columna == "accion")
        assert ancho >= 38, (
            f"la columna mide {ancho} y la etiqueta más larga que rompió producción medía 38 "
            f"(hoy la más larga es {mas_larga})"
        )
        assert ancho > mas_larga - 1, (
            f"la columna mide {ancho} y la etiqueta más larga del programa mide {mas_larga}: "
            "tiene que quedar sitio, no caber por los pelos"
        )
