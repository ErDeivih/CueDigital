# Revisión independiente del T10 — semillas, foto de etiqueta y asignación a siembra

**Quién y cuándo.** Revisor independiente, sin escribir funcionalidad. La revisión se hizo el
**02/10/2026 entre las 19:13 y las 19:45** (hora local). El árbol **se movía mientras se revisaba**: el
agente del T10 seguía editando, y de hecho **ha ido arreglando los hallazgos de esta revisión sobre la
marcha** (entre las 19:35 y las 19:40). Por eso el informe está anclado a **dos fotos** con su hora y su
huella, y cada cosa dice de qué foto es.

**Qué he hecho.** He leído el ticket, el código, las pruebas del ticket, las pantallas nuevas y las dos
revisiones anteriores; y he escrito **un fichero de pruebas** que intenta romper los nueve contratos del
encargo. **49 pruebas**, y a las 19:41 pasa 48 y falla 1.

**Los dos ficheros nuevos (y los únicos que he creado dentro del repositorio):**

- `backend/tests/test_revision_t10.py` — las pruebas de esta revisión (las que fallan están marcadas
  `DEFECTO` y llevan escrito qué le pasaría al agricultor).
- `docs/REVISION_T10.md` — este documento.

**Ningún fichero que ya existía se ha modificado.** No he abierto `backend/cuedigital.db` para escribir
ni lo he usado para pruebas, y **no lo he copiado** (no hacía falta: en la finca real no hay ninguna
semilla). Comprobado al terminar: **446.464 bytes**, `mtime` 30/09/2026 18:05:33, sha256
`71456B0B1E1FE444593939571F16580E5702C53047185837DC270ABF3696BA0D` — la misma huella que se me dio.

---

## 1. Cómo se ejecuta y qué sale

```bash
cd backend
../.venv/Scripts/python.exe -m pytest tests/test_revision_t10.py -q --junit-xml=$env:TEMP\rev10.xml
```

| Foto | Hora | `test_revision_t10.py` | `test_semillas.py` (el del ticket) |
|---|---|---|---|
| **A** (lo que se revisó) | 19:29 | **48 pruebas, 8 fallos**, 0 errores | 45 pruebas, 0 fallos, 0 saltadas |
| **B** (después de sus arreglos) | 19:41–19:42 | **49 pruebas, 1 fallo** (el defecto 9) | **52 pruebas, 0 fallos** (ha añadido 7) |

Y lo que se ha medido de lo que dice el documento del ticket:

| Lo que dice el documento | Lo que he medido | ¿Cuadra? |
|---|---|---|
| «45 pruebas propias», 0 fallos, 0 saltadas | foto A: **45 pruebas, 0 fallos, 0 saltadas**. La que se salta si no hay lector de fotos **se ejecutó** (Tesseract está puesto aquí) | Sí |
| «805 pruebas de JavaScript, 805 en verde» | `node --test "tests_js/*.test.js"`: **805, 805 en verde**, 0 saltadas (68,8 s) | Sí |
| «3534 pruebas de Python en la suite entera, 1 saltada» | foto A (19:22, con mi fichero dentro): **3584 pruebas, 1 saltada, 9 fallos**; otra vez a las 19:30–19:35: **3588, 1 saltada, 9 fallos**. El número se mueve porque los dos agentes seguían añadiendo pruebas: el documento ya avisa de eso | Casi |

> **Los fallos de más en la suite completa de la foto A eran del propio repositorio, no míos**:
> `test_ficheros_de_texto.py` se puso rojo **dos veces** por un fichero
> `backend/web/_comprobacion_movil_390.html` que estaba en ese momento dentro de `backend/web/` (lleva
> marca de orden de bytes y una línea con los acentos estropeados). Lo escribe el guion de navegador del
> T10 mientras mide la pantalla estrecha, y lo borra al terminar: **a las 19:29 el guardián estaba verde
> otra vez**. Lo dejo escrito con las dos horas porque es exactamente el caso de «esto fallaba cuando lo
> medí y ya no falla».

---

## 2. Las dos fotos del árbol

### Foto A — 19:13 a 19:29 (lo que se revisó; aquí existían los 8 defectos)

| Fichero | Bytes | Hora | sha256 (16 primeros) |
|---|---|---|---|
| `backend/app/routers/semillas_api.py` | 46801 | 18:34:25 | `077F987F3AD50CE1` |
| `backend/app/semillas.py` | 27562 | 18:32:38 | `2DC5C02C9AB9EAD1` |
| `backend/app/models.py` | 115531 | 18:21:36 | `20A89059E1226179` |
| `backend/app/schemas.py` | 101112 | 18:37:35 | `58FC56DDCB972403` |
| `backend/app/textos.py` | 312131 | 18:56:00 | `3137CE11981B2D1B` |
| `backend/app/servicios.py` | 106666 | 18:25:09 | `93C9BD8D789F9111` |
| `backend/app/routers/almacen_api.py` | 66192 | 17:08:01 | `405A4498A5A66DA4` |
| `backend/tests/test_semillas.py` | 49684 | 18:33:52 | `AA5EAC00E11BF1F9` |
| `backend/web/app.js` | 669656 → 669825 | 19:17:22 → 19:22:22 | `E17FAF2F…` → `18FCE2DCEE1B53E0` |
| `backend/web/react/pantallas/siembras.js` | 13025 | 18:55:34 | `17307898C35421F5` |
| `docs/T10_SEMILLAS.md` | 25001 | 19:08:46 → 19:16:00 | `31B6BC31608AB39C` |

### Foto B — 19:41 (después de que el T10 arreglara, citando esta revisión)

| Fichero | Bytes | Hora | sha256 (16 primeros) |
|---|---|---|---|
| `backend/app/routers/semillas_api.py` | **53248** | 19:38:08 | `ED692C307DF1548A` |
| `backend/app/semillas.py` | **30929** | 19:35:06 | `C6B8A16AAF241399` |
| `backend/app/textos.py` | **312702** | 19:37:59 | `301CFACD6B046E47` |
| `backend/app/routers/almacen_api.py` | **66842** | 19:38:31 | `298B20AB07847D96` |
| `backend/web/app.js` | **671207** | 19:39:40 | `B6DE20ED23F2C4D6` |
| `backend/web/react/pantallas/siembras.js` | **14202** | 19:39:20 | `FEAB955151C76374` |
| `backend/tests/test_semillas.py` | **59160** | 19:40:31 | (52 pruebas) |
| `docs/T10_SEMILLAS.md` | 25001 | 19:16:00 | `31B6BC31608AB39C` (sin cambios) |

> **Las líneas de fichero que se citan en el apartado 4 son de la foto A**, y esos ficheros ya no dicen
> eso. Cada defecto lleva además el sitio del arreglo en la foto B.

---

## 3. Tabla de lo probado, contrato por contrato

| # | Contrato del encargo | ¿Probado? | Cómo | Resultado |
|---|---|---|---|---|
| 1 | **La cantidad total no es la dosis por hectárea, y los litros no son los kilos** | Sí, a fondo | 6 pruebas en `TestContrato1_LaCantidadNoEsLaDosis`: dosis sin superficie (no se inventa el total), `dosis × ha` calculado y avisado con la cuenta entera, las dos cifras en columnas distintas leídas de nuevo por la API, litros con kilos, el viaje de ida y vuelta del redondeo y cantidad negativa (422) | **Bien**: no he podido confundir las dos cifras por la API, y el total sólo se calcula si hay superficie. En la foto A el aviso de la cuenta **no llegaba a la pantalla** (defecto 8, ya arreglado) |
| 2 | **La semilla sale del almacén y sale UNA sola vez, por la puerta que ya existía** | Sí, a fondo | 10 pruebas en `TestContrato2_LaSemillaSaleUnaVez`: la salida con `origen_tipo="siembra"` contada en la base, la puerta a mano rechazando decir «viene de una siembra» (400), el reenvío de la misma clave, la corrección sin tocar la cantidad, la corrección de la cantidad (una viva y una tachada), anular y volver a apuntar, una segunda salida con otro envase, el mismo envase, la secuencia entera y **los litros con los kilos en el saldo del almacén** | **Dos agujeros en la foto A** (defectos 1 y 2), **los dos arreglados en la foto B**. Los controles (misma clave, mismo envase) pasaban ya en la foto A |
| 3 | **La foto de la etiqueta propone, no afirma** | Sí | 6 pruebas en `TestContrato3_LaFotoPropone`: leer no escribe (lista de semillas vacía, almacén vacío y **ni un fichero nuevo en la carpeta de adjuntos**, mirando el disco), lo que no viene se queda vacío y `tratada` no se convierte en «no», una etiqueta que no habla del tratamiento, la negación, y la unidad que se lee frente a la que ofrece la pantalla | La lectura no escribe nada: **bien**. Tres fallos: la negación se leía al revés (defecto 3, arreglado), la unidad se guardaba como `kgporhectarea` (defecto 4, arreglado) y **queda abierto** el defecto 9 (`l/ha` frente a `L/ha`) |
| 4 | **Un dato ausente no es cero** | Sí | 3 pruebas en `TestContrato4_UnDatoAusenteNoEsCero`: seis campos vacíos que siguen vacíos, la caducidad que no consta (`caducado: null`, ni sí ni no) y una semilla sin ninguna entrada en el almacén | Los campos de la etiqueta y la caducidad **bien**; el saldo decía **0,0** (defecto 5, arreglado) |
| 5 | **Aislamiento entre explotaciones (404, no 403)** | Sí | 7 pruebas en `TestContrato5_DeOtraFincaNoSeVeNada`, con una segunda cuenta y sus identificadores reales: corregir la siembra, subir la foto, sembrar en mi tierra, colgar la etiqueta a mi artículo, descontar de mi envase, preguntar por mi tierra en el listado, y las dos listas | **Bien en las dos fotos**: los siete dan **404** (ninguno 403) y la finca del vecino no ve nada mío. Es la parte más sólida del ticket |
| 6 | **Corregir y anular sin duplicar** | Sí | 7 pruebas en `TestContrato6_CorregirYAnular`: el recorrido entero (apuntar → corregir → anular → volver a apuntar → reenviar) con el almacén a la vista, la siembra corregida que no queda dos veces, anular que devuelve al almacén **sin tocar el libro** (mismo movimiento, mismo id, mismo importe, `anulado` en falso), corregir una anulada (409), anular dos veces (409), la corrección parcial sin fecha y el cambio de semilla | La secuencia entera **cuadra** y el libro no se toca. Los dos fallos (fecha perdida y cambio de semilla en silencio) están **arreglados** en la foto B |
| 7 | **Los textos viven en `textos.py` y ninguno lleva jerga** | Sí | 4 pruebas en `TestContrato7_LosTextos`: `/api/interfaz` sirve el bloque `semillas` y las dos listas de unidades; las **158 frases** de `SEMILLAS` (125 claves) y `MENSAJES_DE_LAS_SEMILLAS` (33) pasan por `palabras_prohibidas_encontradas`; todos los códigos que usa el router existen en `textos.py`; y **todos los `mensaje("SM…")` que usa la pantalla están en lo que sirve `/api/interfaz`** | **Bien**. Y el guardián de los códigos **cazó una rotura real** a las 19:36 (apartado 5) |
| 8 | **Nada de cifras inventadas** | Sí | 4 pruebas en `TestContrato8_LaPantallaNoCalcula`: las dos pantallas nuevas no hacen ninguna cuenta con la dosis, la superficie ni el total; la tarjeta pinta las cifras y las unidades del servidor y su «no descuenta porque»; el aviso de lo calculado sólo existe en la respuesta de guardar; y qué hace la pantalla con ese aviso | Las pantallas **no calculan nada**: bien. El aviso de la cuenta que hace el servidor **se tiraba antes de pintar** (defecto 8, arreglado) |
| 9 | **Firmas y auditoría intactas** | Sí | 2 pruebas en `TestContrato9_FirmasYAuditoria`: la huella y el estado de la firma antes y después de apuntar una siembra (que mueve el almacén), y el rastro de auditoría de apuntar y anular | **Bien**: la huella no cambia. (Matiz en el apartado 6: no cambia porque **una siembra no entra en el fichero que se firma**) |

---

## 4. Defectos confirmados en la **foto A** (los 8 que encontré)

Todos se demuestran con una prueba de `backend/tests/test_revision_t10.py` que **fallaba** mientras el
defecto existía (medido a las 19:29, contra los ficheros de la tabla de la foto A). **Todos los datos de
estas pruebas son sintéticos**: se montan por las puertas de verdad de la API (registro, albarán, tierra,
semilla, siembra) sobre la base temporal que crea `tests/conftest.py` — no hay más remedio: en la finca
real no hay ni una semilla. **Ninguna prueba toca la base del agricultor.**

> **Los ocho están arreglados a las 19:41** (el agente del T10 fue leyendo este documento y arreglando,
> y lo cita en sus propios comentarios). Lo que sigue es lo que había, con su prueba, su consecuencia y
> el sitio del arreglo.

### 1 · Volver a apuntar una siembra anulada desde la cola no la sacaba del almacén — **gravedad alta**
`semillas_api.py:699` (`clave_de_reenvio=f"{clave}:salida"`) con `almacen_api.py:1334-1340`, y el motivo
que se enseñaba en `semillas_api.py:583`.
`TestContrato2…::test_DEFECTO_anular_y_volver_a_apuntar_la_misma_peticion_vuelve_a_descontar`

Anular una siembra y volver a mandar **la misma petición** (lo que hace la cola del móvil: reenvía con la
misma clave) creaba la siembra nueva —201— pero **no apuntaba su salida**: la puerta del almacén
encontraba la salida **vieja** por su clave `«clave:salida»` y la daba por buena, aunque su siembra
estuviera anulada; y la respuesta decía que no descontaba **«porque no se sabe de qué envase sale»**, con
el envase elegido y su número de lote en el mismo JSON. El índice de `siembras` dice justo lo contrario
(«una siembra anulada tiene que dejar volver a apuntarla»). La prueba de control
(`test_anular_y_volver_a_apuntar_con_otra_clave_si_vuelve_a_descontar`, que ya pasaba en la foto A)
demostraba que la causa era el choque de claves.

> **Al agricultor:** después de anular una siembra equivocada, el apunte volvía solo desde el móvil, él
> lo veía apuntado… y la semilla seguía en la nave. El almacén y el cuaderno decían cosas distintas, y el
> aviso le echaba la culpa a un envase que sí había elegido.
>
> **Arreglado a las 19:38** (`semillas_api.py:789-812`, foto B): la siembra ya no inventa una clave para
> su salida, y la protección es la de la puerta por apunte y envase más la clave de la propia siembra.

### 2 · Una segunda salida a mano con otro envase descontaba dos veces — **gravedad media**
`almacen_api.py:1316-1324` (la comprobación de «ya estaba» era **por apunte y envase**), llamada desde
`semillas_api.py:785`. `TestContrato2…::test_DEFECTO_una_segunda_salida_a_mano_para_la_misma_siembra_descuenta_dos_veces`

`POST /api/almacen/salidas` acepta `apunte_tipo="siembra"` para cualquiera que lo llame, así que con un
segundo saco del mismo artículo la misma siembra descontaba dos veces: la prueba contaba **2 salidas
vivas** y 400 kg fuera para una siembra de 200 kg. Con el mismo envase sí lo cazaba (control que
pasaba).

> **Al agricultor:** el mismo saco se le descontaba dos veces del almacén y el libro quedaba con dos
> salidas que no cuadran. **No se alcanzaba desde ninguna pantalla** (no hay ningún sitio que ofrezca
> «siembra» como apunte), sí desde la API del propio programa.
>
> **Arreglado a las 19:38** (`almacen_api.py:1317-1331`, foto B): con `apunte_tipo="siembra"` la búsqueda
> es por apunte **sin mirar el envase**, porque una siembra sale de un solo saco. El comentario nuevo
> explica por qué para un tratamiento o un abono sigue siendo por envase (se pueden gastar dos garrafas).

### 3 · «SEMILLA SIN TRATAMIENTO» se leía como «tratada» — **gravedad media**
`semillas.py:404-408`. `TestContrato3…::test_DEFECTO_sin_tratamiento_se_lee_como_tratada`

La negación que se buscaba era `sin tratar`, que **no** encaja dentro de `sin tratamiento` (sobran
letras), así que la frase más normal de un saco marcaba la semilla como tratada. Fallaban las tres formas
probadas («SEMILLA SIN TRATAMIENTO», «NO LLEVA TRATAMIENTO», «NO SE HA APLICADO NINGÚN TRATAMIENTO»), y
las dos que el ticket sí cubría («SEMILLA NO TRATADA» → no; «SEMILLA TRATADA CON FUNGICIDA» → sí) seguían
bien: la prueba lo comprobaba antes para que no se dudara de por qué fallaba.

> **Al agricultor:** la ficha decía que la semilla viene tratada cuando el papel dice lo contrario, y lo
> decía el programa, no él.
>
> **Arreglado a las 19:35** (`semillas.py`, foto B).

### 4 · La unidad de la dosis se guardaba como una palabra pegada: `kgporhectarea` — **gravedad media-baja**
`semillas.py:445-464` (`_UNIDAD_ESCRITA` y `_unidad_de`), usadas en `semillas.py:302-305`.
`TestContrato3…::test_DEFECTO_la_unidad_de_la_dosis_se_guarda_como_una_palabra_pegada`

«120 kg por hectárea» —la forma en que se escribe la dosis en el papel— se guardaba con
`unidad_dosis = "kgporhectarea"`, aunque la cabecera de `_unidad_de` prometía «la unidad tal cual».

> **Al agricultor:** en su ficha leía «120 kgporhectarea», y ese texto es el que la pantalla usa para
> pre-rellenar el desplegable de la dosis al sembrar (que sólo ofrece `kg/ha`, `g/ha`, `ud/ha` y `L/ha`),
> así que el desplegable se quedaba sin su opción y la siembra podía acabar sin unidad. Lo segundo es
> lectura del código (el `defaultValue` de un `<select>` no tiene opción que case): **no lo he podido
> comprobar en un navegador**.
>
> **Arreglado a las 19:35** (`semillas.py:497-550`, foto B), con una tabla que traduce cada trozo de la
> unidad a su forma corta. **Pero el arreglo dejó un hueco**: ver el defecto 9.

### 5 · Una semilla sin ninguna entrada decía que queda cero — **gravedad baja**
`servicios.py:1341-1355` (un conjunto sin movimientos devuelve `saldo: 0.0`) a través de
`semillas_api.py:99-114`. `TestContrato4…::test_DEFECTO_una_semilla_sin_ninguna_entrada_dice_queda_cero`

Una semilla dada de alta a mano —el camino que el propio documento describe: comprar, hacer la foto y
confirmar— contestaba `queda: {saldo: 0.0, unidad: null}`, con la pantalla escribiendo «Te queda 0» y sin
unidad. El documento promete en su apartado 1.4: «cuando no se puede saber, “No se puede saber lo que
queda” con su motivo. **Nunca un cero**».

> **Al agricultor:** compraba la semilla, confirmaba la etiqueta y la lista le decía que no le queda nada,
> con el saco en la nave. **En descargo del ticket:** el T09 tiene escrito que un envase sin movimientos
> «está a cero, y eso se sabe», y esa decisión es defendible; lo que no lo era es un cero **sin unidad** y
> sin motivo donde el documento promete lo contrario.
>
> **Arreglado a las 19:38**: `semillas_api.py:106-122` (una semilla sin envases y sin movimientos dice
> «no se puede saber» con el motivo `SM35`, `textos.py:5810`), con el comentario diciendo que salió de
> esta revisión.

### 6 · Una corrección parcial le borraba la fecha a la siembra — **gravedad baja-media**
`semillas_api.py:981` (`fecha=datos.fecha` en el registro preparado) frente a la regla del envase en
`semillas_api.py:903-911`. `TestContrato6…::test_DEFECTO_una_correccion_parcial_le_borra_la_fecha_a_la_siembra`

Un `PUT` sin `fecha` dejaba la siembra **sin fecha**, y la salida del almacén se quedaba con la vieja, así
que el libro y el apunte decían cosas distintas del mismo hecho. El propio documento deja escrito el
principio para el envase: «lo que no se pregunta tiene que viajar igual». **Hoy la pantalla siempre manda
la fecha**, así que no se alcanzaba desde la interfaz; sí desde la API.

> **Al agricultor:** el día en que sembró —lo que se enseña en una inspección— desaparecía del cuaderno
> sin que nadie lo hubiera pedido.
>
> **Arreglado a las 19:38** (`semillas_api.py`, foto B).

### 7 · Cambiar la semilla de una siembra se hacía en silencio (y el documento dice que no se puede) — **gravedad baja-media**
`semillas_api.py:900`, `:979-980` y `:903-911`; la afirmación que contradecía está en
`docs/T10_SEMILLAS.md:308-310`. `TestContrato6…::test_DEFECTO_cambiar_la_semilla_de_una_siembra_se_hace_en_silencio`

El documento dice: «Cambiar la semilla de una siembra guardada **no se puede** y se dice por qué». El
`PUT` sí lo hacía: la respuesta confirmaba la siembra con la **semilla 2**, `descuenta: false` y
`lote_id: null`, y por el camino la semilla que sí se sembró **volvía al almacén** sin un solo aviso.

> **Al agricultor:** la siembra pasaba a decir que sembró otra cosa y el almacén recuperaba una semilla
> que ya está en la tierra, sin decirle nada.
>
> **Arreglado a las 19:38**: se rechaza con `SM34_la_semilla_no_se_cambia` (`semillas_api.py:1024`,
> `textos.py:5806`), que además le dice qué hacer («anula esta siembra y apunta la buena»).

### 8 · La cuenta que hace el servidor no llegaba a la pantalla — **gravedad media**
`app.js:14778` (se guardaba el aviso) y `:14784` (se ponía a `null` antes de pintar), frente al
comentario del propio fichero en `:14691-14693` y a lo que promete `docs/T10_SEMILLAS.md:32-33` y
`110-112`. `TestContrato8…::test_DEFECTO_la_cuenta_que_hace_el_servidor_no_llega_a_la_pantalla`, con la
prueba de apoyo `test_el_aviso_de_lo_calculado_solo_vive_en_la_respuesta_de_guardar` (que pasaba y
demostraba que el aviso **sólo** existía en la respuesta de guardar).

`guardarLaSiembra` guardaba la frase del servidor en `suyo.calculado` y la ponía a nulo tres líneas
después, antes de pintar la lista; el cuadro «Lo ha calculado el programa» sólo se pinta en el
formulario, que ya no vuelve a salir. El T09 sí conserva los suyos (`salida.avisos = cuerpo.avisos`).

> **Al agricultor:** el programa multiplicaba dosis × hectáreas por él y le enseñaba «300,00 kg» como si
> lo hubiera escrito él. El corazón de este ticket era que un número calculado se pueda revisar.
>
> **Arreglado a las 19:38–19:39** (`app.js`, foto B). **Nota:** la prueba lee `app.js` (no tengo
> navegador en esta revisión), así que demuestra lo que dice el código, no lo que hace el navegador.

---

## 5. Defecto que sigue abierto a las 19:41: la unidad leída no es la que ofrece el programa

### 9 · «2 L/ha» se lee `l/ha`, y la pantalla ofrece `L/ha` — **gravedad baja**
`semillas.py:497-520` (la tabla del arreglo del defecto 4) frente a `semillas.py:63`
(`UNIDADES_DE_DOSIS = ("kg/ha", "g/ha", "ud/ha", "L/ha")`). Medido contra la foto B
(`semillas.py` del 19:35:06, `C6B8A16AAF241399`).
`TestContrato3…::test_DEFECTO_la_unidad_leida_no_es_la_que_ofrece_el_programa` — **es la única que falla
a las 19:41 (1 de 49)**.

La tabla que traduce cada trozo de la unidad a su forma corta tiene `litro` y `litros` (que dan `L`) y
**no tiene `l`** —ni `kg`, ni `g`, ni `ml`—, así que la forma corta, que es la que escriben las etiquetas
de verdad, se queda como vino del papel en minúsculas. Medido:

| Lo que dice el papel | `unidad_dosis` que sale | ¿Está en la lista de la pantalla? |
|---|---|---|
| `DOSIS RECOMENDADA: 120 kg/ha` | `kg/ha` | Sí |
| `DOSIS RECOMENDADA: 120 kg por hectárea` | `kg/ha` | Sí (esto es lo que arregló el defecto 4) |
| `DOSIS: 120 kilos por hectárea` | `kg/ha` | Sí |
| `DOSIS: 250 g/ha` | `g/ha` | Sí |
| `DOSIS: 90000 ud/ha` | `ud/ha` | Sí |
| `DOSIS: 3 litros/ha` | `L/ha` | Sí |
| **`DOSIS: 2 L/ha`** | **`l/ha`** | **No** |
| **`DOSIS: 2 l/ha`** | **`l/ha`** | **No** |

> **Al agricultor:** la misma unidad escrita de dos maneras da dos textos distintos, y el desplegable de
> la dosis se queda sin su opción y elige «sin decir». Las cuentas del almacén **no** se rompen (comparan
> las unidades sin mirar mayúsculas, `servicios.se_pueden_sumar`), así que esto se queda en la pantalla; y
> como el formulario manda la unidad que diga el desplegable, la siembra puede acabar sin unidad.

**Honestidad sobre esta prueba:** el defecto es de la misma familia que el 4 y el arreglo se quedó a
medias, pero su alcance es pequeño (la pantalla, no el cuaderno). La consecuencia en pantalla es lectura
del código: **no la he comprobado en un navegador**.

---

## 6. Lo que NO he podido probar, y por qué

1. **Una foto de verdad, de un saco de verdad, torcida y con sombras.** Es lo que el propio documento dice
   que falta. La prueba con foto rasterizada del ticket **se ejecutó** (Tesseract está puesto aquí), pero
   eso no es la foto de un móvil de verdad.
2. **La cola del móvil sin cobertura de verdad.** He probado el reenvío con la misma clave por la API (que
   es donde vive la lógica), no cortando la red de un teléfono.
3. **PostgreSQL.** He medido una cosa que sólo se ve ahí: `_la_clave` recorta a **120** caracteres
   (`semillas_api.py:720`) y antes se le pegaba `:salida` (`:699`), con la columna `String(120)`
   (`models.py:1504`). En SQLite entraba igual; en PostgreSQL habría sido un error de la base. Aquí no hay
   PostgreSQL. (El arreglo del defecto 1 quita justamente ese sufijo, así que puede que ya no exista.)
4. **El aspecto en un navegador de verdad y a 390 px.** El documento reconoce que sus dos pantallas no
   están en la lista del guion del coordinador. No lo he repetido.
5. **El guion de navegador del T10.** Vive en la carpeta temporal y no en el repositorio, así que su «6 de
   6» **no lo puedo comprobar**. Lo que sí he visto es que, mientras corre, deja un fichero dentro de
   `backend/web/` y que eso pone en rojo el guardián del propio proyecto (apartado 7).
6. **Las afirmaciones «no se ha tocado» y «sólo añadiendo».** El repositorio **no tiene `.git`** (`git
   status` contesta «not a git repository»), así que no puedo comprobarlas. Lo que sí he mirado: en la
   foto A, `almacen_api.py` tenía `mtime` 17:08, **antes** de los ficheros del T10 (18:21–18:56), así que
   su afirmación de que ese fichero no se tocó **era coherente** con las horas. (En la foto B sí se ha
   tocado: lo arregló a las 19:38.)
7. **La numeración exacta de la suite.** El árbol se mueve: 3584 y luego 3588 con mi fichero dentro.
8. **Firma histórica de verdad.** He comprobado que la huella no cambia al apuntar una siembra, pero **no
   hay una firma con un certificado de verdad** en juego. Además, el matiz: la huella no cambia porque
   `firma.texto_del_cuaderno` sólo escribe tratamientos, abonos y labores (`firma.py:169-208`), así que
   **una siembra no entra en el fichero que se firma**. Cumple el contrato 9 tal y como está escrito, pero
   conviene saberlo: si el cuaderno se firma para una inspección, las siembras no van dentro.

---

## 7. Valoración honesta del documento de T10

**Lo que dice y he podido confirmar.** No exagera en lo que cuenta de sus pruebas: 45 (hoy 52) propias,
805 de JavaScript, el lector de fotos instalado y su prueba ejecutada, y sus afirmaciones sobre qué tocó
cuadran con las horas y los tamaños de los ficheros. Lo que más se sostiene es el **aislamiento entre
fincas** (siete rutas probadas con una segunda finca de verdad, todas 404 y ninguna 403), **la salida
única por la puerta del almacén** (la salida se ve en el libro con `origen_tipo` `siembra`, y a mano no se
puede decir que un movimiento viene de una siembra), **la lectura que no escribe nada** (ni semilla, ni
artículo, ni fichero en el disco, comprobado mirando la carpeta) y **anular sin tocar el libro** (mismo
movimiento, con su fecha y su autor, tachado y sin contar). Y los textos: están todos en `textos.py`, se
sirven por `/api/interfaz` **incluidos los mensajes que usa la pantalla**, y ninguno lleva jerga.

**Donde el documento y el código no decían lo mismo** (los cinco puntos que encontré en la foto A, los
cinco ya arreglados o en vías de ello):

1. **«La semilla sale del almacén y sale UNA sola vez»** (3.4 y 3.5): falso en dos caminos (defectos 1 y
   2). El apartado 3.5 decía «nunca dos vivas»: con un segundo envase había dos.
2. **«Cambiar la semilla de una siembra guardada no se puede y se dice por qué»** (6.3): se podía, y sin
   decir nada (defecto 7).
3. **«Un aviso con la cuenta entera … un número calculado se puede revisar»** (3.2 y 1.5): el servidor lo
   decía y la pantalla lo tiraba (defecto 8). Sus 24 pruebas de JavaScript —hoy algunas más— comprueban
   que el componente **enseña** el cuadro cuando le llegan las frases, pero ninguna que en el uso real le
   lleguen. Es el mismo fallo que `AGENTS.md` cuenta del `plan.herramienta`: un test que da por buena una
   pantalla que el agricultor no tiene.
4. **«una semilla sin cantidad … nunca un cero»** (1.4 y 3.3): tenía una excepción, la semilla sin
   ninguna entrada (defecto 5).
5. **La negación de la etiqueta** (3.3) se cuidaba a medias: «SEMILLA NO TRATADA» estaba cubierta con su
   prueba, «SEMILLA SIN TRATAMIENTO» no y se leía al revés (defecto 3).

**Un sexto punto, de forma:** en 3.8 dice que «los 200 y pico textos nuevos» van en el bloque `SEMILLAS`.
El bloque tiene **125** claves y los mensajes **33** (158 en total). No cambia nada de lo que defiende,
pero la cifra no es la que hay.

**Donde el documento se queda corto, no donde miente.** Sus apartados 6 («lo que no se ha hecho») y 7
(«lo que no se ha podido comprobar») son honestos y coinciden con lo que he visto: la foto real, la cola
sin cobertura, el catálogo oficial de especies que no está y no se ha inventado, y las dos pantallas
fuera del guion de 390 px. Le añadiría una línea a su apartado 6: **el camino de guardar de verdad no
estaba probado por nadie**. Sus pruebas de JavaScript pintan las cuatro pantallas y comprueban los `id`,
pero **ninguna pulsaba `siembra-guardar`, `semilla-guardar` ni `siembra-anular`**: lo he comprobado
buscando esas acciones en los seis ficheros de `tests_js/`, y sólo aparecen en `semillas.test.js` como «no
sale el botón» y «sí sale el botón». En el T09 sus equivalentes (`salida-guardar`, `movimiento-guardar`)
sí se pulsan en `interfaz.test.js`. Es decir: `recogeLaSiembra`, `guardarLaSiembra`, `anularLaSiembra` y
`guardarLaSemilla` no los miraba ninguna prueba — y ahí estaba exactamente el defecto 8.

**Afirmaciones que no he podido confirmar** (ni desmentir): el «6 de 6» de su guion de navegador (vive
fuera del repositorio), que `almacen_api.py` no se hubiera tocado (no hay `git`; en la foto A las horas
eran coherentes) y el recuento exacto de la suite, que se mueve.

**Una observación sin prueba que la demuestre, dicha como tal:** `POST /api/semillas` acepta
`leida_de: "foto"` sin que haya ninguna foto (`schemas.py:1883-1887` y `semillas_api.py:288-293`), así que
el dato que debía decir «esto lo leyó un programa del papel» lo escribe quien llama. No lo cuento como
defecto —la regla del ticket es que la lectura no cree nada, y eso se cumple— pero conviene saber que
`leida_de` es una declaración de quien llama, no una comprobación del servidor.

**Y una nota final, de las 19:44.** El documento del ticket **se ha vuelto a escribir a las 19:44** (de
25.001 a **29.965** bytes, sha `DFF50B150842889C`) y ahora lleva un apartado 7 nuevo, «La revisión del
ticket: los ocho defectos que encontró, y cómo quedaron», con la tabla de los ocho y cómo se arreglaron.
(Ese apartado habla de **48** pruebas de esta revisión: son las que había cuando leyó el fichero; a las
19:41 añadí la del defecto 9 y son 49.)
Todo lo que digo arriba de ese documento es de la versión de las **19:16** (`31B6BC31608AB39C`): las
cuatro frases que señalé (§1.5, §3.2, §3.4 y §6.3) siguen escritas tal cual en el texto (§6.3 en la línea
309), pero ya no engañan a nadie porque el apartado 7 nuevo cuenta exactamente lo que pasó. Es una forma
honesta de cerrarlo: lo que faltaba no era borrar la promesa, era decir en el mismo documento dónde no se
había cumplido.

---

## 8. Cronología: el árbol se movió (y se rompió) mientras se revisaba

| Hora | Qué pasó |
|---|---|
| 19:13–19:29 | **Foto A.** Se miden los 8 defectos. `test_revision_t10.py`: 48 pruebas, 8 fallos |
| 19:16 | Se vuelve a escribir `docs/T10_SEMILLAS.md` (mismo tamaño) |
| 19:17 → 19:22 | `app.js` cambia dos veces |
| 19:22–19:27 | Aparece `backend/web/_comprobacion_movil_390.html` (lo escribe el guion de navegador del T10) y **`test_ficheros_de_texto.py` se pone rojo dos veces**. A las 19:29 el fichero ya no está y el guardián está verde |
| 19:30–19:35 | Suite completa: 3588 pruebas, 1 saltada, 9 fallos (los míos) |
| **19:35–19:38** | **Se arreglan los defectos 3, 4, 1, 2, 5, 6, 7 y 8**, citando esta revisión en los comentarios |
| **19:36–19:38** | **El árbol quedó roto a medias mientras se arreglaba**: el router empezó a usar `SM34_la_semilla_no_se_cambia` y `SM35_no_ha_entrado_para_saber_lo_que_queda` **antes** de que esos textos existieran en `textos.py` (que no se tocó hasta las 19:37:59). En ese hueco `POST /api/semillas` daba **500 (KeyError)** y el `PUT` que cambia la semilla también. Lo cazó mi guardián `test_todos_los_mensajes_que_usa_el_router_existen`, que saca los códigos del propio router y los busca en `textos.py`. A las 19:38, con los dos textos ya escritos, volvió a pasar. También medí, a las 19:38, su propia suite con un `InvalidRequestError: Incorrect number of values in identifier … lotes.id`; un minuto después daba 52 en verde: era el fichero a medio escribir, no un defecto |
| 19:41–19:42 | **Foto B.** `test_revision_t10.py`: 49 pruebas, **1 fallo** (el defecto 9). Su fichero: 52 pruebas, 0 fallos |

Lo de las 19:36 merece quedar escrito por dos motivos: es la demostración de que **el guardián de textos
nuevo sirve** (un código de mensaje que no existe en `textos.py` es un 500 delante del agricultor), y es
el recordatorio de que un árbol que se edita mientras se mide sólo se puede juzgar con la hora y la huella
al lado.

---

## 9. Resumen

1. **49 pruebas** escritas; **48 pasan** y **1 falla** a las 19:41. Sus 52 pruebas propias y las 805 de
   JavaScript, verificadas y en verde.
2. **Encontré 8 defectos** (con la foto A y su prueba que fallaba): dos en el almacén (una siembra
   anulada que vuelve a apuntarse no descontaba; una segunda salida con otro envase descontaba dos veces),
   dos en la lectura de la etiqueta («sin tratamiento» se leía al revés; la unidad salía como
   `kgporhectarea`), uno en el saldo («queda 0» sin movimientos), dos en la corrección (perdía la fecha;
   cambiaba la semilla en silencio) y uno en la pantalla (la cuenta del servidor no se leía).
   **Los ocho están arreglados a las 19:41**, entre las 19:35 y las 19:40, citando esta revisión.
3. **Sigue abierto 1**: el arreglo de la unidad dejó fuera la forma corta en minúscula (`2 L/ha` → `l/ha`,
   que no es ninguna de las que ofrece la pantalla). Y el camino de guardar de la pantalla sigue sin
   ninguna prueba que lo pulse.
4. **El documento dice la verdad en casi todo**: lo que cuenta de sus pruebas y de lo que ha dejado sin
   hacer es correcto, pero se pasaba de optimista en cuatro frases —«sale una sola vez», «cambiar la
   semilla no se puede», «el número calculado se revisa» y «nunca un cero»—, que son exactamente los
   cuatro sitios donde estaban los defectos.
