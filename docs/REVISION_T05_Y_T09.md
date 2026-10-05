# Revisión independiente de T05 y T09

> **Qué es esto.** La revisión de las dos entregas que se dieron por buenas: **T05** (identidad y
> versiones del recinto) y **T09** (el almacén, servidor y pantalla). No es un resumen de los
> documentos: es un intento de **demostrar que están mal**, contrato por contrato, provocándolo con
> el cliente de pruebas de FastAPI sobre bases temporales.
>
> **Lo que no se ha hecho.** No se ha abierto `backend/cuedigital.db` (ni para leer). No se ha
> modificado **ningún** fichero que ya existía. Todo lo que se ha escrito son dos ficheros nuevos:
> este informe y `backend/tests/test_revision_t05_y_t09.py` (**100 pruebas**).
>
> Autor: subagente de revisión independiente (ronda 6). Estado final: **02/10/2026, 17:45**.

---

## 0. Resultado, en cuatro líneas

**102 pruebas nuevas. 0 fallos.** Los **trece defectos** que ha encontrado esta revisión están
arreglados, y **cuatro de ellos citan en su comentario que los encontró la revisión independiente**.
El último (D8) se cerró a las 17:53, mientras se escribía este informe. Ejecutando esto junto con las
suites de las dos entregas y los guardianes del proyecto: **1.113 pruebas, 0 fallos, 0 errores**,
comprobado **dos veces seguidas**.

**El estado final de cada defecto, con la prueba que lo demuestra, está en §10**, que es la tabla que
pidió el coordinador para saber qué se cerró y qué no.

```powershell
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests\test_revision_t05_y_t09.py -q -p no:randomly --junit-xml=$env:TEMP\rev.xml
# Leer el XML, no la consola: la consola no imprime el resumen.
```

### Contra qué estado está hecha (el árbol se movió **más de quince veces** durante la revisión)

| Fichero | Última escritura | SHA-256 (16 primeros) |
|---|---|---|
| `backend/app/versiones_de_recinto.py` | 02/10/2026 17:53:09 | `8688215CB4FE09BD` |
| `backend/app/routers/versiones_api.py` | 02/10/2026 15:58:47 | `7257303FCB2F1F11` |
| `backend/app/geo.py` | 02/10/2026 15:57:54 | `87E6B77273F8BCA8` |
| `backend/app/routers/almacen_api.py` | 02/10/2026 17:08:01 | `405A4498A5A66DA4` |
| `backend/app/models.py` | 02/10/2026 17:13:08 | `7CC22E3E13B06F68` |
| `backend/app/servicios.py` | 02/10/2026 17:17:45 | `8A5E3C85E3838E5C` |
| `backend/app/schemas.py` | 02/10/2026 16:57:44 | `F0EFB90326129A71` |
| `backend/app/textos.py` | 02/10/2026 17:10:42 | `541BA56CBACB9DAF` |
| `backend/app/database.py` | 02/10/2026 17:42:26 | `9A05BCDDF6B079C4` |

> **Aviso que hay que conservar**: durante las dos horas largas de esta revisión el árbol cambió más
> de quince veces (16:57, 16:57, 16:58, 17:07, 17:08, 17:10, 17:13, 17:17, 17:20, 17:22, 17:38, 17:42,
> 17:52, 17:53…), **trece de esos cambios para arreglar defectos que iba encontrando**. Eso significa
> dos cosas, y las dos importan para leer este documento:
>
> 1. Los fallos que se ven en una ejecución son de **la versión del fichero de ese momento**. Una
>    ejecución mía de las 17:54 dio dos fallos que a las 17:56 ya no existían: estaba corriendo el
>    fichero mientras se reescribía. Los números de este informe están tomados de las últimas
>    pasadas completas (17:56 y 17:58), leídos del XML y no de la consola.
> 2. Las líneas que se citan conviene buscarlas **por el texto y no por el número**, porque los
>    ficheros se mueven cada pocos minutos.

---

## 1. Tabla de lo probado

Cada clase del fichero es un contrato del encargo. Los números son los del XML de la última pasada.

| # | Contrato a romper | Cómo se ha atacado | Resultado |
|---|---|---|---|
| 1 | **Un dato ausente nunca es 0 ni «cumple»** (5 pruebas) | Recinto sin superficies por las tres vías; entrada de albarán sin cantidad; `comprado_sin_entrar` al anular el albarán; contadores `sin_poder_saber`/`en_negativo` | **Defecto D-D, arreglado** (17:17) |
| 2 | **No se duplican existencias** (14 pruebas) | Mismo cuerpo con `clave_de_reenvio`/`id_local` 1 y 4 veces; mismo número sin clave; factura después; anulado + vuelto a apuntar; salida anulada reenviada con la misma clave; **índice único con condición en los dos dialectos** (SQLite y PostgreSQL, sin exigir la ortografía del SQL); instalación que ya tenía la tabla; **base nueva que nace con el índice bueno**; **rehacer el índice no cambia ninguna fila** | **D-A, D-B, D-C, D2 y D3: arreglados.** Nada duplica: medido |
| 3 | **Total ≠ dosis por hectárea; litros ≠ kilos** (7 pruebas) | Salida desde un apunte de 2 L en 4 ha; apunte de una nave que solo trae la dosis; total tecleado a mano; abono en kg; unidad del papel contra la de la ficha; merma en kg sobre un envase en L; salida con unidad que no cuadra | Correcto (los dos 409 y el aviso de unidades salen como dicen los documentos) |
| 4 | **Aislamiento entre fincas: 404, no 403** (18 pruebas) | Las cinco rutas de T05 y las once de T09, con identificadores **reales** de otra finca (tierra, campaña, albarán, artículo, lote, movimiento, factura, línea de factura, apunte) | **18/18 → 404.** Ninguna 403, ninguna 200. 401 sin entrar |
| 5 | **Idempotencia de la importación** (7 pruebas) | Foto campo por campo de `versiones_de_recinto` + `parcelas` + auditoría antes y después; lote repetido normal, invertido y rotado; clave a medias en dos tierras; lote contradictorio, también **en finca nueva** | **D4 y D8 arreglados.** Medido: el mismo lote en otro orden no cambia ni una fila ni deja auditoría |
| 6 | **Comparar no escribe** (2 pruebas) | `/comparar` y `/comparar-explotacion` tres veces cada uno, con foto completa antes y después | Correcto: **no escribe ni audita nada** |
| 7 | **Previsualizar no escribe y el plan es el mismo** (3 pruebas) | Previsualizar 3 veces con foto completa; comparación campo a campo del plan de previsualizar contra el de aplicar; previsualización de un lote con un renglón imposible | Correcto: lo único que cambia es `aplicada`/lo escrito y el `parcela_id` de una tierra que aún no existe (y el documento lo dice) |
| 8 | **Las hectáreas declaradas no se sustituyen; lo que no viene no se borra** (6 pruebas) | Declarada 1,75 contra SIGPAC 0,93 y contra la calculada; tierra nueva con y sin declarada; uso/pendiente/fecha que no vienen; ficha de una tierra que ya existe; estado de revisión | **D-E arreglado** (17:20). La declarada, la del SIGPAC y la calculada, como dice el contrato |
| 9 | **Un recinto sin geometría entra, se dice y no se le inventa forma** (2 pruebas) | Se aplica, se lee la fila guardada, se lista por la API | Correcto: `geometria = None`, `area_geometria_ha = None`, `tiene_forma` falso, `con` su frase |
| 10 | **El área que calcula el programa** (12 pruebas) | Cuadrado de 1 km = 100 ha; multiparte; agujero = 99 ha; isla dentro del agujero; **agujero dentro de la isla (3 niveles)**; multiparte con agujero; **las 6 permutaciones de los anillos**; el recinto **oficial** del SIGPAC; punto y línea = `None`; anillos al revés | Correcto a cualquier profundidad y sea cual sea el orden de los anillos (§7) |
| 11 | **Los textos viven en `textos.py` y no llevan jerga** (3 pruebas) | Se sacan del propio JavaScript las 113 claves `libro_…` que piden las seis pantallas nuevas y se comprueba que llegan en `/api/interfaz`; los avisos y textos de las respuestas nuevas, por `PALABRAS_PROHIBIDAS` | Correcto: **ninguna clave sin servir**, y ninguna respuesta nueva con jerga |
| 12 | **Firmas y auditoría intactas** (4 pruebas) | Huella del cuaderno antes/después de importar un lote y de sacar de un lote; huella de un apunte antes/después; anular la salida devuelve el producto | Correcto: **la huella no cambia en ningún caso** |
| 13 | **Una referencia COMPLETA que comparten varias tierras** (17 pruebas) | La finca real montada a escala (65 tierras, 52 referencias, 9 con una y 6 con otra) y **cinco puertas alternativas** (§4) | **Arreglado durante la revisión.** Hoy no elige ninguna, lo dice con `R9` y no escribe nada |
| 14 | **El cero de la referencia no es un hueco** (2 pruebas) | La clave que se **guarda** y la que sale por la API de un recinto con agregado 0 y zona 0; y `None` contra `0` | **D7 arreglado** (17:38) |

**Lo que se ha atacado sin encontrar nada, y conviene que quede dicho:** importar un lote no toca ni
una columna de `parcelas` de una tierra que ya existe; el mismo albarán dos veces no duplica nada
(ni con la clave, ni con el número, ni con el proveedor escrito de otra manera, ni desde la cola sin
cobertura); la factura que llega después no mete ni un litro; un albarán sin proveedor es el **tercer
estado** bien resuelto; y estas dos entregas no escriben en `parcelas` ni en `tratamientos`, así que
no pueden invalidar una firma histórica.

---

## 2. Ningún defecto abierto: el último (D8) se cerró a las 17:53

### D8 — La primera importación de un lote contradictorio, en una finca nueva, decidía por el orden — **baja** *(arreglado el 02/10 a las 17:53)*

- **Dónde.** `backend/app/versiones_de_recinto.py`, al final de `preparar_el_lote`. El primer arreglo
  de D4 decía, con estas palabras:

  > «si una tierra sale más de una vez en el lote, **no se guarda ninguna de sus versiones** y se
  > dice cuáles: no se sabe cuál de los dos recintos es el bueno, así que no se elige.»

  Pero la condición que lo aplicaba empezaba por `if preparado.saltado or preparado.parcela_id is
  None: continue`. Cuando la tierra **todavía no existía** —la primera importación de ese lote— las
  dos entradas tenían `parcela_id` nulo, así que **ninguna se marcaba** y decidía la regla de antes:
  se quedaba **el primero que llegara**.
- **La prueba.** `Test5LaImportacionDeRecintosIdempotente::test_la_primera_importacion_del_lote_contradictorio_tampoco_depende_del_orden`.
  Se importa el mismo lote contradictorio (dos recintos de la misma tierra, 0,93 ha con una forma de
  100 m y 99 ha con una de 1 km) en **dos fincas nuevas**, cada una con los renglones en un orden
  distinto. **Esto es lo que queda guardado, campo por campo, que es lo que hace falta para decidir**
  (lo imprime la propia prueba al fallar):

  | Campo | Lote `[100 m, 1 km]` | Lote `[1 km, 100 m]` |
  |---|---|---|
  | `clave` | `37-70-0-0-503-51-1` | `37-70-0-0-503-51-1` |
  | `referencia` | `37-70-0-0-503-51-1` | `37-70-0-0-503-51-1` |
  | `area_sigpac_ha` | **0.93** | **99.0** |
  | `area_geometria_ha` | **0.933141943359375** | **99.99999997558594** |
  | `geometria` | el cuadrado de 100 m | el cuadrado de 1 km |
  | `area_declarada_ha` | `None` | `None` |
  | `uso_sigpac`, `estado_revision`, `poligono/parcela/recinto` | iguales en los dos | iguales en los dos |

  Es decir: **ganaba el primero que llegaba**, y el `clave` es el mismo en los dos casos (es la misma
  tierra y el mismo recinto del SIGPAC: lo que cambia es la forma y las superficies que traía cada
  renglón).
- **Cómo se arregló (17:53).** Mejor de lo que yo proponía: ahora `preparar_el_lote` agrupa los
  renglones por **identidad** —y esa identidad vale tanto para una tierra que ya existe
  (`("tierra", id)`) como para una que se va a dar de alta en esa misma importación
  (`("ref", clave)`)— y, dentro de cada grupo, distingue **dos casos que no son el mismo**:
  · **el mismo apunte repetido** (misma huella, mismos datos): se queda uno y se dice del resto, que
  es el reenvío del móvil y tiene que seguir funcionando sin protestar; · **dos renglones que se
  contradicen** (mismo recinto, datos distintos): **no se guarda ninguno**, porque elegir por el orden
  en que vengan es elegir a cara o cruz. Es la opción 3 de las tres que había escrito abajo, y además
  cubre el caso de la finca nueva que era justo lo que faltaba.
- **Las tres salidas que había puesto sobre la mesa** (para el registro de cómo se decidió):
  1. **«El primero manda»**: era lo que hacía entonces; exigía decirlo en el documento y asumir que el
     mismo lote en otro orden guarda otra cosa la primera vez.
  2. **«No se guarda ninguno»** sin más: coherente con el principio escrito, pero entonces la
     importación **tampoco da de alta la tierra** y el agricultor se queda sin nada.
  3. **Mirar si los dos renglones son el mismo recinto con datos distintos** y avisar de eso en vez de
     elegir. **Es la que se ha implementado**, separándola del caso «el mismo apunte repetido».
- **Qué le pasaba al agricultor.** Un lote del cuaderno que trajera dos renglones contradictorios para
  la misma tierra le dejaba guardada una superficie o la otra según cómo vinieran escritos los
  renglones. El programa **avisaba** (`R6_recinto_repetido`) en los dos casos, así que no era
  silencioso, y hacía falta un lote contradictorio para llegar aquí: por eso era **baja** y no media.
- **Hoy pasa la prueba**, y siguen pasando las de alrededor: el lote contradictorio repetido en otro
  orden **no reescribe nada**, y el reenvío del mismo apunte no se queja.

---

## 3. Los trece defectos que encontró esta revisión, y en qué han quedado

**Ninguno lo he arreglado yo** (el código no era mío): los arregló el coordinador mientras revisaba.
**Cuatro** de ellos llevan escrito en el comentario del código que los encontró «la revisión
independiente» (D4, D6, D7 y D8, leídos). Cuatro eran **fallos de mis propias pruebas** y los arreglé
yo: se cuentan aparte, en §7, porque una prueba que no consigue ni crear el dato no demuestra nada del
producto. **Los trece están arreglados** y todos tienen su prueba dentro para que no vuelvan.

| # | Defecto | Gravedad | Cómo se veía | Arreglado |
|---|---|---|---|---|
| D-A | Reenviar el mismo albarán tras anularlo, con la misma `clave_de_reenvio`, reventaba con `UNIQUE constraint failed: recepciones.explotacion_id, recepciones.clave_de_reenvio` (lanzado en `almacen_api.py`, `db.flush()` de `crear_recepcion`). Como `app.js` (`enviarOApuntar`) **vuelve a encolar los 5xx**, era un envío en bucle | alta | 500 en la cara del agricultor al reenviar desde el móvil | 17:07 |
| D-B | Reenviar una **salida** anulada con la misma clave devolvía la anulada como si se hubiera apuntado (`ya_estaba: True`): el producto se quedaba devuelto para siempre, en silencio. Contradecía la frase literal del documento | media | Pérdida silenciosa | 17:07 |
| D-C | Una factura enganchada a un albarán **anulado** no se podía enganchar a ningún otro: 409 con «apunta el segundo con su número y engancha la factura al que la trajo», y esa salida era justo la que estaba cerrada | media | Compra sin documento y sin salida | 17:08 |
| D1 | Al anular el albarán, la compra dejaba de aparecer en «comprado y aún sin entrar»: `app/servicios.py`, `lo_comprado_que_no_ha_entrado`, llamaba a `movimientos_del_almacen(...)` sin `solo_los_que_cuentan=True`, así que una entrada de un albarán anulado contaba como «esto ya entró» | media | Almacén a cero y el programa sin decir que esa compra sigue sin entrar | 17:17 |
| D5 | `estado_revision` volvía a `sin_revisar` sin decirlo: no estaba en `CAMPOS_QUE_UNA_IMPORTACION_NO_BORRA` ni en lo que se compara, así que el plan solo decía que cambió la superficie del SIGPAC | baja | Su marca de «revisado» desaparecía | 17:20 |
| D6 | `_tierra_por_la_referencia` miraba primero el **texto** de `ref_sigpac` y, si encontraba **una**, enlazaba sin mirar los números: no veía otra tierra con los mismos números escrita de otra manera | baja | Misma historia en la tierra que no es | 17:22 |
| D-9 | **El caso real de las nueve tierras** (§4): la referencia completa se buscaba con `db.scalar(...)`, que devuelve **la primera** sin `ORDER BY`, y decía que había una sola candidata | **alta** | La versión del recinto colgada de una de las nueve tierras, elegida por el orden interno de la base, y las otras ocho sin ella y sin saberlo | 16:57 y 17:22 |
| D2 | El arreglo de D-A/D-B usaba solo `sqlite_where=`: en PostgreSQL el índice se creaba **único a secas** y el fallo volvía en producción (la base de producción es PostgreSQL) | **media-alta** | El reenvío del móvil roto en producción | 17:13 |
| D4 | El mismo lote contradictorio **en otro orden** reescribía la versión guardada y dejaba un apunte de «actualizar» en la auditoría | media | Su recinto cambiaba de forma y de hectáreas sin que él tocara nada | 17:38 |
| D7 | `clave_del_recinto` usaba `str(numeros.get(campo) or "")`: el **cero** del agregado y de la zona se caía, así que la clave de **todas** las versiones se guardaba como `37-70---507-24-1` en vez de `37-70-0-0-507-24-1`, y `None` («no lo sé») daba la misma clave que `0` («es cero») | media | Una referencia con los ceros comidos, imposible de cotejar con ningún papel | 17:38 |
| D3 | `crear_tablas()` no recreaba los índices de una tabla que ya existía: una instalación que ya tenía `recepciones` con el esquema viejo **no recibía** el arreglo de D-A/D-B | media | El fallo seguía vivo en el ordenador donde la tabla ya existía | 17:42 |

Los cuatro que eran fallos míos están en §7. **Ninguno de los trece sigue abierto: los trece están
arreglados y con su prueba dentro.**

### Y uno más, también arreglado, que el documento daba por bueno

El reparto de textos del almacén: los 178 textos nuevos viven dentro de `CESTA` con prefijo `libro_`
porque `textos.ALMACEN` **no se sirve** en `/api/interfaz`. Era un hueco declarado en el documento de
T09 (§3.5) y sigue igual; lo que sí he comprobado es que **ninguna** de las 113 claves que piden las
seis pantallas se queda sin servir, que es el fallo que ese apaño podía esconder.

---

## 4. El caso real: una referencia **completa** que comparten nueve tierras

Los datos son los que midió el coordinador sobre una copia de la base del agricultor: 65 tierras,
**52 referencias distintas**, `37-70-0-0-507-24-1` compartida por **9** tierras, `37-70-0-0-507-91-3`
por **6**, y **ninguna** a medias. La causa es legítima —el cuaderno de la Junta parte un mismo
recinto en varias líneas de cultivo (trigo, barbecho, avena)—, y la consecuencia es que **la
referencia completa no identifica una tierra**.

**Lo que había**: `db.scalar(consulta.where(Parcela.ref_sigpac == completa))` devuelve la **primera**
fila que salga de la base —sin `ORDER BY`— y la daba por buena diciendo que había **una** candidata.

**Lo que hay**: las dos búsquedas (por el texto de la referencia y por los números) se juntan, las
tierras candidatas se deduplican, y **si sale más de una no se elige ninguna**: el recinto se salta
con `R9_tierra_ambigua`.

**Lo medido con las 17 pruebas de `Test13`**, con la finca montada a escala real:

| Pregunta | Respuesta medida |
|---|---|
| ¿A cuál de las nueve le cuelga la versión? | **A ninguna.** `nuevos = cambiados = iguales = 0`, `detalle` vacío, `versiones_creadas = 0`, `tierras_creadas = []` y las 65 tierras intactas |
| ¿Se lo dice o se calla? | **Se lo dice**: un solo problema, `R9_tierra_ambigua` con `cuantas=9` y con qué hacer |
| ¿Las otras ocho se quedan sin versión y sin saberlo? | Las **nueve** se quedan sin versión y **se sabe**: el aviso es para las nueve |
| Importar dos veces ese lote | **0 versiones, 0 tierras nuevas, 0 apuntes de auditoría** las tres veces. Ni 1, ni 9, ni 18 |
| `GET /api/versiones` de toda la finca | Las nueve **sin versión** (lista vacía), y preguntando tierra por tierra, vacía en las nueve |
| Comparar dos campañas | 0 de todo: **no cuenta recintos donde no se ha apuntado ninguno** |
| Un lote con nueve renglones de la misma referencia, sin decir la tierra | **Ninguno entra** y sale **un problema por renglón** (9) |
| Los mismos nueve diciendo a qué tierra va cada uno | **Entran los nueve** (9 versiones, una por tierra) y la segunda vez `iguales = 9` sin escribir |
| La finca entera (52 referencias) | **50 versiones**, 2 problemas y **15 tierras** (9 + 6) sin versión. Y la segunda vez, las mismas 50 |
| Comparar la finca entera entre dos campañas | **50 desaparecidos** — ni 65 (tierras) ni 52 (referencias) — porque cuenta **(tierra, fuente)** |

### Las cinco puertas alternativas que he probado para volver a colar el fallo

Todas cerradas hoy (las cinco pruebas pasan):

| Puerta | Qué tenía que pasar | Resultado |
|---|---|---|
| **Solo una de las nueve tiene la referencia escrita** y las otras ocho solo los números (la puerta exacta por la que se colaba) | No elegir ninguna: 9 candidatas | Cerrada |
| La referencia **del Catastro** (`37070A507000240000AQ`, sin número de recinto) | 9 candidatas y `R9` | Cerrada |
| La referencia **del visor** (`37:70:0:0:507:24`, seis números) | 9 candidatas y `R9` | Cerrada |
| **Mezclar `parcela_id` explícito** en un renglón con la referencia compartida en otro | El explícito entra en **esa** tierra; el otro no se cuela aprovechando que el lote ya sabía de una tierra | Cerrada |
| La **tierra repetida** en el mismo lote | No crear dos versiones y decir el segundo renglón | Cerrada |

### El hueco que queda, dicho claro (no es una prueba en rojo, es una nota)

El aviso dice «hay 9 tierras que podrían ser» y **no dice cuáles**, y el plan de importación no lleva
ninguna lista de candidatas (ni identificadores ni nombres): lo comprueba
`test_el_aviso_de_las_nueve_dice_cuantas_son_pero_no_cuales`. Es decir, **el aviso no se puede
arreglar desde ninguna pantalla** sin añadir un campo, y son **15 de las 65 tierras** del agricultor
las que caen aquí. La puerta existe en la API (`parcela_id`) y está probada, pero no hay forma de
saber cuál elegir si no lo sabes ya. El documento de T05 dice (§5.2) que «la API ya devuelve todo lo
que hace falta para pintarlas»: para esas 15 tierras, **no**.

---

## 5. Lo que NO he podido probar

1. **Dos peticiones a la vez (la carrera).** He comprobado que **la restricción está y que la base la
   aplica**, pero **no he disparado dos peticiones simultáneas**: con el cliente de pruebas saldría
   una prueba que unas veces pasa y otras no, y una prueba así no protege nada. Ahora hace falta,
   además, **en PostgreSQL**.
2. **PostgreSQL de verdad.** No hay servidor. Lo único que he podido hacer es compilar el SQL en los
   dos dialectos (D2). Nada de estas dos entregas se ha ejecutado contra PostgreSQL.
3. **La base del agricultor.** No se ha abierto, por la regla del encargo. Los 65/52/9 son **sus**
   números, medidos por él sobre una copia; mis pruebas montan una finca con esa **forma**, no con
   sus datos.
4. **Un navegador de verdad.** No he abierto la pantalla del almacén ni he mirado ninguna captura. Lo
   que digo de las seis pantallas nuevas sale de leer el JavaScript y de lo que contestan las rutas.
5. **La suite de JavaScript** (`node --test`, 734 pruebas). No la he ejecutado: el encargo era atacar
   el servidor y la API. Las 21 pruebas nuevas del almacén y el reparto «la clave se pide al abrir el
   formulario» **no los he verificado**.
6. **`scripts/humo.py`** contra un servidor de verdad. No se ha ejecutado aquí: habría que levantar un
   servidor y la prueba sale a internet.
7. **El enganche de una factura con las líneas descuadradas** y **la cola del móvil sin cobertura de
   verdad**: los dos declarados como no probados en el documento de T09, y yo he probado el reenvío
   del mismo cuerpo contra la API, que es la mitad del camino.
8. **El dibujo del recinto en el mapa** (multiparte y con agujeros). He medido el **área** con las dos
   cosas; **no** he comprobado que `geo.dibujo_svg` pinte bien un multipolígono o un polígono con un
   agujero.
9. **La migración sobre una copia de la base real** que cuenta el seguimiento (§12.2). No la he
   repetido: la base real no se toca y el ensayo es del coordinador.

---

## 6. Valoración honesta de los documentos

### `docs/T05_IDENTIDAD_Y_VERSIONES_DEL_RECINTO.md`

**Lo que cuenta se corresponde con lo que hace el código**, con estas salvedades:

- **§1.2, §1.3 y §1.4 (lo construido): verdad.** La tabla, el servicio, las cinco rutas y las
  funciones de `geo.py` están y hacen lo que dice. Las cinco rutas contestan 404 y no 403 con datos
  de otra finca: **18 comprobaciones, 18 correctas**.
- **§1.5 (los textos) y §1.6 (las pruebas): verdad.** El bloque está registrado en `textos_visibles()`
  y los mensajes `R1`–`R13` existen. El número exacto de pruebas de `tests/test_geo.py` (22) lo he
  medido: **22**.
- **§3.2 (la clave del recinto) se quedaba corta y no decía la verdad del todo.** Decía que la clave
  es «la referencia completa si está; si viene a medias, lo que sí vino…», y reconocía como único
  límite que dos recintos a medias son indistinguibles. Faltaban dos cosas que sí pasaban:
  1. con la referencia completa, la clave que se guardaba **no era la referencia**: salía
     `37-70---507-24-1` porque los ceros del agregado y de la zona se caían (D7, hoy arreglado);
  2. y el límite que el documento reconoce como «a medias» es en realidad **mucho mayor**: con
     **referencias completas y válidas** compartidas por hasta nueve tierras, la referencia **no
     identifica una tierra** (§4). Ese caso no estaba en el documento y era el que tiene el
     agricultor.
- **§3.3, «lo que no viene no se borra», era una afirmación más ancha que el código:** el
  `estado_revision` **sí** se borraba (D5, arreglado).
- **§5.2, «la API ya devuelve todo lo que hace falta para pintarlas»: no del todo.** El plan de
  importación avisa de que hay nueve tierras candidatas y **no lleva ninguna lista de cuáles son**,
  así que ninguna pantalla puede ofrecer elegir (§4). Son 15 de sus 65 tierras.
- **§3.7, §3.8 y §5.4 (los tres finales del solape, la forma se compara por su texto, y lo que la
  comparación no ve): verdad**, comprobado, y es la parte más honesta del documento.
- **§4 y §5.1 (los fallos de la suite): no reejecutado.**

### `docs/T09_PANTALLA_DEL_ALMACEN.md`

- **§1 (lo que se puede hacer) y §2 (ficheros): verdad** en lo que se puede comprobar desde el
  servidor y desde los ficheros. Las seis pantallas existen y **todas** sus frases se piden a
  `textos.py` (113 claves, todas servidas).
- **§3.1 y §3.2 (el servidor cuenta; un dato que no se sabe no es un cero): verdad** en todo lo
  probado (saldo `null` con su motivo, tres estados de caducidad, las cuentas que se callan cuando no
  suman).
- **§3.3 (la clave se pide al abrir el formulario): verdad en el cliente**, y el servidor reconoce la
  clave. Lo que el documento **no** contaba es lo que pasa al **anular y reenviar** con esa misma
  clave: era D-A y D-B, y es justo el caso del campo. Hoy está arreglado, en SQLite **y** en
  PostgreSQL.
- **§3.4 y §3.5: verdad.** `textos.ALMACEN` no se sirve en `/api/interfaz` (lo he comprobado), y los
  178 textos nuevos están dentro de `CESTA` con prefijo `libro_`.
- **§4 (lo que falta en la API): verdad, punto por punto**, incluidos los cinco huecos declarados. Es
  la parte más honesta del documento.
- **§5 (las pruebas): no reejecutado** (ni `node --test` ni las siete pruebas de Python de la lista).
- **§7 (lo que no se ha podido comprobar): verdad y bien dicho.**
- **Y lo que el documento no cuenta:** que el aviso de «comprado y aún sin entrar» se quedaba mudo al
  anular el albarán (D1, arreglado), que es justo el aviso del §1.4.

### `docs/SEGUIMIENTO_IMPLEMENTACION_CRM.md`, apartado 12

- Las afirmaciones que he podido comprobar del §12.4 y del §12.5 **son verdaderas**: previsualizar no
  escribe, aplicar dos veces no duplica, un recinto sin forma entra y sale diciéndolo, la superficie
  que nadie dijo sale vacía y **nunca 0**, y las tres áreas van separadas.
- **§12.5 dice: «no hay prueba de carrera… la defensa es la restricción única de la base».**
  Comprobado que la restricción está. Sigue sin haber prueba de carrera, y ahora hace falta una **en
  PostgreSQL**.
- **§12.5 y §12.7 no mencionan el caso de las referencias completas compartidas por nueve tierras**
  (§4), que sí se ha arreglado después: el §12.5 se escribió antes y su tabla de «lo que el
  coordinador ha comprobado» no incluye esa comprobación.
- **§12.7 dice «`pytest` 3.282 casos, 0 fallos».** Con mis 100 pruebas dentro, la suite tiene los
  fallos que tengan las mías (hoy 1) más los que ya tuviera. Quien lea el recuento que sepa que
  incluye esta revisión.

---

## 7. Respuesta a la revisión del coordinador (los ocho fallos que vio)

El coordinador ejecutó este fichero y le salieron **8 fallos**. Eran de **una versión anterior** del
fichero (la de antes de las 17:25). **Hoy los ocho pasan.** Cuatro eran fallos míos de escritura
(tenía razón: no son defectos) y cuatro eran defectos de producto, que él arregló.

### Los cuatro que eran fallos de mis pruebas

Los cuatro fallaban **al construir el dato**, no al comprobar el producto, y los arreglé copiando de
las pruebas que ya pasan (`tests/conftest.py`, `tests/test_facturas.py`,
`tests/test_recepciones_lotes_y_movimientos.py`):

| Prueba | Qué pasaba | Arreglo |
|---|---|---|
| `Test2…::test_la_factura_que_llega_despues_no_vuelve_a_meter_la_mercancia` | `422 {"loc":["body","datos"],"msg":"Field required"}`: mandaba la factura como **JSON** y `POST /api/facturas` la espera como formulario con el JSON dentro del campo `datos` (en la misma petición viaja el fichero) | El ayudante `_factura` manda `data={"datos": json.dumps(cuerpo)}` |
| `Test3…::test_una_salida_desde_un_apunte_dice_el_total_y_la_dosis_por_separado` | No daba `datos`: daba `422 V4_superficie_excedida` («La parcela tiene 2,43 hectáreas y has puesto 4,00»). Fallo mío de datos | La prueba se hace su propia tierra de 5 ha |
| `Test3…::test_un_apunte_que_solo_trae_la_dosis_pide_el_total_en_vez_de_multiplicarlo` | `422 V22_sin_superficie`: un tratamiento de una **tierra** siempre tiene superficie, así que «solo la dosis» no se puede montar así | Se monta donde de verdad pasa: un tratamiento de una **nave** (`nuevo_tratamiento_en_instalacion`) |
| `Test4…::test_no_se_puede_enganchar_una_factura_de_otra_finca` | El mismo `422` de `datos` al crear la factura de la otra finca | Usa `_factura` con las cabeceras de la otra finca |

**Una corrección al diagnóstico, para que quede bien en el registro:** los cuatro **no** fallaban con
el mismo error de `datos`. Los dos de `Test3` fallaban con `V4_superficie_excedida` y
`V22_sin_superficie` (422 también, pero por validación del agricultor, no por esquema). La conclusión
es la misma —eran fallos de mis pruebas—, pero el parecido de los mensajes era casualidad.

### Los otros cuatro: lo que salía, qué esperaba y en qué ha quedado

| # | Prueba | Qué esperaba y qué salió | Qué era | Hoy |
|---|---|---|---|---|
| 1 | `Test2…::test_volver_a_apuntar_un_albaran_anulado_con_la_misma_clave_no_revienta` | Esperaba `200/201`; salió **un 500**: `sqlite3.IntegrityError: UNIQUE constraint failed: recepciones.explotacion_id, recepciones.clave_de_reenvio`, en `almacen_api.py` (`db.flush()` de `crear_recepcion`), por `UniqueConstraint(..., name="uq_recepcion_reenvio")`. La causa: `_recepcion_que_ya_estaba` buscaba la clave **solo entre los no anulados**, así que el anulado seguía ocupándola | **Defecto de producto, de los gordos**: es el reenvío desde el móvil sin cobertura, y `app.js` **vuelve a encolar los 5xx**, así que era un bucle | **Arreglado** (D-A, 17:07): índice único **parcial** (`WHERE anulada = 0`), y después también en PostgreSQL (D2, 17:38) |
| 2 | `Test1…::test_lo_comprado_que_no_ha_entrado_no_se_pierde_al_anular_el_albaran` | Esperaba `['Ejemplo 25 EC']`; salió `[]` (`assert [] == ['Ejemplo 25 EC']`). Paso a paso: compra → recibe → `comprado_sin_entrar == []` (bien) → **anula el albarán** → saldo a 0 (bien) → **`comprado_sin_entrar` sigue vacío** (mal). Sí: **se perdía el aviso** | **Defecto de producto** (D1): `servicios.py`, `movimientos_del_almacen(...)` sin `solo_los_que_cuentan=True` | **Arreglado** (17:17) |
| 3 | `Test8…::test_una_importacion_que_no_dice_el_estado_de_revision_no_lo_borra` | Esperaba `'revisado'`; salió `'sin_revisar'`, y el plan decía que solo cambió `['la superficie del SIGPAC']`, es decir: **ni lo decía** | **Defecto de producto, y sí: el mismo fallo que «las hectáreas declaradas no se sustituyen», con el estado de revisión** (D5) | **Arreglado** (17:20) |
| 4 | `Test10…::test_una_isla_dentro_del_agujero_vuelve_a_sumar` | Esperaba `99,04`; salió `98,96` | **Fallo mío de geometría, no del producto** | Corregido por mí (17:25) |

### El área con anidamiento: el número que salía era el correcto

Mi primera prueba colocaba la isla en `-4.99955`, que es **al oeste** de `-4.9995`: fuera del
agujero, no dentro. La regla par-impar hizo lo que tenía que hacer con la forma que yo dibujé (contar
la isla como un trozo suelto dentro del cuadrado grande y **restarla**), y por eso salió
`100 − 1 − 0,04 = 98,96`. Medido ahora, con la isla **dentro** del agujero:

| Forma (cuadrados, lados en metros) | Área medida | Esperada |
|---|---|---|
| Cuadrado de 1.000 m | **100,0 ha** | 100 |
| + agujero de 100 m | **99,0 ha** | 99 |
| + isla de 20 m dentro del agujero | **99,04 ha** | 99,04 |
| + agujero de 10 m dentro de la isla | **99,03 ha** | 99,03 |
| + otro trozo de 4 m dentro de ese agujero (4 niveles) | **99,0316 ha** | 99,0316 |
| Los tres primeros anillos en las **6 permutaciones** posibles | **99,04 ha** en las seis | 99,04 |

**Conclusión: el área está bien a cualquier profundidad de anidamiento y no depende del orden en que
vengan los anillos.** No hay hectáreas mal declaradas por este camino. Las dos comprobaciones quedan
como pruebas (`test_un_agujero_dentro_de_la_isla_vuelve_a_restar` y
`test_el_area_no_cambia_aunque_los_anillos_vengan_en_otro_orden`), además de la de dos niveles.

### La verificación del arreglo de `_tierra_por_la_referencia`

Hecho: no lo vuelvo a documentar, lo he atacado por **cinco puertas más** (§4). Las cinco están
cerradas hoy, incluidas las dos que se pidieron (la tierra repetida en el mismo lote y la mezcla de
`parcela_id` explícito con la referencia).

### Y lo que ha cambiado en este turno, punto por punto de lo que se pidió

1. **D2: la prueba ya no se ata a la ortografía del SQL.** Antes exigía la cadena `'anulada = 0'`, que
   es la forma de SQLite, y por eso daba un aviso falso con el arreglo bueno puesto. Ahora
   `test_la_unicidad_de_la_clave_de_reenvio_lleva_su_condicion_en_los_dos_dialectos` comprueba **lo
   que hace** el índice: que sea `UNIQUE` (si no, no protege de nada) y que lleve **una condición
   `WHERE` que mencione la columna** de anulado, en los dos dialectos. El `= 0` de SQLite y el
   `= false` de PostgreSQL son la misma cosa dicha en el idioma de cada motor, y mañana podría
   escribirse `WHERE NOT anulada`, igual de buena.
2. **D3: el alcance, medido y escrito con esas palabras.** Está en §10: **el agricultor no está en
   ese caso** (sus tablas del almacén no existen todavía y nacen con el índice bueno), y **rehacer el
   índice no cambia ninguna fila** (con la huella de todas las filas de cinco tablas, antes y
   después). Las dos pruebas están en el fichero.
3. **D4: la prueba que enseña cuál es el recinto que se queda guardado**, con el `clave` exacto y los
   valores campo a campo en los dos órdenes, está en §2 (tabla de D8). Enseñó que ganaba **el primero
   que llegaba**, con el mismo `clave` en los dos casos, y sirvió para decidir el arreglo: hoy **no se
   guarda ninguno** cuando los dos renglones se contradicen, y sí se guarda uno cuando son el mismo
   apunte repetido. Yo no he tocado el código.
4. **La tabla de cierre** que se pidió —los defectos con su estado final y la prueba que demuestra
   cada uno— es **§10**.

---

## 8. Una nota de método, dicha porque pasó

Dos veces, editando mi propio fichero de pruebas, rompí los acentos con las herramientas de
PowerShell (la trampa de `AGENTS.md` §7): la primera con `Get-Content` + reescritura (216 líneas
doblemente codificadas) y la segunda, escribiendo a mano un comentario con la palabra «número» ya
doblemente codificada (la eñe y la u convertidas cada una en dos caracteres). Las dos las cazó
`tests/test_ficheros_de_texto.py`, que recorre `docs/` y `backend/` línea a línea, y las dos las
reparé con la vuelta exacta (`encode("cp1252").decode("utf-8")`, línea a línea, 0 sin poder
revertir). **Hoy quedan 0 líneas con los acentos rotos** en mis dos ficheros, y lo comprueba el
guardián del proyecto. Lo digo porque es exactamente el fallo que este proyecto ya había tenido tres
veces, y porque una revisión que rompe acentos mientras revisa no vale más que la que revisa.

---

## 9. Cómo se reproduce

```powershell
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests\test_revision_t05_y_t09.py -q -p no:randomly --junit-xml=$env:TEMP\rev.xml
```

**102 pruebas, 0 fallos**, y con las suites de las dos entregas y los guardianes dentro:
**1.113 pruebas, 0 fallos, 0 errores** (unos 40 segundos), comprobado dos veces seguidas.

```
Test5LaImportacionDeRecintosEsIdempotente::test_la_primera_importacion_del_lote_contradictorio_tampoco_depende_del_orden
```

Ninguna prueba toca la base del agricultor: `tests/conftest.py` fija `CUEDIGITAL_DATABASE_URL` y
`CUEDIGITAL_ADJUNTOS` a una carpeta temporal antes de importar nada de `app`, y las cuatro pruebas de
migración se montan su propio motor sobre un fichero de `tmp_path`. Las diecisiete pruebas del caso
de las nueve tierras montan una finca con la **forma** de la del agricultor (65 tierras, 52
referencias), no con sus datos.

---

## 10. Estado final de cada defecto, con la prueba que lo demuestra

Esta es la tabla que pidió el coordinador: **qué se cerró, qué no, y con qué prueba**. Los estados
están medidos contra el árbol de las 17:53, no deducidos de lo que digan los documentos. Los nombres
de las pruebas van por su clase del fichero (`Test1`… `Test14`), que es como se busca cada una.

| Defecto | Qué era | Estado final | Dónde se arregló (hora) | La prueba que lo demuestra |
|---|---|---|---|---|
| **D-A** | Reenviar el mismo albarán tras anularlo, con la misma `clave_de_reenvio`, daba **500** (`UNIQUE constraint failed`) y la cola del móvil lo reintentaba en bucle | **Arreglado** | `models.py` + `almacen_api.py` (17:07) | `Test2…::test_volver_a_apuntar_un_albaran_anulado_con_la_misma_clave_no_revienta` |
| **D-B** | Reenviar una **salida** anulada con la misma clave devolvía la anulada como si se hubiera apuntado: pérdida silenciosa | **Arreglado** | `almacen_api.py` + `models.py` (17:07) | `Test2…::test_una_salida_anulada_se_puede_volver_a_apuntar_con_la_misma_clave_de_reenvio` |
| **D-C** | Una factura enganchada a un albarán anulado no se podía enganchar a ningún otro (409 que cerraba la única salida que daba su propio mensaje) | **Arreglado** | `almacen_api.py` (17:08) | `Test2…::test_la_factura_de_un_albaran_anulado_se_puede_enganchar_al_bueno` |
| **D2** | El arreglo de D-A/D-B usaba solo `sqlite_where`: en PostgreSQL el índice nacía **único a secas** y el fallo volvía en producción | **Arreglado** | `models.py` (17:13): `postgresql_where=text("anulado = false")` en los dos índices | `Test2…::test_la_unicidad_de_la_clave_de_reenvio_lleva_su_condicion_en_los_dos_dialectos` |
| **D1** | Al anular el albarán, `comprado_sin_entrar` se quedaba mudo: parecía que el programa había perdido la compra | **Arreglado** | `servicios.py` (17:17) | `Test1…::test_lo_comprado_que_no_ha_entrado_no_se_pierde_al_anular_el_albaran` |
| **D5** | `estado_revision` volvía a `sin_revisar` sin decirlo (la marca de «revisado» del agricultor desaparecía) | **Arreglado** | `versiones_de_recinto.py` (17:20) | `Test8…::test_una_importacion_que_no_dice_el_estado_de_revision_no_lo_borra` |
| **D6** | Una tierra con la referencia escrita de otra manera no contaba como candidata (la puerta estrecha del fallo de las nueve tierras) | **Arreglado** | `versiones_de_recinto.py` (17:22) | `Test13…::test_una_tierra_con_la_referencia_escrita_de_otra_manera_no_cuenta_como_candidata` |
| **D-9** | La referencia **completa** que comparten hasta nueve tierras colgaba la versión de una de ellas, sin decir nada, la que saliera primero de la base | **Arreglado** | `versiones_de_recinto.py` (16:57 y 17:22) | `Test13…::test_la_referencia_que_comparten_nueve_tierras_no_se_le_cuelga_a_ninguna_en_silencio` y las cuatro puertas alternativas de §4 |
| **D4** | El mismo lote contradictorio, **en otro orden**, reescribía la versión guardada y dejaba un apunte de «actualizar» en la auditoría | **Arreglado** | `versiones_de_recinto.py` (17:38) | `Test5…::test_un_lote_contradictorio_en_otro_orden_no_puede_cambiar_lo_guardado` |
| **D7** | La `clave` que se guardaba y se devolvía perdía los ceros del agregado y de la zona: `37-70---507-24-1` en vez de `37-70-0-0-507-24-1` | **Arreglado** | `versiones_de_recinto.py` (17:38) | `Test14…::test_la_clave_de_un_recinto_con_agregado_cero_se_guarda_como_su_referencia` y `…::test_un_agregado_que_no_se_sabe_no_puede_dar_la_misma_clave_que_un_agregado_cero` |
| **D3** | `crear_tablas()` no recreaba los índices de una tabla que ya existía, así que una instalación que ya había arrancado se quedaba con el índice viejo | **Arreglado** | `database.py` (17:42): `asegurar_indices()`, que crea el que falta y **tira y vuelve a crear** el que cambió | `Test2…::test_una_instalacion_que_ya_tenia_la_tabla_no_recibe_el_arreglo_de_la_clave` y `…_de_la_salida` |
| **D8** | La primera importación de un lote contradictorio, en una finca nueva, decidía por el orden de los renglones (§2) | **Arreglado** | `versiones_de_recinto.py` (17:53), citando la revisión | `Test5…::test_la_primera_importacion_del_lote_contradictorio_tampoco_depende_del_orden` |

**Ninguno queda abierto.** Los trece tienen prueba y los trece pasan. Y dos de las pruebas que se
añadieron para medir el alcance de D3 y de D2 —la base nueva y el índice rehecho— siguen ahí para
proteger el arreglo, no solo para el informe:

**Dos cosas que hay que decir de D3, porque cambian si es grave o no** (las dos pedidas, las dos
medidas sobre bases **temporales**; la del agricultor no se abre):

1. **El agricultor no está en ese caso.** Su base tiene 26 tablas y `recepciones` y
   `movimientos_de_existencias` **no están entre ellas**: las seis tablas nuevas de T05 y T09 se crean
   al arrancar, y nacen con el índice bueno desde el primer día. Lo comprueba
   `Test2…::test_una_base_que_no_tenia_las_tablas_nace_con_el_indice_bueno` sobre una base temporal
   **vacía**. No es lo mismo «el agricultor se queda sin el arreglo» que «una instalación de prueba
   que ya había arrancado con la versión anterior se queda sin el arreglo»: **solo lo segundo era
   verdad**, y ya está arreglado de todas formas.
2. **Rehacer un índice no toca los datos.** Es el argumento que hacía falta para poder arreglarlo sin
   miedo: `Test2…::test_rehacer_el_indice_de_una_instalacion_vieja_no_cambia_ninguna_fila` monta una
   instalación vieja de verdad sobre una base temporal (índice único a secas, y dentro una finca, un
   artículo, un lote, **un albarán con su entrada y otro albarán anulado con su clave ocupada**),
   guarda la huella de **todas** las filas de cinco tablas, llama a `crear_tablas()` y comprueba que
   el índice queda con su condición **y que ni una fila cambia**. Tirar y volver a crear un índice no
   es una migración de datos, y esto lo demuestra en vez de afirmarlo.
