# Lo que falta por diseñar: la app entera, pantalla por pantalla

Este documento es **la lista de trabajo** de la parte de Stitch: qué pantallas y qué piezas de la
aplicación tienen ya un diseño de Stitch, cuáles no, y en qué ronda se aplicó lo que hay. Nace de lo que
pidió David (ronda 90): *«usa mucho más Stitch, para cualquier diseño, para cualquier mínima cosa, hazle
caso en las ideas, no pares hasta tener toda la app cubierta con todas las funcionalidades y ui
refactorizadas y perfectas»*.

**La regla de esta lista: no queda nada sin diseño.** Cuando una pantalla tenga su diseño, aquí se apunta
su fichero, la ronda en que se aplicó y qué de él se aplicó. Cuando algo del diseño **no** se pueda
aplicar, se dice aquí y en [`docs/MEJORAR_LA_INTERFAZ_CON_STITCH.md`](../../MEJORAR_LA_INTERFAZ_CON_STITCH.md)
con su motivo.

## 1. La cuenta, para saber de un vistazo cuánto queda

| | Cuántas |
|---|---|
| Pantallas en React (`PANTALLAS_EN_REACT`) | **29** |
| Piezas compartidas (`react/piezas/`) | **10** (dos nuevas el 30/09/2026: `marco.js`, el armazón del ordenador, y `tabla.js`, la tabla de las listas) |
| **Encargos escritos para Stitch** (`PANTALLAS` del guion) | **32** (las 29 pantallas, la lámina de piezas y las **dos láminas de estados nuevos** de la ronda 92) **+ 11 de escritorio** (`PANTALLAS_ESCRITORIO`) |
| **Diseños pedidos y bajados** | **32 de 32** de móvil y **11 de 11** de escritorio — **no queda ninguna pantalla, ninguna pieza ni ningún estado nuevo sin su diseño** |
| **Con diseño de Stitch aplicado** (rediseño de la ronda 76, más lo de las rondas 77 a 93) | **30 pantallas y piezas** + **los 2 estados nuevos de las rondas 92 y 93** (`inicio`, `asistente`, `mis_cosas`, `mi_cuaderno`, `cesta`, `analiticas`, `ayuda`, `cultivos`, `borrador`, `cuaderno_de_la_junta`, `documentos`, `dictado`, `hecho`, `mis_datos`, `medidas`, `facturas`, `planes`, `quien_entra`, `ventas`, `grupos`, `decir_cultivo`, `nuevo_documento`, `firmar`, `nueva_factura`, `interpretacion_factura`, `entrar`, `mapa`, `traer_del_sigpac`, `campanas`, `piezas`) |
| **Con diseño bajado y esperando a aplicarse** | **0 de móvil**. De escritorio: **3** esperan su turno (`ventas`, `analisis` y `maestros`), porque son pantallas que **todavía no existen** en la versión de ordenador (fase 6). Los otros **8 de escritorio están aplicados**: `estructura` (el armazón y la tabla de tierras, con el panel y el dibujo de la forma), `panel` (el panel de mando), `cuaderno` (su tabla, con el pie de los firmados), `almacen` (su tabla y su panel), `formulario` (la forma de los formularios, aplicada en parte), `cultivos` (su tabla, el filtro de las que faltan y la columna de rotación), `facturas` (su tabla) y `campanas` (su tabla) |
| **Estados nuevos con su diseño** (rondas 92 y 93) | **2**: corregir lo que ya está guardado (`docs/stitch/rediseno/corregir_un_apunte.png`) y borrarlo (`docs/stitch/rediseno/borrar_un_apunte.png`). **No hicieron falta más**: la ronda 93 llevó los mismos dos estados a las fichas de lo que se usa, a los análisis, a las ventas, al plan de abono, a los papeles y a las facturas, y un estado nuevo no necesita lámina nueva —la ficha, los dos botones y la pregunta de borrar son los mismos—; lo único que cambia es lo que enseña la ficha, y eso se arma en `app.js` con el mismo dibujo que la lista. Corregir un papel o una factura **usa la pantalla con la que se guardan**, que ya tiene su diseño |
| **Sin encargo escrito** | **0** |

## 2. Las pantallas

Las cuatro primeras son las del rediseño de la ronda 76, ya aplicadas. De las demás, **ninguna tenía
diseño propio**: se han ido mejorando con las ideas que Stitch dio para las cuatro primeras (iconos
dibujados, la tarjeta de una tierra, cada dato con su nombre…), pero **a cada una no se le ha pedido su
diseño**. Eso es lo que se hace a partir de aquí.

| Pantalla (clave) | Qué es | Diseño | Aplicado |
|---|---|---|---|
| `inicio` | «¿Qué has hecho hoy?», las seis acciones | `rediseno/inicio.png` | Rondas 76 y 80 |
| `mi_cuaderno` | El resumen del año, con sus bloques | `rediseno/mi_cuaderno.png` | Rondas 79 a 81 |
| `mis_cosas` | «Mis parcelas, productos y máquinas» | `rediseno/mis_tierras.png` | Rondas 78 y 87 |
| `asistente` | Un paso de apuntar (elegir la tierra) | `rediseno/asistente.png` | Rondas 77 y 82 |
| `cesta` | «Lo que tengo en el almacén» | `rediseno/cesta.png` + **`escritorio/almacen.png`** | **Ronda 90** (etiqueta de estado, «Te queda» destacado, el motivo en su franja) y **el 30/09/2026 la tabla de escritorio**: Producto · Nº de registro · Comprado · Echado · Te queda · Estado · Acciones, con el panel de al lado (de dónde sale lo comprado) y el pie que dice cuántos hay que mirar. **Lo que NO se ha copiado**: las tarjetas de números y la columna de gasto en euros por producto, porque ese número no existe en el programa (ver `docs/LA_APLICACION_DE_GESTION.md`, apartado 6 quater) || `analiticas` | «Los análisis» del laboratorio | `rediseno/analiticas.png` | **Ronda 90** (la edad en su etiqueta, los números en su bloque, el papel con lo que hay que hacer al lado) |
| `ayuda` | «Ayuda»: la ley y los porqués | `rediseno/ayuda.png` | **Ronda 90** (las etiquetas «Sí es obligatorio» / «Es voluntario») |
| `hecho` | «Apuntado»: la confirmación y el DESHACER | `rediseno/hecho.png` | **Ronda 90** (el plazo de espera en su franja, y los botones en su orden: volver primero y deshacer debajo con su explicación) |
| `documentos` | «Los papeles»: lo que acompaña al cuaderno | `rediseno/documentos.png` | **Ronda 90** (guardar un papel también arriba; al papel sin fichero se le dice en su franja y su botón es el grande) |
| `cultivos` | «Qué hay sembrado» este año | `rediseno/cultivos.png` + **`escritorio/cultivos.png`** | **Ronda 90** (la etiqueta «Al día» / «Falta rellenar» en cada tierra, el aviso en su franja y el botón grande para la que falta) y **el 30/09/2026 la tabla de escritorio**: Tierra · Hectáreas · Este año hay · **Rotación** · Otros años · Estado · Acciones, con **la alerta de rotación en su propia columna** y **el filtro «VER SOLO LAS QUE FALTAN»** en la franja del aviso, que es lo que convierte el aviso en algo que se puede arreglar. **Lo que NO se ha copiado**: las columnas de referencia del SIGPAC y del término municipal (la referencia ya está en el nombre de sus tierras, importado del cuaderno de la Junta, y el pueblo está en la ficha), ni la barra de estado de abajo |
| `mis_datos` | El titular y la finca | `rediseno/mis_datos.png` | **Ronda 90** (los once campos numerados; el botón de las fincas con su explicación) |
| `quien_entra` | Quién entra en mi finca y en cuál estás | `rediseno/quien_entra.png` | **Ronda 90** (las hectáreas de cada finca, la etiqueta de «estás trabajando aquí ahora» y qué puede hacer quien ayuda) |
| `medidas` | «Lo que hago sin echar producto» | `rediseno/medidas.png` | **Ronda 90** (las diez medidas numeradas y las hechas diciéndolo con palabras) |
| `ventas` | «Lo que he vendido» | `rediseno/ventas.png` | **Ronda 90** (la fecha en su renglón, el producto en grande y la cuenta de cuántas van y cuánto sale) |
| `grupos` | «Parcelas que se llevan igual» | `rediseno/grupos.png` | **Ronda 90** (las tierras del grupo una por línea con sus hectáreas, y la etiqueta de quién lo juntó) |
| `dictado` | «Dímelo con la voz» | `rediseno/dictado.png` | **Ronda 90** (HABLAR primero, el recuadro debajo y dicho que se puede corregir con el dedo) |
| `borrador` | La revisión de lo dictado | `rediseno/borrador.png` | **Ronda 90** (lo que has dicho, arriba y entero; lo que falta, en su caja de aviso) |
| `nuevo_documento` | «Guardar un papel» | `rediseno/nuevo_documento.png` | **Ronda 90** (los campos numerados, las carpetas para tocar y el papel se sube en la misma pantalla) |
| `firmar` | «Firmar el cuaderno» | `rediseno/firmar.png` | **Ronda 90** (el estado de la firma en su etiqueta y el aviso de que sin certificado no se puede firmar) |
| `planes` | «El plan de abono del año» | `rediseno/planes.png` | **Ronda 90** (el veredicto «En regla» / «Alerta: exceso» en cada plan, y el aviso de cuándo es obligatorio, que el servidor mandaba y nadie leía) |
| `entrar` | Entrar (correo y clave, o certificado) | `rediseno/entrar.png` | **Ronda 90** (revisada, **sin cambios**: ya hace lo que el diseño enseña) |
| `facturas` | «Mis facturas», la lista | `rediseno/facturas.png` + **`escritorio/facturas.png`** | **Ronda 90** (cada factura dice si tiene su papel, con VER LA FACTURA o SUBIR LA FOTO; y la cuenta de cuántas hay) y **el 30/09/2026 la tabla de escritorio** (Fecha · Quién te lo vendió · Nº · Base · IVA · Total · El papel · Acciones, con el papel que falta en ámbar). **Pendiente de esa misma lámina**: la franja de números de arriba (facturas, base, IVA, total del año y cuántas están sin papel) — los números ya se cuentan, falta ponerlos |
| `nueva_factura` | Añadir una factura | `rediseno/nueva_factura.png` | **Ronda 90** (la caja grande del fichero y el trato claro: nada se guarda hasta que él lo mire) |
| `interpretacion_factura` | «Esto es lo que he leído» | `rediseno/interpretacion_factura.png` | **Ronda 90** (la etiqueta «Revisar números» en la línea que no cuadra) y **ronda 93**: la misma pantalla sirve para **corregir una factura guardada** —el diseño de corregir es el de la ronda 91— con otro título, otra pista y el volver a la lista de facturas |
| `mapa` | Buscar la tierra en el mapa del SIGPAC | `rediseno/mapa.png` | **Ronda 90** (la confirmación de que el SIGPAC ha contestado, con el recordatorio de comparar con el papel) |
| `decir_cultivo` | Decir qué hay sembrado en una tierra | `rediseno/decir_cultivo.png` | **Ronda 90** (las cinco preguntas numeradas, la etiqueta «Hace falta» y el aviso que quita el miedo al formulario) |
| `cuaderno_de_la_junta` | Traer las tierras del cuaderno de la Junta | `rediseno/cuaderno_de_la_junta.png` | **Ronda 90** (la barra de las tres fases y el aviso de que leer no apunta nada) |
| `traer_del_sigpac` | Traer una tierra pegando su referencia | `rediseno/traer_del_sigpac.png` | **Ronda 90** (el camino rápido primero y los seis datos del camino largo numerados) |
| `piezas` (lámina) | La tarjeta de una tierra, la lista de botones, el campo con su ayuda, los tres avisos, el bloque de apuntado, la barra del asistente y el estado vacío | `rediseno/piezas.png` | **Ronda 90** (revisada pieza por pieza: todas estaban como la lámina las dibuja; de la del bloque de apuntado salió **la ficha de lo que se acaba de apuntar**, que faltaba) |
| `campanas` | «Los años de mi cuaderno»: en qué año estás apuntando, cuáles tienes y cuánto hay dentro | `rediseno/campanas.png` | **Ronda 93**: es la pantalla nueva, y de su diseño se aplicó el rótulo «Año del cuaderno» encima del año, el año en grande con su etiqueta de estado al lado («Estás apuntando en este» / «Año cerrado»), las dos fechas en su renglón, **cuánto hay dentro** («Tiene 42 apuntes dentro») y el **BORRAR apagado con su explicación al lado** cuando el año no se puede quitar |

## 2 bis. Cómo se retoma la tanda, y qué queda por aplicar

**Los 29 diseños están pedidos y bajados**: no queda ninguna pantalla ni ninguna pieza sin su diseño (eso era
el punto (a) de lo que pidió David, y está hecho). Lo que queda es **aplicarlos**, y se hace en las rondas
siguientes, pantalla por pantalla, con sus pruebas y con la captura mirada. Si hiciera falta volver a pedir
alguno (por ejemplo, porque una captura saliera ilegible), el comando es el mismo y **no duplica nada**: el
fichero `docs/stitch/pantalla_<clave>.json` es el que dice que ya se pidió.

```powershell
cd backend
../.venv/Scripts/python.exe scripts/disenar_con_stitch.py --nuevas 4347842392867690825
```

> **Los ficheros del estilo viejo están renombrados.** Las capturas de las rondas 40 a 70 (`docs/stitch/`)
> se llamaban igual que las claves nuevas, así que `--nuevas` creía que esas pantallas ya tenían diseño y
> **no las pedía** (pasó con «mis facturas»). Se han renombrado a `*_estilo_viejo.*` para que se vea que son
> de antes: el diseño de verdad de esas pantallas se vuelve a pedir con el estilo de ahora.

## 2 ter. Ideas de los diseños que necesitan algo que hoy no existe

No se descartan: se apuntan, porque son funcionalidad de verdad y David ha pedido «todas las
funcionalidades».

| Idea (de qué diseño) | Qué haría falta | Por qué no se ha hecho ya |
|---|---|---|
| **«Ver entradas y salidas de este producto»** (el almacén) | Una pantalla nueva: los apuntes de ese producto, uno detrás de otro | Sería una pantalla nueva con su acceso, sus pruebas y su sitio en la caché del campo. Hoy el producto se mira en su ficha y sus apuntes, en «mi cuaderno» |
| **«Te llega para unas N hectáreas»** (el almacén) | Que el **servidor** calcule con qué gasto medio se ha echado ese producto y lo mande hecho | Hacer esa cuenta en la pantalla, con datos que no tenemos, sería inventarse un número: es justo lo que este proyecto no hace |
| **«Apuntar tratamiento a las N»** (los grupos) | Un atajo que abra el asistente con ese grupo ya elegido | Hoy se hace por el camino de siempre (al apuntar, después de la lista de parcelas salen los grupos). El atajo es una función nueva, no un cambio de diseño |
| **El resumen vivo del papel** (guardar un papel) | Que la pantalla guarde el estado de los campos mientras se escriben | Los campos los lee `app.js` por su `id` (formularios no controlados): es la decisión que sostiene toda la aplicación, y cambiarla es otro trabajo entero |

> Las capturas de las rondas 40 a 70 (`docs/stitch/pantalla_*.png`) son del **estilo viejo** («CUE Digital»
> verde y dorado, con emoji) y no se aplican: el rediseño de la ronda 76 cambió el lenguaje entero
> (botones con borde, iconos dibujados, tarjetas). Se dejan guardadas como historia y para mirar sus ideas
> sueltas, pero cada pantalla que las tenía **vuelve a pedirse** con el estilo nuevo.

## 3. Las piezas y lo que se repite en todas las pantallas

Esto es «cualquier mínima cosa» de lo que pidió David: no son pantallas, son los trozos que salen en
muchas. Se piden juntos en una lámina (`piezas`) para poder revisarlos de una vez.

| Pieza | Dónde se usa | Diseño | Aplicado |
|---|---|---|---|
| `tarjeta` (la tarjeta de una tierra) | El asistente, «mis cosas», «mi cuaderno» | `rediseno/mis_tierras.png` | Rondas 77 a 79 |
| `lista_para_elegir` | La mitad de los pasos del asistente | `rediseno/asistente.png` | Ronda 77 |
| `confirmacion` | Las cinco pantallas de «guardado» y «¿qué has hecho?» | — | — |
| `campo` (el campo con su pregunta y su ayuda) | El asistente y todas las altas | — | — |
| `campos_del_maestro` (un grupo de campos) | Las altas (tierra, producto, máquina…) | — | — |
| `ayuda_de_un_campo` (la ayuda de un campo) | Los pasos del asistente y las altas | — | — |
| `resumen_del_apunte` | El paso del resumen del asistente | — | — |
| La cabecera («Mi cuaderno», la pastilla A+ y Salir) y la franja de pendientes | Todas las pantallas | `rediseno/*.png` (sale en las cuatro) | Rondas 76 y 84 |
| El pie («Si algo no lo entiendes…») | Todas las pantallas | `rediseno/*.png` | Ronda 76 |
| Los avisos (normal, de error y de pendientes) | Todas | — | — |
| Los estados vacíos (una lista sin nada) | Casi todas | — | — |

## 4. Cómo se pide cada diseño (y dónde queda)

1. El encargo escrito de cada pantalla vive en `backend/scripts/disenar_con_stitch.py` (`PANTALLAS`), con
   **el texto real de `textos.py`** y las reglas del campo (móvil, una mano, sol, sin menús escondidos,
   sin barra de pestañas, iconos dibujados).
2. Se le pide a Stitch con el **proyecto** `4347842392867690825` y **nuestro sistema de diseño**
   (`assets/87c81708ca75482bb84bcecc667cd7d9`, hecho con `DESIGN.md`), en `deviceType: MOBILE`.
3. La captura, el HTML y lo que Stitch cuenta de su diseño se guardan en `docs/stitch/rediseno/`
   (`<clave>.png`, `<clave>_grande.png`, `<clave>.html`, `<clave>_explicacion.md`).
4. Se **mira la captura** y se aplica lo que se pueda, **diciendo lo que no** y por qué.

```powershell
cd backend
# la clave está fuera del repositorio (STITCH_API_KEY o %TEMP%\stitch_key.txt)
../.venv/Scripts/python.exe scripts/disenar_con_stitch.py --pantalla cesta --todas 4347842392867690825
```

Tarda minutos por pantalla y **no se reintenta**: si la llamada se corta, se pregunta por la pantalla
(`get_screen`) en vez de volver a pedirla, que la duplicaría.
