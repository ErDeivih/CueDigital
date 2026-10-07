# Revisión del recorrido: Inicio → Tierras → ficha de una tierra → registrar un trabajo → historial actualizado

> **Qué es esto.** La revisión funcional del primer recorrido, **leyendo código y pruebas** y ejecutando lo que
> se puede ejecutar sin tocar la aplicación. No se ha escrito ni modificado **ni una línea de la aplicación**:
> el único fichero que se ha creado es este.
>
> **Sobre qué revisión está medido.** El `app.js` revisado tiene
> `sha256 4D1D2A44BF185D824A2FB30E018C5FF53E3BCC5251759404E06C630711F87EB4` (22.136 líneas) y **está commiteado así**
> en `9d7f1bb` («El recorrido, andando…», que entró **mientras** se hacía esta revisión y que incluye las 7 líneas
> de `app.js:18435-18441` que se citan en §2.E6). Los números de línea de `app.js` son, por tanto, los del
> commit `9d7f1bb`, y cada cita va además con su texto para que se pueda encontrar aunque el fichero se mueva.
> `backend/scripts/comprobar_el_recorrido.py` sí tiene cambios **sin commitear** y son justo la consecuencia de
> §2.E5 (ver §4).

**Lo que se ha ejecutado** (todo en verde, sin tocar `backend/cuedigital.db` ni el puerto 8000):

| Comando | Resultado |
|---|---|
| `python -m pytest tests/test_trabajos.py -q -rs` | **77 pasan, 0 saltan** |
| `python -m pytest tests/test_los_botones_hacen_algo.py tests/test_t06_tierras_y_mapa.py -q` | 32 pasan |
| `node --test tests_js/trabajos.test.js` | **27 pasan** |
| `node --test tests_js/interfaz.test.js` | **338 pasan** |
| Comprobación de esquemas con el cuerpo que manda `app.js` (pydantic, sin HTTP) | **`corregir` falla: ver §2.E1** |

---

## 1. La cadena del recorrido, paso a paso

| # | Paso | Botón (`data-accion`) | Dónde se pinta | Dónde se atiende | A dónde lleva |
|---|---|---|---|---|---|
| 1 | Inicio → Tierras | `mis-cosas` | `react/pantallas/inicio.js:191-196` | `app.js:18632` → `pantallaMisCosas()` (`app.js:8727`) | La lista de tierras |
| 1b | (la otra puerta, la única visible a ≥1024 px) | `inicio` + `data-ir="mis_cosas"` (renglón del menú `#menu-tierras`) | `MODULOS` en `app.js:1470` → `react/piezas/marco.js:86-96` | `app.js:18434` → `irAInicio("mis_cosas")` (`app.js:6590-6596`) | La misma lista |
| 2 | Ver una tierra (móvil) | `cultivo-decir` (**la tarjeta**) | `app.js:8299` (ficha preparada en `tierrasParaMisCosas`, `app.js:8245`) | `app.js:18833` → `pantallaDecirCultivo()` | «Qué hay sembrado» — **no es la ficha** |
| 2b | Abrir **la ficha** de una tierra (móvil) | `tierra-historia` | `app.js:8311-8317` (primer botón bajo la tarjeta) | `app.js:21562` → `abrirLaHistoriaDeUnaTierra(id)` (`app.js:21437`) | `#/tierras/<id>/historial`. **A ≥1024 px la tarjeta está oculta** (`.solo-movil`, `mis_cosas.js:76-107`) → hay que ir por 2c |
| 2c | Abrir la tierra en el ordenador | `elegir-fila` + `data-tabla="tierras"` (el nombre de la fila) | `app.js:8484` (tabla en `tablaDeTierras`, `app.js:8458`) | `app.js:18951` | El **panel** de al lado (`panelDeLaTierra`, `app.js:8600`), que lleva el mismo `tierra-historia` (`app.js:8649` reusa `app.js:8314`) y **ese sí se ve** (el panel vive en `.solo-escritorio`) |
| 3 | Ficha de la tierra | — (es una pantalla, con dirección: `rutas.js:89`) | `PantallaDeLaTierra`, `react/pantallas/trabajos.js:573` | `app.js:1290` → `abrirLaHistoriaDeUnaTierra` → `GET /api/trabajos/tierra/<id>` (`app.js:21451`) + `GET /api/gastos/de-una-tierra/<id>` (`app.js:21454`) | Cultivo de hoy, última labor, historial, **lo previsto**, **costes**, lo que no consta |
| 4 | Planificar un trabajo | `trabajo-planificar` | `trabajos.js:758` (ficha de la tierra); también `trabajos.js:234` (agenda) | `app.js:21563` → `abrirUnTrabajo("planificar", null)` (`app.js:21286`) | El formulario (`trabajos.js:331`) |
| 4b | Guardar lo planificado | `trabajo-previsto-guardar` | `trabajos.js:524` | `app.js:21564` → `guardarElTrabajo()` (`app.js:21398`) → `POST /api/trabajos/previstos` (`app.js:21406`; puerta en `routers/trabajos_api.py:571`) | Vuelve a la agenda (`app.js:21432`) |
| 5 | Marcar **lo que de verdad se hizo** | `trabajo-hecho` | **`trabajos.js:201`, en la agenda** | `app.js:21575` → `abrirUnTrabajo("hecho", id)` | El formulario, con lo previsto al lado (`trabajos.js:386-399`) |
| 5b | Guardar el hecho | `trabajo-hecho-guardar` | `trabajos.js:538` | `app.js:21576` → `guardarElTrabajo()` → `POST /api/trabajos/previstos/<id>/hecho` (`app.js:21408`; puerta en `trabajos_api.py:955`) | Nace la labor y se descuenta del almacén; vuelve a la agenda (`app.js:21432`) |
| 6 | Historial actualizado | — | El hecho sale en `historial.lineas` (`app.js:21487-21507`) de `GET /api/trabajos/tierra/<id>` (`trabajos_api.py:424` → `trabajos.historial_de_una_tierra`) | — | Pero para verlo hay que **volver a entrar**: Inicio → Tierras → buscar → `tierra-historia` |

**La cadena literal de `data-accion`**, tal y como se pulsa:

```
Inicio:            mis-cosas                                   → pantallaMisCosas (la lista)
Tierras (móvil):   tierra-historia          [datos.id = tierra] → #/tierras/<id>/historial
Tierras (PC):      elegir-fila [tabla=tierras]                 → panel de la tierra (misma ficha, al lado)
                                 tierra-historia [datos.id]    → #/tierras/<id>/historial
Ficha:             trabajo-planificar                          → formulario (SIN la tierra puesta, §2.E2)
                   trabajo-previsto-guardar                    → POST /api/trabajos/previstos → agenda
Agenda:            trabajo-hecho [datos.id = plan]             → formulario «lo que he hecho»
                   trabajo-hecho-guardar                       → POST .../<id>/hecho → agenda
(para ver el historial otra vez: mis-cosas → buscar → tierra-historia)
```

`trabajos-ver` (`trabajos.js:556` y `trabajos.js:759`) es el botón de volver de las dos pantallas de los
trabajos; el renglón del menú que abre la agenda es `menu-trabajos` (`app.js:1474`, `marco.js:86-96`).

---

## 2. Los eslabones que faltan o están rotos

Cada uno con su línea y con lo que haría falta, en palabras.

### E1. «Corregir un trabajo hecho» **no se puede hacer desde la pantalla**: contesta 422 siempre
- `app.js:21409` manda el `PUT /api/trabajos/<id>` con `cuerpo`, y `cuerpo` sale de `loEscritoEnLaFicha`
  (`app.js:21360-21395`): `{tipo, subtipo, parcela_id, superficie_ha, horas, equipo_id, observaciones, fecha}`
  (`app.js:21386-21388`). **No lleva `campana_id`.**
- La puerta pide `TrabajoEntrada` (`routers/trabajos_api.py:1171-1174`), y en ese esquema `campana_id` es
  **obligatorio** (`schemas.py:3838`). Comprobado sin HTTP:
  `ValidationError: campana_id — Field required` para el cuerpo exacto de la pantalla.
- Consecuencia: el agricultor pulsa CORREGIRLO → escribe → GUARDAR LA CORRECCIÓN y ve «No se ha podido»
  (`app.js:21421-21423`, porque un 422 no trae una frase del servidor que `avisoDelServidor` sepa leer).
- Qué haría falta: que la corrección mande también la campaña (las otras dos puertas que la necesitan ya la
  añaden a mano: `app.js:21406` y `app.js:21408`), **o** que `campana_id` deje de ser obligatorio al corregir
  (la puerta ya sabe conservarla cuando no se la mandan: `trabajos_api.py:1204-1210`).
- **Por qué no lo caza nada:** las pruebas de Python que corrigen mandan `campana_id` a mano
  (`tests/test_las_existencias_cuadran.py:170-180`), y la prueba de JavaScript del guardado **solo mira la ruta
  y el método**, no el cuerpo (`tests_js/interfaz.test.js:14334-14338`).

### E2. Planificar desde la ficha **no lleva la tierra**: se abre el formulario con la tierra en blanco
- El botón de la ficha es `trabajos.js:758`, **sin `datos`**: no lleva el `id` de la tierra.
- El manejador lo abre literalmente con `null`: `app.js:21563`.
- Y el borrador no tiene de dónde sacarla: `app.js:21302` (`parcela_id: trabajo && trabajo.parcela_id ? … : ""`)
  con `trabajo = null` (`app.js:21295`).
- Consecuencia: «PLANIFICAR UN TRABAJO» desde la ficha de una tierra abre el formulario con **«En qué tierra:
  Elige la tierra»** y hay que volver a buscar la tierra entre 64 en un desplegable. El recorrido no se rompe,
  pero el paso «planificar un trabajo **para esa tierra**» no está dado.
- Qué haría falta: que el botón de la ficha lleve el identificador de la tierra (el dato ya está en el estado,
  `suyo.tierra`, `app.js:21456`) y que `abrirUnTrabajo("planificar", …)` lo use para el borrador.

### E3. Marcar lo que se hizo **no se puede desde la ficha de la tierra**
- En la ficha, lo previsto se pinta **sin ningún botón**: `trabajos.js:654-668` (solo título y cuándo).
- Los botones de «YA LO HE HECHO» / «CAMBIARLO DE DÍA» / «CANCELARLO» están **solo en la agenda**
  (`trabajos.js:197-222`).
- Qué haría falta: los mismos botones en la lista de lo previsto de la ficha (la acción ya existe y ya está
  atendida: `trabajo-hecho`, `app.js:21575`), **o** dejar dicho que ese paso se da en la agenda.

### E4. Desde la ficha **no se vuelve a la lista de tierras**, y Escape tampoco
- El único botón de salida de la ficha es «VOLVER A LOS TRABAJOS» (`trabajos.js:759`, texto en
  `app/textos.py:7801`) y lleva a la agenda (`trabajos-ver`), no a la lista.
- Y **Escape hace lo mismo**: `app.js:5170` mete `trabajos-ver` en `LO_QUE_CIERRA_ESCAPE`, y el manejador
  (`app.js:5191-5197`) pulsa el primer botón visible de esa lista → desde la ficha de una tierra, Escape
  **saca al agricultor a la agenda de los trabajos**. (En esa lista, `trabajos-ver` se justifica por la ficha de
  un trabajo, que está en la agenda; el problema es que la ficha de una tierra pinta el mismo botón.)
- Consecuencia: al guardar, la aplicación lleva a la agenda (`app.js:21432`) y **desde la agenda no hay ningún
  botón que lleve a la historia de una tierra** (sus dos salidas son `ir-inicio` y `cuaderno-abrir`,
  `trabajos.js:304-307`). El propio guion del navegador lo dice: *«se pasa por el principio —«mis cosas»—
  porque al guardar la aplicación vuelve a la agenda de los trabajos, y desde ahí el botón de la historia de
  una tierra no existe. El paso que falta **se dice**»* (`scripts/comprobar_en_un_navegador.py:1093-1096`).
- Qué haría falta: un botón de «volver a mis tierras» en la ficha (y en la ficha de un trabajo cuando se venga
  de una tierra) que devuelva a la lista **con su filtro**, y sacar `trabajos-ver` del Escape de esa pantalla.

### E5. **Los botones del móvil no se pueden pulsar en el ordenador (≥1024 px)**
- El botón `mis-cosas` está dentro del bloque del móvil: `inicio.js:159` (`<div className=${mando ? "solo-movil" : ""}>`)
  y el botón en `inicio.js:191-196`.
- Y `.solo-movil` está **oculto** a partir de 64 rem: `estilos.css:1599-1610` (`@media (min-width: 64rem) { .solo-movil { display: none; } }`).
- **Lo mismo le pasa a `tierra-historia` y a los demás botones de la tarjeta de la tierra**: las tarjetas van
  dentro de `<div className="tarjetas solo-movil">` (`react/pantallas/mis_cosas.js:76-107`). A ≥1024 px hay que
  abrir la ficha por la fila de la tabla (`elegir-fila`, `app.js:8484`) y pulsar `tierra-historia` **en el panel**
  (`app.js:8649`), que sí se ve porque la tabla y el panel viven en `.solo-escritorio` (`mis_cosas.js:68-71`).
- En el ordenador, el panel de mando **no ofrece ninguna entrada a las tierras**: su número de tierras es un
  `<li>` con texto, no un botón (`react/piezas/panel_de_mando.js:35-46`). La única puerta a la lista a 1024 px
  o más es el renglón del menú (`#menu-tierras`, `app.js:1470` + `marco.js:86-96`).
- Consecuencia medida por otro lado: `scripts/comprobar_el_recorrido.py` corría a **1440 px** (hoy `:119`) y pulsa
  con ratón de verdad (`navegador_cdp.py:293-321`); un clic sobre un elemento `display:none` se va a la esquina
  (0,0) y **no pasa nada**, sin que el guion se entere. Por eso ese guion creía que el botón «estaba muerto».
- Qué haría falta: (a) una entrada de verdad a las tierras en el Inicio de escritorio —el número «Tierras» del
  panel de mando es el sitio natural—, **o** (b) que el recorrido se haga al ancho donde esos botones existen
  (el móvil), **o** (c) que el recorrido use las puertas que sí se ven a ese ancho (`#menu-tierras` y
  `elegir-fila`). **No se arregla con un manejador nuevo: ver E6.** *(Quien ha hecho el commit `9d7f1bb` ya ha
  tirado por (c) en el guion, sin commitear todavía: `comprobar_el_recorrido.py:137-143` dice «al ancho del
  ordenador, a las tierras se va por el menú».)*

### E6. Hay **dos manejadores** para `mis-cosas`, y el que se ha añadido hoy no arregla E5
- A la hora de empezar esta revisión, `mis-cosas` **ya estaba atendido**: en `70b5484` hay
  `if (nombre === "mis-cosas") return pantallaMisCosas();` (hoy en `app.js:18632`).
- El commit `9d7f1bb` (entrado durante esta revisión) añade **otra** rama antes, en `app.js:18441`:
  `if (nombre === "mis-cosas") return irAInicio("mis_cosas");`, y su comentario dice que «aquí no había nada
  que lo atendiera» y que «lo encontró el recorrido (`scripts/comprobar_el_recorrido.py`)». **Eso no se sostiene
  contra `70b5484`**, y el comportamiento no cambia (las dos llaman a `pantallaMisCosas()`): la que gana es la
  nueva y la vieja (`app.js:18632`) queda muerta. El fallo de verdad del recorrido era E5 (la visibilidad), y ese
  guion ya se ha corregido yendo por `#menu-tierras`.
- Qué haría falta: dejar una sola de las dos ramas (la de `18441` sobra) y, si se quiere el botón en el
  ordenador, arreglar **la visibilidad** del botón, no el manejador.

### E7. La ficha de la tierra **pide la superficie y no la enseña**
- `app.js:21483-21486` pasa `tierra: {nombre, superficie}` y el componente documenta esa propiedad
  (`trabajos.js:566`), pero **solo pinta el nombre** (`trabajos.js:586`). La superficie no aparece por ningún lado
  de la ficha.
- Qué haría falta: pintarla (la fila ya existe: `Fila`, `trabajos.js:91-98`), que es lo que pide el contrato en el
  resumen fijo de S03 (`docs/CONTRATO_IMPLEMENTACION_CRM.md:139`).

### E8. Menor: la frase de «gastos sin importe» está en singular
`app/textos.py:7901-7903` («Hay {cuantos} gasto de esta tierra…») se rellena con un número que puede ser 2
(`trabajos.js:694`) → «Hay 2 gasto de esta tierra». Y `{cuantos}` no tiene plural en `tabla`.

### E9. Lo que dicen los documentos del T15 ya no es verdad
`routers/trabajos_api.py:39-61` («todavía no se puede importar», lista de lo que falta), `tests/test_trabajos.py:16`
y `:929-931/955-971` («esas se saltan»), y `docs/T15_TRABAJOS.md` §4/§6 («el recorrido contra el servidor, no
todavía»): el router **está integrado** (`main.py:220`), y hoy `test_trabajos.py` pasa **77 de 77 sin saltarse
ninguna**. Quien lea esos comentarios se creerá que esa mitad no está.

---

## 3. Las cinco preguntas, una a una

### 1. ¿Se puede recorrer entero pulsando?
**Sí, con dos salvedades y un rodeo:**

- **Abrir las tierras desde Inicio**: sí en el móvil, con `mis-cosas` (`inicio.js:191-196` → `app.js:18632`).
  **En el ordenador no hay botón en Inicio**: el de `mis-cosas` está oculto por CSS (`estilos.css:1603-1610`) y
  el panel de mando no tiene entrada (E5). En el ordenador se entra por el renglón del menú (`#menu-tierras`).
- **Llegar a la ficha de una tierra (y no al mapa)**: sí. La lista (`mis_cosas`) no lleva al mapa: el mapa es
  otra dirección (`#/tierras/mapa`, `rutas.js:98`) y se abre por `t06-ver-mis-tierras`/el renglón de T06. La
  ficha se abre con `tierra-historia` (`app.js:8311-8317` en la tarjeta del móvil; `app.js:8649` en el panel del
  ordenador) → `#/tierras/<id>/historial` (`rutas.js:89` → `app.js:1290`).
- **Planificar un trabajo para esa tierra**: se puede pulsar `trabajo-planificar` en la ficha
  (`trabajos.js:758` → `app.js:21563`), **pero la tierra no viaja**: hay que volver a elegirla en el
  desplegable (E2). Es el eslabón más flojo del recorrido.
- **Marcar lo que de verdad se hizo**: sí, pero **solo desde la agenda** (`trabajos.js:201`), no desde la ficha
  de la tierra (E3). Hay que salir de la ficha a «VOLVER A LOS TRABAJOS» (`trabajos.js:759`).
- **¿Aparece después en el historial de esa tierra?** Sí: el hecho es una `Labor` y
  `GET /api/trabajos/tierra/<id>` la devuelve en `historial.lineas` (`trabajos_api.py:424-460`,
  `app.js:21487-21507`); está probado en Python (`tests/test_trabajos.py:1288-1337`) y en el navegador
  (`scripts/comprobar_en_un_navegador.py:1080-1105`). **Lo que no hay es camino de vuelta**: al guardar se va a
  la agenda (`app.js:21432`) y desde ahí no hay botón a la tierra (E4), así que el agricultor tiene que
  empezar el recorrido otra vez por Inicio → Tierras → buscar → `tierra-historia`.

### 2. ¿Falta algún eslabón?
Sí, cuatro, y **ninguno es «solo por API» salvo el primero** (que es al revés: la API sí y la pantalla no):

- **Corregir un trabajo hecho**: la pantalla lo manda mal y contesta 422; solo funciona por API (E1).
- **Planificar «para esa tierra»** desde su ficha: la tierra no se hereda (E2).
- **Marcar lo hecho desde la ficha**: ese botón no existe ahí (E3).
- **Volver de la ficha a la lista con el filtro**: el botón de volver lleva a la agenda, y Escape también (E4).
- Y un eslabón de **visibilidad**: en el ordenador, Inicio no ofrece las tierras (E5).

### 3. ¿La ficha de la tierra es una sola?
**No. Hay cuatro pantallas para la misma tierra, y no enseñan lo mismo:**

| Pantalla | Dirección | Qué enseña | Dónde |
|---|---|---|---|
| El panel de la tierra (solo ordenador) | `#/tierras/<id>` (`rutas.js:99`) | Sus datos, su dibujo, hectáreas, municipio y **sus 3 últimos apuntes del año**; botones: `cultivo-decir`, `tierra-historia`, corregir, borrar | `panelDeLaTierra`, `app.js:8600-8652` |
| La historia de la tierra (la «ficha» del T15) | `#/tierras/<id>/historial` (`rutas.js:89`) | Qué hay sembrado hoy, última labor, **todo el historial** (con anulados y corregidos), **lo previsto**, **los costes** y lo que no consta | `trabajos.js:573-762`; datos de `app.js:21437-21564` |
| Lo que ha sido una tierra (T06) | `#/tierras/<id>/versiones` (`rutas.js:103`) | Sus versiones por año y fuente, la comparación de dos años y el ensayo de una importación | `tierra_versiones.js` |
| Qué hay sembrado en esa tierra | `#/tierras/<id>/cultivo` (`rutas.js:107`) | Solo el cultivo declarado (y cambiarlo) | `decir_cultivo.js` |

- **No coinciden.** «Costes» y «lo previsto» **solo** están en la historia; el panel no los tiene. El panel
  enseña «sus últimos apuntes» sacados de lo que hay cargado en memoria (`losApuntesDelAnio()`, `app.js:2458`,
  filtrado por tierra en `app.js:8632-8640`), mientras que la historia los pide a otra puerta
  (`/api/trabajos/tierra/<id>`): son **dos listas del mismo hecho con dos fuentes distintas** y **ninguna prueba
  exige que digan lo mismo**.
- Y tocar la tarjeta en el móvil (lo que hace cualquiera) abre **la cuarta** pantalla, la del cultivo
  (`app.js:8299`), que no tiene ni historial, ni previsto, ni costes.
- Frente al contrato (`docs/CONTRATO_IMPLEMENTACION_CRM.md:137-144`), la «ficha de tierra» pide un resumen fijo
  (mapa, campaña/cultivo, **superficie**, referencias y próximo trabajo) y seis secciones (Historia, Cultivos,
  Productos y abono, Cosecha y cuentas, Documentos y PAC). Lo que hay hoy reparte eso entre cuatro pantallas y
  **la superficie no se enseña en ninguna** (E7). La «comparación anual» del contrato (variedad, siembra,
  cosecha, rendimiento y coste conocido) **no existe**: la comparación de `versiones_api.py` /
  `tierra_versiones.js` no menciona cultivo, cosecha, rendimiento ni coste (buscado: cero coincidencias).

### 4. ¿Se conservan los filtros al volver?
**Sí, y también «por dónde iba»** — pero solo si se vuelve por la puerta de la lista.

- El filtro vive en `estado.filtroTierrasMisCosas`: lo escribe el buscador (`app.js:2335`), lo aplica la lista
  (`app.js:8254`, `8731`) y lo escribe también la dirección al abrirla (`app.js:1159`).
- «Por dónde iba» se guarda **al salir** de la lista: `recordarPorDondeIba()` (`app.js:1097-1104`) guarda
  la dirección (con «q» y el orden) y el `scroll` en `estado.vistas`, porque `TABLA_DE_LA_PANTALLA` incluye `tierras`
  (`app.js:781-791`) y `PantallaMisCosas` marca el módulo `tierras` (`app.js:1525`).
- Al volver, `volverAdondeIba()` (`app.js:1107-1115`) devuelve al scroll si la dirección es **la misma** que se
  guardó, y la dirección se reescribe con el filtro porque `parametrosDeLaPantalla` mete `q` (`app.js:952-956`).
- **Los tres caminos de vuelta:**
  1. El botón «atrás» del navegador → `abrirLaPantalla("tierras", {q})` → `app.js:1159` repone el filtro. ✅
  2. El renglón del menú o el botón `mis-cosas` → `pantallaMisCosas()` con el estado intacto. ✅
  3. **El botón de la ficha** («VOLVER A LOS TRABAJOS», `trabajos.js:759`) → **no vuelve a la lista**: va a la
     agenda. ❌ (E4). El filtro no se pierde (sigue en memoria), pero el agricultor no vuelve por donde iba.
- Ojo con lo que **sí** borra el filtro: cambiar de finca (`olvidarLoDeLaFincaAnterior`, `app.js:3148`), que es
  correcto.
- Y una cosa que no se ha probado: esto está probado **en el módulo** de rutas (`tests_js/rutas.test.js:651-720`,
  «el recorrido que pide T04: lista → ficha → vuelta con los filtros puestos»), **no** en `app.js` con
  `filtroTierrasMisCosas` y el buscador de verdad.

### 5. Qué pruebas cubren hoy ese recorrido
Ver §4.

---

## 4. Qué está probado y qué no

### Probado, y en verde

| Qué | Dónde | Qué cubre de verdad |
|---|---|---|
| La lógica del trabajo (previsto ≠ hecho, el rodillo no borra la siembra, la lluvia no da nascencia, anular/corregir no duplican consumos, reenvíos, huecos ≠ ceros) | `tests/test_trabajos.py` (77, **0 saltadas**) | Las reglas del encargo |
| **El recorrido por la API**: planificar → marcar lo hecho → historial | `tests/test_trabajos.py:1271-1390` — `test_planificar_marcar_lo_hecho_y_que_llegue_al_historial` (1288), `test_marcar_dos_veces_el_mismo_plan_no_apunta_dos_trabajos` (1339), `test_lo_previsto_no_gasta_nada_hasta_que_se_hace` (1366) | Las tres puertas del recorrido, con su rastro |
| La historia y el estado de una tierra | `tests/test_trabajos.py:1144-1250` (`/api/trabajos/tierra/<id>`, `/estado/<id>`) | Que las dos saquen las mismas cifras |
| Las puertas del trabajo por HTTP | `test_trabajos.py:955` (`test_las_puertas_del_router_se_ejecutan_cuando_este_integrado`), `test_las_existencias_cuadran.py:149-180` (POST y **PUT** `/api/trabajos`), `test_el_coste_de_una_tierra.py:57` | Que las puertas existen y contestan |
| Que todo botón pintado tenga quién lo atienda | `tests/test_los_botones_hacen_algo.py:169` | **Solo** que la acción está escrita en `app.js`; no que haga lo que dice |
| Las pantallas del T15 (cómo se ven) | `tests_js/trabajos.test.js` (27) | React a HTML: textos, listas separadas, huecos, costes… |
| `app.js` con un DOM de mentira: la agenda, marcar lo hecho, las cinco puertas y la historia | `tests_js/interfaz.test.js` — `14233`, `14271`, `14286`, `14312` (las cinco puertas: **solo método y ruta**), `14378` (la historia por su dirección), `14509` (la historia desde el botón) | Que cada botón abre lo que toca y que la petición va a la ruta correcta |
| La memoria de la vista (filtros al volver) | `tests_js/rutas.test.js:651-720` | Las funciones `recuerda/recupera/olvida` y `enlaceDeTierra`, no el `app.js` |

### El hueco: **la cadena entera no está probada de punta a punta en ninguna suite**

1. **Python para en la API y JavaScript para en el doble de `fetch`.** Nadie compara **el cuerpo que manda la
   pantalla con el esquema que pide el servidor**: por eso E1 (el `campana_id` que falta al corregir) está verde
   en las dos suites y roto en la aplicación. La prueba de las cinco puertas
   (`tests_js/interfaz.test.js:14312-14376`) comprueba `envio.metodo` y `envio.ruta`, **nunca `envio.cuerpo`**.
2. **Nada comprueba que los botones se vean o se puedan pulsar al ancho en el que se está.** La comprobación de
   rutas del navegador pulsa con `boton.click()` (`scripts/comprobar_en_un_navegador.py:2367`), que **funciona
   con elementos ocultos**, y no mira visibilidad en ningún sitio (no hay `checkVisibility` en ese fichero). Por
   eso E5 (el botón de Inicio oculto en el ordenador) pasa desapercibido. *(El guion nuevo sí usa ratón de verdad
   —y por eso lo encontró, a costa de creer que el botón estaba muerto: E6.)*
3. **Nadie prueba la vuelta de la ficha a la lista con el filtro** en `app.js` (solo en el módulo de rutas).
4. **Nadie prueba que planificar desde la ficha lleve la tierra** (E2), ni que la ficha tenga botón para marcar
   lo hecho (E3), ni para volver a las tierras (E4).
5. **La comprobación del navegador es a mano**: `scripts/comprobar_en_un_navegador.py` (con las rutas del
   recorrido 4 y del 5 en `:1017-1131`) y `scripts/comprobar_el_recorrido.py` **no se ejecutan en las suites**;
   el único test sobre ellos mira que el guion esté escrito (`tests/test_comprobar_en_un_navegador.py:31-79`).
   Lo que se ejecuta en cada cambio (`pytest` + `node --test`) **no ve ninguna de esas rutas**.
6. El recorrido de la API termina en `/api/trabajos/historial/<id>` (`test_trabajos.py:1325`), que es una puerta
   que la pantalla **no usa**: la pantalla usa `/api/trabajos/tierra/<id>` (`app.js:21451`). Esa sí está probada
   (1144-1250), pero no *después* del recorrido de planificar → hecho.

### Y un aviso sobre el propio árbol
Mientras se hacía esta revisión ha entrado el commit **`9d7f1bb`** («El recorrido, andando: dos defectos de verdad
y el buscador de clics arreglado»), que:
1. mete en `app.js` la rama duplicada de E6 (las 7 líneas de `18435-18441`), que **no arregla nada**;
2. arregla `navegador_cdp.py:293-321` para que `pulsar()` **elija el primer elemento que se ve y falle si ninguno
   se ve** en vez de mandar el clic a la esquina (0,0): es lo que **destapa E5**;
3. deja `comprobar_el_recorrido.py` **sin commitear** entrando por `#menu-tierras` y por `elegir-fila`
   (`:137-143`), que es la corrección de E5 por el camino (c).

Queda también un `backend/scripts/ver_la_ficha.py` nuevo y sin commitear que **no he mirado** (no es de esta
revisión). **Ni un fichero de la aplicación de mi parte**: lo único que he creado es este informe.

---

## 5. Lo que no he podido comprobar (y por qué)

1. **No he abierto un navegador.** Todo lo que digo de visibilidad (E5) está leído del CSS y del código
   (`estilos.css:1603-1610`, `inicio.js:159`), y confirmado contra la herramienta del guion (`navegador_cdp.py:293-321`,
   que manda el clic a las coordenadas del elemento). No he visto la pantalla con mis ojos.
2. **No he levantado el servidor ni he hecho ni una llamada HTTP.** No he usado la base temporal ni
   `datos_representativos.py`: la revisión del recorrido es de código y de pruebas. El defecto E1 lo he comprobado
   con el propio esquema de pydantic (sin escribir en ninguna base), no con un `curl`.
3. **No he medido a qué anchos corre cada guion del navegador** a ciencia cierta: en
   `comprobar_en_un_navegador.py` las pantallas de las rutas se vuelcan en una página que se abre **después** de
   dejar la ventana a 1440 px (`:1737`), pero el volcado no dice con qué ancho se hizo; lo que sí es seguro es que
   esas rutas pulsan con `boton.click()` (`:2367`), que no necesita que el botón se vea.
4. **No sé si el recorrido «se entiende»**: que separar «lo que tengo pensado» de «lo que he hecho» se lea bien,
   o que «Sin decir» se lea como un hueco y no como un cero, no lo dice ninguna prueba (lo dice el propio informe
   del T15, `docs/T15_TRABAJOS.md:743-745`).
5. **No he podido fijar los números de línea**: el fichero se ha modificado durante la revisión (§4). Cada cita
   lleva su texto para que valga aunque la línea se haya movido unos renglones.
6. **No he juzgado si el estado actual del árbol (las 7 líneas sin commitear) es lo que se quiere**: eso es de
   quien esté trabajando en paralelo. Lo que sí digo es lo que hay medido: `HEAD` ya atendía `mis-cosas`.

---

## Resumen en cinco líneas

1. **El recorrido se puede dar entero pulsando**, con un rodeo: al guardar, la aplicación lleva a la agenda de los
   trabajos y desde ahí **no hay botón** para volver a la tierra; y en el ordenador el botón de Inicio a las
   tierras está **oculto por el CSS** (hay que entrar por el menú).
2. **Faltan cuatro eslabones**: corregir un trabajo hecho está **roto (422)** desde la pantalla, planificar desde
   la ficha **no lleva la tierra**, marcar lo hecho **no tiene botón** en la ficha, y la ficha **no vuelve a la
   lista** (ni con Escape).
3. **No hay una sola ficha**: hay cuatro pantallas para la misma tierra, y «costes» y «lo previsto» solo están en
   una.
4. **El filtro y el «por dónde iba» sí se conservan** al volver a la lista (menú, `mis-cosas` o «atrás»); el
   problema es que la ficha no ofrece ese camino.
5. **Lo probado está verde** (77 de Python + 365 de JavaScript) pero **ninguna suite recorre la cadena entera**:
   Python para en la API y JavaScript para en el doble de `fetch`, sin comparar el cuerpo contra el esquema — por
   eso el 422 del punto 2 pasa desapercibido.
