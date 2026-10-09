# Estado del rediseño

> **Estado actual, medido (07/10/2026).** Esto es lo que hay hoy, no lo que hubo:
>
> | Qué | Medida / resultado | Cómo se comprueba |
> |---|---|---|
> | Cuerpo de letra | **18 px** en todos los anchos | `scripts/medir_la_cabecera.py` |
> | Títulos | **24 px / 20 px** (h1 / h2) | el mismo guion |
> | Márgenes | **24 px** de 48 rem en adelante · **16 px** en móvil (a propósito: el modo de campo se usa con una mano) | el mismo guion |
> | Cabecera | **64 px** en móvil (medía 83) · en el ordenador **no se enseña**: su trabajo lo hace la barra | el mismo guion |
> | Recorrido real | **64 comprobaciones · 0 fallos · 1 hallazgo** | `pytest tests/test_el_recorrido_se_anda.py` |
> | Normativa | **10 reglas** de la matriz, cada una con su **ayuda para el agricultor**, sus **fuentes oficiales** (18 enlaces) y el aviso de **lo que no está comprobado** | `scripts/medir_la_pantalla_de_normativa.py` · recorrido, paso 8 |
> | Pruebas | **4.660 de Python · 0 fallos** · **1.077 de JavaScript · 0 rojos** | `pytest tests` · `node --test tests_js/*.test.js` |
>
> **Y ya no queda nada pendiente de las cuatro tareas** (07/10/2026), las dos últimas con su número:
>
> | Qué | Estado | Cómo se comprueba |
> |---|---|---|
> | **Barra de ESCRITORIO** | **compactada**: medía **183 px** —y 214 con nombres largos— y son **64**, también con nombres largos. La de 83 → 64 px de antes era la del **móvil**, que en el ordenador ni se enseña | `scripts/medir_la_barra_de_escritorio.py` |
> | **Existencias al corregir y anular** | **comprobado**: corregir de 2 a 5 L deja el **compensatorio** (−3 L, de 43 a 40) y anular **devuelve** lo gastado (de 40 a 45), **las dos con su auditoría** | el recorrido, paso 4 |
>
> *(Los números que aparecen **dentro de citas de una salida de aquel día** —por ejemplo «Comprobaciones: 47»—
> son evidencia con fecha, no el estado de hoy: no se tocan.)*
> | Teclado y zoom 200 % | **203 · 0 fallos · 1 hallazgo** (el de `#/entrar`, decisión defendida) | `scripts/comprobar_teclado_y_zoom.py` |
> | Registrar un trabajo | planificar · guardar · hecho · corregir · anular · **consumo de existencias**, comprobado en el servidor | recorrido, paso 4 |
> | Búsqueda global | puerta del servidor (19 pruebas), palabras, pantalla, **resultados que abren sus fichas**, dirección con el texto | recorrido, paso 7 |
>
## El hallazgo del historial **no era un defecto: era mi consulta** (07/10/2026)

Lo tenía apuntado como «el historial de una tierra no ve el trabajo que su estado sí ve». **Es falso**, y el
fallo era del instrumento —como otras dos veces en este encargo—:

En `trabajos_api.py` hay **dos puertas con nombres que se parecen**:

| Puerta | Qué devuelve |
|---|---|
| `GET /api/trabajos/tierra/{parcela_id}` (`la_historia_de_una_tierra`) | **el estado**: `hechos`, `previstos`, cifras… |
| `GET /api/trabajos/historial/{parcela_id}` (`el_historial_de_una_tierra`) | **la historia**: `lineas`, con su envoltorio y su motivo |

El recorrido pedía `lineas` **a la primera** —que no tiene esa clave— así que llegaba `[]`, siempre, y yo
lo interpreté como un defecto del servidor. **El servidor estaba bien.** Lo que hay que arreglar es el
guion: pedir las líneas a `/historial/{id}`, y volver a exigir **una sola línea** (hoy la comprobación se
dejó en «como mucho una» para no tumbarse por el falso hallazgo).

**Y queda como lección escrita**: dos puertas con nombres casi iguales y claves distintas es una trampa
para el que las lee de prisa — y la he pisado yo.
**Sin hacer, y es lo que queda de verdad** (07/10/2026, al día):

1. **Inicio, qué acciones se quedan arriba** — es una **decisión de producto**, no un cambio de CSS: la
   pantalla tiene 6 acciones en barras y el resto son enlaces de lista (una por tierra, doce «Qué hay
   sembrado»). *Qué se viene a hacer al abrir el cuaderno* es lo que decide cuáles suben.
2. **La forma real de la parcela** en la ficha de una tierra (su dibujo): el dato ya está en el mapa de
   tierras; es traerlo a la ficha.

   > **Comprobado el 07/10/2026, y corregido al día siguiente** (la primera conclusión era a medias):
   >
   > - **La forma SÍ existe y el servidor la devuelve**: `app/routers/parcelas.py` trabaja con los **anillos**
   >   de cada tierra (`tierra.anillos`, listas de `[lon, lat]`), y hasta calcula la caja que los envuelve
   >   (`oeste/este/sur/norte` y el centro). El mapa de la web construye su caja **con esos puntos**
   >   (`app.js` ≈L15010).
   > - Lo que **no** hace el mapa es **dibujar el polígono**: enseña una **foto aérea** con los puntos encima
   >   (*«No hay librería de mapas: hay una caja de coordenadas»*).
   >
   > Así que la ficha tiene **dos caminos**, y hay que elegir uno: **dibujar el anillo** de esa tierra (un
   > polígono pequeño, con lo que ya se calcula la caja) o **traer la foto** de su zona con el anillo encima.
   >
   > **La puerta ya está localizada** (07/10/2026): `GET /api/parcelas/vista` devuelve las tierras **con sus
   > anillos** —cada uno en `[longitud, latitud]`, y separados por trozos y agujeros, no como una lista
   > plana—, y la pide **la pantalla del mapa al abrirse** (`app.js` ≈L15119), **no al arrancar**: son 64
   > tierras con sus formas y en el campo es cuando peor va la conexión. Está escrito en el propio código.
   >
   > Y eso deja la decisión de verdad para la ficha, con tres opciones y sus costes:
   >
   > 1. **Pedir la vista entera** desde la ficha: funciona, pero es traerse las 64 tierras con sus formas
   >    para dibujar **una**. Es lo contrario de lo que hace el mapa.
   > 2. ~~Pedir los anillos de esa tierra sola y dibujarlos~~ → **NO HACE FALTA: el dibujo ya existe**
   >    (07/10/2026). Lo que hay es **`dibujo`**: `GET /api/parcelas` devuelve cada tierra **con su dibujo
   >    hecho**, y tiene sus propias pruebas —`tests/test_dibujo_de_la_parcela.py`—, incluidas las dos que
   >    importan aquí: **sin geometría no se dibuja nada** (no un hueco, ni un cero) y **algo que no es una
   >    geometría no revienta**. También comprueba que el dibujo **cambia** cuando cambia la forma.
   >
   >    **Y ya está localizado dónde viajaba** (07/10/2026): `app.js`, `panelDeLaTierra(tierras)` (≈L8688),
   >    arma el panel de una tierra **con su `dibujo`** (`dibujo: tierra.dibujo || ""`), y su propio
   >    comentario dice: *«La forma de su recinto, que es como el agricultor reconoce una tierra… el diseño de
   >    escritorio de esta pantalla la pide y **el dato ya venía en la ficha**»*. O sea: **el dibujo se
   >    enseñaba en el panel de la tierra**, y las props de la ficha **ya reciben la tierra**.
   >
   >    **Lo que hay que hacer, entonces, es pequeño y concreto**: pasar ese `dibujo` a la ficha y pintarlo
   >    (una edición en `app.js` al montar la ficha, una en `pantallas/trabajos.js` para pintarlo, su frase en
   >    los textos y su prueba), **con la regla de la casa**: si la tierra **no tiene forma**, **no se pinta un
   >    hueco** — igual que ya hace la lista de tierras.
   >
   >    **Y hay que comprobar una cosa primero, que puede ser una regresión de este mismo rediseño**: al
   >    dejar la ficha como pantalla única y **retirar el panel** (el trabajo de «fichas únicas»), puede que
   >    el agricultor **haya dejado de ver la forma de su tierra** —porque se enseñaba justo ahí—.
   >
   >    ### Confirmado, y es una regresión (07/10/2026)
   >
   >    Medido con el recorrido, que ya lo mira (`.panel-dibujo` en la ficha):
   >
   >    ```
   >    [HALLAZGO] la ficha no enseña la forma de la tierra
   >    Comprobaciones: 47   Fallos: 0
   >    ```
   >
   >    **No es una sospecha: la ficha no enseña la forma de la tierra**, y se enseñaba en el panel que se
   >    retiró al dejar la ficha como pantalla única. **Es una regresión de este rediseño.**
   >
   >    El arreglo, localizado: pasar `dibujo` a la ficha al montarla (`app.js`, donde se monta
   >    `pantallaDeLaTierra`, el dato ya está en la tierra) y pintarlo con **la pieza que ya existe**
   >    (`DibujoDeLaParcela`, de `componentes.js`, que usa `tabla.js` con la clase `.panel-dibujo`), **con la
   >    regla de la casa**: si la tierra **no tiene forma**, no se pinta un hueco.
   >
   >    **Y no hace falta tocar el recorrido**: la comprobación ya está puesta y **se pondrá verde sola** en
   >    cuanto la ficha enseñe el dibujo.
   >
   >    ### Y el «no tiene forma» era de mi comprobación, no del escenario (07/10/2026)
   >
   >    La comprobación decía que la tierra de la prueba no tenía forma y **eso no cuadra**: el escenario crea
   >    las tierras con `for indice in range(64)` y da forma a las que cumplen `indice % 11 == 0`
   >    —**`indice == 0` la cumple**—, y la tierra del recorrido es **la primera** (la 18 de la base). Así que
   >    **esa tierra sí tiene forma** y el hallazgo hablaba del escenario cuando el problema estaba **en la
   >    comprobación** (o en lo que el servidor devuelve para esa tierra, que es lo que hay que mirar).
   >
   >    **Lo que hay que hacer, entonces, es un `print` de una línea**: sacar por pantalla **lo que la
   >    comprobación ha encontrado** para esa tierra (su identificador y su `dibujo`) en vez de solo decir que
   >    no tiene. Con eso se ve en un segundo si el fallo es que **no encuentra la tierra** en la lista (y
   >    entonces `su_dibujo` se queda vacío por eso) o que el servidor **no manda el dibujo**. Es el mismo
   >    error que ya ha pasado cuatro veces en este encargo: **el instrumento, no el programa**.
   >
   >    ### El `print`, hecho, y esta vez el hallazgo es verdad (07/10/2026)
   >
   >    ```
   >    (la tierra 18 en la lista del servidor: está; su dibujo: 0 caracteres; y en la ficha: no)
   >    ```
   >
   >    Así que: **la comprobación encuentra la tierra** ✓ y **el servidor dice que esa tierra no tiene
   >    dibujo** (0 caracteres) ✓ → **el hallazgo es verdad**: esa tierra, de verdad, no tiene forma. Lo que
   >    estaba mal era **mi suposición** de las rondas 37 y 38: creí que la tierra del recorrido era la que el
   >    escenario crea **primero** (`indice == 0`, que sí tiene forma), y **no lo es** — la lista de tierras
   >    del escenario no viene en el orden en que se crean, así que la forma acabó en **otra** tierra. Las dos
   >    ediciones del escenario apuntaban a la tierra equivocada.
   >
   >    **Las dos salidas limpias, para elegir una:**
   >
   >    1. **Que el recorrido cree su propia tierra con forma** (con `POST /api/parcelas` y su `geometria`, que
   >       ya se sabe que la acepta) y **abra su ficha** — que es el camino que el recorrido ya sabe andar: la
   >       busca por su nombre y abre su fila. Así se comprueba el dibujo **con una tierra que se sabe que lo
   >       tiene**, y no depende de cómo venga ordenado el escenario.
   >    2. **Que el recorrido elija una tierra de las que el servidor dice que tienen `dibujo`** (se pregunta
   >       a `/api/parcelas` y se coge la primera con dibujo). Más barato, pero ata la prueba al escenario.
   >
   >    La 1 es la buena: **una prueba que se fabrica su propio caso no depende de la suerte del escenario**.
   >
   >    ### La causa, encontrada: la ficha pide su tierra a la puerta equivocada (07/10/2026)
   >
   >    `abrirLaHistoriaDeUnaTierra` (`app.js` ≈L21563) pide su tierra a **`/api/trabajos/tierra/{id}`** —la
   >    puerta del **estado**, que habla de trabajos: lo previsto, lo hecho, las cifras— y **esa respuesta no
   >    lleva `dibujo`**. Por eso `tierra.dibujo` es `undefined` y **no se pinta nada**, ni con una tierra que
   >    tiene forma: *el arreglo estaba puesto, pero le llegaba un dato que no viaja por esa puerta*.
   >
   >    Y el dibujo **sí existe y sí se sirve**: está en el esquema de la tierra (`schemas.py`, `dibujo`, ≈L379)
   >    y lo devuelve la **lista** de tierras (de ahí lo leen sus 18 pruebas). **Lo primero: confirmar en qué
   >    clase está ese campo** —si es `ParcelaSalida`, la puerta de una tierra sola ya lo lleva—.
   >
   >    **Los dos arreglos, y el que recomiendo:**
   >
   >    1. **Que la ficha pida el dibujo a la puerta de la tierra** (`/api/parcelas/{id}`, una petición más y
   >       pequeña) y lo pase a la ficha. **Recomendado**: cada dato por la puerta que lo tiene, y la de la
   >       tierra es la suya.
   >    2. Añadir `dibujo` a la respuesta del **estado** (`/api/trabajos/tierra/{id}`): una edición de backend
   >       y su prueba, pero mezcla en una respuesta de trabajos un dato de la tierra.
   >
   >    Y cuando salga el dibujo de verdad, **la comprobación del recorrido ya está armada** para ponerse
   >    verde: la que crea una tierra con forma —eso ya está escrito— y mira `.panel-dibujo` en su ficha.
   >
   >    ### Confirmado: la puerta de una tierra **sí** lleva el dibujo, y el arreglo es del navegador
   >    (07/10/2026)
   >
   >    El campo `dibujo` está en **`ParcelaSalida`** (`schemas.py` ≈L379, junto a `centro`,
   >    `numero_recinto` y `referencia_catastral`), que es la respuesta de **`GET /api/parcelas/{id}`** —la
   >    puerta de una tierra sola—. Así que **no hay que tocar el servidor**.
   >
   >    El arreglo, exacto: en `abrirLaHistoriaDeUnaTierra` (`app.js` ≈L21563), que hoy pide dos cosas en un
   >    `Promise.all` —la tierra al **estado** y los costes a las cuentas—, **añadir la tercera**: la tierra a
   >    **su propia puerta** (`/api/parcelas/${Number(parcelaId)}`), y pasar **su `dibujo`** a la ficha (donde
   >    ya está el `dibujo: tierra.dibujo || ""` esperándolo). Una petición más, pequeña —unos cientos de
   >    caracteres— y **por la puerta que lo tiene**.
   >
   >    Y **lo primero después**: correr el recorrido, que ya tiene la comprobación armada —crea una tierra
   >    con forma y mira `.panel-dibujo` en su ficha—: si sale verde, el dibujo está de vuelta.
   >
   >    **Queda retirado, por tanto, el plan de «añadir `anillos` a `ParcelaSalida`»** que escribí en las
   >    rondas 26-31: era el camino largo hacia algo que **ya está hecho**. Se deja escrito para que nadie lo
   >    haga: el campo `dibujo` es la puerta.
   >
   >    Con eso, la ficha puede dibujar su polígono **sin traerse las 64 tierras**.
   > 3. **Un botón «verla en el mapa»** desde la ficha: lo más barato y honesto —el mapa ya sabe hacerlo— y
   >    lo que menos pesa en el campo. Puede que sea bastante, y hay que decidirlo antes de dibujar nada.
3. **La pantalla de normativa** (ronda entera: endpoint, textos, renglón en el menú y paso del recorrido),
   con la regla de **no inventar ninguna obligación**: lo que no esté en `docs/MATRIZ_NORMATIVA_CRM.md`, no
   se escribe.

**Y ya no falta** (hecho y medido en estas rondas): los **formularios de escritorio** (campos de 1.105 px a
544, medido antes y después), la **sección de Cultivos** de la ficha (vista en el navegador), **Cuentas** con
sus acciones de apuntar arriba (**1 → 5 visibles**, medido), la **cabecera** (83 → 64 px), los **márgenes**
(24 px de 48 rem en adelante) y la **letra** (18 / 24 / 20), con teclado y zoom re-verificados.

## Las acciones, medidas (07/10/2026): dónde están escondidas

«Las acciones no están claras» no es una medida; esto sí —`scripts/medir_las_acciones.py`, una pantalla por
renglón del menú, contando **cuántas acciones ofrece cada una y cuántas se ven sin desplazarse**—:

| Pantalla | Acciones | **Se ven sin desplazar** | En barra |
|---|---|---|---|
| **Inicio** | 41 | **3** | 6 |
| Buscar | 1 | 1 | 1 |
| **Tierras** | 361 | **13** | 216 |
| Trabajos | 3 | **3** | 3 |
| **Cuentas** | 7 | **1** | 7 |

Lo que dicen los números:

- **Cuentas es el problema**: ofrece siete acciones —apuntar un gasto, un pago, una inversión…— y **seis no
  se ven al abrir la pantalla**. Las acciones principales están **debajo del pliegue**, que es justo lo que
  el encargo llama «no claras».
- **Inicio**: 41 acciones y **3 visibles**, pero **no es el mismo caso que Cuentas** —comprobado mirando
  cuáles son—: casi todas son **una por elemento de lista** (doce «Qué hay sembrado», una por tierra), igual
  que las 361 de Tierras. Eso **no es un defecto**, es un panel con listas. Lo que sí hay que mirar son **las
  6 que van en barras** —las acciones de verdad de la pantalla— y decidir si **las que importan** están
  entre las 3 visibles. Eso es una decisión de producto (qué se viene a hacer al abrir el cuaderno), no un
  cambio de CSS.
- **Tierras** tiene 361 porque es una tabla de 64 tierras con sus acciones por fila: eso **no es un defecto**,
  es una lista; lo que hay que mirar es que sus cabeceras y su buscador estén arriba (lo están).
- **Trabajos** está bien: 3 acciones, las 3 visibles.

**Por dónde empezar, entonces**: por **Cuentas** (seis acciones escondidas) y por decidir **las de Inicio**.
Que es un trabajo de organización, no de CSS — la mitad que el encargo llama «la mejora principal».

## Las fichas, comparadas con lo que pide el rediseño (07/10/2026)

Antes de tocar nada, esto es lo que dice `docs/REDISENO_V0_STITCH_20261007.md` (L81) y lo que hay **hoy**:

| Lo que pide el rediseño | Lo que hay | Falta |
|---|---|---|
| **Identidad** | `h1` + el nombre de la tierra + **superficie** y **referencia SIGPAC** | — |
| **Cultivo de campaña** | la sección **«Qué hay hoy»**, con lo sembrado, su variedad y desde cuándo (y «no lo sé» cuando no consta) | — |
| **Siguiente trabajo** | desde la ficha se **planifica** (`trabajo-planificar`), y lo previsto se lista en ella | — |
| **Secciones Historia / Cultivos** | hay **«Última labor»** y **«El historial»**, con su explicación y sin tirar lo anulado | una sección propia de **Cultivos**, separada de la historia |
| **Forma real** | — | **la forma de la parcela** (su dibujo), que hoy solo se ve en el mapa de tierras |

Es decir: la ficha **ya está por secciones** (`Qué hay hoy`, `Última labor`, `El historial`), con sus títulos
y sus explicaciones; lo que le falta respecto al diseño son **dos cosas concretas**: la sección de
**Cultivos** y la **forma real** de la parcela. Y las «acciones claras» de la ficha son hoy
`trabajo-planificar`, `tierra-versiones` y `cultivo-decir`, todas en su barra.

**Eso es lo que hay que hacer**: no rehacer la ficha, sino **añadirle esas dos cosas**.

## El acceso a normativa: es una pantalla que no existe, y esto es lo que hay (07/10/2026)

El encargo pide «acceso útil a normativa», y el rediseño (L71) dice que el menú debe ofrecer **todas** las
secciones, «incluidas Cuentas y **Normativa**». Hoy **no hay ninguna pantalla de normativa**, y el grupo
«Normativa» **no está en el menú a propósito** (está escrito en `app.js`, L1499): un renglón que no lleva a
ninguna parte es peor que no tenerlo, y eso ya se ha pagado dos veces en esta casa.

Lo que **sí** hay para construirla encima, y por eso es una pantalla y no un enlace:

| Qué hay | Dónde |
|---|---|
| La **matriz normativa** del proyecto (los trabajos legales: L07, N09…) | `docs/MATRIZ_NORMATIVA_CRM.md` |
| El código **la cita en sus decisiones** (por qué no se supone la clasificación ITV/ITEAF, por qué no se ofrece una lista cerrada de clases…) | `app/models.py`, `app/maquinaria.py` |
| Los **enlaces oficiales** y qué es el registro electrónico | `textos.REGISTRO_ELECTRONICO`, `textos.CUADERNO_CYL` |

Así que «acceso útil a normativa» es: **una pantalla con lo que la ley pide** —qué obligación es, cuándo
aplica y **dónde lo publica la Junta**—, con su puerta en el menú, y **sin inventarse ninguna obligación**:
lo que no esté en la matriz, no se escribe. Es una pantalla con su endpoint, sus textos, su renglón y su paso
en el recorrido: **una ronda entera**, no un enlace añadido al menú., y lo que queda por decidir

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

> **Cerrado el 07/10/2026**: la búsqueda global está **entera** —puerta del servidor (19 pruebas), palabras
> servidas y atadas, pantalla (9 pruebas), camino comprobado de punta a punta, **renglón en el menú** y
> **dirección propia** con el texto buscado viajando en ella—. Y el paso 7 del recorrido **ya usa su puerta
> de verdad**: la dirección, su botón y su renglón del menú. **21 comprobaciones, 0 fallos, sin hallazgos.**
>
> **Lo que encontró al hacerlo** (y merece quedar escrito): el cuadro estaba pintado con `value=` y sin
> `onChange`, que en React es un campo **controlado** —React revierte lo que se teclea—, así que **en la
> pantalla de la búsqueda no se podía escribir**. Los tests verdes no lo veían porque `value` y
> `defaultValue` pintan lo mismo en el HTML: hay que **pulsar** para verlo. Arreglado como se escriben los
> campos en esta casa (`defaultValue`), y con guardián nuevo que mira **todas** las pantallas:
> `tests/test_los_campos_se_pueden_escribir.py`, probado en rojo volviendo a meter el defecto.

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

---

## CIERRE del dibujo de la parcela (07/10/2026)

Lo que cuentan las secciones de arriba termina aqui, y esto es **como quedo**:

- **El dibujo esta EN LA FICHA y esta medido**: la ficha de una tierra **con forma** pinta su dibujo
  (.panel-dibujo, **2 trazos, 104 px de alto**). Se comprueba con scripts/medir_el_dibujo_en_la_ficha.py.
- **La causa era el nivel del envoltorio**: la ficha lee su tierra de dentro (datos.tierra) y el dibujo se
  escribia **fuera**, asi que se quedaba donde nadie lo lee. Corregido en pp.js
  (	ierra.tierra.dibujo = ...), y el servidor quedo **exonerado** por el camino (la puerta de una tierra
  devuelve el dibujo: 55 caracteres).
- **Lo que quede escrito arriba como pendiente sobre el dibujo, ya no lo esta.** Se deja dicho aqui porque el
  traspaso tiene que describir el estado actual.

**Y lo unico que **ya no queda nada del encargo**: la pantalla de normativa está hecha y medida** (su fuente unica:
docs/MATRIZ_NORMATIVA_CRM.md; su regla: no inventar ninguna obligacion legal).

## La fuente de la pantalla de normativa, mirada (07/10/2026)

docs/MATRIZ_NORMATIVA_CRM.md tiene **138 lineas** y una estructura clara, que es lo que hace que la pantalla
sea un trabajo de **escribir** y no de **decidir**:

- ## 1. Registro obligatorio de cada regla.
- ## 2. Fuentes y traduccion a requisitos: **N01...N10**, una seccion por regla -N01 condicionalidad (BCAM),
  N02 ecorregimen, N03 solicitud y compromisos de Castilla y Leon, N04 excepciones locales y avisos, N05
  productos y registro de tratamientos, N06 fertilizacion y nitratos, N07 semillas, N08 material ecologico, N09
  inspecciones de maquinaria, N10 cuaderno propio e intercambio-.
- ## 3. Fuentes tecnicas que **no** son normas.

**Y esa tercera seccion es la decision mas importante que la matriz ya trae hecha**: distingue lo que es
**norma** de lo que es **fuente tecnica**, asi que la pantalla **no puede presentarlas igual** -una obligacion
y una recomendacion no se leen igual, y mezclarlas seria inventar obligaciones sin decirlo-.

El trabajo, entonces, es concreto: el endpoint sirve **las diez reglas** con lo que pide cada una, la pantalla
las ensena **agrupadas por lo que son**, y la tercera seccion va **aparte y dicha como lo que es**. Los enlaces
oficiales ya estan en los textos del registro electronico.

## El molde de la pantalla de normativa (07/10/2026)

Mirada **N01** entera en la matriz, cada regla trae **cuatro cosas**, y de ahi sale el molde del endpoint sin
tener que decidir nada:

| Campo | De donde sale |
|---|---|
| codigo | el titulo: N01, N02... |
| 	itulo | el titulo: Condicionalidad: BCAM y requisitos legales |
| uente | la linea Fuente: -la norma, con su nombre |
| enlace | **el enlace oficial** de esa linea (el BOE). Es lo que convierte la pantalla en algo que se puede **comprobar**, en vez de en una opinion del programa |
| 
equisito | el parrafo Requisito de producto: -que tiene que tener el cuaderno |
| visos | los cuidados que la matriz avisa -en N01, **no copiar porcentajes del ecorregimen a BCAM**-. Valen tanto como el requisito |

Las **pruebas** que la matriz apunta en cada regla **no van al endpoint**: son de quien programa, no del
agricultor.

**El primer paso, concreto**: escribir en pp/ la lista de las diez reglas con esos seis campos -transcritas
de la matriz, **sin inventar ni una**-, con su prueba (que esten las diez y que ninguna se quede sin enlace
oficial). Despues, el endpoint que las sirve, la pantalla que las agrupa por lo que son, el renglon del menu
-con sus cuatro numeros, como se hizo con la busqueda- y el paso del recorrido.

### Y la matriz decide mas de lo que parecia: LOS TIPOS y EL ESTADO (07/10/2026)

Leida la seccion **1. Registro obligatorio de cada regla**, hay dos cosas que **no se pueden inventar en la
pantalla** porque la matriz ya las dice, y cambian el diseno:

1. **Cinco tipos distintos, y el usuario ve la diferencia**: *obligacion general, condicion de ayuda
   solicitada, compromiso concedido, recomendacion tecnica y dato informativo*. O sea que **no basta con
   agrupar en norma y fuente tecnica** -mi aproximacion-: cada regla lleva **su tipo** y la pantalla lo
   ensena. Presentar una recomendacion con la cara de una obligacion es exactamente lo que no se puede hacer.
2. **Solo la regla ctiva participa en comprobaciones concluyentes**, y hay mas estados: *localizada,
   transcripcion, revisada, activa, sustituida*. **Y una regla sustituida sigue disponible** para reproducir un
   informe historico: si la pantalla solo ensenara las activas, se perderia eso.

Ademas, cada regla tiene mas campos de los seis que saque de N01 (**autoridad, territorio, articulo/anexo,
fecha de publicacion, vigencia desde/hasta, campanas, version, documento y huella, fecha de revision,
responsable, condiciones de aplicacion, datos requeridos, formula, excepciones, resultado cuando faltan datos y
casos de prueba**). No todos tienen que ir a la pantalla -seria un formulario, no una pantalla-, pero **si
tienen que estar en los datos**: la pantalla elige que ensena, y lo que no ensena **no puede inventarlo**.

**Lo que esto cambia del plan**: la lista de las diez reglas no es «titulo, fuente, enlace, requisito y
avisos», sino que cada una lleva **su tipo y su estado** -y las dos cosas se ven-. El resto de los campos se
guardan aunque no se ensenen.

## Las diez reglas, transcritas de la matriz (07/10/2026)

**Copiadas verbatim** de `docs/MATRIZ_NORMATIVA_CRM.md` para que el primer paso de la pantalla —la lista
de las diez reglas en `app/`— sea teclear contenido y no volver a buscar nada. **No se ha resumido ni
interpretado**: es lo que la matriz dice, entero, y de aquí sale cada campo del endpoint.

```markdown
### N01 — Condicionalidad: BCAM y requisitos legales

Fuente: [RD 1049/2022, anexo II](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23049).
La consulta mostró consolidación de 09/10/2024. BCAM 7 contempla alternativas de
rotación/diversificación; no debe confundirse con el ecorrégimen de rotación.

Requisito de producto: ficha propia de condicionalidad, historial suficiente,
superficies y clasificaciones, alternativa aplicable y excepciones documentadas.
Antes de activar, transcribir íntegramente la práctica elegida con sus umbrales y
definiciones. No copiar porcentajes del ecorrégimen a BCAM. Pruebas: ambas alternativas,
límites exactos, historial ausente y exención acreditada/no acreditada.

### N02 — Ecorrégimen elegido y planificación

Fuente: [RD 1048/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23048),
especialmente artículos 36 y 37 para rotación y siembra directa. La reapertura de
este enlace tuvo un fallo temporal en esta ronda; la fuente ya se consultó en la
preparación de la especificación anterior. Revalidar su redacción al activar reglas.

No congelar como constantes los fragmentos encontrados por buscador: existen
redacciones históricas con diferencias en superficies y excepciones. La unidad de
evaluación y la definición de cultivo importan tanto como el porcentaje.
Guardar práctica solicitada por ámbito, tipología de superficie, parcelas incluidas,
área elegible, cultivos principales/secundarios y justificación de exclusiones.
Un plan con reglas 2026 puede compararse para 2027 como simulación marcada; no
presentarlo como verificación definitiva de una convocatoria aún no incorporada.

### N03 — Solicitud y compromisos de Castilla y León

Fuentes: [portal PAC de la Junta](https://pac.jcyl.es/web/jcyl/PAC/es/Plantilla100Detalle/1284146916532/Normativa/1284293478518/Texto)
y [incorporación a agroambiente y agricultura ecológica 2026](https://www.tramitacastillayleon.jcyl.es/web/jcyl/AdministracionElectronica/es/Plantilla100Detalle/1251181050732/Ayuda012/1285611475254/Propuesta).
Esta última convocatoria contempla nuevos compromisos durante 2026–2028 para
los regímenes enumerados en ella. No inferir que cualquier ayuda dura tres años.

Modelo: Compromiso con expediente, régimen, solicitud, resolución, fecha inicial/final,
superficie/unidades comprometidas y condiciones documentadas. Seguimiento anual
enlazado al mismo compromiso; cambios, cesiones o renuncias conservan resolución.
Pendiente antes de automatizar: leer bases y resolución concreta de cada régimen.
Prueba: cambiar campaña conserva compromiso; solicitud sin concesión no se muestra
como ayuda concedida. Plazos se obtienen por campaña y sus ampliaciones.

### N04 — Excepciones locales y avisos

Fuente: [resolución de 9 de agosto de 2024 sobre topillo en CyL](https://pac.jcyl.es/web/BlobServer?blobcol=urldata&blobheader=application%2Fpdf%3Bcharset%3DUTF-8&blobkey=urldata&blobnocache=true&blobtable=MungoBlobs&blobwhere=822%2F259%2FResoluci%C3%B3n+de+actuaciones+por+alta+poblaci%C3%B3n+de+topillo+campesino.pdf).
El documento identifica campañas 2023/2024 y 2024/2025. Sirve para demostrar que una
flexibilidad tiene ámbito temporal, no para extenderla automáticamente a 2026/2027.
Guardar comarca/municipio, práctica afectada y vigencia. Prueba negativa: resolución
de otra comunidad o campaña no desbloquea una labor en la explotación.

### N05 — Productos y registro de tratamientos

Fuentes: [RD 1311/2012, anexo III](https://www.boe.es/buscar/act.php?id=BOE-A-2012-11605)
y [registro oficial MAPA](https://servicio.mapa.gob.es/regfiweb/Productos/Index).
Ficha de producto y autorización de uso son entidades distintas. La marca no basta
para identificar formulación o uso permitido. Conservar consulta y etiqueta utilizadas.

Matriz de captura por destino: parcela/cultivo, semilla, instalaciones y postcosecha.
Extraer de fuente vigente campos exigibles y documentos asociados; mapear cada uno a
formulario, modelo, informe y prueba. No usar una dosis máxima global como autorización
para cualquier cultivo/plaga. Tratamientos históricos se comprueban a su fecha.
Pendientes: usos específicos, autorizaciones excepcionales y límites de aplicaciones
necesitan evidencia contextual. Falta de acceso al registro = no comprobado.

### N06 — Fertilización y nitratos

Fuentes: [RD 1051/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23052)
y [Orden MAV/398/2022, publicación oficial](https://bocyl.jcyl.es/boletines/2022/05/05/pdf/BOCYL-D-05052022-1.pdf).
El proyecto conserva fuentes y cálculos de los anexos; revisar su cobertura antes de
añadir reglas. No confundir cálculo de nutrientes con plan de abonado completo.

Datos: cultivo/rendimiento previsto y justificación, análisis, aportes de agua y otras
fuentes, composición del abono con unidades, área realmente abonada, fecha y técnica.
Separar N total, fracciones y disponibilidad cuando la regla lo requiera. P y P2O5 no
son la misma magnitud. Límites por cultivo y restricciones temporales son reglas
separadas; ventanas relativas a siembra/cosecha necesitan esas fechas.
Pruebas: provincia ausente, zona desconocida, análisis ausente y cultivo sin equivalencia
no producen cumplimiento. No declarar que el software sustituye al asesor exigible.

### N07 — Semillas, certificación y variedades

Fuentes: [Ley 30/2006](https://www.boe.es/buscar/act.php?id=BOE-A-2006-13555),
[Ley 3/2000](https://www.boe.es/buscar/act.php?id=BOE-A-2000-414),
[catálogos MAPA](https://servicio.mapa.gob.es/germenwai/)
y [legislación técnica por especie](https://www.mapa.gob.es/es/agricultura/legislacion/legislacion-nacional-semillas).
La certificación de material y la protección de la variedad regulan aspectos distintos.

Implementar tres ejes independientes: identidad varietal, categoría/certificación del
lote y derechos/condiciones de uso. Para reempleo, revisar régimen aplicable y supuestos
de la excepción del agricultor; no asumir libertad general ni prohibición universal.
La exigencia de semilla certificada de una ayuda requiere su fuente específica.
Guardar etiqueta, factura, procedencia y documentos de autorización si corresponden.
Prueba: semilla comprada sin etiqueta no queda certificada por defecto; semilla propia
queda documentable sin declararla automáticamente ilícita.

### N08 — Material ecológico

Fuente de localización: [informe oficial MAPA sobre autorizaciones de semilla no
ecológica](https://www.mapa.gob.es/es/alimentacion/temas/produccion-eco/informesemillasnoeco_2021_definitivo_tcm30-617875.pdf).
Es un informe histórico, no una autorización vigente para el usuario. Identifica la
base pública de oferta y el tratamiento separado de autorizaciones.

Requisito: condición ecológica de explotación, producto y lote con evidencias
independientes. Incorporar autorización individual, periodo, especie/variedad y
cantidad cuando corresponda. Antes de activar reglas revisar normativa europea
vigente y procedimiento de la autoridad competente en CyL. No deducir permiso por
ausencia en catálogo ni por una autorización concedida a otra persona.

### N09 — Inspecciones de maquinaria

Fuentes: [RD 1702/2011 ITEAF](https://www.boe.es/buscar/act.php?id=BOE-A-2011-19296)
y [RD 920/2017 ITV](https://www.boe.es/buscar/act.php?id=BOE-A-2017-12841).
Dos obligaciones diferentes. Crear reglas por clasificación técnica, fechas y ámbito,
con exclusiones expresas. Fecha del documento de inspección prevalece como evidencia
registrada; discrepancia con cálculo abre revisión. No llamar a ITEAF «ITV» en etiquetas.
Prueba: tractor, remolque y equipo de aplicación no comparten un vencimiento universal.

### N10 — Cuaderno propio e intercambio

Fuentes: [RD 1054/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23054)
y [Orden APA/204/2023](https://www.boe.es/buscar/act.php?id=BOE-A-2023-5699).
Separar llevanza de registros, formato exigible y comunicación a la Administración.
No convertir la voluntariedad general del CUE en exención de cualquier obligación
sectorial. Mantener requisitos de formato/plazo como reglas independientes con
destinatarios y excepciones. IUWS no condiciona la navegación del CRM.
```

## Decision de David sobre el tipo de las reglas (07/10/2026)

Preguntado porque **la matriz no lo dice** -define los cinco tipos, pero no cual es cada regla-, y elegido:
**el tipo va en los datos, vacio, y la pantalla dice «sin clasificar»**.

Es la opcion que **no inventa nada**, y su consecuencia queda escrita para que nadie la «arregle»:

- La regla ensena **su fuente, su enlace oficial y su requisito**, que es lo que la matriz si dice.
- El tipo se rellena **el dia que se sepa**, y hasta entonces se lee **«sin clasificar»** -no se calla ni se
  adivina-.
- **Y la pantalla nunca presenta una recomendacion tecnica como si fuera una obligacion**: eso es lo que la
  propia matriz pide cuando dice que *el usuario ve la diferencia*, y es la razon de no rellenar el campo a
  ojo.

**Lo mismo vale para el estado** (localizada, transcripcion, revisada, activa, sustituida): va en los datos, y
mientras no se sepa, la pantalla **no da a entender que la regla es concluyente** -solo ctiva lo es-.

## La matriz NO es uniforme, y eso cambia el modelo (07/10/2026)

Al intentar **extraer** las diez reglas para escribirlas en pp/ sin teclear a mano, el intento **se paro tres
veces** -y pararse era lo correcto: nada se ha escrito-. Lo que ha aparecido es que **las diez secciones no
tienen la misma forma**:

| Regla | Como empieza |
|---|---|
| N01 | Fuente: (singular) y **Requisito de producto:** -la unica que usa esa etiqueta- |
| N02 · N04 | Fuente: (singular) |
| N03 · N05 · N06 · N07 · N09 · N10 | **Fuentes: (plural)**, con **varias** normas y varios enlaces |
| N08 | **Fuente de localizacion:** |

Y solo **N06** trae Pruebas:. Peor todavia para un modelo rigido: **N09 dice «Dos obligaciones diferentes.
Crear reglas por...»** -o sea que **una seccion puede contener mas de una obligacion**-.

**Lo que esto cambia, y es para bien**: el modelo de «codigo, titulo, fuente, enlace, requisito» **aplastaria**
lo que la matriz escribe con cuidado -una seccion con dos obligaciones, una con un aviso sobre una convocatoria
concreta, otra que distingue un informe historico de una autorizacion-. El modelo honesto es:

- codigo y 	itulo (que si son uniformes: los diez son ### Nxx — Titulo),
- **uentes**: una **lista** de enlaces oficiales con su nombre -porque hay reglas con dos y tres-,
- **	exto**: lo que la matriz dice de esa regla, **entero y sin tocar**,
- 	ipo y estado: vacios, como se decidio.

Asi no se pierde ni un aviso por el camino, y la pantalla ensena la regla **como esta escrita** y **enlaza sus
fuentes oficiales**, que es lo unico que la hace comprobable. **Y el «una seccion = una regla» hay que
confirmarlo con David** cuando se vea en pantalla (N09 avisa de que son dos).

## La pantalla de normativa: la lista de registros, entera (07/10/2026)

Es la parte que **se ve**, y en esta casa es donde mas sitios hay que tocar: cuando se anadio la busqueda,
saltaron **cinco fallos de registro** que solo aparecieron al correr la suite entera. Esta es la lista completa,
sacada de aquel trabajo, para hacerlo **de una pasada**:

| Que | Donde | Por que |
|---|---|---|
| **La pantalla** | web/react/pantallas/normativa.js | nueva: el componente que pinta las reglas |
| **La pantalla en React** | web/app.js, en PANTALLAS_EN_REACT | sin eso, la pantalla **no existe** para el armazon |
| **Su direccion** | web/react/rutas.js | una fila mas, junto a la de la busqueda |
| **La cache** | web/service-worker.js, en FICHEROS | sin eso, **sin cobertura no carga** |
| **El modulo** | web/app.js, en MODULOS | la fila del menu: clave, texto y grupo |
| **Su pantalla** | web/app.js, en MODULO_DE_LA_PANTALLA | el nombre de la pantalla de ese modulo |
| **Los textos** | ya estan: pp/textos.py, bloque NORMATIVA | servidos en /api/interfaz |

Y **las cuatro pruebas que hay que actualizar a la vez**, o el arbol se queda rojo:

- 	ests_js/rutas.test.js: la lista de rutas, una mas.
- 	ests_js/interfaz.test.js: la lista de modulos **y los recuentos por grupo**, que cambian al anadir la fila.
- 	ests_js/armazon.test.js: el menu pasa de **22 filas a 23**.
- y la copia de textos de las pruebas del movil, si cambia el vocabulario.

**El paso del recorrido**, como el de la busqueda: entrar por el renglon del menu, comprobar que salen las diez
reglas, que cada una ensena **su fuente oficial con su enlace** y que las que no estan clasificadas **lo dicen**.

**Lo que no hay que tocar**: el estado (los textos ya se sirven) y la puerta (ya responde, con sus cinco
pruebas).

---

## CIERRE del encargo (07/10/2026)

Las cuatro prioridades, **hechas y medidas**, y cada una con el comando que lo vuelve a comprobar:

| Prioridad | Estado | Cómo se comprueba |
|---|---|---|
| **1. Registrar un trabajo**: planificar → guardar → marcar realizado → corregir → anular → **existencias** | hecha | `scripts/comprobar_el_recorrido.py` (pasos 3 a 5) |
| **2. Las fichas desde la búsqueda**: consulta, recarga, Atrás/Adelante y contexto conservado | hecha | el mismo recorrido (paso 7) |
| **3. El rediseño**: cuerpo de 18 px, títulos de 24/20, márgenes de 24 px, cabecera compacta, fichas por secciones, formularios de escritorio y acciones claras | hecha | `medir_la_cabecera.py` · `medir_los_formularios.py` · `medir_las_acciones.py` |
| **3 bis. La forma real de la parcela en su ficha** (era una regresión de este rediseño) | hecha | `medir_el_dibujo_en_la_ficha.py` (2 trazos, 104 px) |
| **4. Normativa accesible**: las diez reglas de la matriz, con su fuente oficial y su aviso de que no están clasificadas | hecha | `medir_la_pantalla_de_normativa.py` **y** el paso 8 del recorrido |
| **4 bis. El traspaso al día** | hecha | este documento |

**Los números, todos medidos** el 07/10/2026:

- **4.646 pruebas de Python**, 0 fallos, 1 omitida.
- **1.077 pruebas de JavaScript**, 0 rojos.
- **53 comprobaciones** del recorrido, 0 fallos, 1 hallazgo (el escenario no tiene ninguna tierra con forma
  para comprobar el dibujo: se dice, no se esconde).
- **203 comprobaciones** de teclado y zoom al 200 %, 0 fallos.
- **10 reglas** de normativa, con **18 enlaces oficiales** (el primero, el del BOE) y **10 avisos** de
  «sin clasificar».

**Y tres decisiones que se tomaron mirando, no suponiendo**, y que quedan escritas donde se tomaron:

1. **El tipo y el estado de las reglas van vacíos** y la pantalla dice «sin clasificar»: la matriz define los
   cinco tipos y los cinco estados, pero no dice cuál es cada regla, y rellenarlos habría sido inventar una
   clasificación legal. Lo decidió David.
2. **El guardián del renglón del menú se cambió con su motivo y midiendo antes**: prohibía la palabra
   «normativ» para que nadie llenara el hueco del encargo con una puerta a ninguna parte, y con razón; ahora
   exige que **cada renglón lleve a su pantalla**, comprobado contra la tabla que de verdad lo decide (22
   renglones con su pantalla y 22 pantallas con su renglón).
3. **El comentario del grupo «Normativa»** sigue diciendo que ese grupo no existe, y sigue siendo verdad:
   lo que se añadió es **un renglón** en el grupo de Inicio, no un grupo nuevo.
