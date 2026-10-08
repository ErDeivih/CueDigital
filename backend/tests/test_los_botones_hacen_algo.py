"""Todo botón que se pinta tiene quien lo atienda.

**Por qué existe.** En este programa, un botón no lleva su función pegada: todos los clics los atiende
**un solo manejador delegado** en `document`, que lee `data-accion` y decide qué hacer. Eso tiene una
ventaja (un sitio para todo) y un peligro del tamaño de la aplicación: si alguien escribe una acción
que el manejador no conoce, el botón **se pinta, se puede pulsar y no hace absolutamente nada**. No
salta ningún error, no se pone nada rojo: el agricultor pulsa y no pasa nada.

Esta prueba compara dos listas que tienen que cuadrar:

  · **las acciones que se pintan**: todo `data-accion="…"`, `accion="…"` (React), `accion: "…"`
    (los botones de `boton()`) y sus versiones con `${"…"}` dentro de una plantilla;
  · **las acciones que el manejador atiende**: cada `nombre === "…"` de `app.js`.

Se hizo a mano en la ronda 32 y salió limpio (84 y 84), así que esto es un guardián para que siga
estándolo — no una sospecha.

**Lo que esta prueba NO comprueba, y se dice para no dar más seguridad de la que da:** las acciones
que salen por variable (`data-accion=${algo}`) no se pueden leer de un fichero. Son pocas y se vigilan
aquí mismo: si aparecen en un fichero nuevo, la prueba avisa para mirarlo a mano.
"""

from __future__ import annotations

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[2]
WEB = RAIZ / "backend" / "web"

# Todas las formas en que el programa escribe una acción.
FORMAS = [
    re.compile(r"""data-accion=["']([a-z0-9_-]+)["']"""),
    re.compile(r"""data-accion=\$\{["'`]([a-z0-9_-]+)["'`]\}"""),
    re.compile(r"""\baccion=["']([a-z0-9_-]+)["']"""),
    re.compile(r"""\baccion=\$\{["'`]([a-z0-9_-]+)["'`]\}"""),
    re.compile(r"""\baccion:\s*["'`]([a-z0-9_-]+)["'`]"""),
]

# Y las que salen por variable: no se pueden leer, pero se cuentan y se vigilan.
DINAMICAS = [
    re.compile(r"""data-accion=\$\{(?!["'`])"""),
    re.compile(r"""\baccion=\$\{(?!["'`])"""),
]

ATENDIDAS = re.compile(r"""nombre === ["']([a-z0-9_-]+)["']""")

# Las tres de `nucleo.js` **no son acciones de botón**: son la decisión que toma la cola de apuntes
# pendientes («mandar», «esperar», «nada»). Se quedan fuera a propósito, con su motivo.
NO_SON_BOTONES = {"mandar", "esperar", "nada"}

# En qué ficheros puede haber una acción puesta por variable. Son las que hay hoy: el botón compartido
# de React (`componentes.js`), las dos pantallas que deciden la acción al vuelo (`inicio.js`,
# `mis_cosas.js`), **la lista de botones del asistente** (`lista_para_elegir.js`), que es la pieza donde
# el asistente dibuja las tierras, las naves, los productos y los trabajos —sus acciones son las que le
# pasa `app.js` en cada botón (`elegir`, `tipo-tratamiento`, `anadir-maestro`), y cada paso usa las
# suyas—, **el campo** (`campo.js`), cuyos atajos de fecha («HOY» y «AYER») llevan la acción y el campo
# al que se refieren, y **la confirmación** (`confirmacion.js`), que es la pantalla que sale después de
# guardar algo: sus botones («VER MIS VENTAS», «VOLVER AL INICIO») son distintos en cada una de las ocho
# pantallas que la usan, y se los pasa `app.js`— y **«mi cuaderno»** (`mi_cuaderno.js`), que es una
# pantalla con nueve bloques dentro y cada bloque trae sus propios botones (los de las ventas, los de las
# medidas, los de los análisis, los del plan, el de firmar y los tres de abajo): se los prepara
# `app.js` en `datosDelCuaderno()`— y **la tarjeta** (`tarjeta.js`), que es la pieza con la que se elige la
# tierra en el asistente: su acción y sus datos (`data-campo`, `data-valor`,
# `data-superficie`) son los que `app.js` prepara para cada tierra. Si sale un fichero nuevo aquí, hay que
# mirarlo a mano: esta prueba no puede leer esas acciones.
#
# **`grupos.js` entra en la ronda 92**, y por el mismo motivo que `mi_cuaderno.js`: cada grupo lleva
# ahora sus dos botones (CORREGIR y BORRAR), y cuáles son y de qué grupo se los pasa `app.js`
# (`botonesDeCorregirYBorrar("grupo", grupo.id)`). Se ha mirado a mano, y las dos acciones que puede
# pintar (`cosa-corregir` y `cosa-borrar`) están atendidas en el manejador de clics.
#
# **Y en la ronda 93 entra `acciones_de_una_ficha.js`**, que es la pieza con la que todas las listas
# pintan esos mismos dos botones (las tierras, los grupos, los apuntes del cuaderno, lo que se usa, los
# análisis, las ventas y los planes). Es el caso más claro de por qué esta lista existe: la pieza pinta
# **lo que le pasen**, así que sus acciones no se pueden leer del código. Se ha mirado a mano: por ahí
# solo salen `cosa-corregir` y `cosa-borrar`, y las dos están atendidas.
#
# **Y en la ronda 93 entra `interpretacion_factura.js`**, que es la pantalla que confirma lo que se ha
# leído de una factura **y la que corrige una que ya está guardada**. Su botón de volver lleva a un sitio
# distinto según de dónde se venga: al leer, vuelve a «añadir una factura» (`factura-nueva`); al corregir,
# **a la lista de facturas** (`facturas-abrir`), que es de donde se salió. Es el mismo cuidado de
# `botonParaVolver` en `app.js`, y por eso la acción va por variable. Se ha mirado a mano: las dos
# (`factura-nueva` y `facturas-abrir`) están atendidas en el manejador de clics, y el botón de guardar
# (`factura-guardar`) se pinta literal.
#
# **Y el 30/09/2026 entra `marco.js`**, el armazón del ordenador (el menú lateral y la barra de arriba). Es
# el caso más claro de todos: **cada renglón del menú lleva la acción que le pasa `app.js`** desde su tabla
# de módulos (`MODULOS`), así que aquí no se puede leer ninguna. Se ha mirado a mano: las acciones que
# puede pintar son `ir-inicio`, `inicio` (con su `data-ir`), `cultivo-ver-todos`, `cesta-ver`, `medidas-ver`,
# `papel-ver-todos`, `facturas-abrir`, `campanas-abrir`, `cuaderno-de-la-junta-abrir`, `mis-datos-abrir`,
# `cambiar-letra` y `salir` — las doce están atendidas en el manejador de clics.
#
# **Y `tabla.js` entra el mismo día**, por lo mismo: una celda de la tabla puede ser un botón (el nombre de
# una tierra que se toca para verla en el panel de al lado) y su acción la decide `app.js`. Se ha mirado a
# mano: por ahí sale `elegir-fila` (con su `data-tabla` y su `data-id`), que está atendida; y las cabeceras
# que ordenan (`ordenar-tabla`) se pintan literales en este fichero.
#
# **Y `panel_de_mando.js` entra con la fase 4** (30/09/2026), por el mismo motivo: cada cosa que falta lleva el
# botón que la arregla, y **cuál es ese botón lo decide `app.js`** (hoy `cultivo-ver-todos`, y mañana el que
# sea). Se ha mirado a mano: por ahí sale `cultivo-ver-todos`, que está atendida; y los botones de apuntar
# (`inicio` con su `data-ir`) y los del cierre (`sacar-datos`, `firmar-abrir`) los pone `app.js` desde la
# misma tabla de textos que los del móvil.
#
# **Y `cultivos.js` entra ese mismo día**, al ponerle a la franja de «lo que falta» **el botón que enseña solo
# esas tierras** (del diseño de escritorio de esa pantalla). Se ha mirado a mano: las dos acciones que pueden
# salir por ahí son `cultivo-solo-las-que-faltan` y `cultivo-ver-todas`, y las dos están atendidas en el
# manejador de clics.
# **Y el 03/10/2026 entra `contactos.js`** (T11), por el mismo motivo que la lista de elegir del
# asistente: la tarjeta de un nombre escrito lleva la acción **solo cuando hay dónde enlazarlo**. En una
# finca sin ninguna ficha apuntada, la pantalla de enlazar enseña los nombres escritos **sin botón**
# —un botón que no puede hacer nada promete una salida y no la da— y con el aviso y el botón de AÑADIR
# UNA FICHA que sí la dan. Se ha mirado a mano: las dos acciones que puede salir de ahí son
# `contacto-enlazar` (atendida en el manejador de clics) y ninguna (la tarjeta se pinta como un `<div>`).
# **Y el 03/10/2026 entra `maquinaria.js`** (T14), y entra por un motivo distinto de todos los anteriores:
# **la acción de sus botones de elegir se la pasa `app.js`**, porque la MISMA pieza se usa para tres
# preguntas distintas del formulario de una máquina (la clase, la propiedad y la disponibilidad) y para las
# tres respuestas de cada obligación. Su acción es siempre `maquina-elegir` y está atendida en el manejador
# de clics; lo que se pasa por variable es **el campo** que se está contestando, que es lo que evita tener
# cuatro acciones casi iguales.
FICHEROS_CON_ACCION_POR_VARIABLE = {
    "componentes.js",
    "inicio.js",
    "mis_cosas.js",
    "lista_para_elegir.js",
    "campo.js",
    "confirmacion.js",
    # **`buscar.js` entra el 07/10/2026**, y por el mismo motivo que `maquinaria.js` de arriba: la acción
    # de cada resultado **la decide `nucleo.js`** —«tierras» abre la ficha de esa tierra, «papeles» su
    # lista…—, donde están **literales** y con su explicación, y la pantalla solo la pinta. Comprobado a
    # mano: las cinco acciones que pueden salir de ahí (`tierra-historia`, `gasto-abrir`, `contacto-abrir`,
    # `maquina-ver`, `papel-ver-todos`) están **atendidas en el manejador de clics**, y un grupo nuevo que
    # el servidor añada mañana sale **sin botón** en vez de con uno que no lleva a ningún sitio.
    "mi_cuaderno.js",
    "tarjeta.js",
    "grupos.js",
    "acciones_de_una_ficha.js",
    "interpretacion_factura.js",
    "marco.js",
    # Y `buscar.js`: la acción de cada resultado la decide `nucleo.js` (ver arriba, con sus cinco nombres).
    "buscar.js",
    "tabla.js",
    "panel_de_mando.js",
    "cultivos.js",
    "contactos.js",
    "maquinaria.js",
}


def _ficheros_del_javascript() -> list[pathlib.Path]:
    return [
        fichero
        for fichero in sorted(WEB.rglob("*.js"))
        if "vendor" not in fichero.parts
    ]


def _pintadas_y_dinamicas() -> tuple[dict[str, list[str]], list[str]]:
    pintadas: dict[str, list[str]] = {}
    dinamicas: list[str] = []
    for fichero in _ficheros_del_javascript():
        for numero, linea in enumerate(fichero.read_text(encoding="utf-8").splitlines(), 1):
            for patron in FORMAS:
                for clave in patron.findall(linea):
                    pintadas.setdefault(clave, []).append(f"{fichero.name}:{numero}")
            if any(patron.search(linea) for patron in DINAMICAS):
                dinamicas.append(f"{fichero.name}:{numero}")
    return pintadas, dinamicas


def _atendidas() -> set[str]:
    codigo = (WEB / "app.js").read_text(encoding="utf-8")
    return set(ATENDIDAS.findall(codigo))


class TestLosBotonesHacenAlgo:
    def test_cada_accion_que_se_pinta_la_atiende_alguien(self):
        pintadas, _dinamicas = _pintadas_y_dinamicas()
        atendidas = _atendidas()

        huerfanas = {
            clave: sitios
            for clave, sitios in pintadas.items()
            if clave not in atendidas and clave not in NO_SON_BOTONES
        }
        assert huerfanas == {}, (
            "hay botones que se pintan y no hacen nada: el manejador de clics no conoce estas "
            "acciones, así que el agricultor las pulsa y no pasa nada.\n"
            + "\n".join(
                f"  · {clave} (se pinta en {', '.join(sitios[:4])})"
                for clave, sitios in sorted(huerfanas.items())
            )
        )

    def test_las_dos_listas_no_estan_vacias(self):
        """Si el extractor se rompiera, la prueba de arriba pasaría sin comprobar nada."""
        pintadas, _ = _pintadas_y_dinamicas()
        atendidas = _atendidas()
        assert len(pintadas) > 60, f"solo se han encontrado {len(pintadas)} acciones pintadas"
        assert len(atendidas) > 60, f"solo se han encontrado {len(atendidas)} acciones atendidas"

    def test_las_acciones_por_variable_estan_donde_se_espera(self):
        """Lo que esta prueba no puede leer, al menos que no se multiplique sin que nadie lo vea."""
        _pintadas, dinamicas = _pintadas_y_dinamicas()
        ficheros = {sitio.split(":")[0] for sitio in dinamicas}
        nuevos = ficheros - FICHEROS_CON_ACCION_POR_VARIABLE
        assert nuevos == set(), (
            "hay acciones puestas por variable en ficheros nuevos, y esas no se pueden comprobar "
            f"leyendo el código: {sorted(nuevos)}. Míralas a mano y añade el fichero a "
            "`FICHEROS_CON_ACCION_POR_VARIABLE` con su motivo."
        )

    def test_las_tres_de_la_cola_no_son_botones(self):
        """El motivo de la excepción, comprobado: viven en `nucleo.js` y son decisiones, no botones."""
        nucleo = (WEB / "nucleo.js").read_text(encoding="utf-8")
        for decision in NO_SON_BOTONES:
            assert f'"{decision}"' in nucleo, (
                f"«{decision}» ya no está en nucleo.js: revisa la excepción de esta prueba"
            )
        sin_pintar = " ".join(_pintadas_y_dinamicas()[0])
        for decision in NO_SON_BOTONES:
            assert f"{decision}:" not in sin_pintar.replace(" ", "")
