# T20 — La pantalla de los extractos y la conciliación (S14)

**Ticket:** `T20 / E11 | T12 | Extractos y conciliación reversible; A07 y duplicados`
**Pantalla:** S14 · `#/cuentas/bancos` (§4) · **Casos de aceptación:** A07 y los duplicados
**Fecha:** 06/10/2026
**Ficheros de este encargo (y solo estos tres):** `backend/web/react/pantallas/bancos.js`,
`backend/tests_js/bancos.test.js` y este informe.

> **El servidor del T20 ya estaba integrado y funcionando** (las cinco tablas en `models.py`, los 16
> endpoints bajo `/api/bancos` en `main.py` y los 59 mensajes `T20_…` en `textos.py`). Lo que faltaba era
> **la pantalla**, y es lo que hay aquí. En este informe, todo lo que va en un fichero compartido
> (`textos.py`, `app.js`, `rutas.js`, `service-worker.js`, `docs/REACT.md`, `gastos.js`) está escrito como
> **bloque literal para copiar**, y está dicho **quién lo tiene que copiar**.

---

## 1. Qué hay hecho

### 1.1. `backend/web/react/pantallas/bancos.js` (nuevo, 1.090 líneas)

Es **un fichero con las dos pantallas** del recorrido, como la maquinaria (T14) y los trabajos (T15):

| Pantalla | Dirección | Qué es |
|---|---|---|
| `PantallaDeLosBancos` | `#/cuentas/bancos` | Subir el fichero, **mirar lo que se ha entendido sin apuntar nada**, apuntarlo, la lista de movimientos con su estado y lo que les queda, **lo que queda por cuadrar** (de los dos lados) y la descarga del extracto. |
| `PantallaDeUnMovimiento` | `#/cuentas/bancos/<id>` | La ficha de un movimiento: **contra qué papel va** (las propuestas con su porqué), apuntarlo a mano, **deshacer** sin borrar, decir que es un **traspaso** entre cuentas propias (A07) y **escribir a mano el importe que no consta**. |

El recorrido del encargo, paso a paso y dónde está cada uno:

| Paso | Dónde se hace en la pantalla | Puerta del servidor |
|---|---|---|
| 1. Subir el extracto | «Subir el extracto»: el fichero, la cuenta y (si ya se dijo) la forma de escribir del banco | `POST /api/bancos/extractos/vista-previa` |
| 2. Revisar la vista previa | «Lo que he entendido del fichero»: líneas leídas, **líneas rechazadas con su motivo y su número de línea**, lo que ya estaba, los traspasos propuestos, los avisos con sus líneas, el formato deducido y **los importes que no constan** | (la misma) |
| 3. Apuntar los movimientos | El botón **APUNTAR ESTOS MOVIMIENTOS**, que **solo existe cuando hay una propuesta delante**, y su hermano **NO APUNTAR NADA** | `POST /api/bancos/extractos/importar` |
| 4. Conciliar | La ficha: las propuestas con su porqué y sus papeles, con un botón por propuesta; y el camino a mano (elegir papel y, si es parcial, cuánto) | `GET …/movimientos/{id}/propuestas` + `POST …/conciliar` |
| 5. Deshacer | La ficha: «Deshacer lo apuntado», con la frase que dice que **el movimiento del banco sigue apuntado** | `POST …/desconciliar` |
| 6. Los pendientes | «Lo que queda por cuadrar»: el dinero del banco sin papel y los papeles sin dinero | `GET /api/bancos/pendientes` |
| 7. Corregir a mano el importe | La ficha: el formulario de corrección (importe, si entra o sale, y el motivo) | `PUT /api/bancos/movimientos/{id}` |
| 8. Exportar | El botón DESCARGAR EL EXTRACTO (lo pide `app.js`, que es quien tiene el token) | `GET /api/bancos/movimientos.csv` |

Y las cinco reglas del negocio, cada una atada a un sitio concreto de la pantalla:

1. **Un pago conciliado no crea un segundo gasto.** La pantalla **no pinta ninguna acción que cree nada**:
   no hay «crear gasto», ni «crear factura», ni «crear cobro» (la lista de acciones del apartado 3.3 lo
   enseña entero). Conciliar solo enseña papeles que ya existen.
2. **Un traspaso entre cuentas propias no es un ingreso ni un gasto.** El bloque «Es un traspaso entre
   cuentas tuyas» ata y desata el vínculo (`banco-traspaso-atar` / `banco-traspaso-quitar`), y cuando está
   atado lo dice con esa frase. Y a un traspaso **no se le ofrecen propuestas**: el servidor no las
   propone y la pantalla lo explica en vez de dejar una lista vacía.
3. **Importar dos veces el mismo fichero no duplica movimientos.** La vista previa dice cuántas líneas **ya
   estaban** antes de apuntar nada (`ya_estaban`, con su explicación), y el resultado de la importación lo
   vuelve a decir (`repetidos`). La pantalla no decide nada de eso: lo dice el servidor.
4. **Un importe que no consta es «no lo sé», nunca cero.** Se ve en tres sitios (la vista previa, la lista
   y la ficha) y **la pantalla no se cree el `texto_*`**: mira el dato crudo (`importe === null`) y enseña
   su palabra. Lo mismo con lo que queda por cuadrar (`por_conciliar === null` es «no lo sé», no `0,00 €`).
   Y en la lista de importes que no constan, esos movimientos **se cuentan aparte** de los totales.
5. **Sin conexión no se puede saber si un movimiento ya está.** Un fallo del servidor se enseña con su
   motivo (`error`) y **la pantalla sigue entera**: el botón de leer, el buscador y todo lo demás siguen
   ahí para reintentar. No hay ningún sitio donde la pantalla diga que algo «no está» cuando lo que pasa
   es que no lo ha podido comprobar: lo que no llega se queda vacío y se dice qué ha fallado.

Además, dos caminos que **completan el recorrido** y que sin ellos no se podría ni empezar o arreglar:

- **Dar de alta una cuenta** (`banco-cuenta-nueva` + `banco-guardar`): el `cuenta_id` es obligatorio para
  leer un extracto, y sin ninguna cuenta dada de alta el agricultor no tendría por dónde empezar. El aviso
  trae el botón que lo arregla (regla de la casa: no dejar sin salida).
- **Decir cómo escribe las fechas y los importes tu banco** (`banco-perfil-nuevo`): los avisos de la
  lectura dicen «Dinos cómo escribe las fechas tu banco y vuelve a subir el extracto», y ese «dínoslo» no
  tenía ningún sitio donde decirse. Es un dato que ya existía en el servidor (`POST /perfiles`) sin puerta.

### 1.2. `backend/tests_js/bancos.test.js` (nuevo, 42 pruebas, 0 rojos)

Con `node --test`, sin navegador y sin `jsdom` (el arnés de siempre: React y `htm` de `vendor/` y
`renderToStaticMarkup`). Lo que comprueban está contado en su cabecera; lo que importa del encargo:

| Lo que el encargo pedía comprobar | La prueba que lo comprueba |
|---|---|
| la vista previa enseña las líneas rechazadas **con su motivo y su número de línea** | `la vista previa enseña cada línea rechazada con su motivo y con su número de línea` |
| hasta que no se confirma **no se manda** la importación | `el formulario de subir lleva su campo de fichero, su cuenta y su perfil, y no apunta nada` |
| conciliar manda **las imputaciones que ha elegido el agricultor** | `el botón de una propuesta lleva el índice de **esa** propuesta, en el orden del servidor` |
| deshacer **no** borra el movimiento | `deshacer dice que no borra nada, y el movimiento sigue entero después` |
| un importe que no consta se enseña **como hueco y no como cero** | `un movimiento sin importe se enseña como hueco: ni un cero, ni un total inventado` |
| la pantalla **no lleva ni una frase escrita a mano** | `la pantalla no lee ninguna frase que no esté en los textos, y no le sobra ninguna` + las dos de «ni una frase escrita a mano» |
| **ninguna acción que pinta se queda sin decir qué hace** | `las acciones que pinta la pantalla son las del informe, y ninguna más` (+ la lista del apartado 3.3) |

### 1.3. Lo que **no** he tocado

Ningún otro fichero. En particular: ni `app/models.py`, ni `app/schemas.py`, ni `app/main.py`, ni
`app/textos.py`, ni `web/app.js`, ni `web/react/rutas.js`, ni `web/service-worker.js`, ni `docs/REACT.md`,
ni `backend/cuedigital.db` (no se ha abierto, ni leído, ni copiado). Todo lo que hace falta en esos
ficheros está en el apartado 3, como bloque literal.

---

## 2. Qué he comprobado, con qué comando y qué número salió

### 2.1. Las pruebas de la pantalla

```bash
cd F:\EspacioCodigo\CueDigital\backend
node --test "tests_js/bancos.test.js"
```

**42 pruebas: 42 en verde, 0 rojos.** 0,33 segundos.

### 2.2. Las pruebas **muerden**: cinco roturas a propósito

No basta con que una prueba esté en verde: hay que ver que se pone roja cuando la regla se rompe. Rompí el
código a propósito cinco veces, miré el rojo y **deshice la rotura** (el árbol está como estaba):

| Rotura a propósito | Rojos | La prueba que lo cazó |
|---|---|---|
| Quitar de una línea rechazada **su motivo** (`fila.que_pasa`) en la vista previa | **1** | `la vista previa enseña cada línea rechazada con su motivo y con su número de línea` |
| Que el botón de una propuesta mandara **siempre la primera** (`indice: 0`) | **1** | `el botón de una propuesta lleva el índice de **esa** propuesta, en el orden del servidor` |
| Enseñar `movimiento.texto_importe` en vez de mirar si el importe consta (el cero de relleno) | **1** | `un movimiento sin importe se enseña como hueco: ni un cero, ni un total inventado` |
| Poner el botón de apuntar (`banco-importar`) también en el formulario de subir el fichero | **1** | `el formulario de subir lleva su campo de fichero, su cuenta y su perfil, y no apunta nada` |
| Que el título de lo apuntado no distinguiera lo devuelto al deshacer | **2** | `deshacer dice que no borra nada, y el movimiento sigue entero después` **y** «no le sobra ninguna frase» (la clave `lo_devuelto_titulo` se quedaba sin usar) |
| Poner una acción por variable (`accion: \`${"banco-abrir"}\``) | **1** | `ninguna acción va puesta por variable, para que el guardián pueda leerlas` |

Dos de esas roturas **enseñaron algo** y está contado en el código:

- la del **cero**: al escribir la prueba me di cuenta de que un saldo de `1.500,00 €` contiene la cadena
  `0,00`, así que la prueba habría pasado sin comprobar nada. Ahora el movimiento de esa prueba lleva un
  saldo sin ceros (`1.234,56 €`) y la prueba exige que **no aparezca un `0,00` por ningún lado**;
- la del **título**: la segunda prueba que se puso roja fue la de «no le sobra ninguna frase». Es
  exactamente lo que tiene que pasar —una frase que existe y ya no la lee nadie es una frase que se queda
  vieja— y confirma que ese guardián también muerde.

### 2.3. Los dos guardianes de Python que **este fichero nuevo** pone en rojo (y por qué)

```bash
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests/test_la_migracion_a_react.py tests/test_los_botones_hacen_algo.py -q
```

**6 pruebas, 5 en rojo y 1 en verde**, y **los cinco rojos son de integración pendiente**, no defectos de
la pantalla. Se dice uno por uno porque el coordinador tiene que saber qué va a encontrarse:

| Prueba | Qué dice | Se arregla con |
|---|---|---|
| `test_la_migracion_a_react.py::test_el_codigo_y_los_ficheros_cuadran` | «hay ficheros de pantalla que no están en `PANTALLAS_EN_REACT`: `['bancos']`» | el bloque 3.5 |
| `test_la_migracion_a_react.py::test_todo_el_javascript_de_react_se_guarda_para_el_campo` | «estos ficheros de React NO se guardan para abrir sin cobertura: `['/react/pantallas/bancos.js']`» | el bloque 3.7 |
| `test_la_migracion_a_react.py::test_el_informe_de_la_migracion_se_puede_contar` | «las cuentas no cuadran: `{"migradas": 51, "con_fichero": 52, "en_la_guia": 51, "en_la_cache": 51}`» | los bloques 3.5, 3.6 y 3.7 (los tres, a la vez) |
| `test_los_botones_hacen_algo.py::test_cada_accion_que_se_pinta_la_atiende_alguien` | las **19** acciones `banco-…` que pinta `bancos.js` no las atiende nadie en `app.js` todavía | el bloque 3.4 |
| `test_los_botones_hacen_algo.py::test_las_acciones_por_variable_estan_donde_se_espera` | «hay acciones puestas por variable en ficheros nuevos: `['bancos.js']`» | **ya está arreglado** (ver abajo) |

> **Y una cosa que aprendí aquí, y que conviene que sepa el siguiente que escriba una pantalla.** El
> guardián de las acciones por variable **no quita los comentarios** antes de mirar. La primera versión de
> mi cabecera explicaba la regla escribiendo el ejemplo prohibido (con su dólar y su llave), y eso **hizo
> que el guardián contara `bancos.js` como un fichero de acciones por variable**… sin tener ninguna. La
> salida fácil habría sido añadirlo a `FICHEROS_CON_ACCION_POR_VARIABLE`, y habría sido una mentira
> escrita en un fichero de pruebas. Lo que hice fue reescribir el párrafo sin el ejemplo y **dejar dicho
> el motivo dentro de `bancos.js`** para que nadie lo vuelva a escribir. Comprobado después:
> `dinamicas: []` para `bancos.js` (el propio guardián, leído con su extractor, lo confirma).

También comprobé, con el extractor del propio guardián, que **las acciones que se leen de `bancos.js` son
las 20 del apartado 3.3** (19 huérfanas hoy + `ir-inicio`, que ya está atendida) y que **no hay ninguna
puesta por variable**.

### 2.4. Lo que he mirado a mano, además

- **Que la copia de los textos de la prueba diga lo mismo que el bloque que propongo**: el diccionario
  `BANCOS` de `tests_js/bancos.test.js` y el bloque de `textos.py` del apartado 3.1 se han comparado clave
  por clave y valor por valor (el mismo texto, letra a letra). Las claves que solo las lee `app.js` (los
  rótulos de los formularios y las columnas de la tabla) están **solo** en el bloque de `textos.py`, y por
  eso no salen en el recuento de «frases que no lee nadie» de la prueba de JavaScript: se dice en el
  comentario de la prueba para que no parezca un olvido.
- **Que las cuatro familias de claves compuestas estén enteras** (`estado_…`, `falta_…`, `por_que_no_…` y
  `propuesta_…`): están sacadas de `app/extractos.py` (los cuatro estados de `ESTADOS_DE_CONCILIACION`, los
  seis motivos de lo que puede faltar en un movimiento guardado, los dos `NO_PORQUE_…` y los tres
  `TIPOS_DE_PROPUESTA`), no de una lista escrita a mano. Una prueba recorre las cuatro familias y otra
  comprueba que **salen pintadas**.
- **Que ninguna de mis frases lleve jerga**: hay una prueba con las catorce palabras prohibidas sobre la
  copia entera de los textos.
- **Que los `Decimal` viajan como texto**: comprobado en la prueba del ticket que ya existía
  (`assert corregido.json()["importe"] == "18.50"` en `tests/test_extractos.py`). Por eso **todos los
  importes que la pantalla enseña llegan ya escritos** (`texto_*`) y el formateo del dinero sigue viviendo
  en un solo sitio (`enEuros`, en `app.js`).

---

## 3. Bloques literales para los ficheros compartidos

Todo lo de este apartado es **del coordinador**. Está escrito para copiarse tal cual.

### 3.1. `backend/app/textos.py` — el vocabulario de la pantalla

Va al final del fichero, **después** de `MENSAJES_DE_LOS_EXTRACTOS` (que ya está) y antes del
`def textos_visibles()`. Es un diccionario propio con nombre propio, como `textos.GASTOS` y `textos.AGENDA`.

```python
# --------------------------------------------------------------------------
# El extracto del banco y la conciliación (T20, E11, 06/10/2026)
# --------------------------------------------------------------------------
#
# **Las palabras de S14**: subir el extracto, mirarlo sin apuntar nada, cuadrarlo con las facturas y los
# cobros, deshacerlo y mirar lo que queda. Y las cuatro familias de claves que se leen **compuestas**,
# dichas aquí para que nadie las busque en balde:
#
#   · `estado_<estado>` — cómo está un movimiento (`sin_conciliar`, `conciliado_en_parte`, `conciliado`,
#     `no_se_puede_conciliar`). El servidor manda la clave en `MovimientoSalida.estado`, no la frase.
#   · `falta_<lo_que_falta>` — qué no consta de una línea (`importe_no_consta`, `saldo_no_consta`,
#     `referencia_no_consta`, `concepto_no_consta`, `importe_ilegible_en_la_fila`, `saldo_ilegible`).
#   · `por_que_no_<clave>` — por qué un movimiento no se puede cuadrar (`no_consta_el_importe`,
#     `es_un_traspaso_entre_cuentas_tuyas`).
#   · `propuesta_<tipo>` — cómo cuadra una propuesta (`exacta`, `agrupada`, `parcial`).
#
# Las claves de las cuatro familias salen de `app/extractos.py` (sus constantes), y hay una prueba que las
# recorre enteras: **la que falte sale en blanco en la pantalla sin que salte nada**, y un renglón en
# blanco en medio de una pantalla de dinero es lo peor que puede pasar aquí. **Y ojo con `no_se_puede_conciliar`:
# no es «sin cuadrar»** — uno dice «se puede y no lo has hecho» y el otro «no se puede, y aquí está por qué».
BANCOS: dict[str, str] = {
    # --- la pantalla ---
    "titulo": "El banco y los papeles",
    "explica": (
        "Aquí subes el extracto que has descargado de tu banca y lo cuadras con las facturas y los cobros. "
        "El programa no se conecta a ningún banco: solo lee el fichero que le das tú."
    ),
    "buscando": "Buscando…",
    "volver_a_los_movimientos": "VOLVER A LOS MOVIMIENTOS",
    # --- subir el fichero (leer NO guarda nada) ---
    "subir_titulo": "Subir el extracto",
    "subir_explica": (
        "Elige el fichero que has descargado de tu banca. El programa lo lee y te enseña lo que ha "
        "entendido, sin apuntar nada todavía."
    ),
    "nada_se_apunta": "Leer no apunta nada: primero lo miras y después decides.",
    "fichero": "El fichero del extracto",
    "fichero_pista": "Es el fichero que te has descargado de tu banca.",
    "fichero_elegido": "El fichero que has elegido es",
    "cuenta": "De qué cuenta es",
    "cuenta_pista": "La cuenta de la que has descargado el extracto.",
    "elige_la_cuenta": "Elige la cuenta",
    "perfil": "Cómo escribe tu banco",
    "perfil_pista": "Si ya nos dijiste cómo escribe las fechas y los importes, elígelo aquí.",
    "sin_perfil": "Todavía no lo he dicho",
    "leer_el_extracto": "LEER EL EXTRACTO",
    "leyendo": "Leyendo el extracto…",
    "anadir_una_cuenta": "AÑADIR UNA CUENTA",
    "anadir_un_perfil": "DECIR CÓMO ESCRIBE MI BANCO",
    "sin_cuentas": "Para subir un extracto hace falta decir antes de qué cuenta es.",
    # --- la vista previa: lo que se va a apuntar, y lo que no ---
    "vista_titulo": "Lo que he entendido del fichero",
    "vista_nada_apuntado": "Esto todavía no está apuntado. Míralo y, si está bien, apúntalo.",
    "ya_estaba_el_fichero": "Este mismo fichero ya lo subiste antes.",
    "cuenta_detectada": "En el fichero pone que es la cuenta",
    "cuenta_no_detectada": "En el fichero no se lee de qué cuenta es.",
    "lineas_leidas": "Líneas leídas",
    "movimientos_leidos": "Movimientos entendidos",
    "se_apuntaran": "Se van a apuntar",
    "ya_estaban": "Ya estaban apuntados",
    "ya_estaban_explica": "Estos no se apuntan otra vez: ya los tenías.",
    "rechazadas_cuantas": "Líneas que no se han entendido",
    "entradas": "Dinero que entra",
    "salidas": "Dinero que sale",
    "sin_importe": "Líneas sin importe",
    "sin_importe_explica": (
        "De esas no se sabe cuánto, y no cuentan en los totales. Escribe el importe a mano."
    ),
    "formato_de_fecha": "Las fechas del fichero",
    "formato_no_dicho": "No nos has dicho cómo son",
    "saldo_final": "El saldo que queda",
    "no_consta": "No consta",
    "no_se_sabe": "No lo sé",
    "avisos_titulo": "Lo que hay que mirar de esta lectura",
    "rechazadas_titulo": "Líneas que no se han podido leer",
    "rechazadas_explica": "Estas líneas no se van a apuntar. Cada una dice qué le pasa y en qué línea está.",
    "linea_numero": "Línea",
    "se_van_a_apuntar": "Lo que se va a apuntar",
    "no_hay_ninguno_nuevo": "De este fichero no hay ningún movimiento nuevo que apuntar.",
    "ya_estaba_esta_linea": "Esta línea ya estaba apuntada.",
    "apuntar_los_movimientos": "APUNTAR ESTOS MOVIMIENTOS",
    "importando": "Apuntando…",
    "descartar": "NO APUNTAR NADA",
    "apuntado_titulo": "Lo que se ha apuntado",
    "apuntados": "Movimientos apuntados",
    "repetidos": "Que ya estaban",
    "repetidos_explica": "No se han repetido: ya los tenías apuntados.",
    # --- los traspasos entre cuentas propias (A07) ---
    "traspasos_titulo": "Dinero que ha cambiado de cuenta",
    "traspasos_explica": "Parece el mismo dinero pasado de una cuenta tuya a otra.",
    "traspaso_sale_de": "Sale de",
    "traspaso_entra_en": "Entra en",
    "traspaso_dias": "Días de diferencia",
    "traspaso_donde": "Márcalo abriendo uno de los dos movimientos y diciendo cuál es el otro.",
    # --- la lista de movimientos ---
    "movimientos_titulo": "Los movimientos del banco",
    "movimientos_explica": "Cada línea del extracto, con lo que le queda por cuadrar.",
    "movimientos_vacio": (
        "Todavía no has apuntado ningún movimiento. Sube el extracto de tu banca para empezar."
    ),
    "sin_resultados": (
        "Ningún movimiento coincide con lo que buscas. Prueba con otras letras o pulsa VER TODO."
    ),
    "buscar": "Buscar en los movimientos",
    "buscar_pista": "Escribe parte del concepto o de la referencia.",
    "buscar_boton": "BUSCAR",
    "ver_todo": "VER TODO",
    "exportar": "DESCARGAR EL EXTRACTO",
    "exportar_pista": "Se descarga en un fichero, con el importe en blanco donde no consta.",
    "estado": "Cuáles ver",
    "todos_los_estados": "Todos",
    "fecha": "El día",
    "referencia": "La referencia",
    "importe": "El importe",
    "saldo": "El saldo que quedó",
    "su_cuenta": "La cuenta",
    "como_esta": "Cómo está",
    "imputado": "Ya apuntado a papeles",
    "por_conciliar": "Le queda por cuadrar",
    "abrir": "¿CONTRA QUÉ PAPEL VA?",
    "es_traspaso": "Es un traspaso entre cuentas tuyas: ese dinero solo ha cambiado de sitio.",
    "corregido_a_mano": "Este importe lo escribiste tú.",
    "sin_importe_aviso": (
        "De este movimiento no consta el importe, así que no se puede cuadrar con ningún papel. "
        "Escríbelo a mano."
    ),
    # --- lo que queda por cuadrar, de los dos lados ---
    "pendientes_titulo": "Lo que queda por cuadrar",
    "pendientes_explica": (
        "De un lado, el dinero del banco que todavía no está apuntado a ningún papel. Del otro, las "
        "facturas y los cobros a los que les falta dinero."
    ),
    "dinero_sin_papel": "Dinero del banco sin papel",
    "sin_conciliar_cuantos": "Movimientos sin cuadrar",
    "papeles_sin_dinero": "Papeles sin dinero",
    "de_quien": "Quién",
    "le_falta": "Le falta",
    "sin_pendientes": "No queda nada por cuadrar: todo el dinero apuntado está en su papel.",
    "como_se_cuadra": "Para cuadrar algo, abre el movimiento del banco y dile contra qué papel va.",
    # --- la ficha de un movimiento ---
    "ficha_titulo": "Este movimiento del banco",
    "propuestas_titulo": "Contra qué papel va",
    "propuestas_explica": (
        "Estas son las cuentas que cuadran con este movimiento, y por qué. Elige una y el dinero queda "
        "apuntado a ese papel."
    ),
    "propuestas_vacio": (
        "Con este movimiento no cuadra ninguna factura ni ningún cobro. Puedes apuntarlo a mano."
    ),
    "porque_titulo": "Por qué te lo propongo",
    "a_que_papeles": "A estos papeles",
    "se_apuntaria": "Se apuntarían",
    "quedaria_sin_apuntar": "Quedaría sin apuntar",
    "apuntar_esta": "APUNTAR ESTA",
    "papel_desconocido": "De este papel no se sabe cómo se llama. Míralo antes de apuntar nada aquí.",
    "a_mano_titulo": "Apuntarlo a mano",
    "a_mano_explica": (
        "Elige el papel y, si solo le vas a apuntar una parte, escribe cuánto. Si lo dejas en blanco, se "
        "apunta lo que quepa, del papel más antiguo al más nuevo."
    ),
    "papel": "A qué papel",
    "elige_el_papel": "Elige el papel",
    "cantidad": "Cuánto de este movimiento",
    "cantidad_pista": "Déjalo en blanco para apuntar todo lo que quepa.",
    "apuntar": "APUNTAR ESTE DINERO",
    "sin_papeles": (
        "No tienes ninguna factura ni ningún cobro al que apuntar este dinero. Apúntalo antes."
    ),
    "lo_conciliado_titulo": "Lo que ha quedado apuntado",
    "lo_devuelto_titulo": "Lo que ha vuelto a quedar pendiente",
    "deshacer_titulo": "Deshacer lo apuntado",
    "deshacer_explica": (
        "Deshacer no borra el movimiento del banco: el banco ya movió ese dinero. Lo que se deshace es a "
        "qué papeles estaba apuntado, y queda dicho quién lo deshizo y cuándo."
    ),
    "deshacer": "DESHACERLO",
    "nada_que_deshacer": "De este movimiento no hay nada apuntado a ningún papel.",
    "traspaso_titulo": "Es un traspaso entre cuentas tuyas",
    "traspaso_explica": (
        "Si este dinero solo ha cambiado de cuenta, dilo: así no cuenta como ingreso ni como gasto."
    ),
    "traspaso_ya_esta": "Este movimiento está atado a otro: ese dinero solo ha cambiado de cuenta.",
    "traspaso_el_otro": "La otra parte del traspaso",
    "traspaso_pista": "Tiene que ser de otra cuenta tuya, del mismo importe y al revés.",
    "traspaso_elige": "Elige el otro movimiento",
    "traspaso_atar": "ATAR EL TRASPASO",
    "traspaso_quitar": "QUITAR EL TRASPASO",
    "sin_parejas": "No hay ningún movimiento de otra cuenta tuya al que atarlo.",
    "corregir": "CORREGIR EL IMPORTE A MANO",
    # --- los botones de los formularios (los lee `app.js`, no la pantalla) ---
    "guardar": "GUARDAR",
    "cancelar": "DEJARLO",
    "guardando": "Guardando…",
    # --- el alta de una cuenta (sin ningún dato de banca) ---
    "form_cuenta_titulo": "Añadir una cuenta",
    "form_cuenta_pista": (
        "Aquí no se pide ninguna clave ni el número entero de la cuenta: el programa no se conecta a tu "
        "banco, solo lee el fichero que le des."
    ),
    "cuenta_nombre": "Cómo llamas a esta cuenta",
    "cuenta_nombre_pista": "Un nombre que reconozcas: «La del día a día», «La del gasóleo».",
    "cuenta_banco": "Qué banco es",
    "cuenta_banco_pista": "Si no quieres apuntarlo, déjalo en blanco.",
    "cuenta_ultimos": "Los cuatro últimos números",
    "cuenta_ultimos_pista": (
        "Solo los cuatro últimos. El número entero no hace falta para nada y no se guarda."
    ),
    "cuenta_propia": "Es una cuenta tuya",
    "cuenta_propia_pista": "Lo que se mueve entre tus cuentas no es un ingreso ni un gasto.",
    # --- cómo escribe el banco (el perfil de formato) ---
    "form_perfil_titulo": "Cómo escribe tu banco",
    "form_perfil_pista": (
        "Si tu banco escribe las fechas o los importes de una manera que el programa no puede adivinar, "
        "díselo aquí una vez y se acuerda la próxima vez."
    ),
    "perfil_nombre": "Cómo llamas a esta forma de escribir",
    "perfil_nombre_pista": "Por ejemplo: «El extracto de la cuenta del gasóleo».",
    "perfil_cuenta": "De qué cuenta es",
    "perfil_cuenta_pista": "Si vale para todas tus cuentas, déjalo sin decir.",
    "perfil_decimal": "Cómo escribe los decimales",
    "perfil_fecha": "Cómo escribe las fechas",
    "perfil_sin_signo": "Cuando un importe no trae signo, ¿qué quiere decir?",
    "decimal_coma": "Con coma (1.234,56)",
    "decimal_punto": "Con punto (1,234.56)",
    "fecha_dmy": "Día/mes/año (31/12/2026)",
    "fecha_mdy": "Mes/día/año (12/31/2026)",
    "sin_signo_entra": "Que el dinero entra",
    "sin_signo_sale": "Que el dinero sale",
    # --- la corrección del importe que no consta ---
    "form_correccion_titulo": "Corregir este movimiento",
    "form_correccion_pista": (
        "Sirve para escribir el importe que no consta en el fichero del banco. Si ya has apuntado este "
        "dinero a un papel, deshaz primero la conciliación."
    ),
    "correccion_importe": "El importe",
    "correccion_importe_pista": "Como lo escribe tu banco: 1.234,56",
    "correccion_signo": "Si el dinero entra o sale",
    "signo_entra": "Entra",
    "signo_sale": "Sale",
    "correccion_concepto": "Qué fue",
    "correccion_motivo": "Por qué lo corriges",
    "correccion_motivo_pista": "Escríbelo pensando en que lo vas a leer dentro de dos años.",
    # --- cómo está un movimiento (el servidor manda la clave, no la frase) ---
    "estado_sin_conciliar": "Sin cuadrar",
    "estado_conciliado_en_parte": "A medias",
    "estado_conciliado": "Cuadrado",
    "estado_no_se_puede_conciliar": "No consta el importe",
    # --- lo que no consta de una línea ---
    "falta_importe_no_consta": "No consta el importe",
    "falta_saldo_no_consta": "No consta el saldo",
    "falta_referencia_no_consta": "No trae referencia",
    "falta_concepto_no_consta": "No trae concepto",
    "falta_importe_ilegible_en_la_fila": "El importe no se ha podido leer",
    "falta_saldo_ilegible": "El saldo no se ha podido leer",
    # --- por qué no se puede cuadrar ---
    "por_que_no_no_consta_el_importe": (
        "En este movimiento no consta el importe, así que no se sabe cuánto se puede apuntar a un papel. "
        "Escríbelo y vuelve a intentarlo."
    ),
    "por_que_no_es_un_traspaso_entre_cuentas_tuyas": (
        "Este movimiento es un traspaso entre cuentas tuyas: ese dinero solo ha cambiado de sitio y no "
        "salda ninguna factura."
    ),
    # --- cómo cuadra una propuesta ---
    "propuesta_exacta": "Cuadra exacto con este papel",
    "propuesta_agrupada": "Cuadra con varios papeles a la vez",
    "propuesta_parcial": "Es una parte de lo que le falta",
}
```

Y dentro de `def textos_visibles()`, al final (con `_recoger` y no con `.values()`, por la regla que ya
está escrita allí para `GASTOS` y `AGENDA`):

```python
    # **El extracto del banco y la conciliación (T20, E11, 06/10/2026).** Se recoge entero —con `_recoger`
    # y no con `.values()`— por el mismo motivo que los del T13 y el T15: dentro lleva las cuatro familias
    # de claves compuestas, y `_recoger` las recorre todas. Un texto de pantalla que no pase por aquí es un
    # texto que se lee sin que el test de jerga lo mire.
    textos.extend(_recoger(BANCOS))
```

### 3.2. `backend/app/routers/interfaz.py` — servirlos

Una línea, junto a `"agenda": textos.AGENDA,` (línea 250):

```python
        # **El extracto del banco y la conciliación (T20, E11, 06/10/2026).** Sin esto, la pantalla de S14
        # sale con todos sus botones y sus rótulos en blanco. Y va **aquí** y no solo dentro de la
        # respuesta de `/api/bancos/movimientos` porque la ficha de un movimiento se abre directamente por
        # su dirección (`#/cuentas/bancos/12`) y entonces no hay ninguna lista que traiga sus palabras; y
        # porque esto se guarda en el móvil (`localStorage`, la clave `cuedigital.interfaz`), así que la
        # pantalla sigue teniendo sus palabras **sin cobertura**.
        "bancos": textos.BANCOS,
```

### 3.3. `backend/web/react/rutas.js` — las direcciones

**Dos direcciones y ninguna más.** Van entre `gastos` y `gasto` en la tabla `PANTALLAS`:

```js
  { clave: "gastos", patron: ["cuentas"] },
  // **El extracto del banco y la conciliación (T20, E11, 06/10/2026).** La lista vive **dentro de la
  // familia de las cuentas** (`#/cuentas/bancos`), que es el renglón del menú del que sale, por los mismos
  // motivos que las demás listas de esta tabla: se reconstruye entera al abrir su dirección —pide sus
  // datos al servidor—, así que se puede enlazar, recargar y mandar a quien ayuda. Y **el tramo de texto
  // fijo va antes que el identificador**, como en todas las familias: si no, `#/cuentas/bancos` se leería
  // como la ficha del gasto número «bancos», que no existe.
  { clave: "bancos", patron: ["cuentas", "bancos"] },
  // Y **la ficha de un movimiento tiene su dirección** (`#/cuentas/bancos/12`): al recargarla se vuelven a
  // pedir sus propuestas al servidor, así que no sale vacía. Lo que **no** tiene dirección son sus
  // formularios (subir el fichero, el alta de una cuenta, la forma de escribir del banco, la corrección
  // del importe): al recargar saldrían vacíos, y eso es peor que no tener dirección.
  { clave: "banco_movimiento", patron: ["cuentas", "bancos", ":id"] },
  { clave: "gasto", patron: ["cuentas", ":id"] },
```

**Por qué `#/cuentas/bancos` y no `#/bancos`:** porque S14 es una sección de la familia de las cuentas
(el contrato la dibuja dentro de `/cuentas`, y `#/cuentas` es la lista de gastos de T13), y porque así la
dirección dice de dónde se sale. **Por qué la ficha sí tiene dirección y los formularios no:** la ficha se
reconstruye entera desde el servidor (sus propuestas se piden a su puerta); los formularios viven en la
memoria de la sesión y no se pueden reproducir desde una barra de direcciones.

Lo que **no** se toca: `LISTADOS`. Los filtros de esta lista (el buscador y el estado) **no viajan en la
dirección** y la pantalla no recuerda la vista entre la lista y la ficha. Se decidió así a propósito —
`LISTADOS` es la lista de las que recuerdan su vista, y meter ahí una lista más obliga a tocar el mecanismo
de memoria de vistas de `app.js`, que es de otro encargo— y **se puede añadir después sin cambiar nada de
la pantalla**: la dirección de la lista ya admite parámetros de consulta (`?q=…&estado=…`) y el endpoint de
los movimientos ya los acepta (`texto`, `estado`, `cuenta_id`, `desde`, `hasta`).

### 3.4. `backend/web/app.js` — el bloque entero de la pantalla

Es el bloque más largo del informe y se copia tal cual. Va **con los demás de su familia**, después del de
las cuentas (T13) y antes del de la maquinaria, y **la última línea del fichero no se toca**: el
`include_router` del servidor no tiene nada que ver con esto; lo que importa aquí es que **el manejador de
clics es uno solo** y hay que añadirle las 20 acciones del apartado 3.4.2.

#### 3.4.0. El `import` (arriba del fichero, con los otros)

```js
// **El extracto del banco y la conciliación (T20, E11, 06/10/2026).** Un fichero con las dos pantallas
// del contrato: los movimientos (`#/cuentas/bancos`) y la ficha de un movimiento
// (`#/cuentas/bancos/<id>`), que es donde se dice contra qué papel va el dinero. Es un solo fichero
// porque las dos comparten las mismas piezas (el renglón de dato, el formulario y el bloque de las
// propuestas) y separarlas obligaría a copiarlas.
import { pantallaDeLosBancos, pantallaDeUnMovimiento } from "./react/pantallas/bancos.js";
```

#### 3.4.1. Las cinco listas de `app.js` que hay que tocar para que la pantalla tenga dirección

Son cinco líneas (más un `if`), y **ninguna es opcional**: sin la primera, la prueba de la migración se
pone roja; sin las otras, la pantalla se abre pero **no escribe su dirección**, o el menú se queda sin
marcar el renglón en el que está el agricultor.

**1) `PANTALLAS_EN_REACT`** — una línea por **fichero** (que es lo que cuentan las tres listas que compara
`tests/test_la_migracion_a_react.py`; el fichero tiene dos pantallas, igual que `maquinaria.js`,
`gastos.js` y `trabajos.js`):

```js
  // El extracto del banco y la conciliación (T20, E11, 06/10/2026). Un solo fichero (`bancos.js`) con las
  // dos pantallas: los movimientos con su estado y lo que les queda, y la ficha de uno, que es donde se
  // dice contra qué papel va. Va aquí y en la caché del campo por lo de siempre: sin cobertura, una
  // pantalla que no está guardada es un hueco.
  "bancos",
```

**2) `DIRECCION_PROPIA`** — la dirección de cada pantalla que **no** es la de su renglón del menú:

```js
  // El extracto del banco y la conciliación (T20, 06/10/2026). La lista vive dentro de la familia de las
  // cuentas (`#/cuentas/bancos`) —de ahí sale, y por eso **hay que escribirla aquí**: sin esta línea,
  // `apuntarLaDireccion` le pondría la dirección del renglón del menú (`#/cuentas`) y las dos pantallas
  // escribirían la misma—, y **la ficha de un movimiento tiene la suya** (`#/cuentas/bancos/12`), porque
  // se puede enlazar y recargar: sus propuestas se piden al servidor al abrirla.
  PantallaDeLosBancos: "bancos",
  PantallaDeUnMovimiento: "banco_movimiento",
```

**3) `MODULO_DE_LA_PANTALLA`** — qué renglón del menú se marca al abrirlas (si no, el menú se queda **sin
ningún renglón marcado**, y no saber dónde estás es la mitad de para qué sirve un menú):

```js
  // El banco y los papeles (T20): cuelgan del renglón de las cuentas, igual que un gasto.
  PantallaDeLosBancos: "cuentas",
  PantallaDeUnMovimiento: "cuentas",
```

**4) El identificador en el camino**, dentro de `apuntarLaDireccion` (con los otros: `maquina`,
`venta_importe`, `tierra_versiones`…). **Sin esto, la ficha no tiene dirección**: `#/cuentas/bancos/` no es
la ficha de nada, y `apuntarLaDireccion` no escribiría nada (que es lo correcto: no se toca la barra).

```js
  // **La ficha de un movimiento del banco (T20)**: su identificador en el camino (`#/cuentas/bancos/12`),
  // como la de un gasto o una máquina. Sale del estado, que es donde está el movimiento que se está
  // mirando.
  if (clave === "banco_movimiento") {
    const movimiento = (estado.bancos || {}).movimiento;
    if (!movimiento || !movimiento.id) return;
    parametros.id = movimiento.id;
  }
```

**5) `abrirLaPantalla`** — de dirección a pantalla (donde están `if (clave === "gastos") …`, línea 1186):

```js
  // **El extracto del banco y la conciliación (T20, E11, 06/10/2026)**: los movimientos y la ficha de
  // uno. Las dos se piden al servidor al abrirlas, así que se pueden enlazar y recargar.
  if (clave === "bancos") return abrirLosBancos();
  if (clave === "banco_movimiento") return abrirUnMovimientoDelBanco(parametros.id);
```

Y **no** hay que tocar `PANTALLAS_SIN_DIRECCION` (los formularios de esta pantalla no son pantallas: viven
dentro de las dos de arriba) ni `TABLA_DE_LA_PANTALLA` (esta lista no recuerda su vista; ver el apartado 3.3).

#### 3.4.2. Las 20 acciones, una por una

Estas son **todas** las acciones que la pantalla pinta (comprobado con el extractor del guardián:
19 nuevas + `ir-inicio`, que ya está atendida). Una acción se pinta con `data-accion="…"` y su rama en el
manejador de clics es `if (nombre === "…")`. **Ninguna se pinta por variable.**

| Acción | Dónde se pinta | Qué tiene que hacer |
|---|---|---|
| `banco-leer` | Lista, subir el extracto | Leer el fichero elegido (`#banco-fichero`) y la cuenta (`#banco-cuenta`), y **sin guardar nada** pedir `POST /api/bancos/extractos/vista-previa` (multipart: `fichero`, `cuenta_id`, `perfil_id`). **Guardar el `File` en `estado.bancos.fichero`**: repintar la pantalla borra la casilla. Enseñar la vista previa. |
| `banco-importar` | Vista previa, solo aquí | `POST /api/bancos/extractos/importar` con **el fichero guardado** y `clave_de_reenvio` (una sola por subida, con `claveDeReenvio("extracto")`). Guardar el resultado y recargar la lista. |
| `banco-descartar` | Vista previa | Olvidar la vista previa y el fichero guardado, **sin llamar al servidor**: el agricultor dice que no se apunte nada. |
| `banco-abrir` | Cada movimiento (lista y tabla) | Ir a la ficha: `abrirUnMovimientoDelBanco(data-id)`, que es lo mismo que hace `gasto-abrir`. La dirección la escribe `montar()` sola, con `DIRECCION_PROPIA` (bloque 3.4.1). |
| `banco-buscar` | Lista | Leer `#banco-buscar` y `#banco-estado`, guardarlos en el estado y recargar la lista con `?texto=…&estado=…`. |
| `banco-ver-todos` | Lista | Vaciar el buscador y el estado y recargar la lista. |
| `banco-cuenta-nueva` | Lista (y el aviso de «no hay cuentas») | Abrir el formulario del alta de una cuenta (`{clase: "cuenta"}`). |
| `banco-perfil-nuevo` | Lista | Abrir el formulario de «cómo escribe tu banco» (`{clase: "perfil"}`). |
| `banco-guardar` | Los tres formularios | Mirar `data-clase` y mandar a su puerta: `cuenta` → `POST/PUT /api/bancos/cuentas`, `perfil` → `POST/PUT /api/bancos/perfiles`, `correccion` → `PUT /api/bancos/movimientos/<data-id>`. |
| `banco-cancelar` | Los tres formularios | Cerrar el formulario sin guardar (y volver a pintar la pantalla de la que salió). |
| `banco-elegir` | Los bloques de elegir de un formulario | Guardar la opción elegida en el borrador con `data-campo` y `data-valor`, y volver a pintar el formulario (los botones de elegir no son un `<select>`). |
| `banco-exportar` | Lista | Bajar `GET /api/bancos/movimientos.csv` con el token y descargarlo, como `sacarDatos()` (`api` + `blob` + un `<a download>`). |
| `banco-conciliar-propuesta` | Cada propuesta de la ficha | `POST /api/bancos/movimientos/<id>/conciliar` con **las imputaciones de la propuesta `data-indice`** de las que se pidieron a `/propuestas` (`{imputaciones: [{clase, documento_id, importe}]}`), tal cual, **en el orden del servidor**. |
| `banco-conciliar-a-mano` | La ficha | Leer `#banco-papel` (su valor es `clase:documento_id`) y `#banco-cantidad`, y `POST …/conciliar` con **una** imputación; **si la cantidad va vacía, mandar `importe: null`** (el servidor reparte por orden, del papel más antiguo al más nuevo). |
| `banco-deshacer` | La ficha, con dinero apuntado | `POST /api/bancos/movimientos/<data-id>/desconciliar` con `{imputaciones: []}` (todo lo vivo) y guardar el resultado con `deshecho: true`. **El movimiento no se borra**: `app.js` no toca nada más. |
| `banco-traspaso-atar` | La ficha, con otra cuenta elegida | Leer `#banco-pareja` y `POST /api/bancos/movimientos/<data-id>/traspaso` con `{otro_movimiento_id: <el elegido>}`. |
| `banco-traspaso-quitar` | La ficha, con un traspaso atado | `POST …/traspaso` con `{otro_movimiento_id: null}`. |
| `banco-corregir` | La ficha | Abrir el formulario de corrección (`{clase: "correccion", id}`), con los campos vacíos: lo que se va a escribir es el importe que no consta. |
| `banco-ver` | La ficha | Volver a la lista **sin volver a pedirla** (los datos ya están en el estado), para no perder el filtro que el agricultor tenía puesto. |
| `ir-inicio` | Las dos pantallas | Ya está atendida: volver a la pantalla de inicio. |

#### 3.4.3. El bloque de código

Va con los demás (después del de las cuentas). Está escrito con los ayudantes que ya existen en `app.js`
(`api`, `apiJson`, `valorDeLaCasilla`, `enEuros`, `formateaFecha`, `claveDeReenvio`, `mensaje`,
`accion("volver")`, `montar`, `irA`, `recargarDatos`).

```js
// ---------------------------------------------------------------------------
// El extracto del banco y la conciliación (T20, E11, 06/10/2026)
// ---------------------------------------------------------------------------
//
// LO QUE ESTE BLOQUE HACE, Y LO QUE NO. Hace tres cosas y ninguna más:
//
//   1. **Pide los datos** —las cuentas, los movimientos, los papeles pendientes y las propuestas de un
//      movimiento— y se los pasa a la pantalla, que no calcula nada.
//   2. **Sube el fichero** que el agricultor ha elegido: primero a la vista previa (que **no guarda**) y,
//      cuando él lo dice, a la puerta que apunta los movimientos.
//   3. **Lee lo que el agricultor escribe** por los `id` de los campos y lo manda a su puerta.
//
// Lo que **no** hace: ni una cuenta de dinero. Los importes, los cuadres y lo que le queda por cuadrar
// llegan calculados del servidor (son `Decimal` y viajan como texto), y aquí lo único que se hace con
// ellos es **escribirlos** con `enEuros` (que devuelve vacío cuando el dato no consta, y nunca «0,00 €»).
//
// **Y no se conecta ningún banco.** Lo único que entra es el fichero que el agricultor ha subido: no hay
// claves, ni direcciones de banco, ni un sitio donde poner una credencial.

/** El estado de los bancos, creado la primera vez que hace falta (como el de las cuentas). */
function estadoDeLosBancos() {
  if (!estado.bancos) {
    estado.bancos = {
      cuentas: [],
      perfiles: [],
      movimientos: null,
      pendientes: [],
      cuentaElegida: "",
      perfilElegido: "",
      // **El fichero vive aquí y no en la casilla del formulario.** Repintar la pantalla borra el
      // `<input type="file">`, y lo que solo viviera ahí desaparece: es la trampa que ya costó una ronda
      // con el cuaderno de la Junta (ver AGENTS.md). Por eso se guarda al leerlo, que es lo que permite
      // apuntarlo después sin volver a pedírselo al agricultor.
      fichero: null,
      nombreDelFichero: "",
      vistaPrevia: null,
      resultado: null,
      leyendo: false,
      importando: false,
      filtro: "",
      estado: "",
      formulario: null,
      borrador: null,
      guardando: false,
      error: "",
      aviso: "",
      movimiento: null,
      propuestas: null,
      conciliado: null,
      deshecho: false,
      deshacer: false,
      correccion: null,
    };
  }
  return estado.bancos;
}

/** El vocabulario de esta pantalla: el del banco y el botón de VOLVER que ya está en los textos. */
function textosDeLosBancos() {
  return {
    bancos: t("bancos", {}),
    acciones: accion("volver") ? { volver: accion("volver") } : {},
  };
}

/**
 * Los importes de una respuesta, **escritos**, para que la pantalla no tenga que calcular nada.
 *
 * La API del banco manda los importes como texto decimal exacto («500.00»), que es lo correcto para
 * guardarlos y **no** es lo que se lee: el agricultor lee «500,00 €». Escribirlos aquí, con `enEuros` y
 * `formateaFecha`, deja el formateo del dinero en **un solo sitio** —el que ya usa toda la aplicación— y
 * hace que la pantalla sea tonta a propósito: no puede sumar, ni redondear, ni enseñar un `0,00 €` donde
 * el dato no consta (`enEuros` devuelve vacío).
 *
 * Se recorre **entero** y por eso no hay que acordarse de ningún campo: el día que la API devuelva un
 * importe nuevo, ya viene escrito.
 */
const CAMPOS_DE_DINERO_DEL_BANCO = [
  "importe",
  "saldo",
  "saldo_final",
  "imputado",
  "por_conciliar",
  "pendiente",
  "total",
  "sobrante",
  "entradas",
  "salidas",
];

function conLosImportesEscritos(valor) {
  if (Array.isArray(valor)) return valor.map(conLosImportesEscritos);
  if (valor && typeof valor === "object") {
    const copia = {};
    for (const [clave, dato] of Object.entries(valor)) copia[clave] = conLosImportesEscritos(dato);
    for (const clave of CAMPOS_DE_DINERO_DEL_BANCO) {
      // `texto_<campo>` es lo que enseña la pantalla. Cuando el dato no consta, `enEuros` devuelve
      // **vacío**, y la pantalla escribe su palabra («No consta», «No lo sé»): nunca un cero.
      if (clave in valor) copia[`texto_${clave}`] = enEuros(valor[clave]);
    }
    if ("fecha" in valor) copia.texto_fecha = valor.fecha ? formateaFecha(valor.fecha) : "";
    if ("vencimiento" in valor) {
      copia.texto_vencimiento = valor.vencimiento ? formateaFecha(valor.vencimiento) : "";
    }
    return copia;
  }
  return valor;
}

/** Abre «el banco y los papeles»: se pinta enseguida y se vuelve a pintar con lo que contesta el servidor. */
async function abrirLosBancos() {
  const suyo = estadoDeLosBancos();
  suyo.error = "";
  suyo.aviso = "";
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.vistaPrevia = null;
  suyo.resultado = null;
  pantallaLosBancos();
  await recargarLosBancos();
  pantallaLosBancos();
}

/** Vuelve a pedir las cuentas, los movimientos y los papeles pendientes. */
async function recargarLosBancos() {
  const suyo = estadoDeLosBancos();
  try {
    const cuentas = await apiJson("/api/bancos/cuentas");
    suyo.cuentas = (cuentas || []).map((cuenta) => ({
      valor: cuenta.id,
      texto: [cuenta.nombre, cuenta.ultimos_digitos ? `·${cuenta.ultimos_digitos}` : ""]
        .filter(Boolean)
        .join(" "),
    }));
    if (!suyo.cuentaElegida && suyo.cuentas.length) suyo.cuentaElegida = suyo.cuentas[0].valor;
    const perfiles = await apiJson("/api/bancos/perfiles");
    suyo.perfiles = (perfiles || []).map((perfil) => ({ valor: perfil.id, texto: perfil.nombre }));
    const consulta = new URLSearchParams();
    if (suyo.cuentaElegida) consulta.set("cuenta_id", suyo.cuentaElegida);
    if (suyo.filtro) consulta.set("texto", suyo.filtro);
    if (suyo.estado) consulta.set("estado", suyo.estado);
    const suyos = consulta.toString();
    suyo.movimientos = conLosImportesEscritos(
      await apiJson(`/api/bancos/movimientos${suyos ? `?${suyos}` : ""}`),
    );
    suyo.pendientes = conLosImportesEscritos(await apiJson("/api/bancos/pendientes"));
    suyo.error = "";
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  return suyo;
}

/** La lista del banco, ya en React. */
function pantallaLosBancos() {
  const suyo = estadoDeLosBancos();
  const movimientos = (suyo.movimientos && suyo.movimientos.items) || [];
  const cuantos = (suyo.movimientos && suyo.movimientos.total) || 0;
  return montar(() =>
    pantallaDeLosBancos({
      textos: textosDeLosBancos(),
      cuentas: suyo.cuentas,
      perfiles: suyo.perfiles,
      cuentaElegida: suyo.cuentaElegida,
      perfilElegido: suyo.perfilElegido,
      ficheroElegido: suyo.nombreDelFichero,
      leyendo: suyo.leyendo,
      importando: suyo.importando,
      guardando: suyo.guardando,
      vistaPrevia: suyo.vistaPrevia,
      resultado: suyo.resultado,
      movimientos,
      agregados: (suyo.movimientos && suyo.movimientos.agregados) || {},
      // El singular y el plural con las dos formas del servidor (`conCuenta` elige `<base>_uno` cuando es
      // uno): «Tienes 1 movimientos» es lo primero que hace desconfiar de un programa.
      resumen: cuantos ? conCuenta(t("tabla", {}), "bancos_resumen", cuantos) : "",
      tabla: tablaDeLosMovimientos(movimientos),
      filtro: suyo.filtro,
      estado: suyo.estado,
      pendientes: suyo.pendientes,
      formulario: elFormularioDeLosBancos(suyo.formulario, suyo.borrador),
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/** La tabla del ordenador: una celda menos que columnas (la última, «Acciones», la pone la pieza). */
function tablaDeLosMovimientos(movimientos) {
  const b = t("bancos", {});
  const col = (clave) => t(`tabla.bancos_${clave}`, "");
  const columnas = [
    { texto: col("fecha"), campo: "fecha" },
    { texto: col("concepto") },
    { texto: col("cuenta") },
    { texto: col("importe") },
    { texto: col("estado") },
    { texto: col("por_conciliar") },
    { texto: t("tabla.acciones", "") },
  ];
  const filas = (movimientos || []).map((movimiento) => ({
    celdas: [
      { texto: movimiento.texto_fecha },
      { texto: movimiento.concepto, accion: "banco-abrir", datos: { id: movimiento.id } },
      { texto: movimiento.cuenta || b.no_consta },
      // **Un importe que no consta se enseña con su palabra, no con un cero.**
      {
        texto:
          movimiento.importe === null || movimiento.importe === undefined
            ? b.no_consta
            : movimiento.texto_importe,
      },
      { texto: b[`estado_${movimiento.estado}`] },
      {
        texto:
          movimiento.por_conciliar === null || movimiento.por_conciliar === undefined
            ? b.no_se_sabe
            : movimiento.texto_por_conciliar,
      },
    ],
    acciones: [
      {
        etiqueta: col("abrir"),
        accion: "banco-abrir",
        datos: { id: movimiento.id },
        clase: "boton-claro",
      },
    ],
  }));
  if (!filas.length) return null;
  return {
    clave: "bancos",
    etiqueta: t("tabla.bancos_etiqueta", ""),
    columnas,
    filas,
    resumen: "",
  };
}

/**
 * Abre la ficha de un movimiento: **pide sus propuestas al servidor**.
 *
 * Es lo que hace que esta pantalla se pueda enlazar y recargar: no vive de la lista que había antes, pide
 * sus datos a su puerta. Si esa puerta no contesta (sin cobertura), se dice **que no se ha podido
 * comprobar**, que no es lo mismo que decir que ese movimiento no está.
 */
async function abrirUnMovimientoDelBanco(id) {
  const suyo = estadoDeLosBancos();
  if (!id) return abrirLosBancos();
  suyo.movimiento = null;
  suyo.propuestas = null;
  suyo.conciliado = null;
  suyo.deshacer = false;
  suyo.correccion = null;
  suyo.error = "";
  suyo.aviso = "";
  pantallaUnMovimientoDelBanco();
  try {
    const datos = conLosImportesEscritos(await apiJson(`/api/bancos/movimientos/${id}/propuestas`));
    suyo.propuestas = datos;
    suyo.movimiento = datos.movimiento;
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  pantallaUnMovimientoDelBanco();
}

/** La ficha de un movimiento, ya en React. */
function pantallaUnMovimientoDelBanco() {
  const suyo = estadoDeLosBancos();
  const suyo2 = suyo.propuestas || {};
  const movimiento = suyo.movimiento || {};
  const pendientes = suyo2.pendientes || [];
  return montar(() =>
    pantallaDeUnMovimiento({
      textos: textosDeLosBancos(),
      movimiento,
      propuestas: suyo2.propuestas || [],
      pendientes,
      papeles: losPapelesParaElegir(pendientes),
      parejas: lasParejasDelTraspaso(movimiento),
      formulario: elFormularioDeLosBancos(suyo.correccion, suyo.borrador),
      resultado: suyo.conciliado,
      deshecho: suyo.deshacer,
      guardando: suyo.guardando,
      cargando: !suyo.movimiento && !suyo.error,
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/** Los papeles a los que se puede apuntar dinero, para el desplegable de «apuntarlo a mano». */
function losPapelesParaElegir(pendientes) {
  const b = t("bancos", {});
  return (pendientes || []).map((papel) => ({
    valor: `${papel.clase}:${papel.documento_id}`,
    texto: [papel.que_es, papel.contraparte, papel.referencia, `${b.le_falta} ${papel.texto_pendiente}`]
      .filter(Boolean)
      .join(" · "),
  }));
}

/**
 * Los movimientos de **otras cuentas tuyas**, para atar un traspaso (A07).
 *
 * Lo que se filtra aquí es solo «de otra cuenta»: **el resto lo comprueba el servidor** y lo dice con su
 * frase («tienen que ser del mismo importe y uno tiene que entrar y el otro salir»). Filtrar el importe en
 * el navegador sería comparar dinero donde no toca; que decida quien tiene el dato.
 */
function lasParejasDelTraspaso(movimiento) {
  const suyo = estadoDeLosBancos();
  const items = (suyo.movimientos && suyo.movimientos.items) || [];
  return items
    .filter((otro) => otro.id !== movimiento.id && otro.cuenta_id !== movimiento.cuenta_id)
    .map((otro) => ({
      valor: otro.id,
      texto: [otro.texto_fecha, otro.concepto, otro.texto_importe].filter(Boolean).join(" · "),
    }));
}

/** El formulario que esté abierto, con sus bloques: el alta de una cuenta, el perfil o la corrección. */
function elFormularioDeLosBancos(cual, borrador) {
  if (!cual) return null;
  const b = t("bancos", {});
  const br = borrador || {};
  const opcionesDe = (lista, elegido) =>
    (lista || []).map((uno) => ({ valor: uno.valor, texto: uno.texto, elegido: uno.valor === elegido }));
  const base = {
    guardar: b.guardar,
    cancelar: b.cancelar,
    guardando: b.guardando,
    datos: { clase: cual.clase, id: cual.id || "" },
    bloques: [],
  };
  if (cual.clase === "cuenta") {
    return {
      ...base,
      titulo: b.form_cuenta_titulo,
      pista: b.form_cuenta_pista,
      bloques: [
        { tipo: "texto", id: "banco-cuenta-nombre", etiqueta: b.cuenta_nombre, pista: b.cuenta_nombre_pista, valor: "" },
        { tipo: "texto", id: "banco-cuenta-banco", etiqueta: b.cuenta_banco, pista: b.cuenta_banco_pista, valor: "" },
        { tipo: "texto", id: "banco-cuenta-ultimos", etiqueta: b.cuenta_ultimos, pista: b.cuenta_ultimos_pista, valor: "" },
      ],
    };
  }
  if (cual.clase === "perfil") {
    return {
      ...base,
      titulo: b.form_perfil_titulo,
      pista: b.form_perfil_pista,
      bloques: [
        { tipo: "texto", id: "banco-perfil-nombre", etiqueta: b.perfil_nombre, pista: b.perfil_nombre_pista, valor: "" },
        {
          tipo: "opciones",
          campo: "formato_de_fecha",
          etiqueta: b.perfil_fecha,
          elegido: br.formato_de_fecha || "",
          opciones: opcionesDe([
            { valor: "d/m/Y", texto: b.fecha_dmy },
            { valor: "m/d/Y", texto: b.fecha_mdy },
          ], br.formato_de_fecha),
        },
        {
          tipo: "opciones",
          campo: "decimal",
          etiqueta: b.perfil_decimal,
          elegido: br.decimal || "",
          opciones: opcionesDe([
            { valor: ",", texto: b.decimal_coma },
            { valor: ".", texto: b.decimal_punto },
          ], br.decimal),
        },
        {
          tipo: "opciones",
          campo: "sin_signo_quiere_decir",
          etiqueta: b.perfil_sin_signo,
          elegido: br.sin_signo_quiere_decir || "",
          opciones: opcionesDe([
            { valor: "entra", texto: b.sin_signo_entra },
            { valor: "sale", texto: b.sin_signo_sale },
          ], br.sin_signo_quiere_decir),
        },
      ],
    };
  }
  if (cual.clase === "correccion") {
    return {
      ...base,
      titulo: b.form_correccion_titulo,
      pista: b.form_correccion_pista,
      bloques: [
        { tipo: "numero", id: "banco-importe", etiqueta: b.correccion_importe, pista: b.correccion_importe_pista, valor: "" },
        {
          tipo: "opciones",
          campo: "signo",
          etiqueta: b.correccion_signo,
          elegido: br.signo || "",
          opciones: opcionesDe([
            { valor: "entra", texto: b.signo_entra },
            { valor: "sale", texto: b.signo_sale },
          ], br.signo),
        },
        { tipo: "texto", id: "banco-concepto", etiqueta: b.correccion_concepto, valor: "" },
        { tipo: "texto", id: "banco-motivo", etiqueta: b.correccion_motivo, pista: b.correccion_motivo_pista, valor: "" },
      ],
    };
  }
  return null;
}

/** Lee el extracto **sin guardar nada**: el fichero, la cuenta y (si la hay) la forma de escribir. */
async function leerElExtracto() {
  const suyo = estadoDeLosBancos();
  const casilla = document.getElementById("banco-fichero");
  const cuenta = valorDeLaCasilla("banco-cuenta");
  suyo.error = "";
  suyo.aviso = "";
  if (!casilla || !casilla.files || !casilla.files.length) {
    suyo.error = t("bancos.fichero", "");
    return pantallaLosBancos();
  }
  if (!cuenta) {
    suyo.error = t("bancos.elige_la_cuenta", "");
    return pantallaLosBancos();
  }
  // Sin cobertura no se puede subir un fichero de un tirón: se dice claro en vez de dejar al agricultor
  // esperando una barra que no avanza.
  if (!navigator.onLine) {
    suyo.error = aviso("no_se_pudo");
    return pantallaLosBancos();
  }
  // **El fichero se guarda antes de pintar**: repintar borra la casilla, y este objeto es lo único que
  // queda del fichero que el agricultor ha elegido.
  suyo.fichero = casilla.files[0];
  suyo.nombreDelFichero = casilla.files[0].name || "";
  suyo.cuentaElegida = cuenta;
  suyo.leyendo = true;
  pantallaLosBancos();
  const cuerpo = new FormData();
  cuerpo.append("fichero", suyo.fichero);
  cuerpo.append("cuenta_id", cuenta);
  if (suyo.perfilElegido) cuerpo.append("perfil_id", suyo.perfilElegido);
  try {
    const respuesta = await fetch("/api/bancos/extractos/vista-previa", {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      throw new Error((detalle && detalle.detail) || mensaje("no_se_pudo"));
    }
    suyo.vistaPrevia = conLosImportesEscritos(await respuesta.json());
    suyo.resultado = null;
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.leyendo = false;
  pantallaLosBancos();
}

/**
 * Apunta los movimientos del extracto. **Solo se llega aquí pulsando APUNTAR ESTOS MOVIMIENTOS**: leer no
 * ha guardado nada, y el fichero que se manda es **el que se guardó al leerlo** (la casilla ya no existe).
 */
async function importarElExtracto() {
  const suyo = estadoDeLosBancos();
  if (!suyo.fichero || !suyo.cuentaElegida) return leerElExtracto();
  suyo.importando = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaLosBancos();
  const cuerpo = new FormData();
  cuerpo.append("fichero", suyo.fichero);
  cuerpo.append("cuenta_id", suyo.cuentaElegida);
  if (suyo.perfilElegido) cuerpo.append("perfil_id", suyo.perfilElegido);
  // **La clave de reenvío**: reenviar la misma subida (el móvil sin cobertura) devuelve lo que pasó la
  // primera vez y **no apunta nada dos veces**.
  if (!suyo.claveDeLaSubida) suyo.claveDeLaSubida = claveDeReenvio("extracto");
  cuerpo.append("clave_de_reenvio", suyo.claveDeLaSubida);
  try {
    const respuesta = await fetch("/api/bancos/extractos/importar", {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      throw new Error((detalle && detalle.detail) || mensaje("no_se_pudo"));
    }
    suyo.resultado = conLosImportesEscritos(await respuesta.json());
    suyo.vistaPrevia = null;
    suyo.fichero = null;
    suyo.nombreDelFichero = "";
    suyo.claveDeLaSubida = null;
    await recargarLosBancos();
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.importando = false;
  pantallaLosBancos();
}

/** Baja el extracto en un fichero, como `sacarDatos()`: con el token y por un enlace de descarga. */
async function exportarElExtracto() {
  const suyo = estadoDeLosBancos();
  try {
    const consulta = suyo.cuentaElegida ? `?cuenta_id=${suyo.cuentaElegida}` : "";
    const respuesta = await api(`/api/bancos/movimientos.csv${consulta}`);
    if (!respuesta.ok) throw new Error(mensaje("no_se_pudo"));
    const blob = await respuesta.blob();
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(blob);
    enlace.download = "extracto.csv";
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
  } catch (fallo) {
    avisarDelError(fallo.message);
  }
}

/** Guarda lo que haya abierto: la cuenta, la forma de escribir del banco o la corrección de un importe. */
async function guardarLosBancos(datos) {
  const suyo = estadoDeLosBancos();
  const clase = (datos && datos.clase) || "";
  const id = datos && datos.id ? Number(datos.id) : null;
  const br = suyo.borrador || {};
  suyo.guardando = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaLosBancos();
  try {
    if (clase === "cuenta") {
      await apiJson("/api/bancos/cuentas", {
        method: "POST",
        body: JSON.stringify({
          nombre: valorDeLaCasilla("banco-cuenta-nombre"),
          banco: valorDeLaCasilla("banco-cuenta-banco") || null,
          // Solo los cuatro últimos: el servidor los recorta otra vez, y aquí se dice para que se vea
          // que el número entero no viaja.
          ultimos_digitos: valorDeLaCasilla("banco-cuenta-ultimos") || null,
          clave_de_reenvio: claveDeReenvio("cuenta"),
        }),
      });
    } else if (clase === "perfil") {
      await apiJson("/api/bancos/perfiles", {
        method: "POST",
        body: JSON.stringify({
          nombre: valorDeLaCasilla("banco-perfil-nombre"),
          cuenta_id: suyo.cuentaElegida || null,
          formato_de_fecha: br.formato_de_fecha || null,
          decimal: br.decimal || null,
          sin_signo_quiere_decir: br.sin_signo_quiere_decir || null,
        }),
      });
    } else if (clase === "correccion") {
      const importe = valorDeLaCasilla("banco-importe");
      await apiJson(`/api/bancos/movimientos/${id}`, {
        method: "PUT",
        body: JSON.stringify({
          // **Un importe vacío viaja como `null`** («déjalo en no lo sé»), nunca como 0.
          importe: importe || null,
          signo: br.signo || null,
          concepto: valorDeLaCasilla("banco-concepto") || null,
          motivo: valorDeLaCasilla("banco-motivo") || null,
        }),
      });
    }
    suyo.formulario = null;
    suyo.correccion = null;
    suyo.borrador = null;
    await recargarLosBancos();
    if (suyo.movimiento) await abrirUnMovimientoDelBanco(suyo.movimiento.id);
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.guardando = false;
  if (suyo.movimiento) {
    pantallaUnMovimientoDelBanco();
  } else {
    pantallaLosBancos();
  }
}

/**
 * Cuadra un movimiento contra los papeles que el agricultor ha elegido.
 *
 * **Las imputaciones son las suyas, no las nuestras**: cuando pulsa APUNTAR ESTA se mandan **las de esa
 * propuesta, tal cual y en el orden del servidor** (el botón lleva su índice, y aquí se busca en la misma
 * lista que se le enseñó); y cuando apunta a mano se manda **un** papel, con la cantidad que haya escrito
 * o con `importe: null`, que es «reparte tú lo que quepa, del papel más antiguo al más nuevo».
 */
async function conciliarUnMovimiento(imputaciones) {
  const suyo = estadoDeLosBancos();
  if (!suyo.movimiento || !imputaciones.length) return;
  suyo.guardando = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaUnMovimientoDelBanco();
  try {
    const contestado = conLosImportesEscritos(
      await apiJson(`/api/bancos/movimientos/${suyo.movimiento.id}/conciliar`, {
        method: "POST",
        body: JSON.stringify({ imputaciones }),
      }),
    );
    suyo.conciliado = contestado;
    suyo.deshacer = false;
    suyo.movimiento = contestado.movimiento;
    await abrirUnMovimientoDelBanco(suyo.movimiento.id);
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.guardando = false;
  pantallaUnMovimientoDelBanco();
}

/** Las 20 acciones de los botones de estas dos pantallas. */
async function atenderLosBancos(nombre, elemento) {
  const suyo = estadoDeLosBancos();
  const id = Number(elemento.dataset.id || 0);
  if (nombre === "banco-ver") return pantallaLosBancos();
  if (nombre === "banco-leer") return leerElExtracto();
  if (nombre === "banco-importar") return importarElExtracto();
  if (nombre === "banco-exportar") return exportarElExtracto();
  if (nombre === "banco-abrir") return abrirUnMovimientoDelBanco(id);
  if (nombre === "banco-cuenta-nueva") {
    suyo.formulario = { clase: "cuenta" };
    suyo.borrador = {};
    return pantallaLosBancos();
  }
  if (nombre === "banco-perfil-nuevo") {
    suyo.formulario = { clase: "perfil" };
    suyo.borrador = {};
    return pantallaLosBancos();
  }
  if (nombre === "banco-guardar") return guardarLosBancos(elemento.dataset);
  if (nombre === "banco-cancelar") {
    suyo.formulario = null;
    suyo.correccion = null;
    suyo.borrador = null;
    return suyo.movimiento ? pantallaUnMovimientoDelBanco() : pantallaLosBancos();
  }
  if (nombre === "banco-elegir") {
    suyo.borrador = { ...(suyo.borrador || {}), [elemento.dataset.campo]: elemento.dataset.valor };
    return suyo.movimiento && suyo.correccion
      ? pantallaUnMovimientoDelBanco()
      : pantallaLosBancos();
  }
  if (nombre === "banco-descartar") {
    suyo.vistaPrevia = null;
    suyo.fichero = null;
    suyo.nombreDelFichero = "";
    suyo.claveDeLaSubida = null;
    return pantallaLosBancos();
  }
  if (nombre === "banco-buscar") {
    suyo.filtro = valorDeLaCasilla("banco-buscar");
    suyo.estado = valorDeLaCasilla("banco-estado");
    await recargarLosBancos();
    return pantallaLosBancos();
  }
  if (nombre === "banco-ver-todos") {
    suyo.filtro = "";
    suyo.estado = "";
    await recargarLosBancos();
    return pantallaLosBancos();
  }
  if (nombre === "banco-conciliar-propuesta") {
    const indice = Number(elemento.dataset.indice || 0);
    const propuesta = ((suyo.propuestas || {}).propuestas || [])[indice];
    if (!propuesta) return pantallaUnMovimientoDelBanco();
    return conciliarUnMovimiento(propuesta.imputaciones);
  }
  if (nombre === "banco-conciliar-a-mano") {
    const elegido = valorDeLaCasilla("banco-papel");
    if (!elegido) return pantallaUnMovimientoDelBanco();
    const corte = elegido.indexOf(":");
    const cantidad = valorDeLaCasilla("banco-cantidad");
    return conciliarUnMovimiento([
      {
        clase: elegido.slice(0, corte),
        documento_id: Number(elegido.slice(corte + 1)),
        // Vacío es «reparte tú lo que quepa», que es lo que hace el servidor por orden.
        importe: cantidad || null,
      },
    ]);
  }
  if (nombre === "banco-deshacer") {
    suyo.guardando = true;
    suyo.error = "";
    suyo.aviso = "";
    pantallaUnMovimientoDelBanco();
    try {
      const contestado = conLosImportesEscritos(
        await apiJson(`/api/bancos/movimientos/${id}/desconciliar`, {
          method: "POST",
          body: JSON.stringify({ imputaciones: [] }),
        }),
      );
      suyo.conciliado = contestado;
      suyo.deshacer = true;
      suyo.movimiento = contestado.movimiento;
      await abrirUnMovimientoDelBanco(id);
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    suyo.guardando = false;
    return pantallaUnMovimientoDelBanco();
  }
  if (nombre === "banco-traspaso-atar" || nombre === "banco-traspaso-quitar") {
    const otro = nombre === "banco-traspaso-quitar" ? null : Number(valorDeLaCasilla("banco-pareja"));
    if (nombre === "banco-traspaso-atar" && !otro) return pantallaUnMovimientoDelBanco();
    suyo.guardando = true;
    suyo.error = "";
    pantallaUnMovimientoDelBanco();
    try {
      const contestado = conLosImportesEscritos(
        await apiJson(`/api/bancos/movimientos/${id}/traspaso`, {
          method: "POST",
          body: JSON.stringify({ otro_movimiento_id: otro }),
        }),
      );
      suyo.aviso = (contestado.avisos || []).join(" ");
      suyo.movimiento = contestado.movimiento;
      await abrirUnMovimientoDelBanco(id);
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    suyo.guardando = false;
    return pantallaUnMovimientoDelBanco();
  }
  if (nombre === "banco-corregir") {
    suyo.correccion = { clase: "correccion", id };
    suyo.borrador = {};
    return pantallaUnMovimientoDelBanco();
  }
}
```

Y en el manejador de clics (donde están las ramas de las cuentas), **una línea**:

```js
  if (nombre.startsWith("banco-")) return atenderLosBancos(nombre, elemento);
```

> **Ojo con el orden de esa línea.** Va **antes** de las que empiezan por otros prefijos y da igual dónde
> esté dentro del manejador, porque `banco-` no lo usa ninguna otra acción del programa. Lo que **no** se
> puede es dejar las 20 ramas sin escribir: el guardián `test_los_botones_hacen_algo.py` lee las acciones
> del código y exige que todas tengan quien las atienda (hoy las 19 nuevas están sin atender, y por eso esa
> prueba está roja).

#### 3.4.4. `backend/app/textos.py` — la tabla y la entrada desde las cuentas

Las columnas de la tabla del ordenador, que las lee `app.js` (`t("tabla.bancos_…")`). Van dentro del
diccionario `TABLA` que ya existe, junto a las de las cuentas (`cuentas_concepto`, …):

```python
    # --- La tabla de los movimientos del banco (T20, 06/10/2026) ---
    "bancos_etiqueta": "Los movimientos del banco, en una tabla",
    "bancos_fecha": "El día",
    "bancos_concepto": "Qué fue",
    "bancos_cuenta": "La cuenta",
    "bancos_importe": "El importe",
    "bancos_estado": "Cómo está",
    "bancos_por_conciliar": "Le queda por cuadrar",
    "bancos_abrir": "¿CONTRA QUÉ PAPEL VA?",
    # El pie de la lista, con singular y plural (`conCuenta` busca `<base>_uno` y `<base>`, y rellena
    # `{cuantos}`): «Tienes 1 movimientos» es lo primero que hace desconfiar de un programa.
    "bancos_resumen_uno": "Tienes 1 movimiento",
    "bancos_resumen": "Tienes {cuantos} movimientos",
```

Y el botón para **entrar** en la pantalla desde las cuentas (que es el renglón del menú del que sale), en el
diccionario `GASTOS`, con los demás botones de abajo:

```python
    "los_bancos": "EL BANCO Y LOS PAPELES",
```

con su botón en `backend/web/react/pantallas/gastos.js`, en la `barra-acciones` del final de
`PantallaDeLasCuentas` (después del de las ayudas):

```js
      <${Boton} etiqueta=${g.los_bancos} accion="bancos-ver" clase="boton-claro" />
```

y su rama en el manejador de clics de `app.js`:

```js
  if (nombre === "bancos-ver") return abrirLosBancos();
```

> **Por qué así y no un renglón nuevo en el menú**: S14 es una sección **de las cuentas** (el contrato la
> dibuja dentro de `/cuentas`), y un renglón propio en el menú competiría con «Mis cuentas» para decir lo
> mismo desde dos sitios. El botón deja la pantalla a un toque del renglón del menú de las cuentas, que es
> lo que pide el encargo.

### 3.5. `backend/web/service-worker.js` — la caché del campo

Una línea en `FICHEROS`, junto a las de las demás pantallas:

```js
  // El extracto del banco y la conciliación (T20, 06/10/2026): la lista de movimientos y la ficha de uno.
  // Va a la caché por lo de siempre —una pantalla que no está guardada es un hueco sin cobertura— y aquí
  // con un motivo propio: el extracto se sube **cuando el agricultor tiene el fichero a mano** (en el
  // despacho, o en la nave con el portátil), y esa es justo la situación en la que la cobertura falla.
  "/react/pantallas/bancos.js",
```

**Y hay que subir el número de la caché** (hoy `cuedigital-2026-10-05-69` → `cuedigital-2026-10-06-70`),
porque si no, un agricultor que abra la aplicación sin cobertura después del despliegue se queda con el
`app.js` nuevo pidiendo un fichero que su móvil no tiene:

```js
const CACHE = "cuedigital-2026-10-06-70";
```

### 3.6. `docs/REACT.md` — la tabla del apartado 3

Una fila, con el formato exacto que lee la prueba (`` `pantallas/<nombre>.js`) | ✅ En React ``), al final de
la tabla:

```markdown
| **El banco y los papeles, y la ficha de un movimiento** (`backend/web/react/pantallas/bancos.js`) | ✅ En React (T20) |
```

Y un párrafo contando lo que trae esta pantalla y lo que **no** hace, como el que se le escribió al T14:

```markdown
**Y desde el T20 (06/10/2026) son cincuenta y dos**: entra **un fichero con dos pantallas** —
`bancos.js`: la lista de los movimientos del extracto, con lo que se ha leído **sin apuntar nada**, las
líneas que no se han entendido con su motivo y su número de línea, y lo que queda por cuadrar de los dos
lados; y la ficha de un movimiento, que es donde se dice **contra qué papel va**— con sus propuestas y su
porqué, el apunte a mano, el deshacer y el traspaso entre cuentas propias. Va a la caché del campo, que
sube a la **versión 70**, y la versión del pie se puso al día en el mismo cambio.
**Lo que esta pantalla NO hace, y conviene que quede escrito aquí**: **no se conecta a ningún banco** (no
hay claves, ni direcciones, ni un sitio donde poner una credencial: solo se lee el fichero que el
agricultor ha subido, y hay una prueba del servidor que lo comprueba), y **no crea ningún documento al
conciliar** (conciliar escribe un vínculo con un papel que ya existe: no hay ninguna acción que cree un
gasto, una factura o un cobro).
```

Y la cuenta que exige `test_la_guia_dice_en_que_punto_esta_la_migracion` sigue con su palabra
(«veintiocho») donde está: **no se toca**.

### 3.7. `tests_js/interfaz.test.js` — la prueba que pide la pantalla a React

Ese fichero es de otro encargo y **no lo he tocado**. Lo que hay que añadirle cuando se integre, siguiendo
lo que ya hace con las otras pantallas migradas, es **una prueba por pantalla** que compruebe, con
`montajes`, que **se le pide a React** con los datos de la aplicación: que abrir `#/cuentas/bancos` monta
`PantallaDeLosBancos` y que abrir `#/cuentas/bancos/5` monta `PantallaDeUnMovimiento` con el id 5. Sin eso,
la pantalla se puede quedar sin ningún recorrido que la pulse desde la aplicación.

---

## 4. Lo que NO he podido comprobar, y por qué

| Qué | Por qué | De quién depende |
|---|---|---|
| **Que la pantalla se vea en un navegador** | No hay navegador en este encargo. Lo que sí se ha comprobado es el HTML que produce React (`renderToStaticMarkup`), botón a botón. **Que se vea bien en un móvil, que se pueda tocar con el dedo y que el agricultor sepa usarla no está comprobado.** | del coordinador: `scripts/comprobar_en_un_navegador.py` (y de la prueba con tres agricultores, como dice `docs/REACT.md`) |
| **Que `app.js` funcione** | El bloque del apartado 3.4 **no está en el árbol** (es de un fichero compartido) y **ningún test lo ejecuta**: `interfaz.test.js` no lo carga, y la suite de JavaScript no ejecuta `app.js` contra un DOM. Está escrito copiando las formas que ya funcionan (el POST con `FormData` de «guardar un papel», el `PUT` de un gasto, la descarga de `sacarDatos()`), pero **no se ha ejecutado ni una línea**. | del coordinador, que es quien lo integra y puede correr la comprobación del navegador |
| **Los cinco rojos de Python del apartado 2.3** | Son de integración pendiente (las tres listas de la migración, la caché del campo y las 19 acciones sin atender). **No se han arreglado** porque arreglarlos exige tocar ficheros compartidos. | del coordinador |
| **La suite de Python entera** | El encargo dice que no hace falta (hay otros agentes en el árbol). Solo he corrido los dos guardianes que **mi fichero** pone en rojo, y están dichos uno por uno. | — |
| **Que el recorrido funcione contra un servidor de verdad** | No he levantado el servidor ni he llamado a las 16 rutas. El recorrido que el servidor sí tiene comprobado es el del informe del T20 (`docs/T20_EXTRACTOS.md`, §8.2: 48 comprobaciones en verde) y **esta pantalla está escrita contra esos esquemas, leídos uno por uno**. | — |
| **El deshacer con motivo propio** | **La puerta no acepta ningún motivo**: `ConciliacionEntrada` solo lleva `imputaciones`, y el servidor escribe siempre «Se deshizo a mano» en `motivo_del_deshacer`. El encargo pedía «deshacer con su motivo», así que **lo digo en vez de pedirlo en pantalla y tirarlo**: pedir un motivo y no mandarlo sería una mentira en la pantalla. Hoy la pantalla **no lo pide** y enseña la frase que dice que queda dicho quién y cuándo. Si se quiere el motivo del agricultor, hace falta un cambio en el servidor (bloque opcional abajo). | del coordinador (decisión) |
| **El «¿por qué no?» de un movimiento ya conciliado** | `extractos.por_que_no_se_puede_conciliar` tiene dos razones hoy (`no_consta_el_importe` y `es_un_traspaso_entre_cuentas_tuyas`); las otras dos constantes (`ya_esta_conciliado` y `no_hay_nada_pendiente_de_esa_clase`) existen en el módulo pero ese camino no las devuelve. La pantalla traduce las dos que sí salen; si algún día sale otra, saldría en blanco (y por eso hay una prueba que recorre la familia entera: la que se añada tiene que añadirse a los textos). | del servidor, si cambia |
| **El deshacer de un solo papel** | La puerta acepta imputaciones concretas (`{imputaciones: [{clase, documento_id}]}`), pero **no hay ninguna ruta que devuelva las conciliaciones vivas de un movimiento**, así que la pantalla **no puede enseñarlas** para elegir cuál se deshace. Lo que hace es deshacer **todo lo apuntado** de ese movimiento (que es el caso normal) y decir lo que ha vuelto a quedar pendiente. **Si se quiere deshacer uno solo, hace falta una ruta que las liste.** | del coordinador / de un ticket de servidor |
| **La columna `pareja_de_traspaso_id` de la lista** | El servidor la devuelve y la pantalla usa `es_traspaso_propio` para decir «es un traspaso»; el identificador del par no se enseña porque el otro movimiento puede estar en otra pantalla (y su nombre no viene en la respuesta). | — |

### 4.1. Bloque **opcional** para el servidor: que el motivo del deshacer sea el del agricultor

Si el coordinador decide que sí (el encargo lo pedía), son dos cambios mínimos y **solo entonces** hay que
pedir el motivo en la pantalla (`banco-motivo-deshacer`) y mandarlo:

```python
# en app/routers/extractos_api.py, esquema de entrada
class ConciliacionEntrada(EntradaBase):
    """A qué papeles se apunta este movimiento. Vacío es «míralo tú y reparte lo que quepa»."""

    imputaciones: list[ImputacionEntrada] = Field(default_factory=list)
    # **Lo que el agricultor escriba al deshacer**, y nulo es «no lo dijo»: entonces se guarda la frase
    # de siempre («Se deshizo a mano»). El T20 ya guarda este motivo en la fila; lo que faltaba era la
    # puerta para que llegara de la pantalla.
    motivo: str | None = Field(default=None, max_length=ANCHO_MOTIVO)
```

```python
# y en `deshacer_la_conciliacion`, donde hoy pone `fila.motivo_del_deshacer = textos.mensaje("T20_deshacer_a_mano")`
        fila.motivo_del_deshacer = datos.motivo or textos.mensaje("T20_deshacer_a_mano")
```

**No lo he dado por hecho**: sin ese cambio, la pantalla no pide el motivo (y hay una prueba que comprueba
que no hay ningún campo `banco-motivo-deshacer`, para que nadie lo añada sin cambiar antes el servidor).

---

## 5. Lo que he decidido y conviene no deshacer

1. **Dos pantallas, un fichero.** La lista y la ficha, con la dirección cada una, y los formularios sin
   dirección. Los datos de la ficha **se piden al abrirla** (sus propuestas), así que se puede enlazar y
   recargar; un formulario que al recargar saliera vacío sería peor que no tenerlo.
2. **Los `texto_*` los pone `app.js` y no la pantalla.** Los `Decimal` viajan como texto decimal exacto
   («500.00»), que no es lo que se lee. Escribirlos en `app.js` con `enEuros` deja **el formateo del dinero
   en un solo sitio** y hace que la pantalla no pueda hacer ni una cuenta: hay una prueba que comprueba que
   `bancos.js` no lleva `parseFloat`, `parseInt`, `toFixed`, `Number(` ni `Math.`, y que no suma ningún
   `importe`. **La alternativa —que la pantalla importe `formateaNumero` de `nucleo.js`— también valdría
   (lo hace `hecho.js` con las fechas), pero entonces el «0,00 € cuando no consta» viviría en dos sitios.**
3. **La pantalla mira el dato crudo, no el texto.** `importe === null` (y no «si el texto está vacío») es
   lo que decide que salga «No consta». Está escrito así **a propósito y con una prueba que lo muerde**:
   con un `texto_importe` de `0,00 €` y el importe a nulo, la pantalla enseña su palabra y no el cero.
4. **El índice de la propuesta.** El botón de una propuesta lleva **su índice** en la lista del servidor, y
   las propuestas se pintan **en el orden en que llegan**. Ordenarlas por puntuación sería «más bonito» y
   apuntaría el dinero **a otro papel**. Hay una prueba que comprueba que cada índice está dentro de su
   bloque y en orden.
5. **El fichero se guarda en el estado al leerlo.** Repintar la pantalla borra el `<input type="file">`, y
   al apuntar hay que volver a mandar el mismo fichero. Esto ya costó una ronda en este proyecto con el
   cuaderno de la Junta: **no lo «arregles» volviendo a leer la casilla al importar**.
6. **Leer no apunta nada, y el botón de apuntar solo existe con una propuesta delante.** Hay una prueba
   que exige que `banco-importar` **no** esté en el formulario de subir el fichero. Es lo que impide que
   importar dos veces sea un descuido.
7. **Las cuatro familias de claves compuestas** (`estado_…`, `falta_…`, `por_que_no_…`, `propuesta_…`) se
   traducen en la pantalla porque el servidor manda **claves** y no frases. La que falte sale **en blanco
   sin que salte nada**: hay dos pruebas (una que recorre las familias, otra que exige que salgan pintadas)
   y por eso están en `BANCOS` y no repartidas por ahí.
8. **La pantalla no pide el motivo del deshacer** porque la puerta no lo acepta (apartado 4). Y **no pide
   ninguna credencial**: ni clave, ni usuario, ni dirección de banco. Hay una prueba que lo comprueba sobre
   el código.
9. **El traspaso se ata desde la ficha y se propone en la vista previa.** Desde la vista previa **no se
   puede** atar (el servidor propone las parejas por sus claves de duplicado y la puerta que las ata pide
   el identificador del otro movimiento), y en vez de un botón que no puede funcionar hay una frase que
   dice **dónde** se marca.
10. **Las 20 acciones van literales, y el fichero se llama `bancos.js`.** Añadirlo a
    `FICHEROS_CON_ACCION_POR_VARIABLE` sería una mentira: no tiene ninguna acción por variable. Y **ojo con
    su cabecera**: el guardián de esa prueba **no quita los comentarios**, así que escribir ahí el ejemplo
    prohibido hace que cuente el fichero como uno de los que sí lo hacen (pasó, y está contado dentro del
    propio `bancos.js`).
11. **Las dos direcciones son `#/cuentas/bancos` y `#/cuentas/bancos/<id>`**, dentro de la familia de las
    cuentas: es de donde sale (el renglón del menú) y por eso se lee sola. `bancos` **no** entra en
    `LISTADOS`: sus filtros no viajan en la dirección y la lista no recuerda la vista entre la lista y la
    ficha (se puede añadir después sin tocar la pantalla).
