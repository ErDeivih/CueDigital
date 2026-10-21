"""Comprobar la interfaz **en un navegador de verdad**.

## Por qué existe esto

Los tests de JavaScript corren sin navegador: montan un DOM de mentira, o dibujan los componentes con
el `renderToStaticMarkup` de React. Eso comprueba **qué HTML sale**, pero no comprueba lo que solo
pasa en un navegador de verdad:

- que los ficheros de React y `htm` de `web/vendor/` **se cargan de verdad** en una página;
- que `ReactDOM.createRoot(...).render(...)` **monta** en un navegador (esto es lo único que no se
  puede probar de ninguna otra forma);
- que la aplicación **arranca sin errores de JavaScript**, que es el fallo que dejaría al agricultor
  delante de una pantalla en blanco.

Así que esto abre Chrome (o Edge) **sin ventana**, con un perfil de usar y tirar, y:

1. Carga la pantalla de entrar y comprueba que se ve.
2. Crea una cuenta de prueba **y la deja con datos dentro** (una tierra, su cultivo, un producto y un
   tratamiento): con la finca vacía, las pantallas se verían bien aunque estuvieran rotas, que es
   justo lo que pasó con «mi cuaderno» (contaba cero apuntes de producto porque la lista de
   tratamientos no la rellenaba nadie).
3. Entra con esa cuenta y comprueba que la **pantalla de inicio la dibuja React**.
4. Recorre las pantallas ya migradas y comprueba que se dibujan, que **no saltan errores** y que no
   sale lo que no toca (por ejemplo, «todavía no has apuntado nada» en una finca con apuntes). **Y
   desde la ronda 62 recorre también el asistente de apuntar**, que monta sus pasos en un hueco
   (`#formulario`) en vez de en la pantalla entera: ahí se comprueba que React **llena ese hueco**. Si
   no lo llena, el agricultor ve la pregunta y nada que contestar, y eso no se puede ver en los tests
   (no hay ReactDOM).
5. Guarda una captura de cada una en la carpeta temporal, para poder mirarlas.

## Cómo se lanza

```bash
cd backend
../.venv/Scripts/python.exe scripts/comprobar_en_un_navegador.py
```

Necesita un servidor de verdad corriendo con una base de datos que se pueda ensuciar (la prueba crea
una cuenta y le mete datos). Es una comprobación a mano, como `humo.py`: **no es un test**, porque los
tests no levantan navegadores ni tocan la red del sistema. Lo más cómodo es arrancar un servidor
aparte con una base de datos de usar y tirar:

```bash
CUEDIGITAL_DATABASE_URL=sqlite:////tmp/cuedigital-navegador.db \
  ../.venv/Scripts/python.exe -m uvicorn app.main:app --port 8011
../.venv/Scripts/python.exe scripts/comprobar_en_un_navegador.py http://127.0.0.1:8011
```

Si no encuentra ningún navegador, lo dice y no falla: es una comprobación de más, no un requisito.
"""

from __future__ import annotations

import csv
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
# Y su propia carpeta, para poder usar las dos piezas que viven aquí al lado: el navegador manejado
# por el protocolo de depuración (`navegador_cdp.py`) y la preparación del volumen
# (`datos_representativos.py`).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import httpx  # noqa: E402

import datos_representativos  # noqa: E402
from navegador_cdp import NavegadorDeVerdad, SinNavegador, el_navegador  # noqa: E402

DIRECCION_POR_DEFECTO = "http://127.0.0.1:8010"

NAVEGADORES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

FALLOS: list[str] = []


def comprobar(condicion: bool, descripcion: str) -> None:
    print(f"  [{'OK  ' if condicion else 'FALLO'}] {descripcion}")
    if not condicion:
        FALLOS.append(descripcion)


def navegador() -> str | None:
    return el_navegador()


def crear_cuenta(direccion: str) -> str:
    """Una cuenta de prueba y su token, para poder ver las pantallas de dentro."""
    correo = f"navegador-{os.getpid()}@ejemplo.test"
    with httpx.Client(base_url=direccion, timeout=30.0) as cliente:
        respuesta = cliente.post(
            "/api/cuenta/registro",
            json={
                "nombre": "Prueba del navegador",
                "correo": correo,
                "clave": "una-clave-larga",
                "explotacion": {
                    "nombre": "La finca de la prueba del navegador",
                    "nif": "12345678Z",
                },
            },
        )
        respuesta.raise_for_status()
        return respuesta.json()["token"]


# Las pantallas ya migradas a React, con **cómo se llega a cada una pulsando** y un par de cosas que
# tienen que verse en ella. Se recorre como lo haría el agricultor: pulsando de verdad.
PANTALLAS = [
    # Con una finca que ya tiene un tratamiento apuntado (lo deja `siembra_datos`), la pantalla
    # de inicio tiene que ofrecer repetirlo y **no** puede decir que no hay nada apuntado: ese
    # mensaje se decidía con lo que recordaba el móvil, y el navegador de esta comprobación llega
    # con la memoria vacía. Es justo el caso que se arregló.
    (
        "inicio",
        [],
        [
            "Hola",
            "HE ECHADO PRODUCTO",
            "MI CUADERNO",
            "LO MISMO QUE LA ÚLTIMA VEZ",
        ],
    ),
    (
        "mis cosas",
        ['[data-accion="mis-cosas"]'],
        # Desde la ronda 78 las tierras de esta pantalla son **tarjetas**: con su número, la referencia
        # del SIGPAC con su nombre delante y lo que hay sembrado este año. Se comprueban aquí porque es
        # lo único que no se puede ver en un DOM de mentira: que los datos de la tierra llegan hasta la
        # tarjeta que se dibuja.
        [
            "Mis parcelas, productos y máquinas",
            "Parcelas",
            "El Prado",
            "Glifosato 36 SL",
            "Tierra n.º 1",
            "Referencia oficial SIGPAC",
            "Cultivo de este año",
        ],
    ),
    (
        "los papeles",
        ['[data-accion="mis-cosas"]', '[data-accion="papel-ver-todos"]'],
        ["Los papeles", "GUARDAR UN PAPEL"],
    ),
    (
        "el almacén",
        ['[data-accion="mis-cosas"]', '[data-accion="cesta-ver"]'],
        # El resumen del almacén, **en singular**: la finca de la prueba tiene un producto y antes decía
        # «Tienes 1 productos apuntados» (ronda 84).
        ["Lo que tengo en el almacén", "Tienes 1 producto apuntado."],
    ),
    (
        "qué hay sembrado",
        ['[data-accion="mis-cosas"]', '[data-accion="cultivo-ver-todos"]'],
        # Y aquí, con una sola tierra sin decir qué tiene, «A 1 parcela le falta decir qué tiene este año.»
        # (antes: «A 1 parcelas les falta decir qué tienen este año.»).
        ["Qué hay sembrado", "A 1 parcela le falta decir qué tiene este año."],
    ),
    # Y **cambiar y quitar** lo que hay sembrado (ronda 93), que es lo que se pide desde que David dijo
    # «deja borrar las cosas que introduzca porque puede que me equivoque, o modificar también». Se entra
    # por la tierra que **ya tiene** dicho qué tiene («El Prado», sembrada en `siembra_datos`): en la
    # pantalla tiene que verse que se está **cambiando** y tiene que estar el botón de quitar.
    (
        "cambiar lo que hay sembrado",
        [
            '[data-accion="mis-cosas"]',
            '[data-accion="cultivo-ver-todos"]',
            '[data-accion="cultivo-decir"]',
        ],
        [
            "¿Qué hay sembrado?",
            "ESTÁS CAMBIANDO LO QUE DIJISTE",
            "GUARDAR LOS CAMBIOS",
            "QUITAR EL CULTIVO DE ESTE AÑO",
            # El borde del formulario: la pregunta y sus cinco campos, con sus `id` (que es lo que lee `app.js`).
            'id="cultivo-especie"',
        ],
    ),
    # Y la pregunta de quitarlo, que es lo que impide que un toque de más deje la tierra sin cultivo.
    (
        "quitar lo que hay sembrado",
        [
            '[data-accion="mis-cosas"]',
            '[data-accion="cultivo-ver-todos"]',
            '[data-accion="cultivo-decir"]',
            '[data-accion="cultivo-quitar"]',
        ],
        [
            "¿Seguro que quieres borrarlo?",
            "Lo que va a desaparecer de tu cuaderno",
            "SÍ, BORRARLO",
            "MEJOR CORREGIRLO",
        ],
    ),
    ("la ayuda", ['[data-accion="inicio"][data-ir="ayuda"]'], ["Qué te obliga la ley", "Para qué sirve esto"]),
    ("mis datos", ['[data-accion="inicio"][data-ir="mi_cuaderno"]', '[data-accion="mis-datos-abrir"]'], ["Mis datos", "GUARDAR MIS DATOS"]),
    # Varias cuentas en la misma finca (ronda 89). Se entra desde «mis datos», que es la pantalla de la
    # finca. La cuenta que crea esta comprobación es la titular de su propia finca (la creó ella), así que
    # aquí se ve el campo del correo y el botón de añadir: el camino del titular, que es el que decide
    # quién entra.
    (
        "quién entra en mi finca",
        [
            '[data-accion="inicio"][data-ir="mi_cuaderno"]',
            '[data-accion="mis-datos-abrir"]',
            '[data-accion="quien-entra-abrir"]',
        ],
        [
            "Quién entra en mi finca",
            "Estás en",
            "Eres el titular de esta finca",
            "AÑADIR UNA CUENTA",
            "De momento solo entras tú.",
        ],
    ),
    # **Los años del cuaderno** (ronda 93), la pantalla nueva: el año que está llevando, sus fechas, cuánto
    # hay dentro de cada uno y el botón de empezar el año siguiente. Se entra desde «mis datos», que es la
    # pantalla de la finca y del cuaderno.
    (
        "los años de mi cuaderno",
        [
            '[data-accion="inicio"][data-ir="mi_cuaderno"]',
            '[data-accion="mis-datos-abrir"]',
            '[data-accion="campanas-abrir"]',
        ],
        [
            "Los años de mi cuaderno",
            "Año del cuaderno",
            # El año que crea la propia comprobación al darse de alta la cuenta, con su etiqueta.
            "Estás apuntando en este",
            "EMPEZAR UN AÑO NUEVO",
            "Cuando empiece el año que viene, hazlo aquí",
            "CORREGIR",
            # **Y su tabla** (30/09/2026): los años, uno debajo de otro, con lo que tiene cada uno dentro.
            '<table class="tabla"',
            "Qué tiene dentro",
            'data-accion="ordenar-tabla"',
        ],
    ),
    # Y **empezar un año nuevo**: el primer paso es el año, y sale propuesto el siguiente al último que
    # tiene. Es lo que hasta esta ronda no se podía hacer de ninguna forma desde la aplicación.
    (
        "empezar un año nuevo",
        [
            '[data-accion="inicio"][data-ir="mi_cuaderno"]',
            '[data-accion="mis-datos-abrir"]',
            '[data-accion="campanas-abrir"]',
            '[data-accion="campana-nueva"]',
        ],
        [
            "EMPEZAR UN AÑO NUEVO",
            "¿De qué año es?",
            'id="anio"',
            "SEGUIR",
        ],
    ),
    (
        "las medidas",
        ['[data-accion="inicio"][data-ir="mi_cuaderno"]', '[data-accion="medidas-ver"]'],
        [
            "Marca lo que hagas en tu finca",
            "GUARDAR",
            # La finca de la prueba declara dos medidas en `siembra_datos`, así que aquí se ve también lo
            # que solo sale cuando **ya hay** declaración: el botón de quitarla (ronda 93).
            "BORRAR LO QUE HE DICHO DE ESTAS MEDIDAS",
            "es dejar la finca sin contestar",
        ],
    ),
    # Y la pregunta de quitarla, que es lo que impide que un toque de más borre la declaración entera.
    (
        "quitar la declaración de las medidas",
        [
            '[data-accion="inicio"][data-ir="mi_cuaderno"]',
            '[data-accion="medidas-ver"]',
            '[data-accion="medidas-quitar"]',
        ],
        [
            "¿Seguro que quieres borrarlo?",
            "Lo que va a desaparecer de tu cuaderno",
            "Tienes marcadas 2 medidas",
            "SÍ, BORRARLO",
            "MEJOR CORREGIRLO",
        ],
    ),
    # «Mi cuaderno» contaba cero apuntes de producto porque la lista de tratamientos no la
    # rellenaba nadie: el agricultor veía su año vacío. Se comprueba con datos de verdad.
    #
    # Y desde la ronda 70 esta pantalla está **entera en React** (sus nueve bloques): además de los
    # apuntes se comprueban los textos de cabecera de los bloques, que son los que se perdieron sin
    # querer en otras migraciones (un bloque de React al que no le llega su título sale sin él).
    (
        "mi cuaderno",
        ['[data-accion="inicio"][data-ir="mi_cuaderno"]'],
        [
            # **Ronda 91**: el título de la lista pasó de «1 apunte de producto» a «1 apunte en el
            # cuaderno», porque desde esta ronda la lista enseña los **cuatro** tipos de apunte (producto,
            # abono, trabajo y cosecha) y cada uno se puede corregir y borrar.
            #
            # **Y desde el 05/10/2026 son dos** (T15): el guion deja también un trabajo hecho, y un trabajo
            # hecho **es un apunte del cuaderno** —es lo que pide el recorrido 4: «planificar un trabajo →
            # marcarlo hecho → que llegue al cuaderno»—. Así que el número de verdad es dos, y decirlo aquí
            # es lo que demuestra que el trabajo ha llegado al cuaderno y no se ha quedado en su pantalla.
            "2 apuntes en el cuaderno",
            "Glifosato 36 SL",
            "Lo que falta por completar",
            "Sacar mi cuaderno para la Junta",
            "SACAR EN PAPEL",
            # Desde la ronda 79 cada apunte es una ficha con **cada dato dicho**: su número, la tierra
            # donde se echó (que no salía en ninguna parte) y las hectáreas tratadas. Se comprueba aquí
            # porque es lo único que no se puede ver en un DOM de mentira: que los datos del tratamiento
            # lleguen hasta la ficha que se dibuja.
            "Apunte 1",
            "Tierra y parcela",
            "Hectáreas tratadas",
            "APUNTAR OTRO TRATAMIENTO",
            # Y la ronda 80: la frase de un vistazo («te falta… por apuntar», con el número que sea, que
            # depende de lo que le falte a la finca de la prueba) y el **bloque verde de la inspección**
            # con su botón dentro. Lo que se comprueba es que la frase se dibuja y que el botón que se
            # pulsa con el inspector delante está ahí.
            "por apuntar",
            "SACAR MI CUADERNO",
            # Y la ronda 81: el número de cada bloque, con su palabra. Los dos son fijos en esta finca de
            # la prueba (un análisis y una venta): «1 análisis guardado» y «1 venta apuntada · 42.000 kg».
            "1 análisis guardado",
            "1 venta apuntada",
            # Y la ronda 91: **los dos botones de cada apunte**. Lo que se comprueba con esto es que los
            # botones que se pulsan de verdad están en la pantalla que se dibuja: el manejador de clics es
            # uno solo y lee `data-accion`, así que un botón que no salga es una función que no existe.
            "CORREGIR",
            "BORRAR",
        ],
    ),
    # Corregir y borrar lo que uno ha introducido (ronda 91). Es la comprobación que más falta hacía de
    # esta ronda: los dos botones se pulsan **de verdad** en un navegador, y lo que se mira es que
    # CORREGIR abra el asistente **con lo que ya estaba puesto** (su botón final dice GUARDAR LOS CAMBIOS,
    # no APUNTARLO) y que BORRAR pregunte antes de quitar nada.
    (
        "corregir un apunte",
        ['[data-accion="inicio"][data-ir="mi_cuaderno"]', '[data-accion="cosa-corregir"]'],
        [
            "Corregir lo que apuntaste",
            "Está puesto lo que apuntaste",
            # Lo que se mira aquí es **que el asistente se abra con lo que ya estaba puesto**: la tierra
            # donde se hizo el apunte (la lista de tierras del primer paso, con la suya) y la máquina.
            "El Prado",
            "SEGUIR",
        ],
    ),
    (
        "borrar un apunte",
        ['[data-accion="inicio"][data-ir="mi_cuaderno"]', '[data-accion="cosa-borrar"]'],
        [
            "¿Seguro que quieres borrarlo?",
            "De tu cuaderno desaparece del todo.",
            # Lo que va a desaparecer, con los mismos datos que la ficha que se acaba de tocar: es lo que
            # permite comprobar que es ESE apunte y no el de al lado.
            "Glifosato 36 SL",
            "El Prado",
            "SÍ, BORRARLO",
            "MEJOR CORREGIRLO",
        ],
    ),
    # Corregir y borrar una TIERRA (ronda 92): lo mismo, pero con lo que el agricultor dio de alta él.
    # Se recorren las dos porque el formulario de corregir una tierra es el del alta (no el del
    # asistente de apuntar) y ese camino solo se comprueba de verdad aquí, en un navegador.
    (
        "corregir una tierra",
        ['[data-accion="mis-cosas"]', '[data-accion="cosa-corregir"]'],
        [
            "Corregir lo que apuntaste",
            "El Prado",
            "SEGUIR",
        ],
    ),
    (
        "borrar una tierra",
        ['[data-accion="mis-cosas"]', '[data-accion="cosa-borrar"]'],
        [
            "¿Seguro que quieres borrarlo?",
            "Tierra",
            "El Prado",
            "SÍ, BORRARLO",
            "MEJOR CORREGIRLO",
        ],
    ),
    # Y lo mismo con **todo lo demás que se da de alta** (ronda 93): una ficha de lo que se usa (un
    # producto), un análisis y una venta. Se recorren los tres porque cada uno abre **su propio
    # formulario** (el del alta de un maestro, el del análisis y el de la venta) y eso solo se comprueba
    # de verdad aquí, en un navegador.
    (
        "corregir un producto",
        ['[data-accion="mis-cosas"]', '[data-accion="cosa-corregir"][data-tipo="producto"]'],
        ["Corregir lo que apuntaste", "SEGUIR"],
    ),
    (
        "borrar un producto",
        ['[data-accion="mis-cosas"]', '[data-accion="cosa-borrar"][data-tipo="producto"]'],
        ["¿Seguro que quieres borrarlo?", "SÍ, BORRARLO"],
    ),
    (
        "corregir un análisis",
        [
            # La lista de análisis se abre **desde «mi cuaderno»** (su bloque), no desde el inicio.
            '[data-accion="inicio"][data-ir="mi_cuaderno"]',
            '[data-accion="analisis-ver"]',
            '[data-accion="cosa-corregir"][data-tipo="analitica"]',
        ],
        ["Corregir lo que apuntaste", "SEGUIR"],
    ),
    (
        "borrar una venta",
        [
            '[data-accion="inicio"][data-ir="mi_cuaderno"]',
            '[data-accion="ventas-ver"]',
            '[data-accion="cosa-borrar"][data-tipo="venta"]',
        ],
        ["¿Seguro que quieres borrarlo?", "SÍ, BORRARLO"],
    ),
    # El buscador de tierras del paso (ronda 82). Es lo único que no se puede comprobar en un DOM de
    # mentira: que el campo que pinta React lo lea `app.js` **por su `id`**, que la lista se vuelva a
    # pintar filtrada y que lo que no casa desaparezca (eso se mira en `NO_PUEDE_SALIR`).
    (
        "el buscador de tierras",
        [
            '[data-accion="inicio"][data-ir="echar_producto"]',
            "escribir:#buscar_tierra=suertes",
            '[data-accion="buscar-tierra"]',
        ],
        ["Las Suertes de Arriba", "Buscar entre tus tierras", "VERLAS TODAS"],
    ),
    # El mismo buscador en «mis cosas» (ronda 87): es la pantalla donde el diseño lo pide («Buscar entre tus
    # fincas»), y con 51 tierras mirar una concreta era recorrerlas todas.
    (
        "el buscador de tierras de mis cosas",
        [
            '[data-accion="mis-cosas"]',
            "escribir:#buscar_tierra_mis_cosas=suertes",
            '[data-accion="buscar-tierra-mis-cosas"]',
        ],
        ["Las Suertes de Arriba", "Buscar entre tus tierras", "VERLAS TODAS"],
    ),
    # «Lo que he vendido»: la cosecha comercializada. Se comprueba **cada dato con su nombre** (ronda 86):
    # antes era una línea corrida con seis datos separados por puntos y había que adivinar cuál era cuál.
    (
        "las ventas",
        ['[data-accion="inicio"][data-ir="mi_cuaderno"]', '[data-accion="ventas-ver"]'],
        [
            "Lo que he vendido",
            "42.000,00 kg",
            "A quién",
            "Cooperativa Agrícola de Peñaranda",
            "Partida",
            "Albarán",
        ],
    ),
    # «Los análisis» ya está en React: se comprueba que se dibuja **con el análisis dentro**, que    # es lo único que no se puede ver en un DOM de mentira.
    (
        "los análisis",
        ['[data-accion="inicio"][data-ir="mi_cuaderno"]', '[data-accion="analisis-ver"]'],
        ["Los análisis", "Materia orgánica"],
    ),
    # «Dímelo con la voz», la pantalla del campo. Se abre desde la pantalla de inicio con un solo
    # toque, y tiene que traer su campo para escribir: en el móvil de David es la única forma de
    # apuntar con las manos ocupadas.
    (
        "dímelo con la voz",
        ['[data-accion="dictado"]'],
        ["Dímelo con la voz", "ENTENDERLO"],
    ),
    # **El camino entero del dictado, en un navegador de verdad.** Aquí se comprueba lo que no se
    # puede comprobar en el DOM de mentira: que el texto que se teclea en el campo que pinta React
    # lo lee `app.js` por su `id`, que se manda al servidor y que lo que contesta se enseña.
    (
        "la revisión de lo dictado",
        [
            '[data-accion="dictado"]',
            "escribir:#dictado-texto=he echado dos litros de glifosato en el prado, habia hierba",
            '[data-accion="dictado-entender"]',
        ],
        ["Lo que he entendido", "Mira si está bien", "APUNTARLO"],
    ),
    # **Y el formulario con más campos de los que ya están en React, relleno de verdad.** Seis
    # campos que `app.js` lee por su `id`: si uno se hubiera quedado sin él al pasar a React, el
    # papel se guardaría vacío y sin ningún error. Aquí se escribe, se guarda y se comprueba que el
    # papel vuelve a la lista con lo que se escribió.
    (
        "guardar un papel",
        [
            '[data-accion="mis-cosas"]',
            '[data-accion="papel-ver-todos"]',
            '[data-accion="papel-nuevo"]',
            "escribir:#papel-titulo=Contrato de la finca del rio",
            "escribir:#papel-carpeta=Contratos",
            "escribir:#papel-fecha=2026-03-01",
            "escribir:#papel-quien=El dueno de la tierra",
            '[data-accion="papel-guardar"]',
        ],
        ["Los papeles", "Contrato de la finca del rio", "Contratos"],
    ),
    # Y el mismo papel, corregido (ronda 93). Va **después** de la ruta de arriba a propósito: se apoya en
    # el papel que aquella acaba de guardar. Es la única forma de comprobar en un navegador de verdad que
    # corregir un papel abre **su pantalla** —la de los seis campos, no el asistente— **con lo que ya
    # estaba puesto** y con el botón diciendo «GUARDAR LOS CAMBIOS»: si un `id` se hubiera perdido al pasar
    # a React, el papel se corregiría vacío y sin ningún error.
    (
        "corregir un papel",
        [
            '[data-accion="mis-cosas"]',
            '[data-accion="papel-ver-todos"]',
            '[data-accion="cosa-corregir"][data-tipo="documento"]',
        ],
        [
            "Contrato de la finca del rio",
            'id="papel-titulo"',
            'id="papel-carpeta"',
            "GUARDAR LOS CAMBIOS",
        ],
    ),
    # El plan de abono: se abre desde «mi cuaderno». La finca de la prueba no tiene ninguno, así que
    # se comprueba su estado vacío, que es el que ve cualquier agricultor la primera vez.
    (
        "el plan de abono",
        ['[data-accion="inicio"][data-ir="mi_cuaderno"]', '[data-accion="plan-ver"]'],
        # Textos que **solo** salen en la pantalla del plan: la explicación y la cabecera de la tabla.
        # Los del bloque de «mi cuaderno» no valen para comprobar esto, y confundirlos fue el fallo
        # que trajo la comprobación de los pasos de la ruta.
        ["El plan dice qué abono vas a echar", "Tenías previsto · Llevas"],
    ),
    # Las facturas: la lista y el alta. Se llega desde «lo que tengo en el almacén», que es donde el
    # agricultor se pregunta por el producto que ha comprado.
    (
        "mis facturas",
        [
            '[data-accion="mis-cosas"]',
            '[data-accion="cesta-ver"]',
            '[data-accion="facturas-abrir"]',
        ],
        [
            "Mis facturas",
            "AÑADIR UNA FACTURA",
            # **Y su tabla** (30/09/2026): las facturas del año juntas, con sus números y el papel.
            '<table class="tabla"',
            "Nº de factura",
            "El papel",
            'data-accion="ordenar-tabla"',
        ],
    ),
    (
        "añadir una factura",
        [
            '[data-accion="mis-cosas"]',
            '[data-accion="cesta-ver"]',
            '[data-accion="facturas-abrir"]',
            '[data-accion="factura-nueva"]',
        ],
        ["AÑADIR UNA FACTURA", "LEER LA FACTURA", "ESCRIBIRLA A MANO"],
    ),
    # Y **borrar una factura** (ronda 93), que es lo que David pidió con sus palabras: «recuerda también
    # dejar borrar las cosas que introduzca porque puede que me equivoque». La ruta se para **en la
    # pantalla que pregunta**: pulsar el «SÍ, BORRARLO» quitaría la factura que la ruta de arriba usa, y lo
    # que hay que comprobar aquí es que la ficha ofrece el botón y que la pregunta dice qué va a
    # desaparecer. Lo que pasa **después** de confirmar lo comprueban la prueba de cableado y el `humo`.
    (
        "borrar una factura",
        [
            '[data-accion="mis-cosas"]',
            '[data-accion="cesta-ver"]',
            '[data-accion="facturas-abrir"]',
            '[data-accion="cosa-borrar"][data-tipo="factura"]',
        ],
        [
            "¿Seguro que quieres borrarlo?",
            "Lo que va a desaparecer de tu cuaderno",
            "Cooperativa Agrícola de Peñaranda",
            "SÍ, BORRARLO",
        ],
    ),
    # Y **corregir una factura** (ronda 93), que es la otra mitad de lo que pidió David («o modificar
    # también»). Se recorren los dos momentos, porque son dos pantallas y las dos importan: la que enseña
    # lo que está guardado para cambiarlo, y la que sale después de guardar.
    (
        "corregir una factura: lo que está guardado",
        [
            '[data-accion="mis-cosas"]',
            '[data-accion="cesta-ver"]',
            '[data-accion="facturas-abrir"]',
            '[data-accion="cosa-corregir"][data-tipo="factura"]',
        ],
        [
            # Lo que hay que ver aquí es que **no dice que ha leído nada**: no se ha leído, se está
            # arreglando una factura que ya está en el cuaderno.
            "Esto es lo que tienes guardado",
            "Lo que había antes se queda apuntado en el cuaderno",
            # Los datos guardados, dentro de sus campos, con sus `id` (que es lo que lee `app.js`).
            'id="factura-proveedor"',
            'id="factura-total"',
            "Cooperativa Agrícola de Peñaranda",
            "SÍ, GUARDAR LOS CAMBIOS",
            "VOLVER A MIS FACTURAS",
        ],
    ),
    (
        "corregir una factura: guardar",
        [
            '[data-accion="mis-cosas"]',
            '[data-accion="cesta-ver"]',
            '[data-accion="facturas-abrir"]',
            '[data-accion="cosa-corregir"][data-tipo="factura"]',
            # Se cambia el total, que es lo que haría el agricultor que ve que no es el que puso, y se
            # guarda. Hasta aquí no se ha comprobado nunca el camino entero (el `PUT` con los datos en
            # JSON) en un navegador de verdad: en el DOM de mentira de las pruebas no hay campos.
            "escribir:#factura-total=800",
            '[data-accion="factura-guardar"]',
        ],
        [
            # **«Corregido» y no «Factura guardada»**: decirle «guardada» a quien acaba de arreglar una
            # le haría pensar que tiene dos y volvería a mirar la lista para ver cuál sobra.
            "Corregido",
            "Lo que había antes queda guardado en el historial del cuaderno",
            "Mis facturas",
        ],
    ),
    # **El asistente, que hasta la ronda 62 no se recorría aquí.** Es lo que más se usa del programa, y
    # sus pasos no se montan en la pantalla entera como las demás: se montan en un **hueco**
    # (`#formulario`) que primero pinta la interfaz vieja y luego llena React. Eso no se puede
    # comprobar en el DOM de mentira de los tests (no hay ReactDOM), así que es justo aquí donde tiene
    # que mirarse. Si React no llega a montar, el agricultor ve la pregunta y **nada que contestar**, y
    # en la captura se vería.
    (
        "el asistente: dónde se ha echado",
        ['[data-accion="inicio"][data-ir="echar_producto"]'],
        ["El Prado", "data-campo=\"parcela_id\"", "¿No es en una parcela?"],
    ),
    # Y el camino entero hasta el resumen, que es el paso que más se ve: se contesta lo obligatorio y se
    # saltan los opcionales, como lo haría el agricultor con prisa. **Y se escribe en el campo de las
    # hectáreas**, que es la prueba de verdad de que las dos mitades se hablan: el campo lo pinta React
    # con su `id`, lo que se teclea lo lee `app.js` **por ese `id`** y acaba en el resumen, que es lo
    # último que ve el agricultor antes de apuntar. Si un `id` cambiara al pasar a React, el campo se
    # rellenaría y **se guardaría vacío sin que saltara ningún error**; esto lo caza.
    (
        "el asistente: el resumen",
        [
            '[data-accion="inicio"][data-ir="echar_producto"]',
            '[data-campo="parcela_id"]',
            '[data-accion="asistente-seguir"]',  # de la fecha a las hectáreas
            "escribir:#superficie_tratada_ha=3,5",
            '[data-accion="asistente-seguir"]',  # de las hectáreas al motivo
            '[data-campo="justificacion"]',
            '[data-campo="producto_id"]',
            '[data-accion="asistente-seguir"]',  # la dosis
            '[data-accion="asistente-saltar"]',  # quién y con qué máquina
            '[data-accion="asistente-saltar"]',  # las medidas preventivas
            '[data-accion="asistente-saltar"]',  # las observaciones
            '[data-accion="asistente-saltar"]',  # cómo se echó
        ],
        [
            "Mira si está bien",
            "El Prado",
            "Glifosato 36 SL",
            "class=\"resumen-dato\"",
            # Lo que se escribió en el campo que pinta React, ya en el resumen y escrito como se lee aquí.
            "3,50",
        ],
    ),
    # **Los pasos donde el agricultor escribe.** Son los que más fácil se rompen al pasar a React: el
    # campo tiene que llevar **su `id`** (es lo único que tiene `app.js` para leer lo escrito) y los
    # números tienen que llevar `inputmode="decimal"`, que es lo que hace salir el teclado de números
    # **con coma** en el móvil. Las dos cosas se ven aquí y en ningún otro sitio: en el DOM de mentira de
    # los tests no hay campos.
    (
        "el asistente: las hectáreas",
        [
            '[data-accion="inicio"][data-ir="echar_producto"]',
            '[data-campo="parcela_id"]',
            '[data-accion="asistente-seguir"]',  # de la fecha a las hectáreas
        ],
        ['id="superficie_tratada_ha"', 'inputmode="decimal"', "¿Cuántas hectáreas has tratado?"],
    ),
    # Y la fecha, que es el paso que más se ve de todo el programa: trae el día de hoy puesto, en
    # formato de fecha, y los dos atajos de debajo («HOY» y «AYER»), que es lo que hace que apuntar lo de
    # hoy sean dos toques.
    (
        "el asistente: la fecha",
        [
            '[data-accion="inicio"][data-ir="echar_producto"]',
            '[data-campo="parcela_id"]',
        ],
        ['id="fecha" type="date"', 'data-accion="fecha-rapida"', "data-campo=\"fecha\""],
    ),
    # **Una venta entera, de punta a punta, y es la comprobación más completa de todas.** El asistente de
    # la venta usa **todas** las piezas a la vez: las clases de venta (botones), el producto y la variedad
    # (campos que se escriben), la cantidad, la unidad, la fecha y la lista de tierras… y el resumen, que
    # todavía pinta la interfaz vieja. Si lo que se teclea en un campo que pinta React llega al resumen,
    # es que las dos mitades se hablan **por el `id`**, que es justo lo que hay que demostrar: un `id`
    # cambiado guardaría el apunte vacío sin que saltara ningún error.
    (
        "el asistente: una venta entera",
        [
            '[data-accion="inicio"][data-ir="mi_cuaderno"]',
            '[data-accion="ventas-nueva"]',
            '[data-accion="elegir"][data-campo="tipo"]',
            "escribir:#producto=Lechuga romana",
            "escribir:#variedad=Batavia",
            '[data-accion="asistente-seguir"]',  # del producto a la cantidad
            "escribir:#cantidad=3000",
            # Se elige la unidad **por su valor** y no «la primera»: la primera puede ser los kilos, y
            # entonces el resumen diría «3.000,00 kg» y la comprobación fallaría por un motivo que no es
            # de la pantalla. (Pasó al escribir esta ruta: se pulsaba la primera opción a ciegas.)
            '[data-accion="elegir"][data-campo="unidad"][data-valor="ud"]',
            '[data-accion="asistente-seguir"]',  # de la cantidad a la fecha
            # **El paso que mezcla dos piezas**: el lote (que se escribe) y la fecha de fin (que se elige
            # con el calendario). Se escribe la fecha de fin para comprobar que el campo que pinta React lo
            # lee `app.js` por su `id`: en el resumen sale con el intervalo de días.
            "escribir:#fecha_fin=2026-07-12",
            '[data-accion="asistente-saltar"]',  # el último día y la partida
            '[data-accion="elegir"][data-campo="parcela_id"]',
            '[data-accion="asistente-saltar"]',  # a quién y el albarán
            '[data-accion="asistente-saltar"]',  # lo que quiera apuntar
        ],
        ["APUNTARLO", "Lechuga romana", "Batavia", "3.000,00 ud", "El Prado", "12/07/2026"],
    ),
    # **La pantalla que ofrece los caminos para dar de alta una tierra.** Es una de las que se pasaron a
    # React con la **pieza de la confirmación** (la misma que las cinco pantallas de «guardado»), y se
    # llega en dos toques: es la puerta de todo lo que se puede hacer con una tierra nueva. Se comprueba
    # aquí porque los cuatro caminos (el mapa, el cuaderno de la Junta, la referencia del SIGPAC y
    # apuntarla a mano) son botones que llaman a `app.js`: si se perdiera una acción, el camino
    # desaparecería sin que nada avisara.
    (
        "el alta de una tierra: por dónde",
        [
            '[data-accion="mis-cosas"]',
            '[data-accion="anadir-maestro"][data-tipo="parcela"]',
        ],
        [
            "Traer la parcela del SIGPAC",
            "VER EL MAPA Y ELEGIRLA AHÍ",
            "TRAER MIS TIERRAS",
            "TRAERME LOS DATOS",
            "APUNTARLA A MANO",
            "necesita conexión",
        ],
    ),
    # **Traer la tierra del SIGPAC.** Es una pantalla entera metida en un paso del asistente de dar de
    # alta una tierra, y la que ahorra más trabajo de todas: con 54 líneas, teclear cada tierra es la
    # diferencia entre empezar y no empezar. Se comprueba en un navegador de verdad porque sus campos
    # (`municipio_sigpac`, `poligono_sigpac`, `ref_sigpac`…) los lee `app.js` **por su `id`**: si uno
    # cambiara, el agricultor rellenaría el formulario y se guardaría vacío.
    #
    # Se busca el pueblo de verdad (la lista de los 2.248 municipios la sirve el propio programa, sin
    # salir a internet) y se comprueba que sale en la lista para elegirlo.
    (
        "el asistente: traer la tierra del SIGPAC",
        [
            # Se llega como el agricultor: a «mis cosas» y desde ahí se añade una tierra. Ese botón
            # (`anadir-maestro` con `data-tipo="parcela"`) abre la pantalla que ofrece traerla del SIGPAC
            # o apuntarla a mano.
            '[data-accion="mis-cosas"]',
            '[data-accion="anadir-maestro"][data-tipo="parcela"]',
            '[data-accion="sigpac-si"]',
            "escribir:#municipio_sigpac=Calvarrasa",
            '[data-accion="buscar-pueblo"]',
        ],
        [
            "id=\"municipio_sigpac\"",
            "id=\"provincia_sigpac\"",
            "id=\"ref_sigpac\"",
            "BUSCAR EL PUEBLO",
            "BUSCAR MIS TROZOS",
            "Calvarrasa de Arriba",
        ],
    ),
    # ======================================================================
    # Los recorridos 2, 3 y 4, **pulsando**, que es como los hace el agricultor
    # ======================================================================
    #
    # Hasta el 06/10/2026 estas pantallas se comprobaban dibujadas (y sus flujos estaban probados en
    # las pruebas de cableado y en las del servidor), pero el guion del navegador **no recorría los
    # formularios**: apuntar un gasto, conciliarlo o planificar un trabajo se comprobaba «por
    # pantalla», no palmo a palmo. Estos cuatro recorridos son lo que faltaba para poder decir que el
    # agricultor los completa desde la aplicación: **se escribe en los campos de verdad y se pulsan
    # los botones de verdad**, y lo que se comprueba es lo que sale después.
    #
    # **El recorrido 2 (T13): apuntar un gasto y ver su ficha.** Se apunta con su concepto, su
    # categoría (que se elige pulsando, como en el móvil), su importe **con coma** —que es como lo
    # escribe un agricultor y como lo tiene que leer el programa— y su fecha. Lo que se busca después
    # es el gasto en la lista y, en su ficha, lo que consta que costó, lo que queda por pagar y el
    # botón de repartirlo. Si el guardado no llegara al servidor, la lista no lo enseñaría.
    (
        "el recorrido 2: apuntar un gasto",
        [
            '[data-accion="gastos-ver"]',
            '[data-accion="gasto-nuevo"]',
            "escribir:#gasto-concepto=El gasóleo de la siega",
            # La categoría se elige **por su valor** y no «la primera»: un gasto de gasóleo tiene que
            # quedar en la categoría del gasóleo, y esa lista la sirve el servidor.
            '[data-accion="gasto-elegir"][data-campo="categoria"][data-valor="gasoleo"]',
            "escribir:#gasto-importe=254,10",
            # **La fecha no es un adorno: es la que hace que este gasto sea el primero de la lista.** La
            # lista va del más nuevo al más viejo, y las dos rutas de abajo abren «el primer gasto», que
            # tiene que ser este. Cuando el guion empezó a dejar un gasto de junio (el que cuadra con el
            # banco), la fecha de mayo dejó de ser la más nueva y las dos rutas abrieron **otro** gasto:
            # se vio enseguida porque lo que se busca en su ficha dejó de salir. Si alguien cambia esta
            # fecha, tiene que cambiar también las dos rutas de abajo.
            "escribir:#gasto-fecha=2026-07-01",
            '[data-accion="gasto-guardar"]',
        ],
        # **El recuento, y no solo el texto que se escribió**: mientras el formulario sigue abierto, lo
        # que se tecleó está en su `<input>`, así que buscar «El gasóleo de la siega» pasaría **aunque
        # el gasto no se hubiera guardado** (falso positivo que se vio al arreglar la lectura de los
        # campos, con el grabador delante). El recuento de la lista solo puede venir del servidor: el
        # guion deja **dos** gastos (uno de ellos el que cuadra con el banco, para que el recorrido 3
        # tenga con qué) y esta ruta apunta el tercero.
        ["Mis cuentas", "Tienes 3 gastos apuntados.", "El gasóleo de la siega", "254,10"],
    ),
    # Y **su ficha**, que es donde se contesta la pregunta del recorrido: qué importe consta, qué se
    # ha pagado y **qué queda pendiente**. Va después de la ruta de arriba a propósito: se apoya en
    # el gasto que aquella acaba de guardar, que es el más nuevo y por eso el primero de la lista.
    (
        "el recorrido 2: la ficha del gasto, con lo que queda por pagar",
        [
            '[data-accion="gastos-ver"]',
            '[data-accion="gasto-abrir"]',
        ],
        [
            "El gasóleo de la siega",
            "Falta por pagar",
            "REPARTIRLO",
            "ANULAR",
        ],
    ),
    # **Y repartirlo entre las tierras**, que es la mitad que le faltaba al recorrido: «registrar un
    # gasto → **asignarlo a tierras** → consultar sus repartos». Se entra por la ficha del gasto (el que
    # acaba de apuntar la ruta de arriba), se elige el método y se marcan las tierras con su botón de
    # TODAS —lo que se hace casi siempre—, y lo que se comprueba después es que **el reparto existe**:
    # cada tierra con lo que le toca y su botón de quitarla. Sin esto, la pantalla ofrecía cuatro
    # métodos que no podían repartir nada.
    (
        "el recorrido 2: repartir el gasto entre las tierras",
        [
            '[data-accion="gastos-ver"]',
            '[data-accion="gasto-abrir"]',
            '[data-accion="gasto-repartir"]',
            '[data-accion="gasto-elegir"][data-campo="metodo"][data-valor="area"]',
            '[data-accion="gasto-marcar-todas"]',
            '[data-accion="gasto-guardar"]',
        ],
        [
            "El gasóleo de la siega",
            # El cuadre de la ficha: lo que costó está **en tierras** y no queda nada sin asignar. Es lo
            # que demuestra que el reparto se hizo y que las cuentas cuadran.
            "En tierras, cultivos o máquinas",
            "Sin asignar",
            # Y cada tierra con lo que le toca y su botón de quitarla.
            "El Prado",
            "por hectáreas",
            "QUITARLO DE AQUÍ",
        ],
    ),
    # **Y el mismo gasto repartido entre las máquinas** (ronda 9), que es la otra clase de destino que
    # ofrece el formulario. Es la mitad que faltaba: el desplegable decía «entre tierras, entre cultivos o
    # entre máquinas», pero lo que se podía marcar era **siempre la lista de tierras**, así que eligiendo
    # «máquina» se guardaba un reparto que decía máquina y apuntaba a una tierra —una afirmación falsa en
    # el libro de cuentas—. Ahora se marcan las máquinas de verdad, y por eso el método de las hectáreas
    # no sale (una máquina no tiene superficie). Lo que se comprueba es que el reparto queda **con el
    # nombre de la máquina** y con las horas que se escribieron.
    (
        "el recorrido 2: repartir el gasto entre las máquinas",
        [
            '[data-accion="gastos-ver"]',
            '[data-accion="gasto-abrir"]',
            '[data-accion="gasto-repartir"]',
            '[data-accion="gasto-elegir"][data-campo="destino_tipo"][data-valor="maquina"]',
            '[data-accion="gasto-elegir"][data-campo="metodo"][data-valor="horas"]',
            '[data-accion="gasto-marcar-todas"]',
            # El campo del peso lleva el nombre de la máquina en su `id`, **con los espacios cambiados por
            # guiones bajos** (ver `idDelPesoDelReparto`).
            "escribir:#gasto-peso-El_tractor=4",
            '[data-accion="gasto-guardar"]',
        ],
        [
            "El tractor",
            "QUITARLO DE AQUÍ",
            "En tierras, cultivos o máquinas",
        ],
    ),
    # **Y entre los cultivos** (ronda 9), la tercera clase de destino. Los cultivos que se ofrecen son los
    # que el agricultor tiene **sembrados este año**, leídos de `GET /api/cultivos` (donde el de este año
    # va en `actual.especie`). Esta ruta es la que cazó ese nombre: la prueba de cableado se había escrito
    # con `fila.cultivo`, que es un campo que el servidor **no manda**, así que la lista salía vacía y la
    # prueba daba por bueno un hueco. Con el navegador delante, no: si la lista está vacía, no hay nada
    # que marcar y el paso que marca todas falla diciéndolo.
    (
        "el recorrido 2: repartir el gasto entre los cultivos",
        [
            '[data-accion="gastos-ver"]',
            '[data-accion="gasto-abrir"]',
            '[data-accion="gasto-repartir"]',
            '[data-accion="gasto-elegir"][data-campo="destino_tipo"][data-valor="cultivo"]',
            '[data-accion="gasto-elegir"][data-campo="metodo"][data-valor="manual"]',
            '[data-accion="gasto-marcar-todas"]',
            "escribir:#gasto-peso-TRIGO_BLANDO=254,10",
            '[data-accion="gasto-guardar"]',
        ],
        [
            "TRIGO BLANDO",
            "QUITARLO DE AQUÍ",
            # **El método va en dos trozos, no en una frase**: el rótulo («Se repartió») y el método («a
            # mano») son dos elementos distintos, así que «Se repartió a mano» **no está junto en el
            # HTML**. Es la misma trampa que «El importe No consta» en el recorrido 3: se buscan por
            # separado.
            "Se repartió",
            "a mano",
            "En tierras, cultivos o máquinas",
        ],
    ),
    # **El recorrido 3 (T20): de un movimiento del banco a contra qué papel va.** El extracto ya está
    # importado (lo deja `siembra_datos`, leyendo un fichero de verdad), así que lo que se recorre es
    # la mitad que importa: abrir un movimiento y ver **las cuentas que cuadran con él y por qué**, con
    # la salida de apuntarlo a mano. Conciliar de verdad —elegir la propuesta— se comprueba en las
    # pruebas del servidor y en las de cableado, porque depende de qué papeles haya ese día.
    (
        "el recorrido 3: un movimiento del que no consta el importe",
        [
            '[data-accion="gastos-ver"]',
            '[data-accion="bancos-ver"]',
            '[data-accion="banco-abrir"]',
        ],
        # **El primero de la lista es el que no trae importe** (el fichero de ejemplo tiene una línea
        # así a propósito), y esa es la mitad que más importa de este recorrido: el programa dice que
        # **no consta** —no escribe un cero—, **no ofrece cuadrarlo** con ningún papel (no se puede
        # repartir lo que no se sabe) y da la salida de escribirlo a mano. Si algún día esto enseñara
        # «0,00 €», el agricultor cuadraría su extracto contra un número inventado.
        [
            "Este movimiento del banco",
            "ANOTACION SIN IMPORTE EJEMPLO",
            # **El rótulo y el valor van en elementos distintos**, así que la frase «El importe No consta»
            # no está junta en el HTML: se buscan por separado, y con la frase entera que sí existe.
            "El importe",
            "No consta",
            "De este movimiento no consta el importe",
            "CORREGIR EL IMPORTE A MANO",
            "Contra qué papel va",
        ],
    ),
    # Y **uno con importe**, que es donde se puede cuadrar: la segunda línea de la lista (la de la
    # comisión), que sí lo trae. Se llega con `li:nth-child(2)`, porque la lista del móvil es una
    # `<ul>` con un `<li>` por movimiento y el primero es el que no consta.
    (
        "el recorrido 3: contra qué papel va un movimiento",
        [
            '[data-accion="gastos-ver"]',
            '[data-accion="bancos-ver"]',
            'li:nth-child(2) [data-accion="banco-abrir"]',
        ],
        [
            "Este movimiento del banco",
            "Contra qué papel va",
            "Elige una y el dinero queda apuntado a ese papel",
            "APUNTAR ESTE DINERO",
        ],
    ),
    # **Y conciliarlo**, que es donde termina el recorrido: se elige la propuesta que da el servidor
    # —la factura que cuadra por el importe— y el dinero queda apuntado a ese papel. Se busca el
    # movimiento **por su posición** (la tercera línea del extracto es la de la reparación: la lista va
    # de la más nueva a la más vieja), y lo que se comprueba es lo que el agricultor tiene que poder leer
    # después de pulsar: **a qué papel ha ido el dinero** (con su nombre, no con su número), que queda
    # conciliado, que se puede deshacer —sin el deshacer, un enlace equivocado se quedaría para
    # siempre— y que **ya no se le ofrece apuntar más**, porque no le queda dinero: eso era un botón que
    # solo podía llevar a un error. Las tres cosas se comprobaron primero a mano y estaban mal: la
    # respuesta de la conciliación se perdía al recargar la ficha y el servidor seguía proponiendo el
    # importe entero.
    (
        "el recorrido 3: conciliar un movimiento con su papel",
        [
            '[data-accion="gastos-ver"]',
            '[data-accion="bancos-ver"]',
            'li:nth-child(3) [data-accion="banco-abrir"]',
            '[data-accion="banco-conciliar-propuesta"][data-indice="0"]',
        ],
        [
            "Este movimiento del banco",
            "DESHACERLO",
            "Lo que ha quedado apuntado",
            "Una factura de lo que has comprado",
            "Apuntados 210,00 € de este movimiento a 1 papel(es).",
            "ya está apuntado entero a sus papeles",
        ],
    ),
    # **La historia de una tierra** (T15, 05/10/2026): **el recorrido 5 entero, pulsando**, que es como lo
    # hace el agricultor —«abrir tierra → qué cultivo tiene, qué trabajos se han hecho, qué queda previsto
    # y qué costes conocidos tiene»—. Se entra por «mis cosas» y se pulsa el botón de la ficha de la
    # primera tierra; el guion deja en ella un cultivo declarado, un trabajo hecho, uno pensado y un gasto,
    # así que las cuatro partes del recorrido tienen algo que enseñar. Los cuatro textos que se buscan son
    # los de esas cuatro partes, y **el del cultivo es el que se veía mal**: la pantalla decía «de esta
    # tierra no consta que haya nada sembrado» en una tierra con TRIGO BLANDO declarado, porque «qué hay
    # hoy» solo miraba las labores de siembra. Se arregló el mismo día que se añadió esta ruta.
    #
    # **Va antes de las rutas del recorrido 4, y el orden importa**: esas rutas marcan como hechos **todos**
    # los planes que hay (el guion deja uno y la ruta de planificar deja otro), así que a partir de ahí esta
    # pantalla ya no tiene nada que enseñar en «lo que tengo pensado hacer» —con razón: no queda nada
    # pensado— y esta comprobación dejaría de mirar esa parte. Se descubrió al añadir la ruta del insumo,
    # que consume el último plan.
    (
        "la historia de una tierra (el recorrido 5, pulsando)",
        ['[data-accion="mis-cosas"]', '[data-accion="tierra-historia"]'],
        [
            "Lo que ha pasado en esta tierra",
            "Lo que hay sembrado",
            "TRIGO BLANDO",
            "HE LABRADO LA TIERRA",
            "Lo que tengo pensado hacer",
            "Lo que ha costado esta tierra",
            "VER EL GASTO",
        ],
    ),
    # **El recorrido 4 (T15): planificar un trabajo y marcarlo hecho.** Las dos mitades del ticket, y
    # en su orden: primero se apunta lo que se piensa hacer (que **no gasta nada**) y después se
    # apunta lo que de verdad se hizo, con su día y sus horas. Se comprueba el día en las dos listas,
    # que es lo que demuestra que el plan se guardó y que el hecho llegó a su sitio.
    (
        "el recorrido 4: planificar un trabajo",
        [
            '[data-accion="trabajos-ver"]',
            '[data-accion="trabajo-planificar"]',
            "escribir:#trabajo-tipo=siembra",
            # **La primera tierra, sin escribir su número**: el identificador es del servidor y no se
            # puede saber al escribir la ruta (y una ruta con un número fijo empezaría a apuntar el
            # trabajo a la tierra que no es en cuanto cambiara la base). Por eso el guion sabe elegir
            # «la primera opción de verdad» de un desplegable.
            "elegir-ejemplo:#trabajo-tierra",
            "escribir:#trabajo-fecha-prevista=2026-11-15",
            "escribir:#trabajo-superficie=4,9",
            "escribir:#trabajo-horas=3",
            '[data-accion="trabajo-previsto-guardar"]',
        ],
        ["Los trabajos", "Lo que tengo pensado hacer", "15/11/2026"],
    ),
    (
        "el recorrido 4: marcar lo que se ha hecho de verdad",
        [
            '[data-accion="trabajos-ver"]',
            '[data-accion="trabajo-hecho"]',
            "escribir:#trabajo-fecha=2026-11-20",
            "escribir:#trabajo-horas=5",
            '[data-accion="trabajo-hecho-guardar"]',
        ],
        # **Y el plan que se acaba de cumplir sigue en la lista, diciendo que ya se hizo.** Es la mitad que
        # se arregló al recorrer esta ruta: el plan cumplido se quedaba en «lo que tengo pensado hacer» con
        # su botón «YA LO HE HECHO» otra vez, y pulsarlo contestaba 409 («este trabajo ya estaba apuntado»).
        # Ahora se dice cuándo se hizo y el botón no está.
        [
            "Los trabajos",
            "Lo que he hecho",
            "20/11/2026",
            "Ya lo apuntaste como hecho:",
        ],
    ),
    # **Y de qué envase salió lo que se gastó** (el resto del recorrido 4: «insumos → historial y
    # existencias»). El guion deja un envase con existencias dentro, así que el desplegable de insumos
    # tiene algo de verdad que elegir. Se marca otro trabajo como hecho diciendo **de qué envase** salió el
    # producto y **cuánto** se gastó, y después se abre **la historia de la tierra**, que es donde el
    # agricultor puede leer lo que se gastó en ese trabajo: en la lista de los trabajos hechos, el insumo
    # no se pinta (la agenda enseña el día, la tierra, las horas y lo que falta), y por eso la comprobación
    # termina en la historia. Lo que se busca es el nombre del producto **y** la cantidad: sin el nombre,
    # «6 L» no dice de qué, que es la mitad de la pregunta que se hace el día de una inspección.
    (
        "el recorrido 4: de qué envase salió lo que se gastó",
        [
            '[data-accion="trabajos-ver"]',
            '[data-accion="trabajo-hecho"]',
            "escribir:#trabajo-fecha=2026-12-03",
            "escribir:#trabajo-horas=4",
            # El envase y la cantidad, elegidos como lo haría el agricultor: el envase del desplegable
            # (su identificador es del servidor y no se puede escribir en la ruta) y la unidad escrita.
            "elegir-ejemplo:#trabajo-insumo",
            "escribir:#trabajo-cantidad=6",
            "escribir:#trabajo-unidad=L",
            '[data-accion="trabajo-hecho-guardar"]',
            # Y a la historia de la tierra, que es donde se lee lo que gastó ese trabajo. Se pasa por el
            # principio —«mis cosas»— porque al guardar la aplicación vuelve a la agenda de los trabajos,
            # y desde ahí el botón de la historia de una tierra no existe. El paso que falta **se dice**:
            # el guion apunta los pasos que no encuentran lo suyo y la comprobación falla por ellos.
            '[data-accion="ir-inicio"]',
            '[data-accion="mis-cosas"]',
            '[data-accion="tierra-historia"]',
        ],
        [
            "Lo que ha pasado en esta tierra",
            "Glifosato 36 SL",
            "6 L",
        ],
    ),
    # **Y que el almacén lo sepa**, que es la otra mitad de «insumos → existencias»: lo que gastó el
    # trabajo de la ruta de arriba tiene que estar **descontado** del envase. Se entra por el libro del
    # almacén, que es donde está el envase (la otra pantalla —«lo que tengo en el almacén»— lleva la
    # cuenta del producto por lo comprado y lo echado, y es otra cosa: ahí no hay ningún lote). El guion
    # deja 40 L y la ruta de arriba gasta 6.
    #
    # **Este número depende del orden de las dos rutas** (una gasta y la otra mira), y por eso va escrito
    # con su cuenta al lado: si alguien las reordena, la comprobación falla con su frase en vez de dar por
    # bueno un número que ya no es.
    (
        "el recorrido 4: el envase tiene descontado lo que se gastó",
        [
            '[data-accion="mis-cosas"]',
            '[data-accion="cesta-ver"]',
            '[data-accion="libro-ver"]',
        ],
        [
            "El libro del almacén",
            "Glifosato 36 SL",
            "ENV-2026-07",
            # 40 L que había, menos los 6 L que gastó el trabajo de la ruta anterior.
            "34,00 L",
            "6,00 L",
        ],
    ),
    # **La bandeja de los papeles** (T08, 06/10/2026): lo que llega y hay que revisar. Se entra por donde
    # entra el agricultor —«los papeles» y su botón de la bandeja—, que es además el recorrido 1 del
    # encargo. Se comprueba con un papel dentro (lo deja `siembra_datos` subiéndolo por las mismas puertas
    # que el agricultor): su título, que está **sin revisar** y el botón de mirarlo. Una bandeja vacía se
    # vería bien aunque estuviera rota, que es la lección de siempre.
    (
        "la bandeja de los papeles",
        ['[data-accion="papel-ver-todos"]', '[data-accion="bandeja-ver"]'],
        [
            "La bandeja de los papeles",
            "Tienes 1 papel en la bandeja.",
            "El ticket del gasóleo",
            "Sin revisar",
            "MIRAR ESTE PAPEL",
        ],
    ),
    # **Y la ficha de un papel**, que es la mitad que sostiene la regla del ticket: **el original a un lado
    # y lo que se ha leído al otro**, sin que nada haya entrado en el cuaderno. Es la pantalla donde más
    # cosas pueden salir en blanco (tiene el original, la propuesta, los enlaces y los candidatos), así que
    # se recorren sus cuatro bloques por su nombre.
    (
        "la ficha de un papel de la bandeja",
        [
            '[data-accion="papel-ver-todos"]',
            '[data-accion="bandeja-ver"]',
            '[data-accion="bandeja-abrir"]',
        ],
        [
            "El ticket del gasóleo",
            "El papel, tal y como llegó",
            "VER EL ORIGINAL",
            "el-ticket-del-gasoleo.png",
            "Lo que el programa ha leído",
            "LEER EL PAPEL",
        ],
    ),
    # **Y enlazarlo con un papel que ya existe** (el resto del recorrido 1): se elige la clase (la primera
    # de la lista, que es la factura de lo que ha comprado), se buscan los candidatos y se elige el
    # primero. Lo que se comprueba es lo que el ticket pide: que quede dicho **con qué va** (con su
    # nombre, no con su número de la base) y que **el original siga ahí**, que es la regla del ticket
    # («el original no se toca»). Enlazar no crea nada: el candidato es algo que ya estaba en el cuaderno.
    (
        "el recorrido 1: enlazar un papel con lo que ya existe",
        [
            '[data-accion="papel-ver-todos"]',
            '[data-accion="bandeja-ver"]',
            '[data-accion="bandeja-abrir"]',
            "elegir-ejemplo:#bandeja-clase",
            '[data-accion="bandeja-buscar-candidatos"]',
            "elegir-ejemplo:#bandeja-candidato",
            '[data-accion="bandeja-enlazar"]',
        ],
        [
            "El ticket del gasóleo",
            "Con esto va",
            "Una factura de lo que has comprado",
            "Cooperativa Agrícola de Peñaranda",
            "El papel, tal y como llegó",
            "VER EL ORIGINAL",
        ],
    ),
    # **Y enlazarlo con un gasto y con una máquina**, que son las otras dos clases que el contrato pide
    # («vincular a compra, gasto, venta, máquina o trabajo»). La ruta de arriba elige **la primera clase de
    # la lista** (la factura de lo que ha comprado); estas dos eligen la clase **por su valor**, que es
    # como se elige en la pantalla, y comprueban que lo enlazado se lee **con su nombre** (el concepto del
    # gasto, el nombre y la matrícula de la máquina) y que el original sigue donde estaba. Se recorren dos
    # clases y no las cinco porque lo que cambia entre ellas es de qué tabla sale el nombre —y eso tienen
    # sus pruebas en el servidor, una por clase—, no el camino: el camino es el mismo y ya está aquí.
    (
        "el recorrido 1: enlazar un papel con un gasto",
        [
            '[data-accion="papel-ver-todos"]',
            '[data-accion="bandeja-ver"]',
            '[data-accion="bandeja-abrir"]',
            "escribir:#bandeja-clase=gasto",
            '[data-accion="bandeja-buscar-candidatos"]',
            "elegir-ejemplo:#bandeja-candidato",
            '[data-accion="bandeja-enlazar"]',
        ],
        [
            "Con esto va",
            # El nombre de lo enlazado empieza por la clase y sigue con el gasto: se busca el principio,
            # que es lo que no cambia según cuál sea el gasto más nuevo de la finca.
            "Un gasto ·",
            "El papel, tal y como llegó",
            "VER EL ORIGINAL",
        ],
    ),
    (
        "el recorrido 1: enlazar un papel con una máquina",
        [
            '[data-accion="papel-ver-todos"]',
            '[data-accion="bandeja-ver"]',
            '[data-accion="bandeja-abrir"]',
            "escribir:#bandeja-clase=maquina",
            '[data-accion="bandeja-buscar-candidatos"]',
            "elegir-ejemplo:#bandeja-candidato",
            '[data-accion="bandeja-enlazar"]',
        ],
        [
            "Con esto va",
            "Una máquina · El tractor",
            "El papel, tal y como llegó",
            "VER EL ORIGINAL",
        ],
    ),
    # **Las cuentas de la explotación** (T13, 05/10/2026). Se entra por el renglón del menú, que es como
    # entra el agricultor. Se buscan tres cosas distintas: el título, **el botón que lleva a los bancos**
    # (que es el primer paso del recorrido 3) y el resumen con su número. Ese número —«Tienes 1 gasto
    # apuntado.»— es lo que demuestra que el gasto que deja `siembra_datos` ha llegado hasta la pantalla
    # y no se ha quedado en el servidor.
    (
        "las cuentas",
        ['[data-accion="gastos-ver"]'],
        # **Tres**: el guion deja uno, el que cuadra con el extracto (para la conciliación) y el que
        # apunta el recorrido 2 —que va antes—. Se dice el número de verdad y se explica por qué, en vez
        # de dejar una comprobación que un día diga que no cuadra sin decir de qué.
        ["Mis cuentas", "EL BANCO Y LOS PAPELES", "Tienes 3 gastos apuntados."],
    ),
    # **Los trabajos** (T15, 05/10/2026): la agenda. Se comprueban **las dos listas a la vez** —lo
    # pensado y lo hecho—, porque el guion deja una cosa de cada: con una sola lista comprobada, la otra
    # podría quedarse sin dibujar y esto seguiría verde. Y el botón de planificar, que es la puerta del
    # recorrido 4.
    (
        "los trabajos",
        ['[data-accion="trabajos-ver"]'],
        ["Los trabajos", "Lo que tengo pensado hacer", "PLANIFICAR UN TRABAJO", "Lo que he hecho"],
    ),
    # **El banco y los papeles** (T20, 05/10/2026). Se llega por donde llega el agricultor: de las
    # cuentas, por el botón de los bancos. Con el extracto ya importado por `siembra_datos` tiene que
    # verse **un movimiento de verdad con su concepto**, y eso es lo que demuestra que lo que se leyó del
    # fichero ha llegado a la pantalla: una lista vacía pasaría cualquier prueba.
    (
        "el banco y los papeles",
        ['[data-accion="gastos-ver"]', '[data-accion="bancos-ver"]'],
        ["El banco y los papeles", "LEER EL EXTRACTO", "Los movimientos del banco", "ADEUDO SEGURO AGRARIO EJEMPLO"],
    ),
]

# Los pasos del asistente donde el formulario **tiene que estar dentro del hueco** (`#formulario`), y qué
# formulario es. Se comprueba que el hueco **no se ha quedado vacío**: si React no monta (un fichero de
# `web/react/` que no ha llegado, la caché de un móvil a medias tras un despliegue), el agricultor ve la
# pregunta y no tiene dónde contestar. Es un fallo que **solo** se ve en un navegador de verdad.
#
# Desde la ronda 72 el hueco lo pinta React (es un `<div id="formulario">` dentro de la pantalla del
# asistente) en vez de la interfaz vieja, pero la comprobación sigue siendo la misma y sigue valiendo:
# busca el hueco **vacío** en el DOM de verdad.
FORMULARIO_CON_PIEZA = {
    "el asistente: dónde se ha echado": "la lista de tierras",
    "el asistente: el resumen": "el resumen del apunte",
    "el asistente: las hectáreas": "el campo de las hectáreas",
    "el asistente: la fecha": "el campo de la fecha",
    "el asistente: una venta entera": "el resumen de la venta",
    "el asistente: traer la tierra del SIGPAC": "la pantalla del SIGPAC",
}

# **La versión de ordenador** (30/09/2026): las rutas que se recorren con una ventana ancha y lo que tiene
# que estar en el armazón. No es cada pantalla otra vez —eso ya se hace arriba, en la versión de móvil, y las
# pantallas son las mismas—: aquí se comprueba **el armazón** (que exista, que lleve a los módulos y que diga
# el año) y **lo que solo existe en el ordenador**, que es la tabla y el panel de al lado.
ESCRITORIO = [
    (
        "el panel, con el menú delante",
        [],
        [
            # El menú, con los módulos de verdad: si uno se quedara sin su renglón, no se llegaría a él.
            "El menú de la aplicación",
            "Panel",
            "Mi cuaderno",
            "Mis parcelas, productos y máquinas",
            "Lo que tengo en el almacén",
            "Mis facturas",
            "Los años de mi cuaderno",
            "Mis datos",
            # Y la barra: el año que se está llevando, la cuenta y el botón de apuntar.
            "Campaña",
            "APUNTAR",
            "Tu cuenta",
            # **Y el panel de mando** (fase 4, 30/09/2026): la portada del ordenador. Antes, esta pantalla era
            # la del móvil estirada (seis botones de ancho completo); ahora enseña el estado del año. Se
            # comprueba en el HTML que dibuja el navegador de verdad: si React no montara el panel, aquí no
            # habría ni una tarjeta.
            "Panel de mando",
            "Apuntes este año",
            "Hectáreas tratadas",
            "Lo que has vendido",
            "Tus tierras",
            "Lo que falta por completar",
            "Los últimos apuntes",
            "Apuntar algo de hoy",
            "Cierre y trámites",
        ],
    ),
    (
        "las tierras, desde el menú",
        ['[data-accion="inicio"][data-ir="mis_cosas"]'],
        [
            "Mis parcelas, productos y máquinas",
            # El módulo en el que se está, marcado: es lo que hace que un menú sirva para saber dónde estás.
            'id="menu-tierras"',
            "menu-activo",
            "El Prado",
            # **Y la tabla** (fase 2, 30/09/2026): con 64 tierras, en el ordenador se miran de arriba abajo.
            # Se comprueba que está de verdad en el HTML que dibuja el navegador, con sus columnas, sus
            # datos y el total del pie: si React no montara la tabla, aquí no habría ni una cabecera.
            '<table class="tabla"',
            "Qué tiene este año",
            "Hectáreas",
            # Y las cabeceras que ordenan, que es lo que se hace con 64 tierras.
            'data-accion="ordenar-tabla"',
            # El total del pie de la tabla (las hectáreas de las tierras que hay). Se busca la forma, no el
            # número: el número depende de las tierras que tenga la finca de la prueba.
            "tierras · ",
            " ha</td>",
            # **Y el panel de detalle, al lado** (fase 3, 30/09/2026): la ficha de la tierra elegida. Sin
            # nada elegido dice qué hacer; con una tierra elegida (esta ruta toca su nombre) enseña sus datos
            # y sus botones sin cambiar de pantalla.
            "La tierra que has elegido",
            "Toca el nombre de una tierra",
            'data-accion="elegir-fila"',
        ],
    ),
    (
        "las tierras, con una elegida en el panel",
        [
            '[data-accion="inicio"][data-ir="mis_cosas"]',
            # Se toca el nombre de la primera tierra de la tabla: eso es lo que abre su ficha al lado.
            '[data-accion="elegir-fila"]',
        ],
        [
            "La tierra que has elegido",
            'class="panel-detalle"',
            # Los datos de la tierra elegida, con su nombre delante, y el botón que la abre entera.
            "Referencia oficial SIGPAC",
            "Hectáreas",
            "VER O CAMBIAR LO QUE HAY SEMBRADO",
        ],
    ),
    (
        "el cuaderno, con la tabla de los apuntes",
        ['[data-accion="inicio"][data-ir="mi_cuaderno"]'],
        [
            "Mi cuaderno",
            # **La tabla de los apuntes del año** (30/09/2026, fase 2): en el ordenador, la lista del año
            # entera —qué se hizo, dónde, cuántas hectáreas y cuándo— con lo último arriba.
            '<table class="tabla"',
            "Fecha",
            "Clase",
            "Hectáreas",
            'data-accion="ordenar-tabla"',
            "ha tratadas",
            # Y sus apuntes, con el producto de verdad de los datos de la prueba.
            "Glifosato 36 SL",
        ],
    ),
    (
        "las facturas, con su tabla",
        ['[data-accion="mis-cosas"]', '[data-accion="cesta-ver"]', '[data-accion="facturas-abrir"]'],
        [
            "Mis facturas",
            '<table class="tabla"',
            "Quién te lo vendió",
            "Total",
            # La factura de la prueba (la que deja `siembra_datos`) con un número de la tabla. Se comprueba
            # la **base**, y no el total, a propósito: una ruta anterior de esta misma comprobación cambia
            # el total (es la de «corregir una factura»), así que el total depende del orden de las rutas y
            # lo que se está mirando aquí es que la tabla enseña los números de la factura.
            "Cooperativa Agrícola de Peñaranda",
            "620,00",
        ],
    ),
    (
        # **Qué hay sembrado, con su tabla** (30/09/2026). Es la lista más larga del programa después de las
        # tierras y se le había quedado sin tabla: en el ordenador se veían tres tarjetas enormes por pantalla
        # (se vio en la revisión de la interfaz, con las 64 tierras de verdad).
        "qué hay sembrado, con su tabla",
        ['[data-accion="cultivo-ver-todos"]'],
        [
            "Qué hay sembrado",
            '<table class="tabla"',
            "Tierra",
            "Este año hay",
            "Rotación",
            "Otros años",
            "Estado",
            'data-accion="ordenar-tabla"',
            # El pie: cuántas tierras hay y cuántas tienen dicho su cultivo.
            "tierra",
            "con su cultivo dicho",
            # Y el botón de la fila, que es el mismo que el de la tarjeta.
            'data-accion="cultivo-decir"',
            # **Y el filtro de las que faltan** (30/09/2026, del diseño de escritorio de esta pantalla): la
            # franja dice a cuántas les falta y su botón enseña solo esas.
            'data-accion="cultivo-solo-las-que-faltan"',
        ],
    ),
    (
        # **El almacén, con su tabla** (30/09/2026): el libro de entradas y salidas del diseño de escritorio
        # que pidió Stitch (`docs/stitch/escritorio/almacen.png`). Se comprueba en el HTML que dibuja el
        # navegador de verdad: si React no montara la tabla, aquí no habría ni una cabecera.
        "el almacén, con su tabla",
        ['[data-accion="mis-cosas"]', '[data-accion="cesta-ver"]'],
        [
            "Lo que tengo en el almacén",
            '<table class="tabla"',
            # Las columnas del libro de entradas y salidas. **El número de registro no está aquí** (está en
            # el panel): en la tabla ensanchaba lo justo para apilar los dos botones de la última columna.
            "Producto",
            "Comprado",
            "Echado",
            "Te queda",
            "Estado",
            "Acciones",
            # Las cabeceras que ordenan la tabla, y el producto de verdad de los datos de la prueba.
            'data-accion="ordenar-tabla"',
            "Glifosato 36 SL",
            # El pie: cuántos productos hay. Se busca la forma («producto en el almacén») y no el número
            # entero, que es el que tenga la finca de la prueba.
            "producto en el almacén",
            # Y el panel de al lado, sin nada elegido: dice qué hacer en vez de quedarse en blanco.
            "El producto que has elegido",
            "Toca el nombre de un producto",
            'data-accion="elegir-fila"',
        ],
    ),
    (
        "el almacén, con un producto elegido en el panel",
        [
            '[data-accion="mis-cosas"]',
            '[data-accion="cesta-ver"]',
            # Se toca el nombre del producto en la tabla: eso es lo que abre su ficha al lado.
            '[data-accion="elegir-fila"]',
        ],
        [
            "El producto que has elegido",
            'class="panel-detalle"',
            # Sus cuentas, su número de registro (que en la tabla no cabe) y **de dónde sale lo comprado**:
            # el servidor lo mandaba desde siempre y ninguna pantalla lo enseñaba. En los datos de la prueba,
            # lo comprado viene de la factura.
            "Te queda",
            "Nº de registro",
            "De dónde sale",
            "Sale de tus facturas",
            # Y sus dos botones, ahí mismo: corregir el producto o borrarlo.
            'data-accion="cosa-corregir"',
            'data-accion="cosa-borrar"',
        ],
    ),
    # **La maquinaria** (T14, 03/10/2026). La pidió el agente del ticket al entregar, con sus tres textos,
    # y tenía razón: **este guion no mencionaba «maquinaria» ni una vez**, así que el módulo más nuevo se
    # quedaba fuera de la comprobación oficial de la interfaz. Se entra por el renglón del menú, que es
    # como entra el agricultor, y se buscan tres cosas distintas:
    #
    #   · «Mi maquinaria», el título: que la pantalla se dibuje;
    #   · «Próxima revisión», la cabecera de su columna —**con su tilde**, que es como la escribe el
    #     programa: el ticket la propuso sin tilde en su informe y así no la encontraría—;
    #   · «Vencida», que es la palabra del estado de la ITV que el guion deja apuntada con fecha pasada.
    #     Esa es la que importa de verdad: dice que el estado se decide con la fecha del papel y que se
    #     informa **con palabras y no solo con un color**.
    (
        "la maquinaria",
        ['[data-accion="maquinaria-ver"]'],
        ["Mi maquinaria", "Próxima revisión", "Vencida"],
    ),
]

# Los textos que **no pueden** salir en una pantalla concreta. Es la otra mitad de la comprobación: no
# basta con que salga lo que tiene que salir; lo que no toca, no puede estar.
NO_PUEDE_SALIR = {
    "inicio": ["Todavía no has apuntado nada"],
    # El buscador de tierras (ronda 82): después de buscar «suertes», la otra tierra **no puede salir**. Es
    # la mitad que importa de esta comprobación: que la lista se haya filtrado de verdad. Con un DOM de
    # mentira esto no se puede ver (el campo que pinta React no existe), y es justo lo que une el campo con
    # la lista.
    "el buscador de tierras": ["El Prado", "Calvarrasa de Arriba"],
    # El mismo buscador en «mis cosas» (ronda 87), con su propio campo y su propio filtro.
    "el buscador de tierras de mis cosas": ["El Prado", "Calvarrasa de Arriba"],
    # **El gasto no se ofrece como papel al que apuntar un movimiento del banco, y eso se comprueba.**
    # El guion deja un gasto de la reparación del remolque con **el mismo importe y el mismo día** que la
    # línea del extracto: es el caso en el que un programa descuidado contaría el mismo dinero dos veces
    # (una como gasto y otra como pago del banco). Aquí no puede salir porque **conciliar solo apunta a
    # papeles de tres clases** —factura nuestra, cobro sin factura y factura de compra— y un gasto no es
    # ninguna de las tres: las demás clases están declaradas como pendientes en
    # `extractos.CLASES_QUE_FALTAN`. Es un límite de esta versión, y por eso se dice aquí, en vez de
    # dejar que se descubra contando dinero.
    "el recorrido 3: conciliar un movimiento con su papel": ["La reparación del remolque"],
}

# Pantallas migradas a React que **no** se recorren aquí, con el motivo. Es importante decirlo: si no,
# el siguiente que lea esta lista cree que están todas y no lo están.
NO_SE_RECORREN = {
    "firmar": (
        "la pantalla de firmar solo se abre con un certificado configurado (`puede_firmar`), y el "
        "servidor de pruebas de esta comprobación no lo tiene: el botón no existe y la ruta fallaría "
        "por un motivo que no es de la pantalla. Está cubierta por las pruebas del componente y por "
        "la de cableado (`tests_js/react.test.js` e `interfaz.test.js`)"
    ),
}


# ==========================================================================
# 6 y 7. El volumen de verdad, y las descargas pulsando el botón
# ==========================================================================
#
# ## Por qué estas dos secciones existen
#
# Todo lo de arriba se comprueba con **dos tierras y una campaña**, y con un navegador que solo sabe
# volcar el HTML (`--dump-dom`). Eso deja fuera justo lo que el encargo pide comprobar:
#
#   · Que una lista larga diga el número que de verdad tiene, que el buscador **filtre**, que los
#     filtros dejen ver 10 de 64, que la selección múltiple marque y desmarque, y que un nombre de
#     ochenta caracteres no rompa una tarjeta ni ensanche una tabla. Con dos tierras, nada de eso se
#     puede ver: una lista de dos filas se lee igual esté bien o esté mal.
#   · Que una exportación **se lleve lo que se está viendo**. Eso no está en el DOM: está en un
#     fichero que el navegador guarda. Un volcado de HTML no puede distinguir «descargó 10» de
#     «descargó 64», ni siquiera «descargó» de «no hizo nada».
#
# Las dos cosas las sabe hacer `navegador_cdp.NavegadorDeVerdad` (el navegador manejado por el
# protocolo de depuración): pulsa de verdad y observa las descargas. Y los datos los deja
# `datos_representativos.preparar`, que devuelve **los identificadores que ha creado** para no tener
# que hablar de «la primera tierra».

# Los tres anchos del contrato. Se miden cambiando las métricas del dispositivo, no abriendo otra
# ventana: medir es lo que da valor a la comprobación (si un ancho no se mide, no se ha comprobado).
ANCHOS_DEL_CONTRATO = (390, 1024, 1440)

# Las pantallas con lista larga, con lo que tiene que salir en cada una. Los textos que se buscan
# **salen del escenario** —el número de tierras, los alias, los conceptos— y no se escriben a mano:
# un número escrito a mano deja de ser verdad en cuanto cambia el escenario, y entonces la
# comprobación pasa por el motivo equivocado.
PANTALLAS_CON_VOLUMEN = (
    (
        "las tierras",
        "#/tierras",
        lambda e: [
            f"Tienes {len(e.tierras)} tierras apuntadas",
            e.tierras[0].alias,
            e.tierras[-1].alias,
        ],
    ),
    (
        "las tierras en el mapa y en la tabla",
        "#/tierras/mapa",
        lambda e: [
            # **Sin filtro el pie no dice «ves N de M»**: dice el total de la finca y los tres «sin».
            # La frase «ves N de M» sale cuando hay filtro, y eso se comprueba más abajo, buscando y
            # filtrando de verdad.
            f"{len(e.tierras)} tierras",
            "MARCAR LAS QUE SE VEN",
            "QUITAR LA SELECCIÓN",
            "No has marcado ninguna tierra.",
        ],
    ),
    (
        "los papeles",
        "#/papeles",
        lambda e: ["Los papeles", "VER EL PAPEL", "SUBIR EL PAPEL"],
    ),
    (
        "las cuentas",
        "#/cuentas",
        lambda e: [f"Tienes {len(e.gastos)} gastos apuntados.", "Gasto de la prueba"],
    ),
    (
        "el banco y los papeles",
        "#/cuentas/bancos",
        lambda e: [
            "DESCARGAR EL EXTRACTO",
            # **El alcance que anuncia la pantalla**, que es la mitad de lo que pide el encargo:
            # «se descarga lo que estás viendo». Si esto cambiara, la comprobación lo dice.
            "Se descarga en un fichero lo que estás viendo",
            # **El recuento de la lista**: es el número que tiene que salir también en el fichero.
            # (El primer movimiento del extracto **no se busca aquí**: la lista enseña los más nuevos
            # y el «COSECHERA 01» cae más abajo, fuera de lo que la pantalla pinta. Lo que se lleva el
            # fichero se comprueba en la sección de las descargas, contando sus filas.)
            f"Tienes {e.movimientos_de_la_cuenta_principal} movimientos",
        ],
    ),
    (
        "los contactos",
        "#/contactos",
        lambda e: [f"Tienes {len(e.contactos)} fichas apuntadas.", "Proveedor de la prueba 01 S.L."],
    ),
    (
        "los trabajos",
        "#/trabajos",
        lambda e: ["Lo que tengo pensado hacer", "Lo que he hecho", "YA LO HE HECHO"],
    ),
    (
        "el libro del almacén",
        "#/almacen/libro",
        lambda e: ["El libro del almacén", "Lo que queda en el almacén"],
    ),
    (
        "mi cuaderno",
        "#/cuaderno",
        lambda e: [
            "apuntes en el cuaderno",
            "Lo que falta por completar",
            # El botón del fichero de datos y el del cuaderno de la Junta: los dos exportan, y los
            # dos tienen que existir con este volumen (el de la Junta solo sale cuando el servidor
            # sabe qué hojas llevan datos, o sea cuando de verdad hay algo que sacar).
            "GUARDAR LOS DATOS EN UN FICHERO",
            "SACAR MI CUADERNO",
        ],
    ),
    (
        "lo que he vendido",
        "#/ventas",
        lambda e: ["Lo que he vendido", f"{e.cuantas['ventas']} ventas apuntadas"],
    ),
)


def _texto_de_la_pantalla(nav: NavegadorDeVerdad) -> str:
    """Lo que se lee en la pantalla, para poder comprobar los recuentos y las frases."""
    return (
        nav.evaluar(
            "document.querySelector('#pantalla') ? document.querySelector('#pantalla').innerText : ''"
        )
        or ""
    )


def _lo_que_se_sale(nav: NavegadorDeVerdad) -> str:
    """Cuánto se sale la página de lo ancho («1367 de 1024»), o vacío si cabe entera.

    Se mide el ancho **de verdad** de la página contra el ancho **de verdad** de la ventana. Sin
    esto, una comprobación de anchura que midiera otra cosa diría que todo cabe sin haber mirado.
    """
    dentro = int(nav.evaluar("window.innerWidth") or 0)
    ancho = int(
        nav.evaluar(
            "Math.max(document.documentElement.scrollWidth, "
            "document.body ? document.body.scrollWidth : 0)"
        )
        or 0
    )
    return f"{ancho} de {dentro}" if ancho > dentro + 1 else ""


def _abrir_con_la_sesion(
    nav: NavegadorDeVerdad, direccion: str, ruta: str, paso: int, *, segundos: float = 25.0
) -> bool:
    """Abre una pantalla **con la sesión puesta** y espera a que la aplicación la monte.

    Dos cosas que costaron una vuelta cada una y que no se pueden «simplificar»:

      · **La consulta cambia en cada vuelta** (`?paso=3#/tierras`). Cambiar solo el trozo de la
        dirección (`#/...`) **no recarga la página**: el navegador solo avisa del cambio de trozo, y
        la aplicación se queda con el token y los datos que leyó al arrancar. Con la consulta
        distinta, cada pantalla es un documento nuevo, que es lo que se quiere medir.
      · **El token se pone en cada documento nuevo** (`Page.addScriptToEvaluateOnNewDocument`), antes
        de que arranque la aplicación: el navegador se abre sin ventana y no hay nadie para teclear
        en la pantalla de entrar.
    """
    nav.abrir(f"{direccion}/index.html?paso={paso}{ruta}")
    return nav.esperar(
        "document.querySelector('#pantalla') && "
        "document.querySelector('#pantalla').innerText.length > 200",
        segundos=segundos,
    )


def _el_volumen(
    nav: NavegadorDeVerdad, direccion: str, escenario: datos_representativos.Escenario, paso: list[int]
) -> None:
    """Las pantallas con lista larga, a los tres anchos del contrato."""
    for nombre, ruta, esperadas in PANTALLAS_CON_VOLUMEN:
        paso[0] += 1
        montada = _abrir_con_la_sesion(nav, direccion, ruta, paso[0])
        comprobar(montada, f"volumen · {nombre}: la pantalla se monta con {len(escenario.tierras)} tierras y lo demás")
        if not montada:
            continue
        # **Y se espera a los datos, no solo a que la pantalla esté montada.** Hay pantallas —las
        # cuentas, el banco— que se pintan primero con sus explicaciones y piden lo suyo al servidor
        # después: leer el texto en cuanto hay 200 caracteres lee la pantalla **antes** de que lleguen
        # los gastos, y entonces la comprobación diría que no sale un recuento que sí sale.
        esperadas_aqui = [esperado for esperado in esperadas(escenario) if esperado]
        if esperadas_aqui:
            nav.esperar(
                " && ".join(
                    f"document.body.innerText.includes({json.dumps(esperado)})"
                    for esperado in esperadas_aqui
                ),
                segundos=20,
            )
        texto = _texto_de_la_pantalla(nav)
        falta = [esperado for esperado in esperadas_aqui if esperado not in texto]
        comprobar(
            falta == [],
            f"volumen · {nombre}: sale lo que tiene que salir "
            f"({', '.join(falta) if falta else 'los recuentos y los datos de verdad'})",
        )
        for ancho in ANCHOS_DEL_CONTRATO:
            nav.medir(ancho, 900)
            # Un respiro para que el navegador termine de recolocar lo que cambia de forma al pasar
            # de móvil a ordenador: medir a media transición daría un ancho que no es el de nadie.
            time.sleep(0.3)
            se_sale = _lo_que_se_sale(nav)
            comprobar(
                se_sale == "",
                f"volumen · {nombre}: a {ancho} px no se sale de lo ancho "
                f"({'se sale ' + se_sale + ' px' if se_sale else 'cabe entera'})",
            )
        nav.medir(1440, 900)


def _cuantas_tierras_se_ven(nav: NavegadorDeVerdad) -> int:
    """Cuántas tierras tiene **pintadas** la tabla de la vista de las tierras.

    Se cuentan las casillas de marcar, que son una por fila. Es la mitad que hace que un recuento
    valga: la pantalla puede decir «ves 10 de 64» y estar pintando 64 filas, y eso es justo lo que
    hay que cazar.
    """
    return int(nav.evaluar("document.querySelectorAll('[data-accion=\"t06-marcar\"]').length") or 0)


def _el_volumen_se_busca_y_se_marca(
    nav: NavegadorDeVerdad, direccion: str, escenario: datos_representativos.Escenario, paso: list[int]
) -> None:
    """El buscador, los filtros, la selección múltiple y los datos incompletos, **pulsando**.

    Es la mitad que no se puede comprobar con dos tierras: con 64, un buscador que no filtre deja
    64 filas y un filtro que no filtre deja el pie diciendo «ves 64 de 64».
    """
    total = len(escenario.tierras)
    paso[0] += 1
    comprobar(
        _abrir_con_la_sesion(nav, direccion, "#/tierras/mapa", paso[0]),
        "volumen · la vista de las tierras se abre para buscar y marcar",
    )
    # --- lo primero, sin tocar nada ------------------------------------------------------------
    nav.esperar("document.body.innerText.includes('No has marcado ninguna tierra.')", segundos=15)
    texto = _texto_de_la_pantalla(nav)
    pintadas = _cuantas_tierras_se_ven(nav)
    # **Sin filtro el pie no dice «ves N de M», dice el total de la finca** (y los tres «sin»): por
    # eso no se busca la misma frase que con el filtro puesto.
    comprobar(
        f"{total} tierras" in texto and pintadas == total,
        f"volumen · sin filtros, el pie dice que hay {total} tierras y la tabla pinta {pintadas}",
    )

    # --- la selección múltiple: marcar todo, desmarcarlo y marcar una ---------------------------
    nav.pulsar('[data-accion="t06-marcar-todas"]')
    texto = _texto_de_la_pantalla(nav)
    casillas = int(nav.evaluar("document.querySelectorAll('[data-accion=\"t06-marcar\"]:checked').length") or 0)
    comprobar(
        f"Has marcado {total} tierras" in texto and casillas == total,
        f"volumen · MARCAR LAS QUE SE VEN marca las {total} tierras y su recuento cuadra "
        f"(dice «{'Has marcado ' + str(total) + ' tierras' if f'Has marcado {total} tierras' in texto else 'otra cosa'}» y hay {casillas} casillas marcadas)",
    )
    nav.pulsar('[data-accion="t06-desmarcar-todas"]')
    texto = _texto_de_la_pantalla(nav)
    casillas = int(nav.evaluar("document.querySelectorAll('[data-accion=\"t06-marcar\"]:checked').length") or 0)
    comprobar(
        "No has marcado ninguna tierra." in texto and casillas == 0,
        f"volumen · QUITAR LA SELECCIÓN desmarca las {total} tierras ({casillas} casillas marcadas)",
    )
    # Y una sola, **por su identificador** (el que devolvió la preparación): es lo que comprueba que
    # la casilla de una fila concreta marca esa fila y no otra.
    una = escenario.tierras[0]
    nav.pulsar(f'[data-accion="t06-marcar"][data-id="{una.id}"]')
    texto = _texto_de_la_pantalla(nav)
    casillas = int(nav.evaluar("document.querySelectorAll('[data-accion=\"t06-marcar\"]:checked').length") or 0)
    comprobar(
        "Has marcado 1 tierra" in texto and casillas == 1,
        "volumen · la casilla de una tierra la marca sola, y el recuento lo dice en singular",
    )
    nav.pulsar(f'[data-accion="t06-marcar"][data-id="{una.id}"]')
    comprobar(
        "No has marcado ninguna tierra." in _texto_de_la_pantalla(nav),
        "volumen · volver a pulsar la casilla la desmarca",
    )

    # --- el buscador: lo que casa sale, lo que no casa no ---------------------------------------
    nav.evaluar(
        "(() => { const campo = document.querySelector('#t06_buscar');"
        f" campo.value = {json.dumps(escenario.búsqueda_de_tierra)};"
        " campo.dispatchEvent(new Event('input', { bubbles: true })); return null; })()"
    )
    nav.pulsar('[data-accion="t06-buscar"]')
    nav.esperar("document.body.innerText.includes('Ves ')", segundos=10)
    texto = _texto_de_la_pantalla(nav)
    casan = escenario.cuantas_casan
    pintadas = _cuantas_tierras_se_ven(nav)
    comprobar(
        f"Ves {casan} de {total} tierras" in texto and pintadas == casan,
        f"volumen · el buscador «{escenario.búsqueda_de_tierra}» deja {casan} de {total} tierras "
        f"y la tabla pinta {pintadas} "
        f"(el pie dice «{'Ves ' + str(casan) + ' de ' + str(total) + ' tierras' if f'Ves {casan} de {total} tierras' in texto else 'otra cosa'}»)",
    )
    # **La mitad que importa**: la tierra que no casa no puede seguir ahí. Se busca una que no casó
    # (por construcción) y se exige que no esté en la pantalla.
    sin_casar = next(
        tierra for tierra in escenario.tierras if escenario.búsqueda_de_tierra.lower() not in tierra.alias.lower()
    )
    comprobar(
        sin_casar.alias not in texto,
        f"volumen · el buscador no deja la tierra que no casa ({sin_casar.alias[:40]}…)",
    )
    nav.pulsar('[data-accion="t06-quitar-filtros"]')
    pintadas = _cuantas_tierras_se_ven(nav)
    comprobar(
        f"{total} tierras" in _texto_de_la_pantalla(nav) and pintadas == total,
        f"volumen · QUITAR LOS FILTROS devuelve las {total} tierras a la vista (pinta {pintadas})",
    )

    # --- un filtro por lo sembrado ---------------------------------------------------------------
    # El valor de la opción lo da la pantalla, no se escribe a mano: se busca el botón cuyo texto es
    # el cultivo y se pulsa **ese**, por su `data-valor`.
    cultivo = "TRIGO BLANDO"
    sin_ese_cultivo = next(
        tierra for tierra in escenario.tierras if tierra.cultivo != cultivo
    )
    valor = nav.evaluar(
        "(() => { const boton = Array.from(document.querySelectorAll("
        "'[data-accion=\"t06-filtrar\"][data-campo=\"cultivo\"]')).find((b) => b.innerText.trim() === "
        f"{json.dumps(cultivo)}); return boton ? boton.dataset.valor : null; }})()"
    )
    comprobar(
        valor is not None,
        f"volumen · la vista de las tierras ofrece el filtro «{cultivo}» (valor {valor!r})",
    )
    if valor is not None:
        nav.pulsar(f'[data-accion="t06-filtrar"][data-campo="cultivo"][data-valor="{valor}"]')
        texto = _texto_de_la_pantalla(nav)
        con_ese_cultivo = escenario.cuantas_casan_por_cultivo.get(cultivo, 0)
        pintadas = _cuantas_tierras_se_ven(nav)
        comprobar(
            f"Ves {con_ese_cultivo} de {total} tierras" in texto and pintadas == con_ese_cultivo,
            f"volumen · el filtro de «{cultivo}» deja {con_ese_cultivo} de {total} tierras "
            f"(la tabla pinta {pintadas})",
        )
        comprobar(
            sin_ese_cultivo.alias not in texto,
            "volumen · el filtro de cultivo deja fuera lo que no tiene ese cultivo "
            f"({sin_ese_cultivo.cultivo or 'sin decir'})",
        )
        nav.pulsar('[data-accion="t06-quitar-filtros"]')

    # --- los datos que no se saben: un hueco, nunca un cero ---------------------------------------
    sin_superficie = escenario.tierras_sin_superficie[0]
    fila = nav.evaluar(
        "(() => { const boton = document.querySelector("
        f"'[data-accion=\"t06-elegir-fila\"][data-id=\"{sin_superficie.id}\"]');"
        " return boton ? boton.closest('tr').innerText : null; })()"
    )
    comprobar(
        fila is not None and "Sin hectáreas dichas" in fila,
        "volumen · una tierra sin superficie se lee «Sin hectáreas dichas»",
    )
    comprobar(
        fila is not None and "0,00" not in fila and "0 ha" not in fila,
        "volumen · una tierra sin superficie NO se lee como cero hectáreas",
    )
    sin_cultivo = escenario.tierras_sin_cultivo[0]
    fila = nav.evaluar(
        "(() => { const boton = document.querySelector("
        f"'[data-accion=\"t06-elegir-fila\"][data-id=\"{sin_cultivo.id}\"]');"
        " return boton ? boton.closest('tr').innerText : null; })()"
    )
    comprobar(
        fila is not None and "Sin decir qué tiene" in fila,
        "volumen · una tierra sin cultivo declarado se lee «Sin decir qué tiene»",
    )
    sin_forma = escenario.tierras_sin_forma[0]
    fila = nav.evaluar(
        "(() => { const boton = document.querySelector("
        f"'[data-accion=\"t06-elegir-fila\"][data-id=\"{sin_forma.id}\"]');"
        " return boton ? boton.closest('tr').innerText : null; })()"
    )
    comprobar(
        fila is not None and "SIN FORMA" in fila,
        "volumen · una tierra sin forma se dice con palabras («SIN FORMA»), no con un color",
    )

    # --- el nombre largo, en la lista de tarjetas ------------------------------------------------
    paso[0] += 1
    comprobar(
        _abrir_con_la_sesion(nav, direccion, "#/tierras", paso[0]),
        "volumen · la lista de tarjetas se abre con nombres largos",
    )
    largo = max(escenario.tierras, key=lambda tierra: len(tierra.alias))
    nav.esperar(
        f"document.body.innerText.includes({json.dumps(largo.alias)})", segundos=15
    )
    texto = _texto_de_la_pantalla(nav)
    comprobar(
        largo.alias in texto,
        f"volumen · el nombre más largo ({len(largo.alias)} caracteres) se lee entero: {largo.alias[:60]}…",
    )
    nav.medir(390, 900)
    comprobar(
        _lo_que_se_sale(nav) == "",
        "volumen · el nombre más largo no rompe la tarjeta a 390 px "
        f"({'se sale ' + _lo_que_se_sale(nav) if _lo_que_se_sale(nav) else 'cabe entera'})",
    )
    nav.medir(1440, 900)


def _el_fichero_descargado(
    nav: NavegadorDeVerdad,
    direccion: str,
    ruta: str,
    selector: str,
    carpeta: pathlib.Path,
    paso: list[int],
    *,
    antes: list[str] | None = None,
) -> pathlib.Path | None:
    """Abre una pantalla, **pulsa el botón de verdad** y devuelve el fichero que ha bajado.

    Cada descarga va a **su propia carpeta vacía**: el ayudante devuelve el fichero más reciente de
    la carpeta, así que con una sola carpeta para todas no se sabría de qué botón es cada fichero (y
    el navegador añade «(1)» al nombre cuando ya existe otro igual).

    `antes` son los pasos que hay que dar en esa pantalla antes de descargar (escribir en el
    buscador y pulsarlo, por ejemplo). Un paso que empieza por `pulsar:` es un clic; lo demás es
    JavaScript que se ejecuta en la página.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    for viejo in carpeta.iterdir():
        viejo.unlink()
    paso[0] += 1
    if not _abrir_con_la_sesion(nav, direccion, ruta, paso[0]):
        return None
    for accion in antes or []:
        if accion.startswith("pulsar:"):
            nav.pulsar(accion[len("pulsar:") :])
        else:
            nav.evaluar(accion)
    nav.descargas_en(str(carpeta))
    try:
        nav.pulsar(selector)
    except RuntimeError:
        return None
    return nav.lo_descargado(segundos=60)


def _filas_del_csv(fichero: pathlib.Path, separador: str = ";") -> list[list[str]]:
    """Las filas de un CSV, sin las vacías. El del cuaderno trae marca de orden de bytes al principio."""
    texto = fichero.read_text(encoding="utf-8-sig")
    return [fila for fila in csv.reader(texto.splitlines(), delimiter=separador) if any(fila)]


def _la_pista_del_boton(nav: NavegadorDeVerdad, selector: str) -> str:
    """Lo que la pantalla dice del botón que se va a pulsar: su texto y **el bloque donde vive**.

    Es lo que permite comprobar el «alcance anunciado» del encargo: si un botón se lleva lo
    filtrado, la pantalla tiene que decirlo. Y se lee **el bloque, no la pantalla entera**: buscar la
    frase en toda la pantalla da falsos positivos —«todo el año» también está en el bloque de las
    medidas preventivas—, y una comprobación que pasa por el motivo equivocado no vale nada. Se sube
    por los antepasados hasta el último que **no** es el contenedor de la pantalla (`main#pantalla`),
    que es lo que se llama «el bloque donde vive el botón».
    """
    return (
        nav.evaluar(
            "(() => { const boton = document.querySelector("
            f"{json.dumps(selector)}); if (!boton) return '';"
            " let caja = boton.parentElement; let bloque = boton;"
            " while (caja && caja.tagName !== 'MAIN' && caja.tagName !== 'BODY'"
            " && caja.tagName !== 'HTML') { bloque = caja; caja = caja.parentElement; }"
            " return boton.innerText + ' || ' + bloque.innerText; })()"
        )
        or ""
    )


def _las_descargas(
    nav: NavegadorDeVerdad,
    direccion: str,
    escenario: datos_representativos.Escenario,
    paso: list[int],
    temporal: pathlib.Path,
) -> None:
    """**Pulsar cada botón de exportar y mirar el fichero que se descarga.**

    Se comprueba lo que no se puede comprobar por la API: que el botón existe, que hace algo, cómo se
    llama el fichero, en qué formato sale, qué filas lleva, de qué explotación y de qué campaña es, y
    **si se lleva lo que la pantalla dice que se lleva**. Y que no aparezca ni un registro de otra
    explotación (la preparación crea dos cuentas justo para esto).
    """
    jena = [marca for marca in escenario.marcas_ajenas if marca]

    def no_se_cuela(texto: str) -> str:
        """La marca de la explotación ajena que apareciera, o vacío. Ninguna puede aparecer."""
        return next((marca for marca in jena if marca in texto), "")

    # --------------------------------------------------------------- 1. el fichero de datos
    fichero = _el_fichero_descargado(
        nav,
        direccion,
        "#/cuaderno",
        '[data-accion="sacar-datos"]',
        temporal / "datos",
        paso,
    )
    comprobar(fichero is not None, "descargas · el botón «GUARDAR LOS DATOS EN UN FICHERO» descarga algo")
    if fichero is not None:
        anio = escenario.volumen.campana_actual.anio
        comprobar(
            fichero.name == f"cuaderno_{anio}.csv",
            f"descargas · el fichero de datos se llama «cuaderno_{anio}.csv» (se llama «{fichero.name}»)",
        )
        texto = fichero.read_text(encoding="utf-8-sig")
        primera = texto.splitlines()[0] if texto.splitlines() else ""
        comprobar(
            escenario.volumen.nombre in primera and str(anio) in primera,
            f"descargas · el fichero de datos dice de qué explotación y de qué campaña es («{primera[:90]}»)",
        )
        tierras_en_el_fichero = sum(1 for tierra in escenario.tierras if tierra.alias in texto)
        comprobar(
            tierras_en_el_fichero == len(escenario.tierras),
            f"descargas · el fichero de datos lleva las {len(escenario.tierras)} tierras "
            f"({tierras_en_el_fichero} de {len(escenario.tierras)})",
        )
        comprobar(
            not no_se_cuela(texto),
            f"descargas · el fichero de datos no lleva nada de otra explotación ({no_se_cuela(texto)})",
        )
        # **El alcance anunciado**, que es lo que pide el encargo: si un botón solo puede llevar una
        # cosa (todo, lo filtrado o lo seleccionado), tiene que decir cuál. Este botón se lleva **el
        # cuaderno entero del año que está abierto**, y eso no lo dice ni su etiqueta ni el bloque
        # donde vive: se comprueba y, si no lo dice, se dice —que es lo que hay que hacer con un
        # hallazgo, en vez de taparlo—.
        anuncio = _la_pista_del_boton(nav, '[data-accion="sacar-datos"]')
        comprobar(
            any(
                frase in anuncio
                for frase in (
                    "todo el año",
                    "todos los años",
                    "el año que está abierto",
                    "lo que estás viendo",
                    "Se abre con Excel",
                )
            ),
            "descargas · el botón «GUARDAR LOS DATOS EN UN FICHERO» dice qué se lleva: ni su etiqueta "
            "ni la barra de botones donde vive dicen si son todos los años, el año que está abierto "
            "o lo que se ve. (El texto que lo explicaba existe en el servidor —`cuaderno.datos_pista`, "
            "«Se abre con Excel. Guárdalo: es tu cuaderno, por si te lo piden»— y no lo pinta ninguna "
            "pantalla.)",
        )

    # --------------------------------------------------------------- 2. el papel (PDF)
    fichero = _el_fichero_descargado(
        nav, direccion, "#/cuaderno", '[data-accion="sacar-papel"]', temporal / "papel", paso
    )
    comprobar(fichero is not None, "descargas · el botón «SACAR EN PAPEL» descarga algo")
    if fichero is not None:
        comprobar(
            fichero.name == "cuaderno.pdf",
            f"descargas · el papel se llama «cuaderno.pdf» (se llama «{fichero.name}»)",
        )
        comprobar(
            fichero.read_bytes()[:4] == b"%PDF",
            "descargas · el fichero del papel es un PDF de verdad (empieza por %PDF)",
        )

    # --------------------------------------------------------------- 3. el cuaderno de la Junta
    fichero = _el_fichero_descargado(
        nav,
        direccion,
        "#/cuaderno",
        '[data-accion="cuaderno-sacar"]',
        temporal / "junta",
        paso,
    )
    comprobar(fichero is not None, "descargas · el botón «SACAR MI CUADERNO» descarga algo")
    if fichero is not None:
        comprobar(
            fichero.name == "cuaderno-de-la-junta.xlsx",
            f"descargas · el cuaderno de la Junta se llama «cuaderno-de-la-junta.xlsx» (se llama «{fichero.name}»)",
        )
        # Y **su alcance, anunciado en la pantalla**: «todo lo que tienes apuntado». Es la otra mitad
        # de lo que pide el encargo y aquí sí se dice, así que se exige.
        comprobar(
            "todo lo que tienes apuntado" in _la_pista_del_boton(nav, '[data-accion="cuaderno-sacar"]'),
            "descargas · la pantalla dice qué se lleva el cuaderno de la Junta (todo lo apuntado)",
        )
        try:
            import openpyxl

            libro = openpyxl.load_workbook(fichero, read_only=True)
            comprobar(
                len(libro.sheetnames) == 25,
                f"descargas · el cuaderno de la Junta es un XLSX que se abre y trae las 25 hojas "
                f"({len(libro.sheetnames)})",
            )
            todo = []
            for hoja in libro.worksheets:
                for fila in hoja.iter_rows(values_only=True):
                    todo.extend(str(celda) for celda in fila if celda is not None)
            dentro = "\n".join(todo)
            comprobar(
                escenario.volumen.nombre in dentro and str(escenario.volumen.campana_actual.anio) in dentro,
                "descargas · el cuaderno de la Junta dice de qué explotación y de qué año es",
            )
            # **Las tierras van por sus números del SIGPAC, no por el alias del agricultor**, y está
            # bien: el cuaderno de la Junta no conoce los nombres que él les pone. Lo que se
            # comprueba es que **cada tierra con referencia** tiene su fila, con su polígono y su
            # parcela, en la hoja 2.1 (la de «datos de las parcelas»). Buscar el alias ahí sería
            # buscar algo que ese fichero no debe llevar.
            hoja_parcelas = next(
                (hoja for hoja in libro.worksheets if hoja.title.startswith("2.1")), None
            )
            comprobar(
                hoja_parcelas is not None,
                "descargas · el cuaderno de la Junta trae la hoja 2.1 de los datos de las parcelas",
            )
            if hoja_parcelas is not None:
                filas = list(hoja_parcelas.iter_rows(values_only=True))
                en_el_fichero = {
                    (str(fila[6]), str(fila[7]))
                    for fila in filas
                    if len(fila) > 7 and fila[6] not in (None, "") and fila[7] not in (None, "")
                }
                esperadas = {
                    (tierra.ref_sigpac.split("-")[4], tierra.ref_sigpac.split("-")[5])
                    for tierra in escenario.tierras
                    if tierra.ref_sigpac
                }
                faltan = sorted(esperadas - en_el_fichero)
                comprobar(
                    not faltan,
                    f"descargas · el cuaderno de la Junta lleva las {len(esperadas)} tierras con "
                    f"referencia, cada una con su polígono y su parcela "
                    f"({len(esperadas) - len(faltan)} de {len(esperadas)}"
                    + (f"; faltan {faltan[:3]}" if faltan else "") + ")",
                )
            comprobar(
                not no_se_cuela(dentro),
                f"descargas · el cuaderno de la Junta no lleva nada de otra explotación ({no_se_cuela(dentro)})",
            )
            libro.close()
        except ImportError:  # pragma: no cover - openpyxl está en requirements.txt
            comprobar(False, "descargas · no se ha podido abrir el XLSX (falta openpyxl)")

    # --------------------------------------------------------------- 4. el extracto, entero
    fichero = _el_fichero_descargado(
        nav,
        direccion,
        "#/cuentas/bancos",
        '[data-accion="banco-exportar"]',
        temporal / "extracto-todo",
        paso,
    )
    comprobar(fichero is not None, "descargas · el botón «DESCARGAR EL EXTRACTO» descarga algo")
    sin_filtro = ""
    if fichero is not None:
        comprobar(
            fichero.name == "extracto.csv",
            f"descargas · el extracto se llama «extracto.csv» (se llama «{fichero.name}»)",
        )
        sin_filtro = fichero.read_text(encoding="utf-8-sig")
        filas = _filas_del_csv(fichero)
        comprobar(
            filas and "Concepto" in filas[0],
            f"descargas · el extracto lleva sus cabeceras ({' · '.join(filas[0][:4]) if filas else 'sin cabecera'})",
        )
        de_la_principal = escenario.movimientos_de_la_cuenta_principal
        comprobar(
            sin_filtro.count("CUOTA DE LA COSECHERA") == escenario.movimientos_que_casan
            and sin_filtro.count("GASTO CORRIENTE DE LA NAVE") == de_la_principal - escenario.movimientos_que_casan,
            "descargas · sin filtro, el extracto se lleva los movimientos de la cuenta que está puesta "
            f"({len(filas) - 1} filas)",
        )
        comprobar(
            not no_se_cuela(sin_filtro),
            f"descargas · el extracto no lleva nada de otra explotación ({no_se_cuela(sin_filtro)})",
        )
        anuncio = _la_pista_del_boton(nav, '[data-accion="banco-exportar"]')
        comprobar(
            "lo que estás viendo" in anuncio,
            f"descargas · la pantalla del banco dice qué se lleva el fichero («{anuncio[:120]}»)",
        )

    # --------------------------------------------------------------- 5. el extracto, filtrado
    # **La comprobación que pidió el encargo con sus palabras**: «un filtro de 10 tierras entre 64 no
    # debe exportar silenciosamente las 64». Se filtra la lista por un texto que casa con 10 de los 30
    # movimientos de la cuenta y se mira el fichero: tiene que llevar 10, no 30.
    escribir_el_filtro = (
        "(() => { const campo = document.querySelector('#banco-buscar');"
        f" campo.value = {json.dumps(escenario.búsqueda_del_banco)};"
        " campo.dispatchEvent(new Event('input', { bubbles: true })); return null; })()"
    )
    fichero = _el_fichero_descargado(
        nav,
        direccion,
        "#/cuentas/bancos",
        '[data-accion="banco-exportar"]',
        temporal / "extracto-filtrado",
        paso,
        antes=[escribir_el_filtro, 'pulsar:[data-accion="banco-buscar"]'],
    )
    comprobar(fichero is not None, "descargas · el extracto filtrado se descarga")
    if fichero is not None and sin_filtro:
        texto = fichero.read_text(encoding="utf-8-sig")
        filas = _filas_del_csv(fichero)
        casan = escenario.movimientos_que_casan
        comprobar(
            texto.count("CUOTA DE LA COSECHERA") == casan,
            f"descargas · con «{escenario.búsqueda_del_banco}» puesto, el fichero lleva los {casan} "
            f"movimientos que se ven, no los {escenario.movimientos_de_la_cuenta_principal} "
            f"(lleva {texto.count('CUOTA DE LA COSECHERA')})",
        )
        comprobar(
            "GASTO CORRIENTE DE LA NAVE" not in texto,
            "descargas · el extracto filtrado NO se lleva los movimientos que el filtro deja fuera",
        )
        comprobar(
            len(filas) - 1 == casan,
            f"descargas · el extracto filtrado tiene {casan} filas de datos ({len(filas) - 1})",
        )

    # --------------------------------------------------------------- 6. el papel de un documento
    # Este no es una exportación de una lista: es la descarga del fichero de un papel. Se comprueba
    # igual (nombre, formato y que el contenido sea el que se subió) porque es un botón de descargar.
    fichero = _el_fichero_descargado(
        nav, direccion, "#/papeles", '[data-accion="papel-ver"]', temporal / "papel-de-un-documento", paso
    )
    comprobar(fichero is not None, "descargas · el botón «VER EL PAPEL» de un papel descarga su fichero")
    if fichero is not None:
        comprobar(
            fichero.name == datos_representativos.NOMBRE_DEL_PAPEL_CON_FICHERO,
            f"descargas · el papel descargado se llama como el que se subió "
            f"(«{fichero.name}», se subió «{datos_representativos.NOMBRE_DEL_PAPEL_CON_FICHERO}»)",
        )
        comprobar(
            fichero.read_bytes() == datos_representativos.UN_PNG_DE_UN_PIXEL,
            "descargas · el papel descargado es el mismo fichero que se subió, byte a byte",
        )


def pagina_de_pantalla(token: str, direccion: str, ruta: list[str]) -> pathlib.Path:
    """Una página que deja la sesión puesta y arranca la aplicación, **servida por el propio programa**.

    Se hace así y no tecleando en la pantalla de entrar porque el navegador se abre sin ventana: no
    hay nadie para escribir.

    **Y se sirve desde el propio servidor, no desde un fichero local.** Se probó primero con un
    fichero en la carpeta temporal y **no funcionaba**: un `import` de módulo desde otro origen está
    prohibido por el navegador (hace falta CORS, y el programa no lo pone porque no lo necesita), así
    que `app.js` no llegaba a cargarse y la pantalla salía vacía. Ése fue, de hecho, el primer fallo
    que encontró esta comprobación.

    El fichero se crea al empezar y **se borra al terminar** (ver `main`): si se quedara ahí, sería un
    fichero de más dentro de la aplicación.
    """
    token_json = json.dumps(token)
    contenido = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <!-- El mismo `viewport` que `index.html`. Sin él, el navegador dibuja la página como si fuera
       ancha y la captura sale recortada: eso pasó, y me hizo buscar un fallo de anchura en la
       aplicación que no existía. -->
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Comprobación en navegador</title>
  <link rel="stylesheet" href="/estilos.css">
</head>
<body>
  <div id="aviso-pendientes" class="aviso oculto"></div>
  <!-- El armazón del ordenador (30/09/2026): el menú lateral y la barra de arriba. Tiene que estar aquí
       como está en `index.html`, o en el navegador no se monta y la comprobación de escritorio no
       comprobaría nada. -->
  <div id="marco" class="marco"></div>
  <header class="cabecera">
    <button type="button" class="cabecera-titulo" data-accion="ir-inicio">
      <span aria-hidden="true">🌾</span><span id="cabecera-texto">Mi cuaderno</span>
    </button>
    <div class="cabecera-botones">
      <button type="button" class="boton-letra" data-accion="cambiar-letra">A+</button>
      <button type="button" class="boton-letra" data-accion="salir">Salir</button>
    </div>
  </header>
  <main id="pantalla" class="pantalla" aria-live="polite"></main>
  <p id="pie" class="pie"></p>
  <script>
    // La sesión, puesta a mano: es lo único que hace este fichero.
    window.localStorage.setItem("cuedigital.token", {json.dumps(token)});
    // Y lo que no se encuentre al recorrer la ruta, para poder decirlo al final.
    window.pasosSinEncontrar = [];
  </script>
  <script>
    // Y las pulsaciones, hechas por el navegador como las haría una persona: se espera a que la
    // aplicación arranque y se van pulsando los botones de la ruta. Al final, el navegador vuelca el
    // HTML ya con la pantalla pedida, que es lo que se comprueba.
    //
    // **Un paso también puede ser escribir en un campo**, y hace falta de verdad: hay pantallas que
    // leen lo que el agricultor ha tecleado **por el `id` del campo** (el dictado, por ejemplo), y
    // eso solo se puede comprobar en un navegador de verdad, porque en el DOM de mentira de los
    // tests no hay campos. Se escribe así: `escribir:#dictado-texto=lo que sea`.
    //
    // (Las llaves van dobladas porque esto es una f-string de Python: si no, Python se cree que son
    // sus propias expresiones y el fichero no compila. Ya pasó al escribirlo.)
    window.addEventListener("load", () => {{
      const ruta = {json.dumps(ruta)};
      setTimeout(async () => {{
        for (const paso of ruta) {{
          if (paso.startsWith("escribir:")) {{
            const resto = paso.slice("escribir:".length);
            const corte = resto.indexOf("=");
            const campo = document.querySelector(resto.slice(0, corte));
            if (campo) {{
              campo.value = resto.slice(corte + 1);
              // Y se avisa a la página, como hace el navegador al teclear: si algún día un campo
              // se pinta con React y escucha sus cambios, esto sigue funcionando.
              campo.dispatchEvent(new Event("input", {{ bubbles: true }}));
            }} else {{
              // **Un paso que no encuentra lo que busca tiene que doler.** Si se calla, la
              // comprobación sigue como si nada y acaba dando por bueno **otra pantalla**: pasó
              // con «el plan de abono», que se quedó en «mi cuaderno» y aun así «pasó», porque los
              // textos que se buscaban también estaban allí. Por eso se apunta en el título.
              window.pasosSinEncontrar.push("escribir:" + resto.slice(0, corte));
            }}
          }} else if (paso.startsWith("elegir-ejemplo:")) {{
            // `elegir-ejemplo:#trabajo-tierra`: se elige **la primera opción de verdad** del
            // desplegable (la de después de «sin decir»). Hace falta porque un identificador de la base
            // —el de una tierra— **no se puede escribir en la ruta**: es del servidor y cambia con cada
            // base, así que la ruta dice «la primera tierra» y no un número que un día no existirá.
            const desplegable = document.querySelector(paso.slice("elegir-ejemplo:".length));
            if (desplegable && desplegable.options && desplegable.options.length > 1) {{
              desplegable.value = desplegable.options[1].value;
              // Se avisa a la página como lo haría una persona: sin esto, el valor cambia en la
              // pantalla pero quien lo lea por un escuchador no se entera.
              desplegable.dispatchEvent(new Event("input", {{ bubbles: true }}));
              desplegable.dispatchEvent(new Event("change", {{ bubbles: true }}));
            }} else {{
              window.pasosSinEncontrar.push(paso);
            }}
          }} else {{
            const boton = document.querySelector(paso);
            if (boton) {{
              boton.click();
            }} else {{
              window.pasosSinEncontrar.push(paso);
            }}
          }}
          await new Promise((listo) => setTimeout(listo, 900));
        }}
        // Al final se deja escrito en la página lo que no se encontró, y quien comprueba lo lee.
        var avisos = [];
        // **Y si la pantalla se sale de lo ancho.** Una frase larga, una tabla de tres columnas o unos
        // botones puestos uno al lado del otro que no caben se cortan en el borde **sin dar ningún
        // error**: el agricultor ve menos y nadie se entera. A 390 px, que es el ancho que pide el
        // contrato, es lo que hay que vigilar. Va **antes** del aviso de los pasos para no romper su
        // lector, que se lo queda todo hasta el final.
        var ancho = Math.max(
          document.documentElement.scrollWidth,
          document.body ? document.body.scrollWidth : 0
        );
        var cabe = window.innerWidth;
        // El ancho se dice **siempre**, no solo cuando hay fallo: así el informe enseña con qué ancho
        // se ha medido de verdad. Sin esto, una comprobación que dijera «cabe» midiendo una ventana
        // de 500 px pasaría por buena creyendo que midió 390.
        avisos.push("ANCHO: " + ancho + " en " + cabe);
        if (ancho > cabe + 1) {{
          avisos.push("SE-SALE: " + ancho + " de " + cabe);
        }}
        if (window.pasosSinEncontrar.length > 0) {{
          avisos.push("SIN-ENCONTRAR: " + window.pasosSinEncontrar.join(" | "));
        }}
        if (avisos.length > 0) {{
          document.title = avisos.join(" § ");
        }}
      }}, 2000);
    }});
  </script>
  <script src="/vendor/react.production.min.js"></script>
  <script src="/vendor/react-dom.production.min.js"></script>
  <script src="/vendor/htm.umd.js"></script>
  <script type="module" src="/app.js"></script>
</body>
</html>
"""
    destino = pathlib.Path(__file__).resolve().parents[1] / "web" / "_comprobacion_navegador.html"
    destino.write_text(contenido, encoding="utf-8")
    return destino


def pagina_estrecha(token: str, fragmento: str = "", ancho: int = 390) -> pathlib.Path:
    """Una página que mete **la aplicación de verdad** en un hueco del ancho que se le pida.

    **Por qué un hueco y no una ventana.** Al navegador sin ventana no se le puede pedir un ancho de
    390 px: no baja de 500 (medido, ver `ANCHO_MINIMO_DE_LA_VENTANA`), y tampoco lo baja el factor de
    escala del dispositivo. El recorrido miraba el móvil a 500 px y **los 390 px del contrato no se
    habían medido nunca**. Un hueco sí tiene su propio ancho de verdad, así que las reglas de ancho
    del CSS se aplican como en un teléfono de 390 px.

    **Y sirve para cualquier ancho**, no solo para 390: se usa también para medir a **1024 y 1440 px**
    las pantallas nuevas de T06 y T10, que traen tablas, mapas y formularios y son justo las que
    cambian de forma al pasar de 64 rem. Antes solo se miraban a 390 px —el ancho donde antes se rompe
    todo— pero el contrato pide los tres.

    Se carga `/index.html`, que es la aplicación de verdad —no una copia del armazón como
    `pagina_de_pantalla`—, y se le puede pasar un trozo de dirección (`#/tierras`) para mirar una
    pantalla con datos y no solo la portada. El hueco comparte origen con la página, así que se puede
    leer lo que mide por dentro. El fichero se borra al terminar, como el otro.
    """
    alto = 844 if ancho <= 500 else 900
    contenido = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <!-- El mismo `viewport` que la aplicación: sin él, el hueco se dibujaría como si fuera ancho. -->
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>sin medir</title>
  <style>
    html, body {{ margin: 0; padding: 0; background: #ddd; }}
    /* El ancho que se quiere medir, ni uno más. A 390 px es un teléfono; a 1024 y 1440, la versión
       de ordenador, que entra a partir de 64 rem (1024 px). */
    iframe {{ width: {ancho}px; height: {alto}px; border: 0; display: block; }}
  </style>
  <script>
    // La sesión se pone **antes** de que arranque la aplicación de dentro: el hueco comparte origen,
    // así que ve el mismo almacén del navegador.
    window.localStorage.setItem("cuedigital.token", {json.dumps(token)});
  </script>
</head>
<body>
  <iframe id="el-movil" src="/index.html{fragmento}"></iframe>
  <script>
    (function () {{
      var marco = document.getElementById("el-movil");
      function medir() {{
        var avisos = [];
        try {{
          var dentro = marco.contentDocument;
          var ancho = Math.max(
            dentro.documentElement.scrollWidth,
            dentro.body ? dentro.body.scrollWidth : 0
          );
          var cabe = marco.clientWidth;
          // El ancho se dice **siempre**: así el informe enseña que de verdad se midió en 390 px.
          avisos.push("HUECO: " + ancho + " en " + cabe);
          // **Y en qué dirección ha acabado la aplicación** (05/10/2026). Una dirección que la propia
          // aplicación escribe y que luego no sabe abrir deja al agricultor en **otra** pantalla, y eso no
          // lo ve ninguna otra comprobación: la pantalla «cabe» y está «montada», pero no es la que se
          // pidió. Pasó con `#/trabajos`, que caía al panel de mando porque su clave no estaba en la tabla
          // de puertas de `app.js`; desde aquí se cazó y desde aquí se sigue vigilando.
          avisos.push("DIRECCION: " + dentro.location.hash);
          if (ancho > cabe + 1) {{
            avisos.push("SE-SALE: " + ancho + " de " + cabe);
          }}
          // Y que la pantalla haya montado de verdad, no que se haya quedado en blanco: una página
          // vacía «cabe» siempre, así que sin esto la comprobación de anchura no valdría nada. Se dice
          // **cuánto** ocupa el cuerpo y quien comprueba exige un mínimo.
          avisos.push("CUERPO: " + (dentro.body ? dentro.body.innerHTML.length : -1));
        }} catch (error) {{
          avisos.push("NO-SE-PUDO-MEDIR: " + error);
        }}
        document.title = avisos.join(" § ");
      }}
      // Se espera a que la aplicación de dentro arranque: si se mide antes, se mide una página vacía y
      // «cabe» no querría decir nada.
      marco.addEventListener("load", function () {{ setTimeout(medir, 3000); }});
    }})();
  </script>
</body>
</html>
"""
    destino = pathlib.Path(__file__).resolve().parents[1] / "web" / "_comprobacion_en_un_hueco.html"
    destino.write_text(contenido, encoding="utf-8")
    return destino


def _cuerpo_del_hueco(html: str) -> int | None:
    """Cuánto ocupa el cuerpo de la aplicación dentro del hueco, para saber que no está vacía.

    **Se lee del `<title>`, no de todo el HTML.** Buscar el aviso en el HTML entero fue un fallo real
    de esta misma comprobación: el nombre del aviso aparece también **dentro del `<script>`** que lo
    escribe, así que la búsqueda lo encontraba siempre y la comprobación pasaba dijera lo que dijera
    la página. Es el mismo tropiezo que ya hubo con `SIN-ENCONTRAR`; de ahí que todo se lea del
    título.
    """
    encontrado = re.search(r"CUERPO: (-?\d+)", _titulo(html))
    return int(encontrado.group(1)) if encontrado else None


def _titulo(html: str) -> str:
    """El `<title>` que dejó escrito la página de la comprobación, para poder decirlo al fallar."""
    encontrado = re.search(r"<title>([^<]*)</title>", html)
    return encontrado.group(1) if encontrado else ""


def _ancho_del_hueco(html: str) -> tuple[int, int] | None:
    """Con qué ancho se midió dentro del hueco: `(lo que ocupa la pantalla, lo que mide el hueco)`."""
    encontrado = re.search(r"HUECO: (\d+) en (\d+)", html)
    if not encontrado:
        return None
    return int(encontrado.group(1)), int(encontrado.group(2))


def la_primera_tierra(direccion: str, token: str) -> int | None:
    """El identificador de una tierra de la finca, para poder abrir su ficha por su dirección.

    La ficha de las versiones de una tierra se abre por `#/tierras/<id>/versiones` (T06), así que hace
    falta un identificador de verdad. Se pregunta al servidor en vez de inventarse un número: abrir
    `#/tierras/1/versiones` cuando la tierra 1 no existe comprobaría la pantalla de «esa tierra no
    está», que se dibuja igual de bien y no dice nada de la pantalla que se quiere mirar.
    """
    try:
        with httpx.Client(
            base_url=direccion, timeout=30.0, headers={"Authorization": f"Bearer {token}"}
        ) as cliente:
            tierras = cliente.get("/api/parcelas").json()
    except (httpx.HTTPError, ValueError):
        return None
    if not tierras:
        return None
    return int(tierras[0]["id"])


def el_primer_papel_de_la_bandeja(direccion: str, token: str) -> int | None:
    """El identificador del primer papel de la bandeja, para abrir su ficha por su dirección.

    **Lo pide el T08** (06/10/2026) por el mismo motivo que la ficha de una tierra o de una máquina: su
    dirección lleva el identificador (`#/papeles/bandeja/12`), así que hace falta uno de verdad. Se
    pregunta al servidor en vez de inventarse un número: abrir `#/papeles/bandeja/1` cuando el papel 1 no
    existe comprobaría la pantalla de «ese papel no está en tu bandeja», que se dibuja igual de bien y no
    dice nada de la ficha que se quiere mirar.
    """
    try:
        with httpx.Client(
            base_url=direccion, timeout=30.0, headers={"Authorization": f"Bearer {token}"}
        ) as cliente:
            datos = cliente.get("/api/bandeja").json()
    except (httpx.HTTPError, ValueError):
        return None
    papeles = datos.get("papeles") if isinstance(datos, dict) else None
    if not papeles:
        return None
    return int(papeles[0]["id"])


def la_primera_maquina(direccion: str, token: str) -> int | None:
    """El identificador de una máquina de la finca, para poder abrir su ficha por su dirección.

    **Lo pidió el ticket de la maquinaria (T14, 03/10/2026)** y tiene razón: su ficha se abre por
    `#/maquinaria/<id>`, así que hace falta un identificador de verdad. Se pregunta al servidor en vez de
    inventarse un número, por el mismo motivo que con las tierras: abrir `#/maquinaria/1` cuando la
    máquina 1 no existe comprobaría la pantalla de «esa máquina no está», que se dibuja igual de bien y
    no dice nada de la ficha que se quiere mirar.
    """
    try:
        with httpx.Client(
            base_url=direccion, timeout=30.0, headers={"Authorization": f"Bearer {token}"}
        ) as cliente:
            datos = cliente.get("/api/maquinaria").json()
    except (httpx.HTTPError, ValueError):
        return None
    maquinas = datos.get("maquinas") if isinstance(datos, dict) else None
    if not maquinas:
        return None
    return int(maquinas[0]["id"])


# Un PNG de verdad, de un píxel: es lo que se sube a la bandeja (T08) para que la pantalla tenga un
# papel dentro. Se escribe aquí, en bytes, porque hace falta un fichero que el servidor acepte —y que
# sea una imagen de verdad, que es lo que sube el agricultor con la cámara— y no un texto disfrazado.
UN_PNG_DE_UN_PIXEL = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15ca89"
    "0000000a49444154789c6360000002000154a24f5f0000000049454e44ae426082"
)

# El extracto de ejemplo del proyecto: el mismo fichero que usan las pruebas del ticket del banco. Se
# usa tal cual —y no se escribe aquí otro— para que lo que se comprueba en el navegador sea **lo mismo**
# que lo que ya está probado en el servidor: si el fichero de ejemplo cambiara, esta comprobación lo nota.
RUTA_DEL_EXTRACTO_DE_EJEMPLO = (
    pathlib.Path(__file__).resolve().parent.parent / "tests" / "datos" / "extracto_de_ejemplo_cuenta_principal.csv"
)


def siembra_datos(direccion: str, token: str) -> list[str]:
    """Deja una finca con datos de verdad: una tierra, su cultivo, un producto, un tratamiento y un análisis.

    **Hace falta.** Sin datos, las pantallas se comprueban **vacías**, y una pantalla vacía se ve
    bien aunque la lista esté rota: lo que hay que ver es una lista con cosas dentro. Es la misma
    lección de siempre en este proyecto («una lista que no enseña nada pasa cualquier prueba»).
    """
    cabeceras = {"Authorization": f"Bearer {token}"}
    creado: list[str] = []
    with httpx.Client(base_url=direccion, timeout=30.0, headers=cabeceras) as cliente:
        campana = cliente.get("/api/campanas/actual").json()
        parcela = cliente.post(
            "/api/parcelas",
            json={
                "alias": "El Prado",
                "ref_sigpac": "37-70-0-0-503-51",
                "municipio": "Calvarrasa de Arriba",
                "provincia": "Salamanca",
                "codigo_ine": "37070",
                "poligono": 503,
                "numero_parcela": 51,
                "numero_recinto": 1,
                "superficie_ha": 4.9,
                "uso_sigpac": "TA",
                "sistema": "secano",
            },
        )
        if parcela.status_code == 201:
            creado.append("una tierra")
            # **Una segunda tierra**, para que el buscador de tierras tenga entre qué elegir (ronda 82): con
            # una sola tierra, buscar «suertes» no demuestra nada, porque la lista ya tenía una.
            cliente.post(
                "/api/parcelas",
                json={
                    "alias": "Las Suertes de Arriba",
                    "ref_sigpac": "37-70-0-0-112-4-2",
                    "municipio": "Peñaranda de Bracamonte",
                    "provincia": "Salamanca",
                    "codigo_ine": "37246",
                    "poligono": 112,
                    "numero_parcela": 4,
                    "numero_recinto": 2,
                    "superficie_ha": 3.2,
                    "uso_sigpac": "TA",
                    "sistema": "secano",
                },
            )
            creado.append("otra tierra")
            cliente.post(
                f"/api/parcelas/{parcela.json()['id']}/cultivos",
                # **Con su fecha de siembra** (05/10/2026): la historia de una tierra enseña «desde cuándo»
            # con esta fecha, y sin ella la pantalla dice «Sin decir» —que es lo correcto, y por eso
            # mismo no comprobaría nada—. Con fecha se comprueba en un navegador de verdad que el dato
            # llega hasta la pantalla.
            json={
                "campana_id": campana["id"],
                "especie": "TRIGO BLANDO",
                "sistema": "secano",
                "fecha_inicio": "2025-11-10",
            },
            )
            creado.append("su cultivo")
            # Un análisis de tierra con sus números: la pantalla «los análisis» ya está en React y
            # sin un boletín dentro no se vería nada de lo que hay que ver (los números y el papel).
            analisis = cliente.post(
                "/api/analiticas",
                json={
                    "campana_id": campana["id"],
                    "tipo": "suelo",
                    "fecha_toma_muestra": "2026-02-14",
                    "fecha_resultado": "2026-02-20",
                    "parcela_id": parcela.json()["id"],
                    "laboratorio": "Laboratorio Agrario de Villamuriel",
                    "numero_informe": "B-2026-77",
                    "parametros": [
                        {"clave": "materia_organica", "valor": "1,80"},
                        {"clave": "ph", "valor": "7,4"},
                    ],
                },
            )
            if analisis.status_code == 201:
                creado.append("un análisis")
            # Un plan de abono del año. Hace falta de verdad para poder ver la pantalla del plan:
            # **con la finca sin planes, «mi cuaderno» enseña el botón de hacerlo, no el de verlo**,
            # y una ruta que buscara «ver el plan» no encontraría nada (eso pasó, y por eso ahora un
            # paso que no encuentra su botón hace fallar la comprobación).
            plan = cliente.post(
                "/api/planes",
                json={
                    "campana_id": campana["id"],
                    "parcela_id": parcela.json()["id"],
                    "cultivo": "TRIGO BLANDO",
                    "superficie_ha": 4.9,
                    "necesidad_n": 100.0,
                    "necesidad_p": 40.0,
                    "herramienta": True,
                    "analitica_id": analisis.json()["id"] if analisis.status_code == 201 else None,
                },
            )
            if plan.status_code == 201:
                creado.append("un plan de abono")
            # Una venta. Es lo que hace falta para ver **el bloque «lo que he vendido» con su número**
            # («1 venta apuntada · 42.000 kg», ronda 81): sin ninguna venta, ese bloque enseña su frase de
            # «todavía no has apuntado ninguna venta» y la línea del número no se dibuja.
            venta = cliente.post(
                "/api/ventas",
                json={
                    "campana_id": campana["id"],
                    "tipo": "comercializada",
                    "fecha": "2026-07-10",
                    "producto": "Trigo blando",
                    "cantidad": 42000.0,
                    "unidad": "kg",
                    "lote": "L-2026-07",
                    "comprador": "Cooperativa Agrícola de Peñaranda",
                    "numero_albaran": "ALB-2026-118",
                    "parcela_id": parcela.json()["id"],
                },
            )
            if venta.status_code == 201:
                creado.append("una venta")
        # Las medidas preventivas declaradas (ronda 93). Hacen falta para que la pantalla de las medidas
        # enseñe lo que solo sale **cuando ya hay declaración**: el botón de quitarla. Se declaran con
        # **`PUT`**, que es el único método que acepta esa ruta (con `POST` contesta 405, y ese fue el
        # fallo que se encontró al probar la aplicación contra un servidor de verdad).
        medidas = cliente.put(
            "/api/medidas",
            json={"aplicadas": ["rotacion", "higiene"], "observaciones": {}},
        )
        if medidas.status_code == 200:
            creado.append("las medidas declaradas")
        producto = cliente.post(
            "/api/productos",
            json={
                "nombre_comercial": "Glifosato 36 SL",
                "numero_registro": "ES-00849",
                "unidad_dosis": "L/ha",
                "unidad_compra": "L",
            },
        )
        if producto.status_code == 201:
            creado.append("un producto")
            # **Un envase con existencias dentro** (ronda 9, recorrido 4). Hace falta para poder
            # recorrer la mitad del recorrido que habla de **insumos y existencias**: marcar un trabajo
            # hecho diciendo de qué envase salió el producto no se puede ni pulsar si no hay ningún
            # envase, y el desplegable de insumos sale vacío —que es correcto y no comprueba nada—.
            # Se mete mercancía por las **dos puertas que existen**: el artículo, su lote y una entrada
            # apuntada a mano con su motivo (que es como se apunta lo que ya estaba en la nave antes de
            # empezar a llevar el cuaderno con el programa).
            articulo = cliente.post(
                "/api/almacen/articulos",
                json={
                    "nombre": "Glifosato 36 SL",
                    "categoria": "fitosanitario",
                    "unidad": "L",
                    "producto_id": producto.json()["id"],
                },
            )
            lote = cliente.post(
                "/api/almacen/lotes",
                json={
                    "articulo_id": articulo.json()["id"],
                    "numero_lote": "ENV-2026-07",
                    "presentacion": "garrafa de 20 L",
                    "contenido_por_envase": 20.0,
                    "ubicacion": "La nave",
                },
            )
            entrada = cliente.post(
                "/api/almacen/movimientos",
                json={
                    "tipo": "entrada",
                    "lote_id": lote.json()["id"],
                    "cantidad": 40.0,
                    "unidad": "L",
                    "fecha": "2026-03-16",
                    "motivo": "Lo que ya estaba en la nave cuando empecé a llevar el cuaderno aquí",
                },
            )
            if articulo.status_code == 201 and lote.status_code == 201 and entrada.status_code == 201:
                creado.append("un envase con existencias")
            # **Una factura de verdad** (ronda 93). Hace falta desde que la ficha de una factura ofrece
            # BORRAR: con la lista vacía, esa pantalla enseña «todavía no has subido ninguna» y el botón
            # que hay que pulsar **no existe**, así que la ruta no comprobaría nada (una lista vacía pasa
            # cualquier prueba). Se manda el `datos` como formulario porque en la misma petición viaja el
            # fichero, y aquí no se manda ninguno: una factura sin papel es el caso más común.
            factura = cliente.post(
                "/api/facturas",
                data={
                    "datos": json.dumps(
                        {
                            "fecha": "2026-03-15",
                            "proveedor": "Cooperativa Agrícola de Peñaranda",
                            "proveedor_nif": "F37012345",
                            "numero_factura": "2026/00123",
                            "base_imponible": 620.0,
                            "cuota_iva": 130.2,
                            "tipo_iva_pct": 21.0,
                            "total": 750.2,
                            "lineas": [
                                {
                                    "descripcion": "GLIFOSATO 36% SL 20 L",
                                    "cantidad": 40,
                                    "unidad": "L",
                                    "precio_unitario": 4.25,
                                    "importe": 170.0,
                                    "producto_id": producto.json()["id"],
                                }
                            ],
                        }
                    )
                },
            )
            if factura.status_code == 201:
                creado.append("una factura")
        # **Una máquina con su ITV vencida** (T14, 03/10/2026). Hace falta por el mismo motivo que las
        # demás: sin ninguna máquina, la lista se comprueba **vacía**, y una lista vacía se ve bien aunque
        # esté rota —además, el botón VER de una fila no existiría y la ruta de la ficha no tendría a
        # dónde ir—. Y con una ITV **vencida** se ve lo que solo sale cuando hay una fecha pasada: la
        # palabra «Vencida» en su columna, que es la que informa sin depender del color.
        #
        # **Aquí no se declara ninguna obligación de más**: se declara la ITV como aplicable (que es lo
        # que hace el agricultor) y se apunta su inspección con la fecha que traía el papel. Las otras
        # cuatro obligaciones se quedan como nacen, en «no lo sé»: si algún día alguien las diera por
        # buenas sin que nadie las declare, esta pantalla lo enseñaría.
        maquina = cliente.post(
            "/api/maquinaria",
            json={
                "nombre": "El tractor",
                "clase": "tractor",
                "propiedad": "propia",
                "disponibilidad": "disponible",
                "matricula": "1234 ABC",
                "numero_roma": "ROMA-2026-1123",
                "horas": 4200,
            },
        )
        if maquina.status_code == 201:
            creado.append("una máquina")
            cliente.put(
                f"/api/maquinaria/{maquina.json()['id']}/obligaciones/itv",
                json={"aplicabilidad": "si", "origen": "documento"},
            )
            cliente.post(
                f"/api/maquinaria/{maquina.json()['id']}/inspecciones",
                json={
                    "tipo": "itv",
                    "fecha": "2025-03-12",
                    "resultado": "favorable",
                    "proxima_fecha": "2026-03-12",
                },
            )
            creado.append("su ITV vencida")
        # **Un gasto de verdad** (T13, 05/10/2026). Hace falta por el mismo motivo que todo lo de arriba:
        # sin ningún gasto, la lista de cuentas se comprueba **vacía**, y una lista vacía se ve bien aunque
        # esté rota. Se apunta **a la tierra** y con su importe —y no suelto— porque es lo que hace que la
        # historia de esa tierra enseñe lo que consta que ha costado con un número dentro (recorrido 5) en
        # vez de su frase de «de esta tierra no hay ningún gasto apuntado».
        gasto = cliente.post(
            "/api/gastos",
            json={
                "campana_id": campana["id"],
                "fecha": "2026-04-12",
                "concepto": "Gasóleo para el tractor",
                "categoria": "gasoleo",
                "proveedor": "Cooperativa Agrícola de Peñaranda",
                "parcela_id": parcela.json()["id"],
                # **Los importes van como texto decimal**, que es la regla del dinero en este programa:
                # un número de JSON es una coma flotante y ya ha perdido céntimos antes de entrar, así
                # que el servidor lo rechaza (igual que en las ventas, los cobros y los pagos).
                "base_imponible": "210.00",
                "cuota_iva": "44.10",
                "importe": "254.10",
            },
        )
        if gasto.status_code == 201:
            creado.append("un gasto")
        # **Un gasto que cuadra con una línea del extracto** (06/10/2026). Se apunta con el importe y el
        # día de la línea «REPARACION DEL REMOLQUE TALLER EJEMPLO» del fichero de ejemplo que importa el
        # propio guion.
        #
        # **Y no es eso lo que hace que la conciliación tenga propuesta, aunque lo parezca**: un gasto no
        # es una de las tres clases que se pueden conciliar (`extractos.CLASES_QUE_FALTAN` dice cuáles
        # faltan), así que la propuesta del movimiento la da **la factura de compra** que también deja el
        # guion. Este gasto está aquí por lo contrario: para poder comprobar que **no** se ofrece, que es
        # la mitad del «pendientes sin duplicar» del recorrido 3 (ver `NO_PUEDE_SALIR`). Si algún día se
        # conciliaran los gastos, esa comprobación fallará, y tendrá que fallar: hay que decidir entonces
        # si el mismo dinero cuenta dos veces.
        reparacion = cliente.post(
            "/api/gastos",
            json={
                "campana_id": campana["id"],
                "fecha": "2026-06-20",
                "concepto": "La reparación del remolque",
                "categoria": "reparacion",
                "proveedor": "Taller Ejemplo",
                "importe": "210.00",
            },
        )
        if reparacion.status_code == 201:
            creado.append("un gasto que cuadra con el banco")
        # **Un trabajo pensado y otro hecho** (T15, 05/10/2026). Los dos, porque la pantalla de los trabajos
        # tiene **dos listas** y con una sola no se comprobaría la mitad que falta. El hecho es, además, lo
        # que hace que la historia de la tierra tenga algo que contar y que su última labor salga dicha.
        #
        # **Sin insumos, y es una decisión**: lo que se gasta del almacén se apunta saliendo de un envase, y
        # aquí no hay ninguno dado de alta (el guion deja un producto, que no es un envase); un trabajo a
        # mano que no gastó nada del almacén es un caso de verdad y no un hueco.
        if parcela.status_code == 201:
            pensado = cliente.post(
                "/api/trabajos/previstos",
                json={
                    "campana_id": campana["id"],
                    "tipo": "laboreo",
                    "subtipo": "cultivador",
                    "fecha_prevista": "2026-09-20",
                    "parcela_id": parcela.json()["id"],
                    "superficie_ha": 4.9,
                    "horas": 3.0,
                    "observaciones": "Pensado para después de la cosecha",
                },
            )
            if pensado.status_code == 201:
                creado.append("un trabajo pensado")
            hecho = cliente.post(
                "/api/trabajos",
                json={
                    "campana_id": campana["id"],
                    "tipo": "laboreo",
                    "subtipo": "cultivador",
                    # **Antes del tratamiento, y no es un detalle**: el cuaderno ordena los apuntes por su
                    # fecha (el último arriba) y las rutas de «corregir un apunte» y «borrar un apunte» del
                    # guion pulsan **el primero de la lista**, que llevan años comprobando un tratamiento
                    # (sus textos y sus datos). Con el trabajo el 14 de abril, el primero pasaba a ser el
                    # trabajo y esas dos comprobaciones dejaban de mirar lo que dicen mirar. El 18 de marzo
                    # lo deja detrás y las dos siguen comprobando un tratamiento, que es lo que quieren.
                    "fecha": "2026-03-18",
                    "parcela_id": parcela.json()["id"],
                    "superficie_ha": 4.9,
                    "horas": 2.5,
                    "observaciones": "Pasé el cultivador",
                },
            )
            if hecho.status_code == 201:
                creado.append("un trabajo hecho")
        # **Una cuenta y su extracto** (T20, 05/10/2026). Primero la cuenta —un extracto sin cuenta no se
        # puede subir, y el propio programa lo dice— y después el extracto, que es **el fichero de ejemplo
        # del proyecto**, el mismo que usan las pruebas del ticket: seis movimientos y una anotación **sin
        # importe**, que es justo lo que hace que la pantalla tenga que decir un hueco en vez de un cero.
        cuenta = cliente.post(
            "/api/bancos/cuentas",
            json={
                "nombre": "La cuenta del banco",
                "banco": "Banco del Páramo",
                "ultimos_digitos": "5555",
            },
        )
        if cuenta.status_code == 201:
            creado.append("una cuenta del banco")
            with open(RUTA_DEL_EXTRACTO_DE_EJEMPLO, "rb") as el_fichero:
                extracto = cliente.post(
                    "/api/bancos/extractos/importar",
                    data={"cuenta_id": str(cuenta.json()["id"])},
                    files={"fichero": ("extracto.csv", el_fichero, "text/csv")},
                )
            # **200 y no 201, y esto costó una vuelta**: la ruta de importar devuelve `200 OK` con el
            # resultado de la importación (no crea *un* recurso: apunta los movimientos de un fichero),
            # así que exigir 201 hacía que la comprobación dijera que no se había dejado el extracto
            # cuando sí estaba —y las pantallas del banco lo enseñaban con sus movimientos dentro—.
            if extracto.status_code in (200, 201):
                creado.append("su extracto importado")
        # **Un papel en la bandeja** (T08, 06/10/2026). La bandeja es la pantalla nueva y, sin ningún papel
        # dentro, se comprobaría **vacía** —y una lista vacía se ve bien aunque esté rota—. Se sube una
        # imagen de verdad por las **dos puertas del recorrido 1**, en su orden: primero se comprueba que
        # ese fichero no estaba (que es lo que el agricultor hace sin darse cuenta al elegirlo) y después se
        # sube con su tipo y su título. Con un papel «recién subido» la pantalla enseña lo que tiene que
        # enseñar: que está sin revisar y qué falta por decir.
        el_papel = ("el-ticket-del-gasoleo.png", UN_PNG_DE_UN_PIXEL, "image/png")
        comprobado = cliente.post("/api/bandeja/comprobar", files={"fichero": el_papel})
        if comprobado.status_code == 200 and not comprobado.json().get("ya_estaba"):
            subido = cliente.post(
                "/api/bandeja/subir",
                data={
                    "tipo": "ticket",
                    "titulo": "El ticket del gasóleo",
                    # **Con fecha anterior al contrato que guarda el guion después** (01/03/2026), y no es un
                    # detalle: la lista de papeles va de la fecha más nueva a la más vieja, y la ruta de
                    # «corregir un papel» pulsa el CORREGIR **del primero**, que es el contrato que la ruta de
                    # arriba acaba de guardar. Con el ticket el 8 de abril el primero pasaba a ser el ticket y
                    # esa comprobación dejaba de mirar lo que dice mirar.
                    "fecha": "2026-02-20",
                    "quien": "Gasolinera de Peñaranda",
                },
                files={"fichero": el_papel},
            )
            if subido.status_code == 201:
                creado.append("un papel en la bandeja")
        if parcela.status_code == 201:
            tratamiento = cliente.post(
                "/api/tratamientos",
                json={
                    "campana_id": campana["id"],
                    "fecha": "2026-04-10",
                    "parcela_id": parcela.json()["id"],
                    "superficie_tratada_ha": 4.9,
                    "justificacion": "Vi la hierba en el campo",
                    "plaga": "Hierbas adventicias",
                    "producto_id": producto.json()["id"],
                    "dosis": 3,
                },
            )
            if tratamiento.status_code == 201:
                creado.append("un tratamiento")
    return creado


def abre(el_navegador: str, url: str, perfil: pathlib.Path, segundos: int = 6, ventana: str = "") -> str:
    """Abre una página sin ventana y devuelve el HTML **ya ejecutado el JavaScript**.

    `ventana` es el tamaño («1440,900»): hace falta para comprobar **la versión de ordenador**, porque el
    armazón (el menú lateral y la barra de arriba) solo se enseña a partir de 64 rem y el CSS decide con el
    ancho de la ventana. Sin esto, la comprobación de escritorio miraría una pantalla de móvil.

    Ojo: el número de `ventana` **no es el ancho que se mide**. Ver `ventana_para`.
    """
    orden = [
        el_navegador,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={perfil}",
    ]
    if ventana:
        orden.append(f"--window-size={ventana}")
    orden += [
        f"--virtual-time-budget={segundos * 1000}",
        "--dump-dom",
        url,
    ]
    resultado = subprocess.run(orden, capture_output=True, text=True, encoding="utf-8", timeout=120)
    return resultado.stdout or ""


def _pasos_sin_encontrar(html: str) -> list[str]:
    """Los pasos de la ruta que no encontraron lo que buscaban.

    La página de la comprobación lo deja escrito en su `<title>` (ver `pagina_de_pantalla`). Se lee
    del HTML que vuelca el navegador: si un paso no encontró su botón o su campo, aquí sale, y quien
    comprueba lo dice y falla. Sin esto, un selector equivocado deja la comprobación en la pantalla
    anterior y la da por buena.
    """
    encontrado = re.search(r"<title>[^<]*SIN-ENCONTRAR: ([^<]*)", html)
    if not encontrado:
        return []
    return [paso.strip() for paso in encontrado.group(1).split("|") if paso.strip()]


def _ancho_medido(html: str) -> tuple[int, int] | None:
    """Con qué ancho se midió de verdad: `(lo que ocupa la página, lo que cabe en la ventana)`.

    Es lo que hace que la comprobación de un ancho valga algo: sin esto, el navegador podría estar
    midiendo otro ancho y la comprobación diría que todo cabe.
    """
    encontrado = re.search(r"ANCHO: (\d+) en (\d+)", html)
    if not encontrado:
        return None
    return int(encontrado.group(1)), int(encontrado.group(2))


# --------------------------------------------------------------------------
# El ancho que se pide no es el ancho que se mide
# --------------------------------------------------------------------------
#
# **Medido el 03/10/2026, y cambia lo que estas comprobaciones valían.** Al navegador sin ventana se
# le pide un tamaño con `--window-size`, y ese número **no es** el ancho de la página: la ventana se
# lleva 16 px de marco, así que pedir 1024 daba **1008** y pedir 1440 daba **1424**. O sea que la
# comprobación que decía «el ancho mínimo del ordenador (1024 px)» estaba midiendo 1008, que son 16
# px **por debajo** del corte de 64 rem (1024 px): justo por el lado del móvil. Se descubrió al
# apuntar en el `<title>` el ancho de verdad para comprobar los 390 px.
#
# Lo que sí funciona: pedir el ancho deseado **más el marco**. Medido: 1040 → 1024 y 1456 → 1440.
#
# Y lo que no se puede alcanzar: **por debajo de 500 px, el navegador no baja** (pedirle 390 da 500;
# el factor de escala del dispositivo tampoco lo baja). Para medir los 390 px del contrato hay un
# hueco de verdad, ver `pagina_estrecha`.
MARCO_DEL_NAVEGADOR = 16

# El ancho más pequeño que el navegador sin ventana acepta. Por debajo de esto hay que usar un hueco.
ANCHO_MINIMO_DE_LA_VENTANA = 500


def ventana_para(ancho_css: int, alto: int = 900) -> str:
    """El tamaño de ventana que hay que pedir para medir `ancho_css` píxeles **de verdad**."""
    if ancho_css < ANCHO_MINIMO_DE_LA_VENTANA:
        raise ValueError(
            f"el navegador no baja de {ANCHO_MINIMO_DE_LA_VENTANA} px de ventana: "
            f"para {ancho_css} px hay que usar un hueco (`pagina_estrecha`)"
        )
    return f"{ancho_css + MARCO_DEL_NAVEGADOR},{alto}"


def _la_direccion_medida(html: str) -> str:
    """En qué dirección ha acabado la aplicación dentro del hueco (`#/trabajos?campana=2026`).

    El `&` de la consulta llega escapado en el volcado del navegador (`&amp;`): se desescapa aquí, que
    si no la comparación fallaría por un motivo que no es de la pantalla.
    """
    trozo = re.search(r"DIRECCION: ([^§]*)", html)
    return trozo.group(1).strip().replace("&amp;", "&") if trozo else ""


def _la_pantalla_se_sale(html: str) -> str:
    """Cuánto se sale la pantalla de lo ancho, o vacío si cabe.

    Devuelve el texto tal cual («412 de 390») para poder decirlo en el mensaje del fallo: un número
    dice si es un píxel de nada o una columna entera de más, y eso es lo que decide si hay que tocar
    el CSS o el texto de un botón.
    """
    encontrado = re.search(r"SE-SALE: (\d+ de \d+)", html)
    return encontrado.group(1) if encontrado else ""


def _formulario_vacio(html: str) -> bool:
    """¿El hueco del formulario se ha quedado vacío?

    El asistente es una pantalla de React, y dentro lleva el hueco `#formulario` con **el formulario del
    paso dentro**. Si el paso no se puede montar (un fichero de `web/react/` que no ha llegado, la caché
    de un móvil a medias tras un despliegue), el hueco se queda tal y como lo pinta el componente:
    `<div id="formulario"></div>`. Eso es exactamente lo que se busca aquí.

    Se mira el hueco **vacío** y no el contenido, porque lo que hay dentro es HTML anidado (el resumen
    lleva `<div>` dentro) y cortarlo por el primer `</div>` daría una respuesta falsa.
    """
    return bool(re.search(r'<div id="formulario">\s*</div>', html))


def captura(
    el_navegador: str,
    url: str,
    perfil: pathlib.Path,
    destino: pathlib.Path,
    ventana: str = "500,1400",
) -> bool:
    # **El mismo presupuesto de tiempo que la comprobación** (`--virtual-time-budget`), y no menos.
    # Estaba en 8000 y una pantalla cuya ruta lleva ocho pasos (escribir en seis campos y guardar)
    # tarda más: la captura salía **a mitad de camino**, con el formulario relleno y sin guardar, que
    # es justo lo contrario de lo que se quiere mirar. Se vio en la captura de «guardar un papel».
    #
    # `ventana` es el tamaño: por defecto el de un móvil (`500,1400`), y `1440,900` para mirar cómo queda
    # la versión de ordenador (30/09/2026).
    orden = [
        el_navegador,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        f"--user-data-dir={perfil}",
        f"--window-size={ventana}",
        "--virtual-time-budget=14000",
        f"--screenshot={destino}",
        url,
    ]
    subprocess.run(orden, capture_output=True, text=True, timeout=120)
    return destino.exists() and destino.stat().st_size > 0


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Comprueba la interfaz en un navegador de verdad.")
    parser.add_argument("direccion", nargs="?", default=DIRECCION_POR_DEFECTO)
    argumentos = parser.parse_args()
    direccion = argumentos.direccion

    el_navegador = navegador()
    if not el_navegador:
        print("No hay ningún navegador instalado en este ordenador: no se puede comprobar así.")
        print("No es un fallo del programa: es una comprobación que aquí no se puede hacer.")
        return 0
    print(f"Comprobando la interfaz en {el_navegador}\n")

    with tempfile.TemporaryDirectory(prefix="cuedigital-navegador-") as temporal:
        perfil = pathlib.Path(temporal)

        print("1. La pantalla de entrar")
        html = abre(el_navegador, f"{direccion}/", perfil)
        comprobar("id=\"pantalla\"" in html, "la página carga y tiene su contenedor")
        comprobar("Entrar" in html or "entrar" in html, "se ve la pantalla de entrar")
        # **La puerta, con sus campos.** Desde la ronda 55 esta pantalla la dibuja React, y lo que no
        # se puede permitir es que se dibuje sin los campos: el agricultor escribiría su correo y su
        # clave y no habría dónde. En el DOM de mentira de los tests esto no se puede comprobar.
        comprobar('id="correo"' in html, "está el campo del correo")
        comprobar('id="clave"' in html, "está el campo de la clave")
        comprobar('data-accion="entrar"' in html, "está el botón de entrar")

        try:
            token = crear_cuenta(direccion)
        except httpx.HTTPError as error:
            comprobar(False, f"no se ha podido crear la cuenta de prueba: {error}")
            print("\nRESULTADO: no se ha podido comprobar (¿está el servidor en marcha?)")
            return 1
        print("\n2. Una finca con datos, para que las pantallas no se comprueben vacías")
        datos = siembra_datos(direccion, token)
        comprobar(
            datos == [
                "una tierra",
                # La segunda tierra se añadió en la ronda 82 para que el buscador de tierras se pueda
                # comprobar de verdad: escribir unas letras y que la lista se quede con la que casa.
                "otra tierra",
                "su cultivo",
                "un análisis",
                "un plan de abono",
                # La venta se añadió en la ronda 81 para que el bloque «lo que he vendido» de «mi cuaderno»
                # se compruebe **con su número** («1 venta apuntada · 42.000 kg») y no con su frase de
                # «todavía no has apuntado ninguna».
                "una venta",
                # Las medidas declaradas (ronda 93): sin ellas, la pantalla de las medidas no enseña el
                # botón de quitarlas y esa parte no se comprobaría en un navegador de verdad. Se declaran
                # **antes** del producto porque se declaran dentro del bloque de la finca.
                "las medidas declaradas",
                "un producto",
                # Y su envase con existencias dentro (ronda 9): sin él, el recorrido 4 no puede decir de
                # qué se gastó el producto, y el desplegable de insumos sale vacío.
                "un envase con existencias",
                # La factura se añadió en la ronda 93 para que el borrado de una factura se pueda
                # comprobar de verdad: con la lista vacía, el botón BORRAR de una factura no existe.
                "una factura",
                # La máquina con su ITV vencida (T14, 03/10/2026): sin ella, la lista de maquinaria se
                # comprobaría vacía y la palabra «Vencida» —que es la que informa sin depender del
                # color— no saldría nunca. Va detrás de la factura porque es donde se da de alta.
                "una máquina",
                "su ITV vencida",
                # El gasto, el trabajo pensado, el trabajo hecho, la cuenta y su extracto (T13, T15 y T20,
                # 05/10/2026): son los datos que hacen que las cuatro pantallas nuevas se comprueben **con
                # cosas dentro**. Van aquí, en este orden, porque es el orden en el que se dan de alta.
                "un gasto",
                # Y el que cuadra con una línea del extracto, para poder recorrer la conciliación.
                "un gasto que cuadra con el banco",
                "un trabajo pensado",
                "un trabajo hecho",
                "una cuenta del banco",
                "su extracto importado",
                # Y el papel de la bandeja (T08, 06/10/2026): es lo que hace que la bandeja se compruebe
                # con algo dentro y que su ficha tenga un original que enseñar.
                "un papel en la bandeja",
                "un tratamiento",
            ],
            f"se ha dejado: {', '.join(datos)}",
        )

        print("\n3. Todas las pantallas ya migradas a React, en el navegador")
        for nombre, ruta, esperadas in PANTALLAS:
            pagina = pagina_de_pantalla(token, direccion, ruta)
            try:
                # **El presupuesto de tiempo es el de la ruta más larga**, no el de la primera. La página
                # espera 2 s a que arranque la aplicación y luego 900 ms por cada paso, así que la ruta
                # del asistente hasta el resumen (doce pasos, con un campo escrito por el camino) se come
                # casi todo lo que había. Estaba en 14 s y la ruta llegaba justa: si se añade un paso más,
                # el volcado se tomaría **a mitad de camino** y la comprobación diría que falta algo que
                # sí está. Es tiempo **virtual** del navegador, así que subirlo no cuesta tiempo real.
                html = abre(el_navegador, f"{direccion}/{pagina.name}", perfil, segundos=18)
                falta = [texto for texto in esperadas if texto not in html]
                comprobar(falta == [], f"{nombre}: se dibuja ({', '.join(falta) if falta else 'todo lo que tiene que salir'})")
                comprobar(
                    "no se ha podido abrir" not in html,
                    f"{nombre}: sin el aviso de emergencia de React",
                )
                sobran = [texto for texto in NO_PUEDE_SALIR.get(nombre, []) if texto in html]
                comprobar(sobran == [], f"{nombre}: no sale lo que no toca ({', '.join(sobran)})")
                # **Y todos los pasos de la ruta tienen que haber encontrado lo que buscaban.** Sin
                # esto, un selector que no existe no se pulsa, la comprobación se queda en la
                # pantalla anterior y **da por buena una pantalla que no es**: pasó con «el plan de
                # abono», que se quedó en «mi cuaderno» y aun así pasó, porque los textos que se
                # buscaban estaban en las dos.
                perdidos = _pasos_sin_encontrar(html)
                comprobar(
                    perdidos == [],
                    f"{nombre}: los pasos de la ruta encuentran lo que buscan"
                    + (f" (no se encontró: {', '.join(perdidos)})" if perdidos else ""),
                )
                # Y, en los pasos del asistente, que React **haya llenado el hueco**: si no, la pregunta
                # sale sin nada que contestar (ver `_formulario_vacio`).
                if nombre in FORMULARIO_CON_PIEZA:
                    comprobar(
                        not _formulario_vacio(html),
                        f"{nombre}: React ha llenado el hueco del formulario "
                        f"({FORMULARIO_CON_PIEZA[nombre]})",
                    )
            finally:
                pagina.unlink(missing_ok=True)

        print("\n4. La versión de ordenador: el armazón (menú lateral y barra de arriba)")
        # **Esto es lo que pidió David** (30/09/2026): *«debe ser responsive para usarse en pc y móvil, no
        # solo móvil… no es una app usable de gestión»*. Se abre la aplicación **con una ventana de
        # ordenador** (1440x900) y se comprueba que está el armazón: el menú con sus módulos y la barra con
        # el año, la cuenta y el botón de apuntar. Sin ventana ancha no tendría sentido: el armazón solo se
        # enseña a partir de 64 rem, y eso lo decide el CSS con el ancho de verdad.
        for nombre, ruta, esperadas in ESCRITORIO:
            pagina = pagina_de_pantalla(token, direccion, ruta)
            try:
                html = abre(
                    el_navegador,
                    f"{direccion}/{pagina.name}",
                    perfil,
                    segundos=20,
                    ventana=ventana_para(1440, 900),
                )
                falta = [texto for texto in esperadas if texto not in html]
                comprobar(
                    falta == [],
                    f"escritorio · {nombre}: se dibuja el armazón "
                    f"({', '.join(falta) if falta else 'el menú y la barra, con todo lo que tienen que enseñar'})",
                )
                comprobar(
                    "no se ha podido abrir" not in html,
                    f"escritorio · {nombre}: sin el aviso de emergencia de React",
                )
                perdidos = _pasos_sin_encontrar(html)
                comprobar(
                    perdidos == [],
                    f"escritorio · {nombre}: los pasos de la ruta encuentran lo que buscan"
                    + (f" (no se encontró: {', '.join(perdidos)})" if perdidos else ""),
                )
                # Y el armazón se pinta **de verdad**: si React no hubiera montado el marco, el contenedor
                # seguiría vacío y no habría ni un renglón de menú.
                comprobar(
                    'id="menu-cuaderno"' in html and 'class="barra"' in html,
                    f"escritorio · {nombre}: React ha montado el armazón en su contenedor",
                )
            finally:
                pagina.unlink(missing_ok=True)

        print("\n4 bis. El ancho mínimo del ordenador (1024 px) y el zoom al 200 %")
        # **Esto se miraba a mano, y por eso se rompía sin que nadie se enterara** (02/10/2026). La versión
        # de ordenador entra a partir de **64 rem, que son exactamente 1024 px**: es el ancho en el que la
        # disposición se rompe antes, porque es el primero en el que se enseña el armazón con la tabla al
        # lado y no hay ni un píxel de sobra. Hasta ahora el recorrido automático miraba el móvil (500 px) y
        # 1440 px, y 1024 px solo se había mirado en capturas a mano.
        #
        # Y el **zoom del 200 %**: el navegador, al ampliar, reduce los píxeles CSS que le caben, así que
        # una ventana de 1440 px con zoom al 200 % ve la página **como si midiera 720 px**. Por eso se
        # comprueba a 720 px: ahí la versión de ordenador **no** puede salir (está por debajo de 64 rem) y
        # la del móvil tiene que dibujarse entera. No es el zoom de verdad —eso solo lo prueba un navegador
        # con la ampliación puesta—, pero sí es el ancho al que equivale, y es lo que se puede automatizar
        # aquí sin mentir en el informe.
        for nombre, ruta, esperadas in ESCRITORIO[:2]:
            pagina = pagina_de_pantalla(token, direccion, ruta)
            try:
                url = f"{direccion}/{pagina.name}"
                html = abre(el_navegador, url, perfil, segundos=20, ventana=ventana_para(1024, 768))
                falta = [texto for texto in esperadas if texto not in html]
                comprobar(
                    falta == [],
                    f"1024 px · {nombre}: se dibuja el armazón y la tabla "
                    f"({', '.join(falta) if falta else 'todo lo que tiene que enseñar'})",
                )
                # **El ancho de verdad, no el que se pidió.** Sin esto, esta comprobación puede estar
                # midiendo 16 px menos y decir que ha mirado el corte de 64 rem sin haberlo mirado.
                medido = _ancho_medido(html)
                comprobar(
                    medido is not None and medido[1] == 1024,
                    f"1024 px · {nombre}: se ha medido con 1024 px de ancho de verdad "
                    f"({medido[1] if medido else 'sin medir'})",
                )
                comprobar(
                    'id="menu-cuaderno"' in html and 'class="barra"' in html,
                    f"1024 px · {nombre}: React ha montado el armazón en su contenedor",
                )
                comprobar(
                    _pasos_sin_encontrar(html) == [],
                    f"1024 px · {nombre}: los pasos de la ruta encuentran lo que buscan",
                )
            finally:
                pagina.unlink(missing_ok=True)

        pagina = pagina_de_pantalla(token, direccion, [])
        try:
            html = abre(
                el_navegador,
                f"{direccion}/{pagina.name}",
                perfil,
                segundos=20,
                ventana=ventana_para(720, 900),
            )
            comprobar(
                "no se ha podido abrir" not in html,
                "a 720 px (lo que ve una ventana de 1440 con zoom al 200 %) la pantalla se dibuja",
            )
            comprobar(
                "Apuntar algo de hoy" in html or "APUNTAR" in html,
                "a 720 px se sigue pudiendo apuntar: la pantalla no se queda a medias",
            )
        finally:
            pagina.unlink(missing_ok=True)

        print("\n4 ter. El ancho de un móvil de verdad (390 px)")
        # **390 px es el ancho que pide el contrato y el de un teléfono normal**, y hasta ahora no se
        # había medido nunca: el recorrido miraba el móvil a 500 px —que es más ancho que casi cualquier
        # teléfono que se lleva al campo— y pedirle 390 px al navegador **no sirve**, porque no baja de
        # 500 (ver `ANCHO_MINIMO_DE_LA_VENTANA`). La única forma de tener 390 px de verdad es meter la
        # aplicación en un **hueco de 390 px**, que sí tiene su propio ancho y sus propias reglas de
        # ancho. Se mide el hueco, no la ventana.
        # **Y los tres anchos del contrato, no solo el móvil.** Las pantallas nuevas de T06 y T10
        # (la tabla con el mapa, la ficha de versiones, las semillas y las siembras) se miraban solo a
        # 390 px —que es donde antes se rompe todo— pero el contrato pide **390, 1024 y 1440**, y a
        # 1024 px es justo donde entra la versión de ordenador (64 rem): una tabla que a 390 px cabe
        # con desplazamiento puede partirse de otra manera al lado de un panel. Se miden las nuevas a
        # los tres anchos; las de siempre, a 390, que ya tienen su comprobación de ordenador aparte.
        pantallas_estrechas = [
            ("inicio", "", (390,)),
            ("las tierras", "#/tierras", (390,)),
            ("el almacén", "#/almacen/libro", (390,)),
            # **Las tierras con su mapa** (T06, 03/10/2026): la pantalla donde la tabla, los filtros,
            # los grupos y el mapa tienen que caber juntos. Es la que más se rompe en un móvil, porque
            # lleva una tabla con desplazamiento al lado de un mapa, y el guion del navegador no la
            # recorría: se abre por su dirección, que es como la abre el agricultor.
            ("las tierras y el mapa", "#/tierras/mapa", (390, 1024, 1440)),
            # **Las semillas y las siembras** (T10, 03/10/2026): las dos pantallas nuevas del ticket de
            # semillas. Se abren por su dirección, que es como las abre el agricultor.
            ("las semillas", "#/semillas", (390, 1024, 1440)),
            ("las siembras", "#/semillas/siembras", (390, 1024, 1440)),
            # **Los contactos** (T11, 02/10/2026): la lista de fichas y la revisión de los nombres
            # escritos. Las pidió el agente del ticket al entregar, y tenía razón: **este guion no
            # mencionaba «contactos» ni una vez**, así que el módulo más nuevo no estaba cubierto por
            # la comprobación oficial de la interfaz (él las midió con uno suyo, temporal, a los tres
            # anchos: 33 comprobaciones verdes). Se abren por su dirección, que es como las abre el
            # agricultor.
            ("los contactos", "#/contactos", (390, 1024, 1440)),
            ("la revisión de los nombres", "#/contactos/revisar", (390, 1024, 1440)),
            # **El dinero de las ventas** (T12, 02/10/2026): la tabla de entregas y ventas (S12 del
            # contrato), la lista de las facturas nuestras y la de los cobros. Las pidió el agente del
            # ticket al entregar: son ocho columnas en una tabla, que es justo lo que se rompe a 390 px, y
            # «el rótulo de la última columna caía encima de los botones» fue uno de los defectos que
            # encontró la revisión. A 1024 px es donde entra la versión de ordenador.
            ("las ventas y su dinero", "#/ventas", (390, 1024, 1440)),
            ("las facturas que hemos emitido", "#/ventas/facturas", (390, 1024, 1440)),
            ("los cobros", "#/ventas/cobros", (390, 1024, 1440)),
            # **La maquinaria** (T14, 03/10/2026): la lista con sus ocho columnas. La pidió el agente del
            # ticket al entregar, y tenía razón: **este guion no mencionaba «maquinaria» ni una vez**. Y
            # es una tabla de nueve columnas, que es justo lo que se rompe de ancho: el propio ticket
            # midió que se salía **1.621 px dentro de un hueco de 1.024** antes de meterla en el
            # contenedor que se desplaza solo. A 1024 px es donde entra la versión de ordenador.
            ("la lista de maquinaria", "#/maquinaria", (390, 1024, 1440)),
            # **Las cuentas, los trabajos y el banco** (T13, T15 y T20, 05/10/2026), a los tres anchos del
            # contrato. Son las tres que llevan tabla o lista larga —los gastos con sus columnas de importe
            # y pendiente, y los movimientos del banco, que son siete columnas—, que es justo lo que se
            # rompe de ancho. Se abren por su dirección, que es como las abre el agricultor.
            # **Y el panel de mando**, la portada del ordenador, que es la primera que ve el agricultor
            # en un PC y la que nadie medía a 1024 ni a 1440 px. Aquí sí se mide, y sirvió: su tabla de
            # «los últimos apuntes» empujaba la página **2 px** fuera del hueco a 1024 px (`se sale 1026 de
            # 1024`) y con ella toda la pantalla. Se arregló metiéndola en el contenedor que se desplaza
            # solo (`.tabla-scroll`), como la tabla de la maquinaria de T14. A 390 px ya estaba medido
            # arriba, en «inicio», así que aquí solo van los dos anchos de ordenador.
            ("el panel de mando", "", (1024, 1440)),
            # **La bandeja de los papeles (T08, 06/10/2026)**, a los tres anchos del contrato. Lleva la
            # subida del fichero, la lista de lo que hay que revisar y lo que falta por decir de cada
            # papel, así que es una de las que se rompen de ancho. Se abre por su dirección.
            ("la bandeja de los papeles", "#/papeles/bandeja", (390, 1024, 1440)),
            ("las cuentas", "#/cuentas", (390, 1024, 1440)),
            ("los trabajos", "#/trabajos", (390, 1024, 1440)),
            ("el banco y los papeles", "#/cuentas/bancos", (390, 1024, 1440)),
        ]
        # **Y la ficha de versiones de una tierra** (T06), que se abre por `#/tierras/<id>/versiones`
        # y necesita el identificador de una tierra de verdad: se le pregunta al servidor cuál hay. Si
        # no hubiera ninguna, esa pantalla no se comprueba —mejor eso que comprobar una dirección que
        # no lleva a nada y dar por bueno un «cabe» que no significa nada—.
        identificador_de_una_tierra = la_primera_tierra(direccion, token)
        if identificador_de_una_tierra is None:
            comprobar(False, "no hay ninguna tierra con la que abrir la ficha de versiones")
        else:
            pantallas_estrechas.append(
                (
                    "las versiones de una tierra",
                    f"#/tierras/{identificador_de_una_tierra}/versiones",
                    (390, 1024, 1440),
                )
            )
        # **Y la ficha de un papel de la bandeja** (T08), que se abre por `#/papeles/bandeja/<id>` y
        # necesita, como las tres de arriba, un identificador de verdad. Es la pantalla con más bloques de
        # la bandeja —el original, lo leído, los enlaces y los candidatos—, así que se mide a los tres
        # anchos. Misma regla que las otras: si no hubiera ningún papel, esa pantalla no se comprueba.
        identificador_de_un_papel = el_primer_papel_de_la_bandeja(direccion, token)
        if identificador_de_un_papel is None:
            comprobar(False, "no hay ningún papel en la bandeja con el que abrir su ficha")
        else:
            pantallas_estrechas.append(
                (
                    "la ficha de un papel de la bandeja",
                    f"#/papeles/bandeja/{identificador_de_un_papel}",
                    (390, 1024, 1440),
                )
            )
        # **Y la historia de una tierra** (T15), que se abre por `#/tierras/<id>/historial` y necesita,
        # como las dos de arriba, el identificador de una tierra de verdad. Es **el recorrido 5 entero**
        # —lo que hay sembrado, lo que se ha hecho, lo que está pensado y lo que consta que ha costado—,
        # así que se mide a los tres anchos: lleva el historial, sus tablas y la tabla de costes, que es
        # donde una pantalla así se sale de lo ancho. Misma regla que las otras dos: si no hubiera ninguna
        # tierra, esa pantalla no se comprueba, mejor eso que medir una dirección que no lleva a nada.
        if identificador_de_una_tierra is None:
            comprobar(False, "no hay ninguna tierra con la que abrir su historia")
        else:
            pantallas_estrechas.append(
                (
                    "la historia de una tierra",
                    f"#/tierras/{identificador_de_una_tierra}/historial",
                    (390, 1024, 1440),
                )
            )
        # **Y la ficha de una máquina** (T14), que se abre por `#/maquinaria/<id>` y también necesita un
        # identificador de verdad. Misma regla: si no hubiera ninguna máquina, esa pantalla no se
        # comprueba, mejor eso que comprobar una dirección que no lleva a nada. (El guion deja una
        # máquina con su ITV vencida, así que lo normal es que la haya.)
        identificador_de_una_maquina = la_primera_maquina(direccion, token)
        if identificador_de_una_maquina is None:
            comprobar(False, "no hay ninguna máquina con la que abrir su ficha")
        else:
            pantallas_estrechas.append(
                (
                    "la ficha de una máquina",
                    f"#/maquinaria/{identificador_de_una_maquina}",
                    (390, 1024, 1440),
                )
            )
        for nombre, fragmento, anchos in pantallas_estrechas:
            for ancho in anchos:
                pagina = pagina_estrecha(token, fragmento, ancho)
                try:
                    html = abre(el_navegador, f"{direccion}/{pagina.name}", perfil, segundos=16)
                    medido = _ancho_del_hueco(html)
                    comprobar(
                        medido is not None and medido[1] == ancho,
                        f"{ancho} px · {nombre}: se ha medido en un hueco de {ancho} px de verdad "
                        f"({medido[1] if medido else html and 'sin medir'} px)",
                    )
                    # **Y que sea esa pantalla.** Sin esto, una dirección que la aplicación no sabe
                    # abrir mediría otra pantalla y la comprobación diría «cabe entera» de algo que no es
                    # lo que se pidió: es la mitad que le faltaba a esta parte del guion.
                    direccion_medida = _la_direccion_medida(html)
                    esperada = fragmento.split("?")[0] or "#/"
                    comprobar(
                        direccion_medida.split("?")[0] == esperada,
                        f"{ancho} px · {nombre}: se ha medido **esa** pantalla "
                        f"(se pidió {esperada} y la aplicación acabó en {direccion_medida or 'ninguna'})",
                    )
                    se_sale = _la_pantalla_se_sale(html)
                    cuerpo = _cuerpo_del_hueco(html)
                    comprobar(
                        cuerpo is not None and cuerpo >= 2000,
                        f"{ancho} px · {nombre}: la aplicación está montada dentro del hueco, no en "
                        f"blanco ({cuerpo if cuerpo is not None else 'sin medir'} caracteres)",
                    )
                    comprobar(
                        se_sale == "",
                        f"{ancho} px · {nombre}: la pantalla NO se sale de lo ancho "
                        f"({'se sale ' + se_sale + ' px' if se_sale else 'cabe entera'})",
                    )
                finally:
                    pagina.unlink(missing_ok=True)

        # Y una captura del hueco a 390 px, para poder mirarla: es el ancho en el que hay que ver que la
        # frase más larga no se corta y que los botones se siguen pudiendo pulsar con el dedo.
        pagina = pagina_estrecha(token, "")
        try:
            destino = pathlib.Path(tempfile.gettempdir()) / "cuedigital-movil-390.png"
            comprobar(
                captura(el_navegador, f"{direccion}/{pagina.name}", perfil, destino),
                f"captura del móvil a 390 px en {destino}",
            )
        finally:
            pagina.unlink(missing_ok=True)

        print("\n5. Capturas, para poder mirarlas")
        # La primera (la que más se ve), una del medio, **la última de la lista**, **«mi cuaderno»**
        # —la que más se mira de todas: el agricultor entra ahí a ver su año—, **el paso de elegir la
        # tierra**, que es la lista que más se usa del año y donde están las tarjetas de las tierras, y
        # **«mis cosas»**, que desde la ronda 78 enseña las tierras como tarjetas: es la pantalla donde
        # se ve si el muro de cincuenta y una filas iguales se ha convertido en algo que se reconoce.
        # Se eligen **por su nombre** y no por su número: en una lista que crece, un número no
        # significa nada.
        por_nombre = {nombre: (nombre, ruta, esperadas) for nombre, ruta, esperadas in PANTALLAS}
        for nombre, ruta, _esperadas in (
            PANTALLAS[0],
            PANTALLAS[5],
            PANTALLAS[-1],
            por_nombre["mi cuaderno"],
            por_nombre["el asistente: dónde se ha echado"],
            por_nombre["mis cosas"],
        ):
            pagina = pagina_de_pantalla(token, direccion, ruta)
            try:
                destino = pathlib.Path(tempfile.gettempdir()) / f"cuedigital-{nombre.replace(' ', '-')}.png"
                comprobar(
                    captura(el_navegador, f"{direccion}/{pagina.name}", perfil, destino),
                    f"captura de «{nombre}» en {destino}",
                )
            finally:
                pagina.unlink(missing_ok=True)

        # **Y las capturas de la versión de ordenador** (30/09/2026), que son las que hay que mirar para
        # saber si esto parece una aplicación de gestión o sigue pareciendo un móvil estirado: el panel (el
        # armazón con la pantalla de inicio), **las tierras con su tabla** y **el almacén con la suya**, que
        # es donde se ve si una lista larga se lee de un tirón. Se llaman `cuedigital-escritorio*.png` y no se
        # confunden con las del móvil.
        for indice, (nombre, ruta, _esperadas) in enumerate(ESCRITORIO):
            pagina = pagina_de_pantalla(token, direccion, ruta)
            try:
                # El nombre del fichero sale de la ruta, no de su número: `cuedigital-escritorio.png` para
                # la primera y `cuedigital-escritorio-<lo-que-sea>.png` para las demás. Se hacía por número
                # y **la segunda captura pisaba a la tercera** (las dos acababan en el mismo fichero), que es
                # justo el fallo que estas capturas existen para evitar: mirar una pantalla creyendo que es
                # otra.
                sufijo = "" if indice == 0 else "-" + re.sub(r"[^a-z0-9]+", "-", nombre.lower()).strip("-")
                destino = pathlib.Path(tempfile.gettempdir()) / f"cuedigital-escritorio{sufijo}.png"
                comprobar(
                    captura(
                        el_navegador,
                        f"{direccion}/{pagina.name}",
                        perfil,
                        destino,
                        ventana=ventana_para(1440, 900),
                    ),
                    f"captura de la versión de ordenador ({nombre}) en {destino}",
                )
            finally:
                pagina.unlink(missing_ok=True)

        # **Y no puede quedar nada dentro de la aplicación**: la página se borra en cada vuelta, y
        # aquí se comprueba que no se ha quedado ninguna (una ejecución interrumpida dejaría una).
        comprobar(
            not list((pathlib.Path(__file__).resolve().parents[1] / "web").glob("_comprobacion*")),
            "no queda ningún fichero de la comprobación dentro de la aplicación",
        )

        # ==================================================================
        # 6 y 7. El volumen de verdad, y las descargas pulsando el botón
        # ==================================================================
        #
        # **Estas dos van al final a propósito**: crean su propia explotación con 64 tierras (unos
        # minutos y unas cuatrocientas peticiones) y no tocan nada de lo de arriba. Si fallaran, lo de
        # arriba ya está comprobado y contado.
        print("\n6. El volumen: 64 tierras, listas largas, búsqueda, filtros y selección")
        escenario = None
        try:
            escenario = datos_representativos.preparar(direccion)
        except Exception as error:  # noqa: BLE001 - se dice lo que ha pasado y se sigue
            comprobar(False, f"la preparación del volumen ha fallado: {error}")
        if escenario is not None:
            print(f"   (lo que ha creado la preparación: {escenario.resumen().replace(chr(10), chr(10) + '    ')})")
            comprobar(
                len(escenario.tierras) == 64,
                f"volumen · la preparación deja las 64 tierras (deja {len(escenario.tierras)})",
            )
            comprobar(
                0 < escenario.cuantas_casan < len(escenario.tierras),
                f"volumen · la búsqueda de la prueba casa con parte de las tierras, no con todas "
                f"({escenario.cuantas_casan} de {len(escenario.tierras)})",
            )
            comprobar(
                len(escenario.tierras_sin_superficie) > 0
                and len(escenario.tierras_sin_forma) > 0
                and len(escenario.tierras_sin_cultivo) > 0,
                "volumen · la preparación deja a propósito tierras sin superficie, sin forma y sin cultivo",
            )
            try:
                with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
                    # El token, en **cada documento nuevo**: el navegador se abre sin ventana y no hay
                    # nadie para teclear en la pantalla de entrar.
                    nav.orden(
                        "Page.addScriptToEvaluateOnNewDocument",
                        {
                            "source": "window.localStorage.setItem('cuedigital.token', "
                            f"{json.dumps(escenario.volumen.token)});"
                        },
                    )
                    paso = [0]
                    _el_volumen(nav, direccion, escenario, paso)
                    _el_volumen_se_busca_y_se_marca(nav, direccion, escenario, paso)
                    print("\n7. Las descargas: se pulsa el botón de verdad y se mira el fichero")
                    with tempfile.TemporaryDirectory(prefix="cuedigital-descargas-") as descargas:
                        _las_descargas(
                            nav, direccion, escenario, paso, pathlib.Path(descargas)
                        )
            except SinNavegador as error:
                # Es la misma regla que al principio: sin navegador esto no se puede comprobar, y se
                # dice; no es un fallo del programa.
                comprobar(False, f"no se ha podido comprobar el volumen en un navegador: {error}")

    print()
    if FALLOS:
        print(f"RESULTADO: {len(FALLOS)} comprobaciones han fallado")
        for fallo in FALLOS:
            print(f"  - {fallo}")
        return 1
    print("RESULTADO: la interfaz se abre y se dibuja en un navegador de verdad")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
