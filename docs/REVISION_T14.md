# Revisión independiente del T14 — maquinaria e inspecciones (S16)

> **Qué es esto:** la revisión del ticket T14 hecha por otro agente, intentando **romperlo**, no
> confirmarlo. **Cuándo:** 05/10/2026. **Base:** `docs/T14_MAQUINARIA.md` (el informe del ticket),
> el contrato (§4 S16 y §9), `docs/MATRIZ_NORMATIVA_CRM.md` (trabajo legal **L07**) y el código
> entregado.
> **Pruebas de esta revisión:** `backend/tests/test_revision_t14.py` (24 pruebas: **16 en rojo** a
> propósito, una por defecto encontrado, y 8 verdes que son puertas que he comprobado y quiero dejar
> atadas). No he tocado ni una línea del ticket: solo he roto tres cosas **a propósito** y las he
> vuelto a dejar como estaban (§3).

---

## Resumen de una pantalla

**14 defectos.** Se puede dar por bueno el **modelo y las reglas** —que es lo difícil de este
ticket, y está bien hecho: no se calcula ninguna fecha, ningún valor por defecto convierte «no lo
sé» en «cumple», y el aislamiento entre fincas está bien puesto—, pero **no se puede dar por bueno
el ticket tal y como está**, porque **lo que se ve y lo que se pulsa no funciona**:

| # | Gravedad | Qué |
|---|---|---|
| 1 | **GRAVE** | **«APUNTAR UNA INSPECCIÓN» no hace nada**: el formulario revienta con `TypeError: (estado.documentos \|\| []).map is not a function`, así que la única puerta que tiene una inspección **no se abre** (ni el alta ni la corrección) |
| 2 | **GRAVE** | **«undefined: ITV el 12/05/2026» en la tarjeta del móvil**: dos claves que no existen en `textos.py` |
| 3 | **GRAVE** | **Corregir una máquina no se guarda**: el formulario manda clase, propiedad y disponibilidad **vacías** y el servidor contesta `422 ««» no es una de las clases de máquina que se pueden elegir»` |
| 4 | Medio | Lo apuntado en la ficha nueva **no llega al cuaderno de la Junta**: el ROMA y la ITEAF de la hoja 1.3 siguen siendo los viejos, y el ticket promete lo contrario por escrito |
| 5 | Medio | La pantalla **no manda `clave_de_reenvio`**: dos toques del botón (o un reintento) apuntan **dos inspecciones** — el caso A12 que el ticket dice cubrir |
| 6 | Medio | El reenvío **no se cierra por máquina**: la misma clave para otra máquina contesta la inspección de la primera y la segunda no se apunta |
| 7 | Medio | La **copia de los textos del test del móvil dice otra cosa que el servidor** en 35 de sus 172 textos, y falta el guardián que lo comprueba (todas las demás pantallas lo tienen) |
| 8 | Medio-bajo | Quitar una máquina **borra sus obligaciones declaradas sin rastro** en la auditoría |
| 9 | Medio-bajo | Una fecha **ya pasada** no se marca «Vencida» si nadie declaró que la obligación aplica: se queda en la lista sin ninguna palabra al lado |
| 10 | Bajo | Traer un equipo del cuaderno que tiene **próxima ITEAF pero no última** hace **desaparecer esa fecha de la vista** |
| 11 | Bajo | Dos máquinas pueden ser **el mismo equipo** del cuaderno (el enlace no es único en el alta ni en la corrección) |
| 12 | Bajo | **Diez textos** de la maquinaria se escribieron y **no se enseñan en ningún sitio**, y uno de ellos es el único que dice que los papeles de las inspecciones hay que guardarlos tres años |
| 13 | Bajo | El guardián que impide calcular fechas **solo mira un fichero**: metiendo el cálculo en el router, el guardián del ticket **sigue verde** (§3, medido) |
| 14 | Bajo | El papel que demuestra una inspección **no se puede abrir ni se dice cuál es**: la ficha solo escribe «Con su papel» *(sin prueba: es del navegador, ver §4)* |

**Lo que yo haría, en este orden:** los tres graves primero (son tres arreglos pequeños: una línea
en `papelesParaElegir`, dos claves en `textos.py`, y partir de lo que ya está guardado al corregir),
y el 4 y el 5 antes de dar el ticket por entregado, porque son dos promesas que el ticket hace por
escrito y no cumple.

---

## 1. Lo que he comprobado que está bien

Lo primero que miré fue la trampa del ticket y la puerta de calidad del §9, y las dos están
cumplidas de verdad. Comprobado leyendo el código y con pruebas propias:

| Qué se comprobó | Dónde | Cómo |
|---|---|---|
| **No hay ni una fecha calculada.** Ni suma de días, ni plazo por defecto, ni `relativedelta`, ni una fecha «deducida» que acabe en pantalla. La próxima fecha es **la del papel**, copiada | `app/maquinaria.py:214-226,306,321-326,339`; `app/routers/maquinaria_api.py:704-713`; `web/app.js` (bloque de la maquinaria, 16744-17211); `web/react/pantallas/maquinaria.js` | Barrido a mano de los tres ficheros + 2 pruebas guardián (`TestNoSeCalculaNingunaFecha`). **El único sitio donde se hace aritmética con fechas es la resta `proxima - hoy`, para decir «quedan N días»** (`maquinaria.py:340`), que no inventa ninguna fecha |
| **Ningún valor por defecto permisivo.** `propiedad`, `disponibilidad` y la aplicabilidad nacen en `no_se`; el resultado de una inspección nace en `no_consta`; `clase`, `propiedad` y `disponibilidad` **no tienen valor por defecto en el esquema y no se pueden guardar sin contestar** | `app/models.py:609,618,655,657,699`; `app/schemas.py:593-604` | `test_una_obligacion_sin_declarar_no_se_lee_como_que_no_le_toca` (mía, verde) + las tres del ticket |
| **Ni un cero donde no se sabe**: las horas, el número de ROMA, la próxima fecha y las horas de una avería son `None` («no lo sé») y se enseñan como «Falta decirlo», nunca como `0` ni como `01/01/1970` | `app/models.py:613,601,701,743`; `app/schemas.py:603,706` | Leído y probado por los caminos de la API |
| **El aislamiento entre fincas contesta 404, no 403**, y está en **todas** las rutas con identificador (máquina, obligaciones, inspecciones, averías, anular, borrar); y los avisos por identificador de otra finca devuelven la lista vacía | `app/routers/maquinaria_api.py:114-127,501,537,565,636,682-690,738,862-868,342-344` | `test_cada_puerta_de_la_maquinaria_comprueba_que_el_objeto_es_de_esta_finca` (mía: recorre **las rutas del router**, no una lista a mano, y exige la comprobación en cada una; verde) + la del ticket para los avisos |
| **El caso feo del papel de otra finca, por las dos puertas** (apuntar y **corregir** una inspección) y el equipo de otra finca en el alta | `app/routers/maquinaria_api.py:114-127` | 2 pruebas mías, verdes |
| **Anular deja de contar para la última inspección, para la próxima fecha y para los avisos**, y la fila sigue en el cuaderno | `app/maquinaria.py:228-235`; `app/routers/maquinaria_api.py:816-830` | `test_anular_una_inspeccion_la_saca_de_la_ultima_y_del_aviso` (mía, verde) |
| **`EquipoAplicacion` no se ha reutilizado como inventario**: la tabla nueva es `maquinas` y los equipos de echar producto se enseñan aparte con su botón | `app/models.py:556-628`; `app/routers/maquinaria_api.py:259-290` | Leído; las pruebas del ticket lo cubren |
| **El guardián del recuento de tablas** (`TABLAS_QUE_SON_PARTE_DE_LA_MAQUINA`) avisa el día que aparezca una cuarta tabla que use una máquina | `app/routers/maquinaria_api.py:77-90`; `tests/test_t14_maquinaria.py:735-748` | Verde |
| **Los papeles y las facturas no se pueden dejar colgando**: borrar un documento que demuestra una inspección contesta 409 | `app/routers/maquinaria_api.py:703`; `app/routers/documentos_api.py` | La decisión del ticket (contar `documento_id` como dependencia) me parece la buena |
| **El JavaScript no calcula ni compone frases por su cuenta**, y la caché del campo lleva la pantalla nueva y la versión subida (68, la misma que la del pie) | `web/service-worker.js:260,333`; `tests/test_la_version_visible.py` | Leído; la suite de JavaScript pasa entera (896) |

---

## 2. Los defectos, por gravedad

### 1. GRAVE — El botón «APUNTAR UNA INSPECCIÓN» no hace nada (la pantalla revienta)

**Qué pasa.** `papelesParaElegir()` lee la lista de papeles como si `estado.documentos` fuera una
lista:

```js
// web/app.js:17504-17510
function papelesParaElegir() {
  return (estado.documentos || []).map((papel) => ({ valor: String(papel.id), … }));
}
```

Y `estado.documentos` **no es una lista**: es lo que devuelve `GET /api/documentos`, que es un
objeto con la lista dentro (`{"textos": …, "documentos": [...], "carpetas": …}`,
`app/routers/documentos_api.py:152-154`). Esa variable se carga al entrar
(`web/app.js:4608` → `estado.documentos`, `web/app.js:4667`), así que **con la aplicación abierta
normalmente esa rama siempre es el objeto**.

Medido ejecutando la función de verdad (extrayéndola de `app.js` y llamándola con la forma que
devuelve el servidor):

```
CODIGO REAL:
function papelesParaElegir() {
  return (estado.documentos || []).map((papel) => ({ ... }));
}
REVIENTA: TypeError: (estado.documentos || []).map is not a function
```

Y esa función se llama **desde un solo sitio**: `web/app.js:17526`, dentro de
`formularioDeUnaInspeccion()`. O sea: al pulsar **APUNTAR UNA INSPECCIÓN** (o **CORREGIR** una
inspección) el manejador de clics revienta antes de repintar. El resto del programa lee la misma
variable bien (`web/app.js:5678`, `8422`, `8629`: `(estado.documentos || {}).documentos`), así que
es un despiste de este fichero.

**A quién le hace daño, con nombre y apellidos.** David está en la nave con el móvil, con el
certificado de la ITEAF del pulverizador en la mano y acaba de abrir la ficha de la máquina. Pulsa
**APUNTAR UNA INSPECCIÓN**… y no pasa nada: la pantalla se queda igual, sin un aviso y sin un
error. Vuelve a pulsar, tampoco. Se queda sin poder apuntar la inspección **por ninguna vía** (la
API funciona, pero la única puerta que tiene es ese botón), y lo que es peor: se queda con la
sensación de que el programa está roto justo en la pantalla nueva. La corrección de una inspección
tampoco se puede abrir.

**Qué habría que hacer.** Leer la misma forma que leen las otras cuatro pantallas:

```js
return ((estado.documentos || {}).documentos || []).map(…);
```

**Prueba:** `test_revision_t14.py::TestApuntarUnaInspeccionDesdeLaPantalla::test_la_lista_de_papeles_tiene_la_forma_que_lee_el_formulario`
(roja hoy; compara la forma que devuelve `GET /api/documentos` con la que lee la función).

> **Y una nota sobre cómo se coló:** el ticket comprobó esta pantalla en un navegador de verdad
> (§2 de su informe), y **lo que midió fue que la página se dibuja y que no se sale de lo ancho** —
> en su informe no consta que pulsara los botones—. Una captura no es un recorrido: este defecto solo
> se ve al pulsar.

### 2. GRAVE — «undefined: ITV el 12/05/2026» en la tarjeta del móvil

**Qué pasa.** La tarjeta de cada máquina (la del móvil, la que se usa en el campo) compone tres
renglones con claves del diccionario de la maquinaria:

```js
// web/app.js:16987-16989
proxima: `${m.proxima_revision}: ${textoDeLaProximaRevision(resumen)}`,
papeles: `${m.documentacion}: ${textoDeLaDocumentacion(resumen)}`,
disponibilidad: `${m.disponibilidad}: ${disponibilidad_texto}`,
```

`m` es `t("maquinaria", {})`, o sea `textos.MAQUINARIA_DE_LA_FINCA`, y **`proxima_revision` y
`documentacion` no existen ahí**: existen en `textos.TABLA` (`app/textos.py:4871-4872`), que es de
donde los saca la tabla del ordenador (`web/app.js:17032-17033`). Una clave que no existe no pasa
por `rellena` (que es lo que deja los huecos sin escribir «undefined» a propósito,
`web/nucleo.js:390`), así que se interpola tal cual.

Medido con el diccionario **de verdad** que sirve el servidor:

```
clave m.proxima_revision -> undefined
clave m.documentacion    -> undefined
LO QUE PINTA LA TARJETA DEL MOVIL:
  undefined: ITV el 12/05/2026
  undefined: 1 papel
  ¿Puedes contar con ella para trabajar?: Si puedo
```

**A quién le hace daño.** David, de pie en la parcela, abre «mi maquinaria» en el móvil para saber
si puede contar hoy con el Landini. Lo que lee es `undefined: ITV el 12/05/2026`. La primera
palabra de cada renglón está en inglés y no dice nada; y como es el renglón que dice **cuándo toca
la próxima revisión**, el dato que más importa de la pantalla llega con basura delante. (La tabla
del ordenador, en cambio, sí dice «Próxima revisión» y «Papeles», porque las coge de `TABLA`.)

**Qué habría que hacer.** O usar `col("proxima_revision")` / `col("documentacion")` como la tabla
(lo más coherente, porque son los nombres de la tabla del contrato), o añadir las dos claves a
`MAQUINARIA_DE_LA_FINCA`. Y de paso: `disponibilidad` sí existe, pero es la **pregunta** («¿Puedes
contar con ella para trabajar?»), no el rótulo de la tabla («Disponibilidad») — se lee raro.

**Pruebas:** `test_la_tarjeta_del_movil_no_ensena_la_palabra_undefined` y
`test_todas_las_claves_que_usa_la_maquinaria_existen` (las dos rojas hoy; la segunda es un barrido
de todas las claves `m.<clave>` que usa la pantalla, para que no quede otra igual).

### 3. GRAVE — Corregir una máquina no se guarda (y el formulario enseña las preguntas en blanco)

**Qué pasa.** El camino que el propio ticket pone por delante («la matrícula mal copiada, las horas,
el número de ROMA o la clasificación técnica», `maquinaria_api.py:530-535`) **no funciona**, y falla
por dos sitios a la vez:

1. La ficha que se prepara para la pantalla **no lleva el valor en crudo** de los tres campos de
   elegir: devuelve `clase_texto`, `propiedad_texto` y `disponibilidad_texto` (para leer), pero no
   `clase`, `propiedad` ni `disponibilidad` (`web/app.js:17134-17166`). El formulario marca la
   opción elegida con `elegido("clase") = b.clase || maquina.clase || ""` (`web/app.js:17380`), y
   `maquina.clase` es `undefined`: **al abrir «Corregir esta máquina» las tres preguntas salen sin
   ninguna respuesta marcada**, aunque el agricultor las contestó el primer día (y el texto de la
   pantalla dice «Está puesto lo que apuntaste», `textos.py` → `form_corregir_pista`).
2. `recogeLaMaquina()` lee del borrador, y el borrador de una corrección **nace vacío**
   (`web/app.js:18521`: `suyo.borrador = {}`) y solo se rellena con lo que el agricultor **vuelva a
   pulsar**:

```js
// web/app.js:17711-17723
return {
  nombre: valorDeLaCasilla("maquina-nombre"),
  clase: b.clase || "",
  …
  propiedad: b.propiedad || "",
  disponibilidad: b.disponibilidad || "",
```

Ejecutando **esa misma función** con el código real y un borrador vacío (que es el estado en el que
se queda al pulsar CORREGIR), esto es lo que se manda:

```json
{"nombre": "El Landini", "clase": "", "clasificacion_tecnica": "Tractor agrícola de ruedas",
 "matricula": "1234 ABD", "numero_serie": null, "numero_roma": null, "marca": null, "modelo": null,
 "anio": null, "propiedad": "", "horas": 2400, "disponibilidad": "", "equipo_aplicacion_id": null,
 "notas": null}
```

Y el servidor contesta (medido por la API):

```
422 {"detail":"«» no es una de las clases de máquina que se pueden elegir, así que no lo he
guardado. Elige una de la lista."}
```

**A quién le hace daño.** David copió mal la matrícula del Landini en el cuaderno de la Junta y
quiere arreglarla. Abre la máquina, pulsa CORREGIR, cambia la matrícula, pulsa GUARDAR… y le sale
«**«» no es una de las clases** de máquina que se pueden elegir»: un mensaje que habla de una lista
vacía entre comillas y que él no puede entender, porque la pantalla le acaba de enseñar la clase
(«Tractor») marcada. Perderá un rato pulsando las tres preguntas a ver si así entra, y si se cansa,
la matrícula se queda mal **en los dos sitios** (en la ficha y en la hoja 1.3 del cuaderno).

**Qué habría que hacer.** Dos líneas y un dato:
1. que `unaMaquinaPreparada` devuelva también `clase`, `propiedad` y `disponibilidad` en crudo;
2. que `recogeLaMaquina` parta de lo que ya está guardado cuando el borrador no lo traiga
   (`b.clase || maquina.clase || ""`), igual que ya hace con los campos de texto
   (`escrito(id, "matricula")`, `web/app.js:17381-17382`).

**Pruebas:** `test_la_ficha_preparada_lleva_la_clase_la_propiedad_y_la_disponibilidad`,
`test_corregir_una_maquina_no_manda_las_tres_respuestas_vacias` y
`test_el_servidor_rechaza_lo_que_hoy_manda_la_pantalla` (las tres rojas hoy; la tercera manda por la
API exactamente el cuerpo que compone la pantalla y exige que se guarde).

### 4. Medio — Lo que se apunta en la ficha nueva **no llega al cuaderno de la Junta**

**Qué pasa.** El ticket promete, por escrito, que el enlace entre las dos tablas evita escribir dos
veces lo mismo: «se enlazan los dos (`equipo_aplicacion_id`), de forma que **corregirlo una vez lo
corrige en los dos sitios y no hay dos fichas de la misma máquina**»
(`app/routers/maquinaria_api.py:389-396`, y lo mismo en la cabecera de `app/models.py:542-545` y en
el texto de la pantalla «así no se escribe dos veces»).

Y no es verdad: **son dos filas independientes y nadie las sincroniza**. Corregir la máquina escribe
en `maquinas` (`maquinaria_api.py:522-548`); la hoja 1.3 del cuaderno de la Junta —el papel y el
fichero que se entregan— se compone de `EquipoAplicacion` (`app/routers/cuaderno.py:400-413`:
nombre, tipo, número de ROMA, número de serie y las dos fechas de la ITEAF), que se queda como
estaba. Ni el número de ROMA, ni el nombre, ni la ITEAF apuntada en la ficha nueva llegan allí.

**A quién le hace daño.** David trae el pulverizador a la lista nueva, corrige el número de ROMA
(que había copiado mal) y apunta la ITEAF que le acaban de pasar: la ficha queda perfecta. En
diciembre saca el cuaderno de la Junta para firmarlo y **la hoja 1.3 sigue llevando el ROMA viejo y
la ITEAF de 2024**, porque el que se imprime es el del equipo del cuaderno. El programa le ha dicho
que era la misma máquina («no se escribe dos veces») y le entrega un papel con el dato viejo: eso es
exactamente el fallo que en este proyecto más caro sale, porque se descubre delante de un inspector.

**Qué habría que hacer.** O se sincroniza (al corregir la máquina y al apuntar una ITEAF, actualizar
el equipo enlazado; y al revés), o **el programa deja de decir que lo corrige en los dos sitios** y
la pantalla de la máquina avisa de que la hoja 1.3 se rellena en el cuaderno. Lo que no vale es
prometer lo uno y hacer lo otro.

**Pruebas:** `test_corregir_la_maquina_corrige_el_equipo_del_cuaderno` y
`test_la_iteaf_apuntada_en_la_maquinaria_llega_al_cuaderno` (rojas hoy).

### 5. Medio — La pantalla no manda `clave_de_reenvio`: dos toques apuntan dos inspecciones

**Qué pasa.** El servidor tiene el caso A12 bien resuelto y probado
(`maquinaria_api.py:741-750` y `887-896`: si llega una clave ya vista, se contesta lo que ya había).
**Pero ninguna pantalla de este ticket manda la clave**: en `guardarLoDeLaMaquinaria`
(`web/app.js:17742-17789`) los tres cuerpos (máquina, inspección y avería) se componen sin
`clave_de_reenvio`. En el resto del programa la clave se pide **al abrir el formulario**
(`claveDeReenvio`, `web/app.js:9015-9023`, con su motivo escrito: «si se pidiera al guardar, dos
pulsaciones del mismo botón mandarían dos claves distintas»), y en la maquinaria no se pide en
ningún sitio.

Medido por la API: dos envíos idénticos sin clave → **dos inspecciones** (`test_sin_clave_dos_envios_del_mismo_apunte_son_dos_inspecciones`, verde: documenta el efecto).

**A quién le hace daño.** David está apuntando la ITEAF, la conexión del campo va lenta y el botón
no responde; vuelve a pulsarlo. Quedan **dos inspecciones** de la misma máquina con la misma fecha y
el mismo papel: en su cuaderno parece que le han pasado dos, y el día que le pidan explicarlo tendrá
que decir que una es un toque de más. Y el reintento del móvil (el caso que el ticket dice cubrir en
su §1) tampoco lo cubre esta pantalla, porque la clave no viaja.

**Qué habría que hacer.** Pedir la clave al abrir cada formulario (como los demás apuntes) y
mandarla en el cuerpo de las tres altas.

**Prueba:** `test_la_pantalla_manda_la_clave_de_reenvio_en_lo_que_apunta` (roja hoy).

### 6. Medio — El reenvío no se cierra por máquina

**Qué pasa.** La consulta que reconoce un reenvío busca por finca y clave, **pero no por máquina**
(`maquinaria_api.py:741-750`, y lo mismo en las averías, `887-896`). Si llega la misma clave para
otra máquina, se contesta **la inspección de la primera** (con su `maquina_id` dentro) y la segunda
**no se apunta**.

**A quién le hace daño.** Hoy no se puede provocar desde la pantalla (la clave de la aplicación lleva
fecha y azar), pero sí desde cualquier otra cosa que hable con esta puerta: un guion que importe una
lista de inspecciones de un taller, o un cliente que reutilice la clave de la petición anterior. El
agricultor recibe un «guardado» que no es suyo y su remolque se queda sin la ITV apuntada, sin que
nada lo diga.

**Qué habría que hacer.** Cerrar el reenvío por `maquina_id` + `tipo` + clave (y por `maquina_id` +
clave en las averías). Y una prueba que lo ate.

**Prueba:** `test_la_clave_de_reenvio_no_se_confunde_entre_maquinas` (roja hoy).

### 7. Medio — La copia de los textos del test del móvil dice otra cosa que el servidor (35 textos)

**Qué pasa.** `tests_js/maquinaria.test.js` lleva su propia copia de los textos de la pantalla
(líneas 49-222) y la escribió **abreviada**. Comparada con `textos.MAQUINARIA_DE_LA_FINCA`, **35 de
sus 172 textos dicen algo distinto**; entre ellos, justo los del ticket:

| Clave | Lo que sirve el servidor | Lo que dice la copia del test |
|---|---|---|
| `clasificacion_falta` | «Falta la clasificación técnica de esta máquina, que es lo que dice qué inspecciones le tocan. **Mírala en la ficha del ROMA o en el papel de la última inspección y escríbela aquí.**» | «Falta la clasificación técnica de esta máquina, que es lo que dice qué inspecciones le tocan.» |
| `campo_proxima_fecha_pista` | «Si el papel la trae, cópiala. **Si no, déjala en blanco: el programa no la calcula.**» | «Si el papel la trae, cópiala.» |
| `form_inspeccion_pista` | «Copia las fechas del papel. **El programa no las calcula**…» | «Copia las fechas del papel.» |
| `que_es_seguro` | «La póliza de la máquina. **La del coche y la de la cosecha no son la misma.**» | «La póliza de la máquina.» |

Y falta el guardián que lo vigila: todas las demás pantallas del proyecto tienen su
`test_la_copia_lleva_los_textos_de_…` en `tests/test_interfaz.py` (líneas 852-1118), y **la
maquinaria no lo tiene**, así que la copia puede quedarse atrás sin que nada avise. Es el fallo que
este proyecto ya cerró dos veces, y está escrito en el propio AGENTS.md: «sin esto, la copia podría
quedarse con una frase vieja y el test de la pantalla comprobaría una pantalla que el agricultor no
tiene —y pasaría—».

**A quién le hace daño.** A David, dentro de unos meses: un test verde que dice que la pantalla
enseña «Mírala en la ficha del ROMA…» cuando la pantalla ya dice otra cosa (o al revés) es un test
que protege una pantalla que no existe. Y las 20 pruebas del componente son **la única** comprobación
de lo que se ve.

**Qué habría que hacer.** Copiar los textos **literales** (como hacen las otras pantallas) y añadir
el `test_la_copia_lleva_los_textos_de_la_maquinaria` que lo exige.

**Prueba:** `test_la_copia_de_los_textos_del_test_del_movil_dice_lo_que_sirve_el_servidor` (roja hoy;
nombra los 35).

### 8. Medio-bajo — Quitar una máquina borra sus obligaciones declaradas sin dejar rastro

**Qué pasa.** `quitar_maquina` borra las obligaciones de la máquina con una sentencia
(`maquinaria_api.py:586-595`) y después la máquina (con su rastro, `correcciones.borrar`). De la
máquina queda el rastro entero en la auditoría; **de las obligaciones no queda nada escrito**: ni su
aplicabilidad, ni su origen («lo dice el papel» / «lo digo yo»), ni sus notas.

**A quién le hace daño.** David apunta un remolque que le han prestado, contesta que la ITV no le
toca y que lo dice el papel, y a los dos meses lo devuelve y quita la máquina de la lista. Si algún
día le preguntan por qué ese remolque no tenía ITV apuntada, en el programa no hay ni una línea que
lo explique: la declaración se ha ido sin rastro. La regla de la casa es la contraria («nada se borra
sin rastro», y `correcciones.borrar` existe justo para esto).

**Qué habría que hacer.** Que las obligaciones se borren **dejando su rastro** en la auditoría (con
`correcciones.borrar`, una a una, o apuntando su contenido en el rastro de la máquina), o que no se
borren y se queden como parte del historial.

**Prueba:** `test_quitar_una_maquina_deja_escrito_lo_que_se_habia_declarado` (roja hoy).

### 9. Medio-bajo — Una fecha que ya pasó no se marca «Vencida» si nadie declaró la obligación

**Qué pasa.** La situación de una obligación se decide así: si nadie ha declarado si le toca, es
`no_se_si_toca` **y de ahí no se sale** (`app/maquinaria.py:309-326`): la fecha apuntada que ya pasó
no cuenta en `vencidas` (`maquinaria.py:563`), no sale el aviso M4, y la tabla escribe la fecha
**sin ninguna palabra al lado** (el renglón «Vencida» sale de la situación, `web/app.js:16926-16932`).
El aviso que sí sale —M9, «no has dicho si le toca»— **no habla de la fecha**, y además el endpoint
de planificar un trabajo lo filtra (`maquinaria.py:507-520`), así que en la lista de avisos de esa
máquina no sale nada.

**A quién le hace daño.** David trae del cuaderno el pulverizador (con su ITEAF de 2024 apuntada) y
todavía no ha contestado las cinco preguntas. En la lista lee «ITEAF el 12/05/2024» y, como no lleva
la palabra «Vencida» ni ningún aviso que hable de la fecha, parece una fecha escrita y nada más.
Se va a echar producto con el pulverizador sin saber que la ITEAF está caducada desde hace año y
medio. Lo mismo pasa con una obligación declarada «no le toca» que tenga una inspección vieja.

**Qué habría que hacer.** Que una fecha apuntada que ya pasó **se diga** aunque falte la
declaración: contarla en «vencidas» y sacar el aviso M4 (el texto de la obligación puede seguir
diciendo «no se sabe si le toca»). Es una decisión de producto, y la dejo señalada con su prueba.

**Prueba:** `test_una_fecha_ya_pasada_no_se_queda_sin_la_palabra_vencida` (roja hoy).

### 10. Bajo — Traer un equipo con próxima ITEAF pero sin última pierde esa fecha de la vista

**Qué pasa.** `traer_un_equipo_del_cuaderno` solo trae la inspección y la obligación **si el equipo
tiene fecha de la última ITEAF** (`maquinaria_api.py:446-471`); y en el cuaderno se puede apuntar la
próxima sin la última (`EquipoEntrada`, `app/schemas.py:528-529`, y la hoja 1.3 las pregunta por
separado). En ese caso la máquina queda sin inspección y sin obligación declarada, y el equipo **ya
no sale en «equipos que todavía no están en esta lista»** (porque está enlazado): la fecha que el
agricultor tenía escrita en el cuaderno **no se ve en ninguna parte de esta pantalla**.

**A quién le hace daño.** David tiene apuntado en el cuaderno «próxima ITEAF: 01/03/2029» del
pulverizador y le faltó poner la fecha de la última. Trae el equipo a la lista nueva y la ficha le
dice «No se sabe si le toca»: cree que el programa ha perdido el dato (y desde esa pantalla, es
verdad que no lo ve).

**Qué habría que hacer.** Traer también la próxima fecha cuando exista (como inspección «sin fecha
de la última» no vale —una inspección sin fecha no dice nada—, así que lo más honesto es dejar el
equipo en la lista de «equipos sin ficha» hasta que se traiga entero, o enseñar la fecha del equipo
enlazado en la ficha de la máquina).

**Prueba:** `test_traer_un_equipo_con_proxima_iteaf_pero_sin_ultima_no_pierde_la_fecha` (roja hoy).

### 11. Bajo — Dos máquinas pueden ser el mismo equipo del cuaderno

**Qué pasa.** El enlace `equipo_aplicacion_id` no es único: `desde-equipo` contesta 409 si el equipo
ya está enlazado (tiene prueba), pero por el alta y por la corrección se puede enlazar el mismo
equipo a otra máquina (`maquinaria_api.py:510-548`). Quedan dos fichas que dicen ser el mismo
pulverizador, y la lista de la maquinaria lo enseña dos veces.

**A quién le hace daño.** A David, cuando corrija una de las dos: no hay forma de saber cuál es la
buena, y la hoja 1.3 tiene un solo equipo para las dos fichas. Es la mitad del defecto 4, otra vez.

**Qué habría que hacer.** Comprobar en el alta y en la corrección que ese equipo no está ya enlazado
(409 con el mensaje M15, que ya existe).

**Prueba:** `test_dos_maquinas_no_pueden_ser_el_mismo_equipo_del_cuaderno` (roja hoy).

### 12. Bajo — Diez textos de la maquinaria se escribieron y no se enseñan en ningún sitio

**Qué pasa.** Leyendo **el programa** (`app/` y `web/`, sin contar las copias de los tests, que
nombran claves que la aplicación no usa), **10 textos** de `MAQUINARIA_DE_LA_FINCA` no se nombran en
ningún sitio:

| Clave | Texto | Por qué importa |
|---|---|---|
| **`guarda_el_papel`** (`textos.py:6846`) | «Los papeles de las inspecciones hay que poder enseñarlos **tres años**. Si los guardas en «los papeles», deja aquí apuntado cuál es.» | Es **el único texto del programa que dice cuánto hay que conservar los papeles de una inspección**, y estaba pensado para ir debajo del campo del papel. Nunca se lee |
| `proxima_fecha_pista` (`6868`) y `documento_pista` (`6873`) | «Cópiala del papel. El programa no la calcula…» / «Si lo tienes guardado en «los papeles», elígelo…» | Son las pistas escritas para el campo de la próxima fecha y el del papel; se enseñan sus primas (`campo_proxima_fecha_pista` `6742`, `campo_documento_pista` `6746`), así que estas dos se quedaron de una versión anterior |
| `equipo_ya_esta` (`6673`), `apuntar_otra_inspeccion` (`6890`), `arreglada_el` (`6901`), `sin_arreglar` (`6902`), `sin_arreglar_desde` (`6903`), `la_maquina` (`6911`), `fijate` (`6912`) | — | Textos sustituidos por otros (los `_texto` que sí usa la pantalla): ruido de mantenimiento |

**A quién le hace daño.** A David, por `guarda_el_papel`: se le pide el certificado de la ITEAF, lo
guarda donde puede, y **ninguna pantalla le ha dicho que tiene que conservarlo tres años** ni que el
programa tiene un sitio donde dejarlo apuntado. Los demás son ruido: cuestan de leer a quien
mantenga esto y hacen dudar de si el texto que se ve es el bueno.

**Qué habría que hacer.** Enseñar `guarda_el_papel` debajo del campo del papel de una inspección (es
donde estaba pensado) y borrar los otros nueve, o darles uso.

**Prueba:** `test_ningun_texto_de_la_maquinaria_se_queda_sin_usar` (roja hoy; nombra los diez).

### 13. Bajo — El guardián que impide calcular fechas solo mira un fichero

**Qué pasa.** La prueba `test_no_hay_ninguna_funcion_que_sume_dias_a_una_fecha`
(`tests/test_t14_maquinaria.py:283-296`) lee **el código de `app/maquinaria.py`** y exige que no
aparezca un `timedelta`. Es buena idea, pero el sitio donde una fecha calculada entraría de verdad
es otro: **el router**, que es quien escribe `proxima_fecha` en la fila, y **la pantalla**, que es
quien la enseña. Lo he medido (§3): metiendo el cálculo en el router, **el guardián sigue verde**.

**A quién le hace daño.** A nadie hoy (no hay ningún cálculo). El día que alguien lo meta
—«aprovecho y calculo yo la próxima»—, la prueba que existe para impedirlo no lo verá, y el
agricultor se llevará una fecha inventada con la misma cara que una del papel. Es la trampa del
ticket, que es lo que este ticket tenía que proteger.

**Qué habría que hacer.** Ensanchar el guardián a los tres ficheros (router, módulo y pantalla), que
es lo que hago en `TestNoSeCalculaNingunaFecha` (2 pruebas, verdes hoy: son el guardián que faltaba).

### 14. Bajo — El papel que demuestra la inspección no se puede abrir ni se dice cuál es *(sin prueba)*

**Qué pasa.** El contrato pide que cada obligación tenga «aplicabilidad, fuente, última inspección,
resultado, próxima fecha **y documento**». La ficha enseña **si hay papel** («Con su papel» / «Sin
papel apuntado», `web/app.js:17126,17191`), pero no **cuál** es ni deja abrirlo: el `documento_id`
llega en la respuesta y la pantalla no lo usa (`maquinaria.js:366-369`).

**A quién le hace daño.** David, en una inspección: la ficha dice que la ITEAF tiene papel, y para
enseñarlo tiene que irse a «los papeles» y buscarlo a mano entre todos los del año.

**Prueba:** ninguna. Es del navegador y la suite de Python no puede pulsar botones (ver §4). Lo dejo
señalado para que lo decida quien corresponda; si se quiere, se arregla enseñando el título del papel
(y, si existe, el botón de abrirlo, que ya tiene «los papeles»).

---

## 3. Los tres que rompí a propósito

Para saber si las pruebas del ticket **prueban de verdad**, rompí tres cosas a propósito, medí, y
**volví a dejarlo todo exactamente como estaba** (lo he comprobado línea a línea, y después he
vuelto a correr las 58 pruebas del ticket: **verdes**).

### 3.1. Un cálculo de fecha escondido en el router → **el guardián del ticket no lo ve**

* **Qué toqué:** `app/routers/maquinaria_api.py`, en `_una_inspeccion_guardable` (línea 704-710).
  Puse `"proxima_fecha": datos.proxima_fecha or datos.fecha + dt.timedelta(days=365)` (versión
  tosca) y después una versión **solo para la obligación `mantenimiento`**, que es la que ninguna
  prueba del ticket ejerce.
* **Qué medí:**
  * versión tosca: **1 rojo de 58** — y no es el guardián, es
    `test_sin_la_fecha_de_la_proxima_se_dice_que_no_se_sabe` (que sí caza un cálculo burdo);
  * versión escondida (solo `mantenimiento`): **58 verdes de 58**, y con ella puesta
    `test_no_hay_ninguna_funcion_que_sume_dias_a_una_fecha` sale **VERDE**.
  * Con la misma trampa puesta, **mi** guardián
    (`TestNoSeCalculaNingunaFecha::test_ni_el_modulo_ni_el_router_suman_dias_a_una_fecha`) sale
    **ROJO**.
* **Conclusión:** el guardián del ticket protege el módulo, no la puerta por la que entra el dato. La
  trampa del ticket (no calcular fechas) no está cerrada del todo.
* **Deshecho:** sí. `timedelta` no aparece en el router (comprobado) y las 58 pruebas del ticket
  están verdes.

### 3.2. Un valor por defecto permisivo en el modelo → **la prueba del ticket lo caza**

* **Qué toqué:** `app/models.py`, `ObligacionDeMaquina.aplicabilidad`: `default="no_se"` →
  `default="no"` (el defecto que el ticket dice que no puede repetir: «no le toca» dicho por nadie).
* **Qué medí:** **1 rojo**: `test_los_valores_por_defecto_del_modelo_no_son_permisivos`
  (`assert 'no' == 'no_se'`). La prueba hace su trabajo.
* **Deshecho:** sí (`default="no_se"` otra vez).

### 3.3. Una obligación sin fila leída como «no le toca» → **la prueba central del ticket lo caza**

* **Qué toqué:** `app/maquinaria.py:300`, en `estado_de_una_obligacion`:
  `... or NO_SE` → `... or NO`. Es exactamente el defecto número uno del proyecto, y el corazón de
  este ticket.
* **Qué medí:** **3 rojos**: `test_una_maquina_nueva_no_tiene_ninguna_obligacion_dada_por_buena`,
  `test_un_tractor_sin_roma_y_sin_iteaf_se_apunta_y_no_se_le_pide_ninguno` y
  `test_un_remolque_y_un_apero_no_comparten_el_vencimiento_de_un_tractor`. Bien: la regla está bien
  protegida.
* **Deshecho:** sí (`or NO_SE`).

---

## 4. Lo que NO he podido comprobar, y por qué

1. **PostgreSQL no está disponible hoy** (el motor de Docker está caído), así que **no he podido
   correr la suite contra el motor de producción**. Y conviene decirlo del ticket, porque su informe
   **se contradice**: su §3.1 dice que «la pasada completa sobre PostgreSQL no ha terminado dentro
   de este encargo» y remite a su §4, y su §4 **no lleva ningún resultado de PostgreSQL** (solo los
   recuentos y los dos rojos). Si esa pasada no se hizo, **lo que queda sin medir son las longitudes
   de las columnas nuevas con datos de verdad** (su propio §3.1 lo dice: el defecto del
   `varchar(30)`), y eso es la mitad de por qué este proyecto corre una pasada allí.
2. **No he abierto un navegador.** Los defectos 1, 2 y 3 los he demostrado **ejecutando el código
   real de `app.js` con `node`** (extrayendo la función y llamándola con los datos que devuelve el
   servidor: es el `TypeError` y el «undefined» de arriba, literales). Es una medida fuerte, pero
   **no es un recorrido**: no he visto la pantalla rota con los ojos ni he medido anchos. La
   comprobación de anchos que el ticket hizo (1.621 px → dentro de `.tabla-scroll`) no la he
   repetido, y **no la pongo en duda**: su medición es de fiar.
3. **No he corrido `scripts/humo.py`** contra un servidor de verdad. Habría hecho falta levantar un
   servidor (con base temporal y en un puerto libre) y **no aporta nada a estos defectos**: es un
   guion de API, y los tres graves viven en el navegador. Lo que sí he corrido es la API entera por
   sus puertas (`TestClient`), que es de donde salen los defectos 4 a 11.
4. **La suite de JavaScript la he corrido, pero no la he ampliado.** `node --test` da **896 pruebas
   y 0 fallos** (medido hoy), o sea que el ticket no ha roto nada. Las dos pruebas de recorrido que
   harían falta para cazar los defectos 1 y 3 (pulsar APUNTAR UNA INSPECCIÓN y CORREGIR una
   máquina) **no las he escrito porque solo puedo escribir dos ficheros y ninguno es de
   `tests_js/`**. Los defectos 1 y 3 los he cazado desde Python con pruebas que **leen el código**
   (estáticas): cazan el defecto y evitan que vuelva, pero no sustituyen a un recorrido.
5. **Nada de esto está comprobado con un agricultor delante** (lo mismo que dice el ticket en su
   §3.3): no sé si las cinco obligaciones se entienden, ni si «Falta la clasificación técnica» dice
   lo suficiente. Eso no lo dice ninguna prueba.
6. **No he podido verificar la clasificación técnica contra la norma** (L07 sigue sin transcribir):
   el programa la guarda como texto libre y no la valida, que es lo que el ticket decidió, y me
   parece bien. Pero no hay forma de comprobar que lo que el agricultor copia del papel sea la
   clasificación de verdad.
7. **Aviso de que el repositorio se mueve mientras reviso:** `app/textos.py` **ha cambiado durante
   esta revisión** (a las 12:22, +5 líneas en otro sitio: el bloque de la maquinaria pasó de la
   línea 6613 a la 6618). No cambia nada de lo que cuento (he vuelto a comprobar las claves que
   faltan), pero **las líneas de este informe son las de hoy a las 12:50**. `app.js`,
   `maquinaria.js`, `app/models.py`, `app/maquinaria.py`, `app/routers/maquinaria_api.py` y
   `tests/test_t14_maquinaria.py` no los ha tocado nadie más que yo (y yo solo para romper y
   deshacer, §3).

---

## 5. Las pruebas, los recuentos y lo que le toca al coordinador

**Lo que he corrido** (desde `F:\EspacioCodigo\CueDigital\backend`):

| Qué | Comando | Resultado |
|---|---|---|
| Lo mío y lo del ticket | `..\.venv\Scripts\python.exe -m pytest tests/test_t14_maquinaria.py tests/test_revision_t14.py -q` | **16 en rojo, 66 en verde**: las 58 del ticket **verdes**, y 16 de mis 24 rojas (una por defecto) |
| La suite entera | `..\.venv\Scripts\python.exe -m pytest tests -q` | **3958 pruebas recogidas** (medido con mis dos ficheros): en rojo, **mis 16** y **1 de `test_lista_de_la_junta.py`** (el recuento de la documentación, ver abajo). Todo lo demás, verde |
| Las de JavaScript | `node --test "tests_js/*.test.js"` | **896 pruebas, 0 en rojo** |

**Ficheros que he escrito (los dos que podía escribir, y ninguno más):**

* `backend/tests/test_revision_t14.py` — 24 pruebas (16 rojas a propósito + 8 verdes).
* `docs/REVISION_T14.md` — este informe.

**Y el recuento, que le toca al coordinador** (los tres ficheros compartidos no los toco):

* **La suite de Python tiene hoy 3958 pruebas** (medido con los dos ficheros de esta revisión; mis
  dos ficheros nuevos suman además **2 casos cada uno** al `parametrize` de
  `tests/test_ficheros_de_texto.py`). **Sin mi fichero de pruebas son 3934** y **sin ninguno de los
  dos, 3930**: lo he medido con `--collect-only`.
* **Los tres documentos dicen 3955** (`README.md:1378`, `AGENTS.md:45`,
  `docs/LO_QUE_PIDE_LA_JUNTA.md:22`), así que `test_el_numero_de_pruebas_de_python_es_el_de_verdad`
  está **en rojo** — y **ya lo estaba antes de que yo llegara**: mis dos ficheros explican 28 de las
  3958 (las 24 pruebas, más 2 casos por fichero en `test_ficheros_de_texto.py`), así que lo que había
  antes eran **3930** y la documentación decía 3955. Sospecho que hay pruebas que no se recogen hoy
  porque dependen de PostgreSQL y el motor de Docker está caído, pero **eso no lo he podido
  comprobar** y es lo primero que miraría: hay que medirlo con el motor levantado y alinear los tres
  sitios.
* **El recuento de JavaScript (896) sí está bien en los tres**, y mi trabajo no lo cambia.
* El ticket dice en su §4 que hay **3886 pruebas de Python y 2 rojos** y que los documentos dicen
  3818: **las dos cosas están desfasadas** a día de hoy (los documentos ya se movieron a 3955 y la
  suite está en 3930–3958). Su §4, por tanto, ya no sirve como medida: hay que volver a medir.
