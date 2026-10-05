# T05 / E2 — Identidad y versiones del recinto; importación repetible sobre copia

> **Qué es este documento.** La entrega de T05 contada sin adornos: **qué se ha construido**, **qué
> había ya** y se ha reutilizado, **qué decisiones se han tomado y por qué**, **qué no se ha podido
> comprobar** y **qué falta de otros** (ficheros que no eran míos).
>
> **Manda lo que digan el código y las pruebas**, no este documento. Todo lo que se afirma aquí se
> puede comprobar con el comando que se escribe al lado.

Última actualización: **02/10/2026** (la fecha del reloj de la máquina donde se ha hecho el trabajo;
los documentos del repositorio usan fechas de ronda que pueden ir por delante de esta).

---

## 1. Qué se ha construido

### 1.1. La tabla `versiones_de_recinto` (`backend/app/models.py`)

Una fila por **tierra, campaña y fuente**: la frase del contrato (§2.1) traducida a una restricción
única. Guarda:

| Qué | Columna | Detalle |
|---|---|---|
| La tierra y su campaña | `parcela_id`, `campana_id` | Las dos con su índice y su clave foránea. |
| De dónde se supo | `fuente`, `fecha_consulta` | `sigpac`, `cuaderno_de_la_junta`, `agricultor`, `medicion_en_campo`. |
| La referencia, tal y como vino | `provincia`, `municipio`, `agregado`, `zona`, `poligono`, `numero_parcela`, `numero_recinto`, `referencia`, `clave` | `referencia` es la de los siete números y **solo** cuando están todos. |
| Si el polígono es válido | `poligono_valido` | Falso cuando falta cualquier número: una referencia sin el recinto no lo es. |
| La forma | `geometria` | WKT, como en `Parcela`. Vacía = recinto **sin forma**, que es una cosa de verdad. |
| **Las tres áreas** | `area_geometria_ha`, `area_sigpac_ha`, `area_declarada_ha` | Tres magnitudes distintas. Ninguna se deduce de otra. |
| El uso, la pendiente y la revisión | `uso_sigpac`, `pendiente_pct`, `estado_revision` | `sin_revisar` al entrar: importar no es revisar. |

### 1.2. El servicio (`backend/app/versiones_de_recinto.py`, nuevo)

  · `numeros_de_la_referencia` / `referencia_completa` / `clave_del_recinto`: leer una referencia de
    las tres formas que existen (los siete números, los seis del visor, la referencia catastral),
    **sin rellenar ningún número que no venga**.
  · `comparar(antes, despues)` y `que_cambio`: la comparación `igual / cambiado / desaparecido /
    nuevo` con el porqué. **Función pura: no escribe nada.**
  · `buscar_solapes`, `diferencia_de_superficie`: los solapes y las diferencias de superficie.
  · `plan_de_importacion` (solo lee) y `aplicar_importacion` (escribe, de forma repetible): las dos
    usan la misma preparación (`preparar_el_lote`), así que lo que se enseña antes de aplicar **no
    puede** diferir de lo que pasa después.

### 1.3. Las cinco rutas (`backend/app/routers/versiones_api.py`, nuevo)

```
POST /api/versiones/previsualizar         qué pasaría con un lote (no escribe nada)
POST /api/versiones/aplicar               importar el lote (aplicarlo dos veces no duplica nada)
GET  /api/versiones                       las versiones de una tierra o de toda la finca
GET  /api/versiones/comparar              igual/cambiado/desaparecido/nuevo de una tierra
GET  /api/versiones/comparar-explotacion  lo mismo, de la finca entera
```

Todas pasan por `explotacion` (`deps.py`) y por `obtener_de_la_explotacion` para las tierras y las
campañas: **404 y no 403**, para no decir si un identificador existe en el cuaderno de otro.

### 1.4. Medir una forma (`backend/app/geo.py`)

`area_ha`, `anillos_de_un_wkt`, `rectangulo_de_un_wkt`, `punto_dentro_del_wkt` y `se_solapan`. Estaba
pedido en el encargo («si ya hay una forma de medir el área de un WKT, úsala; si no la hay,
impleméntala ahí con su prueba»): **no había ninguna**, así que se ha implementado aquí, con sus
pruebas en `backend/tests/test_geo.py`.

### 1.5. Los textos (`backend/app/textos.py`)

  · Un bloque nuevo al final, `VERSIONES_DE_RECINTO`: los nombres de las cuatro fuentes, los cuatro
    estados de la comparación, los estados de revisión, **qué es cada cosa que puede cambiar** («la
    forma del trozo», «las hectáreas que declaras»…) y las frases que dicen cómo está una versión
    («Sin forma: no ha venido el polígono»). Registrado en `textos_visibles()`, como los demás.
  · Trece mensajes nuevos en `MENSAJES` (`R1_`…`R13_`): lo que se dice cuando el lote no se puede
    apuntar del todo, y el resumen de la comparación. Ninguno bloquea el trabajo: el recinto que no
    se puede guardar se explica y los demás se guardan.

### 1.6. Las pruebas

  · `backend/tests/test_versiones_de_recinto.py` — **45 pruebas nuevas**.
  · `backend/tests/test_geo.py` — **12 pruebas nuevas** de la medida de una forma (el fichero tenía
    10 y tiene 22).

**Total: 57 pruebas nuevas** (Python; este ticket no ha tocado JavaScript).

---

## 2. Qué había ya, y se ha reutilizado (no se ha duplicado)

  · **`Parcela`** sigue siendo «lo que la tierra es hoy»: alias, referencia, forma, superficie
    declarada y del SIGPAC. **No se ha tocado ni una columna suya**; la versión es una tabla aparte,
    y esa separación es justamente el contrato (§2.1: «Separar tierra que el agricultor reconoce,
    recinto SIGPAC de una campaña y superficie declarada a la PAC»).
  · **`sigpac.lee_busqueda`** lee la referencia del lote: el mismo lector que usa el mapa, para no
    tener dos maneras de entender una referencia.
  · **`catalogos.municipio_por_codigo_ine`** convierte los códigos que manda el SIGPAC en el nombre
    del pueblo, igual que el alta desde el SIGPAC (`routers/parcelas.py`).
  · **`geo.centroide_wkt` y `geo.dibujo_svg`** siguen siendo los que dibujan el trozo: la versión no
    trae un dibujo propio.
  · **`auditoria`** guarda lo que había antes de cada cambio de una versión, con el mismo criterio
    que el resto del programa (nada se cambia sin rastro).
  · **`deps.obtener_de_la_explotacion`** es el patrón de aislamiento que sigue este router.
  · **`db_sesion`, `cliente`, `cuenta`, `crear_cuenta`, `campana`** son las fixtures que ya existían
    en `tests/conftest.py`. No se ha añadido ninguna fixture compartida.

---

## 3. Decisiones, con su motivo

### 3.1. Una versión por tierra, campaña y fuente (y no una por recinto)

Es lo que dice el contrato, literal («una versión por campaña y fuente»), y encaja con el modelo de
hoy: **una tierra es un recinto** (`Parcela` guarda una referencia del SIGPAC con su número de
recinto). El día que una tierra pueda llevar varios recintos —el `VinculoTierraRecinto` del contrato
§11, que todavía no existe— hará falta una fila por vínculo.

**Consecuencia, dicha entera:** dos recintos distintos de la misma tierra en el mismo lote y la misma
fuente son un dato contradictorio, y el programa **lo dice** (`R6_recinto_repetido`) en vez de guardar
el último y callarse. Está probado en
`TestLoQueElLoteNoSePuedeApuntar::test_dos_recintos_distintos_para_la_misma_tierra_en_un_lote_se_dicen`.

### 3.2. `clave`: con qué recinto hablaba la importación

La referencia completa si está; si viene a medias, lo que sí vino; y si no vino ninguna referencia,
la huella de la forma. Sirve para reconocer el mismo lote repetido y para avisar del caso de arriba.
**Límite conocido y asumido:** dos recintos de la misma tierra a los que les falta el mismo trozo y
traen los mismos números son, para el programa, el mismo recinto. No se pueden distinguir, y tratarlos
como dos sería inventarse una diferencia que nadie ha visto.

### 3.3. Lo que no viene no se borra

Al actualizar una versión, **un campo que la entrada no trae se queda como estaba**
(`CAMPOS_QUE_UNA_IMPORTACION_NO_BORRA`). Es lo que hace que la importación repetible se pueda medir
—si no, la segunda aplicación compararía lo que trae el lote (con huecos) contra lo guardado (sin
ellos) y creería que hay cambios— y, sobre todo, es lo que protege las hectáreas declaradas: el
SIGPAC no puede llevarse por delante un dato que puso el agricultor. Probado en
`TestLasHectareasDeclaradasNoSeSustituyen`.

### 3.4. La fecha de consulta no se rellena con la de hoy

Si el lote no dice cuándo se consultó, se queda en blanco. Poner la fecha de hoy afirmaría una
consulta que quizá se hizo en marzo, que es exactamente el defecto que persigue
`docs/T02_VALORES_POR_DEFECTO.md`.

### 3.5. El área de la forma se calcula aquí, y está comprobada contra el SIGPAC

Se mide sobre un plano local en metros (cada grado de longitud corregido por el coseno de la
latitud, como en `dibujo_svg`), y **el número está contrastado con datos oficiales**:

| Recinto oficial (`data/sigpac/`) | Superficie que publica el SIGPAC | Área medida por `geo.area_ha` | Diferencia |
|---|---|---|---|
| `recinto_de_ejemplo.json` | 2,7923 ha | **2,788534 ha** | −0,13 % |
| `recinto_de_ejemplo_503_51.json` | 4,9016 ha | **4,893739 ha** | −0,16 % |

Es el orden de error que se espera de medir sobre un plano en vez de sobre el elipsoide, y **no
cambia ninguna decisión**: la superficie que se declara sigue siendo la del SIGPAC o la del
agricultor, nunca esta. Los anillos se suman **por profundidad** (el de fuera suma, un agujero resta,
una isla dentro de un agujero vuelve a sumar), así que el resultado no depende de hacia dónde estén
dibujados los anillos.

### 3.6. A partir del 2 % se avisa de que dos superficies no cuadran

No es un número puesto a ojo: el error medido de la medida es del 0,13–0,16 % (§3.5), así que el 2 %
es unas quince veces ese error y no salta por cómo se mide, y sigue siendo lo bastante fino para que
una parcela de una hectárea avise cuando se le van 200 m². **No es un límite legal**: es el punto a
partir del cual merece la pena que alguien mire. Por debajo también se dice cuánto se llevan,
simplemente no se marca como aviso.

### 3.7. Los solapes tienen **tres respuestas**, no dos

  · **`si`** — un vértice de una forma cae dentro de la otra: hay solape, seguro.
  · **`puede`** — los rectángulos que envuelven las formas se tocan pero ningún vértice cae dentro:
    es el caso de dos trozos que se cruzan como una cruz, y también el de dos que se rozan.
  · **`no`** — los rectángulos no se tocan, así que las formas tampoco.
  · **`no_se`** — a alguna le falta la forma.

Calcular la intersección exacta de dos polígonos no se hace aquí, y **se dice por qué**: no se va a
recortar ninguna parcela sola. Lo que sí se puede decir sin inventar nada es lo de arriba, y el
contrato pide exactamente eso: **detectar y avisar, no corregir**. Probado en
`TestLosSolapesYLasSuperficies` y en `tests/test_geo.py::TestSiDosTrozosSePisan`.

### 3.8. Comparar se hace por (tierra, fuente), y la forma se compara por su texto

  · Por **(tierra, fuente)**: el SIGPAC de un año con el SIGPAC de otro, y lo que dijo el agricultor
    con lo que dijo el agricultor. Mezclar fuentes diría «cambiado» de un recinto que solo ha mirado
    otra.
  · La **forma** se compara **por el texto que vino**. Un recinto cuyos vértices vengan en otro orden
    saldrá como «cambiado» aunque sea el mismo trozo, y eso el agricultor lo ve en pantalla con su
    porqué y decide. Comparar formas de verdad es calcular su intersección (§3.7).
  · **No se compara el estado de revisión** (marcar algo como revisado no es que el recinto haya
    cambiado) **ni la fecha de consulta** (dice cuándo se miró, no cómo es el recinto).

### 3.9. Un recinto que no se puede identificar **no se apunta, y se dice qué falta**

Si un renglón del lote no trae ni referencia ni forma, o trae una referencia sin el número de
recinto sin decir a qué tierra va, o hay dos tierras que podrían ser la suya, el programa **no elige
ninguna**: lo pone en `problemas` con el motivo escrito y sigue con los demás. Lo que **no** hace es
dar de alta una tierra sin referencia, y el motivo es doble: sería inventarse una tierra y, además,
la próxima importación del mismo lote crearía **otra** (no habría nada con lo que reconocerla), con lo
que la importación dejaría de ser repetible.

Se da de alta una tierra **solo cuando el lote trae su referencia completa**, y con lo que el lote
trae y nada más: ni el alias de nadie, ni la superficie del SIGPAC copiada a la que se cultiva
(`superficie_ha` es la declarada, y si no viene, se queda en blanco).

### 3.9 bis. La tierra se reconoce por su referencia **y por sus números**

`Parcela.ref_sigpac` es texto, y hay tierras que se dieron de alta a mano o que llegaron del cuaderno
de la Junta **sin la referencia escrita** pero con su polígono, su parcela y su recinto. Si la
búsqueda se quedara en el texto, el lote daría de alta una tierra repetida, que es justo lo que el
contrato prohíbe. Así que cuando la referencia no encuentra nada se buscan sus números, **con el
número de recinto dentro**: sin él, dos tierras de la misma parcela serían indistinguibles y entonces
**no se elige ninguna** (se dice en `problemas`). Probado en
`TestLaVersionNoTocaLaTierra::test_la_tierra_se_reconoce_por_sus_numeros_aunque_no_tenga_la_referencia_escrita`.

### 3.10. La tabla nueva cuenta como dependencia de la tierra y como «otra cosa» del año

Dos guardianes del proyecto avisaron de que había que decidir (y eso es justo lo que existen para
hacer):

  · `tests/test_las_tierras_se_pueden_corregir.py::test_las_tablas_que_apuntan_a_una_tierra_se_cuentan_todas`
    → **sí es una dependencia**: a una tierra con versiones importadas no se le puede dar al botón
    de borrar; se corrige, y el mensaje es el de siempre (`B2_tierra_con_apuntes`).
  · `tests/test_analisis_ventas_planes_y_campanas.py::test_las_tablas_que_apuntan_a_una_campana_son_las_de_hoy`
    y `test_todas_las_tablas_del_ano_estan_clasificadas` → entra en **`OTRAS_COSAS`**
    (`routers/explotacion.py`): no es un apunte del cuaderno ni una tierra con su cultivo dicho, es
    la ficha de qué era esa tierra ese año. Cuenta para el total, porque borrar el año se llevaría
    por delante la historia de sus recintos.

Las dos pruebas se han actualizado **explicando por qué el comportamiento nuevo es el correcto**
(`AGENTS.md` §1), y ninguna se ha desactivado ni borrado.

---

## 4. Cómo se comprueba

```powershell
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests\test_versiones_de_recinto.py -q --junit-xml=$env:TEMP\t05.xml
..\.venv\Scripts\python.exe -m pytest tests\test_geo.py -q --junit-xml=$env:TEMP\t05_geo.xml
..\.venv\Scripts\python.exe -m pytest tests -q --junit-xml=$env:TEMP\t05_todo.xml
node --test "tests_js/*.test.js"
```

Resultados medidos el 02/10/2026 (se leen del XML, que es lo que dice la verdad):

| Qué | Pruebas | Fallos | Errores |
|---|---|---|---|
| `tests/test_versiones_de_recinto.py` (nuevo) | **45** | 0 | 0 |
| `tests/test_geo.py` | **22** (12 nuevos) | 0 | 0 |
| Suite de Python entera | **3284** | **4** → ver §5.1 | 0 |
| Suite de JavaScript entera | **734** | 0 | 0 |

(La suite entera se midió tres veces: 3276 pruebas, luego 3280 y luego 3284. La diferencia no es de
este ticket: hay otro agente añadiendo pruebas a la vez. Las 67 de esta tabla —45 + 22— pasan las tres
veces.)

Las pruebas de la suite entera que fallan están explicadas una por una en §5.1: **ninguna es de este
ticket**, y las dos que sí lo eran (los guardianes de tablas) ya están actualizadas y en verde.

**Ninguna prueba toca la base del agricultor.** `tests/conftest.py` fija `CUEDIGITAL_DATABASE_URL` a
una carpeta temporal antes de importar nada de `app`, y todos los datos que usan estas pruebas se
construyen dentro de la propia prueba (con dos excepciones que leen respuestas **de verdad** del
SIGPAC guardadas en `data/sigpac/`, sin salir a internet).

---

## 5. Lo que **no** se ha podido comprobar, y lo que no se ha hecho

### 5.1. Las pruebas rojas de la suite, dichas con nombre

Al correr la suite entera salen **3284 pruebas con 4 fallos**, y **ninguno es de este ticket**:

  1. `tests/test_lista_de_la_junta.py::test_los_numeros_de_test_de_la_documentacion_no_se_quedan_viejos`
     — Compara el número de pruebas de JavaScript que dicen `README.md`/`AGENTS.md`/
     `docs/LO_QUE_PIDE_LA_JUNTA.md` (**712**) con las que hay de verdad en `backend/tests_js/*.test.js`
     (**734**, medido con `node --test` y contando los `test(` de los ficheros). Este ticket **no ha
     tocado ni un fichero de `tests_js/` ni de `web/`**, así que el desfase viene de ahí. Arreglarlo es
     cambiar un número en tres documentos compartidos, y hacerlo ahora mismo volvería a quedarse viejo
     en cuanto el otro agente añada la siguiente prueba: **lo tiene que cerrar el coordinador cuando
     pare ese trabajo**.
  2, 3 y 4. `test_comprobar_en_un_navegador.py::test_la_pagina_de_la_comprobacion_no_se_queda_en_la_aplicacion`
     y dos casos de `test_ficheros_de_texto.py` (`[_comprobacion_navegador.html]`) — **son transitorios
     y de otro agente**: su guion de comprobación en un navegador escribe
     `backend/web/_comprobacion_navegador.html` **dentro de la aplicación** mientras corre, y si la
     suite pasa en ese momento ve un fichero que no debería estar ahí. Comprobado: con ese fichero
     fuera del disco, esos dos ficheros de pruebas pasan enteros (**807 pruebas, 0 fallos**).
     Este ticket no ha tocado `web/`, y no borra ese fichero a mano porque es el otro agente quien lo
     está escribiendo ahora mismo.
  5. Los dos guardianes de tablas (que sí fallaban por este ticket): **ya están en verde**,
     actualizados con su motivo (§3.10), y con ellos la suite pasó de 3 fallos a 1.

Además, la suite de Python tiene **3284** pruebas y los tres documentos dicen **3195**. Antes de este
ticket la suite tenía **3227** (3284 − 45 − 12), así que el número llevaba tiempo desfasado: la prueba
que lo vigila solo comprueba que los tres documentos **digan lo mismo entre ellos**, no que coincidan
con la realidad. Actualizar esos tres documentos no es de este ticket (son compartidos) y se apunta en
§7.

### 5.2. No hay pantalla

Este ticket es la capa de datos y de servidor. **No se ha tocado ni un fichero de `backend/web/`**
(eran de otro agente y no eran de este encargo): la tabla de tierras con su grupo «sin forma», la
ficha de una tierra con sus versiones y la previsualización de una importación **están por hacer** en
la interfaz, y son de T06. La API ya devuelve todo lo que hace falta para pintarlas, incluidos los
nombres resueltos (`fuente_texto`, `anio`, `estado_texto`, `como_esta`).

### 5.3. No se ha abierto la base del agricultor

Ni para leer. **No se sabe cuántas tierras del agricultor tienen ya una referencia completa**, ni
cuántas se enlazarían solas si se importara un lote del SIGPAC hoy. Tampoco se ha ejecutado
`scripts/humo.py` contra un servidor de verdad (necesita levantar el programa y ese recorrido sale a
internet; el recorrido completo de estas rutas **sí** se ha probado de punta a punta con el cliente
de pruebas de FastAPI, sobre base temporal).

### 5.4. Lo que la comparación no ve, y se sabe

  · Dos formas **iguales dibujadas de otra manera** (vértices en otro orden, o el anillo cerrado con
    otro vértice) salen como «cambiado»: la forma se compara por el texto que vino, no por su
    geometría.
  · La **versión vieja de una tierra que viene en el mismo lote** no se compara con la nueva para
    buscar solapes (sería la misma tierra consigo misma y saldría «se pisan» en cada corrección): por
    eso, y solo por eso, dos tierras distintas cuya clave a medias sea idéntica no se avisan entre sí.
  · El **solape** entre dos formas que se cruzan sin ningún vértice dentro se dice como «puede», no
    como «sí» (§3.7).

### 5.5. Cosas del encargo que no se han hecho, a propósito

  · **No se ha tocado `scripts/humo.py`**: añadirle un caso de aceptación de la importación sería lo
    suyo, pero es un fichero compartido y el encargo no lo pedía. Queda apuntado en §7.
  · **No se ha escrito ninguna migración**: la tabla es nueva y `crear_tablas()` la crea sola al
    arrancar (`AGENTS.md` §3.9), así que no hay nada que migrar. Todas sus columnas nuevas admiten
    vacío o traen valor por defecto, así que no entra en `COLUMNAS_QUE_DEJARON_DE_SER_OBLIGATORIAS`.

---

## 6. Ficheros

**Creados:**

```
backend/app/versiones_de_recinto.py                  El servicio (versiones, comparación, importación)
backend/app/routers/versiones_api.py                 Las cinco rutas
backend/tests/test_versiones_de_recinto.py           45 pruebas
docs/T05_IDENTIDAD_Y_VERSIONES_DEL_RECINTO.md        Este documento
```

**Modificados (todos con el editor de ficheros, nunca reescribiendo desde PowerShell):**

```
backend/app/models.py             + VersionDeRecinto (al final, sin reordenar nada)
backend/app/schemas.py            + 9 esquemas de entrada y salida (al final)
backend/app/geo.py                + area_ha, anillos, rectángulo, punto dentro, solapes
backend/app/textos.py             + VERSIONES_DE_RECINTO y 13 mensajes R1–R13, registrados
backend/app/main.py               + el router nuevo (una línea, detrás de iuws_api)
backend/app/routers/explotacion.py + "VersionDeRecinto" en OTRAS_COSAS (con su motivo)
backend/tests/test_geo.py         + 12 pruebas de la medida de una forma
backend/tests/test_las_tierras_se_pueden_corregir.py        guardián: 8 tablas, con su motivo
backend/tests/test_analisis_ventas_planes_y_campanas.py     guardián: 12 tablas, con su motivo
```

---

## 7. Lo que hace falta de otros (ficheros que no eran de este ticket)

1. **`backend/app/routers/parcelas.py`, línea ~755** (docstring de
   `_cuantos_apuntes_tiene_la_tierra`): dice «**Son las siete que hay**: tratamientos, abonos,
   labores, el cultivo declarado de una campaña, análisis, ventas y planes de abono». Ahora son
   **ocho**: falta la versión del recinto. El código no hace nada distinto —la cuenta se saca de las
   tablas de verdad—, pero el comentario se ha quedado viejo y este ticket no ha tocado ese fichero
   para no chocar con T06, que trabaja justo ahí. **Cambio necesario:** «siete» → «ocho» y añadir «la
   versión del recinto» a la lista.
2. **`README.md` (líneas 1369 y 1372), `AGENTS.md` (línea 45) y `docs/LO_QUE_PIDE_LA_JUNTA.md`
   (línea 22)**: los tres dicen **3195 pruebas de Python y 712 de JavaScript**. Lo real, medido, es
   **3284** de Python y **734** de JavaScript. Mientras los tres sigan diciendo lo mismo, la prueba
   que los vigila pasa para Python; la de JavaScript **falla** (§5.1) porque esa sí comprueba la
   realidad. **Cambio necesario:** actualizar los tres números **cuando el otro agente termine** de
   tocar `tests_js/`, o la cifra volverá a quedarse vieja.
3. **`backend/scripts/humo.py`**: el recorrido completo contra un servidor de verdad no tiene ningún
   caso de T05. **Cambio necesario (cuando se pida):** previsualizar un lote, aplicarlo dos veces y
   comprobar que la segunda no crea nada.
4. **La pantalla (T06)**: la tabla de tierras con el grupo «sin forma», la ficha de la tierra con sus
   versiones y la previsualización de la importación. La API ya sirve todo lo que hace falta.
