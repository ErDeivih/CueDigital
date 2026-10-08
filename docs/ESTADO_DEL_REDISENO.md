# Estado del rediseño, y lo que queda por decidir

> **Para qué es este fichero.** El encargo del rediseño está en
> [`REDISENO_V0_STITCH_20261007.md`](REDISENO_V0_STITCH_20261007.md) y su material en
> `docs/stitch/crm_20261007/`. Esto es lo que **ya está hecho y medido**, y —lo que más importa— **la
> decisión que falta tomar** antes de seguir. Se escribe el 07/10/2026, al cerrar una sesión larga, para
> que la siguiente no tenga que reconstruir el estado leyendo diffs.

---

## 1. Lo que está entregado, y con qué se comprueba

| Qué | Cómo se comprueba (comando) |
|---|---|
| **El recorrido del encargo**: Inicio → Tierras → buscar entre 64 → ficha → planificar → historial → volver a la lista | `pytest tests/test_el_recorrido_se_anda.py` — **levanta el servidor en una base temporal y anda el recorrido con Chrome sin ventana**. 15 comprobaciones, 0 fallos. Capturas por paso en `%TEMP%\cd-ui\recorrido-*.png` |
| **Menú agrupado** (Inicio · El campo · La gestión · El cuaderno · Ajustes) y **navegación completa a 390/712 px** | `python scripts/comprobar_el_armazon.py <dir>` (61 comprobaciones) y `node --test tests_js/armazon.test.js` |
| **Contexto**: finca, campaña y **lo que falta por apuntar**, en la barra, desde cualquier pantalla | Dentro del recorrido: «la barra dice lo que falta por apuntar» |
| **Las cuatro pantallas se identifican** (ruta, elemento propio, sin formulario de entrar y con datos del servidor), con **casos negativos** | `python scripts/mirar_pantallas.py <dir>` — 16 capturas del escenario de 64 tierras, y el escenario vacío aparte (`--vacio`) |
| **Filtros conservados al volver** | `tests_js/interfaz.test.js` (memoria de vista) y `scripts/comprobar_en_un_navegador.py` |
| **La misma tierra se dice igual en el panel y en su ficha** | `tests_js/interfaz.test.js` → «la misma tierra se dice igual en el panel y en su ficha» |
| **El móvil abre la ficha** (y no otra pantalla distinta que el ordenador) | `python scripts/comprobar_la_ficha_en_el_movil.py <dir>` — 4 comprobaciones a 390 px |

**Números al cerrar esta sesión**: 4.583 pruebas de Python (0 rojos, 1 omitida), 1.065 de JavaScript
(0 rojos). Los tres documentos con los recuentos (`README.md`, `AGENTS.md`,
`LO_QUE_PIDE_LA_JUNTA.md`) los compara `test_lista_de_la_junta.py`.

**Los cuatro defectos de la revisión del 07/10** están cerrados, cada uno con su comprobación: el cuaderno
vacío no se contradice, los importes no se parten a ningún ancho, las capturas son de la explotación de 64
tierras, y la comprobación de pantalla mira la identidad y no una palabra suelta.

---

## 2. Lo que queda, y **la decisión que hay que tomar**

### 2.1 «Fichas únicas» — es una decisión, no un arreglo

Hoy **la misma tierra se puede mirar en cuatro pantallas**:

| Pantalla | Dónde se entra | Qué enseña |
|---|---|---|
| **El panel** de la fila | `elegir-fila`, en la lista de tierras (ordenador) | nombre, referencia, hectáreas y un botón a su historia |
| **Su historia** (`#/tierras/<id>/historial`) | el botón del panel, o la tarjeta en el móvil | qué hay hoy, los trabajos hechos, lo previsto, los costes |
| **Su cultivo** | `cultivo-decir` / «VER EL CULTIVO» | lo sembrado, para decir o corregir el cultivo |
| **Sus versiones** (`#/tierras/<id>/versiones`) | su dirección | la comparación entre campañas (contrato, §137-144) |

**Lo que ya se ha hecho** para que no se contradigan: el móvil abre la ficha (no el cultivo) y hay una
prueba que exige que el panel y la ficha digan **el mismo nombre y la misma superficie**.

**La decisión que falta**: **cuál de esas cuatro es *la* ficha de una tierra** y qué entra dentro. Las
opciones honestas son dos:

- **(a) La historia es la ficha** y las otras tres se convierten en **secciones suyas** (el panel desaparece
  como pantalla propia: al elegir una fila se abre la ficha; «decir el cultivo» y «versiones» pasan a ser
  bloques dentro). Es lo que pide el encargo y lo que menos pantallas deja.
- **(b) El panel es la ficha** y la historia es una sección suya. Deja la lista más rápida de usar (se ve
  la tierra sin salir de la lista) pero obliga a que la historia quepa en un panel lateral.

Lo que **no** se puede seguir es lo de ahora: cuatro sitios que enseñan trozos distintos del mismo bicho.
Y antes de tocar nada: **hay que decidir si las «versiones» (la comparación anual) se construyen** — el
contrato las pide y no existen (`versiones_api.py` no tiene variedad, siembra, cosecha, rendimiento ni
coste por campaña).

**La decisión está tomada (07/10/2026): opción (a)** — **la historia es la ficha**. Elegir una tierra en
la lista lleva a su ficha, y el panel lateral deja de ser una pantalla propia.

**Estado del plan, por pasos** (para no volver a leerlo entero):

| Paso | Estado |
|---|---|
| 2. La ficha tiene todo lo que tenía el panel (la **referencia oficial** era lo único que faltaba) | **hecho** (`8a7f18d`) |
| 1. La lista lleva a la ficha **de un paso**: el **nombre** de la tierra abre su ficha (`tierra-historia`) | **hecho** (`8df361a`), en su forma segura: el resto de la fila sigue marcando y el panel no ha desaparecido |
| 3. El panel: **se queda como vista previa** (enseña nombre, hectáreas, referencia y el botón a la ficha) | **decidido así**; no hay que borrar nada ni cambiar pruebas, porque no se quita |
| 4. El recorrido: abrir la ficha es **un paso** | **hecho** en el guion (`abrir_el_historial` intenta primero el nombre y deja los dos pasos como salida) |
| 5. El cultivo y las versiones, desde la ficha | **hecho** (los dos botones están en la ficha, medidos) |

**Lo que queda, entonces, es una sola cosa de este rediseño**: la **búsqueda global** (§2.3), que es
función nueva. Y del encargo, las **medidas del despacho** (§2.4), que siguen sin aplicarse a propósito.

**Lo que hay que hacer, por orden, y con lo que hay que tener cuidado:**

1. **`elegir-fila` lleva a la ficha** (`app.js`, el manejador de clics): en vez de solo marcar la fila y
   pintar el panel, abre `#/tierras/<id>/historial` (que ya existe y funciona: `abrirLaHistoriaDeUnaTierra`).
   **Cuidado**: la lista de tierras es la pantalla más usada y **la que conserva el filtro y el «por dónde
   iba»**; el recorrido automático comprueba las dos cosas, así que se verá en rojo si se rompen.

   **Lo que hay que tocar, ya localizado** (para que la vuelta siguiente no lo busque):

   - `app.js`, en el manejador de clics: hoy hay una rama para `elegir-fila` que marca la fila y pinta el
     panel; tiene que acabar llamando a `abrirLaHistoriaDeUnaTierra(id)` —la misma función que usa el botón
     «su historia» del panel—. **Si el panel se queda como vista previa, hay que decidir si la fila abre la
     ficha o solo marca**: las dos cosas a la vez no pueden ser.
   - **Las pruebas que afirman lo de ahora** y hay que cambiar **diciendo por qué** (no borrar):
     `tests_js/interfaz.test.js` → «elegir una tierra la enseña en el panel de al lado, sin salir de la
     página» y todo lo que lee `tablaDeTierrasPedida().panel`; y `tests_js/react.test.js` si compara las
     acciones del panel.
   - **El recorrido automático** (`scripts/comprobar_el_recorrido.py`): la función `abrir_el_historial`
     da **dos pasos** (la fila y el botón del panel). Con (a) será **uno**: la fila. Y su comentario
     explica por qué son dos, así que hay que cambiarlo también.
   - **Y el filtro al volver**: `recordarPorDondeIba` / `volverAdondeIba` ya lo conservan por la dirección;
     el recorrido lo comprueba, así que si la ficha se abre de otra forma se verá.
2. **Lo que el panel enseñaba de más, a la ficha**: nombre, referencia SIGPAC y hectáreas. Hoy la ficha
   enseña nombre y superficie (la superficie se arregló el 07/10); **falta la referencia oficial**.
3. **El panel se queda como vista previa o se quita**: si se quita, hay que borrar sus pruebas y las que
   comprueban que elegir una fila lo pinta (`tests_js/interfaz.test.js`: «elegir una tierra la enseña en
   el panel de al lado…» y las de su `tabla.panel`). **Se cambian diciendo por qué**, como manda el
   proyecto, no se borran sin más.
4. **Comprobarlo en el navegador**: el recorrido automático (`pytest tests/test_el_recorrido_se_anda.py`)
   ya anda la lista → ficha → trabajo → historial; hay que añadirle el paso «desde la lista se abre la
   ficha» y **quitar** el que hoy pasa por el panel (`abrir_el_historial` da dos pasos: la fila y el botón
   del panel; con (a) será uno).
5. **Y el cultivo y las versiones, como secciones dentro** de la ficha (hoy ya se llega a las dos desde
   ella, que es la mitad del camino).

**Lo que NO hay que hacer**: inventar una pantalla nueva, ni dos fichas a la vez, ni quitar el panel sin
mover antes a la ficha lo que el panel enseñaba (la referencia oficial es lo único que falta).

### 2.2 El eslabón del cultivo: cerrado

Se intentó dos veces y a la segunda se midió: **la aplicación funcionaba y el que estaba mal era el
guion** (`scripts/medir_el_cultivo_desde_la_ficha.py`). El botón está en la ficha, y al pulsarlo lleva a
`#/tierras/<id>/cultivo` con sus cinco campos. En el recorrido se comprueba **que el botón está**, porque
pulsarlo desde ahí hace que el clic caiga en la barra pegajosa: es un problema de colocación del clic del
guion, no del producto.

### 2.3-bis El «defecto» del botón **no era de la aplicación** (medido el 07/10/2026)

Al poner la ruta y el bloque que pinta al llegar por la dirección, el recorrido automático se puso rojo:
«escribir en el cuadro y pulsar BUSCAR no enseña los grupos». Lo apunté como defecto del producto. **No lo
era.**

La medición (`scripts/medir_el_camino_de_la_busqueda.py`, nuevo) **separa el camino del guion**: abre las
tierras, **inyecta** en esa pantalla el cuadro y el botón igual que los pinta la pantalla de la búsqueda, escribe
la tierra de la prueba y **pulsa con un clic de verdad**. Resultado:

```
después de pulsar BUSCAR
  h1: Buscar
  tarjetas (grupos): 1
  texto: … | Tierras | El Alto de la Dehesa Boyal, al lado del p…
=> EL CAMINO FUNCIONA: la pantalla pinta los grupos.
```

Es decir: **el manejador, la petición y la pantalla funcionan de punta a punta**; lo que fallaba era **dónde
aterrizaba el clic del guion** — la misma casa que el botón de «decir el cultivo» (ronda 18), donde también
el culpable era el guion y no el programa. Tercera vez en esta sesión.

**Lo que queda, entonces, es solo la puerta**: el renglón del menú y la dirección. Nada del producto está
roto.

**Y ya está comprobado en el recorrido automático** (07/10/2026), con su salida leída a mano:

```
── Paso 7: La búsqueda global   (dirección: #/tierras/18/historial?…)
  [OK  ] escribir en el cuadro y pulsar BUSCAR enseña los grupos con sus resultados
Comprobaciones: 18   Fallos: 0
Hallazgos: 1  · la búsqueda global funciona de punta a punta … pero todavía no tiene puerta
```

El paso **inyecta** el cuadro y el botón (como se hizo con el cultivo en la ronda 18) porque la pantalla no
tiene puerta a la que agarrarse; **el día que la tenga, el paso usará la suya en vez de inyectar nada**, y
ese hallazgo desaparecerá solo.

**Lo que hay que mirar, por orden** (no se ha podido investigar todavía, y el motivo es el de abajo):

1. **Si la petición sale y con qué**. `pantallaBuscar()` llama a `/api/buscar?texto=…` con `apiJson`; hay que
   ver si esa llamada se hace, si contesta y **qué trae**.
2. **Si lo que trae llega a la pantalla**: `montar(() => pantallaDeLaBusqueda({ …, resultado }))` — el
   `resultado` tiene que ser el del servidor, no `null` por un `catch` que se lo come.
3. **Si la pantalla pinta lo que le llega**: `losGruposDeLaBusqueda` está probado por separado (6 pruebas),
   así que si el dato entra, la pintura está cubierta.

**La mitad del servidor ya está descartada** (07/10/2026): una prueba busca exactamente lo que el recorrido
buscaba —los primeros 24 caracteres de un nombre largo— y **el servidor lo encuentra**. Así que el defecto
está en el camino de la pantalla.

**Y hay una sospecha concreta, que ya ha pasado dos veces en esta casa**: que **el clic no llegue al botón**
y caiga en otra cosa. En la ronda 18 pasó con el botón de «decir el cultivo» (el clic caía en la barra
pegajosa de arriba) y en la ronda 8 con el de «mis cosas» (caía en un elemento oculto en la esquina). Aquí
encaja con lo medido: al pulsar BUSCAR **no aparecía ningún resultado y la dirección dejaba de contener
`buscar`** — que es justo lo que pasaría si el clic hubiera acabado en el botón APUNTAR de la barra
(`ir-inicio`), que lleva al inicio. **Lo primero que hay que hacer, entonces, no es tocar la aplicación:
es mirar dónde aterriza el clic** (con el guion de medición, como se hizo con el cultivo).

**Y para investigarlo hace falta la puerta primero**: hoy no hay forma de llegar a esa pantalla (ni por
menú ni por dirección), y sin llegar no se puede pulsar. Así que **el orden es: puerta (renglón e
dirección) → y después este defecto**, que se reproduce solo con el paso del recorrido que ya está escrito.

**No hay que dar la búsqueda por terminada mientras esto no se arregle**, aunque las tres piezas (servidor,
palabras, pantalla) estén cada una en verde: el camino de punta a punta es el que decide si una función
existe.

### 2.3 La búsqueda global: la puerta está hecha; falta la caja

**Lo que ya está** (07/10/2026): `GET /api/buscar?texto=` — **los cinco grupos, probados** (14 pruebas en
`tests/test_la_busqueda_global.py`): **tierras** (nombre y referencia oficial), **gastos** (concepto, con
su importe), **personas** (con su teléfono o NIF), **máquinas** (nombre y matrícula) y **papeles** (título,
con su tipo). Los resultados van **por grupos**, que es la forma pensada para crecer sin rediseñar.

Tres reglas que se comprueban **en cada grupo, sin excepción**: el cotejo es **el mismo** que el del
buscador de tierras (`_como_se_busca`: sin tildes, en minúsculas y con los espacios de dentro juntos); con
**una letra** no se busca y se dice por qué (`muy_corto`); y —lo más importante aquí— **no sale nada de
otra explotación**, ni tierras, ni gastos, ni personas, ni máquinas, ni papeles.

**Lo que falta: la caja en la cabecera.** Es una pantalla, y por eso no se ha hecho al final de una sesión
larga. Lo que hay que hacer, con el patrón que ya existe en la casa:

1. **El cuadro y su botón, en la cabecera del armazón.** El patrón es el del buscador de tierras: un
   `input` con su `id` y un botón con su `data-accion` (aquí `buscar`), que es lo que lee el manejador de
   clics de siempre. En el móvil, dentro del menú (donde ya está todo).
2. **Una pantalla de resultados**, con **dirección propia** (`#/buscar?texto=…`), por el mismo motivo que
   la ficha de una tierra la tiene: que recargar deje al agricultor donde estaba y que el enlace se pueda
   guardar. Se registra en `web/react/rutas.js` y en las dos tablas de `app.js` (la de direcciones y la de
   módulos, con el módulo de «Inicio» marcado).
3. **Las palabras, del servidor** (`textos.py`): el rótulo del cuadro, su pista («escribe al menos dos
   letras»), el título de la pantalla, el nombre de cada grupo y las dos frases de «no hay nada» y «no se
   ha buscado». Nada escrito a mano en el componente.
4. **Y comprobarlo donde se ve**: un paso nuevo en el recorrido automático
   (`scripts/comprobar_el_recorrido.py`) que escriba en el cuadro, pulse, y exija ver un grupo con su
   resultado y la dirección `#/buscar`.

**Lo que falta: el cable que une la pantalla con la aplicación.** La pantalla ya está
(`web/react/pantallas/buscar.js`, 9 pruebas de JavaScript que la dibujan con React) y sus palabras también.
Faltan los **seis sitios** donde se registra una pantalla, y están localizados mirando cómo está hecha
`tierra_versiones`, que es el modelo exacto (una pantalla con dirección propia, que cuelga de un módulo):

| Dónde | Qué |
|---|---|
| `web/react/rutas.js` (~L103, junto a `tierra_versiones`) | `{ clave: "buscar", patron: ["buscar"] }` |
| `app.js` (~L821, con las demás) | `PantallaBuscar: "buscar"` — de qué módulo cuelga |
| `app.js` (~L977) | el bloque que prepara sus datos (llamar a `/api/buscar` con el texto de la dirección) |
| `app.js` (~L1235) | el bloque de su **dirección** (`#/buscar?texto=…`), que es lo que hace que recargar deje al agricultor donde estaba |
| `app.js` (~L1565) | y la tabla del otro lado (la que dice en qué módulo marcar el menú) |
| `app.js` (`MODULOS`, grupo `inicio` o `ajustes`) | **el renglón del menú**, con su acción, para que se llegue a ella sin escribir la dirección |
| `app.js` (manejador de clics) | `if (nombre === "buscar") return pantallaDeLaBusqueda(…);` — y así el guardián de los botones ve su dueño |

**Y la comprobación, que no se puede saltar**: un paso nuevo en `scripts/comprobar_el_recorrido.py` que
escriba en el cuadro, pulse BUSCAR y exija ver un grupo con su resultado y la dirección `#/buscar` — y
correrlo con `pytest tests/test_el_recorrido_se_anda.py`, que es donde vive. (Ese paso **ya está**: se
apunta como hallazgo mientras falte el cable, y se pone verde solo cuando esté.)

### Lo que falta: **dos** cosas, y no una

**1. El renglón del menú** (`MODULOS`, grupo `inicio`, con `accion: "buscar"` y `texto: "buscar.titulo"`)
y las **cuatro pruebas que fijan el menú en 21 renglones**, que hay que cambiar **con su motivo escrito**.
Se intentó el 07/10/2026 y se revirtió para no dejar el árbol en rojo; esto es exactamente lo que salió,
para no tener que descubrirlo otra vez:

| Prueba | Qué cambia |
|---|---|
| `tests_js/armazon.test.js` → «los renglones del menú son 21, sin repeticiones…» | 21 → **22** (el título de la prueba, L255, y la comprobación, **L256**) |
| `tests_js/armazon.test.js` → «con los 21 renglones de verdad, agrupados salen los mismos…» | 21 → **22** (el título, L426, y la comprobación, **L447**) |
| `tests_js/armazon.test.js` → «el lector de las tablas de `app.js` lee lo que dice leer» | **L562**: `MODULOS.length` 21 → **22** (y su mensaje) |
| `tests_js/interfaz.test.js` → «el armazón se monta con la finca, el año, la cuenta y todos los módulos» | la lista de claves gana `"buscar"` **detrás de `"panel"`**, y el grupo `inicio` pasa de **1 a 2** |

**Y una más que hay que devolver al ponerlo**: `MODULO_DE_LA_PANTALLA` en `app.js` tiene que volver a llevar
`PantallaBuscar: "buscar"` — se quitó el 07/10/2026 **a propósito**, porque sin renglón en el menú el guardián
dice «estas pantallas marcan un módulo que no está en el menú: ['buscar']». Con el renglón puesto, vuelve.

**Y lo que NO hay que hacer** (ya está escrito arriba, pero se repite porque es el error fácil): registrar la
pantalla **sin** el renglón del menú —queda inalcanzable, como pasó con la historia de una tierra y con sus
versiones— o hacerlo **sin** el paso del recorrido, que es lo único que demuestra que funciona al pulsar.

**Y una cosa más, medida el 07/10/2026: el renglón del menú y la dirección son EL MISMO ARREGLO.** No se
pueden hacer por separado, y ya se probó:

- La pantalla **no escribe su dirección** al buscar (medido con el guion: la dirección se queda en
  `#/tierras?…` aunque los grupos salen).
- El motivo: para traducir de pantalla a dirección, `apuntarLaDireccion` usa las tablas de traducción de
  `app.js`, y la entrada `PantallaBuscar: "buscar"` **se quitó a propósito** el 07/10/2026 porque marcaba un
  módulo que no estaba en el menú — lo cazó el guardián: «estas pantallas marcan un módulo que no está en el
  menú: `['buscar']`».
- Así que **mientras no haya renglón, no hay módulo; y sin módulo, la pantalla no puede escribir su
  dirección**. Poner el renglón (y devolver esa entrada a la tabla) arregla **las dos puertas de una vez**.

**Ya está comprobado y en verde** (para no repetirlo): la búsqueda funciona de punta a punta —se busca, se
pide al servidor y se pintan los grupos— comprobado en el recorrido automático **inyectando su cuadro y su
botón**, porque todavía no tiene puerta. Su salida, leída a mano:

```
── Paso 7: La búsqueda global
  [OK  ] escribir en el cuadro y pulsar BUSCAR enseña los grupos con sus resultados
Comprobaciones: 18   Fallos: 0
```

**2. Su dirección propia** (`#/buscar?texto=…`), y son **cinco** ediciones, no tres (mirado el 07/10/2026
en el código, con `tierra_versiones` como modelo):

| Dónde | Qué |
|---|---|
| `web/react/rutas.js` | `{ clave: "buscar", patron: ["buscar"] }` |
| `app.js`, el bloque que arma **los parámetros de la dirección** (≈L977, junto a `tierra_versiones`) | que el texto buscado viaje en la dirección, leyéndolo del estado |
| `app.js`, el bloque que pinta **cuando se llega por la dirección** (≈L1235) | `if (clave === "buscar") return …` con el texto de la dirección |
| `app.js`, `pantallaBuscar()` | que **acepte el texto como parámetro**: hoy lo lee del cuadro (`#buscar_global`), y al llegar por una dirección **el cuadro todavía no existe** |
| `app.js`, `pantallaBuscar()` | y que **guarde en el estado** lo que se ha buscado ✅ *(hecho)* |

**Y esto es lo que se ha medido, que cambia el sitio del arreglo** (07/10/2026): la dirección **no se escribe
desde la pantalla**. `montar()` solo pinta; la dirección la escribe **`apuntarLaDireccion(...)`**
(`app.js` ≈L1010), que arma sus parámetros con `parametrosDeLaPantalla(clave)` (≈L948) y usa
`escribirLaDireccion` + `history.pushState` — **y a propósito con `pushState` y no `location.hash`**, porque
escribir el fragmento a mano dispara `hashchange` y volvería a abrir la misma pantalla en un bucle (está
comentado en el código, y es de esas cosas que no hay que «arreglar»).

Por tanto, **lo que falta no es un bloque de parámetros**: es que **la búsqueda pase por ese camino**. Dos
formas, y hay que elegir mirando cómo lo hacen las pantallas que ya se enlazan:

1. que el manejador de `buscar` llame a `apuntarLaDireccion(...)` después de buscar; o
2. que la búsqueda navegue como navega el resto (por donde entran las demás pantallas con dirección).

Y **se probó y no vale** (medido, y por eso no está en el código): añadir un bloque
`if (clave === "buscar") parametros.texto = …` en `parametrosDeLaPantalla` **no cambia nada**, porque esa
función solo se ejecuta cuando la navegación la llama, y pintar una pantalla no la llama.

**No es un adorno**: sin ella, recargar la página deja al agricultor fuera de su búsqueda, y el enlace no se
puede guardar ni mandar — que es exactamente el defecto que este proyecto ya ha tenido dos veces por botón
(la historia de una tierra y sus versiones) y una tercera por dirección (la búsqueda, hoy).

**Lo que ya está hecho y no hay que repetir**: la puerta del servidor (`GET /api/buscar`, cinco grupos, 17
pruebas), sus palabras (`textos.py` + `/api/interfaz`, atadas por una prueba), la pantalla
(`buscar.js`, 9 pruebas que la dibujan con React), su `pantallaBuscar()` y su manejador, y su registro
donde el proyecto lo exige (lista de React, caché del service worker y la guía `docs/REACT.md`).

La cabecera del encargo la pide. **No hay ninguna puerta en el servidor para eso**: comprobado, lo único
que existe es la búsqueda del SIGPAC (`parcelas.py:933`). Hace falta un endpoint que busque en tierras,
gastos, papeles, personas y máquinas a la vez, con su forma de decir «no hay nada» y su permiso por
explotación. Un buscador de mentira sería peor que no tenerlo.

### 2.3 Lo que **no** hay que rehacer

- El armazón (menú, contexto, navegación) está hecho y medido a los cuatro anchos.
- El recorrido está atado a la suite: **no se puede romper sin que salga en rojo**.
- Las medidas del despacho del encargo (menú 240 px, cuerpo 16 px, títulos 24/20, cifras 26, controles 44)
  **siguen sin aplicarse a propósito**: el encargo dice que hay que acordarlas y actualizar `DESIGN.md` y
  sus pruebas antes de tocarlas, y el campo se queda a 18 px.

---

## 3. Cómo se comprueba todo (los comandos, en orden)

```powershell
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests -q          # 4.583 (incluye el recorrido, con servidor y Chrome)
node --test "tests_js/*.test.js"                        # 1.065

# Y las comprobaciones de navegador, contra un servidor de pruebas (nunca el 8000):
$env:CUEDIGITAL_DATABASE_URL="sqlite:///$env:TEMP\cd-prueba.db"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8029   # en otra ventana
..\.venv\Scripts\python.exe scripts\comprobar_el_recorrido.py http://127.0.0.1:8029
..\.venv\Scripts\python.exe scripts\comprobar_el_armazon.py   http://127.0.0.1:8029
..\.venv\Scripts\python.exe scripts\mirar_pantallas.py        http://127.0.0.1:8029
..\.venv\Scripts\python.exe scripts\comprobar_la_ficha_en_el_movil.py http://127.0.0.1:8029
```

**Nunca** contra `backend/cuedigital.db` (la base del agricultor) ni contra el puerto 8000.
