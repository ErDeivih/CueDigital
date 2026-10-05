# T14 — Maquinaria e inspecciones, separadas y con su fuente (S16)

> **Ticket:** T14 / E8 (dependencias T04 y T11, cerradas). **Fecha:** 05/10/2026.
> **Qué entrega, en una frase:** la pantalla `/maquinaria` (lista y ficha), con las **cinco obligaciones
> separadas** —ITV, ITEAF, mantenimiento, seguro y ROMA—, cada una con su aplicabilidad y su fuente, sus
> inspecciones con documento, sus averías y sus avisos al planificar un trabajo; y **sin calcular ni una
> fecha de plazo**: lo que el programa no sabe lo dice y lo pregunta.
>
> **Este informe se ha reescrito después de la revisión independiente** (`docs/REVISION_T14.md`, 14
> defectos). El apartado 8 dice, uno por uno, qué se hizo con cada uno. **Los 24 guardianes de la revisión
> están en verde.**

---

## 1. Lo que funciona (una línea por cosa)

### La trampa del ticket, que es lo que más importa

| Qué | Dónde |
|---|---|
| **No se deduce qué le toca a una máquina por su nombre ni por su clase.** La aplicabilidad de las cinco obligaciones la declara el agricultor, con tres estados (`sí`, `no` y «no lo sé»), y **sin declarar nada vale «no lo sé»** | `app/maquinaria.py`, `models.ObligacionDeMaquina.aplicabilidad` |
| **Se pide la clasificación técnica** (el contrato lo manda con esas palabras) y se guarda tal cual, en texto libre: la tabla oficial de clasificaciones por máquina no está transcrita (L07) y ofrecer una lista cerrada sería inventarse la regla | `models.Maquina.clasificacion_tecnica`, pantalla de la ficha |
| **La próxima fecha de una inspección es la que trae el papel**, copiada. La única aritmética con fechas es la resta `próxima − hoy` para decir «quedan N días», que no inventa ninguna fecha | `models.InspeccionDeMaquina.proxima_fecha`, `maquinaria.estado_de_una_obligacion` |
| **Cuando no se sabe, se dice y se pregunta**: «No se sabe si le toca», «No hay ninguna apuntada», «No se sabe cuándo toca la próxima», «Toca el X, pero no se sabe cuándo fue la última» + el aviso que pide mirar la clasificación en el papel | `textos.MAQUINARIA_DE_LA_FINCA`, ficha de una máquina |
| **Ningún valor por defecto permisivo**: `propiedad`, `disponibilidad` y `aplicabilidad` nacen en `no_se`; el **resultado** de una inspección nace en `no_consta` (que no es «favorable»); y las tres primeras se preguntan con botones y **no se pueden guardar sin contestar** | `models.py`, `schemas.MaquinaEntrada` |
| **Una fecha que ya pasó se dice que pasó, aunque falte por contestar si la obligación le toca**: la fecha es un hecho (la escribió el agricultor) y esconderlo le deja comparando de cabeza. Lo que no se dice es que le toque | `maquinaria.proxima_revision` (`vencidas`), aviso `M4` |

### La puerta de calidad del §9: `EquipoAplicacion` no es «la maquinaria»

| Qué | Dónde |
|---|---|
| **No se ha reutilizado `EquipoAplicacion` como el inventario.** Hay una tabla nueva (`maquinas`) que cubre aperos, remolques y cosechadora, y **`EquipoAplicacion` sigue siendo lo que era**: los equipos de echar producto de la hoja 1.3 del cuaderno | `models.Maquina`, cabecera del bloque en `models.py` |
| **Un tractor sin ROMA y sin ITEAF se apunta y el programa no le pide ninguno de los dos** (la prueba que el inventario del T01 pedía y no se podía escribir) | `test_t14_maquinaria.py::test_un_tractor_sin_roma_y_sin_iteaf_se_apunta_y_no_se_le_pide_ninguno` |
| **Lo que ya estaba apuntado no desaparece**: los equipos del cuaderno que no están en la lista se enseñan aparte, diciendo qué son y con el botón de traerlos | `GET /api/maquinaria` → `equipos_sin_ficha`, pantalla |
| **Traerlos no inventa nada**: se copia lo que el agricultor ya había escrito (nombre, ROMA, marca, serie) y sus fechas de inspección. **La clasificación técnica se queda vacía** y la disponibilidad en «no lo he mirado»; su titularidad solo se traduce cuando dice «propia» (en el cuaderno «ajena» no es «alquilada») | `POST /api/maquinaria/desde-equipo/<id>` |
| **Y si el cuaderno solo tenía la fecha de la próxima** (la hoja 1.3 las pregunta por separado), **esa fecha no se pierde**: se guarda con su obligación y la ficha dice que se sabe cuándo toca y no cuándo fue la última | `ObligacionDeMaquina.proxima_fecha_declarada`, situación `sin_la_ultima`, aviso `M20` |
| **Un equipo del cuaderno es UNA máquina, no dos**: el enlace es único por las tres puertas (traerlo, darlo de alta y corregirlo) y se contesta 409 diciendo cuál es ya | `_el_equipo_no_esta_enlazado` |
| **Lo que se apunta en la ficha nueva llega a la hoja 1.3 del cuaderno**: el nombre, el ROMA, la serie, la marca, el modelo y **las dos fechas de la ITEAF** (de la última inspección apuntada). Sin esto, el agricultor corregía el ROMA donde el programa le dice y **el cuaderno que se entrega a la Junta seguía con el número viejo** | `_llevar_al_cuaderno`, llamado desde el alta, la corrección, y al apuntar, corregir, anular o borrar una inspección |

### La pantalla y sus recorridos

| Qué | Dónde |
|---|---|
| **Lista** con las ocho columnas del contrato: máquina, tipo, matrícula o serie, propiedad o alquiler, horas, próxima revisión, papeles y disponibilidad; más buscador, orden por columna y pie con el total del conjunto | `#/maquinaria` |
| **Ficha** con los datos, las cinco obligaciones, las inspecciones, las averías y los avisos; se abre por su dirección (`#/maquinaria/<id>`) y se recarga entera | `#/maquinaria/<id>` |
| **Cada obligación enseña**: su nombre y qué es, la aplicabilidad con sus tres respuestas, **de dónde sale** lo declarado, la última inspección, el resultado, la próxima fecha (la del papel), el papel y **la fuente de la obligación** (la norma, con su enlace al BOE, o lo que falta) | ficha |
| **Una inspección sin documento se apunta y se dice que no lo trae**; y con documento, **se dice cuál es y se puede abrir** (`VER EL PAPEL`) | `POST .../inspecciones`, ficha |
| **El aviso de los tres años, que es una obligación de la ley**: «los registros y documentos se conservarán al menos durante los 3 años siguientes» (artículo 16.3 del RD 1311/2012) | ficha, junto a las inspecciones |
| **Avisos al planificar un trabajo** (endpoint con la fecha del trabajo) y **en el paso del asistente donde se elige la máquina**: «no puedes contar con ella», «la ITV venció el…», «está al caer» | `GET /api/maquinaria/avisos`, `app.js` → `avisoDeLaMaquinaDeUnEquipo` |
| **Registro de averías** con qué pasó, cuándo, si está arreglada y las horas del cuenta-horas; la avería **no cambia sola la disponibilidad** | `POST .../averias` |
| **La ITV y la ITEAF no se confunden**: cada una con su nombre y su explicación («La inspección técnica del vehículo…» / «La inspección de las máquinas con las que se echa el producto. **No es la ITV.**»), y las dos fuentes son normas distintas | `textos.MAQUINARIA_DE_LA_FINCA`, `maquinaria.FUENTE_DE_LA_OBLIGACION` |
| **Corregir, anular y reenviar sin duplicar**: corregir en la misma fila con rastro en la auditoría, anular con motivo (y lo anulado **deja de contar** para la última inspección), borrar con rastro (también el de las obligaciones al quitar una máquina), y `clave_de_reenvio` **por máquina** para que el móvil que reintenta no apunte dos veces | router, `TestCorregirAnularYReenviar`, `TestReenviarSinDuplicar` (revisión) |
| **Aislamiento entre fincas con 404, no 403**, en todas las puertas: máquina, inspecciones, averías, obligaciones y el papel que se enlaza | `TestAislamientoEntreFincas`, `test_cada_puerta_de_la_maquinaria_comprueba_que_el_objeto_es_de_esta_finca` (revisión: recorre las rutas del router) |
| **Lo que el programa no sabe calcular se declara** en la pantalla: los plazos por clasificación técnica (L07), con lo que es, para qué haría falta y de quién depende | `maquinaria.QUE_FALTA`, `/api/interfaz` |

---

## 2. Cómo se ha comprobado (los comandos y los números)

```powershell
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests -q --junit-xml=$env:TEMP\t14.xml
node --test "tests_js/*.test.js"
```

| | Medido (05/10/2026) |
|---|---|
| Python | **3.960 pruebas**, 1 en rojo (§5: es el recuento de la documentación, que alineo yo) |
| JavaScript | **896 pruebas, 0 en rojo** |
| Antes de este ticket | 3.818 de Python y 874 de JavaScript |
| Los 24 guardianes de la revisión (`tests/test_revision_t14.py`) | **24 en verde** |
| Los 58 del ticket (`tests/test_t14_maquinaria.py`) | **58 en verde** |

Las pruebas nuevas del ticket son `backend/tests/test_t14_maquinaria.py` (58) y
`backend/tests_js/maquinaria.test.js` (20), más dos de recorrido dentro de `tests_js/interfaz.test.js`
(el aviso al elegir la máquina de un trabajo y que **elegir una opción no borre lo escrito** en el
formulario). Las 10 pruebas de más de `test_ficheros_de_texto.py` no son pruebas escritas a mano: ese
fichero revisa **todos** los ficheros de texto del proyecto y hay 10 ficheros nuevos (los míos y los dos
guiones).

### El recorrido, contra un servidor aislado

```powershell
# servidor de usar y tirar, en un puerto libre (el 8000 es el de David), con su base temporal
$env:CUEDIGITAL_DATABASE_URL="sqlite:///C:/Users/David/AppData/Local/Temp/t14_humo/humo.db"
$env:CUEDIGITAL_SECRETO="secreto-solo-para-el-humo-t14"
$env:CUEDIGITAL_ADJUNTOS=".../t14_humo/adjuntos"
$env:CUEDIGITAL_CONFIAR_EN_CABECERAS="1"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8477
```

**Antes de arrancar se comprueba el motor** (`engine.dialect.name == "sqlite"` y que la dirección sea la
base temporal: la de por defecto es una **ruta relativa** y un guion lanzado desde `backend/` escribiría
en el cuaderno de verdad). La base del agricultor está intacta.

| Guion | Resultado (05/10/2026, con el código final) |
|---|---|
| `scripts/humo.py http://127.0.0.1:8477` (**sin editarlo**) | `RESULTADO: todo correcto` |
| `scripts/comprobar_en_un_navegador.py http://127.0.0.1:8477` (**sin editarlo**) | `RESULTADO: la interfaz se abre y se dibuja en un navegador de verdad` (todas sus pantallas, a 390/1024/1440, sin salirse de lo ancho) |
| Mis pantallas a 390, 1024 y 1440 px | `RESULTADO: todo correcto` — ver abajo |

**Los tres casos del ticket, medidos en un navegador de verdad** con las funciones del guion del
coordinador (**no se ha editado**: `pagina_de_pantalla` para el contenido y `pagina_estrecha`, la del
hueco, para el ancho), desde un guion mío en la carpeta temporal:

| Qué se midió | Resultado |
|---|---|
| `#/maquinaria` y `#/maquinaria/<id>` se dibujan **por su dirección** (enlace directo) | OK, las tres pantallas |
| Ancho de la página dentro de un hueco **de verdad** de 390, 1024 y 1440 px | 375 en 390 · 1009 en 1024 · 1425 en 1440 — **no se sale** en ninguna |
| Que no sea una pantalla en blanco (cuerpo montado) | 12.860 a 24.056 caracteres |
| Capturas | `%TEMP%\t14-la-lista-de-maquinaria-*.png`, `t14-la-ficha-del-tractor-*.png`, `t14-ficha-entera.png` (la ficha entera de arriba abajo, que es la que se miró a ojo) |

> **Y dos defectos que encontró esta medición, que es justo para lo que está.** La lista se salía de lo
> ancho a 1024 y 1440 px (**1.621 px** dentro de un hueco de 1.024) y la ficha a los tres anchos (1.287 en
> 390). Las dos causas, arregladas: la tabla **no iba dentro de `.tabla-scroll`** (el contenedor que se
> desplaza solo él, como en las demás tablas) y las obligaciones de la ficha usaban la clase de las
> **tarjetas** (`display: flex`, que no parte), con siete botones dentro. Ahora van como renglones de lista
> y la tabla lleva su contenedor: medido de nuevo, no se sale en ninguno de los tres anchos.

### Las pruebas que este ticket tenía que escribir (y están escritas)

| Caso | Prueba |
|---|---|
| Una máquina **sin clasificación técnica no inventa su plazo**: lo pide y no enseña ninguna fecha | `test_una_obligacion_que_aplica_y_sin_inspeccion_pide_el_dato_y_no_ensena_fecha`, `test_sin_clasificacion_tecnica_la_ficha_lo_pide_y_no_ensena_ninguna_fecha_inventada` |
| **Una inspección sin documento se apunta y se dice que no lo trae** | `test_se_apunta_sin_papel_y_la_respuesta_lo_dice`, `test_una_inspeccion_sin_papel_se_ensena_y_dice_que_no_lo_trae` |
| **Una inspección vencida se ve al planificar un trabajo** | `test_una_inspeccion_vencida_sale_en_los_avisos_de_planificar`, `test_al_elegir_la_maquina_de_un_trabajo_se_avisa_de_lo_que_hay_que_mirar` (recorrido del asistente) |
| La ficha **distingue las cinco obligaciones** | `test_la_ficha_enseña_las_cinco_obligaciones_separadas`, `test_la_ficha_trae_las_cinco_en_su_orden_y_con_su_nombre` |
| **Aislamiento entre fincas (404, no 403)** | `TestAislamientoEntreFincas` (5 pruebas) |
| **Corrección, anulación y reenvío sin duplicar** | `TestCorregirAnularYReenviar` (11 pruebas) |
| **Nada por defecto convierte «no se sabe» en «cumple»** | `test_una_maquina_nueva_no_tiene_ninguna_obligacion_dada_por_buena`, `test_los_valores_por_defecto_del_modelo_no_son_permisivos`, `test_la_clase_y_la_propiedad_y_la_disponibilidad_hay_que_decirlas` |

---

## 3. Lo que NO he podido comprobar (dicho por mí, antes de que se pregunte)

1. **PostgreSQL no se ha podido usar en esta sesión: el motor de contenedores se quedó colgado.** La base
   se creó bien (`docker exec cuedigital-pg createdb -U postgres cuedigital_maquinaria`, y aparece en la
   lista), y la pasada entera llegó a arrancar, pero **no terminó**; después, `docker ps` y
   `docker exec … psql` **se quedan colgados** (timeout de 30 s sin respuesta), así que no es un problema
   del programa: es el motor. **Aviso para el coordinador: esto mismo puede estar afectando a su pasada
   sobre `cuedigital_pruebas`.** No he reiniciado Docker por mi cuenta: es una acción visible y suya.
   - **Lo que sí está comprobado sin el servidor**: `test_arranque_en_postgresql.py` (verde) usa un motor
     con **dialecto real de PostgreSQL** y comprueba que los índices nuevos del modelo se crean; y las
     columnas de texto nuevas llevan su tope declarado en el modelo, con la comprobación de esquema que lo
     lee (`_cabe_en_la_columna`) y la comprobación previa al `INSERT` de `database.py`, que **saca las
     tablas del modelo** y por eso cubre las nuevas sola.
   - **Lo que queda sin medir en PostgreSQL**: las longitudes de las columnas nuevas con datos de verdad
     (el defecto del `varchar(30)` que ya mordió una vez).
   - **Y una advertencia técnica, para cuando se pueda**: la columna `inspecciones_de_maquina.fecha` sigue
     siendo obligatoria, así que no hay ninguna reconstrucción de tabla pendiente; la única columna nueva
     sobre una tabla existente es `obligaciones_de_maquina.proxima_fecha_declarada`, **anulable**, que se
     añade sola con `ALTER TABLE … ADD COLUMN` (no pasa por la reconstrucción de SQLite).
2. **El guion del navegador del coordinador NO cubre mis pantallas.** Tiene su lista escrita a mano y es
   suyo: **se pasa, no se edita**. Mis pantallas las he medido con **sus funciones** desde un guion mío en
   la carpeta temporal (§2). **Petición concreta**, lista para pegar:
   - en `pantallas_estrechas`: `("la lista de maquinaria", "#/maquinaria", (390, 1024, 1440))` y
     `("la ficha de una máquina", f"#/maquinaria/{identificador}", (390, 1024, 1440))`, con el
     identificador pedido al servidor como ya se hace con `la_primera_tierra`;
   - en `PANTALLAS`: `("la maquinaria", ['[data-accion="maquinaria-ver"]'], ["Mi maquinaria", "Próxima revisión", "Vencida"])`.
3. **Nada de esto está probado con un agricultor delante.** Que las cinco obligaciones se entiendan, que
   «1 aviso» en una celda se lea bien en el móvil al sol y que el agricultor sepa qué hacer con «Falta la
   clasificación técnica» **no lo dice ninguna prueba**: hace falta la prueba con personas.
4. **Las capturas son de un navegador sin ventana.** Las he mirado (la ficha entera, la lista a 390, 1024 y
   1440), pero no sustituyen a mirarlo en el móvil de David.
5. **El programa no valida la clasificación técnica** que se guarda: la copia del papel tal cual, porque la
   tabla oficial por clasificación sigue sin transcribir (L07). Es deliberado —es el corazón del ticket—
   pero conviene decirlo: **no se compara con nada, porque no hay con qué**.
6. **La descarga del papel desde la ficha** (`VER EL PAPEL`) usa el mismo camino que la pantalla de los
   papeles (`GET /api/documentos/<id>/fichero` con el vale), y **eso sí está probado en Python**; lo que no
   he probado en un navegador de verdad es la descarga en sí (el guion del coordinador no llega a mis
   pantallas). Si el fichero no está subido, el servidor contesta y la pantalla lo dice.

---

## 4. Los recuentos

| Medida | Antes del ticket | Ahora (05/10/2026, medido) |
|---|---|---|
| Pruebas de Python | 3.818 | **3.960** |
| Pruebas de JavaScript | 874 | **896** |

**La única prueba en rojo es `test_lista_de_la_junta.py`, y es el recuento de la documentación**: los tres
documentos dicen **3.958** de Python y 896 de JavaScript, y hay **3.960**. Los dos de más son un **fichero
de texto** que la documentación no contaba cuando se contó: `scripts/copiar_textos_t14.py`, que
`test_ficheros_de_texto.py` cuenta **dos veces** (tiene dos pruebas parametrizadas sobre la misma lista de
ficheros). El número de JavaScript (896) ya está bien.

**Dos salidas, y elige tú** (las dos de un minuto):

1. **Alinear los tres documentos a 3.960** (el número medido): `README.md` `# 3958 tests` →
   `# 3960 tests`; `AGENTS.md` `# Python (3958 tests)` → `# Python (3960 tests)`;
   `docs/LO_QUE_PIDE_LA_JUNTA.md` `tenía 3958 tests de Python` → `tenía 3960 tests de Python`.
2. **Borrar `scripts/copiar_textos_t14.py`** y dejar los documentos como están: volvería a 3.958 y la
   suite quedaría entera en verde. **Lo dejo en tus manos porque el guion lo escribí yo** (§5 cuenta para
   qué sirve y por qué creo que no es lo mismo que el de los acentos, que ya está borrado).

Los números son **medidos**: `pytest` los cuenta al recoger (el XML de la última pasada dice
`tests="3960" failures="1"`), y los de JavaScript con la misma expresión que usa el guardián
(`^test(` en `tests_js/*.test.js`). **Y ojo con atribuir la diferencia**: entre mi primera medida y la
última, el árbol ha crecido también por la revisión (su `tests/test_revision_t14.py`, con 24 pruebas, y su
documento, que también es un fichero de texto revisado), así que el total no es «lo mío» más lo de antes.

---

## 5. Ficheros

### Nuevos

| Fichero | Qué es |
|---|---|
| `backend/app/maquinaria.py` | La lógica pura: las cinco obligaciones, sus estados, los avisos, lo que falta y **el porqué escrito de que no se calcule ninguna fecha** |
| `backend/app/routers/maquinaria_api.py` | El router: lista, ficha, obligaciones, inspecciones, averías, el aviso al planificar y **el enlace con el cuaderno** (`_llevar_al_cuaderno`) |
| `backend/web/react/pantallas/maquinaria.js` | La lista y la ficha, en React (un fichero, dos pantallas) |
| `backend/tests/test_t14_maquinaria.py` | 58 pruebas |
| `backend/tests_js/maquinaria.test.js` | 20 pruebas del componente, con la **copia literal** de los textos |
| `backend/scripts/copiar_textos_t14.py` | Copia los textos de la maquinaria del servidor a la copia del test del móvil, para que no vuelvan a quedarse viejos (35 de 172 lo estaban). Es una **copia derivada con guardián permanente**, no una herramienta de un incidente (ver §4) |
| `docs/T14_MAQUINARIA.md` | Este informe |

### Tocados

| Fichero | Qué se hizo |
|---|---|
| `backend/app/models.py` | Cuatro tablas nuevas (`Maquina`, `ObligacionDeMaquina`, `InspeccionDeMaquina`, `AveriaDeMaquina`) y la columna `ObligacionDeMaquina.proxima_fecha_declarada`, con el porqué de cada cosa |
| `backend/app/schemas.py` | Los esquemas de entrada y salida (y `trae_papel` en la salida, que dice en el dato que una inspección no trae papel) |
| `backend/app/textos.py` | Los textos de la pantalla, los mensajes `M1`–`M20`, las ocho columnas de la tabla y el bloque de **recuentos**. Además: **`TABLA` entra en `textos_visibles()`**, que era el único diccionario de textos de pantalla que se quedaba fuera del test de jerga |
| `backend/app/routers/interfaz.py` | Los textos de la maquinaria, sus listas cerradas y `maquinaria_que_falta` |
| `backend/app/routers/maestros.py` | **Dos líneas**: borrar un equipo del cuaderno cuenta también si la maquinaria lo tiene enlazado (si no, la fila quedaría apuntando a algo que ya no está y el ROMA desaparecería de la hoja 1.3) |
| `backend/app/main.py` | El router nuevo |
| `backend/web/app.js` | Las dos pantallas, sus datos preparados, sus acciones, el aviso en el paso de la máquina del asistente, `#/maquinaria` en el menú y en el enrutador, y **la llamada a los avisos al arrancar** (una más: es lo que permite avisar en el asistente) |
| `backend/web/react/rutas.js` | Las dos direcciones (`#/maquinaria`, `#/maquinaria/<id>`) |
| `backend/web/service-worker.js` | `maquinaria.js` en la caché del campo y **la caché a la versión 68** |
| `docs/REACT.md` | La fila de la tabla de pantallas y el párrafo del T14 (con lo que esta pantalla **no** hace) |
| `backend/tests/test_los_botones_hacen_algo.py` | `maquinaria.js` en la lista de ficheros que pintan acciones por variable, con su motivo |
| `backend/tests/test_los_papeles_y_las_facturas_se_pueden_corregir.py` | **La prueba que había que decidir**: `tablas_que_apuntan_a("documento_id")` ya no está vacía (una inspección apunta a su papel). Decisión: **cuenta como dependencia** (409 antes que dejar el cuaderno apuntando a un papel que no está), y su comentario lo explica |
| `backend/tests_js/interfaz.test.js` | El renglón de la maquinaria en el menú, la copia de los textos de su tabla y **dos pruebas de recorrido nuevas** |
| `backend/tests_js/rutas.test.js` | Las dos direcciones nuevas en la tabla y en el mapa de identificadores |

### Compartidos (que conviene mirar en la revisión)

- **`backend/app/textos.py`**: el fichero más compartido del proyecto. He tocado el bloque de recuentos, la
  tabla, la maquinaria y los mensajes. **No he cambiado ningún texto existente** salvo dos cosas, dichas:
  la columna `matricula_o_serie` («Matrícula o nº de serie» → «Matrícula o serie», porque con nueve
  columnas esa cabecera sacaba de la pantalla los botones de la fila, medido) y **el mensaje `M15`**, que
  ahora nombra la máquina porque lo usan las tres puertas del enlace con el equipo del cuaderno.
  Y `M19` para quitar una máquina con cosas dentro.
- **`backend/tests_js/interfaz.test.js`**: 13.000 líneas compartidas con los demás tickets. He añadido dos
  pruebas y tres entradas de textos; **no he tocado ninguna prueba existente**.
- **`docs/REACT.md`**: la tabla de pantallas migradas (una fila más) y un párrafo del T14.

---

## 6. Un accidente que hay que contar: `app.js` y los acentos

**Lo escribo porque es exactamente el defecto del que `AGENTS.md` (§7, «Trampas del entorno») avisa, y lo
cometí.** Esta sección es todo lo que queda del incidente: el guion de un solo uso que escribí para
repararlo **se ha borrado** (en `scripts/` viven los guiones del programa, no las herramientas de un
accidente), así que la receta útil es esta, escrita.

**Qué comando lo destrozó, y sobre qué fichero**

```powershell
# lo que hice, y lo que NO hay que hacer nunca
$t = Get-Content web\app.js -Raw
$t = $t.Replace('suyo.formulario = formularioDeLaMaquina({ corrigiendo: false });', 'suyo.formulario = { … };')
# …seis reemplazos iguales…
Set-Content -Path "$env:TEMP\app_nuevo.js" -Value $t -Encoding utf8
Copy-Item "$env:TEMP\app_nuevo.js" web\app.js -Force
```

- **Fichero:** `backend/web/app.js` (18.715 líneas cuando pasó, el más grande del proyecto).
- **Qué le pasó:** el fichero se leyó con la página de códigos del sistema y se reescribió en UTF-8, así que
  **cada carácter acentuado se dobló** («ó» → «Ã³», «í» → «Ã­», ««» → «Â«Â»»): **2.839 líneas de 18.715**
  quedaron con doble codificación, se le puso la **marca de orden de bytes** (239 187 191) y el final del
  fichero pasó de `arrancar();\n` a `arrancar();\n\r\n`.
- **Cuánto texto se dobló, con la cuenta hecha:** el fichero pasó de **816.701** bytes (después de repararlo
  y de quitarle el `\r\n` que añadió PowerShell) a **831.085** bytes cuando estaba destrozado, o sea
  **14.384 bytes de más**: 3 de la marca de orden de bytes, 1 del `\r` del final y **14.380 que son
  7.190 caracteres acentuados doblados** (cada uno pasa de 2 bytes a 4: `ó` = C3 B3 → `Ã` + `³`).
  **Hoy el fichero mide 823.771 bytes**, y esa diferencia con los 816.701 ya no es del accidente: es el
  trabajo del ticket y de la revisión, hecho después con las herramientas de edición.
- **Cómo se detectó:** mirando los bytes del fichero (la marca de orden de bytes) y buscando
  «clasificación técnica» dentro (ya no estaba). **No lo cazó ningún test**, porque no se llegó a ejecutar
  ninguno: `test_ficheros_de_texto.py` es el que lo habría dicho con nombre y apellidos.

**Cómo se reparó** (el procedimiento que `AGENTS.md` deja escrito, aplicado tal cual)

1. La vuelta atrás es `texto.encode("cp1252").decode("utf-8")`, **línea a línea** (no del fichero entero:
   el viaje redondo de un fichero a medias revienta por las líneas que sí están bien y no arregla nada), y
   **las líneas que no se pueden deshacer se dejan tal cual**.
2. **La primera pasada dejó 14 líneas sin reparar** (16 contando las dos del final del fichero), y ahí está
   lo que hubo que descubrir: Python sabe *leer* los cinco bytes que cp1252 no define (0x81, 0x8D, 0x8F,
   0x90 y 0x9D) y los deja como caracteres de control, pero **no sabe volver a escribirlos**
   (`"\x81".encode("cp1252")` levanta `UnicodeEncodeError`), y justo esos cinco bytes son la segunda mitad
   de las **mayúsculas acentuadas** («MÁQUINAS»: C3 81) y de media docena de emojis de la interfaz. La
   segunda pasada tradujo esos cinco caracteres a su byte antes de decodificar, y las 14 quedaron reparadas.
   **Esto vale para el próximo que lo sufra, y por eso está escrito aquí y no en un guion que se ha
   borrado.**
3. El `\r\n` que PowerShell añadió al final se quitó después, comparando los últimos bytes a mano.

**Cómo se comprobó que quedó bien** (todo ello ejecutado de nuevo por el coordinador, con el mismo
resultado):

| Comprobación | Resultado |
|---|---|
| Marca de orden de bytes | **0** (el fichero empieza por `/*`, no por EF BB BF) |
| Rastros de doble codificación (`Ã`, `Â`, `â€`, `ð`, `Ÿ`) | **0 ocurrencias** de cada uno |
| `CR` sueltos / `CRLF` | **0** |
| «clasificación técnica» y las frases acentuadas | Están (se buscaron después de reparar) |
| `node --check web/app.js` | **OK** |
| `tests/test_ficheros_de_texto.py` (revisa la **doble codificación línea a línea**) | **verde** (905 pruebas, 0 fallos en esa familia) |
| **Las 896 pruebas de JavaScript** | **verdes**, y son las que comparan los textos de `app.js` con los del servidor **palabra por palabra** (una frase perdida o cambiada las pone rojas) |
| El guardián de botones (`test_los_botones_hacen_algo.py`) | **verde**: exige que **cada** `accion="…"` pintada tenga su rama `nombre === "…"` en `app.js`; si la reparación se hubiera comido un trozo de código, los pares dejarían de cuadrar |
| El recorrido completo en un navegador de verdad (`comprobar_en_un_navegador.py`) | **«la interfaz se abre y se dibuja»**: todas sus pantallas se dibujan, sin errores de JavaScript |
| Mis tres pantallas, medidas a 390/1024/1440 | **todo correcto** (contenido y ancho) |

**Y lo que NO se puede demostrar, dicho:** **este repositorio no tiene control de versiones** (no hay
`.git`), así que **no hay un original con el que comparar byte a byte**. La reparación es la inversa exacta
de la transformación que se aplicó (una ida y vuelta de codificación es biyectiva **en las líneas que se
pudieron deshacer**, y las que no se pudieron se dejaron intactas), y lo que la acredita es el
comportamiento: los textos, los botones, el dibujado y las tres pantallas. Lo único que se me ocurre que
podría haberse perdido sin que ninguna de esas pruebas lo note es una frase que se hubiera reparado a algo
**también válido en UTF-8 pero distinto del original** — por eso la segunda pasada se limitó a las líneas
con rastro de doblado, y no se tocó ninguna otra. Si al cerrar el recorrido o el navegador te sale algo
raro en una pantalla que no sea mía, sospecha de aquí primero: es el único sitio donde podría estar.

---

## 7. La revisión independiente: los 14 defectos, uno por uno

`docs/REVISION_T14.md` (05/10/2026) dice, de sus 14 defectos: *«se puede dar por bueno el modelo y las
reglas —que es lo difícil de este ticket— pero no el ticket tal y como está, porque lo que se ve y lo que
se pulsa no funciona»*. Tenía razón: el modelo estaba bien y la pantalla tenía tres defectos graves. Esto
es lo que se hizo con cada uno:

| # | Gravedad | Estado |
|---|---|---|
| 1 | GRAVE | **Arreglado.** «APUNTAR UNA INSPECCIÓN» reventaba (`(estado.documentos \|\| []).map`): `estado.documentos` es la **respuesta entera** de `GET /api/documentos`, no la lista. Ahora se lee `.documentos` (`papelesParaElegir`, con su comentario) |
| 2 | GRAVE | **Arreglado.** «undefined: ITV el 12/05/2026» en la tarjeta del móvil: los dos rótulos se sacan de `textos.TABLA` (`col("proxima_revision")`, `col("documentacion")`), y la revisión lo comprueba |
| 3 | GRAVE | **Arreglado.** Corregir una máquina no se guardaba: clase, propiedad y disponibilidad se exigen al dar de alta y **se conservan al corregir** (lo resolvió el coordinador durante la revisión, y su prueba lo exige) |
| 4 | Medio | **Arreglado ahora.** Lo apuntado en la ficha nueva no llegaba a la hoja 1.3: `_llevar_al_cuaderno` copia identidad y fechas de la ITEAF al equipo del cuaderno, y se llama desde las seis puertas (alta, corrección, apuntar, corregir, anular y borrar una inspección) |
| 5 | Medio | **Arreglado** (con el coordinador). La pantalla no mandaba `clave_de_reenvio`: ahora el formulario la manda y hay una prueba de que **dos envíos del mismo apunte son uno** |
| 6 | Medio | **Arreglado** (con el coordinador). El reenvío se cierra **por máquina**: la misma clave en otra máquina ya no contesta la inspección de la primera |
| 7 | Medio | **Arreglado ahora.** La copia de los textos del test del móvil decía otra cosa en 35 de 172: ahora es **literal** y la genera `scripts/copiar_textos_t14.py` desde el diccionario de verdad. El guardián que lo comprueba es de la revisión y está en verde |
| 8 | Medio-bajo | **Arreglado ahora.** Quitar una máquina borraba sus obligaciones sin rastro: ahora se borran una a una con `correcciones.borrar` (rastro en la auditoría), y de paso eso fija el orden del borrado |
| 9 | Medio-bajo | **Arreglado ahora.** Una fecha ya pasada sin obligación declarada: la tabla cuenta `vencidas` y la celda lleva la palabra **«Vencida»** (la situación de la fecha manda para la tabla), y sale el aviso `M4`. La ficha sigue diciendo las dos cosas: que no se sabe si le toca **y** que la fecha pasó |
| 10 | Bajo | **Arreglado ahora.** Traer un equipo con próxima ITEAF y sin última: la fecha **no se pierde**, se guarda en la obligación (`proxima_fecha_declarada`) y la ficha dice «Toca el 01/03/2029, pero no se sabe cuándo fue la última» (aviso `M20`) |
| 11 | Bajo | **Arreglado ahora.** Dos máquinas con el mismo equipo del cuaderno: se comprueba en el alta y en la corrección (409 nombrando la máquina que ya lo tiene), con `permitido` para que guardar sin tocar el enlace no se estorbe a sí misma |
| 12 | Bajo | **Arreglado ahora.** Los diez textos que no se enseñaban: se borraron los ocho que eran restos de versiones anteriores y **se enseñan los dos que importan** —`guarda_el_papel`, que es el único texto del proyecto que dice que los papeles de las inspecciones hay que poder enseñarlos **tres años** (artículo 16.3 del RD 1311/2012), y su rótulo— debajo de las inspecciones de la ficha |
| 13 | Bajo | **Cubierto por los guardianes de la revisión** (`TestNoSeCalculaNingunaFecha`), que miran **tres ficheros**: el módulo, el router y la pantalla, y los tres están en verde. El guardián del ticket (`timedelta` en `app/maquinaria.py`) se queda como la primera línea, pero **el que cierra el agujero es el de la revisión** |
| 14 | Bajo | **Arreglado ahora.** El papel no se decía cuál era ni se podía abrir: la ficha escribe el **nombre** del papel y lleva `VER EL PAPEL` (`accion="papel-ver"`, la misma que usa la pantalla de los papeles), en la obligación y en cada inspección |

Los tres que la revisión «rompió a propósito» (§3 de su documento) siguen cazados: un valor por defecto
permisivo en el modelo y una obligación sin fila leída como «no le toca» los caza el ticket; el cálculo de
fecha escondido en el router lo caza ahora el guardián de la revisión.

---

## 8. Lo que queda pendiente o a medias (dicho sin adornos)

1. **Los plazos de las inspecciones no se calculan, y no es un olvido: es el ticket.** Está declarado en la
   pantalla y en `maquinaria.QUE_FALTA` (trabajo legal **L07**: «clasificación ITV/ITEAF por máquina real»).
   El día que se transcriba, con su fuente y su versión, hay que **ampliar los guardianes de las fechas**
   (el del módulo y el de la revisión) explicando la fuente.
2. **El coste de las averías y del mantenimiento no se apunta.** La avería guarda qué pasó, cuándo, si está
   arreglada y las horas, **no lo que costó**: el dinero es del T13 (gastos y repartos) y una columna de
   importe suelta aquí sería un número sin proveedor, sin factura y sin reparto a la tierra. El plan del
   proyecto lo pone en `Mantenimiento`, con proveedor y coste documentado.
3. **No hay `Mantenimiento` como tabla**: el mantenimiento existe como obligación (con su fecha y su papel)
   y como inspección apuntada. Un servicio con proveedor, horas y coste necesitaría su propia tabla.
4. **El tipo de papel «inspección» no existe en `catalogos.TIPOS_DOCUMENTO`** (hay contrato, factura,
   albarán de Sigfito y otros). El contrato del CRM lo pide en la bandeja documental (S10, del T08) y el
   certificado de una inspección es justo el papel que este ticket enlaza. Hoy se enlaza como «otros» y el
   enlace funciona; **queda apuntado para el T08** en vez de tocar su catálogo.
5. **No hay panel de detalle al lado de la tabla.** Las otras tablas lo tienen; aquí la fila lleva su botón
   VER y abre la ficha entera. Con cinco obligaciones, una inspección con su papel y una avería, el panel se
   quedaba en un resumen que no dice nada. Es trabajo de una ronda, y hay que decidir qué se enseña en él.
6. **La exportación a papel y a CSV sigue enseñando los equipos del cuaderno**, no la lista nueva
   (`routers/cuaderno.py`). Es deliberado: la hoja 1.3 pide **los equipos de echar producto**, y ahí no
   pintan un remolque ni la cosechadora. **Falta decidir** si el cuaderno propio debe llevar además un
   listado de maquinaria con sus inspecciones.
7. **`test_arranque_en_postgresql.py` no se salta**, aunque algún informe diga que sí: usa un motor con
   dialecto real de PostgreSQL. Lo digo porque lo leí en un comentario de otro ticket y no es verdad.
8. **La pasada en PostgreSQL sigue pendiente del motor de contenedores** (§3.1). Es lo único que este
   ticket no ha podido medir donde el proyecto dice que se mide de verdad.
