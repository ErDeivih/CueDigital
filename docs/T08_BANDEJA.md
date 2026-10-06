# T08 — La bandeja documental (S10)

> **La parte ejecutable del ticket, entregada.** El corpus del T07 (facturas de verdad para medir la
> precisión del lector) **no se ha usado** y **no bloquea nada**: la bandeja funciona entera sin él, y lo
> único que no se hace es decir si la lectura es buena —porque sin corpus no se puede afirmar—.

## El recorrido, en una frase

> **Subir un documento → revisar sus datos → vincularlo a una compra, un gasto, una venta, una máquina o
> un trabajo, conservando el original.**

Y las dos reglas que son la razón de ser de este ticket, cada una con dónde está escrita:

1. **El original no se toca nunca.** Se guarda tal y como llegó, con su fichero, su nombre y su **huella**
   (`bandeja.huella_de`), y **no se reescribe** con lo que el programa cree haber leído. La huella se
   calcula **al subir** y no se vuelve a calcular ni al leer ni al confirmar.
2. **Lo leído es una propuesta, no un dato.** El programa **propone** (`POST …/leer`), el agricultor
   **acepta** (`POST …/revisar`) y después **confirma** (`POST …/confirmar`). Confirmar **no acepta
   campos**: «confirmar sin haber mirado» no es un descuido que haya que vigilar, es una puerta que no
   existe. Y la pantalla **no dice** «leído correctamente» ni da ningún porcentaje: dice que **no se puede
   medir** y por qué.

### ¿Se puede completar hoy el recorrido? — **No, y le falta una sola cosa: la integración**

El código de los seis ficheros está entero y probado; lo que falta es que se peguen en los ficheros
compartidos los **bloques literales del apartado 3**: las nueve columnas nuevas y la tabla de vínculos en
`models.py` (más los ocho esquemas en `schemas.py`), los cuatro tipos y sus etiquetas en `catalogos.py`,
los textos, el `include_router` de `main.py`, el vocabulario en `interfaz.py` y **las 19 acciones nuevas en
el manejador de `app.js`** (más la dirección, el botón que entra desde «los papeles», la línea del service
worker y la fila de `docs/REACT.md`). **Con esos bloques pegados tal y como están escritos aquí, el
recorrido se completa entero**: lo he ejecutado de punta a punta contra esas tablas y esos esquemas en un
SQLite temporal (apartado 2.3), y lo que no está integrado se salta en la suite **diciendo qué falta**
(apartado 4.1).

Mientras no se integre, hay **una prueba compartida en rojo, y es de esperar**: la de los botones
(`tests/test_los_botones_hacen_algo.py`), porque la pantalla pinta 19 acciones que el manejador de clics
todavía no conoce. Es exactamente lo que pasó con el T20 en su momento, y se arregla con el bloque 3.6.
La lista exacta de lo que falta por atar, para que no se quede ninguna (la comprueba una prueba de este
ticket, `TestLasAccionesDeLaPantalla`):

pendientes en app.js: bandeja-abrir, bandeja-buscar-candidatos, bandeja-cancelar, bandeja-clasificar, bandeja-comprobar, bandeja-confirmar, bandeja-descartar, bandeja-desenlazar, bandeja-enlazar, bandeja-filtrar, bandeja-guardar, bandeja-leer, bandeja-olvidar-fichero, bandeja-original, bandeja-rectificar, bandeja-revisar, bandeja-subir, bandeja-ver, bandeja-ver-todas

---

## 1. Qué hay hecho, fichero por fichero

| Fichero | Líneas | Qué es |
|---|---|---|
| `backend/app/bandeja.py` | 774 | la lógica pura: tipos, estados, huella, duplicados, la propuesta, lo aceptado, los vínculos y las rectificativas |
| `backend/app/routers/bandeja_api.py` | 1303 | las trece puertas de la bandeja |
| `backend/tests/test_bandeja.py` | 1679 | sus pruebas de Python (122) |
| `backend/web/react/pantallas/bandeja.js` | 1092 | las dos pantallas, en React sin compilación |
| `backend/tests_js/bandeja.test.js` | 1245 | sus pruebas de pantalla (30) |
| `docs/T08_BANDEJA.md` | este fichero | el informe, con los bloques literales para integrar |

### 1.1 `backend/app/bandeja.py` — la lógica pura (sin FastAPI y sin base de datos)

Lo que decide, y por qué está aquí y no en el router: **esto son cuentas y reglas**, y así se puede probar
entero sin servidor.

| Qué | Dónde |
|---|---|
| Los tipos de papel: los cuatro de siempre **más los cuatro nuevos** (`inspeccion`, `ticket`, `albaran`, `analitica`), sin romper los que hay | `TIPOS_NUEVOS`, `TIPOS_DE_PAPEL`, `etiqueta_de_papel`, `es_un_tipo_de_papel`, `carpeta_sugerida_para` |
| Los cuatro estados de la revisión y lo que se puede hacer en cada uno | `RECIEN_SUBIDO`…`CONFIRMADO`, `ESTADOS`, `esta_sin_revisar`, `estado_al_subirlo`, `estado_al_clasificar`, `estado_al_revisar`, `se_puede_confirmar`, `se_puede_descartar_la_propuesta` |
| La huella y los duplicados | `huella_de` (la misma del lector de facturas: **no se escribe una tercera copia**), `es_el_mismo_papel`, `decision_sobre_el_duplicado` |
| La lectura como **propuesta** (importes en texto decimal, sin ningún porcentaje) | `propuesta_de_factura`, `propuesta_sin_leer`, `a_json`/`de_json`, `tiene_algo`, `campos_de_la_propuesta` |
| Lo que el agricultor **acepta**, y lo que de ahí pasa al papel | `campos_aceptados`, `fecha_escrita`, `hay_algo_aceptado`, `para_el_papel`, `DatoQueNoVale` |
| Las seis clases de vínculo y sus reglas | `CLASES_DE_VINCULO`, `CLASES_SUGERIDAS`, `es_una_clase_de_vinculo`, `clases_que_se_sugieren`, `ya_esta_vinculado` |
| Las rectificativas, incluido el círculo que no se puede cerrar | `puede_rectificar_a`, `hay_ciclo` |
| Los nombres y el buscador | `clave_del_estado`, `clave_de_la_clase`, `describe_el_tamano`, `titulo_por_defecto`, `se_parece_a_lo_que_se_busca` |

**Lo que NO hace, y se dice:** no lee facturas (eso es `app/facturas.py`, que se **reutiliza**), no escribe
en la base de datos y **no dice nada sobre lo buena que es la lectura**.

### 1.2 `backend/app/routers/bandeja_api.py` — el router

Trece puertas, todas con su docstring diciendo qué hacen y qué **no** hacen (la tabla está en la cabecera
del fichero). Las tres decisiones que se ven en el código:

* **`subir` llama a las puertas que ya existen** (`documentos_api.crear` y `documentos_api.subir_fichero`)
  en vez de volver a guardar ficheros por su cuenta: dos caminos que escriben en disco son dos sitios
  donde equivocarse con las rutas.
* **El duplicado se comprueba antes de escribir nada** (en `comprobar` y otra vez en `subir`, que contesta
  409 sin crear ni una fila ni un fichero). Se mira **por huella**, y también contra
  `models.Factura.huella`, que ya existía desde el lector de facturas.
* **`confirmar` no acepta campos.** Los campos se aceptan en `revisar`; sin eso, contesta 409 y dice qué
  hacer.

### 1.3 `backend/tests/test_bandeja.py` — sus pruebas de Python

Dos mitades, como en el T13 y el T20: la **lógica pura** (corre hoy, sin tablas) y el **recorrido por la
API** (se salta diciendo qué falta, y corre solo el día que se integre).

### 1.4 `backend/web/react/pantallas/bandeja.js` — la pantalla (React 18 UMD + `htm`, sin compilación)

Dos pantallas en un fichero, como la maquinaria, los trabajos y el banco: **la bandeja**
(`#/papeles/bandeja`) y **la ficha de un papel** (`#/papeles/bandeja/<id>`). Las dos se reconstruyen
enteras al abrir su dirección y piden sus datos al servidor; **los formularios no tienen dirección**.

Cada campo que espera cada una está listado, campo por campo, en el apartado 6.3.

### 1.5 `backend/tests_js/bandeja.test.js` — las pruebas de la pantalla

Con `node --test`, contra el componente (`renderToStaticMarkup`), como las del banco y los gastos: sin
`jsdom` y sin dependencias nuevas.

### 1.6 `docs/T08_BANDEJA.md` — este informe

---

## 2. Qué he comprobado, con qué comando y qué número salió

### 2.1 Las pruebas de Python del ticket

```
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests/test_bandeja.py -q
```

**Resultado: 84 pruebas en verde, 38 saltadas, 0 rojos** (122 pruebas). Las 38 que se saltan son el
recorrido por la API, y se saltan **con el motivo escrito**: falta integrar las tablas, los esquemas y los
textos (el detalle exacto, en el apartado 4.1). Las 84 que corren son la lógica pura y los tres guardianes
del propio ticket (los bloques del informe, las puertas del router y las acciones de la pantalla).

**No he corrido la suite entera de Python** (hay otros agentes en el árbol y tarda minutos), como pide el
encargo: solo `tests/test_bandeja.py`. Las suites que podían romperse por este cambio se han mirado **una a
una y solo esas tres** (`test_los_papeles_y_las_facturas_se_pueden_corregir.py`, `test_sin_jerga.py` y
`test_que_no_falte_ningun_texto.py`): **71 pruebas, 71 en verde** en el árbol de hoy, y el apartado 3.11
dice las dos líneas que hay que actualizar al integrar. Y la de los botones
(`tests/test_los_botones_hacen_algo.py`) está **en rojo a propósito**: es la única, y se arregla
integrando el bloque 3.6 (dice, con nombre y apellidos, las 19 acciones que faltan por atar).

### 2.2 Las pruebas de la pantalla

```
cd F:\EspacioCodigo\CueDigital\backend
node --test "tests_js/bandeja.test.js"
```

**Resultado: 30 pruebas, 30 en verde, 0 rojos.**

### 2.3 El recorrido entero, contra las tablas propuestas (medido, no prometido)

Como el T20, y por el mismo motivo: las pruebas del recorrido por la API se saltan mientras falte la
integración, así que **el recorrido se ha pasado contra las tablas y los esquemas propuestos**. No se ha
tocado ni un fichero del proyecto: se copia `backend/app` y `backend/tests` a una carpeta temporal (sin la
base de datos ni los papeles del agricultor: hay una comprobación que lo verifica), se le aplican **los
bloques literales del apartado 3 leídos del propio informe** —que es lo que garantiza que esos bloques sean
los buenos: si estuvieran mal escritos o faltara uno, la verificación no pasaría— y allí se corre el
recorrido entero contra un SQLite temporal y una carpeta de adjuntos temporal.

**Resultado: 193 pruebas, 193 en verde, 0 rojos** — las 122 del ticket (que allí **ya no se saltan
ninguna**) y las 71 de las tres pruebas compartidas que cambian de lista. Y en la misma corrida pasan
también `tests/test_documentos.py` y `tests/test_t14_maquinaria.py`, que son las dos que el apartado 3.11
dice que **no** se rompen: lo están, medido, y no prometido.

Lo que hace ese recorrido, y lo que salió:

| Paso | Qué comprueba | Resultado |
|---|---|---|
| Registro y `GET /api/bandeja` | la bandeja nace vacía | vacía, `cuantos = 0` |
| `POST /comprobar` del mismo fichero | no escribe nada y calcula la huella | huella de 64 caracteres, `ya_estaba = false` |
| `POST /subir` con `tipo=factura` | el papel queda **clasificado**, con su huella, su fichero y su carpeta | 201, y se archiva en «Facturas» |
| `POST /subir` sin decir el tipo | el papel nace **recién subido** | estado `recien_subido`, y la bandeja lo cuenta |
| `POST /comprobar` **otra vez del mismo fichero** | el duplicado **se dice** | `ya_estaba = true`, con el título del que ya estaba |
| `POST /subir` otra vez | **no crea una segunda ficha** | 409, y `GET /api/bandeja` sigue con **1** papel |
| `POST /leer` | lee el fichero y guarda la propuesta; **el estado no cambia** | estado `clasificado`, `quien` y `fecha` del papel siguen vacíos |
| `POST /leer` de un contrato | no se sabe leer, y **se dice por qué** | la propuesta se guarda con su aviso y sus líneas vacías |
| `POST /confirmar` sin revisar | **no deja** | 409 «antes de confirmar hay que revisar el papel…» |
| `POST /revisar` | guarda lo aceptado; el estado pasa a `propuesta_revisada` | 200, con `lo_aceptado` en texto decimal y escrito |
| `POST /revisar` con un importe ilegible | se dice | 422 |
| `POST /revisar` con un campo en blanco | el blanco es «no lo sé», no «déjalo como estaba» | guardado como nulo |
| `POST /confirmar` | pasa lo aceptado al papel, con quién y cuándo | estado `confirmado`, `quien`, `fecha` y «David» |
| La huella y el fichero **después de confirmar** | **no han cambiado** | la misma huella, el mismo nombre, los mismos bytes |
| `GET /api/documentos/{id}/fichero` | el original se descarga **byte a byte** igual al que se subió | idéntico |
| `POST /descartar` | la lectura descartada **no se borra** | queda con su motivo, y el papel vuelve a «sin revisar» |
| `POST /clasificar` después de revisar | no se pierde lo aceptado, pero hay que revisarlo otra vez | sigue ahí, y `se_puede_confirmar` vuelve a falso |
| Un papel confirmado | **sale de la bandeja** y se ve en «los papeles» | `cuantos = 0`, y `estado=todos` lo enseña |
| `POST /vincular` con un gasto de verdad | enlaza y **no crea ningún gasto** | sigue habiendo 1 gasto (el que había) |
| `POST /vincular` con una máquina, además | un papel puede ir con varias cosas a la vez | 2 vínculos |
| `POST /vincular` con una inspección | además rellena `inspeccion.documento_id` | la ficha de la máquina cuenta 1 papel |
| `POST /vincular` con otra inspección que ya tiene papel | se dice | 409 «esa inspección ya tiene su papel» |
| `POST /desvincular` | quita el vínculo y **no borra el gasto** | 0 vínculos, el gasto sigue |
| `DELETE /api/documentos/{id}` de un papel enlazado | lo dice en vez de dejar el vínculo colgando | 409 «en uso» (lo cuenta `correcciones.en_uso`, que ya mira los `documento_id`), y **anular** sí se puede |
| `POST /rectificar` | la rectificativa apunta a la anterior, y **las dos quedan** | la primera se ve «corregida por» la segunda |
| `POST /rectificar` a sí mismo y con un círculo | se dice | 422 «un papel no se rectifica a sí mismo» / 409 «haría un círculo» |
| `GET /bandeja/candidatos` | son cosas que ya existen, con su nombre | 1 candidato, y se puede buscar por texto |
| Otra finca | **no ve** el papel, ni su ficha, ni su fichero, ni puede confirmarlo | 404 en todas las puertas, y su bandeja está vacía |

### 2.4 Que las pruebas muerden (ocho roturas a propósito)

Se han roto **ocho** cosas de una en una, se ha mirado el rojo y **se ha deshecho cada rotura** dejando el
fichero **byte a byte como estaba** (el script guarda una copia antes y restaura en un `finally`; el árbol
se ha comprobado después con `git status`, y solo están mis seis ficheros). Las cinco primeras se cazan en
el recorrido de la API (la copia temporal del apartado 2.3) y las tres últimas en la pantalla:

| Rotura a propósito | Prueba que la caza |
|---|---|
| **1.** En `subir_a_la_bandeja`, dejar de avisar del duplicado (`if False and decision.get("duplicado")`) | `test_subir_dos_veces_el_mismo_papel_no_crea_dos_fichas` |
| **2.** En `confirmar_el_papel`, dejar confirmar sin haber revisado (`if False and not bandeja.se_puede_confirmar(…)`) | `test_no_se_puede_confirmar_sin_haber_revisado` |
| **3.** En `vincular_el_papel`, **crear un gasto** al enlazar | `test_enlazar_no_crea_el_gasto_ni_la_factura` |
| **4.** En `rectificar_a_otro_papel`, **anular** el papel rectificado (`otro.anulado = True`) | `test_una_rectificativa_deja_las_dos_y_se_dice_cual_corrige_a_cual` |
| **5.** En `confirmar_el_papel`, **recalcular la huella** al confirmar | `test_la_huella_y_el_fichero_no_cambian_al_confirmar` |
| **6.** En `bandeja.js`, enseñar el importe **sin mirar el dato** (`unDato` devuelve el texto tal cual) | «un importe que no consta se enseña como hueco»: la pantalla enseñaba `0,00 €` |
| **7.** En `bandeja.js`, ofrecer el botón de subir **aunque el papel ya estuviera** (`yaEstaba = false`) | «cuando el papel ya estaba se dice, con cuál era, y no se ofrece subirlo» |
| **8.** En `bandeja.js`, dar un **porcentaje** de la lectura (`${propuesta.lineas_que_cuadran} %`) | «la pantalla no dice que la lectura esté bien, y dice que no se puede medir» |

**Las ocho se cazan** (8 de 8). El script de la comprobación imprime, una por una, el nombre de la prueba
que tenía que ponerse roja y si se puso; el resultado fue «LAS OCHO MUERDEN».

### 2.5 Lo que **no** se ha comprobado, y por qué

Está en el apartado 4. En una línea: **la pantalla en un navegador de verdad**, porque `app.js` (que es
quien la monta y quien atiende sus botones) lo integra el coordinador y este ticket no lo toca.

---

## 3. Los bloques literales para integrar

Todo lo de este apartado está pensado para **pegarse tal cual**. Cada bloque lleva su fichero y el sitio
exacto donde va.

### 3.1 `app/models.py` — las columnas nuevas de `documentos_anexos`

Van **dentro** de la clase `DocumentoAnexo`, **entre `fichero_bytes` y `anulado`** (el orden importa: es
el que devuelve `correcciones.campos_corregibles`, y con él está escrita la lista del apartado 3.10).

<!-- bloque: modelos-columnas -->
```python
    # --- La bandeja documental (T08, S10, 06/10/2026) ---------------------
    #
    # Lo que le faltaba a un papel para poder llegar por la bandeja: su huella, en qué punto va la
    # revisión, lo que se ha leído, lo que el agricultor ha aceptado y a quién rectifica. Las cuatro
    # cosas van **en el papel**, y no en una tabla de la bandeja, porque son cosas del papel: un
    # contrato es el mismo contrato se mire desde la bandeja o desde «los papeles», y tener dos filas
    # del mismo papel acabaría con una de las dos vieja.

    # **La huella del fichero tal y como llegó** (SHA-256, 64 caracteres). Es lo que permite decir
    # «este mismo papel ya lo tienes» **antes** de apuntarlo, y **no se recalcula nunca**: si se
    # recalculara al confirmar y el fichero hubiera cambiado, la huella diría que es otro papel y el
    # duplicado se colaría. Vacía cuando el papel no tiene fichero (uno apuntado de palabra).
    huella: Mapped[str | None] = mapped_column(String(64), index=True)

    # En qué punto va la revisión: recien_subido | clasificado | propuesta_revisada | confirmado (ver
    # `bandeja.ESTADOS`). Mientras no sea `confirmado`, el papel está **sin revisar** y se ve en la
    # bandeja; al confirmarlo sale de la bandeja y se ve en «los papeles».
    estado_revision: Mapped[str] = mapped_column(String(24), default="recien_subido", index=True)

    # **Lo que el programa ha leído, guardado aparte de los campos del papel.** Es una propuesta: vive
    # en su columna, en JSON, y **no se escribe** en `titulo`, `fecha` ni `quien` hasta que el
    # agricultor confirma. Dentro van los campos de la cabecera, las líneas, los avisos del lector y
    # las dos cuentas que sí se pueden comprobar. No hay ningún porcentaje ni ninguna medida de la
    # calidad de la lectura, y eso es a propósito: el corpus para medirla (T07) no existe.
    propuesta: Mapped[str | None] = mapped_column(Text)
    # Cómo se leyó (`pdf`, `escaneo`, `foto`, `texto`), para poder decirlo sin abrir la propuesta.
    como_se_leyo: Mapped[str | None] = mapped_column(String(20))
    # Y si el agricultor ha dicho que la lectura no le sirve. Descartarla **no la borra**: queda lo que
    # se leyó, que es lo que permite entender dentro de un año por qué este papel se escribió a mano.
    propuesta_descartada: Mapped[bool] = mapped_column(Boolean, default=False)

    # **Lo que el agricultor ha aceptado** de esa lectura: los mismos campos, en JSON y con los importes
    # en texto decimal. Es lo que pasa al papel al confirmar, y es lo que deja ver la diferencia entre
    # «lo que propuso el programa» y «lo que aceptó él».
    datos_confirmados: Mapped[str | None] = mapped_column(Text)

    # Quién y cuándo dio el visto bueno. Vacío quiere decir «todavía no lo ha confirmado nadie», que no
    # es lo mismo que «confirmado sin decir quién».
    confirmado_en: Mapped[dt.datetime | None] = mapped_column(DateTime)
    confirmado_por_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))

    # A quién rectifica este papel (la factura corregida rectifica a la anterior). La relación se guarda
    # **solo en la rectificativa**, que es quien sabe a quién corrige: así no hay dos columnas que
    # puedan decir cosas distintas, y «esta está rectificada» se deduce (hay otra que la apunta).
    rectifica_a_id: Mapped[int | None] = mapped_column(ForeignKey("documentos_anexos.id"))
```

**Las seis columnas se añaden solas a una base que ya existe**: todas admiten nulo o traen valor por
defecto, así que `asegurar_columnas` las pone al arrancar (`estado_revision` con `'recien_subido'` y
`propuesta_descartada` con `0`). Los papeles que ya tenía el agricultor se quedan **sin huella y sin
estado**, y eso es lo correcto: no han pasado por la bandeja. Un papel sin huella no se puede detectar
como duplicado, y la bandeja **no los enseña** (solo salen los que tienen estado de revisión), así que no
aparecen 200 papeles viejos de golpe.

### 3.2 `app/models.py` — la tabla de los vínculos

Va **después** de la clase `DocumentoAnexo`, en su mismo apartado (antes del comentario grande de «Facturas
de compra»).

<!-- bloque: modelos-tabla -->
```python
class VinculoDeDocumento(Base):
    """Con qué va un papel: la compra, el gasto, la venta, la máquina, el trabajo o la inspección.

    ## Por qué es una tabla y no seis columnas en el papel

    Porque **un papel puede ir con varias cosas a la vez** y con un número distinto de cada una: la
    factura del gasóleo va con el gasto y con el tractor, y el albarán de una labor va con el trabajo y
    con la máquina que la hizo. Con columnas fijas (`gasto_id`, `maquina_id`…) el día que un papel fuera
    con dos gastos habría que cambiar la tabla; así, lo que hay es una fila por vínculo.

    Y es **una sola tabla para las seis clases** en vez de seis tablas casi iguales, por el mismo motivo
    por el que este programa tiene un solo `adjuntos.py`: seis sitios donde equivocarse con el
    aislamiento entre fincas son seis sitios donde equivocarse. Lo que dice de qué va cada fila es
    `clase`, y sus valores son los de `bandeja.CLASES_DE_VINCULO`.

    ## Nada se crea al enlazar

    Enlazar escribe una fila aquí y **no toca ninguna otra tabla** (con una excepción, dicha en su
    sitio: enlazar un certificado con su inspección rellena `InspeccionDeMaquina.documento_id`, que es
    el campo que ya existía y que enseña la ficha de la máquina). Ni un gasto, ni una factura, ni una
    venta salen de aquí: eso se apunta en su pantalla, con sus campos y sus comprobaciones.

    ## Se puede quitar, y queda el rastro

    Desvincular **borra esta fila** y escribe en la auditoría quién, cuándo y con qué estaba enlazado.
    Dejarla «quitada» (`quitado_en`) parecía más prudente y es peor: esa fila seguiría contando como
    dependencia del papel para siempre —`correcciones.en_uso` cuenta las filas, no las vivas— y el
    agricultor no podría borrar un papel por un enlace que él mismo ya había quitado.
    """

    __tablename__ = "vinculos_de_documento"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    documento_id: Mapped[int] = mapped_column(ForeignKey("documentos_anexos.id"), index=True)
    # compra | gasto | venta | maquina | trabajo | inspeccion. Ver `bandeja.CLASES_DE_VINCULO`.
    clase: Mapped[str] = mapped_column(String(20), index=True)
    # La fila de esa clase: la factura de compra, el gasto, la venta, la máquina, la labor o la
    # inspección. No es una clave ajena a propósito: apunta a **seis tablas distintas**, así que la base
    # no puede comprobarlo y quien comprueba que sea de esta finca es el router.
    entidad_id: Mapped[int] = mapped_column(Integer, index=True)

    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    creado_por_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))


```

### 3.3 `app/schemas.py` — los esquemas de salida

Van al final del bloque de los papeles (después de `DocumentoSalida`, línea ~2141).

<!-- bloque: esquemas -->
```python
# --------------------------------------------------------------------------
# La bandeja documental (T08, S10, 06/10/2026)
# --------------------------------------------------------------------------
#
# Lo que sale por estas puertas, con una regla que se repite y conviene leer una vez: **de cada cabecera
# van las dos cosas**, el dato (`campos`, con los importes en texto decimal, que es como viaja el dinero
# en este programa) y su versión escrita (`textos`, «980,10 €»). Y no es un adorno: es lo que hace que la
# pantalla pueda **no creerse el texto**. Cuando un campo no consta, su versión escrita sale vacía y quien
# decide qué se enseña es el dato, así que un importe que no consta se enseña como hueco y nunca como
# `0,00 €`.


class VinculoDeUnPapelSalida(SalidaBase):
    """Con qué va un papel, con el nombre de lo enlazado **ya compuesto** en el servidor.

    `que_es` es lo que se lee («Un gasto · Gasóleo · 01/10/2026»): el vocabulario vive en el servidor, y
    la pantalla no compone nombres ni enseña identificadores.
    """

    id: int
    clase: str
    etiqueta_clase: str
    entidad_id: int
    que_es: str
    creado_en: dt.datetime


class LaPropuestaSalida(SalidaBase):
    """Lo que el programa ha leído. **Es una propuesta, no un dato.**

    Lo que **no** lleva, y es lo más importante: ninguna medida de la calidad de la lectura. Ni un
    porcentaje, ni una confianza, ni un «leído correctamente». El corpus para medirlo (T07) no existe.
    Lo que sí lleva son las dos cuentas que el lector puede comprobar (si cuadra la base más el IVA, y
    si las líneas suman la base) y, en cada línea, si su cuenta cuadra.
    """

    clase: str
    como_se_leyo: str
    leido_en: str
    campos: dict
    textos: dict
    lineas: list[dict]
    avisos: list[str]
    lineas_leidas: int
    lineas_que_cuadran: int
    cuadra_el_total: bool
    suman_las_lineas: bool


class LoQueSeAceptoSalida(SalidaBase):
    """Lo que el agricultor ha aceptado de esa lectura. **Todavía no está confirmado.**"""

    campos: dict
    textos: dict


class PapelDeLaBandejaSalida(SalidaBase):
    """Un papel, con todo lo que hace falta para enseñarlo y para decidir qué hacer con él.

    Los tres `se_puede_*` los decide **el servidor** y no la pantalla. Ese es el detalle que hace que el
    recorrido no se pueda saltar desde el navegador: `se_puede_confirmar` es falso mientras no haya algo
    aceptado, así que una pantalla no puede confirmar lo que el servidor no deja confirmar.
    """

    id: int
    titulo: str
    tipo: str
    etiqueta_tipo: str
    carpeta: str
    # El estado **y su palabra ya resuelta**: la pantalla no traduce claves.
    estado: str
    etiqueta_estado: str
    sin_revisar: bool
    fecha: dt.date | None
    quien: str | None
    # El original: su nombre, su tipo, sus bytes (y lo que ocupa, ya escrito) y su huella.
    tiene_fichero: bool
    nombre_del_fichero: str | None
    tipo_del_fichero: str | None
    bytes: int | None
    texto_tamano: str
    huella: str | None
    como_se_leyo: str | None
    propuesta_descartada: bool
    la_propuesta: LaPropuestaSalida | None
    lo_aceptado: LoQueSeAceptoSalida | None
    se_puede_leer: bool
    se_puede_confirmar: bool
    se_puede_descartar_la_propuesta: bool
    confirmado_en: dt.datetime | None
    confirmado_por: str | None
    # A quién rectifica este papel y quiénes lo rectifican a él: las dos cosas, porque una rectificativa
    # deja las dos versiones y hay que poder ver la cadena desde los dos lados.
    rectifica_a: dict | None
    rectificada_por: list[dict]
    vinculos: list[VinculoDeUnPapelSalida]
    clases_sugeridas: list[str]
    cuantos_candidatos: dict
    creado_en: dt.datetime


class LaBandejaSalida(SalidaBase):
    """La bandeja entera: lo que hay que revisar, y el vocabulario para preguntarlo."""

    textos: dict
    papeles: list[PapelDeLaBandejaSalida]
    cuantos: int
    sin_revisar: int
    sin_decir_de_que_es: int
    resumen: str
    tipos: list[dict]
    estados: list[dict]
    clases: list[dict]


class ElFicheroComprobadoSalida(SalidaBase):
    """Lo que se ha visto del fichero **antes de apuntarlo**: su huella y si ese papel ya estaba.

    Esta puerta **no escribe nada**, y por eso existe: es lo que permite decir el duplicado antes de que
    nada haya cambiado.
    """

    huella: str
    bytes: int
    texto_tamano: str
    nombre_del_fichero: str
    tipo_del_fichero: str
    ya_estaba: bool
    donde: str | None
    el_que_ya_estaba: dict | None
    que_hacer: str


class LosCandidatosSalida(SalidaBase):
    """Con qué se puede enlazar un papel: lo que **ya existe** en el cuaderno, con su nombre compuesto."""

    clase: str
    etiqueta_clase: str
    items: list[dict]
    cuantos: int
    truncado: bool
    sin_candidatos: str


class LoQueHaPasadoSalida(SalidaBase):
    """Lo que devuelven las puertas que cambian algo: el papel **como ha quedado**, y lo que hay que decir."""

    papel: PapelDeLaBandejaSalida
    avisos: list[str]


```

### 3.4 `app/catalogos.py` — los cuatro tipos nuevos

`TIPOS_DOCUMENTO` pasa a tener ocho. **Los cuatro de siempre no se tocan** (son los que nombra el documento
de la Junta) y los cuatro nuevos se añaden al final.

<!-- bloque: catalogos -->
```python
# ... y los cuatro de la bandeja documental (T08, S10, 06/10/2026).
#
# Llevan aquí desde el primer día del catálogo y se apuntaban mal, cada uno por su motivo:
#
#   · **`inspeccion`**: el certificado de la ITV o de la ITEAF de una máquina. Es el que el T14 dejó
#     escrito que faltaba (`tests/test_t14_maquinaria.py`: «se apunta como "otros" porque no hay un tipo
#     de papel para un certificado de inspección (…) el día que exista ese tipo, este certificado irá al
#     suyo»).
#   · **`ticket`**: el tique del gasóleo o del taller. No es una factura —casi nunca lleva NIF— y
#     meterlo como «factura» ensucia la lista de facturas.
#   · **`albaran`**: el albarán de entrega de grano o de compra. **No es** el de envases de Sigfito, que
#     ya tenía su tipo: son dos papeles distintos y con el mismo nombre se confundirían.
#   · **`analitica`**: el boletín de un laboratorio **en papel**. Sus números tienen su sección propia
#     con su boletín; aquí está el papel, que es lo que se enseña en una inspección.
TIPOS_DOCUMENTO = (
    "contrato",
    "factura",
    "albaran_sigfito",
    "otros",
    "inspeccion",
    "ticket",
    "albaran",
    "analitica",
)

ETIQUETA_DOCUMENTO = {
    "contrato": "Un contrato",
    "factura": "Una factura",
    "albaran_sigfito": "Un albarán de envases (Sigfito)",
    "otros": "Otro papel",
    "inspeccion": "Un certificado de inspección",
    "ticket": "Un ticket de compra",
    "albaran": "Un albarán de entrega",
    "analitica": "Un boletín de análisis",
}
```

> **Ojo con `app/bandeja.py`:** allí hay una copia de estos cuatro tipos y estas cuatro etiquetas
> (`TIPOS_NUEVOS` y `ETIQUETAS_NUEVAS`) **para que el ticket funcione antes de integrarse**. Está escrita
> para que no estorbe el día que esto se integre: `TIPOS_DE_PAPEL` no repite y `etiqueta_de_papel` prefiere
> **siempre** la del catálogo. Se pueden borrar las dos constantes de `bandeja.py` cuando esto esté
> integrado, y hay una prueba que lo comprueba (`test_los_cuatro_de_siempre_siguen_estando`).

### 3.5 `app/textos.py` — los textos del agricultor

Dos bloques: los mensajes del router (prefijo `T08_`, como los `T20_` del banco) y las palabras de la
pantalla.

<!-- bloque: textos-mensajes -->
```python
# --------------------------------------------------------------------------
# Los mensajes de la bandeja documental (T08, S10, 06/10/2026)
# --------------------------------------------------------------------------
#
# Lo que el servidor dice cuando algo no se puede hacer, con el prefijo `T08_` de este ticket (los del
# banco son `T20_`, y así se sabe de qué pantalla es cada uno). Todos dicen **qué pasa y qué hacer**, que
# es la regla de la casa: un aviso que no dice qué hacer deja al agricultor parado delante de la pantalla.
MENSAJES_DE_LA_BANDEJA: dict[str, str] = {
    # --- el papel y su ficha ---
    "T08_ese_papel_no_esta_en_tu_bandeja": "Ese papel no está en tu bandeja. Míralo en LOS PAPELES y vuelve a intentarlo.",
    "T08_eso_no_esta_en_tu_cuaderno": "Eso no está en tu cuaderno. Elige algo que ya tengas apuntado.",
    "T08_sin_fichero_no_se_puede_leer": "Este papel está apuntado sin su fichero, así que no hay nada que leer. Súbelo desde LOS PAPELES y vuelve a intentarlo.",
    "T08_este_papel_no_lo_se_leer": "De este tipo de papel todavía no sé leer nada. Escribe los datos a mano: quedan guardados igual.",
    "T08_el_fichero_ha_cambiado": "El fichero que tengo guardado no es el que subiste, así que no lo he leído. Vuelve a subir el papel bueno.",
    # --- clasificar y revisar ---
    "T08_ese_tipo_no_existe": "Ese tipo de papel no lo conozco. Los que hay: {tipos}.",
    "T08_ese_estado_no_existe": "Ese estado no lo conozco. Los que hay: {estados}.",
    "T08_no_has_aceptado_nada": "No has dicho qué queda de este papel. Escribe lo que ponga el papel y vuelve a intentarlo.",
    "T08_ese_importe_no_se_entiende": "Ese importe no lo entiendo. Escríbelo como en el papel, por ejemplo 1.234,56.",
    "T08_esa_fecha_no_se_entiende": "Esa fecha no la entiendo. Escríbela como 31/12/2026.",
    "T08_esa_fecha_no_existe": "Esa fecha no existe. Mírala y vuelve a escribirla.",
    "T08_no_hay_lectura_que_descartar": "De este papel no hay ninguna lectura que descartar. Léelo primero.",
    "T08_dime_por_que_no_sirve": "Dime por qué no te sirve la lectura, para que quede apuntado.",
    "T08_revisado_sin_confirmar": "Guardado lo que queda de este papel. Está sin confirmar: confírmalo cuando lo tengas claro.",
    "T08_lectura_descartada": "Descartada esa lectura: queda guardada con tu motivo, y el papel sigue esperando.",
    # --- confirmar ---
    "T08_hay_que_revisar_antes": "Antes de confirmar hay que revisar el papel y decir qué queda: ábrelo, mira lo que dice (o escríbelo a mano) y guárdalo.",
    "T08_papel_confirmado": "Papel confirmado. Ya está en LOS PAPELES, con su fichero tal y como llegó.",
    # --- el duplicado ---
    "T08_el_mismo_papel_ya_estaba": "Este mismo papel ya lo tienes: «{titulo}», subido el {cuando}. No se ha apuntado otra vez.",
    "T08_el_mismo_papel_esta_en_una_factura": "Este mismo fichero ya lo subiste como la factura de compra «{quien}» (nº {numero}). No se ha apuntado otra vez.",
    "T08_papel_en_la_bandeja": "Papel guardado tal y como llegó. Está en la bandeja, sin revisar: nada ha entrado en tu cuaderno todavía.",
    # --- enlazar ---
    "T08_esa_clase_no_existe": "Con eso no se puede enlazar un papel. Se puede con: {clases}.",
    "T08_dime_con_que_lo_enlazo": "Dime con qué quieres enlazar este papel.",
    "T08_no_hay_nada_que_enlazar": "No hay nada de eso en tu cuaderno. Apúntalo primero en su pantalla y vuelve a intentarlo.",
    "T08_ya_estaba_enlazado": "Este papel ya está enlazado con eso.",
    "T08_esa_inspeccion_ya_tiene_papel": "Esa inspección ya tiene su papel. Quítaselo a la otra antes de ponérselo a esta.",
    "T08_papel_enlazado": "Enlazado. No se ha creado nada: el papel solo dice con qué va.",
    "T08_dime_que_enlace_quito": "Dime qué enlace quieres quitar.",
    "T08_ese_enlace_no_esta": "Este papel no está enlazado con eso, así que no hay nada que quitar.",
    "T08_papel_desenlazado": "Quitado ese enlace. Lo que había apuntado sigue en tu cuaderno igual que estaba.",
    # --- rectificar ---
    "T08_dime_a_que_papel_rectifica": "Dime a qué papel corrige este. Elige uno de la lista.",
    "T08_un_papel_no_se_rectifica_a_si_mismo": "Un papel no puede corregirse a sí mismo. Elige el papel al que corrige.",
    "T08_esto_haria_un_circulo": "Así los papeles se corregirían unos a otros en círculo. Mira a qué corrige cada uno y elige el bueno.",
    "T08_rectifica_a_otro": "Apuntado: este papel corrige a ese. Los dos siguen ahí, y el corregido queda marcado.",
}
MENSAJES.update(MENSAJES_DE_LA_BANDEJA)
```

<!-- bloque: textos-bandeja -->
```python
# --------------------------------------------------------------------------
# La bandeja de los papeles (T08, S10, 06/10/2026)
# --------------------------------------------------------------------------
#
# **Lo que llega y hay que revisar**, que no es lo mismo que «los papeles» (lo que ya está archivado):
# la bandeja es la mesa de la entrada y «los papeles» es el armario. Las palabras son las del agricultor,
# y las tres que más importan se dicen aquí para que nadie las busque: **el original** (el fichero tal y
# como llegó, que no se toca), **la propuesta** (lo que el programa ha leído, que no es un dato) y **lo
# que has aceptado** (que es lo que queda, y todavía sin confirmar).
#
# Dos familias de claves se leen **compuestas**, y las dos las resuelve el servidor y llegan ya escritas:
#
#   · `estado_<estado>` — cómo está un papel (`recien_subido`, `clasificado`, `propuesta_revisada`,
#     `confirmado`) más `estado_desconocido`, que es lo que se dice si el estado no es ninguno de esos.
#     El servidor manda la palabra en `etiqueta_estado`.
#   · `clase_<clase>` — con qué va un papel (`compra`, `gasto`, `venta`, `maquina`, `trabajo`,
#     `inspeccion`) más `clase_desconocida`. El servidor manda la palabra en `etiqueta_clase`.
#
# Y `que_hacer_<estado>`: qué hacer con un papel que está así. **No hay `que_hacer_confirmado`** a
# propósito: de un papel confirmado no hay nada que hacer, y por eso su frase no existe (la pantalla no la
# busca).
BANDEJA: dict = {
    "titulo": "La bandeja de los papeles",
    "explica": (
        "Aquí llega lo que todavía no has mirado: la foto de una factura, el ticket del gasóleo, el "
        "certificado de una máquina. El papel se guarda tal y como llega, y nada entra en tu cuaderno "
        "hasta que tú lo confirmes."
    ),
    "cuantos": "Tienes {cuantos} papeles en la bandeja.",
    # Con uno solo, «Tienes 1 papeles en la bandeja» (ronda 84).
    "cuantos_uno": "Tienes 1 papel en la bandeja.",
    "sin_papeles": (
        "La bandeja está vacía: no tienes ningún papel esperando. Sube uno con el botón de aquí arriba "
        "cuando te llegue."
    ),
    "sin_resultados": "Ningún papel coincide con lo que buscas. Prueba con otras letras o pulsa VER TODO.",
    "faltan_por_decir_de_que_son": (
        "Hay papeles a los que todavía no has dicho de qué son. Ábrelos y dilo: un papel que no se sabe "
        "qué es no sirve de nada en una inspección."
    ),
    "no_consta": "No consta",
    "si": "Sí",
    "no": "No",
    "buscando": "Buscando…",
    # Lo que se dice de algo enlazado que ya no está en el cuaderno: se dice, en vez de enseñar su número.
    "eso_ya_no_esta": "eso ya no está en tu cuaderno",
    # --- subir: el original entra tal y como llega ---
    "subir_titulo": "Subir un papel",
    "subir_explica": (
        "Elige el fichero (una foto o un PDF) y di de qué es. El papel se guarda tal y como llegó."
    ),
    "nada_se_apunta": (
        "Subir no apunta nada al cuaderno: solo guarda el papel. Lo que se lea de él es una propuesta, "
        "y la confirmas tú."
    ),
    "fichero": "El papel, en una foto o en un PDF",
    "fichero_pista": "Hazle una foto al papel o elige el fichero que ya tienes.",
    "fichero_elegido": "El fichero que has elegido es",
    "de_que_es": "¿De qué es?",
    "de_que_es_pista": "Si todavía no lo sabes, déjalo en «no lo sé» y díselo luego desde la bandeja.",
    "no_lo_se_todavia": "Todavía no lo sé",
    "decir_de_que_es": "DECIR DE QUÉ ES",
    "comprobar_el_fichero": "COMPROBAR EL FICHERO",
    "comprobando": "Comprobando…",
    "subir_el_papel": "SUBIR EL PAPEL",
    "subiendo": "Subiendo…",
    "olvidar_el_fichero": "ELEGIR OTRO FICHERO",
    "lo_que_se_ha_comprobado": "Lo que he visto del fichero",
    "la_huella": "Su huella",
    "la_huella_pista": (
        "Es la huella del fichero tal y como llegó. Sirve para saber que este papel es este y no otro, y "
        "no cambia nunca."
    ),
    "tamano": "Cuánto ocupa",
    "ya_estaba": "Este mismo papel ya lo tienes",
    "ya_estaba_explica": (
        "No se ha guardado otra vez: el mismo papel no puede estar dos veces. Es este:"
    ),
    "del_que_ya_estaba_subido": "Lo subiste el",
    "abrir_el_que_ya_estaba": "VER EL PAPEL QUE YA TENÍA",
    "no_estaba": "Este papel no lo tenías: puedes subirlo.",
    # --- la lista ---
    "lista_titulo": "Lo que hay que revisar",
    "lista_explica": (
        "Cada papel, con cómo está y qué le falta. Los que confirmes salen de aquí y se ven en LOS PAPELES."
    ),
    "buscar": "Buscar en la bandeja",
    "buscar_pista": "Escribe parte del nombre o de quién te lo dio.",
    "buscar_boton": "BUSCAR",
    "ver_todo": "VER TODO",
    "cuales_ver": "Cuáles ver",
    "todos_los_estados": "Todos",
    "sin_revisar": "Sin revisar",
    "todos_los_tipos": "De todo",
    "lo_que_es": "Qué es",
    "el_dia_del_papel": "El día del papel",
    "de_quien": "De quién",
    "el_fichero": "El fichero",
    "sin_fichero": "Sin fichero",
    "su_lectura": "Su lectura",
    "tiene_propuesta": "Leído, sin revisar",
    "sin_propuesta": "Todavía no se ha leído",
    "enlazado_con": "Va con",
    "sin_enlazar": "Sin enlazar con nada",
    "abrir": "MIRAR ESTE PAPEL",
    "los_papeles": "VER TODOS LOS PAPELES",
    # --- la ficha: el original, siempre a la vista ---
    "ficha_titulo": "Este papel",
    "el_original": "El papel, tal y como llegó",
    "el_original_explica": (
        "Este es el fichero que subiste. El programa no lo cambia nunca: lo que se lee de él va aparte."
    ),
    "ver_el_original": "VER EL ORIGINAL",
    "sin_fichero_aviso": (
        "Este papel está apuntado sin su fichero. Súbelo desde LOS PAPELES para poder leerlo."
    ),
    # --- la propuesta: lo que se ha leído, y que no es un dato ---
    "la_propuesta": "Lo que el programa ha leído",
    "la_propuesta_explica": "Esto es una propuesta, no un dato: nada de esto ha entrado en tu cuaderno.",
    # **La frase que sostiene la mitad del ticket.** No hay corpus (T07) para medir la lectura, así que no
    # se puede decir que esté bien: se dice que no se puede medir, y se pide al agricultor que la mire.
    "no_se_mide_la_lectura": (
        "El programa no dice si esta lectura está bien: para eso habría que compararla con muchísimas "
        "facturas de verdad, y esa colección todavía no existe. Mírala tú, campo por campo."
    ),
    "leer_el_papel": "LEER EL PAPEL",
    "leyendo": "Leyendo el papel…",
    "no_hay_propuesta": "De este papel no hay ninguna lectura. Puedes escribir los datos a mano.",
    "este_papel_no_lo_se_leer": (
        "De este tipo de papel todavía no sé leer nada. Escribe los datos a mano y quedan guardados igual."
    ),
    "avisos_titulo": "Lo que hay que mirar de esta lectura",
    "las_lineas": "Las líneas que he leído",
    "sin_lineas": "No he reconocido ninguna línea. Puede ser una factura de servicios.",
    "lineas_leidas": "Líneas leídas",
    "lineas_que_cuadran": "Con la cuenta bien",
    # Lo único que se puede afirmar de una línea sin corpus: si su cuenta cuadra, que es aritmética.
    "la_cuenta_cuadra": "La cuenta cuadra",
    "la_cuenta_no_cuadra": "La cuenta no cuadra: mírala antes de guardar",
    "cuadra_el_total": "La base más el IVA da el total",
    "suman_las_lineas": "Las líneas suman la base",
    "cantidad": "Cuánto",
    "precio": "El precio",
    "importe": "El importe",
    "proveedor": "El proveedor",
    "nif_del_proveedor": "Su NIF",
    "numero_de_factura": "El número de factura",
    "fecha": "La fecha",
    "base_imponible": "La base",
    "cuota_de_iva": "El IVA",
    "tipo_de_iva": "El tipo de IVA",
    "total": "El total",
    "descartada": "Esta lectura la descartaste: no te servía.",
    # --- revisar y confirmar: dos actos distintos ---
    "lo_aceptado": "Lo que has aceptado",
    "lo_aceptado_explica": "Esto es lo que queda de este papel. Todavía no está confirmado.",
    "revisar": "REVISAR Y DECIR QUÉ QUEDA",
    "revisar_titulo": "Decide qué queda",
    "revisar_pista": (
        "Corrige lo que haga falta y guarda: lo que guardes es lo que quedará. Después lo confirmas."
    ),
    "guardar": "GUARDAR LO QUE QUEDA",
    "guardando": "Guardando…",
    "cancelar": "DEJARLO",
    "sin_aceptar_nada": "Todavía no has dicho qué queda de este papel.",
    "hay_que_revisar_antes": (
        "Antes de confirmar hay que decir qué queda: revisa la lectura o escribe los datos a mano."
    ),
    "confirmar": "CONFIRMAR ESTE PAPEL",
    "confirmando": "Confirmando…",
    "confirmar_explica": (
        "Al confirmarlo, lo que has aceptado pasa al papel con tu nombre y la fecha. El fichero no se toca."
    ),
    "ya_esta_en_los_papeles": "Este papel ya está confirmado y se ve en LOS PAPELES.",
    "confirmado_por": "Lo confirmaste tú",
    "confirmado_en": "Cuándo",
    "motivo": "¿Por qué no te sirve?",
    "descartar_pista": "Dímelo, para que quede apuntado por qué este papel se escribió a mano.",
    "descartar_la_propuesta": "ESTA LECTURA NO ME SIRVE",
    # --- enlazar: con lo que ya existe, y sin crear nada ---
    "enlazar_titulo": "Con qué va este papel",
    "enlazar_explica": (
        "Un papel puede ir con una compra, un gasto, una venta, una máquina, un trabajo o una inspección."
    ),
    "no_crea_nada": (
        "Enlazar no crea nada: ni un gasto, ni una factura, ni una venta. Solo dice con qué va este papel."
    ),
    "de_que_clase": "¿Con qué quieres enlazarlo?",
    "buscar_candidato": "Buscar lo que ya tienes",
    "buscar_candidato_pista": "Escribe parte del nombre si no lo encuentras en la lista.",
    "buscar_candidatos": "BUSCAR",
    "cual_de_ellos": "¿Cuál de ellos?",
    "elige_uno": "Elige uno",
    "enlazar": "ENLAZARLO",
    "enlazando": "Enlazando…",
    "enlazado_titulo": "Con esto va",
    "desenlazar": "QUITARLO DE AHÍ",
    "sin_candidatos": "No hay nada de eso en tu cuaderno. Apúntalo primero en su pantalla y vuelve.",
    # --- rectificar: las dos quedan ---
    "rectificar_titulo": "Este papel corrige a otro",
    "rectificar_explica": (
        "Si es la factura corregida que sustituye a la anterior, dilo aquí. Las dos quedan: la corregida "
        "sigue ahí, marcada, y no se borra."
    ),
    "a_que_papel": "¿A qué papel corrige?",
    "elige_el_papel": "Elige el papel",
    "rectificar": "DECIR QUE CORRIGE A ESE",
    "rectifica_a": "Corrige a",
    "rectificada_por": "Este papel está corregido por",
    "nadie_lo_ha_corregido": "Este papel no corrige a ninguno ni lo ha corregido nadie.",
    "volver_a_la_bandeja": "VOLVER A LA BANDEJA",
    # --- cómo está un papel (`estado_<estado>`) ---
    "estado_recien_subido": "Recién subido",
    "estado_clasificado": "Sin leer",
    "estado_propuesta_revisada": "Revisado, sin confirmar",
    "estado_confirmado": "Confirmado",
    "estado_desconocido": "No se sabe cómo está",
    # --- y qué hacer con él, según cómo esté (`que_hacer_<estado>`) ---
    "que_hacer_recien_subido": (
        "Falta decir de qué es: elige su tipo y el papel sale de «recién subido»."
    ),
    "que_hacer_clasificado": "Falta mirarlo: léelo (o escríbelo a mano) y di qué queda.",
    "que_hacer_propuesta_revisada": "Ya has dicho qué queda: confírmalo cuando quieras.",
    # --- con qué se puede enlazar (`clase_<clase>`): el servidor manda la clave, la pantalla la palabra ---
    "clase_compra": "Una factura de lo que has comprado",
    "clase_gasto": "Un gasto",
    "clase_venta": "Una venta de tu cosecha",
    "clase_maquina": "Una máquina",
    "clase_trabajo": "Un trabajo hecho",
    "clase_inspeccion": "Una inspección de una máquina",
    "clase_desconocida": "Algo de tu cuaderno",
}
```

Y dos líneas más en `textos.py`, que son las que hacen que estos textos **se revisen**:

```python
# En `textos_visibles()`, al final (después de `textos.extend(_recoger(BANCOS))`):
    # **La bandeja de los papeles (T08, S10, 06/10/2026).** Se recoge entera, con `_recoger` y no con
    # `.values()`, por el mismo motivo que los del T13, el T15 y el T20: dentro lleva las familias
    # compuestas (`estado_…`, `clase_…`, `que_hacer_…`) y `_recoger` las recorre todas. Un texto de
    # pantalla que no pase por aquí es un texto que se lee sin que el test de jerga lo mire.
    textos.extend(_recoger(BANDEJA))
```

Y en `tests/test_sin_jerga.py` (la prueba del singular, que es la que impide «Tienes 1 papeles»):

```python
            # **La bandeja documental (T08, S10, 06/10/2026)**: el pie de la lista de lo que hay que
            # revisar. Con un solo papel se leería «Tienes 1 papeles en la bandeja».
            (textos.BANDEJA, "cuantos", "la bandeja de los papeles"),
```

### 3.6 `backend/web/app.js` — el estado, las pantallas y las 18 acciones

Este es el bloque más largo, y el único que **hace falta de verdad** para que el recorrido se pueda pulsar.
Va en el sitio de los otros bloques de pantalla (junto a los del banco, al final del fichero), y las cinco
líneas de cableado van en sus tablas.

<!-- bloque: app-js-cableado -->
```javascript
// 1) En `PANTALLAS_EN_REACT` (la lista que dice qué ficheros son pantallas de React, línea ~265):
  // La bandeja documental (T08, S10, 06/10/2026). Un solo fichero (`bandeja.js`) con las dos pantallas: lo
  // que hay que revisar, con la subida y la comprobación del duplicado, y la ficha de un papel, que es donde
  // se mira el original con la propuesta al lado y se confirma. Va aquí, y en la caché del campo, por lo de
  // siempre: los papeles se miran en la nave y en el despacho, y una pantalla que no está guardada es un
  // hueco justo cuando hay que decidir si un papel entra en el cuaderno.
  "bandeja",

// 2) En `DIRECCION_PROPIA` (línea ~795). La lista cuelga del renglón de «los papeles», pero su dirección es
//    otra (`#/papeles/bandeja`), así que hay que escribirla aquí: sin esta línea, `apuntarLaDireccion` le
//    pondría la dirección del renglón del menú (`#/papeles`) y las dos pantallas escribirían la misma.
  // Las dos pantallas de la bandeja documental (T08, S10, 06/10/2026). La lista es un sitio al que se
  // vuelve y la ficha de un papel se reconstruye entera al abrirla (pide sus datos al servidor), así que
  // las dos se pueden enlazar, recargar y mandar a quien ayuda.
  PantallaDeLaBandeja: "bandeja",
  PantallaDeUnPapelDeLaBandeja: "bandeja_papel",

// 3) En `ABRIR_LA_PANTALLA` (línea ~1333, junto a `maquinaria`). La ficha **no va aquí**: la abre
//    `abrirLaPantalla`, que es quien comprueba que ese identificador sea de esta finca.
  // La bandeja documental (T08, S10, 06/10/2026): la lista se pide al servidor al abrirla, así que su
  // dirección la reconstruye entera.
  bandeja: () => abrirLaBandeja(),

// 4) En `abrirLaPantalla` (línea ~1217, junto a `banco_movimiento`), los tres finales de siempre: se abre,
//    «eso no está en tu cuaderno» o, sin cobertura, «no lo he podido comprobar».
  if (clave === "bandeja_papel") return abrirUnPapelDeLaBandeja(parametros.id);

// 5) En `apuntarLaDireccion` (línea ~1004, junto a `banco_movimiento`), el identificador del papel.
  // **La ficha de un papel de la bandeja (T08)**: su identificador en el camino (`#/papeles/bandeja/12`).
  // Sale del estado, que es donde está el papel que se está mirando.
  if (clave === "bandeja_papel") {
    const papel = (estado.bandeja || {}).papel;
    if (!papel || !papel.id) return;
    parametros.id = papel.id;
  }

// 6) En `MODULO_DE_LA_PANTALLA` (línea ~1450): las dos cuelgan del renglón de «los papeles», para que el menú
//    sepa dónde está el agricultor.
  PantallaDeLaBandeja: "papeles",
  PantallaDeUnPapelDeLaBandeja: "papeles",

// 7) Y en el manejador de clics (`document.addEventListener("click", …)`, línea ~20280, junto a
//    `atenderLosBancos`):
  if (nombre.startsWith("bandeja-")) return atenderLaBandeja(nombre, elemento);
```

<!-- bloque: app-js -->
```javascript
// ---------------------------------------------------------------------------
// La bandeja documental (T08, S10, 06/10/2026)
// ---------------------------------------------------------------------------
//
// LO QUE ESTE BLOQUE HACE, Y LO QUE NO. Hace lo mismo que el del banco: pide los datos, recoge lo que el
// agricultor escribe y atiende las acciones de sus botones. Y tiene **tres cosas que no hace ningún otro**,
// las tres por el mismo motivo (el original no se toca y lo leído no es un dato):
//
//   1. **El fichero que se está subiendo vive en el estado**, como el del extracto del banco, y por lo
//      mismo: repintar la pantalla borra la casilla del fichero, y hay que volver a mandarlo al subirlo
//      después de comprobarlo. Es la trampa que ya costó una ronda con el cuaderno de la Junta.
//   2. **Nada se sube sin comprobarlo antes.** El botón de subir solo se pinta cuando el servidor ha dicho
//      que ese fichero no estaba (`bandeja-comprobar`), así que este bloque no tiene ninguna puerta por la
//      que se pueda subir un papel sin pasar por ahí.
//   3. **Aquí no se calcula ningún importe.** Los importes llegan del servidor en texto decimal y **ya
//      escritos** (el servidor manda `campos` y `textos`), y la pantalla solo los coloca. Lo único que se
//      escribe aquí es la fecha del papel y la de confirmarlo, con `formateaFecha`.

/** El estado de la bandeja, creado la primera vez que hace falta (como el de las cuentas). */
function estadoDeLaBandeja() {
  if (!estado.bandeja) {
    estado.bandeja = {
      // Lo que devolvió `GET /api/bandeja`: los papeles, el vocabulario y el pie ya compuesto.
      datos: null,
      // El papel que se está mirando, con su propuesta y sus enlaces (`GET /api/bandeja/<id>`).
      papel: null,
      // Con qué se puede enlazar: `GET /api/bandeja/candidatos?clase=…`.
      candidatos: [],
      // El fichero que se está subiendo, **en el estado** (ver la cabecera de este bloque).
      fichero: null,
      nombreDelFichero: "",
      // Lo que contestó `POST /api/bandeja/comprobar`: la huella y si ese papel ya estaba. **No ha
      // guardado nada.**
      comprobado: null,
      comprobando: false,
      subiendo: false,
      // El buscador y los dos filtros de la lista.
      filtro: "",
      estadoElegido: "sin_revisar",
      tipoElegido: "",
      // Lo que está puesto en la subida ahora mismo.
      tipoNuevoElegido: "",
      // La clase con la que se está buscando para enlazar, y lo que se ha escrito para buscarla.
      claseElegida: "",
      claseBuscada: "",
      buscandoCandidatos: false,
      // El formulario abierto (la revisión de un papel), con lo que se ha escrito.
      formulario: null,
      borrador: null,
      guardando: false,
      error: "",
      aviso: "",
    };
  }
  return estado.bandeja;
}

/** El vocabulario de estas pantallas: el de la bandeja y el botón de VOLVER que ya está en los textos. */
function textosDeLaBandeja() {
  return {
    bandeja: t("bandeja", {}),
    acciones: accion("volver") ? { volver: accion("volver") } : {},
  };
}

/** La fecha de un papel, escrita como se escribe aquí. Lo que no consta se queda vacío. */
function laFechaDeUnPapel(fecha) {
  return fecha ? formateaFecha(fecha) : "";
}

/**
 * Un papel, con las fechas escritas.
 *
 * Se escribe aquí la fecha (y no en la pantalla) por la regla de siempre: el formateo de las fechas vive
 * en un solo sitio (`formateaFecha`), y la pantalla no calcula ni formatea nada. Los importes **no se
 * tocan**: el servidor ya manda `campos` (el dato) y `textos` (el mismo, escrito).
 */
function conLasFechasEscritasDeLaBandeja(papel) {
  if (!papel) return papel;
  return {
    ...papel,
    texto_fecha: laFechaDeUnPapel(papel.fecha),
    texto_confirmado_en: papel.confirmado_en ? formateaFecha(papel.confirmado_en) : "",
  };
}

/** La lista de la bandeja, ya en React. */
function pantallaLaBandeja() {
  const suyo = estadoDeLaBandeja();
  const datos = suyo.datos || {};
  return montar(() =>
    pantallaDeLaBandeja({
      textos: textosDeLaBandeja(),
      papeles: (datos.papeles || []).map(conLasFechasEscritasDeLaBandeja),
      tipos: datos.tipos || [],
      estados: datos.estados || [],
      clases: datos.clases || [],
      resumen: datos.resumen || "",
      cuantos: datos.cuantos || 0,
      sinDecirDeQueEs: datos.sin_decir_de_que_es || 0,
      estadoElegido: suyo.estadoElegido,
      tipoElegido: suyo.tipoElegido,
      filtro: suyo.filtro,
      ficheroElegido: suyo.nombreDelFichero,
      tipoNuevoElegido: suyo.tipoNuevoElegido,
      comprobado: suyo.comprobado,
      comprobando: suyo.comprobando,
      subiendo: suyo.subiendo,
      formulario: elFormularioDeLaBandeja(suyo.formulario, suyo.borrador),
      guardando: suyo.guardando,
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/** La ficha de un papel, ya en React. */
function pantallaUnPapelDeLaBandeja() {
  const suyo = estadoDeLaBandeja();
  const papel = conLasFechasEscritasDeLaBandeja(suyo.papel);
  return montar(() =>
    pantallaDeUnPapelDeLaBandeja({
      textos: textosDeLaBandeja(),
      papel: papel || {},
      candidatos: suyo.candidatos,
      // Los otros papeles de la finca, para decir a cuál corrige este: el propio papel no sale de la lista
      // (un papel no se rectifica a sí mismo, y la puerta del servidor lo diría).
      papelesParaRectificar: (suyo.papelesParaRectificar || []).filter(
        (uno) => !papel || uno.valor !== papel.id,
      ),
      clases: (suyo.datos || {}).clases || [],
      claseElegida: suyo.claseElegida,
      claseBuscada: suyo.claseBuscada,
      buscandoCandidatos: suyo.buscandoCandidatos,
      formulario: elFormularioDeLaBandeja(suyo.formulario, suyo.borrador),
      guardando: suyo.guardando,
      cargando: !suyo.papel && !suyo.error,
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/** Abre la bandeja: se pinta enseguida y se vuelve a pintar con lo que contesta el servidor. */
async function abrirLaBandeja() {
  const suyo = estadoDeLaBandeja();
  suyo.error = "";
  suyo.aviso = "";
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.papel = null;
  suyo.comprobado = null;
  suyo.fichero = null;
  suyo.nombreDelFichero = "";
  pantallaLaBandeja();
  await recargarLaBandeja();
  pantallaLaBandeja();
}

/** Vuelve a pedir la bandeja con el filtro que esté puesto. */
async function recargarLaBandeja() {
  const suyo = estadoDeLaBandeja();
  const consulta = new URLSearchParams();
  consulta.set("estado", suyo.estadoElegido || "sin_revisar");
  if (suyo.tipoElegido) consulta.set("tipo", suyo.tipoElegido);
  if (suyo.filtro) consulta.set("texto", suyo.filtro);
  try {
    suyo.datos = await apiJson(`/api/bandeja?${consulta.toString()}`);
    // Los otros papeles de la finca, para poder decir a cuál corrige este. Se piden con la lista y no con
    // cada ficha: son los mismos para todas.
    const todos = await apiJson("/api/bandeja?estado=todos");
    suyo.papelesParaRectificar = (todos.papeles || []).map((uno) => ({
      valor: uno.id,
      texto: [uno.titulo, uno.etiqueta_tipo, laFechaDeUnPapel(uno.fecha)].filter(Boolean).join(" · "),
    }));
    suyo.error = "";
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  return suyo;
}

/**
 * Abre la ficha de un papel: **pide sus datos al servidor**.
 *
 * Es lo que hace que esta pantalla se pueda enlazar y recargar: no vive de la lista que había antes, pide
 * su papel a su puerta. Si esa puerta no contesta (sin cobertura), se dice **que no se ha podido
 * comprobar**, que no es lo mismo que decir que ese papel no está.
 */
async function abrirUnPapelDeLaBandeja(id) {
  const suyo = estadoDeLaBandeja();
  if (!id) return abrirLaBandeja();
  suyo.papel = null;
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.error = "";
  suyo.aviso = "";
  pantallaUnPapelDeLaBandeja();
  try {
    // **La lista se pide también aquí**, y no es un capricho: la ficha se puede abrir **directamente por
    // su dirección** (`#/papeles/bandeja/12`, un enlace que le mandan al agricultor), y sin la lista no
    // habría ni el vocabulario de las clases ni los otros papeles a los que este puede corregir. Son dos
    // peticiones al servidor y la pantalla sale entera, que es lo que se espera de una dirección.
    if (!suyo.datos) await recargarLaBandeja();
    suyo.papel = await apiJson(`/api/bandeja/${id}`);
    // Las clases que este papel sugiere (por su tipo) van delante; si no sugiere ninguna, se empieza por
    // el gasto, que es lo que más se enlaza.
    const clases = (suyo.datos && suyo.datos.clases) || [];
    suyo.claseElegida =
      (suyo.papel.clases_sugeridas || [])[0] || (clases[0] && clases[0].valor) || "gasto";
    suyo.claseBuscada = "";
    await buscarCandidatosDeLaBandeja();
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  pantallaUnPapelDeLaBandeja();
}

/** Pide los candidatos de la clase elegida: cosas que **ya están** en el cuaderno. */
async function buscarCandidatosDeLaBandeja() {
  const suyo = estadoDeLaBandeja();
  suyo.buscandoCandidatos = true;
  const consulta = new URLSearchParams();
  consulta.set("clase", suyo.claseElegida || "gasto");
  if (suyo.claseBuscada) consulta.set("texto", suyo.claseBuscada);
  try {
    const datos = await apiJson(`/api/bandeja/candidatos?${consulta.toString()}`);
    suyo.candidatos = datos.items || [];
  } catch (fallo) {
    suyo.candidatos = [];
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.buscandoCandidatos = false;
}

/** La subida: leer el fichero que se ha elegido y comprobar si ese mismo papel ya estaba. */
async function comprobarElFicheroDeLaBandeja() {
  const suyo = estadoDeLaBandeja();
  const entrada = document.getElementById("bandeja-fichero");
  if (!entrada || !entrada.files || entrada.files.length === 0) {
    suyo.error = t("bandeja.fichero", "");
    pantallaLaBandeja();
    return;
  }
  // Sin cobertura no se puede subir un fichero de un tirón, así que se dice claro en vez de dejar al
  // agricultor esperando delante de una barra que no avanza. Es la misma decisión que en los papeles.
  if (!navigator.onLine) {
    suyo.error = aviso("no_se_pudo");
    pantallaLaBandeja();
    return;
  }
  // **El fichero se guarda en el estado**, porque repintar la pantalla borra la casilla y hay que volver a
  // mandarlo al subirlo.
  suyo.fichero = entrada.files[0];
  suyo.nombreDelFichero = suyo.fichero.name || "";
  suyo.tipoNuevoElegido = valorDeLaCasilla("bandeja-tipo-nuevo") || "";
  suyo.comprobado = null;
  suyo.error = "";
  suyo.aviso = "";
  suyo.comprobando = true;
  pantallaLaBandeja();
  try {
    const cuerpo = new FormData();
    cuerpo.append("fichero", suyo.fichero);
    const respuesta = await fetch("/api/bandeja/comprobar", {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    const datos = await respuesta.json().catch(() => null);
    if (!respuesta.ok) throw new Error((datos && datos.detail) || mensaje("no_se_pudo"));
    suyo.comprobado = datos;
  } catch (fallo) {
    // Si no se ha podido comprobar, **no se puede subir**: el botón de subir no se pinta sin la
    // comprobación, y eso es justo lo que impide que un duplicado entre sin decirlo.
    suyo.fichero = null;
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.comprobando = false;
  pantallaLaBandeja();
}

/** Sube el papel: el fichero que ya se comprobó, con el tipo que se haya dicho. */
async function subirElPapelALaBandeja() {
  const suyo = estadoDeLaBandeja();
  if (!suyo.fichero) return pantallaLaBandeja();
  suyo.subiendo = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaLaBandeja();
  try {
    const cuerpo = new FormData();
    cuerpo.append("fichero", suyo.fichero);
    if (suyo.tipoNuevoElegido) cuerpo.append("tipo", suyo.tipoNuevoElegido);
    const respuesta = await fetch("/api/bandeja/subir", {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    const datos = await respuesta.json().catch(() => null);
    if (!respuesta.ok) throw new Error((datos && datos.detail) || mensaje("no_se_pudo"));
    suyo.aviso = (datos.avisos || []).join(" ");
    // El fichero y lo comprobado se olvidan: ya está guardado, y volver a subirlo sin querer crearía el
    // aviso de duplicado otra vez (que es lo que tiene que pasar).
    suyo.fichero = null;
    suyo.nombreDelFichero = "";
    suyo.comprobado = null;
    suyo.tipoNuevoElegido = "";
    await recargarLaBandeja();
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.subiendo = false;
  pantallaLaBandeja();
}

/**
 * Guarda lo que el agricultor ha aceptado de la lectura (`bandeja-revisar` → `bandeja-guardar`).
 *
 * Los campos salen de los `id` del formulario, que es como esta aplicación lee todo lo que se escribe, y
 * **vacío es «no lo sé»**: se manda la cadena vacía y el servidor lo guarda como nulo, que es lo que hace
 * que borrar un importe que el lector leyó mal sirva de algo.
 */
async function guardarLaRevisionDeLaBandeja() {
  const suyo = estadoDeLaBandeja();
  const id = (suyo.formulario || {}).id || (suyo.papel || {}).id;
  if (!id) return pantallaUnPapelDeLaBandeja();
  const campos = {};
  for (const campo of [
    "proveedor",
    "proveedor_nif",
    "numero_factura",
    "fecha",
    "base_imponible",
    "cuota_iva",
    "tipo_iva_pct",
    "total",
  ]) {
    campos[campo] = valorDeLaCasilla(`bandeja-${campo}`) || "";
  }
  suyo.guardando = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaUnPapelDeLaBandeja();
  try {
    const contestado = await apiJson(`/api/bandeja/${id}/revisar`, {
      method: "POST",
      body: JSON.stringify({ campos }),
    });
    suyo.aviso = (contestado.avisos || []).join(" ");
    suyo.papel = contestado.papel;
    suyo.formulario = null;
    suyo.borrador = null;
    await recargarLaBandeja();
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.guardando = false;
  pantallaUnPapelDeLaBandeja();
}

/** Una puerta del papel que solo cambia su estado: leerlo, confirmarlo, descartar la lectura o rectificar. */
async function hacerAlgoConElPapelDeLaBandeja(id, puerta, cuerpo = {}) {
  const suyo = estadoDeLaBandeja();
  if (!id) return pantallaUnPapelDeLaBandeja();
  suyo.guardando = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaUnPapelDeLaBandeja();
  try {
    const contestado = await apiJson(`/api/bandeja/${id}/${puerta}`, {
      method: "POST",
      body: JSON.stringify(cuerpo),
    });
    suyo.aviso = (contestado.avisos || []).join(" ");
    suyo.papel = contestado.papel;
    suyo.formulario = null;
    suyo.borrador = null;
    await recargarLaBandeja();
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.guardando = false;
  pantallaUnPapelDeLaBandeja();
}

/**
 * El formulario de la revisión, con sus campos puestos.
 *
 * Los valores que salen son **los que ya se han aceptado** si los hay, y si no **los que se han leído**: así
 * el agricultor corrige sobre lo que el programa propuso en vez de escribirlo todo, que es lo que hace que
 * una lectura aproveche aunque tenga una errata. Y el rótulo de cada campo es el del tipo de papel: no se
 * pregunta «¿cuál es la base imponible?» a quien está mirando un contrato.
 */
function elFormularioDeLaBandeja(cual, borrador) {
  if (!cual) return null;
  const b = t("bandeja", {});
  const br = borrador || {};
  const papel = estadoDeLaBandeja().papel || {};
  const propuesta = papel.la_propuesta || {};
  const aceptado = papel.lo_aceptado || {};
  const de = (campo) => {
    if (br[campo] !== undefined) return br[campo];
    const suyo = (aceptado.campos || {})[campo];
    if (suyo === undefined || suyo === null) return (propuesta.campos || {})[campo] || "";
    return suyo;
  };
  return {
    titulo: b.revisar_titulo,
    pista: b.revisar_pista,
    guardar: b.guardar,
    cancelar: b.cancelar,
    guardando: b.guardando,
    datos: { clase: "revision", id: papel.id || "" },
    error: "",
    bloques: [
      { tipo: "texto", id: "bandeja-proveedor", etiqueta: b.proveedor, valor: de("proveedor") },
      { tipo: "texto", id: "bandeja-proveedor_nif", etiqueta: b.nif_del_proveedor, valor: de("proveedor_nif") },
      { tipo: "texto", id: "bandeja-numero_factura", etiqueta: b.numero_de_factura, valor: de("numero_factura") },
      { tipo: "fecha", id: "bandeja-fecha", etiqueta: b.fecha, valor: de("fecha") },
      { tipo: "numero", id: "bandeja-base_imponible", etiqueta: b.base_imponible, valor: de("base_imponible") },
      { tipo: "numero", id: "bandeja-cuota_iva", etiqueta: b.cuota_de_iva, valor: de("cuota_iva") },
      { tipo: "numero", id: "bandeja-tipo_iva_pct", etiqueta: b.tipo_de_iva, valor: de("tipo_iva_pct") },
      { tipo: "numero", id: "bandeja-total", etiqueta: b.total, valor: de("total") },
    ],
  };
}

/**
 * Las 19 acciones de los botones de estas dos pantallas.
 *
 * **La 20 y la 21 (`papel-ver-todos` y `ir-inicio`) ya existían** y las atiende el manejador de siempre: por
 * eso no están aquí, y por eso la lista del informe las cuenta aparte.
 */
async function atenderLaBandeja(nombre, elemento) {
  const suyo = estadoDeLaBandeja();
  const id = Number(elemento.dataset.id || 0);
  if (nombre === "bandeja-ver") return abrirLaBandeja();
  if (nombre === "bandeja-abrir") return abrirUnPapelDeLaBandeja(id);
  if (nombre === "bandeja-comprobar") return comprobarElFicheroDeLaBandeja();
  if (nombre === "bandeja-subir") return subirElPapelALaBandeja();
  if (nombre === "bandeja-olvidar-fichero") {
    // Se olvida lo elegido y lo comprobado: es la salida de «este papel ya lo tenías», para poder elegir
    // otro fichero sin recargar la pantalla.
    suyo.fichero = null;
    suyo.nombreDelFichero = "";
    suyo.comprobado = null;
    suyo.error = "";
    return pantallaLaBandeja();
  }
  if (nombre === "bandeja-filtrar") {
    suyo.filtro = valorDeLaCasilla("bandeja-buscar");
    suyo.estadoElegido = valorDeLaCasilla("bandeja-estado") || "sin_revisar";
    suyo.tipoElegido = valorDeLaCasilla("bandeja-tipo") || "";
    await recargarLaBandeja();
    return pantallaLaBandeja();
  }
  if (nombre === "bandeja-ver-todas") {
    suyo.filtro = "";
    suyo.estadoElegido = "sin_revisar";
    suyo.tipoElegido = "";
    await recargarLaBandeja();
    return pantallaLaBandeja();
  }
  if (nombre === "bandeja-original") return descargarDocumento(id);
  if (nombre === "bandeja-leer") return hacerAlgoConElPapelDeLaBandeja(id, "leer");
  if (nombre === "bandeja-confirmar") return hacerAlgoConElPapelDeLaBandeja(id, "confirmar");
  if (nombre === "bandeja-descartar") {
    return hacerAlgoConElPapelDeLaBandeja(id, "descartar", {
      motivo: valorDeLaCasilla("bandeja-motivo-descartar"),
    });
  }
  if (nombre === "bandeja-clasificar") {
    return hacerAlgoConElPapelDeLaBandeja(id, "clasificar", {
      tipo: valorDeLaCasilla("bandeja-tipo-del-papel"),
    });
  }
  if (nombre === "bandeja-revisar") {
    // Abre el formulario con lo que ya hay puesto (lo aceptado o lo leído). No guarda nada todavía.
    suyo.formulario = { clase: "revision", id };
    suyo.borrador = {};
    return pantallaUnPapelDeLaBandeja();
  }
  if (nombre === "bandeja-guardar") return guardarLaRevisionDeLaBandeja();
  if (nombre === "bandeja-cancelar") {
    suyo.formulario = null;
    suyo.borrador = null;
    return pantallaUnPapelDeLaBandeja();
  }
  if (nombre === "bandeja-buscar-candidatos") {
    suyo.claseElegida = valorDeLaCasilla("bandeja-clase") || suyo.claseElegida;
    suyo.claseBuscada = valorDeLaCasilla("bandeja-candidato-buscar") || "";
    await buscarCandidatosDeLaBandeja();
    return pantallaUnPapelDeLaBandeja();
  }
  if (nombre === "bandeja-enlazar") {
    const elegido = valorDeLaCasilla("bandeja-candidato");
    if (!elegido) return pantallaUnPapelDeLaBandeja();
    // El candidato se manda con **su clase y su identificador**: la clase va en el dato del desplegable
    // (`clase:entidad_id`), como en la conciliación del banco, así que no hay que adivinarla.
    const corte = elegido.indexOf(":");
    return hacerAlgoConElPapelDeLaBandeja(id, "vincular", {
      clase: elegido.slice(0, corte),
      entidad_id: Number(elegido.slice(corte + 1)),
    });
  }
  if (nombre === "bandeja-desenlazar") {
    return hacerAlgoConElPapelDeLaBandeja(id, "desvincular", {
      clase: elemento.dataset.clase,
      entidad_id: Number(elemento.dataset.entidad),
    });
  }
  if (nombre === "bandeja-rectificar") {
    const alQueCorrige = valorDeLaCasilla("bandeja-rectifica-a");
    if (!alQueCorrige) return pantallaUnPapelDeLaBandeja();
    return hacerAlgoConElPapelDeLaBandeja(id, "rectificar", {
      rectifica_a_id: Number(alQueCorrije),
    });
  }
}
```

### 3.7 `backend/web/react/rutas.js` — la dirección de la bandeja

Va **después** de `{ clave: "papeles", patron: ["papeles"] }` (línea ~194). **El tramo de texto fijo va
antes que el identificador**, como en todas las familias de esa tabla.

<!-- bloque: rutas -->
```javascript
  // **La bandeja documental (T08, S10, 06/10/2026).** La lista vive **dentro de la familia de los
  // papeles** (`#/papeles/bandeja`), que es el renglón del menú del que sale: la bandeja es lo que llega
  // y hay que revisar, y «los papeles» es lo que ya está archivado. Se reconstruye entera al abrir su
  // dirección —pide sus datos al servidor—, así que se puede enlazar, recargar y mandar a quien ayuda.
  // Y el tramo de texto fijo va **antes** que el identificador, como en todas las familias: si no,
  // `#/papeles/bandeja` se leería como un papel llamado «bandeja», que no existe.
  { clave: "bandeja", patron: ["papeles", "bandeja"] },
  // Y **la ficha de un papel tiene su dirección** (`#/papeles/bandeja/12`): al recargarla se vuelven a
  // pedir al servidor su propuesta, sus enlaces y sus candidatos, así que no sale vacía. Lo que **no**
  // tiene dirección son sus formularios (la revisión de lo que queda y la comprobación del fichero que se
  // está subiendo): al recargar saldrían vacíos, y eso es peor que no tener dirección.
  { clave: "bandeja_papel", patron: ["papeles", "bandeja", ":id"] },
```

### 3.8 `backend/web/service-worker.js` — el fichero en la caché, y la versión

Dentro de `FICHEROS`, junto a `bancos.js`. Y **la caché sube de número** (`CACHE`, línea 277) y también la
versión de `app.js` (`VERSION_DE_LA_APLICACION`), que tienen que ser **la misma cadena** (lo exige
`tests/test_la_version_visible.py`).

<!-- bloque: service-worker -->
```javascript
  // La bandeja documental (T08, S10, 06/10/2026): lo que llega y hay que revisar, y la ficha de un papel,
  // las dos en un fichero. Se guarda para el campo por el mismo motivo que las cuentas: un papel se mira
  // en la nave y en el despacho, y una pantalla que no está en la caché es un hueco justo cuando hay que
  // decidir si un papel entra en el cuaderno.
  "/react/pantallas/bandeja.js",
```

```javascript
// Y las dos versiones, que tienen que ser la MISMA cadena:
//   · service-worker.js:  const CACHE = "cuedigital-2026-10-06-71";
//   · app.js:             const VERSION_DE_LA_APLICACION = "2026-10-06-71";
```

### 3.9 `docs/REACT.md` — la fila de la pantalla

En la tabla de pantallas migradas, **con la forma que tienen sus filas** (dos columnas: qué es y en qué
estado), después de la del banco (línea ~171):

<!-- bloque: react-md -->
```markdown
| **La bandeja de los papeles, y la ficha de un papel** (`backend/web/react/pantallas/bandeja.js`) | ✅ En React (T08) |
```

Y en el párrafo que cuenta cuántas son («Y desde el T06 son treinta y siete…»), el número sube en dos:
**treinta y nueve** (la lista y la ficha), y se añaden a la frase que las nombra. Las dos se reconstruyen
enteras al abrir su dirección, así que van también en `PANTALLAS_EN_REACT`, en la caché del service worker
y en la tabla de `rutas.js` (los bloques 3.6, 3.7 y 3.8).

### 3.10 `app/main.py`, `app/routers/interfaz.py` y el botón que entra desde «los papeles»

Sin esto, las puertas no existen y la pantalla sale **con todas sus palabras en blanco**.

<!-- bloque: main-include -->
```python
# 1) En el `from .routers import (…)` de `main.py`, en su sitio por orden alfabético (después de
#    `analiticas_api`):
    bandeja_api,

# 2) Y el router, al final de los `include_router` (después de `trabajos_api`):
# **La bandeja documental (T08, S10, 06/10/2026).** Lo que llega y hay que revisar: subir el papel tal y
# como llega, leerlo, confirmar lo que el agricultor acepta y decir con qué va. Va detrás de
# `documentos_api` porque el papel que guarda es el mismo (`documentos_anexos`) y usa sus puertas para el
# alta y para el fichero, y detrás de `extractos_api` porque un papel se puede enlazar con un movimiento
# conciliado.
app.include_router(bandeja_api.router)
```

<!-- bloque: interfaz -->
```python
# 3) En `app/routers/interfaz.py`, dentro del vocabulario que devuelve `interfaz()` (después de
#    `"bancos": textos.BANCOS,`):
        # **La bandeja documental (T08, S10, 06/10/2026).** Sin esto, la pantalla sale con todos sus
        # botones y sus rótulos en blanco. Y va **aquí** y no solo dentro de la respuesta de
        # `/api/bandeja` por el mismo motivo que los del banco: la ficha de un papel se abre directamente
        # por su dirección (`#/papeles/bandeja/12`) y entonces no hay ninguna lista que traiga sus
        # palabras; y porque esto se guarda en el móvil (`localStorage`, la clave `cuedigital.interfaz`),
        # así que la pantalla sigue teniendo sus palabras **sin cobertura**, que es justo cuando se miran
        # los papeles (en la nave, con el móvil en la mano).
        "bandeja": textos.BANDEJA,
```

<!-- bloque: documentos-boton -->
```python
# 4) El texto del botón, en `app/textos.py`, dentro de `DOCUMENTOS`:
    "bandeja": "LA BANDEJA: LO QUE HAY QUE REVISAR",
```

```javascript
// 5) Y el botón, en `backend/web/react/pantallas/documentos.js` (en la barra de abajo, antes de
//    `maestros.titulo`). Es la puerta de entrada a la bandeja: la lista de lo que llega cuelga del renglón
//    de «los papeles», y desde aquí es donde se entra, como el banco se entra desde las cuentas.
      <${Boton} etiqueta=${d.bandeja} accion="bandeja-ver" clase="boton-claro" />
```

### 3.11 Las pruebas compartidas que cambian (y por qué)

Integrar esto **pone en rojo tres cosas de pruebas que ya existían**, y las tres son buenas noticias: cada
una está escrita para avisar de exactamente esto. La cuarta fila de la tabla no se pone roja, y se dice para
que nadie la busque.

| Fichero y prueba | Qué pasa | Qué hay que poner |
|---|---|---|
| `tests/test_los_papeles_y_las_facturas_se_pueden_corregir.py::test_lo_que_una_correccion_no_toca_es_lo_que_el_formulario_no_manda` | el papel tiene nueve columnas nuevas que el formulario de corregir no manda | la lista pasa a `["fichero_nombre", "fichero_ruta", "fichero_tipo", "fichero_bytes", "huella", "estado_revision", "propuesta", "como_se_leyo", "propuesta_descartada", "datos_confirmados", "confirmado_en", "confirmado_por_usuario_id", "rectifica_a_id"]` |
| El mismo fichero, `test_lo_que_apunta_a_un_papel_es_la_inspeccion_de_una_maquina` | hay una **tercera** tabla que apunta a un papel | la lista pasa a `["conciliaciones_de_movimiento", "inspecciones_de_maquina", "vinculos_de_documento"]`, y en su docstring se dice por qué: un papel que está enlazado con un gasto o con una máquina no se puede borrar sin dejar el vínculo apuntando a algo que ya no está (lo que sí se puede es **anular** el papel) |
| `tests/test_los_botones_hacen_algo.py::test_cada_accion_que_se_pinta_la_atiende_alguien` | la pantalla pinta 19 acciones que `app.js` todavía no conoce | se arregla **integrando el bloque 3.6** (no hay que tocar la prueba) |
| `tests/test_sin_jerga.py::test_los_textos_que_llevan_cuenta_tienen_singular_y_plural` | **no se pone rojo**, y se dice para no confundir | conviene añadir `(textos.BANDEJA, "cuantos", "la bandeja de los papeles")` a su lista, para que la regla del singular siga cubriendo el texto nuevo (el plural y el singular están escritos, y hay una prueba en `test_bandeja.py` que lo exige) |

Y **dos que pueden dar la lata y no la dan**, comprobadas de verdad en la corrida del apartado 2.3 (no es
una suposición): `test_documentos.py` **pasa entero** con los cuatro tipos nuevos y con el texto del botón
que entra a la bandeja —`test_los_tipos_se_sirven_con_su_nombre` compara los tipos servidos con
`catalogos.TIPOS_DOCUMENTO` y está escrita así a propósito—, y `test_t14_maquinaria.py` también: el
certificado que apunta como «otros» **se puede seguir apuntando como «otros»** (el tipo nuevo se **añade**,
no sustituye), y su propia prueba lo dice mientras esperaba este ticket.

---

## 4. Lo que NO he podido comprobar, y por qué

### 4.1 El recorrido por la API, tal y como lo cuenta la suite

`tests/test_bandeja.py` **se salta** las pruebas del recorrido por la API mientras falte la integración, en
vez de dar un verde que no comprueba nada (el patrón del T13 y del T20). Lo que falta, exactamente:

* en `app/models.py`: las columnas `DocumentoAnexo.huella`, `estado_revision`, `propuesta`, `como_se_leyo`,
  `propuesta_descartada`, `datos_confirmados`, `confirmado_en`, `confirmado_por_usuario_id` y
  `rectifica_a_id`, y la tabla `VinculoDeDocumento`;
* en `app/schemas.py`: los ocho esquemas del apartado 3.3 (sin ellos **no se puede ni importar el
  router**: `from ..schemas import …`);
* en `app/textos.py`: `BANDEJA` y los mensajes `T08_*` (sin ellos, la primera puerta que hable revienta);
* en `app/catalogos.py`: los cuatro tipos nuevos (sin ellos, subir un certificado de inspección contesta
  422).

La prueba que lo comprueba (`TestLoQueFaltaEstaDicho`) lee **de verdad** `app.models` con `hasattr`: el día
que se integre, dice que no falta nada sola, sin que nadie se acuerde de tocar el fichero de pruebas.

### 4.2 La pantalla en un navegador de verdad

**No se ha abierto en un navegador**, y no se puede: `app.js` (que es quien monta la pantalla, escribe la
dirección y atiende los clics) lo integra el coordinador y este ticket no lo toca. Lo que sí está
comprobado es lo que se puede comprobar sin navegador: el HTML que produce el componente (30 pruebas con
`renderToStaticMarkup`), que ninguna frase esté escrita a mano, que las claves que lee existan, y que las
acciones que pinta estén todas en la lista del informe.

Lo que **queda por ver** en un navegador, y conviene mirarlo al integrar: que el `<input type="file">` de
la subida siga teniendo su fichero después de repintar (el estado lo guarda `app.js`, que es el único sitio
donde puede estar), y que los `data-` de los botones de quitar un enlace (`data-clase` y `data-entidad`)
lleguen como los lee `atenderLaBandeja`. El valor del desplegable de candidatos (`clase:identificador`) sí
está comprobado: hay una prueba de la pantalla que exige que salga así en el HTML.

### 4.3 La lectura de una foto de verdad (y la precisión del lector)

**No se ha medido** si la lectura acierta, y es una decisión del ticket, no un olvido: el corpus para
medirlo es el T07, que está bloqueado. Lo que sí se ha comprobado es que **la pantalla no lo afirma**:
ningún porcentaje, ninguna «confianza», ninguna frase que diga que está bien leído (hay una prueba que lo
muerde en las dos mitades, la de Python y la de la pantalla).

Lo que **no** se ha podido probar: leer un PDF escaneado o una foto con el lector de letras instalado
(`tesseract`), porque en este ordenador no está. El camino del lector es el que ya existía
(`facturas.leer_factura`), así que lo que se prueba es que la bandeja **lo usa** y que cuando no hay
lector lo dice en vez de inventarse nada.

### 4.4 El recorrido con las 64 tierras del agricultor

Se ha probado contra una base vacía, con un gasto, una máquina y una inspección de mentira. **No se ha
probado** con los datos reales de la finca: `backend/cuedigital.db` **no se ha abierto, ni leído, ni
copiado**, como pide el encargo. Lo que podría notarse con datos de verdad: la lista de candidatos para
enlazar (se ofrecen **los 50 más nuevos** de cada clase, y hay un buscador por texto), y el rendimiento de
la bandeja con muchos papeles (hoy pide las rectificaciones y los vínculos de cada papel de la lista; con
cientos de papeles habría que mirarlo).

---

## 5. Lo que he decidido, y conviene no deshacer

1. **La bandeja no es una tabla nueva de papeles: es una vista del mismo papel.** Un papel vive en
   `documentos_anexos` con su fichero y su carpeta, y lo que añade el T08 son columnas suyas (huella,
   estado, propuesta, lo aceptado). Dos tablas habrían acabado con el mismo contrato en dos sitios y uno
   de los dos viejo.
2. **`confirmar` no acepta campos.** La regla «el programa propone y el agricultor confirma» está metida
   en la forma de las puertas, no en un aviso: sin `revisar` antes, `confirmar` contesta 409. No hay que
   «arreglarlo» añadiéndole campos por comodidad.
3. **La huella se calcula al subir y no se recalcula nunca.** No es un detalle de rendimiento: recalcularla
   al confirmar es lo que haría que un fichero cambiado por debajo dejara de parecer el mismo papel.
4. **Los cuatro tipos nuevos se añaden a los cuatro de siempre.** `inspeccion` es el que el T14 dejó
   pedido por escrito. Y los papeles que ya existían **no cambian de tipo** al migrar: se quedan como
   estaban.
5. **Enlazar no crea nada**, y la única excepción está dicha y probada: enlazar un certificado con su
   inspección rellena `InspeccionDeMaquina.documento_id`, que es el campo que ya existía y que enseña la
   ficha de la máquina. Si esa inspección ya tiene su papel, se contesta 409 en vez de pisarlo.
6. **Un papel puede estar enlazado con varias cosas a la vez**, y por eso hay una tabla de vínculos y no
   seis columnas. Y desvincular **borra la fila** (dejando el rastro en la auditoría): una fila «quitada»
   contaría como dependencia del papel para siempre e impediría borrarlo con un motivo que ya no es verdad.
7. **Las rectificativas dejan las dos, y la relación se guarda solo en la rectificativa** (`rectifica_a_id`).
   «Esta está rectificada» se **deduce**; dos columnas que se apunten la una a la otra acabarían diciendo
   cosas distintas.
8. **La propuesta y lo aceptado van en dos columnas distintas** (`propuesta` y `datos_confirmados`), y no
   en los campos del papel. Es lo que permite ver la diferencia entre lo que el programa propuso y lo que
   el agricultor aceptó, y lo que hace que revisar no sea confirmar.
9. **No hay ninguna medida de la calidad de la lectura, en ningún sitio.** Ni en la base, ni en la API, ni
   en la pantalla. Lo único que se dice de una línea es si **su cuenta cuadra**, que es aritmética. Si
   alguien quiere poner un porcentaje, antes hace falta el corpus del T07.
10. **La pantalla obedece al servidor en los tres `se_puede_*`.** No decide por su cuenta si se puede
    confirmar: lo pregunta. Así el recorrido no se puede saltar desde el navegador.
11. **La lista solo enseña lo que ha pasado por la bandeja** (los papeles con estado de revisión), no los
    papeles viejos que el agricultor ya tenía: si no, abrir esta pantalla por primera vez le enseñaría dos
   cientos de papeles que no ha subido hoy.
12. **No hay tabla de escritorio** (`.solo-escritorio`), a diferencia de las otras listas: la bandeja es una
    cola de lo que acaba de llegar, con cuatro o cinco papeles, y una tabla de doce columnas para cinco
    filas no ayuda a nadie. Se dice aquí para que no parezca un olvido.

---

## 6. Lo que `app.js` tiene que preparar, campo por campo

### 6.1 La lista — `pantallaDeLaBandeja(propiedades)`

| Propiedad | De dónde sale | Qué es |
|---|---|---|
| `textos` | `{bandeja: t("bandeja"), acciones: {volver}}` | el vocabulario entero |
| `papeles` | `GET /api/bandeja` → `papeles` | los papeles, cada uno con su estado y lo que le falta |
| `tipos` | ídem → `tipos` | `[{valor, etiqueta}]`, los ocho tipos de papel |
| `estados` | ídem → `estados` | `[{valor, etiqueta}]`, para el desplegable |
| `clases` | ídem → `clases` | `[{valor, etiqueta}]`, las seis clases de vínculo |
| `resumen` | ídem → `resumen` | el pie ya compuesto («Tienes 7 papeles…») o la frase de bandeja vacía |
| `cuantos` | ídem → `cuantos` | cuántos papeles se están enseñando |
| `sinDecirDeQueEs` | ídem → `sin_decir_de_que_es` | cuántos están recién subidos, sin tipo |
| `estadoElegido`, `tipoElegido`, `filtro` | estado de `app.js` | lo que está puesto en los dos desplegables y en el buscador |
| `ficheroElegido`, `tipoNuevoElegido` | estado de `app.js` | el fichero que se está subiendo y el tipo que se le ha dicho |
| `comprobado` | `POST /api/bandeja/comprobar` | la huella, el tamaño y si ese papel ya estaba (**no guarda nada**) |
| `comprobando`, `subiendo`, `guardando` | estado de `app.js` | lo que está en marcha |
| `formulario` | `app.js` (`elFormularioDeLaBandeja`) | el formulario abierto, o `null` |
| `error`, `aviso` | estado de `app.js` | lo que ha dicho el servidor, malo y bueno |

### 6.2 La ficha — `pantallaDeUnPapelDeLaBandeja(propiedades)`

| Propiedad | De dónde sale | Qué es |
|---|---|---|
| `textos` | como arriba | el vocabulario |
| `papel` | `GET /api/bandeja/<id>` | el papel con su estado, su original, su propuesta, lo aceptado, sus enlaces y sus rectificaciones |
| `candidatos` | `GET /api/bandeja/candidatos?clase=…&texto=…` → `items` | `[{valor, texto}]`, donde **`valor` es `clase:identificador`** (`gasto:12`): lo que se elige lleva consigo de qué es, y el botón de enlazar no depende de otro campo. Lo único que `app.js` tiene que hacer con él es partirlo por los dos puntos |
| `papelesParaRectificar` | `GET /api/bandeja?estado=todos` → `papeles` | `[{valor, texto}]`: los otros papeles, sin el propio |
| `clases` | `GET /api/bandeja` → `clases` | las seis clases, para el desplegable |
| `claseElegida`, `claseBuscada` | estado de `app.js` | con qué clase se está buscando y qué se ha escrito |
| `buscandoCandidatos`, `guardando`, `cargando` | estado de `app.js` | lo que está en marcha |
| `formulario` | `app.js` | la revisión abierta, o `null` |
| `error`, `aviso` | estado de `app.js` | lo que ha dicho el servidor |

**Dos cosas que `app.js` tiene que escribir y no vienen del servidor:** `texto_fecha` (la fecha del papel)
y `texto_confirmado_en` (cuándo se confirmó), las dos con `formateaFecha`. Los importes **no**: el servidor
manda `campos` (el dato) y `textos` (el mismo, escrito).

### 6.3 Las 21 acciones que pinta la pantalla

Las 19 nuevas, una por una, con lo que tiene que hacer `app.js` (el bloque 3.6 las implementa entero):

| Acción | Dónde sale | Qué tiene que hacer |
|---|---|---|
| `bandeja-comprobar` | la subida | leer el fichero de `#bandeja-fichero`, guardarlo **en el estado** y mandarlo a `POST /api/bandeja/comprobar` |
| `bandeja-subir` | la subida, **solo si no es duplicado** | mandar el mismo fichero con el tipo a `POST /api/bandeja/subir` y recargar la lista |
| `bandeja-olvidar-fichero` | la subida | olvidar el fichero y lo comprobado, para poder elegir otro |
| `bandeja-abrir` | la lista y el aviso del duplicado | abrir `GET /api/bandeja/{id}` (la ficha) |
| `bandeja-filtrar` | la lista | recargar con lo que hay en `#bandeja-buscar`, `#bandeja-estado` y `#bandeja-tipo` |
| `bandeja-ver-todas` | la lista | quitar el filtro y volver a los que están sin revisar |
| `bandeja-ver` | la ficha | volver a la lista (que se reconstruye entera) |
| `bandeja-clasificar` | la ficha | `POST …/clasificar` con el tipo de `#bandeja-tipo-del-papel` (saca el papel de «recién subido») |
| `bandeja-leer` | la ficha | `POST …/leer`: lee el original y guarda **la propuesta** |
| `bandeja-revisar` | la ficha | abrir el formulario de la revisión, con lo aceptado o lo leído ya puesto |
| `bandeja-guardar` | el formulario | leer sus campos y mandarlos a `POST …/revisar` (vacío es «no lo sé») |
| `bandeja-cancelar` | el formulario | cerrarlo sin guardar nada |
| `bandeja-confirmar` | la ficha, **solo si el servidor dice que se puede** | `POST …/confirmar`, sin campos |
| `bandeja-descartar` | la ficha | `POST …/descartar` con el motivo de `#bandeja-motivo-descartar` |
| `bandeja-buscar-candidatos` | la ficha | `GET /api/bandeja/candidatos` con la clase de `#bandeja-clase` y el texto de `#bandeja-candidato-buscar` |
| `bandeja-enlazar` | la ficha | partir el valor de `#bandeja-candidato` (`clase:entidad_id`) y mandarlo a `POST …/vincular` |
| `bandeja-desenlazar` | la ficha | `POST …/desvincular` con la clase y el identificador de sus `data-` |
| `bandeja-rectificar` | la ficha | `POST …/rectificar` con el papel elegido en `#bandeja-rectifica-a` |
| `bandeja-original` | la ficha | descargar el original: **la puerta que ya existe** (`descargarDocumento(id)`, T01) |

Y las dos que **ya existían** y no hay que tocar: `papel-ver-todos` (ir a «los papeles») e `ir-inicio`.

**Los `id` de los campos que `app.js` lee por su nombre** (si uno cambia, el formulario se guarda vacío sin
que salte nada): `bandeja-fichero`, `bandeja-tipo-nuevo`, `bandeja-tipo-del-papel`, `bandeja-buscar`,
`bandeja-estado`, `bandeja-tipo`, `bandeja-motivo-descartar`, `bandeja-clase`, `bandeja-candidato-buscar`,
`bandeja-candidato`, `bandeja-rectifica-a` y los ocho del formulario de la revisión
(`bandeja-proveedor`, `bandeja-proveedor_nif`, `bandeja-numero_factura`, `bandeja-fecha`,
`bandeja-base_imponible`, `bandeja-cuota_iva`, `bandeja_tipo_iva_pct`, `bandeja-total`).

---

## 7. Lo que NO se hace, y la pantalla lo dice

* **No se mide la calidad de la lectura.** Ni porcentaje, ni «confianza», ni «leído correctamente». La
  pantalla dice, con esas palabras, que **no se puede medir** y por qué (no hay colección de facturas de
  verdad con la que comparar). Es el T07, y está bloqueado.
* **No se acepta nada solo.** Ni el tipo, ni la fecha, ni el importe, ni la propuesta: el programa propone
  y el agricultor confirma, y mientras no lo confirme el papel está **sin revisar** y se ve.
* **No se crea nada al enlazar.** Ni un gasto, ni una factura, ni una venta. Hay una prueba que lo
  comprueba por el lado del servidor (el gasto sigue siendo 1) y otra por el lado de la pantalla (no hay
  ninguna acción que ofrezca crear algo).
* **No se borra nada al rectificar.** Las dos versiones quedan, la corregida marcada.
* **No se reescribe el original.** Ni al leer, ni al revisar, ni al confirmar, ni al rectificar.
