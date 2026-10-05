# REVISIÓN INDEPENDIENTE DEL T12 — Entregas/ventas, importes decimales y cobros parciales (A06/A08)

> **Quién escribe esto y con qué intención.** No soy el agente del ticket: soy el revisor. Lo que sigue
> es **el intento de romper la entrega**, no un resumen de ella. Las doce cosas que cuento como defectos
> las he provocado yo, con el comando delante y la salida literal; lo que **no** he podido romper está
> también, al final, porque eso es la mitad del informe. Todo se ha medido sobre bases temporales: la
> base del agricultor (`backend/cuedigital.db`) **no se ha abierto, ni copiado, ni usado**.

---

## 0. Resumen de una pantalla

| | |
|---|---|
| **Defectos encontrados** | **12**: 3 de gravedad **alta**, 5 **media** y 4 **baja** |
| **Los tres que más me preocupan** | (1) cuatro entradas mal escritas tumban con un **500** el apunte de un ajuste; (2) **nueve campos de texto libre** se pasan del tope de su columna y **en PostgreSQL falla la operación entera** (en SQLite no se nota); (3) un **importe que no cabe en su columna** revienta en PostgreSQL (el mismo `varchar` que ya costó un defecto de producción) |
| **Lo que NO he podido romper** | el A06 (121−40 = 81,00 exactos y **una** sola factura), el A08 por el detalle (importe en blanco, estado, aviso y la factura rechazada con su «qué hacer»), **los decimales** (incluido el que pierde céntimos: 100 cobros de 0,10 € sobre 10,00 €), **el pie que cuadra con las filas** (10.270,00 · 9.970,00 · 5.000,00 · 4.970,00), el reenvío de las cuatro cosas, el aislamiento (catorce puertas, todas 404), la ausencia de promesa fiscal y los cuatro fallos que el informe cuenta como arreglados |
| **Medido hoy** | Python **3.793** pruebas recogidas (suite completa en SQLite: **4 fallos**, los cuatro de recuentos de documentación) · JavaScript **869 pruebas, 0 fallos** · **48** pantallas en React y **48** ficheros · `docs/REACT.md` marca **41** y la documentación dice 3.700 y 867 · **en PostgreSQL, una prueba del propio ticket sale en rojo** (§2, defecto 12) |
| **El árbol se movió a mitad** | `docs/T12_VENTAS.md` (01:18:50) y `tests/test_el_dinero_de_las_ventas.py` (01:09:31) se editaron **después** de empezar esta revisión: el informe pasó de decir «3.792 pruebas» a «3.793», que es lo que mide `pytest`. Los ficheros de código no han cambiado desde las 01:03, así que los defectos están medidos sobre la última versión viva (§6) |

---

## 1. Foto del árbol revisado

Medido el **03/10/2026 a las 01:21:43** (hora local), con `Get-Item` + `Get-FileHash`:

| Fichero | Tamaño | Hora | sha256 (16 primeros) |
|---|---|---|---|
| `backend/app/dinero.py` | 19501 | 23:40:05 | `479E2BE4476CDD32` |
| `backend/app/ventas.py` | 17287 | 22:42:01 | `DB56505CA224A136` |
| `backend/app/routers/ventas_api.py` | 96891 | 01:03:34 | `C1E704BF77BEF90C` |
| `backend/app/models.py` | 154169 | 00:25:13 | `227664A1EC703778` |
| `backend/app/schemas.py` | 121294 | 23:27:36 | `C1BCCCF5D3B4A4FD` |
| `backend/app/textos.py` | 352385 | 00:43:29 | `7FA5ECEED3FE8072` |
| `backend/web/app.js` | 754318 | 00:18:18 | `DBEAA55DACCB8076` |
| `backend/web/react/pantallas/ventas.js` | 11326 | 00:18:23 | `9B9E4863246317DD` |
| `backend/web/react/piezas/tabla.js` | 11628 | 18:42:44 | `20D7FAC32A072929` |
| `backend/tests/test_el_dinero_de_las_ventas.py` | 93830 | 01:09:31 | `208E7903316082C5` |
| `backend/tests_js/react.test.js` | 390054 | 23:19:47 | `1AD57296E1812606` |
| `backend/tests_js/interfaz.test.js` | 660785 | 23:55:04 | `A5DD9D918B0192D1` |
| `docs/T12_VENTAS.md` | 43641 | 01:18:50 | `4056A4A98146C73F` |

> **La base del agricultor, intacta.** `backend/cuedigital.db` no se ha abierto. Las sondas fijan
> `CUEDIGITAL_DATABASE_URL` a una carpeta temporal **o** a una base propia de esta revisión
> (`cuedigital_revision`, `cuedigital_revision_probe`, `cuedigital_revision_rev`,
> `cuedigital_revision_x`), y comprueban `engine.dialect.name` antes de escribir nada. **No he usado
> `cuedigital_pruebas`**, que es la del coordinador: la vi en `pg_stat_activity` desde antes de empezar
> y no la he tocado.

### Cómo se reproduce cada cosa

```powershell
# La suite completa en SQLite (la que sostiene los recuentos)
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests -q --junit-xml=$env:TEMP\rev12_sqlite.xml

# La suite en PostgreSQL (base propia)
docker exec cuedigital-pg createdb -U postgres cuedigital_revision
$env:CUEDIGITAL_SUITE_SOBRE="postgresql+psycopg://postgres:pruebas@127.0.0.1:55432/cuedigital_revision"
..\.venv\Scripts\python.exe -m pytest tests -q --junit-xml=$env:TEMP\rev12.xml

# Lo que solo se ve en PostgreSQL: la suite del ticket, parando en el primer fallo
$env:CUEDIGITAL_SUITE_SOBRE="postgresql+psycopg://postgres:pruebas@127.0.0.1:55432/cuedigital_revision_x"
..\.venv\Scripts\python.exe -m pytest tests/test_el_dinero_de_las_ventas.py -q -x

# Las pruebas de esta revisión (una por defecto), en los dos motores
..\.venv\Scripts\python.exe -m pytest tests/test_revision_t12.py -q
```

Las sondas que usé para provocar los defectos **no viven en el repositorio** (están en
`%TEMP%\t12rev\`: `sonda_t12.py`, `probes*.py`, `render_ventas.mjs`). Lo que sí queda en el repositorio
es la prueba que falla mientras cada defecto exista: `backend/tests/test_revision_t12.py`.

---

## 2. Los doce defectos

> En todos, «lo que debería pasar» está escrito desde el sitio del agricultor: qué ve y qué deja de
> poder hacer. Los tres primeros son **de la misma familia que el `varchar(30)` del rastro**, que es la
> que ya llegó a producción: en SQLite todo verde y en PostgreSQL la operación entera sin hacer.

### DEFECTO 1 — cuatro entradas mal escritas tumban con un **500** el apunte de un ajuste · gravedad **ALTA**

**Qué pasa.** `POST /api/ventas/{venta_id}/ajustes` recibe `datos: dict` —sin esquema— y llama
directamente a `dinero.a_decimal`, `dinero.de_texto` y `dt.date.fromisoformat`. Cuando el valor no le
gusta, la excepción (`ErrorDeDinero`, que es un `ValueError`) **no la recoge nadie**: no hay
`exception_handler` para ella en `main.py`. El servidor contesta **500**. Con cuatro entradas distintas:

**Cómo lo he provocado** (sonda `probes2.py 500`, con el cliente puesto para que no reviente y poder
leer el estado; **idéntico en SQLite y en PostgreSQL**):

```
La caza del 500 (el móvil reintenta los 5xx para siempre)
  ajuste con importe como número de coma flotante: 500 Internal Server Error
  ajuste con importe como texto que no es número: 500 Internal Server Error
  ajuste con cantidad como texto que no es número: 500 Internal Server Error
  ajuste con fecha en castellano: 500 Internal Server Error
  ajuste con cantidad como número: 201 {...}
  ajuste con importe con tres decimales: 201 {...}
  cobro con importe float: 422 {'detail': [{'type': 'value_error', 'loc': ['body', 'importe'],
        'msg': 'Value error, Un importe no se acepta como número de coma flotante: mándalo com...'}]}
  cobro con importe basura: 422 {'detail': [{'type': 'value_error', ...'«cuarenta» no es un importe.'}]}
```

Y sin recoger la excepción, lo que sale del servidor es la traza:

```
app.dinero.ErrorDeDinero: Un importe no se acepta como número de coma flotante: mándalo como texto
decimal (por ejemplo "121.00"). Un Float ya ha perdido céntimos antes de llegar aquí.
```

**Qué debería pasar.** Un **422 con la frase del agricultor**, que es lo que ya hace `POST /api/cobros`
con el mismo cuerpo: allí el esquema (`CobroEntrada`, con su validador) convierte la excepción en un
mensaje, y aquí no hay nada que la pare. De los cinco endpoints del dinero, este es el único que
**recibe un `dict` crudo y además convierte números y fechas dentro** (los de anular también reciben un
`dict`, pero solo leen el motivo, que es texto y no puede reventar).

**Por qué es alta.** Un 5xx no se puede arreglar mandándolo otra vez, y este programa **reintenta los
5xx**: `app.js` (`mandarPendientes`) deja el apunte en la cola y vuelve a mandarlo en cada pasada
—«el servidor está de mal humor: se reintenta luego»—. Y la pantalla del ajuste manda el importe como
texto (así que por ahí no entra), pero **cualquier otro cliente que mande el número como número de JSON
—que es lo natural en JSON— recibe un 500**: un importe que el propio módulo de dinero existe para
rechazar *con un mensaje* acaba en una traza del servidor.

**¿Hay una prueba que lo habría cazado?** No. Las 63 pruebas de `test_el_dinero_de_las_ventas.py`
mandan siempre el importe como cadena (es lo correcto) y las de `tests_js` no llegan al servidor. La
prueba que lo caza está en `tests/test_revision_t12.py::TestDefecto1…` (falla hoy en los dos motores).

---

### DEFECTO 2 — texto de longitud libre en columnas con tope: **nueve campos del dinero** · gravedad **ALTA**

**Qué pasa.** Los campos de texto que rellenan las pantallas nuevas acaban en columnas con tope y
**nadie comprueba que quepan**. **SQLite no comprueba la longitud de un `VARCHAR`** (guarda las 250
letras enteras y contesta 201); **PostgreSQL sí**, y como la fila se escribe en la misma transacción,
**lo que falla entero es la operación**: un `DataError` y un 500, con el apunte sin guardar.

**Cómo lo he provocado.** `python probes3.py` (sonda que manda 250 caracteres en cada campo, con
`sonda_t12.py` fijando la base a un fichero temporal **o** a `cuedigital_revision_probe`), dos veces:

```
                                        SQLite   PostgreSQL
ajuste: evidencia_descripcion (200)       201     500 Internal Server Error
cobro:  referencia            (120)       201     500 Internal Server Error
cobro:  cliente               (200)       201     500 Internal Server Error
factura: numero               (80)        201     500 Internal Server Error
factura: cliente              (200)       201     500 Internal Server Error
factura: cliente_nif          (20)        201     500 Internal Server Error
venta:  comprador             (200)       201     500 Internal Server Error
venta:  numero_albaran        (80)        201     500 Internal Server Error
venta:  clave_de_reenvio      (120)       201     500 Internal Server Error
```

Y lo que hay debajo, literal, en PostgreSQL:

```
psycopg.errors.StringDataRightTruncation: value too long for type character varying(200)
sqlalchemy.exc.DataError: (psycopg.errors.StringDataRightTruncation) value too long for type character varying(200)
[SQL: INSERT INTO ajustes_de_entrega (explotacion_id, venta_id, tipo, fecha, cantidad, unidad, importe,
origen, motivo, evidencia_descripcion, …) VALUES (…)]
```

De los nueve, **siete son columnas nuevas del T12** (`ajustes_de_entrega.evidencia_descripcion`,
`cobros.referencia`, `cobros.cliente`, `facturas_emitidas.numero`, `.cliente`, `.cliente_nif` y
`ventas_de_cosecha.clave_de_reenvio`) y dos son columnas de siempre que ahora se rellenan desde sitios
nuevos (`ventas_de_cosecha.comprador` y `.numero_albaran`).

**Qué debería pasar.** O el endpoint rechaza el texto con una frase (422: «eso es más largo de lo que
cabe»), o lo guarda **cabiendo**. Lo que no puede pasar es admitirlo y guardarlo entero en un sitio
donde no cabe, porque entonces el mismo programa funciona en un motor y no en el otro — que es
exactamente el defecto que el propio informe del T12 cuenta en su §7 y que le costó 67 pruebas en rojo
al proyecto.

**¿Hay una prueba que lo habría cazado?** No, y el guardián que existe **no lo cubre**:
`tests/test_las_etiquetas_del_rastro_caben.py` lee `accion="…"` de `app/**/*.py` (yo lo he ejecutado:
pasa, y las etiquetas del T12 miden entre 5 y 17 caracteres). Los campos de arriba no son etiquetas de
rastro: son **texto del agricultor** que va a una columna con tope, y ahí el guardián no mira. La
prueba que lo caza es `TestDefecto2…`, que recorre los nueve campos y compara con el ancho **declarado
en el modelo** (no con un número escrito a mano). **Está escrito en el informe que PostgreSQL no se
había medido: estos nueve son la factura de no haberlo medido.**

---

### DEFECTO 3 — un importe que no cabe en su columna (`VARCHAR(24)`) revienta en PostgreSQL · gravedad **ALTA**

**Qué pasa.** `dinero.ImporteExacto.impl = String(MAXIMO_DE_CIFRAS)`, con `MAXIMO_DE_CIFRAS = 24`, y
`a_texto` **no mira cuántos caracteres devuelve**. Un importe con 22 cifras enteras se guarda como
`"999999999999999999999999.99"`, que mide **27**:

```
a_texto(99999999999999999999.99)      = '99999999999999999999.99'      len 23
a_texto(999999999999999999999.99)     = '999999999999999999999.99'     len 24
a_texto(999999999999999999999999.99)  = '999999999999999999999999.99'  len 27
a_texto(1e25)                         = '10000000000000000000000000.00' len 29
```

**Cómo lo he provocado** (`python probes2.py grandes`, mismo guion, dos motores):

```
MOTOR: sqlite
  importe=121.00: 201 {...}
  importe=99999999999999999999.99: 201 {...}
  importe=999999999999999999999.99: 201 {...}
  importe=99999999999999999999999999.99: 201 {...}

MOTOR: postgresql
  importe=121.00: 201 {...}
  importe=99999999999999999999.99: 201 {...}
  importe=999999999999999999999.99: 201 {...}
  !!! la sonda grandes reventó: DataError('(psycopg.errors.StringDataRightTruncation)
      value too long for type character varying(24)')
```

Lo mismo con un cobro (`cobro con importe enorme: 500 Internal Server Error` en PostgreSQL, `201` en
SQLite) y con el importe de un ajuste.

**Qué debería pasar.** Que el importe se rechace con una frase antes de tocar la base («ese importe no
puede ser»), o que el texto se recorte a lo que se puede guardar **diciéndolo**. Un 500 con la traza
del motor no es una respuesta para un agricultor.

**¿Hay una prueba que lo habría cazado?** No. Hay una prueba de que la columna guarda **texto**
(`typeof(importe) == 'text'`), que es otra cosa. Y el informe §7 dice expresamente que `importe` es
`VARCHAR(24)`: el número estaba medido; lo que no se midió es **qué pasa cuando el texto no cabe**.

---

### DEFECTO 4 — `GET /api/ventas` no trae las cuentas y dice `facturada: false` de una entrega facturada · gravedad **MEDIA**

**Qué pasa.** `listar_ventas` llama a `con_nombres(db, venta)` **sin pasarle la explotación**
(`ventas_api.py:498`), así que `_las_cuentas_en_la_salida` no se ejecuta y la lista devuelve los campos
del dinero **en su valor por defecto**: `importe_total: None`, `texto_importe: ""`, `cobrado: null`,
`pendiente: null`, `estado: ""`, `etiqueta_estado: ""` y `facturada: false`.

**Cómo lo he provocado** (`python probes2.py lista`): una entrega de 121,00 € dentro de una factura con
40,00 € cobrados, mirada por las tres puertas:

```
fila de la lista: {'importe': '121.00', 'importe_total': None, 'texto_importe': '',
                   'cobrado': None, 'texto_cobrado': '', 'pendiente': None, 'texto_pendiente': '',
                   'estado': '', 'etiqueta_estado': '', 'facturada': False, 'factura_numero': None}
ficha:            {'importe_total': '121.00', 'texto_importe_total': '121,00 €',
                   'texto_cobrado': '40,00 €', 'texto_pendiente': '81,00 €',
                   'estado': 'cobrada_en_parte', 'etiqueta_estado': 'Cobrada en parte'}
tabla fila:       {'importe': '121,00 €', 'cobrado': '40,00 €', 'pendiente': '81,00 €',
                   'estado': 'Cobrada en parte'}
la tabla y la lista dicen lo mismo: False
```

**Qué debería pasar.** Lo mismo que la ficha y que la tabla, que ya coinciden entre sí. Y sobre todo:
**`facturada: false` no es un hueco, es una afirmación falsa** — la peor forma de un dato que no se
sabe, porque el programa no dice «no lo he mirado», dice «no está facturada». (`estado: ""` es un
hueco; `facturada: false` es un no.)

**¿Hay una prueba que lo habría cazado?** No, y es fácil de ver por qué: las pruebas del T12 miran la
**ficha** y la **tabla**, que son las dos puertas que sí funcionan. La prueba está en
`TestDefecto4…`; compara las ocho columnas del dinero entre la lista y la ficha.

> **Nota para valorarlo, y lo digo yo antes de que me lo digan:** hoy ninguna pantalla enseña el
> dinero de esa lista (`pantallaVentas` usa `/api/ventas/tabla`), así que **no hay un sitio donde el
> agricultor esté leyendo un `false` falso ahora mismo**. Lo que hay es una puerta pública que
> contesta mal, y el día que alguien la use para pintar la lista —que es lo que hizo la pantalla hasta
> el T12— la mentira sale a la pantalla. Por eso la pongo media y no alta.

---

### DEFECTO 5 — el rótulo «De dónde» cae encima de los botones, y esa columna no se pinta · gravedad **MEDIA**

**Qué pasa.** La pieza `Tabla` (`web/react/piezas/tabla.js`) pinta **una cabecera por columna** y, al
final de cada fila, **la celda de las acciones**. Por eso todas las tablas del programa escriben **una
celda menos que columnas** y la última columna es la de las acciones (por ejemplo `tablaDeTierras`, que
termina en `{ texto: col("acciones") }`).

En la tabla de S12 eso no se cumple: **el servidor manda doce columnas de datos** (la última, `donde`)
y `pantallaVentas` calcula las celdas con `columnas.slice(0, -1)` — once — **dando por hecho que la
última columna del servidor es la de las acciones, y no lo es**.

**Cómo lo he provocado.** He volcado la tabla **de verdad** (`GET /api/ventas/tabla`, con dos entregas
y un cobro) y he renderizado `PantallaVentas` con `react-dom-server` en Node, copiando el trozo de
`pantallaVentas()` que prepara las columnas y las celdas (`%TEMP%\t12rev\render_ventas.mjs`):

```
COLUMNAS QUE MANDA EL SERVIDOR (12):
  cliente, producto, fecha, cantidad, importe, vencimiento, cobrado, pendiente, estado, partida,
  albaran, donde
CABECERAS QUE SE PINTAN (12):
  ["Cliente","Producto","Fecha","Cantidad","Importe","Vencimiento","Cobrado","Pendiente","Estado",
   "Partida","Albarán","De dónde"]
CELDAS DE LA PRIMERA FILA (12):
  1. Un vecino   2. Cebada   3. 12/07/2026   4. 42.000,00 kg   5. 79,00 €   6. (vacío)
  7. 0,00 €   8. 79,00 €   9. Sin cobrar   10. L-2026-07   11. ALB-2026-118   12. PONER EL IMPORTE

   1. Cliente        | Un vecino
   …
  11. Albarán       | ALB-2026-118
  12. De dónde      | PONER EL IMPORTE      ← el rótulo de una columna de datos, encima de los botones
```

O sea: **el valor de «De dónde» no se pinta nunca en el ordenador** (en la tarjeta del móvil sí) y la
columna de los botones sale con el nombre de otra cosa. El rótulo que falta **ya existe en los textos
del servidor y no lo usa nadie**: `textos.VENTA["tabla_acciones"] = "Acciones"` (`textos.py:2798`);
`grep tabla_acciones` en todo el repositorio lo encuentra **solo ahí**, ni en el Python ni en el
JavaScript.

**Qué debería pasar.** Que la última columna de la tabla sea la de las acciones, con su rótulo, y que
las doce columnas del servidor tengan su celda. El arreglo más corto es añadirla al final de
`COLUMNAS_DE_LA_TABLA` (`ventas_api.py:925`) con el rótulo que ya está escrito.

**¿Hay una prueba que lo habría cazado?** Casi: hay una que comprueba `celdas = columnas − 1`
(`tests_js/interfaz.test.js`, «las celdas de la fila no cuadran con las columnas»), pero **la cuenta
cuadra por casualidad**: once celdas más la de acciones son doce, las mismas que cabeceras. Lo que
ninguna prueba mira es **qué rótulo le toca a la celda de los botones**. La prueba está en
`TestDefecto5…`, y comprueba además que no se arregle quitando «De dónde» del contrato.

---

### DEFECTO 6 — los tres enlaces con la ficha del cliente (`contacto_id`) no tienen puerta · gravedad **MEDIA**

**Qué pasa.** El T12 añade `contacto_id` a la entrega, a la factura y al cobro. El endpoint las valida
(`_comprobar_sitio`, `crear_factura_emitida`, `apuntar_un_cobro`), el modelo las guarda, y el informe
las presenta como la mitad de lo que hace falta para contestar «¿cuánto me debe la cooperativa?» **sin
comparar nombres a ojo** (§3.1). Pero **ninguna pantalla las pregunta**:

```
$ grep -l contacto web/react/pantallas/{ventas,venta_importe,venta_ajuste,facturas_emitidas,
      facturar_entregas,factura_emitida,cobros,cobro_nuevo}.js
(sin resultados: ninguna de las ocho pantallas del dinero nombra el contacto)

$ grep -n contacto_id web/app.js
5278:  contacto_id: venta.contacto_id,               ← devolverlo al corregir (no borrarlo)
12554: contacto_id: entrega.contacto_id,             ← devolverlo al guardar el importe
```

Y los tres sitios donde se manda el cuerpo de la petición no lo llevan: `guardarElImporteDeUnaEntrega`
lo devuelve tal cual (no lo pregunta), y `guardarLaFacturaEmitida` y `guardarElCobro` **no lo mandan
siquiera** (solo mandan el `cliente` de texto libre).

**Qué debería pasar.** Es la regla que `AGENTS.md` §4 llama **el fallo que más veces ha pagado este
proyecto**: «un campo en el modelo sin pantalla que lo pregunte» (el cultivo del año anterior, los
datos de la portada del cuaderno, el campo de la máquina al cosechar). El informe presume en su §3.8 de
que «los cuatro campos del dinero tienen su puerta»: **estos tres enlaces no la tienen**, y el propio
informe dice para qué los quiere.

**¿Hay una prueba que lo habría cazado?** No. `TestDefecto6…` mira `app.js` y exige que las tres
pantallas lean el contacto de un campo del formulario —una puerta de verdad— y no que lo devuelvan.

---

### DEFECTO 7 — 28 de las 30 acciones nuevas del dinero no se pulsan en ninguna prueba · gravedad **MEDIA**

**Qué pasa.** `tests_js/react.test.js` comprueba los botones nuevos **mirando el HTML** (una expresión
regular sobre `data-accion="…"`), que solo demuestra que están pintados. Contadas una por una, las
acciones del T12 que el manejador de clics de `app.js` sabe atender son **30**, y las que alguna prueba
pulsa de verdad son **2**:

```
acciones del dinero en el manejador de app.js: 30
se pulsan en algún tests_js:  ventas-nueva, ventas-ver
NO se pulsan (28): ajuste-anular, ajuste-anular-si, ajuste-elegir-origen, ajuste-elegir-tipo,
  ajuste-guardar, cobro-anular, cobro-anular-si, cobro-conciliar, cobro-conciliar-con,
  cobro-desconciliar, cobro-guardar, cobro-nuevo, cobros-ver, factura-emitida-abrir,
  factura-emitida-anular, factura-emitida-anular-si, factura-emitida-guardar, factura-emitida-nueva,
  facturar-marcar, facturas-emitidas-ver, venta-ajuste, venta-importe, venta-importe-guardar,
  ventas-buscar, ventas-facturar, ventas-solo-pendientes, ventas-solo-sin-importe, ventas-ver-todas
```

**Y una cosa que sí he comprobado, para que se lea entera:** las **20 funciones** que esos botones
llaman (`pantallaImporteDeUnaEntrega`, `guardarElCobro`, `conciliarUnCobro`, `pantallaFacturarEntregas`,
…) **existen** en `app.js`. O sea que hoy no hay ningún botón roto: lo que falta es **la prueba que lo
demuestre**. Es el mismo hueco que en el T10 escondió una acción sin cablear y que en el T11 dejó las
cuatro pantallas de contactos sin ejecutar ni una vez.

**Qué debería pasar.** Que cada acción nueva se pulse en `tests_js` con el manejador delegado que lee
`data-accion` (`pulsar(entorno, "…")`), como ya se hace con las del T09. `TestDefecto7…` lo exige: saca
la lista de acciones del propio `app.js` (sin listas a mano) y comprueba que todas se pulsan.

---

### DEFECTO 8 — el pie convierte «no se sabe» en `0,00 €` · gravedad **BAJA**

**Qué pasa.** El A08 lo dice con estas palabras: «cantidad conocida, importe pendiente; **no ingreso
cero**». La fila lo cumple; **el pie y los totales no**. Con una sola entrega de 8.000 kg sin precio:

```
tabla pie:   1 entrega · 0,00 € · pendiente 0,00 €
totales:     {'importe': '0.00', 'facturado': '0.00', 'cobrado': '0.00', 'pendiente': '0.00',
              'entregas': 1, 'sin_importe': 1, 'por_cobrar': 0}
avisos:      ["A 1 entrega le falta el importe, así que no entra en estas cuentas."]
fila:        importe '' | importe_valor None | estado 'Falta el importe'
```

**Lo que salva a medias, y por eso es baja:** el aviso **sí** está y se pinta justo al lado del pie
(`ventas.js:188`), así que el agricultor puede leer por qué ese cero no es un cero. Pero el número más
grande de la pantalla dice «0,00 €» de un año entero del que no se sabe nada, y el informe §3.5 vende
lo contrario: «un total que suma lo que hay y calla que le faltan importes parece que cuadra, y no
cuadra» — aquí no lo calla, pero **el total sigue estando en cero**, y el A08 lo prohíbe. Cero y «no lo
sé» no son lo mismo.

**Dónde NO se cuela el cero** (lo he buscado, que era la mitad del encargo): la fila de la tabla deja el
importe **vacío** y `importe_conocido: false`; `/api/ventas` y `/api/ventas/{id}` devuelven `None` y
`""`; `/api/ventas/informe` **no lleva dinero**; y el **CSV y el PDF del cuaderno** (`/api/cuaderno/…`)
llevan producto, cantidad, fecha, lote, comprador y albarán, pero **ni un importe** — así que ahí no
hay ningún cero que interpretar. El único sitio es el pie.

**¿Hay una prueba que lo habría cazado?** No: `test_no_aparece_como_ingreso_de_cero_euros` mira la
**fila** y el **aviso**, no el pie. `TestDefecto8…` mira el pie.

---

### DEFECTO 9 — un cobro que redondea a cero se acepta y queda como `0,00 €` · gravedad **BAJA**

**Qué pasa.** `apuntar_un_cobro` comprueba `importe <= 0` **sobre lo que llega**, antes de redondear al
céntimo. Un cobro de `0.004` pasa el filtro (es mayor que cero) y luego `ImporteExacto` lo guarda
redondeado:

```
cobro con importe de tres decimales: 201 {'cobro': {'importe': '0.005', 'texto_importe': '0,01 €', …}}
cobro con importe de cuatro decimales: 201 {'cobro': {'importe': '0.004', 'texto_importe': '0,00 €', …}}
```

**Qué debería pasar.** Lo que dice el propio aviso del endpoint —«Un cobro de cero euros no es un
cobro»—: comprobarlo sobre **lo que se va a guardar**, no sobre lo que llega. Hoy la lista de lo que ha
entrado puede llevar un renglón de 0,00 €.

**¿Hay una prueba que lo habría cazado?** `test_un_cobro_de_cero_no_es_un_cobro` manda `importe: 0` y
pasa; el caso del redondeo no está. Prueba: `TestDefecto9…`.

---

### DEFECTO 10 — el aviso de la entrega repetida sale con el hueco en blanco (y dice algo que no es) · gravedad **BAJA**

**Qué pasa.** Cuando la misma entrega viaja dos veces en la misma petición de facturar, el endpoint
contesta el aviso `D6_esa_entrega_ya_esta_facturada` **con el número vacío**:

**Cómo lo he provocado** (`POST /api/facturas-emitidas {"entregas":[1,1],"fecha":"…"}`):

```
422 {"detail": "Esa entrega ya está dentro de la factura . Una entrega no puede estar en dos
     facturas: si te has equivocado, quita la factura y vuelve a hacerla con las que quieras."}
```

Dos cosas en una frase: el hueco donde iba el número, y que **dice algo que no es** — esa entrega no
está en ninguna factura; lo que pasa es que se ha mandado dos veces en la misma petición. El informe
(§8, la quinta cosa) cuenta que esto se arregló «comprobándolo antes de escribir nada» y tiene razón en
lo que importa (no hay 500 y no se escribe a medias): lo que falta es que **la frase diga eso**. La
prueba del ticket (`test_la_misma_entrega_reenviada_no_se_factura_dos_veces`) comprueba el 422, no lo
que se lee. Prueba: `TestDefecto10…`.

---

### DEFECTO 11 — una factura anulada enseña `0,00 €` y «0 entregas» · gravedad **BAJA**

**Qué pasa.** «Anular no borra nada» es verdad **en los datos**: tras anular una factura de 121,00 €
quedan en la base **4 líneas (2 anuladas)** y **2 facturas (1 anulada)**, con su motivo y su rastro en
`auditoria`. Lo que no es verdad es lo que **enseña** la ficha, porque `como_se_ve_una_factura` solo
mira las líneas vivas (`anulada.is_(False)`):

```
anular la factura sin cobros: 200 | total que enseña: 0,00 € | entregas: 0
filas en lineas_de_factura_emitida: (4, 2)   ← cuatro líneas, dos anuladas
filas en facturas_emitidas:         (2, 1)
```

**Qué debería pasar.** Que el documento anulado siga diciendo **lo que decía** (121,00 € y su entrega
dentro) con la marca de que está anulado. Un documento anulado convertido en un documento de cero euros
es la misma trampa del A08 —«no lo sé»/«no vale» leído como cero— aplicada a un papel, y el sitio donde
dentro de un año se mira qué se emitió y por qué se quitó. Prueba: `TestDefecto11…`.

---

### DEFECTO 12 — una prueba del propio ticket se pone roja en PostgreSQL por construcción · gravedad **MEDIA**

**Qué pasa.** `tests/test_el_dinero_de_las_ventas.py:159`, la prueba que cierra el círculo del ticket
—«el importe va y vuelve de la base sin perder ni un céntimo»—, empieza así:

```python
def test_el_importe_va_y_vuelve_de_la_base_sin_perder_ni_un_centimo(self, cliente, cuenta, campana, parcela):
    """La prueba que cierra el círculo: **lo guardado en la base es exacto**. …"""
    assert engine.dialect.name == "sqlite", engine.dialect.name
```

**Cómo lo he provocado.** La suite del ticket contra PostgreSQL (base propia; comando en §1):

```
$ ..\.venv\Scripts\python.exe -m pytest tests/test_el_dinero_de_las_ventas.py -q -x
........F
FAILED tests/test_el_dinero_de_las_ventas.py::TestElDineroNoPierdeCentimos::
       test_el_importe_va_y_vuelve_de_la_base_sin_perder_ni_un_centimo
E   assert engine.dialect.name == "sqlite", engine.dialect.name
E   AssertionError: postgresql
E   assert 'postgresql' == 'sqlite'
```

Tres consecuencias, y las tres importan:

1. **El informe dice «4 en rojo, y las cuatro de recuentos de documentación… Ninguna otra».** En
   PostgreSQL hay una **quinta**, y es de este mismo fichero. La frase es verdad en SQLite y falsa en el
   motor de producción.
2. **La promesa central del ticket no se comprueba donde más importa.** «El importe se guarda como texto
   decimal canónico» es una decisión que existe *por* PostgreSQL (`supports_native_decimal`) tanto como
   por SQLite, y el viaje de ida y vuelta no se mide allí.
3. **Y la mitad del test sí valdría en PostgreSQL**: las líneas que comprueban que la API devuelve el
   mismo importe y que en la base está guardado como `"0.10"` son independientes del motor. Lo único que
   no es portable es `SELECT typeof(importe)`, que es sintaxis de SQLite.

**Qué debería pasar.** Lo que ya hace el proyecto cuando una prueba solo puede correr en un motor:
**saltarse diciendo por qué** (`tests/test_arranque_en_postgresql.py`), no ponerse roja. O mejor:
comprobar lo mismo en PostgreSQL con `pg_typeof(importe)` —o con
`information_schema.columns.data_type`—, que es donde el «texto y no número» de verdad se juega algo.

**¿Hay una prueba que lo habría cazado?** Ninguna, porque en SQLite —el único motor donde se había
corrido— el `assert` pasa. `TestDefecto12…` lo caza leyendo el fichero: falla mientras haya un
`assert engine.dialect.name ==` en una prueba del ticket, y pasa tanto si se salta diciéndolo como si
se comprueba en los dos motores.

---

## 3. Lo que he intentado romper y **no** he podido

Esto también es resultado: son las promesas del informe que he atacado y han aguantado, con el número
delante.

**A06, entero.** Factura de 121,00 €, cobro de 40,00 €: el pendiente queda en **81,00 € exactos** y el
aviso lo dice con las dos cifras («llevas cobrado 40,00 € de 121,00 €: quedan 81,00 € por cobrar»).
Cobro de los 81: pendiente **0,00 €**, cobrado 121,00 €, estado «Cobrada», y **las facturas contadas
antes y después: 1 y 1**. No hay ninguna línea en el router que cree una factura desde un cobro, y se
nota: conciliar un segundo importe no crea nada.

**A08 por el detalle.** 8.000 kg sin precio: `importe: None`, `importe_total: None`, `estado:
sin_importe`, `texto_importe: ""`, la fila de la tabla con `importe_conocido: false`, y el aviso con el
número. Facturarla contesta **422 con lo que hay que hacer**: «Esa entrega no se puede facturar todavía
porque no se sabe por cuánto. Ponle el importe o el precio, y vuelve a facturarla.»

**Los decimales, uno por uno** (medidos con `dinero.py` directamente y por la API):

| Cuenta | Resultado |
|---|---|
| `0,10 + 0,20` | `0.30` (no `0.30000000000000004`) |
| 21 % sobre 121,00 | `25.41` |
| `80,999` al céntimo | `81.00` (no `80.99`) |
| `0,125` y `0,135` | `0.13` y `0.14` (al alza las dos) |
| 42.000 kg × 0,2350 €/kg | `9870.00` (y redondeando el precio antes, `10080.00`: los 210 € de diferencia que el informe dice) |
| `float`, `bool`, `nan`, `inf` | rechazados a la cara con su frase |
| `de_texto("1.234,56")` | `1234.56`; `de_texto("0,2350")` → `0.2350` |
| Guardar y leer «0.10» | vuelve `'0.10'` y **en SQLite `typeof(importe) = 'text'`** |

**Y la prueba que de verdad buscaba céntimos perdidos: 100 cobros parciales.** 100 cobros de 1,00 €
sobre 100,00 € → cobrado **100,00 €**, pendiente **0,00 €**, «Cobrada». Y la que pierde el céntimo en
JavaScript y aquí no: **100 cobros de 0,10 € sobre 10,00 € → cobrado 10,00 €, pendiente 0,00 €** (en
coma flotante, `0.1 × 100` no da `10`). El pie y las filas siguen cuadrando: `1 entrega · 10,00 € ·
pendiente 0,00 €`.

**El pie que cuadra con el detalle, con los datos del informe.** Monté las cuatro entregas del informe
(una sin importe, una suelta de 300,00 €, dos agrupadas con una devolución de −100,00 € y un pago
parcial de 5.000,00 €) y **sumé las filas**:

```
totales: {'importe': '10270.00', 'facturado': '9970.00', 'cobrado': '5000.00',
          'pendiente': '4970.00', 'entregas': 4, 'sin_importe': 1, 'por_cobrar': 2}
pie:     4 entregas · 10.270,00 € · pendiente 4.970,00 €
suma de las filas: 10270.00  5000.00  4970.00   → cuadra: True True True
resumen del año == tabla: True
```

Los cuatro números son **exactamente** los del informe, y la suma de la columna «cobrado» **es** lo
cobrado (5.000,00 € en una sola fila, no repetido en las dos de la factura).

**Agrupar sin duplicar, y el índice de verdad.** El importe de la factura es la suma de sus líneas
(121 + 79 = 200,00 €, y `facturado` cuenta 200,00 €, no 400,00). Volver a facturar una entrega ya
facturada contesta **422 diciendo en qué factura está** («Esa entrega ya está dentro de la factura F-1…»).
Y el índice único **existe en la base**, mirado en el esquema y no en el comentario:

```
SQLite:      CREATE UNIQUE INDEX uq_linea_de_factura_por_entrega
             ON lineas_de_factura_emitida (explotacion_id, venta_id) WHERE anulada = 0
PostgreSQL:  CREATE UNIQUE INDEX uq_linea_de_factura_por_entrega ON public.lineas_de_factura_emitida
             USING btree (explotacion_id, venta_id) WHERE (anulada = false)
```

(Los otros cuatro índices de reenvío también están, con su `WHERE` en los dos motores: `uq_venta_reenvio`,
`uq_ajuste_reenvio`, `uq_factura_emitida_reenvio` y `uq_cobro_reenvio`.)

**Reenviar no duplica: las cuatro cosas.** La misma entrega, el mismo ajuste, la misma factura y el
mismo cobro, mandados dos veces con la misma clave: el mismo identificador, **una sola fila** en cada
lista, `ya_estaba: true` en el cobro y el pendiente donde estaba. El caso que alarma al proyecto —el
móvil que reintenta sin cobertura— **no duplica nada** y tampoco contesta 500.

**Anular no borra, y anular la factura libera.** La entrega facturada no se anula ni se borra (409, y
el aviso dice en qué factura está); la factura con cobros no se quita (409); el cobro anulado devuelve
la deuda (la factura vuelve a 81,00 € pendientes) y **sigue en la base** con su motivo; al anular la
factura, **sus entregas quedan libres y se vuelven a facturar** (201, 200,00 €); y el rastro de
`auditoria` queda con las cuatro entidades y sus etiquetas (`crear`, `anular`, `corregir`, `conciliar`,
`desconciliar`, `subir_papel`), todas muy por debajo de los 80 caracteres de la columna.

**Aislamiento: catorce puertas, todas cerradas.** Desde otra finca (otra cuenta, otra explotación), con
los identificadores de la primera a mano: leer la entrega, leer la factura, listar sus ajustes,
corregirla, anularla, borrarla, apuntarle un ajuste, anular ese ajuste, subirle el papel, cobrar contra
su factura, anular su cobro, conciliar un cobro **propio** contra su factura, anular su factura y
facturar su entrega → **404 en las catorce**. Y sus cinco lecturas de lista (ventas, facturas, cobros,
tabla e informe) salen **vacías** (0 filas). Ni un 403, ni una fila, ni un dato suyo.

**Nada de esto se presenta como factura fiscal.** Ni «IVA», ni «Verifactu», ni «impuesto», ni
«Hacienda», ni «ley» en los textos de `VENTA`/`FACTURA_EMITIDA`/`COBRO` ni en las ocho pantallas del
dinero (lo único que aparece es el aviso, y dice lo contrario: «La factura que se hace desde esta
pantalla es tu cuenta de lo que has vendido: **no es un documento con validez oficial**»). Las tres
pantallas de la factura pintan `AvisoNoOficial`, y la factura no tiene base imponible, ni cuota, ni
tipo: su total es la suma de lo entregado.

**Los cuatro fallos que el informe cuenta como arreglados: los he ido a mirar, y están arreglados.**

- **Corregir una venta no le borra el dinero** (§8.4). Ida y vuelta completa: creo una entrega con
  importe 121,00 €, precio 0,2350 y vencimiento, **reenvío por `PUT` el mismo cuerpo que devolvió la
  API** (que es lo que hace el navegador) y el importe, el precio y el vencimiento **siguen ahí**
  (`200`, `121,00 €`, `0.2350`, `2026-08-10`); el `PUT` es idempotente (segundo `PUT`, otro 200). Y en
  el código está el motivo escrito: `borradorDeUnaVenta` devuelve los cuatro campos, y `cargaVenta` los
  manda aunque el asistente no los pregunte.
- **Las tarjetas del móvil ya no salen vacías** (§8.1): `app.js` copia `...fila` **además** de las
  celdas (`app.js:12340`), que es exactamente lo que faltaba, y el comentario dice por qué.
- **Una cosecha usada por una entrega no se borra** (§8.3): 409 con el número y qué hacer («Esa cosecha
  la usa 1 entrega: dice que la partida salió de ahí. Corrige primero la entrega —o quítale esa
  cosecha— y después podrás borrarla.»), y una cosecha sin entregas sí se borra (200).
- **La tabla cabe** (§8.2): está dentro de `.tabla-scroll` (`ventas.js:207`). *(No he medido los anchos
  yo: ver §4.2.)*

**Las etiquetas del rastro.** `auditoria.accion` mide **80** y `entidad` **60** en el modelo (y en
PostgreSQL, `character_maximum_length` = 80 y 60), y las etiquetas del T12 miden entre 5 y 17
caracteres. He ejecutado el guardián (`tests/test_las_etiquetas_del_rastro_caben.py`): **pasa**.

---

## 4. Lo que **no** he podido comprobar, escrito por mí antes de que me lo pidas

1. **La pasada completa de la suite contra PostgreSQL no ha terminado, y lo digo con la medida.** La
   arranqué a las 01:07 con el comando del encargo sobre `cuedigital_revision`; una hora después iba por
   el **8 %** de las 3.793 pruebas y la paré, porque a ese paso son unas siete horas. (El contenedor
   tenía **otra pasada del coordinador en marcha desde antes de empezar** —la vi en `pg_stat_activity` y
   no la he tocado—, y las dos se estorban: cada prueba vacía 40 tablas con
   `TRUNCATE … RESTART IDENTITY CASCADE`.) En su lugar corrí contra PostgreSQL, en bases propias, **la
   suite del ticket y los ficheros que el T12 toca**, y ese resultado es el de §5.4 — que es donde
   apareció el defecto 12. Lo que **sí** he medido en PostgreSQL, una por una, es lo que solo se ve allí
   (defectos 1, 2 y 3, los índices, la longitud de las columnas y las doce pruebas de esta revisión,
   que fallan igual en los dos motores).
2. **Nada en un navegador de verdad.** El defecto 5 lo he medido **renderizando el componente en Node**
   con `react-dom-server` y la tabla real del servidor: es HTML de verdad, pero no es un navegador. No
   he medido los anchos a 390/1.024/1.440 px, ni he visto las tarjetas del móvil pintadas, ni el
   `.tabla-scroll` funcionando. Los «21 anchos medidos» del informe §5 no los he reproducido.
3. **`scripts/humo.py` y `scripts/comprobar_en_un_navegador.py`.** El informe dice que los pasó los dos
   con «todo correcto». **No los he vuelto a pasar** (necesitan levantar un servidor y Chrome y no son
   de esta revisión): me los creo como declaración del agente, no como medida mía.
4. **Dos peticiones a la vez.** No he montado ninguna prueba de concurrencia real: la protección que hay
   es un índice único en la base, y a eso me remito. El propio informe dice lo mismo en su §6.3.
5. **Los papeles del ajuste por la pantalla.** El botón no existe (el informe lo declara); por la API sí
   he probado que sube el fichero y que el aislamiento lo cierra (404 desde otra finca). No he probado
   el nombre del fichero con `../..` en esta revisión (hay una prueba del ticket que lo mira en disco).
6. **La puesta al día de una base vieja** (las seis columnas nuevas añadidas a `ventas_de_cosecha`): la
   prueba del ticket existe y pasa; yo no la he reproducido a mano.
7. **Las 63 pruebas del ticket, leídas una por una.** He leído las que sostienen las afirmaciones del
   informe (A06, A08, el pie, el reenvío, el aislamiento, la emisión fiscal, el esquema) y he mirado sus
   nombres todos; no he auditado el contenido de las 63.
8. **El detalle del CUADERNO de la Junta y el volcado oficial (IUWS).** El informe declara que el dinero
   no va ahí. He comprobado que el CSV y el PDF del cuaderno no llevan importes, y **no** he mirado si
   el volcado oficial (T19/T22) debería llevarlos: es de otro ticket, como dice el informe.
9. **Jerga y textos.** No he revisado los textos nuevos a mano: me apoyo en los tests del proyecto
   (`test_sin_jerga`, `textos_visibles`), que pasan.
10. **El `.gitignore`, los adjuntos y la copia de seguridad.** No he mirado la carpeta de adjuntos en
    esta revisión más allá de que el aislamiento y el borrado del papel funcionen.

---

## 5. Los recuentos reales, medidos hoy

### 5.1. Python

```
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests -q --junit-xml=$env:TEMP\rev12_sqlite.xml
→ 3793 pruebas, 4 fallos, 0 errores, 1 saltada
```

Los cuatro fallos, con su nombre (los mismos que el informe declara, y ninguno más **en SQLite**):

```
FAILED tests/test_la_migracion_a_react.py::TestLasTresListasDicenLoMismo::test_la_documentacion_dice_lo_mismo_que_el_codigo
FAILED tests/test_la_migracion_a_react.py::TestElInventarioDeLoQueFalta::test_el_informe_de_la_migracion_se_puede_contar
FAILED tests/test_lista_de_la_junta.py::TestElResumenCuadraConLaTabla::test_los_numeros_de_test_de_la_documentacion_no_se_quedan_viejos
FAILED tests/test_lista_de_la_junta.py::TestElResumenCuadraConLaTabla::test_el_numero_de_pruebas_de_python_es_el_de_verdad
```

Y lo que dicen, literal:

```
AssertionError: la documentación dice 3700 pruebas de Python y hay 3793.
AssertionError: la documentación dice 867 pruebas de JavaScript y hay 869 (contadas en los ficheros de `tests_js/`)
AssertionError: las cuentas no cuadran: {"migradas": 48, "con_fichero": 48, "en_la_guia": 41, "en_la_cache": 48}
```

`pytest --collect-only` confirma el número: **«3793 tests collected in 1.22s»**. El informe del T12 ya
dice 3.793 (lo corrigió a las 01:18; a las 01:05 decía 3.792, que fue lo primero que leí).

### 5.2. JavaScript

```
node --test "tests_js/*.test.js"
→ tests 869 · pass 869 · fail 0 · skipped 0 · duration_ms 68540.70
```

**869 y 0 fallos**, exactamente lo que dice el informe (y la documentación sigue diciendo 867).

### 5.3. Pantallas y documentación

| Qué | Cuánto |
|---|---|
| Ficheros en `backend/web/react/pantallas/` | **48** |
| Claves en `PANTALLAS_EN_REACT` (`app.js:155`) | **48** |
| Filas de la guía `docs/REACT.md` (`en_la_guia`) | **41** |
| Lo que dice `docs/REACT.md` en prosa | «**veintiocho**» (líneas 199 y 692) y «treinta y cinco» (196) |
| Lo que dice la documentación de pruebas | **3.700** Python y **867** JavaScript en `README.md`, `AGENTS.md` y `docs/LO_QUE_PIDE_LA_JUNTA.md` |

Los dos recuentos que el informe pide (3.793 y 869) son **los que yo mido**. Las siete filas que faltan
en `docs/REACT.md` son las siete pantallas nuevas del T12, y las dos pruebas que lo dicen están en rojo:
el informe lo declara y no lo arregla porque el fichero es del coordinador.

### 5.4. PostgreSQL

Bases propias (`cuedigital_revision`, `cuedigital_revision_probe`, `cuedigital_revision_rev`,
`cuedigital_revision_x`). **`cuedigital_pruebas`, la del coordinador, no se ha tocado.**

| Medida en PostgreSQL | Resultado |
|---|---|
| `tests/test_el_dinero_de_las_ventas.py -q -x` (la suite del ticket) | **`........F`**: 8 pasan y **la novena falla** — `TestElDineroNoPierdeCentimos::test_el_importe_va_y_vuelve_de_la_base_sin_perder_ni_un_centimo`, con `assert engine.dialect.name == "sqlite"` → `AssertionError: postgresql` (**defecto 12**) |
| `tests/test_revision_t12.py` (esta revisión) | **fallan las doce**, con las mismas razones que en SQLite |
| Los nueve textos que se pasan de su columna | **500** (DataError `varying(200)`/`(120)`/`(80)`/`(20)`) — en SQLite, 201 (**defecto 2**) |
| El importe de 27 caracteres | **500** (DataError `varying(24)`) — en SQLite, 201 (**defecto 3**) |
| Los cuatro cuerpos mal formados del ajuste | **500** — igual que en SQLite (**defecto 1**) |
| Los cinco índices únicos parciales del dinero | existen, con su `WHERE` en sintaxis de PostgreSQL |
| `auditoria.accion` / `entidad` | `character_maximum_length` = **80** / **60** |
| `ventas_de_cosecha.importe` | `character varying(24)` — texto, no número |
| La suite completa | **no ha terminado** (8 % en una hora; ver §4.1) |

---

## 6. El árbol se movió mientras revisaba

- A las **01:05** leí `docs/T12_VENTAS.md` (43.641 bytes entonces) y decía «**3.792** pruebas recogidas».
- A las **01:09:31** se editó `backend/tests/test_el_dinero_de_las_ventas.py` (63 pruebas nuevas en vez
  de 62) y a las **01:18:50** el informe, que ahora dice «**3.793**» y añade el apartado de las
  etiquetas del rastro y un análisis del guardián de las etiquetas.
- Los ficheros de **código** (`ventas_api.py` 01:03:34, `models.py` 00:25:13, `textos.py` 00:43:29,
  `app.js` 00:18:18, `dinero.py` 23:40:05, `ventas.py` 22:42:01) **no han cambiado** desde antes de
  empezar, así que los doce defectos están medidos sobre la versión viva.
- Los recuentos de este informe son de la **01:21–02:10**, es decir, de después del último cambio: la
  suite de SQLite que cito (3.793 / 4 fallos) y los 869 de JavaScript son de la versión actual.
- **Una consecuencia práctica:** el guardián de la documentación pedirá el número que salga del árbol en
  cada momento. Con mi fichero de revisión dentro, `pytest --collect-only` dice ahora
  **«3808 tests collected»** (los 3.793 de arriba más las 12 pruebas de esta revisión y los casos que
  `tests/test_ficheros_de_texto.py` añade por los dos ficheros nuevos). Está dicho para que no
  sorprenda: **la revisión suma al recuento como cualquier otra prueba**, y cuando se quite, volverá a
  bajar. El informe del T12 pide 3.793 para la documentación y eso es lo correcto **mientras esta
  revisión no esté en el árbol**.

> **Y una cosa mía, dicha por mí:** a mitad de esta revisión hice un `-replace` con PowerShell sobre
> este mismo fichero (justo lo que `AGENTS.md` §7 prohíbe) y **lo dejé en blanco**. Lo he reescrito
> entero con las herramientas del agente, con el contenido íntegro; lo digo porque el fichero pasó unos
> minutos con 0 bytes y quien lo haya abierto en ese hueco no ha visto nada. No ha afectado a ninguna
> medida: las pruebas y los recuentos de este informe son de antes y de después, y coinciden.

---

## 7. Lo que pido, en una lista

1. **Arreglar los tres defectos altos**, que son de la misma familia y se arreglan de la misma manera:
   validar en la puerta. El ajuste pide un esquema (`AjusteEntrada`, como `CobroEntrada`); los nueve
   campos de texto piden un tope (o el ancho de su columna, o un 422 con frase); y el importe pide
   comprobar que su texto cabe en los 24 caracteres antes de guardarlo.
2. **Decidir** los cinco medios: la lista de ventas (¿se le pasa la explotación a `con_nombres`?), la
   última columna de la tabla (`COLUMNAS_DE_LA_TABLA` + `textos.VENTA["tabla_acciones"]`, que ya está
   escrito y sin usar), las tres puertas del `contacto_id`, **las 28 acciones que no se pulsan** y la
   prueba que se para por el motor (defecto 12: `pytest.skip` con su motivo, o comprobar lo mismo con
   `pg_typeof`).
3. **La pasada completa contra PostgreSQL**, que es donde han salido los tres altos y el defecto 12. El
   informe la declara sin medir; yo la he empezado y no ha terminado, y lo que he medido allí ya
   justifica hacerla entera antes de cerrar el ticket (y con el contenedor libre, no con dos pasadas a
   la vez).
4. **Los recuentos de la documentación** (3.793 y 869) y **las siete filas de `docs/REACT.md`**: son del
   coordinador y el informe los pide bien.
