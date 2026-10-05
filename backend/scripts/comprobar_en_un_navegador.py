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

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

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
    for ruta in NAVEGADORES:
        if pathlib.Path(ruta).exists():
            return ruta
    return None


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
            "1 apunte en el cuaderno",
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
                json={"campana_id": campana["id"], "especie": "TRIGO BLANDO", "sistema": "secano"},
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
                # La factura se añadió en la ronda 93 para que el borrado de una factura se pueda
                # comprobar de verdad: con la lista vacía, el botón BORRAR de una factura no existe.
                "una factura",
                # La máquina con su ITV vencida (T14, 03/10/2026): sin ella, la lista de maquinaria se
                # comprobaría vacía y la palabra «Vencida» —que es la que informa sin depender del
                # color— no saldría nunca. Va detrás de la factura porque es donde se da de alta.
                "una máquina",
                "su ITV vencida",
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
