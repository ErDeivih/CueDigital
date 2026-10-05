# Revisión independiente de T06 — el mapa, las tierras y la ficha de versiones

> **Qué es esto.** La revisión de la entrega **T06** (la vista de las tierras con su mapa, la ficha de
> versiones de una tierra y la función nueva `database.asegurar_indices`). No es un resumen del
> documento: es un intento de **demostrar que está mal**, contrato por contrato, provocándolo con el
> cliente de pruebas de FastAPI sobre bases temporales y leyendo el JavaScript que de verdad corre.
>
> **Lo que NO se ha hecho.** No se ha abierto `backend/cuedigital.db` para escribir (para leerlo se ha
> copiado a una carpeta temporal **con la huella comprobada**, y la copia se ha borrado al terminar:
> §3.1). No se ha modificado **ningún** fichero que ya existía. Todo lo que se ha escrito son dos
> ficheros nuevos: este informe y `backend/tests/test_revision_t06.py` (**42 pruebas**).
>
> **Aviso para leer lo de abajo: el árbol se movió mientras se revisaba, y se movió por esta revisión.**
> Entre las 18:15 y las 18:45 del 02/10/2026 los ficheros de T06 cambiaron **una veintena de veces** y,
> de los nueve defectos que encontró este trabajo, **los nueve están arreglados** al cerrar (ocho de
> ellos citan «la revisión de T06» con su número en el código; ver §2). Eso significa dos cosas:
> **los fallos de una ejecución son de la versión del fichero de ese momento**, y las líneas que se
> citan conviene buscarlas **por el texto y no por el número**.

---

## 0. Resultado, en cuatro líneas

**42 pruebas nuevas. 0 fallos al cerrar (a las 18:42:52). 9 defectos encontrados, 9 arreglados durante
la revisión** —uno de ellos, el de la caja del mapa, lo destapó *mi* prueba del contrato 2 como
consecuencia del arreglo de otro—. Ninguno de los nueve está abierto hoy, y cada uno tiene su prueba
dentro para que no vuelva. Lo que sigue **sin resolver** son **cinco afirmaciones del documento y del
código que no son verdad**, medidas en §4, y el estado de la suite (§3.3: **3527 pruebas y 6 fallos,
ninguno de este ticket y ninguno mío**).

```powershell
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests\test_revision_t06.py -q --junit-xml=$env:TEMP\rev6.xml
# Leer el XML: la consola no imprime el resumen.
```

### Contra qué estado está hecha (el árbol se movió **una veintena de veces** durante la revisión)

Última escritura y SHA-256 (16 primeros) en el momento de cerrar, **02/10/2026 18:46**:

| Fichero | Última escritura | SHA-256 (16) |
|---|---|---|
| `backend/app/routers/parcelas.py` | 02/10 18:37:39 | `67BFBDBD5ABF2BB3` |
| `backend/app/routers/mapa.py` | 02/10 16:58:42 | `C10E6A29A7E939B6` |
| `backend/app/schemas.py` | 02/10 18:37:35 | `58FC56DDCB972403` |
| `backend/app/textos.py` | 02/10 18:39:41 | `7B9BC049F98E4902` |
| `backend/app/database.py` | 02/10 18:36:11 | `BAF54122E7F48D38` |
| `backend/web/app.js` | 02/10 18:41:37 | `11D0022F209CD9E8` |
| `backend/web/react/pantallas/tierras_mapa.js` | 02/10 18:38:51 | `8F51EAC50A36D455` |
| `backend/web/react/pantallas/tierra_versiones.js` | 02/10 17:16:05 | `983675AF7F85DD97` |
| `backend/tests/test_t06_tierras_y_mapa.py` | 02/10 18:43:16 | `D681F0290E4D1659` |
| `backend/tests_js/tierras_y_versiones.test.js` | 02/10 18:44:36 | `C67A9297587BA99C` |
| `docs/T06_MAPA_Y_TIERRA.md` | 02/10 18:24:29 | `50E35FB066119C97` |

> **Medido y comprobado:** `backend/cuedigital.db` tiene sha256 `71456B0B1E1FE444…` (06 primeros
> `71456b0b`, los mismos que cita el documento). **No se ha modificado**: su fecha de última escritura
> sigue siendo el 30/09/2026 18:05:33, antes de empezar esta revisión.

---

## 1. Tabla de lo probado

Cada clase del fichero nuevo es un contrato del encargo. «Resultado» dice lo que salió **cuando se
atacó** y lo que pasa **hoy** (a las 18:42:52, 42 de 42 en verde).

| # | Contrato a romper | Cómo se ha atacado | Resultado |
|---|---|---|---|
| 1 | **Los recuentos cuadran con las filas** (7 pruebas) | Una finca **de la forma de la suya** (sin forma, sin cultivo, sin hectáreas, sin pueblo y sin referencia) y, además, **una reimplementación fiel de `filtrarLasTierras`**, sacada del propio JavaScript, para aplicar cada opción de los cuatro filtros y contar las filas. Y el pie, uno por uno, contra lo que enseña cada fila (se lee en `app.js` la línea que decide cada etiqueta) | **D1, D3 y la mitad de D1-bis: defectos, arreglados.** Hoy: cada opción de los cuatro filtros deja salir exactamente las tierras que dice, y el pie cuadra con las filas |
| 2 | **Una tierra sin forma no desaparece, y al mapa no se le inventa nada** (3 pruebas) | Sin formas: `hay_forma` falso, caja vacía y **ni un solo decimal en toda la respuesta** (para que no haya ni un centro inventado). Con formas sintéticas: la envolvente contra **los anillos que la propia respuesta manda**, uno por uno, con un multipolígono partido a un grado de distancia | **D2 y una rotura nueva del arreglo de D7: encontradas y arregladas.** Hoy la envolvente contiene todos los vértices |
| 3 | **Un dato ausente no es cero** (2 pruebas) | Tierra sin superficie, sin referencia, sin versión: ningún `0.0` en toda la respuesta donde no se ha medido nada que sea cero; y una tierra sin versión **no** se cuenta como «sin revisar» | Correcto (los dos) |
| 4 | **Ensayar una importación no escribe** (2 pruebas) | **Cien** previsualizaciones del mismo lote con la huella de **todas** las tablas del modelo (nombres de columna y `repr` de cada valor) antes y después; y el plan del ensayo contra el del apunte de verdad | Correcto: **ni una fila, ni un apunte de auditoría, ni una versión**; y el ensayo dice lo mismo que el apunte |
| 5 | **Comparar no escribe y no se inventa los estados** (3 pruebas) | Los cuatro estados montados a mano (igual / cambiado / desaparecido / nuevo) y contados; **veinte** comparaciones con la huella de todas las tablas; dos campañas sin ninguna versión | Correcto: 1/1/1/1, 20 comparaciones sin escribir nada, y con cero datos son cuatro ceros (no un «todo bien») |
| 6 | **Aislamiento entre explotaciones: 404, no 403** (5 pruebas) | Una **segunda finca de verdad** creada por la API, con su campaña, su tierra y su versión: se usan **sus identificadores** en `/api/versiones?parcela_id=`, `?campana_id=`, `/comparar` y `/comparar-explotacion`, y se comprueba que la caja de mi finca no envuelve su forma | Correcto: **404 en las cuatro** (ninguna 403), la vista no ve ni una tierra ajena, y `/api/mapa/estado` no lleva datos de ninguna finca |
| 7 | **Las capas del mapa** (4 pruebas) | Que cada capa diga qué enseña, de quién es y de cuándo (leyendas distintas entre sí, todas de `textos.py`); el fallo del servicio **con un doble** (`SigpacNoContesta`: 503 y el texto del servidor, sin servir media imagen); y la caja que la vista da al mapa contra el propio `/api/mapa/imagen` | **D7: defecto, arreglado.** Hoy la caja que da la vista se puede pedir (200) y, si la finca no cabe entera, se dice y la pantalla lo lee. **Y `se_puede_ocultar` se sirve y no lo lee nadie** (§2, D-nota) |
| 8 | **Ni una cifra inventada** (3 pruebas) | Recorrido del JSON entero: ninguna clave que suene a cuenta hecha (total, media, porcentaje, suma…) fuera de los recuentos declarados; **y la lista entera de sitios donde puede haber un decimal**, con el camino de cada uno; los números del ensayo contra lo que hay guardado | Correcto en los tres (la lista de decimales se ha tenido que ampliar dos veces, y las dos por un decimal legítimo: §2, D2) |
| 9 | **Los textos viven en `textos.py`** (3 pruebas) | Clave por clave de los dos bloques nuevos (servidos en `/api/interfaz` **y** registrados en `textos_visibles()`), la jerga de `PALABRAS_PROHIBIDAS` en los dos bloques y en la respuesta entera, y la etiqueta del recuento de «sin forma» del ensayo leída en `app.js` | **D9: defecto, arreglado.** Hoy los dos bloques están servidos y sin jerga, y el ensayo tiene su propia etiqueta (`recintos_sin_forma`) |
| 10 | **`asegurar_indices()`** (5 pruebas) | Base recién creada (idempotente), base **sin ninguna tabla**, índice que falta, **índice cambiado a mano** (único a secas, sin la condición de las anuladas) y **un índice que no se puede crear** (dos filas repetidas), con la huella de todas las filas antes y después | **D10: defecto, arreglado.** Hoy: ni una fila cambia, nada se queda a medias y el fallo sale como `RuntimeError` con un mensaje en castellano |
| 11 | **La vista no se queda vieja** (dos pruebas) | Se lee el código de la pantalla: cuándo se pide la vista, qué la invalida y qué se recarga al abrir la ficha de una tierra | **D11: defecto, arreglado.** Hoy la vista se olvida cuando los datos se recargan |

**Nada de esto sale a internet y nada de esto toca la base del agricultor**: `tests/conftest.py` fija
`CUEDIGITAL_DATABASE_URL` y `CUEDIGITAL_ADJUNTOS` a una carpeta temporal antes de importar nada de
`app`, y el fallo del servicio de mapas se prueba **con un doble**, que es lo que el encargo pedía
(«no dependas de internet»).

---

## 2. Los nueve defectos, uno por uno

Los números **D1, D2, D3, D7, D9 y D11 son los del propio código**, que ya los cita con ese nombre
(«revisión de T06, D7»); los otros tres son míos y los digo con nombre. En cada uno: qué era, la
prueba que lo demuestra (**que estaba en rojo mientras el defecto estaba ahí**), qué le pasaba al
agricultor, y cómo quedó.

### D1 — El pie contaba las hectáreas de una manera y la fila las enseñaba de otra — **media**
*(encontrado 18:2x, arreglado 18:33)*

- **Dónde.** `backend/app/routers/parcelas.py`: `tiene_hectareas_dichas` era «la tierra tiene
  superficie **o** su versión del año trae `area_declarada_ha`», y de ahí salían el recuento del pie
  (`_los_totales_de_las_tierras`) y las **opciones del filtro de la PAC**. La columna «Hectáreas» de
  la tabla se llena solo con `superficie_ha` (`backend/web/app.js`, la línea que prepara
  `superficie_texto`) y `tierras_mapa.js` pinta «Sin hectáreas dichas» cuando ese texto viene vacío.
- **La prueba.** `Test1::test_la_columna_de_las_hectareas_y_el_recuento_del_pie_usan_el_mismo_dato`.
- **Qué le pasaba al agricultor.** Una tierra importada del cuaderno de la Junta **sin la superficie
  cultivada** (queda en `None`: hallazgo A7 de `docs/T02_VALORES_POR_DEFECTO.md`) pero con las
  hectáreas que él declara en su versión salía en la tabla con la etiqueta «Sin hectáreas dichas», y a
  la vez el pie decía que **no había ninguna** así y el filtro «Sin hectáreas dichas» **no se ofrecía**.
  Usaba el filtro para saber a qué tierras les falta la superficie y el programa le decía que a
  ninguna: dejaba de rellenar el dato que le faltaba.
- **Cómo quedó.** `tiene_hectareas_dichas=(parcela.superficie_ha is not None)` y, además, las
  hectáreas declaradas tienen su propio texto en la fila. **La prueba se reformuló**: antes decía «el
  pie tiene que decir 0» (que era describir el defecto) y ahora dice «el pie tiene que decir lo mismo
  que enseñan las filas», que es el contrato.

### D1-bis — Las hectáreas declaradas se servían y no las leía nadie — **baja**
*(encontrado 18:2x, arreglado 18:38)*

- **Dónde.** `TierraEnLaVista.area_declarada_ha` (esquema y `routers/parcelas.py`) se servía en cada
  fila «para la tabla», y **ninguna pantalla lo leía**: ni `app.js` ni `tierras_mapa.js` lo nombraban.
- **La prueba.** `Test1::test_lo_declarado_en_la_version_tiene_que_verse_donde_se_cuenta`.
- **Qué le pasaba al agricultor.** Declaraba las hectáreas de una tierra (es el dato que el cuaderno de
  la Junta pide aparte) y en la tabla no había ni una columna donde apareciera: podía volver a
  escribirlas creyendo que no se habían guardado.
- **Cómo quedó.** `app.js` monta `hectareas_declaradas_texto` y `tierras_mapa.js` lo enseña.

### D2 — La misma respuesta decía «0 tierras con forma» y «1 tierra con forma» — **baja**
*(encontrado 18:2x, arreglado 18:33)*

- **Dónde.** `routers/parcelas.py`, `_el_mapa_de_la_finca`: `tierras_con_forma` contaba las tierras con
  **el texto de la geometría** (`if tierra.geometria`), mientras `totales.con_forma` contaba las que
  tienen **anillos que se pueden dibujar** (`tiene_forma`). Una geometría escrita que no tiene anillos
  —un `POINT`, una línea, un polígono degenerado— hacía que los dos números de la misma respuesta se
  contradijeran, con `hay_forma` en falso y `tierras_con_forma` en 1.
- **La prueba.** `Test2::test_los_dos_recuentos_de_forma_de_la_misma_respuesta_cuadran`.
- **Qué le pasaba al agricultor.** Hoy nada, porque ese campo no lo lee ninguna pantalla (es una cifra
  que el servidor da mal y que el día que alguien pinte diría lo contrario que el pie). Por eso es
  baja.
- **Cómo quedó.** La caja y el recuento se calculan **de las tierras ya montadas** (`anillos`), un solo
  dato para los dos, y el esquema lo explica.
- **Y una cosa que aprendí de mi propia prueba:** al arreglarlo, la lista de decimales permitidos de
  `Test8` se puso roja, porque la respuesta creció con `extension` (§D7). Es lo que tiene que pasar:
  **un decimal nuevo se justifica en la prueba en vez de colarse**.

### D3 — El pueblo se juntaba por mayúsculas y se filtraba sin tildes — **media**
*(encontrado 18:2x, arreglado 18:37)*

- **Dónde.** `routers/parcelas.py`, `juntando_sin_mayusculas`: agrupaba las opciones del filtro por
  `escrito.upper()`; la pantalla (`tierras_mapa.js` → `paraBuscar` = `nucleo.sinTildes`) coteja las
  filas **sin tildes, sin mayúsculas y con los espacios de dentro juntos**. Dos normalizaciones
  distintas: una tierra escrita `MACHACON` y otra `Machacón` salían como **dos opciones con el
  recuento partido**, y al elegir cualquiera de las dos la pantalla enseñaba las dos.
- **La prueba.** `Test1::test_el_mismo_pueblo_escrito_de_dos_maneras_no_parte_el_recuento`.
- **Qué le pasaba al agricultor, y por qué no es un caso inventado.** En su cuaderno hay **3 tierras
  con `MACHACON`** (sin tilde: vienen del cuaderno de la Junta, que escribe lo que pone el papel) y la
  lista oficial del INE, que es de donde el formulario coge el pueblo, lo escribe **`Machacón`**
  (comprobado en `data/municipios_cyl.csv`). El día que apunte una tierra más eligiendo su pueblo de la
  lista tendría las dos formas en la misma finca: elige su pueblo, ve dos entradas del mismo pueblo y
  una le dice «3 tierras» y le enseña cuatro. Es el daño del filtro que dice 7 y enseña 6.
- **Cómo quedó.** Las dos partes usan **la misma normalización** (`_como_se_busca`, con el mismo
  criterio que `nucleo.sinTildes`).

### D7 — La vista daba una caja que el propio programa rechazaba — **media**
*(encontrado 18:2x, arreglado 18:35)*

- **Dónde.** `_el_mapa_de_la_finca` agrandaba la caja si era **más pequeña** que el mínimo del servicio
  de mapas, pero **no la recortaba si era más grande** que el máximo (`mapa.LADO_MAXIMO_GRADOS`, medio
  grado: unos 55 km). El propio `/api/mapa/imagen` contesta **422** a esa caja.
- **La prueba.** `Test7::test_la_caja_que_da_la_vista_la_tiene_que_aceptar_el_mismo_programa`.
- **Qué le pasaba al agricultor.** Abría el mapa de sus tierras y no veía ninguna foto; el aviso que
  leía era «no se ha podido traer la imagen… **puede ser la cobertura** o que el servicio no conteste»,
  que era mentira: su cobertura estaba bien y el servicio contestaba. Se quedaba sin mapa y con una
  pista que no llevaba a ningún sitio. **Con formas sintéticas**, porque con sus datos (0 de 64 tierras
  con forma medida) hoy no se puede ver; una explotación con tierras a 60 km es de lo más normal en
  Castilla y León, que es justo el caso contra el que el contrato avisa.
- **Cómo quedó.** La caja que se devuelve **es siempre una caja que este programa acepta** (se queda en
  el máximo) y la respuesta **dice que no se ve toda la finca** (`se_puede_ensenar_entera`), con la
  finca entera aparte (`extension`). La pantalla lee el aviso y lo dice en el mapa.

### D7-bis — El arreglo de D7 rompió el contrato 2 («la caja contiene todas las formas») — **media**
*(lo destapó esta revisión a las 18:35, arreglado a las 18:37)*

- **Qué pasó.** Al recortar la caja al medio grado, **la respuesta siguió diciendo que esa caja
  envolvía las formas** y ya no era verdad: un multipolígono con un trozo a un grado de distancia se
  salía de ella (`assert -5.304 <= -5.5`, medido). Mi prueba del contrato 2 se puso roja en cuanto se
  aplicó el arreglo de D7.
- **La prueba.** `Test2::test_la_caja_envuelve_todas_las_formas_y_no_se_queda_corta` (exige la
  invariante contra **el campo que la respuesta declara como envolvente**, `extension` si está y si no
  `caja`, para que siga valiendo si mañana le cambian el nombre).
- **Por qué importa.** Un campo que dice envolver todas las formas y no las envuelve es una cifra falsa
  del mismo tipo que las de `docs/T02_VALORES_POR_DEFECTO.md`: cualquier cosa que se apoye en él
  —incluido el propio JavaScript, que lo usa para decidir por dónde puede mirar— coloca una tierra
  fuera de la vista sin decirlo.
- **Cómo quedó.** `extension` (la envolvente sin recortar, `schemas.py`), con la tensión explicada en
  el propio esquema: `caja` es la parte que se puede pedir y `extension` es todo lo que hay.

### D9 — El ensayo llamaba «No se sabe» al número de recintos sin forma — **baja**
*(encontrado 18:2x, arreglado 18:39)*

- **Dónde.** `backend/web/app.js`, al preparar el ensayo de una importación:
  `{ etiqueta: textos.no_se_sabe, valor: plan.sin_forma }`. «No se sabe» es la frase que se usa cuando
  un **área** no se conoce; el agricultor leía «No se sabe  3» donde el dato es «3 recintos sin forma».
- **La prueba.** `Test9::test_la_etiqueta_del_recuento_de_sin_forma_del_ensayo_no_puede_ser_la_de_no_se_sabe`.
- **Qué le pasaba al agricultor.** Cosas distintas con la misma frase: «no se sabe» sugiere que hay tres
  datos que el programa no ha podido mirar, y lo que hay son tres recintos a los que no les ha llegado
  el polígono. **Y no lo podía cazar la prueba de «ni una frase escrita a mano»**: esa prueba comprueba
  que la frase exista en la copia de los textos, no que se esté usando para lo que es.
- **Cómo quedó.** Clave propia en `textos.py` (`recintos_sin_forma`).

### D10 — Si un índice no se puede crear, el programa no arranca y no lo explica — **media**
*(encontrado 18:2x, arreglado 18:36)*

- **Dónde.** `database.asegurar_indices` no atrapaba el fallo al crear un índice, y `crear_tablas()` se
  llama al arrancar (`main.py`), donde **solo se atrapa `RuntimeError`** para contarle al agricultor
  qué ha pasado y qué hacer. Con dos filas que incumplen un índice único salía
  `sqlite3.IntegrityError: UNIQUE constraint failed: recepciones.explotacion_id, recepciones.clave_de_reenvio`
  —una traza de Python en inglés— y el programa no se abría.
- **La prueba.** `Test10::test_si_un_indice_no_se_puede_crear_la_base_se_queda_entera_y_se_dice_en_castellano`,
  que además comprueba **lo que sí estaba bien**: la base **no se queda a medias** (ni un índice a medio
  crear ni una fila tocada), porque SQLite deshace el DDL.
- **Qué le pasaba al agricultor.** Con su base de hoy, **nada**: se ha medido (§3.2) que
  `crear_tablas()` no tiene que crear ni rehacer ningún índice suyo. Le pasaría a una instalación cuyo
  fichero tuviera filas repetidas antes de que el índice existiera, o después de una edición a mano.
- **Cómo quedó.** Una sola transacción para todos los índices y el fallo traducido a un `RuntimeError`
  con el porqué y qué hacer.

### D11 — La vista de las tierras se pide una vez por sesión y nadie la olvida — **media-alta**
*(encontrado 18:2x, arreglado 18:41)*

- **Dónde.** `web/app.js`: `/api/parcelas/vista` se pide solo `if (!t06.vista)` y se guarda en
  `estado.t06.vista`; **no había ni una línea** que la vaciara (ni `t06.vista = null` ni una segunda
  llamada), y el comentario decía «salvo que se fuerce» sin que existiera forma de forzarlo.
- **La prueba.** `Test11::test_despues_de_apuntar_una_tierra_la_vista_no_puede_seguir_contando_la_de_antes`
  (o se pide al abrir siempre, o hay alguna forma de olvidarla: cualquiera de las dos vale).
- **Qué le pasaba al agricultor.** Apuntaba una tierra en el asistente, corregía un nombre o borraba la
  que no era, y al volver a **la pantalla que existe para ver todas sus tierras** la tierra nueva no
  estaba y el pie seguía diciendo las de antes; en la misma sesión, «mis cosas» (que sí se recarga)
  decía 65 y esta pantalla decía 64. Una tierra borrada seguía en la lista y su botón llevaba a una
  dirección que ya no existía. El riesgo de verdad es el de siempre con una lista vieja: **volver a
  apuntar la tierra que cree que no se ha guardado**.
- **Cómo quedó.** `olvidarLaVistaDeLasTierras()`, llamada cuando los datos se recargan.

### Lo que no es un defecto, pero se ha medido y hay que decidir — **nota**

- **`mapa.extension` se sirve y no lo lee ninguna pantalla** (se ha buscado en todo `backend/web/`). El
  esquema dice que está «para no perder la información de dónde están las tierras de fuera», y la
  pantalla hoy lo resuelve por otro camino (deja que el centro se salga de la caja cuando la finca no
  cabe entera, `app.js`). Es un campo de 10 minutos antes de escribir esto y el arreglo está a medias:
  **o se usa, o se quita**, pero no conviene dejarlo ahí sin puerta. No he escrito prueba para esto a
  propósito: nació mientras revisaba y juzgarlo sería juzgar un trabajo a medias.
- **`se_puede_ocultar`** (de las capas del mapa) se sirve, es `true` en las tres y **tampoco lo lee
  nadie**: el contrato pide «que una capa que no se puede ocultar lo diga» y hoy no hay ninguna forma
  de que lo diga (D-nota en la tabla de §1). Está puesto como prueba que pasa
  (`Test7::test_lo_que_hace_falta_para_decir_que_una_capa_no_se_puede_ocultar_lo_lee_alguien`), que se
  pondrá roja el día que alguien lo use —al revés de lo que es costumbre—, y lo digo aquí porque es la
  familia de fallo que `AGENTS.md` §4 llama «un dato que existe y no tiene puerta».

---

## 3. Lo medido sobre los datos de verdad

### 3.1. Cómo se ha medido, y qué se ha borrado

Se copió `backend/cuedigital.db` a `%TEMP%` **comprobando la huella** (`sha256` de origen y copia
idénticos: `71456b0b1e1fe444593939571f16580e5702c53047185837dc270abf3696ba0d`), se leyó con
`sqlite3` en modo **solo lectura**, y al terminar **se borraron la copia y sus ficheros de al lado**
(comprobado: en `%TEMP%` no queda ningún `rev6_*.db`). El original no se ha abierto para escribir ni
una vez: su fecha de última escritura sigue siendo la del 30/09/2026.

Además se hizo **una segunda copia** para medir **qué le hace `crear_tablas()` a su base al
actualizar** (que es lo que el contrato 10 pide medir), y también se ha borrado.

### 3.2. Lo que dice su base, y lo que le hará el programa al arrancar

| Hecho medido | Número |
|---|---|
| Tierras | **64** en su explotación (y 1 más de la explotación 3: 65 en total) |
| Con geometría escrita | **0** |
| Sin superficie | **0** (y ninguna con 0 ha) |
| Sin la referencia completa (los tres números) | **0 de 64** |
| Nombres distintos | **60** para 64 tierras (hay 4 nombres repetidos, uno de ellos 3 veces) |
| Referencias distintas | **51** entre sus 64 tierras (`37-70-0-0-507-24-1` la comparten **9**) |
| Municipios, tal cual están escritos | **7**, todos en mayúsculas y sin tildes (`CALVARRASA DE ARRIBA` 54, `MACHACON` 3, `TERRADILLOS` 2, `PELABRAVO` 2, `CARBAJOSA DE LA SAGRADA` 1, `CALVARRASA DE ABAJO` 1, `ARAPILES` 1) |
| Especies sembradas en 2026 | **5** (`TRIGO BLANDO` 19, `CEBADA` 14, `BARBECHO TRADICIONAL` 12, `VEZA VELLOSA` 6, `AVENA` 3), 54 tierras con cultivo dicho y **10 sin decirlo** |
| Tabla `versiones_de_recinto` | **no existe** en su base (se crea vacía al arrancar) |
| Al arrancar, columnas que se añaden | **ninguna**; columnas «imposibles»: **ninguna** |
| Al arrancar, tablas nuevas | **8**, entre ellas `versiones_de_recinto` |
| Al arrancar, tablas reconstruidas | 5 tablas (para que 17 columnas puedan decir «no se sabe») |
| **Al arrancar, índices creados o rehechos** | **ninguno** (así que `asegurar_indices` no hace nada en su base: el defecto D10 no le toca) |
| **Filas tocadas por ese arranque** | **ni una**: la huella de las **26** tablas que ya existían es idéntica antes y después (comparando por `rowid` el nombre de cada columna y el `repr` de cada valor) |

**Y con eso se puede comprobar la tabla de §5.2 bis del documento de T06**, que dice: 64 tierras, 0 con
forma, 64 sin forma, 10 sin decir el cultivo, 0 sin hectáreas dichas, 64 sin ninguna versión de este
año, campaña 2026, `hay_forma` falso, caja nula, 7 municipios distintos, 6 opciones en el filtro de lo
sembrado con la mayor de 19 tierras, y ninguna zona de nitratos en la respuesta. **Las he comprobado
todas, una por una, y todas son verdad** (la última, la de la zona de nitratos, porque el esquema de la
vista no tiene ese campo). El nombre de 42 caracteres también.

### 3.3. El estado de la suite (medido a las 18:41)

| Qué | Pruebas | Fallos |
|---|---|---|
| `tests/test_revision_t06.py` (este trabajo) | **42** | **0** |
| `tests/test_t06_tierras_y_mapa.py` (el del ticket, que ha crecido hoy) | 28 | 0 |
| `tests_js/tierras_y_versiones.test.js` | 41 | 0 |
| Suite de Python entera | **3527** | **6** |
| Suite de JavaScript entera (`node --test`) | **805** | **0** |

**Los 6 fallos de Python no son de T06 y no son míos.** Son de las pantallas nuevas `semillas.js` y
`siembras.js`, que el otro agente está escribiendo ahora mismo: `test_la_migracion_a_react` (dos
ficheros de pantalla que no están en la lista y las cuentas del inventario), `test_la_version_visible`
(el pie dice `2026-10-03-64` y la caché `2026-10-03-65`), `test_las_tierras_se_pueden_corregir` (una
tabla nueva, `siembras`, que apunta a una tierra), `test_los_botones_hacen_algo` (11 acciones de
`semillas.js`/`siembras.js` que se pintan y no las atiende nadie) y `test_lista_de_la_junta` (la
documentación dice 775 pruebas de JavaScript y hoy hay 805). **Ninguno nombra un fichero de T06.**
Cuando se escribió este informe estaban en rojo, y así se deja dicho.

---

## 4. Afirmaciones que **no** son verdad (medidas, sin prueba automática)

No llevan prueba porque la suite **no puede leer la base del agricultor ni sus documentos**: la medida
está aquí, con el comando al lado.

1. **La justificación de juntar el pueblo sin distinguir mayúsculas es falsa.** El código dice, en tres
   sitios y en la prueba de JavaScript (como «**Medido**»): «el mismo pueblo está escrito
   `CALVARRASA DE ARRIBA` en 54 tierras y `Calvarrasa de Arriba` en 1»
   (`routers/parcelas.py`, `tierras_mapa.js` ×2, `tests_js/tierras_y_versiones.test.js`).
   **La medida de verdad**: `CALVARRASA DE ARRIBA` 54 y `CALVARRASA DE **ABAJO**` 1 — **dos pueblos
   distintos**, uno con «Arriba» y otro con «Abajo». El arreglo (D3) es correcto de todas formas, pero
   se justificó con un ejemplo que no existe, y eso es exactamente lo que `AGENTS.md` prohíbe («los
   umbrales y las medidas se miden, no se inventan»). Además: lo que sí hay en sus datos y no se estaba
   cubriendo es la **tilde** (`MACHACON` en su cuaderno, `Machacón` en la lista oficial), que es el caso
   que D3 arregló. **Comando**: `SELECT municipio, COUNT(*) FROM parcelas WHERE explotacion_id=1 GROUP
   BY municipio` sobre la copia.
2. **`docs/T06_MAPA_Y_TIERRA.md` §1.4 dice que de la versión sale «la más nueva» de la campaña.** El
   código coge la primera de una consulta ordenada por `(parcela_id, clave)` y se queda con ella; con
   dos fuentes del mismo año (que el ticket dice que es normal) las dos **empatan** y decide el orden
   que le sale al plan de la consulta. **Lo he intentado romper y no he podido**: con dos tierras
   idénticas y las importaciones en orden contrario, las dos enseñan lo mismo (medido: gana la versión
   cuya `fuente` va antes por orden alfabético, o sea `agricultor` antes de `sigpac`, que encima es la
   dirección buena). Es una frase del documento que no describe lo que hace el código, no un defecto.
3. **§1.4 sigue diciendo que `mapa.caja` es «la caja que envuelve las formas que de verdad hay».** Desde
   el arreglo de D7 eso ya no es así: `caja` es **la parte que se puede pedir de una vez** y quien
   envuelve todo es `extension` (lo dice el esquema nuevo). El documento no se ha actualizado. **Es la
   frase que hizo que mi prueba del contrato 2 se pusiera roja cuando el arreglo entró**: mientras el
   esquema y el documento digan cosas distintas, cualquiera que se apoye en el documento se equivoca.
4. **Los recuentos del documento están viejos** (§1.8 y §5.1): dice **19** pruebas de Python del ticket
   y **35** de JavaScript, y hoy hay **28** y **41**; dice **3422** de Python y **775** de JavaScript, y
   hoy hay **3527** y **805**. No es culpa del documento —el árbol no ha parado— pero quien lo lea tiene
   que saber que **hoy no cuadra**, y el guardián que lo vigila está en rojo por eso.
5. **Las fechas del documento van un día por delante del reloj de esta máquina.** El documento dice
   «Última actualización: 03/10/2026 (la fecha del reloj de la máquina donde se ha hecho el trabajo)» y
   fecha sus medidas el 03/10/2026; el reloj de esta máquina, mientras se escribía esto, decía
   **02/10/2026 18:4x** (y su propio fichero tiene fecha de escritura de hoy, 02/10 18:24). Es lo único
   de este informe que podría ser culpa del reloj y no del texto, y por eso lo digo así.

**Y lo que sí se ha comprobado que es verdad**, porque un informe que solo cuenta lo malo no dice
cuánto se ha mirado: la tabla de §5.2 bis (las doce líneas), que «previsualizar no escribe» y que el
apunte deja la frase de «sin forma» (§5.2), que `scripts/comprobar_en_un_navegador.py` **no** incluye
las dos rutas nuevas (§4.5, comprobado leyendo el guion), que no hay ninguna capa de avisos (§4.3), que
no hay ningún botón que mida distancias ni áreas (§4.1) y que la capa de la fecha no se inventa (§4.2).

---

## 5. Lo que NO he podido probar

1. **Un navegador de verdad.** No he abierto ninguna de las dos pantallas. Todo lo que digo del
   JavaScript sale de leerlo, de ejecutar su suite (`node --test`: 805 pruebas, 0 fallos) y de las
   mediciones que el otro agente hizo en Chrome (§5.2 bis del documento), que **no he repetido**. En
   particular: que las 64 tierras se vean a 390, 1024 y 1440 px lo doy por bueno **por lo que dice el
   documento**, no por haberlo visto.
2. **La base del agricultor por la API.** Solo la he leído con SQL (§3). No he levantado un servidor
   sobre la copia ni he dado acceso a una cuenta, así que **no he visto la respuesta de `/api/parcelas/vista` con
   sus 64 tierras**: lo que se puede deducir de ahí lo he deducido de los datos y de las pruebas
   sintéticas, no de la respuesta de verdad.
3. **PostgreSQL.** Nada de T06 se ha ejecutado contra él. La limitación que `asegurar_indices` reconoce
   por escrito (en otro motor solo crea los índices que falten, porque no puede leer la definición
   guardada) **no la he probado**: no hay servidor. Tampoco el índice único parcial en su dialecto.
4. **El IGN y el SIGPAC de verdad.** El fallo del servicio lo he probado **con un doble** (como pedía el
   encargo). Que la ortofoto llegue de verdad, y cuánto tarda, es lo que dice §5.2 del documento y no lo
   he comprobado.
5. **Los campos que nacieron mientras revisaba**: `clave_recinto`, `cuantas_con_el_mismo_nombre`,
   `mismoRecinto` (el aviso de «varias tierras comparten el recinto») y `extension` en la pantalla. Los
   he visto aparecer y no los he juzgado: no se puede revisar lo que se está escribiendo.
6. **La carrera de dos peticiones a la vez**, los permisos de varias cuentas en una misma finca y todo lo
   que no sea T06 (el almacén, la firma, el CUE de la Junta).
7. **`scripts/humo.py`** contra un servidor de verdad: no se ha ejecutado.

---

## 6. Valoración honesta del documento de T06

**Lo que cuenta se corresponde con lo que hace el código, con cuatro salvedades** (las tres primeras de
§4 y los recuentos). En detalle:

- **§1.1, §1.2, §1.3 y §1.5 (lo construido y los textos): verdad.** Las dos direcciones existen, las dos
  pantallas existen, los dos bloques de textos están en `textos.py` y se sirven en `/api/interfaz`
  (`tierras` y `versiones`), y las 27 claves de cada bloque no llevan jerga. Comprobado clave por clave.
- **§1.4 (lo que devuelve el servidor): verdad, salvo la frase de la caja** (salvedad 3). Los cuatro
  bloques (`tierras`, `totales`, `mapa`, `filtros`) son lo que dice, y los recuentos son recuentos.
- **§1.7 y §5.2 bis (lo medido con los datos de verdad): verdad, y lo he comprobado yo.** Es la parte
  que más valor tiene del documento: el dato «0 de 64 tierras con forma» cambia lo que significa
  «representativo», y a partir de ahí el documento hace lo correcto, que es no apoyarse en «casi todas
  tienen forma».
- **§2 (lo reutilizado): verdad** en lo que se puede comprobar: `geo.anillos_de_un_wkt`,
  `geo.rectangulo_de_un_wkt`, `servicios.los_cultivos_de_la_finca`, las funciones de T05 y `nucleo.js`.
- **§3.8 («ninguna cifra que el servidor no haya dado»): verdad, y está probado por partida doble**: la
  prueba del ticket (la lista de claves de `totales` escrita entera) y la mía (`Test8`, que recorre el
  JSON y exige que cada decimal esté en una lista de sitios justificados).
- **§3.9 (la imagen que no llega): verdad**, incluida la historia del `<img src="">` con los datos
  reales; y el camino del fallo está probado con un doble.
- **§4 (lo que NO se ha hecho): verdad y es lo más honesto del documento.** He comprobado una por una
  las cinco cosas que declara: no hay botón de medir distancia ni área, la fecha no se inventa (los dos
  WMS no publican dimensión de tiempo: por eso `fecha` va en `null` y se dice), no hay capa de avisos,
  el zoom y el punto no viajan en la dirección, y el guion del navegador no recorre las dos rutas
  nuevas. **Declarar lo que falta con esas palabras es exactamente lo que hay que hacer**, y es lo que
  hace que este documento se pueda creer en lo demás.
- **§5.1 (los recuentos): no reejecutado**, y hoy están viejos (§4.4). El propio documento avisa de que
  el recuento de dos tickets a la vez solo se cierra cuando los dos paran: eso es verdad, y hoy se puede
  ver —la documentación dice 775 pruebas de JavaScript y hay 805, y hay un guardián en rojo por eso—.
- **§8 (la trampa del `Get-Content`): verdad y bien contada.** Y añado una del mismo tipo, que le ha
  pasado a esta revisión y conviene dejar escrita: **el árbol se movió mientras se revisaba**, así que
  los fallos de una ejecución hay que fecharlos. Lo digo en §0.

**Lo que el documento no cuenta y yo sí he encontrado**: que el pie y la fila podían no cuadrar en las
hectáreas (D1), que el pueblo se juntaba de una manera y se filtraba de otra (D3), que la caja del mapa
podía no caber en el propio programa (D7) y que la lista de tierras se quedaba vieja toda la sesión
(D11). Los cuatro son de la mitad del ticket que el documento cuenta como terminada, y ninguno de los
cuatro se veía en las pruebas que el ticket traía.

---

## 7. Cómo se reproduce

```powershell
cd F:\EspacioCodigo\CueDigital\backend

# Las 42 pruebas de esta revisión
..\.venv\Scripts\python.exe -m pytest tests\test_revision_t06.py -q --junit-xml=$env:TEMP\rev6.xml

# Las del ticket y su suite de JavaScript
..\.venv\Scripts\python.exe -m pytest tests\test_t06_tierras_y_mapa.py -q
node --test tests_js/tierras_y_versiones.test.js

# La suite entera (el 02/10/2026 a las 18:41: 3527 y 6 fallos, los 6 de `semillas`/`siembras`)
..\.venv\Scripts\python.exe -m pytest tests -q --junit-xml=$env:TEMP\rev6_todo.xml
node --test "tests_js/*.test.js"
```

**Ninguna prueba de este trabajo toca la base del agricultor**: `tests/conftest.py` fija
`CUEDIGITAL_DATABASE_URL` y `CUEDIGITAL_ADJUNTOS` a una carpeta temporal antes de importar nada de
`app`, y las cinco pruebas de `asegurar_indices` se montan **su propio motor** sobre un fichero de
`tmp_path` (no tocan ni el esquema de la base de la suite). Las mediciones de §3 se hicieron sobre
copias temporales de su base, **con la huella comprobada y borradas al terminar**.

**Y una nota de método, porque pasó:** la copia de la base del agricultor se ha borrado de `%TEMP%`
(comprobado: no queda ningún `rev6_*.db`, ni sus `-wal`/`-shm`, ni la copia que `crear_tablas` deja al
reconstruir tablas). Dejar los datos de un agricultor —con su NIF— en el temporal de la máquina no es
una revisión: es un descuido.
