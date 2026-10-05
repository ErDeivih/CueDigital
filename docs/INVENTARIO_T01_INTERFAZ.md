# T01 — Inventario de la interfaz: pantallas, armazón, contrato de pantalla, fichas, estados y huecos

Fecha: 01/10/2026. Encargo: ticket **T01 / E0** del
[CONTRATO_IMPLEMENTACION_CRM.md](CONTRATO_IMPLEMENTACION_CRM.md) («Inventario
ruta→pantalla→API→modelo→pruebas; estados realmente existentes»).

**Alcance: solo lectura sobre el código.** No se ha modificado ningún fichero salvo este informe. No se
ha tocado `backend/cuedigital.db`, no se ha ejecutado ningún servidor, ni `scripts/humo.py`, ni la
comprobación de navegador.

**Cómo se ha comprobado.** Leyendo el código y buscando con `grep`, fichero por fichero. Todo lo que
se afirma aquí lleva `fichero:línea`. Los informes anteriores del repositorio son históricos y **no**
se han usado como fuente: lo que dicen se ha verificado en el código o se ha descartado.

**Advertencia de método, para que nadie se apoye de más en este documento.** No se ha abierto un
navegador (estaba prohibido en el encargo), así que **todo lo visual está deducido del JSX, del CSS y
de los textos**, no visto. Donde eso importa —el apartado 6 entero, y el vacío de las seis listas de
maestros en el ordenador— se dice expresamente. El apartado 8 lista lo que no se ha podido comprobar.

---

## 1. Las pantallas que existen hoy

### 1.1 La fuente de la verdad

La lista de pantallas vive **en el propio código**: `PANTALLAS_EN_REACT`, al principio de
`app.js:96-127`, con **29 claves**:

```
 96: const PANTALLAS_EN_REACT = new Set([
 97:   "inicio",
...
126:   "campanas",
127: ]);
```

Cada clave tiene su fichero en `backend/web/react/pantallas/` (29 ficheros, uno por clave: la
correspondencia es 1 a 1 y se ha comprobado) y su función `montar()` en `app.js`. Lo que **no** son
pantallas son las **once piezas** de `backend/web/react/piezas/` (`acciones_de_una_ficha.js`,
`ayuda_de_un_campo.js`, `campo.js`, `campos_del_maestro.js`, `confirmacion.js`,
`lista_para_elegir.js`, `marco.js`, `panel_de_mando.js`, `resumen_del_apunte.js`, `tabla.js` y
`tarjeta.js`), y el propio proyecto lo tiene
escrito: *«la lista `PANTALLAS_EN_REACT` es la lista de pantallas, y meter ahí un trozo sería mentir en
la tabla»* (`docs/REACT.md:256-258`).

### 1.2 El menú lateral: 16 módulos

`MODULOS`, en `app.js:529-546`. El orden no es alfabético, es el del trabajo del agricultor
(`app.js:520-528`):

| # | `clave` | Rótulo (clave de `textos.py`) | `data-accion` del renglón | Línea |
|---|---|---|---|---|
| 1 | `panel` | `menu.panel` («Panel») | `ir-inicio` | `app.js:530` |
| 2 | `cuaderno` | `cuaderno.titulo` («Mi cuaderno») | `inicio` + `data-ir="mi_cuaderno"` | `app.js:531` |
| 3 | `tierras` | `maestros.titulo` | `inicio` + `data-ir="mis_cosas"` | `app.js:532` |
| 4 | `cultivos` | `cultivos.titulo` («Qué hay sembrado») | `cultivo-ver-todos` | `app.js:533` |
| 5 | `grupos` | `grupos.titulo` | `inicio` + `data-ir="grupos"` | `app.js:534` |
| 6 | `almacen` | `cesta.titulo` | `cesta-ver` | `app.js:535` |
| 7 | `analisis` | `analitica.titulo` | `inicio` + `data-ir="analisis"` | `app.js:536` |
| 8 | `plan` | `plan.titulo` | `inicio` + `data-ir="planes"` | `app.js:537` |
| 9 | `ventas` | `venta.titulo` | `inicio` + `data-ir="ventas"` | `app.js:538` |
| 10 | `medidas` | `medidas.titulo` | `medidas-ver` | `app.js:539` |
| 11 | `papeles` | `documentos.titulo` | `papel-ver-todos` | `app.js:540` |
| 12 | `facturas` | `facturas.titulo` | `facturas-abrir` | `app.js:541` |
| 13 | `anos` | `campanas.titulo` | `campanas-abrir` | `app.js:542` |
| 14 | `junta` | `cuaderno_cyl.titulo` | `cuaderno-de-la-junta-abrir` | `app.js:543` |
| 15 | `datos` | `mis_datos.titulo` | `mis-datos-abrir` | `app.js:544` |
| 16 | `ayuda` | `ayuda.pantalla.titulo` | `inicio` + `data-ir="ayuda"` | `app.js:545` |

**El menú solo existe a partir de 64 rem** (1024 px): se esconde por CSS en pantalla estrecha
(`estilos.css:1817-1821`, `.marco { display: none }`), con un motivo escrito: *«en el móvil manda la
pantalla de inicio, sin menús que aprender»* (`estilos.css:1815-1816`).

### 1.3 Qué módulo marca el menú, y qué pantallas no marcan ninguno

`MODULO_DE_LA_PANTALLA` (`app.js:558-582`) traduce **componente de React → módulo**, y no botón →
módulo, con el motivo escrito: *«una misma pantalla se abre por muchos caminos (…). Lo que dice en qué
sitio estás es la pantalla que está puesta, no el botón que pulsaste»* (`app.js:550-557`).

Mapea **23 de las 29 pantallas**. Las **seis que NO están** en el mapa son:

| Pantalla | Por qué no marca módulo |
|---|---|
| `PantallaEntrar` | es la de entrar: no se está «en» ningún módulo |
| `PantallaMapa` | cuelga del alta de una tierra, no de un módulo |
| `PantallaTraerDelSigpac` | es un **paso** dentro del asistente de dar de alta una tierra |
| `PantallaDictado` | cuelga de la pantalla de inicio |
| `PantallaBorrador` | cuelga del dictado |
| `PantallaFirmar` | se llega desde «mi cuaderno» y desde el panel de mando |

Y eso tiene una consecuencia real en el código: cuando `modulo` es `""`, `pintarMarco()` **vuelve a
pintar el armazón cada vez** en vez de ahorrárselo:

```
597:   if (estado.marcoPintado === modulo && modulo !== "") return;
```

### 1.4 Las 29 pantallas, con su componente, su módulo y cómo se llega

La columna «se llega con» son los `data-accion` que la abren, leídos **del manejador de clics**, que es
uno solo y delegado en `document` (`app.js:10944-10946`). Los `data-ir` se resuelven en `irAInicio()`
(`app.js:5135-5209`).

| Clave | Componente React | Fichero | Módulo | Se llega con (y dónde está en el código) |
|---|---|---|---|---|
| `inicio` | `PantallaInicio` | `pantallas/inicio.js` | `panel` | `ir-inicio` (`app.js:10949`); `inicio` en el `default` de `irAInicio` (`app.js:5206-5207`); cabecera de móvil (`index.html:26`); menú (`app.js:530`); botón `VOLVER` de casi todas las pantallas (`accionesDeConfirmacion`, `app.js:675-680`) |
| `entrar` | `PantallaEntrar` | `pantallas/entrar.js` | — | arranque sin token (`app.js:11330`); `salir` (`app.js:11213` → `app.js:3797`); `cambiar-modo-entrar` (`app.js:11212`) |
| `mi_cuaderno` | `PantallaMiCuaderno` | `pantallas/mi_cuaderno.js` | `cuaderno` | `inicio` + `data-ir="mi_cuaderno"` (`app.js:5162-5164`); menú (`app.js:531`); botón «MI CUADERNO» de la pantalla de inicio (`textos.py:800-806`) |
| `asistente` | `PantallaAsistente` | `pantallas/asistente.js` | `cuaderno` | `trabajo` (`app.js:10951`); `anadir-maestro` (salvo parcela) (`app.js:10960`); `sigpac-si` / `sigpac-no` (`app.js:10962-10963`); `inicio` + `echar_producto` / `abonar` / `trabajo` (`app.js:5136-5160`); `repetir` (`app.js:11214`); `campana-nueva` (`app.js:11019`); `plan-hacer` (`app.js:11147`); `analisis-nuevo` (`app.js:11149`); `ventas-nueva` (`app.js:11155`); `cosa-corregir` / `hecho-corregir` (`app.js:11222`, `11236`) |
| `hecho` | `PantallaHecho` | `pantallas/hecho.js` | `cuaderno` | se pinta **al guardar** (`pantallaHecho`, `app.js:2069`) |
| `mis_cosas` | `PantallaMisCosas` | `pantallas/mis_cosas.js` | `tierras` | `mis-cosas` (`app.js:11086`); `inicio` + `data-ir="mis_cosas"` (`app.js:5165-5171`); menú (`app.js:532`); botón «📋 MIS PARCELAS, PRODUCTOS Y MÁQUINAS» (`inicio.js:191-196`); `parcela-traida-seguir` (`app.js:11085`) |
| `cultivos` | `PantallaCultivos` | `pantallas/cultivos.js` | `cultivos` | `cultivo-ver-todos` (`app.js:11108`); `cultivo-solo-las-que-faltan` (`app.js:11115`); `cultivo-ver-todas` (`app.js:11119`); menú (`app.js:533`); `inicio` + `data-ir="cultivos"` (`app.js:5188-5193`) |
| `decir_cultivo` | `PantallaDecirCultivo` | `pantallas/decir_cultivo.js` | `cultivos` | `cultivo-decir` (`app.js:11123`), desde la tarjeta de una tierra y desde la tabla |
| `grupos` | `PantallaGrupos` | `pantallas/grupos.js` | `grupos` | `grupo-ver` (`app.js:11129`); menú (`app.js:534`); `inicio` + `data-ir="grupos"` (`app.js:5173`) |
| `cesta` | `PantallaCesta` | `pantallas/cesta.js` | `almacen` | `cesta-ver` (`app.js:11107`); menú (`app.js:535`) |
| `analiticas` | `PantallaAnaliticas` | `pantallas/analiticas.js` | `analisis` | `analisis-ver` (`app.js:11148`); menú (`app.js:536`); `inicio` + `data-ir="analisis"` (`app.js:5179`) |
| `planes` | `PantallaPlanes` | `pantallas/planes.js` | `plan` | `plan-ver` (`app.js:11146`); menú (`app.js:537`); `inicio` + `data-ir="planes"` (`app.js:5176`) |
| `ventas` | `PantallaVentas` | `pantallas/ventas.js` | `ventas` | `ventas-ver` (`app.js:11154`); menú (`app.js:538`); `inicio` + `data-ir="ventas"` (`app.js:5185`) |
| `medidas` | `PantallaMedidas` | `pantallas/medidas.js` | `medidas` | `medidas-ver` (`app.js:11156`); menú (`app.js:539`); `inicio` + `data-ir="medidas"` (`app.js:5182`) |
| `documentos` | `PantallaDocumentos` | `pantallas/documentos.js` | `papeles` | `papel-ver-todos` (`app.js:11087`); menú (`app.js:540`) |
| `nuevo_documento` | `PantallaNuevoDocumento` | `pantallas/nuevo_documento.js` | `papeles` | `papel-nuevo` (`app.js:11088`) |
| `facturas` | `PantallaFacturas` | `pantallas/facturas.js` | `facturas` | `facturas-abrir` (`app.js:10980`); menú (`app.js:541`) |
| `nueva_factura` | `PantallaNuevaFactura` | `pantallas/nueva_factura.js` | `facturas` | `factura-nueva` (`app.js:10984`) |
| `interpretacion_factura` | `PantallaInterpretacionDeLaFactura` | `pantallas/interpretacion_factura.js` | `facturas` | `factura-leer` / `factura-mano` (`app.js:10996-10997`, vía `estado.facturas.interpretacion`); `cosa-corregir` de una factura (`app.js:11222` → `OTRAS_COSAS.factura.corregir`, `app.js:4676-4683`) |
| `campanas` | `PantallaCampanas` | `pantallas/campanas.js` | `anos` | `campanas-abrir` (`app.js:11015`); menú (`app.js:542`); `inicio` + `data-ir="campanas"` (`app.js:5195-5199`) |
| `cuaderno_de_la_junta` | `PantallaCuadernoDeLaJunta` | `pantallas/cuaderno_de_la_junta.js` | `junta` | `cuaderno-de-la-junta-abrir` (`app.js:11005`); menú (`app.js:543`); `cuaderno-abrir` (`app.js:10968`) |
| `mis_datos` | `PantallaMisDatos` | `pantallas/mis_datos.js` | `datos` | `mis-datos-abrir` (`app.js:11007`); menú (`app.js:544`) |
| `quien_entra` | `PantallaQuienEntra` | `pantallas/quien_entra.js` | `datos` | `quien-entra-abrir` (`app.js:11031`), **y solo se produce en un sitio**: `mis_datos.js:109` |
| `ayuda` | `PantallaAyuda` | `pantallas/ayuda.js` | `ayuda` | `inicio` + `data-ir="ayuda"` (`app.js:5203`); menú (`app.js:545`); botón «❓ NO SÉ QUÉ PULSAR» (`textos.py:814-820`) |
| `mapa` | `PantallaMapa` | `pantallas/mapa.js` | — | `mapa-abrir` (`app.js:10966`), desde el botón «ELEGIR EN EL MAPA» de `pantallaTraerOApuntar` (`app.js:5237-5243`); `mapa-volver` (`app.js:11035`) |
| `traer_del_sigpac` | `pantallaTraerDelSigpac` | `pantallas/traer_del_sigpac.js` | — | **no es una pantalla suelta**: es un paso del asistente (`app.js:5798`, `montar: () => … pantallaTraerDelSigpac(…)`) al que se llega con `sigpac-si` (`app.js:10962`) |
| `dictado` | `PantallaDictado` | `pantallas/dictado.js` | — | `dictado` (`app.js:11134`), desde el botón «🎤 DÍMELO CON LA VOZ» (`inicio.js:184-190`) |
| `borrador` | `PantallaBorrador` | `pantallas/borrador.js` | — | `dictado-entender` (`app.js:11140` → `pantallaBorrador(borrador)`, `app.js:9428`) |
| `firmar` | `PantallaFirmar` | `pantallas/firmar.js` | — | `firmar-abrir` (`app.js:11143`), desde «mi cuaderno» (`app.js:1634`) y desde el cierre del panel de mando (`app.js:1124`) |

### 1.5 Rutas: no hay ninguna

**No hay enrutador.** `index.html` tiene un solo punto de montaje y ninguna ruta:

```
38:   <main id="pantalla" class="pantalla" aria-live="polite"></main>
```

Búsqueda de `pushState`, `location.hash`, `history.` y `enrutad` en todo `backend/web/`: **cero
coincidencias** (fuera de `vendor/`). El cambio de pantalla lo hacen funciones de `app.js` y el
manejador delegado de clics por `data-accion`.

**Consecuencia directa contra el contrato** (`CONTRATO_IMPLEMENTACION_CRM.md:82-83`): *«Cada registro
tiene una ficha única accesible desde todos sus contextos»*. Hoy **no hay dirección que abra una
factura, una tierra ni un producto**, y no hay «enlace permanente al contexto» (que el contrato pide
en la sección 1, `CONTRATO...md:20-22`).

---

## 2. El armazón

### 2.1 Dónde vive y cómo se monta

El armazón **no es una pantalla**: va fuera del contenedor de las pantallas, en `#marco`
(`index.html:19-23`), y lo pinta `react/piezas/marco.js` con **otro montador**:

```
736: 1. **El armazón vive fuera del contenedor de las pantallas** (`#marco`, en `index.html`), y lo
737:    pinta `react/piezas/marco.js` … **No se monta con `montar()`** sino con `montarFueraDeLaPantalla()`,
738:    y se apunta en **su propia lista** (`montajesDelMarco`, en `react/montar.js`) — no en `montajes`.
```

El motivo está escrito: las pruebas de cableado cuentan cuántas **pantallas** se le piden a React
(`docs/REACT.md:740-742`). El armazón se rehace **solo cuando cambia el módulo** (`pintarMarco`,
`app.js:594-627`; el atajo, `app.js:597`), y si algo falla al prepararlo **el armazón no se pinta y la
pantalla sí** (`app.js:591-593`).

### 2.2 El menú lateral

- Componente: `Modulo` (`marco.js:35-50`) y el `<nav className="menu">` (`marco.js:68-78`).
- Lleva, arriba, **el nombre de la cuenta** (`marco.js:73`), y debajo los 16 módulos, uno por renglón.
- **El renglón activo se marca con tres cosas a la vez**, que es la regla de la casa (el color no
  informa solo): clase `menu-activo` (`marco.js:41`), `aria-current="page"` (`marco.js:44`) y, por CSS,
  fondo distinto **y barra amarilla a la izquierda** (`estilos.css:1257-1263`).
- CSS: `estilos.css:1197-1263`. Fijo, verde oscuro, 17 rem de ancho (`--ancho-menu`, `estilos.css:64`).
- **Solo en el ordenador**: `@media (min-width: 64rem)` (`estilos.css:1194`), y oculto en estrecho
  (`estilos.css:1817-1821`).

### 2.3 La barra de arriba

- `marco.js:79-111`. Lleva **dos datos** y **tres botones**:
  - «**Campaña**» + el año (`marco.js:81-84`),
  - «**Tu cuenta**» + el nombre (`marco.js:85-88`),
  - `APUNTAR` (`data-accion="ir-inicio"`, `marco.js:91-93`), `A+` (`cambiar-letra`, `marco.js:94-101`),
    `Salir` (`salir`, `marco.js:102-109`).
- CSS: `estilos.css:1265-1330`. Fija arriba, verde, sin transparencias.

### 2.4 La cabecera de móvil

- `index.html:25-36`: `header.cabecera`, con el título «🌾 Mi cuaderno» que es un botón
  (`data-accion="ir-inicio"`), y los dos botones de letra y salida.
- CSS: `estilos.css:97-140` (pegajosa arriba, `position: sticky; top: 0; z-index: 10`).
- **En el ordenador se esconde**, y está escrito por qué: *«en el ordenador su trabajo lo hace la
  barra, y dos barras pegadas son una de más. La letra grande y el salir siguen estando, en la barra»*
  (`estilos.css:1186-1187`; la regla, `estilos.css:1332-1335`).

### 2.5 Qué contexto muestra: las cuatro preguntas, contestadas con evidencia

**¿Qué contexto muestran el menú y la barra?**

| Dato | ¿Está? | Dónde | De dónde sale |
|---|---|---|---|
| **Cuenta** (quién apunta) | **Sí**, dos veces: arriba del menú y en la barra | `marco.js:73` y `marco.js:85-88` | `cuenta: estado.nombre \|\| (estado.miFinca \|\| {}).nombre \|\| ""` (`app.js:613`) |
| **Campaña** (el año) | **Sí**, en la barra | `marco.js:81-84` | `campana: estado.campana ? String(estado.campana.anio \|\| "") : ""` (`app.js:614`) |
| **Explotación** (la finca) | **No se muestra.** No hay rótulo «Finca» ni nombre de finca | `textos.py:3773-3778`, y de hecho existe `menu-finca` en el CSS (`estilos.css:1221-1226`) **pero ningún componente emite esa clase** | — |
| **Búsqueda global** | **No** | `marco.js:64-113` no tiene ni un `<input>`; `grep` de `pushState\|buscar\|buscador` en `marco.js`: cero | — |

El **porqué** del «no hay Finca» está escrito en el propio texto del servidor, y no es un olvido:

```
3773:     # **No hay «Finca» en la barra, y es una decisión** (30/09/2026). En este programa la finca se
3774:     # identifica por **el nombre del titular**: `Explotacion.nombre` es el campo «¿Cómo te llamas?» de
3775:     # «Mis datos» y no hay un nombre de finca aparte
...
3778:     # tenga nombre propio —o cuando una cuenta entre en varias, que ya se puede—, ese dato vuelve a la
3779:     # barra: el hueco está hecho y solo falta el dato.
```

**¿Hay selector de campaña? NO.** El año de la barra es **texto**, no un botón (`marco.js:81-84`), y la
campaña activa **no se puede elegir en ninguna pantalla**: el servidor devuelve siempre **la más
nueva**, sin parámetro ni endpoint para cambiarla:

```
145: @router.get("/campanas/actual", response_model=CampanaSalida)
146: def campana_actual(explotacion: ExplotacionActual, db: Db) -> models.Campana:
147:     campana = db.scalar(
148:         select(models.Campana)
149:         .where(models.Campana.explotacion_id == explotacion.id)
150:         .order_by(models.Campana.anio.desc())
151:         .limit(1)
```
(`backend/app/routers/explotacion.py:145-151`)

La pantalla «Los años de mi cuaderno» **sí** deja crear, corregir y borrar años
(`campanas-abrir`, `campana-nueva` en `app.js:11015-11028`), y **dice cuál se está llevando**
(`campanas.el_que_llevo`, `app.js:9129`, `textos.py:3856`), pero **no deja ponerse a trabajar en otro**.
El contrato pide lo contrario en la sección 1: *«selector de campaña visible en despacho»*
(`CONTRATO...md:20-21`).

**¿Hay selector de explotación? NO en la cabecera, pero sí se puede cambiar de finca** — en otra
pantalla y por otro camino:

- `finca-entrar` (`app.js:11034` → `entrarEnLaFinca()`, `app.js:1927-1948`): cambia el vale,
  **vuelve a pedir todos los datos** y lleva al inicio. El porqué está escrito: *«lo que hay en memoria
  (las tierras, los apuntes, el cuaderno de la Junta) es de la finca en la que se estaba, y enseñarlo
  después de cambiar sería enseñarle a un agricultor los datos de otra finca»* (`app.js:1919-1926`).
- El botón está en `quien_entra.js:78`, y la lista de fincas **solo sale si hay más de una**
  (`quien_entra.js:190-200`, `fincas.length > 1`).
- La pantalla sí dice en cuál estás: `quien_entra.js:160` (`d.estas_en` + el nombre).
- **Y a esa pantalla solo se llega desde un sitio**: `mis_datos.js:109` (módulo «datos»).
- **Ojo con la barra**: al cambiar de finca, `estado.nombre` **no cambia**, así que «Tu cuenta» sigue
  diciendo lo mismo y **la barra nunca dice en qué finca estás trabajando**.

**¿Hay búsqueda global? NO.** Grep de `buscar` en `backend/web/`: solo hay **dos buscadores**, y los
dos son de tierras:

| Buscador | `id` del campo | Dónde | A qué llega |
|---|---|---|---|
| El del asistente (elegir una tierra) | `buscar_tierra` | `app.js:2190-2203` | `buscar-tierra`, `buscar-tierra-limpiar` (`app.js:11078-11079`) |
| El de «mis cosas» (mirar las tierras) | `buscar_tierra_mis_cosas` | `app.js:2213-2229` | `buscar-tierra-mis-cosas`, `buscar-tierra-limpiar-mis-cosas` (`app.js:11081-11082`) |

Están separados **a propósito** y hay un motivo escrito: *«con uno solo, buscar «prado» al apuntar
dejaría «mis cosas» enseñando dos tierras de las 51 sin que nadie lo hubiera pedido allí»*
(`app.js:1178-1181`). **El contrato pide una búsqueda que incluya tierra, referencia SIGPAC, contacto,
producto, factura y máquina** (`CONTRATO...md:85-87`): hoy solo hay tierra (y por nombre y referencia,
vía `tierrasQueCasen`, `nucleo.js`).

### 2.6 Resumen del apartado 2

| Pregunta del encargo | Respuesta | Evidencia |
|---|---|---|
| Menú lateral | **Sí**, 16 módulos, solo en ≥64 rem, con el activo marcado de tres formas | `app.js:529-546`, `marco.js:68-78`, `estilos.css:1197-1263`, `estilos.css:1817-1821` |
| Barra de arriba | **Sí**, con campaña + cuenta + APUNTAR + A+ + Salir | `marco.js:79-111` |
| Cabecera de móvil | **Sí**, oculta en el ordenador | `index.html:25-36`, `estilos.css:1332-1335` |
| Contexto: cuenta | **Sí** | `app.js:613`, `marco.js:73`, `85-88` |
| Contexto: campaña | **Sí, como texto** | `app.js:614`, `marco.js:81-84` |
| Contexto: explotación | **No** (por decisión escrita; se cambia en otra pantalla) | `textos.py:3773-3778`, `app.js:11034`, `quien_entra.js:190-200` |
| Selector de campaña | **NO** | `app.js:614`, `explotacion.py:145-151` |
| Selector de explotación | **NO en la cabecera**; sí en «Quién entra en mi finca» | `quien_entra.js:190-200` |
| Búsqueda global | **NO** | `marco.js:64-113`; solo dos buscadores de tierras, `app.js:2190-2229` |

---

## 3. El contrato común de pantalla, punto por punto

El texto a cumplir (`CONTRATO_IMPLEMENTACION_CRM.md:89-93`):

```
89: Todas las tablas: título y total, búsqueda, filtros con etiquetas removibles,
90: orden estable, columnas configurables, selección y acciones permitidas, pie con
91: filtrados/total. Exportar indica si exporta seleccionados, filtrados o todos. Las
92: sumas no se calculan sobre la página visible: el servidor devuelve el agregado del
93: conjunto filtrado. Fechas y cantidades se ordenan por valor, no por texto formateado.
```

### 3.1 Qué tablas existen hoy

Seis, y todas se montan con **la misma pieza** (`react/piezas/tabla.js`, `Tabla`), que **no calcula
nada**: *«Ni los totales, ni el orden, ni qué está en ámbar: todo eso lo prepara `app.js`»*
(`tabla.js:18-19`).

| Tabla | Función que la prepara | `clave` | ¿Panel de al lado? | Se pinta en |
|---|---|---|---|---|
| Tierras | `tablaDeTierras` (`app.js:6942-7019`) | `tierras` | **Sí** — `panelDeLaTierra` (`app.js:7060`) | `mis_cosas.js:69` |
| Cuaderno (apuntes) | `tablaDeApuntes` (`app.js:7126-7179`) | `apuntes` | No | `mi_cuaderno.js:94` |
| Años del cuaderno | `tablaDeLosAnos` (`app.js:9191-9237`) | `anos` | No | `campanas.js:107` |
| Facturas | `tablaDeFacturas` (`app.js:7987-8051`) | `facturas` | No | `facturas.js:148` |
| Almacén | `tablaDeLaCesta` (`app.js:7739-7802`) | `cesta` | **Sí** — `panelDelProducto` (`app.js:7813`) | `cesta.js:129` |
| Qué hay sembrado | `tablaDeLosCultivos` (`app.js:8662-8723`) | `cultivos` | No | `cultivos.js:157` |

**Solo hay dos paneles de detalle en toda la aplicación.** Comprobado: `grep "panel: panel"` en
`app.js` devuelve **dos** líneas (`app.js:7017` y `app.js:7800`).

### 3.2 Los diez requisitos, uno por uno

#### (1) Título y total

**Existe, con dos matices.**

- **Título:** el componente `Tabla` **no pinta título visible**: `etiqueta` solo va al `aria-label`
  (`tabla.js:203`, `<table className="tabla" aria-label=${frase(tabla.etiqueta)}>`), y el motivo está
  escrito en `textos.py:3603` (*«El nombre de la tabla, para quien no ve la pantalla (lector de
  pantalla)»*). El título que ve el agricultor es el `h1`/`h2` de la pantalla: `mis_cosas.js:59`
  (`<h2>{seccion.titulo}</h2>`, «Parcelas»), `mi_cuaderno.js:88` (`cuaderno.apuntes_titulo`),
  `cesta.js:116`, `facturas.js:136`, `campanas.js:100`, `cultivos.js:128`.
- **Total en el pie (`<tfoot>`):** `tabla.js:212-220`. Los textos, del servidor:

| Tabla | Texto del pie | Clave | Línea |
|---|---|---|---|
| Tierras | «{cuantas} tierras · {hectareas} ha» | `resumen_tierras` | `textos.py:3630` |
| Apuntes | «{cuantas} apuntes · {hectareas} ha tratadas» (+ « · N firmados» si los hay) | `resumen_apuntes` | `textos.py:3643`; `app.js:7164-7171` |
| Años | «{cuantas} años en tu cuaderno» | `resumen_anos` | `textos.py:3657` |
| Facturas | «{cuantas} facturas · {total} €» o «…falta el total de alguna» | `resumen_facturas` / `resumen_facturas_sin_total` | `textos.py:3667-3669` |
| Almacén | «{cuantas} productos en el almacén» (+ « · N hay que mirarlos» si los hay) | `resumen_cesta` / `resumen_cesta_mirar` | `textos.py:3694-3696`; `app.js:7786-7791` |
| Cultivos | «{cuantas} tierras · N con su cultivo dicho» | `resumen_cultivos` / `resumen_cultivos_dichas` | `textos.py:3728-3730` |

**Lo que falta:** el **total del pie solo se ve en el ordenador**. En el móvil la tabla no se dibuja
(`.solo-escritorio`, `estilos.css:1372-1373` y `1809-1813`), y el `resumen` va **dentro** del objeto de
la tabla, así que en las tarjetas del móvil **no hay ningún total**. El total de «mis cosas» en el móvil
es `seccion.cuantas` (`mis_cosas.js:61`), que es **el total de la lista entera**, no el de lo filtrado.

Y hay una consecuencia peor: **cuando no hay filas, el componente no pinta nada**:

```
201:   if (!filas.length) return null;
```

Es decir: con 0 filas desaparece la tabla **y su título accesible y su pie**. En el móvil eso no se
nota, pero en el ordenador la pantalla se queda sin la tabla (el vacío lo cubre el aviso de la
pantalla, que sí se pinta — ver el punto 5 de esto mismo apartado).

#### (2) Búsqueda

**Existe en UNA tabla: la de tierras.** Es el buscador de «mis cosas» (`app.js:2213-2229`), escrito en
el campo `buscar` de la sección (`app.js:7197` → `mis_cosas.js:62`). Y **es de cliente**: filtra sobre
lo que ya está cargado, con `tierrasQueCasen(estado.parcelas, estado.filtroTierrasMisCosas)`
(`app.js:6759`).

Las otras cinco tablas **no tienen búsqueda**: `tablaDeApuntes`, `tablaDeLosAnos`, `tablaDeFacturas`,
`tablaDeLaCesta` y `tablaDeLosCultivos` no reciben ningún parámetro de búsqueda y ninguna pantalla les
pasa un campo (`cesta.js:129`, `facturas.js:148`, `campanas.js:107`, `cultivos.js:157`,
`mi_cuaderno.js:94`).

**Lo que falta:** búsqueda en cuaderno, facturas, almacén, años y cultivos; y **ninguna llama al
servidor** (no hay `limit`, `offset` ni `q` en ninguna llamada de `app.js`: grep de `limit=|offset=|
page=|pagina` → cero coincidencias).

#### (3) Filtros con etiquetas removibles

**No existe.** Hay **dos** cosas que hacen de filtro, y ninguna es una etiqueta removible:

| Lo que hay | Cómo se quita | Línea |
|---|---|---|
| El buscador de tierras de «mis cosas» | botón `VERLAS TODAS` (`buscar-tierra-limpiar-mis-cosas`) | `app.js:2215-2220`, `textos.py:1508` |
| El filtro «solo las que faltan decir el cultivo» | botón `VERLAS TODAS` (`cultivo-ver-todas`) | `app.js:8609`, `11115-11122`, `cultivos.js:157-166` |

Y no hay **más filtros** en ninguna tabla. Lo que el contrato pide para S02 —«cultivo, municipio,
secano/regadío, titularidad, campaña, sin cultivo, trabajo realizado/pendiente y sin forma»
(`CONTRATO...md:123-124`)— **no existe**: `grep` de `filtro` en `app.js` da solo el estado de los dos
buscadores (`app.js:232-233`), su lectura (`app.js:1195-1198`) y los dos filtros de arriba.

**Lo que falta:** todo el sistema de filtros. No hay ni una clave en `textos.py` para «quitar filtro»
(chip) ni para «filtros aplicados».

#### (4) Orden estable

**Existe, y está bien hecho.** Hay tres piezas:

- `ORDEN_DE_ENTRADA` (`app.js:6867-6874`): «por dónde empieza el orden de cada tabla», con su motivo
  escrito (`app.js:6850-6866`). Ejemplo: `tierras: { campo: "numero", sentido: 1 }`,
  `apuntes: { campo: "fecha", sentido: -1 }`, `facturas: { campo: "fecha_iso", sentido: -1 }`,
  `anos: { campo: "anio_numero", sentido: -1 }`, `cesta: { campo: "nombre_comercial", sentido: 1 }`,
  `cultivos: { campo: "alias", sentido: 1 }`.
- `ordenarFichas` (`app.js:6887-6907`): ordena, manda al final lo que no tiene dato
  (`app.js:6899-6902`) **y desempata** para que el orden no baile entre dos pulsaciones:
  ```
  6905:     return (Number(una[desempate]) || 0) - (Number(otra[desempate]) || 0);
  ```
- El orden es **de la pantalla, no del aparato** (`app.js:6878-6881`), así que las tarjetas del móvil
  salen en el mismo orden que la tabla.
- Ordenar es un `data-accion` más: `ordenar-tabla` con `data-tabla` y `data-campo`
  (`tabla.js:56-65`, `app.js:11180-11191`), y **cada tabla repinta la suya** (`repintarLaPantallaDeLaTabla`,
  `app.js:7033-7040`) — con el fallo que eso arregló contado en `app.js:7024-7028`.

**Lo que falta:** el orden **no se guarda** (vive en `estado.ordenDeLaTabla`, `app.js:6842-6848`, que es
memoria: al recargar se pierde), así que no hay «vistas guardadas por usuario» (`CONTRATO...md:21`).

#### (5) Columnas configurables

**No existe.** Las columnas se escriben a mano en cada `tablaDe…` (`app.js:6950-6956`, `7130-7138`,
`7745-7757`, `7991-8000`, `8666-8677`, `9195-9204`) y no hay ninguna interfaz para mostrarlas,
ocultarlas o reordenarlas. Grep de `ocultar`, `mostrar-columna`, `columnas-config` en `backend/web/`:
cero coincidencias fuera de comentarios.

De hecho **el proyecto ha ido en la dirección contraria a propósito**, y lo tiene razonado: quitar
columnas para que quepan los botones (`app.js:6946-6949`, `7747-7751`). Eso está bien como decisión de
ancho, pero **no sustituye** a que el agricultor pueda elegir qué ve.

**Lo que falta:** todo.

#### (6) Selección y acciones permitidas

**Parcial, y con una limitación clara: la selección es de UNA fila y solo en dos tablas.**

- Elegir fila: `elegir-fila` (`app.js:11170-11179`), con `data-tabla` y `data-id`. Marca `filaElegida`
  (`app.js:7049-7052`), y volver a tocar la misma fila la quita (`app.js:11176-11177`, *«es como se
  cierra el panel sin buscar un botón de cerrar»*).
- **Solo las tablas de tierras y de almacén** tienen celda-botón con `elegir-fila`
  (`app.js:6963-6970` y `app.js:7762-7768`). Las otras cuatro no.
- La fila **no** es un botón, y el motivo está escrito: *«un `<tr>` no se puede enfocar con el teclado»*
  (`tabla.js:88-90`).
- Acciones por fila: la última columna la pinta la pieza (`tabla.js:108-110`), con los botones que
  prepara `app.js` — `botonesDeCorregirYBorrar` (`app.js:4834-4860`) más la acción propia de la fila.
  Un botón puede venir **apagado** y con su explicación al lado (`acciones_de_una_ficha.js:25-28`), como
  el borrar de un año con cosas dentro (`app.js:9105-9111` + `campanas.js:69-78`).

**Lo que falta:** selección múltiple, «seleccionar todos los filtrados» y **edición múltiple** (que S02
pide con vista previa, `CONTRATO...md:127`). Hoy no hay ni una casilla de selección en toda la
aplicación.

#### (7) Pie con filtrados/total

**Existe en las dos tablas que tienen filtro**, y solo en el ordenador:

| Tabla | Texto | Dónde |
|---|---|---|
| Tierras, con el buscador puesto | «**{cuantas} de {total} tierras · {hectareas} ha**» | `textos.py:3631`, `app.js:7000-7005` |
| Cultivos, con el filtro puesto | «**{cuantas} de {total} tierras**» | `textos.py:3733`, `app.js:8709-8710` |

En las otras cuatro el pie solo dice el total, porque **no hay nada que filtrar**.

**Lo que falta:** el «cuántas de cuántas» **no llega al móvil** (va dentro del objeto de la tabla, que
en el móvil no se pinta), y la línea de cuenta del móvil dice **el total de la lista entera** aunque
estés filtrando:

```
7211:       cuantas: cuantas
7212:         ? rellena(m(cuantas === 1 ? "cuantas_tierras_una" : "cuantas_tierras"), { cuantas })
```
donde `cuantas` es `estado.parcelas.length` (`app.js:7183`), es decir el total, no `tierras.length`.

#### (8) Exportación declarada

**Existe, pero no es la que pide el contrato: no hay ninguna exportación por tabla.** Hay **tres**
descargas en todo el programa, y las tres son **del cuaderno entero**:

| Qué | `data-accion` | Endpoint | Dónde está el botón |
|---|---|---|---|
| El cuaderno en papel (PDF) | `sacar-papel` (`app.js:11215`) | `GET /api/cuaderno/pdf` (vía `sacarPapel`, `app.js:5093`) | Inicio (`textos.py:807-813`), «mi cuaderno» (`app.js:1681`), panel de mando (`app.js:1116-1120`) |
| Los datos en CSV | `sacar-datos` (`app.js:11216`) | `GET /api/cuaderno/export.csv` (`app.js:5120`) | «mi cuaderno» (`app.js:1685`), panel de mando (`app.js:1121`) |
| El cuaderno de la Junta (Excel) | `cuaderno-sacar` (`app.js:11004`) | `GET /api/cuaderno-cyl/exportar` (`app.js:1955`) | «mi cuaderno» (`app.js:1657`) |

**Ninguna de las tres dice si exporta los seleccionados, los filtrados o todos** (que es lo que exige
`CONTRATO...md:91`). Y **no hay ningún botón de exportar en ninguna de las seis tablas**: la columna de
acciones de una fila lleva como mucho dos botones (`CORREGIR` y `BORRAR`/`ANULAR`), y no hay barra de
acciones encima de la tabla.

**Lo que falta:** todo. Y ojo con el CSV: sale del cuaderno entero, así que con un filtro puesto
exportaría **más** de lo que se está viendo, sin decirlo.

#### (9) Agregados del servidor y no de la página

**Cumple en UNA tabla (el almacén) y no cumple en cinco.** Es el punto donde el contrato se incumple
más claramente, porque aquí **no hay paginación**: todas las listas se cargan enteras, así que «el
agregado del conjunto filtrado» acaba siendo, de hecho, un agregado del conjunto **cargado**, calculado
en el navegador.

| Tabla | ¿De dónde sale el número del pie? | Evidencia |
|---|---|---|
| **Almacén** | **Del servidor.** Comentario explícito: *«las cuentas ya vienen contadas del servidor»* | `app.js:7606-7607`; `GET /api/productos/cesta/situacion` (`app.js:3641`) calcula en `servicios.situacion_de_la_cesta` (`backend/app/routers/maestros.py:280-331`, con `cuantas`, `sin_cantidad`, `sin_poder_comparar` y `resumen`) |
| Tierras | **De la página**: `reduce` sobre las tierras cargadas | `app.js:6999` |
| Apuntes | **De la página**: `reduce` sobre las fichas | `app.js:7159` |
| Facturas | **De la página**: `sumaCompleta()` sobre las facturas cargadas | `app.js:8023-8030` |
| Años | **De la página**: `ordenadas.length` | `app.js:9235` |
| Cultivos | **De la página**: filtros y `.length` | `app.js:8706-8714` |

Y el panel de mando (S01) suma en la página: hectáreas tratadas (`app.js:999-1002`), hectáreas de la
finca (`app.js:1003-1006`) y kilos vendidos (`app.js:1008`).

**Lo que falta:** los agregados del servidor. La API de listas **no devuelve ningún agregado**: es una
`response_model=list[...]` que devuelve la lista entera.

#### (10) Orden por valor y no por texto

**Existe, y es de lo mejor resuelto del contrato.** `ordenarFichas` (`app.js:6887-6907`) hace
exactamente lo que pide el contrato:

```
6888:   const valor = (ficha) => {
6889:     const suyo = ficha[orden.campo];
6890:     if (typeof suyo === "number") return suyo;
...
6893:     if (suyo !== "" && Number.isFinite(numero) && String(suyo).trim() !== "") return numero;
6894:     return String(suyo).toLocaleLowerCase("es");
```

Y las columnas de fecha **no se ordenan por la fecha escrita**: cada `tablaDe…` guarda el dato en crudo
en un campo aparte y ordena por él:

- facturas: `fecha_iso: factura.fecha || ""` (`app.js:7945`) y la columna ordena por `fecha_iso`
  (`app.js:7992`), mientras que la celda enseña `fecha_escrita` (`app.js:8004`).
- años: ordena por `anio_numero` (`app.js:9196`) y por `desde_iso` / `hasta_iso` (`app.js:9197-9198`).
- apuntes: ordena por `fecha`, que es la fecha ISO (`app.js:7131`) — y el motivo está escrito en
  `app.js:6830-6831`.
- El texto se compara con `toLocaleLowerCase("es")` **a propósito**: *«es lo que hace que «Ávila» no
  acabe detrás de «Zamora»»* (`app.js:6883-6884`).

**Lo que falta:** nada de fondo. Un detalle: el desempate se hace con `Number(...)`, así que en una
tabla cuyo campo de desempate no sea numérico (todas lo son hoy: `numero`, `id`, `producto_id`,
`parcela_id`) el desempate sería un empate; **no comprobado si alguna vez se pasa otro**.

### 3.3 Cuadro resumen del contrato, por tabla

Leyenda: **S** = existe · **P** = parcial · **N** = no existe.

| Requisito | Tierras | Apuntes | Años | Facturas | Almacén | Sembrado |
|---|---|---|---|---|---|---|
| Título | S (h2 de la sección) | S (`cuaderno.apuntes_titulo`) | S | S | S | S |
| Total en el pie | S | S (+ firmados) | S | S (o «falta el total») | S (+ a mirar) | S (+ dichas) |
| Búsqueda | **S** (solo cliente) | N | N | N | N | N |
| Filtros con etiquetas removibles | **N** (hay buscador, no chip) | N | N | N | N | **P** (un filtro, sin chip) |
| Orden estable | S | S | S | S | S | S |
| Columnas configurables | N | N | N | N | N | N |
| Selección y acciones | **P** (una fila + 1 botón + panel) | P (acciones, no selección) | P | P | **P** (una fila + panel) | P |
| Pie con filtrados/total | **S** (solo en el ordenador) | N (no hay filtro) | N | N | N | **S** (solo en el ordenador) |
| Exportación declarada | N | N | N | N | N | N |
| Agregados del servidor | N | N | N | N | **S** | N |
| Orden por valor | S | S | S | S | S | S |

**Los cuatro huecos que atraviesan todas las tablas:** columnas configurables, exportación declarada,
selección múltiple y filtros con etiquetas removibles. **El que más se nota:** los agregados, porque en
el almacén el servidor los da y en las otras cinco no, y hoy no hay forma de que las dos formas de
contar cuadren desde fuera.

---

## 4. Las fichas (paneles de detalle)

El texto a cumplir (`CONTRATO_IMPLEMENTACION_CRM.md:95-97`):

```
95: Todas las fichas: identidad, estado con explicación, acción principal, historial y
96: documentos vinculados. Guardar conserva contexto y filtros al volver. Avisar de
97: cambios pendientes antes de salir. Campos avanzados plegables, no ocultos al guardar.
```

### 4.1 Tres hechos que atraviesan todas las fichas

**(a) Solo hay DOS paneles de detalle, y son de ordenador.** `panelDeLaTierra` (`app.js:7060-7112`,
enganchado en `app.js:7017`) y `panelDelProducto` (`app.js:7813-7863`, enganchado en `app.js:7800`).
Los dos los pinta la misma pieza `Panel` (`tabla.js:125-181`). **Las otras cuatro tablas no tienen
panel**, así que una factura, un año, un análisis o un apunte **no tienen ninguna ficha**: se ven en su
renglón de la lista y nada más.

**(b) No hay ficha por URL.** No hay enrutador (apartado 1.5), así que **ninguna ficha es accesible
«desde todos sus contextos»** (`CONTRATO...md:82-83`): no hay dirección que abra una factura.

**(c) Los dos huecos que no existen en NINGUNA ficha, comprobados con búsqueda:**

- **Aviso de cambios sin guardar: NO existe.** Grep de `beforeunload` en todo `backend/web/`: **cero
  coincidencias**. No hay aviso al cerrar, recargar ni con el botón atrás. Lo único parecido es una
  **etiqueta de botón** dentro del asistente (`app.js:773-778`, texto en `textos.py:2823`,
  `corregir.volver_sin_guardar`), que no cubre ninguno de esos tres casos.
- **Campos avanzados plegables: NO existen** (salvo en la ayuda). Grep de `<details>` y `summary` en
  `backend/web/`: **una sola coincidencia**, y está en la pantalla de ayuda
  (`pantallas/ayuda.js:47-48`). Grep de `avanzad` y `plegable` en `textos.py`: cero coincidencias.

### 4.2 Las fichas, una a una

Los siete puntos del contrato, ficha a ficha. **S** = sí · **P** = parcial · **N** = no · **—** = no
existe en ninguna ficha (ver 4.1c).

| # | Ficha | Qué es | Identidad | Estado + explicación | Acción principal | Historial | Docs vinculados | Aviso cambios | Plegables |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Tierra, panel de detalle** (`app.js:7060`) | Panel al lado de la tabla | P (por número: «Tierra n.º N», `app.js:7074`; el nombre está en la celda, `app.js:6967`) | S (aviso del pendiente, `app.js:7085`) | **S** (`cultivo-decir`, `app.js:7102-7107`) | P (3 últimos del año, `app.js:7092-7100`) | N | — | — |
| 2 | **Producto del almacén, panel** (`app.js:7813`) | Panel al lado de la tabla | P (sin el nombre comercial: está en la celda, `app.js:7765`) | P (motivo en franja; el estado va en la celda, `app.js:7775`) | N (solo CORREGIR/BORRAR, `app.js:7861`) | N | N | — | — |
| 3 | **Producto del almacén, ficha de lista** (`cesta.js:42-93`) | Tarjeta del móvil | S | **S** (4 etiquetas con palabras + motivo, `app.js:7649-7660`) | N | N | N | — | — |
| 4 | **Factura, ficha de lista** (`facturas.js:51-95`) | Renglón-ficha | S (proveedor, nº, fecha, total, líneas) | P (aviso «falta el papel») | P (ver/subir el papel, `facturas.js:67-91`) | N | **S** (su propio papel) | — | — |
| 5 | **Factura, interpretación/corrección** (`interpretacion_factura.js:163-219`) | **Pantalla propia** (la única ficha completa) | **S** (8 campos, `app.js:8241-8255`) | P (avisos de la lectura; sin estado del documento) | **S** (`factura-guardar`, `interpretacion_factura.js:203-211`) | N (se promete por texto, `textos.py:2829`, pero no se puede ver) | N | N | N |
| 6 | **Análisis** (`analiticas.js:49-144`) | Ficha de lista | S | S (edad del boletín, `app.js:10512-10521`) | **S** (subir el informe, `analiticas.js:111-116`) | N | P (su propio boletín) | — | — |
| 7 | **Plan de abono** (`planes.js:43-99`) | Ficha de lista | S | **S** («En regla» / «Alerta: exceso», `planes.js:49-58`) | N | N (solo el cultivo precedente) | P (el análisis en que se apoya, `planes.js:69-83`) | — | — |
| 8 | **Venta** (`ventas.js:33-66`) | Ficha de lista | S | **N** (ni estado, ni importe, ni cobrado, ni pendiente: ver 4.3) | N | N | N (el nº de albarán es texto) | — | — |
| 9 | **Papel / documento** (`documentos.js:37-76`) | Ficha de lista | S | P (aviso «falta el fichero») | **S** (subir el fichero, `documentos.js:59-64`) | N | **S** (su propio fichero) | — | — |
| 10 | **Apunte del cuaderno** (`mi_cuaderno.js:86-124`) | Tarjeta, **de solo lectura** | S («Apunte N», `app.js:1444`) | P (plazo de seguridad; «Firmado» solo en la tabla, `app.js:7147`) | N (**la tarjeta no es un botón a propósito**, `mi_cuaderno.js:81-84`) | N | N | N (solo al corregir) | — |
| 11 | **Tierra en «mis cosas»** (`tarjeta.js:77-167`) | Tarjeta del móvil | S (nombre + nº + referencia) | P (aviso del pendiente, `app.js:6784`) | **S** (abre lo sembrado, `app.js:6800-6801`) | N | N | — | — |
| 12 | **Maestro** (producto, abono, aplicador, asesor, máquina, nave) (`app.js:4208-4256`) | Renglón-ficha | S (mínima) | **N** | N | N | N | — | — |
| 13 | **Año / campaña** (`campanas.js:39-82`) | Ficha de lista | S | **S** (etiqueta + «cuánto tiene dentro» + por qué no se puede quitar, `app.js:9105-9133`) | N | P («cuánto tiene dentro», `app.js:9167-9181`) | N | — | — |
| 14 | **Mapa (parcela del SIGPAC)** (`mapa.js:125-170`) | **Pantalla propia**, con el alta dentro | P (referencia, uso, pueblo, ref. catastral, nombre) | P («comprobado» + recordatorio de comprobarlo con el papel, `mapa.js:62-71`) | **S** (`mapa-apuntar`, `mapa.js:103`) | N | N | P (conserva el nombre escrito, `app.js:5684-5689`) | — |
| 15 | **Confirmación antes de borrar** (`confirmacion.js:95-146`) | Pantalla propia | S | P (explica qué es anular y por qué no se borra, `app.js:4972-4973`) | **S** (BORRAR SÍ / ANULAR) | N (se afirma que queda rastro, `app.js:4976`) | N | — | — |

### 4.3 Lo que hay que entender del cuadro

1. **Identidad y estado con explicación están resueltos en casi todas**, y los tres mejores ejemplos
   del proyecto son el almacén (`app.js:7649-7660`: cuatro etiquetas con palabras y el motivo al lado),
   el año del cuaderno (`app.js:9105-9133`) y el análisis (`app.js:10512-10521`).
2. **Historial y documentos vinculados no existen como vínculo.** Lo más cercano es el panel de la
   tierra con tres apuntes del año (`app.js:7092-7100`) y el fichero propio de cada registro. **No hay
   ni un solo vínculo entre un documento y el hecho del que es evidencia**, que es lo que pide el
   contrato en la sección 11 (`CONTRATO...md:468`).
3. **La acción principal solo está en 6 de 15 fichas.** En las demás hay dos botones, y son
   CORREGIR (claro) y BORRAR (peligro): `botonesDeCorregirYBorrar` (`app.js:4834-4860`) es **el único
   trozo de ficha que es común a todas**, y **no pone ninguna acción principal**.
4. **La venta es el caso más pobre y el que más choca con S12.** `filasDeLaVenta` (`app.js:9938-9948`)
   da cantidad, tipo, comprador, lote, albarán y dónde — y **ningún importe**. El contrato pide
   «importe conocido, vencimiento, cobrado y pendiente» (`CONTRATO...md:236-237`) y la prueba **A08**
   («Venta con 8.000 kg y sin precio → cantidad conocida, importe pendiente; no ingreso cero»,
   `CONTRATO...md:340`). Es el ejemplo de manual del proyecto —«un hueco es una pregunta»— aplicado
   bien (no se inventa un cero) pero **sin enseñar que falta**: no hay ni una fila que diga «importe
   pendiente».
5. **Un comentario del código está desactualizado y conviene que no engañe a nadie.** `app.js:7953-7954`
   dice que la ficha de una factura «hoy solo BORRAR»; `OTRAS_COSAS.factura` **sí tiene `corregir`**
   (`app.js:4676-4683`) y **no tiene `sin_corregir`**, así que `botonesDeCorregirYBorrar` **sí añade
   CORREGIR** (el `if` de `app.js:4840`). Comprobado: `grep` de `sin_corregir` en `app.js` da solo tres
   líneas, y las tres son de lectura (`app.js:4839`, `4840`, `4953`).

---

## 5. Los estados obligatorios

El texto a cumplir (`CONTRATO_IMPLEMENTACION_CRM.md:99-103`):

```
 99: Estados obligatorios: cargando, vacío nuevo, sin resultados por filtro, acceso
100: restringido, servicio no disponible, copia local antigua, pendiente de enviar,
101: conflicto, guardado y dato incompleto. Cada uno tiene texto y siguiente acción.
102: No presentar una tabla vacía cuando falló la consulta.
```

Aviso de vocabulario: **todo el texto que ve el agricultor vive en `backend/app/textos.py`** y llega
por `GET /api/interfaz` (`backend/app/routers/interfaz.py:69`, `"aviso": textos.INTERFAZ`; y `:71`,
`"mensajes": textos.MENSAJES`). El JavaScript los pide con `t("aviso.<clave>")`, `mensaje("<clave>")` y
`t("<bloque>.<clave>")` (`app.js:294`, `304`, `309`).

| # | Estado | ¿Existe? | Dónde vive el texto | Siguiente acción |
|---|---|---|---|---|
| 1 | cargando | **Parcial** | `textos.py:2976` (solo la cabecera); `textos.py:3463` (muerto); en botones: `textos.py:3923`, `3939`, `3509` | — |
| 2 | vacío nuevo | **Sí**, el mejor cubierto | `textos.py:2961-2975` (asistente), `1447-1493` (maestros), y **una clave por pantalla** | **Sí**: cada uno con su botón |
| 3 | sin resultados por filtro | **Sí, solo en 2 sitios** | `textos.py:1509-1512`; pie: `textos.py:3631`, `3733` | **Sí** (`VERLAS TODAS`) |
| 4 | acceso restringido | **Parcial** | `textos.py:1031-1032`, `996-1000`; el 401 usa un texto **escrito en JavaScript** | **No** en el 401 |
| 5 | servicio no disponible | **Sí**, por casos; sin texto de 5xx | `textos.py:669`, `2977`, `3421`, `2664`, `3546`, `3926`, `855` | **Sí**, casi siempre |
| 6 | copia local antigua | **NO existe — no encontrado** | ninguna clave | **No** |
| 7 | pendiente de enviar | **Sí** | `index.html:17`, `app.js:461-482`, `textos.py:2951-2958`, `549` | **Parcial** |
| 8 | conflicto | **NO existe — no encontrado** | solo el 409 de firma (`textos.py:2754`) | **No** |
| 9 | guardado | **Sí**, una confirmación por tipo | `textos.py:2946`, `2828-2829`, `2171`, `2377`, `2228`, `2306`, `1477`, `3893`, `4081` | **Sí** |
| 10 | dato incompleto | **Sí** | `textos.py:930-940`, `1527`, `3825-3831`, `606/613/620`, `482/498/522`, `2993` | **Sí**, con el botón |

### 5.1 Explicación de cada uno

#### 1. Cargando — **parcial**

Lo único que se ve mientras se carga es **el título de la cabecera cambiado**:

```
3774:   cabeceraTexto.textContent = t("aviso.cargando", "");
```
(`app.js:3773-3774`, texto en `textos.py:2976`: «Un momento…»)

**No hay estado de carga en ninguna lista ni tabla.** `cargarDatos()` espera a un `Promise.all` de
**27 peticiones** (`app.js:3624-3660`) y solo después se pinta nada: durante todo ese tiempo la pantalla
anterior sigue puesta. Hay tres textos de «estoy trabajando» que **sí** se ven, pero son de botón, no de
pantalla: «Leyendo la factura…» (`textos.py:3923` → `nueva_factura.js:63`), «Guardando la factura…»
(`textos.py:3939` → `interpretacion_factura.js:206`) y «Abriendo el cuaderno…» (`textos.py:3509` →
`cuaderno_de_la_junta.js:164`).

**Dos textos muertos, comprobados:**
- «Cargando el mapa…» (`textos.py:3463`): `estado.mapa.cargando` se inicializa a `false`
  (`app.js:5496`) y **nunca se pone a `true`** — grep de `cargando = true` en `backend/web/`: solo
  aparece en una prueba de JavaScript (`tests_js/react.test.js:4833`). El componente lo lee
  (`mapa.js:51`) y **no se llega a ver nunca**.
- «Mandando lo que tenías apuntado…» (`textos.py:2959`): grep de `mandando` en `backend/web/` → cero
  llamadas (solo dos comentarios).

Y `mapa.buscando` se pone a `true` (`app.js:5701`, `app.js:5735`) **pero no se pasa al componente**: en
`app.js:5678` solo viaja `cargando`. Los textos «Mirando en el SIGPAC…» (`textos.py:3430`) y «Apuntando
la parcela…» (`textos.py:3453`) tampoco se ven.

#### 2. Vacío nuevo — **sí, el mejor cubierto**

Hay una frase por pantalla y **casi todas con su botón**, que es la regla de la casa («si le dices al
agricultor que le falta algo, le das el botón que lo arregla»). Los tres casos:

- **El agricultor nuevo** (ni una parcela): `inicio.js:84-96`, con el aviso
  (`maestros.falta_parcela`, `textos.py:1447-1449`) y **un solo botón principal** que lo arregla
  (`anadir-maestro` tipo parcela, `inicio.js:89-95`). Es la excepción documentada del `DESIGN.md:432-436`.
- **Cada sección de «mis cosas»**: siete frases elegidas por convención de nombre
  (`app.js:7254`, `vacio: m(\`sin_${seccion.tipo}\`)`), de `textos.py:1472-1493` («Todavía no tienes
  parcelas.», «Todavía no has apuntado ningún producto comprado.»…), y debajo **siempre** el botón de
  añadir (`mis_cosas.js:154-159`).
- **Cada pantalla de lista**: cuaderno (`textos.py:913`), papeles (`3118-3120`), facturas (`4008`),
  cultivos (`3232-3233`), grupos (`3316-3318`), años (`3894`), ventas (`2374`), planes (`2169`),
  análisis (`2225`), medidas (`2297`).

**El problema grave, y es el que el contrato prohíbe expresamente.** En `cargarDatos()` **cada una de
las 27 peticiones lleva su propio `catch` que la convierte en lista vacía**:

```
3624:   ] = await Promise.all([
3625:     apiJson("/api/campanas/actual").catch(() => null),
...
3629:     apiJson("/api/campanas").catch(() => []),    apiJson("/api/parcelas").catch(() => []),
```
(`app.js:3624-3660`; y así las 27)

Consecuencia: **si el servidor falla, la pantalla dice «Todavía no tienes parcelas»**. Es exactamente
lo que prohíbe `CONTRATO...md:102` («No presentar una tabla vacía cuando falló la consulta»), y además
choca con la regla 7 del proyecto («lo que no se sabe se queda en blanco y se pregunta»): aquí un «no
lo sé» se está presentando como un «no hay».

#### 3. Sin resultados por filtro — **sí, pero solo en dos sitios**

| Dónde | Texto | Salida |
|---|---|---|
| Buscador del asistente | «Con esas letras no encuentro ninguna tierra.» + «Prueba con menos letras, o míralo en la lista entera.» (`textos.py:1509-1512`) | `VERLAS TODAS` (`textos.py:1508`) — `app.js:2150-2165` |
| Buscador de «mis cosas» | los mismos dos textos (`app.js:7200-7210`) | `VERLAS TODAS` — `mis_cosas.js:136-151` |
| Pie de la tabla, con filtro | «12 de 64 tierras · X ha» (`textos.py:3631`) / «12 de 64 tierras» (`textos.py:3733`) | el botón de arriba |

**Lo que falta:** (a) **filtro puesto y ninguna tierra pendiente en «qué hay sembrado» no tiene frase
de «sin resultados»**: `cultivos.js:131` solo enseña el vacío si `parcelas.length === 0 && !aviso.texto`,
y con el filtro puesto `aviso.texto` es el resumen del servidor (`app.js:8630`), que no está vacío;
(b) las otras cuatro tablas no tienen filtro, luego no pueden tener este estado; (c) **no hay etiquetas
removibles** en ningún sitio (ver 3.2 punto 3).

#### 4. Acceso restringido — **parcial, y con el peor texto del programa**

Lo bueno está en la finca y **viene del servidor**:

- `textos.py:1031` — `"no_es_tuya": "Esa finca no es tuya o ya no tienes acceso a ella."` (lo lanza
  `fincas_api.py:98` con 404).
- `textos.py:1032` — `"solo_el_titular": "Solo el titular de la finca puede decidir quién más entra."`
  (403, `fincas_api.py:175`, `218`).
- Y una explicación **permanente** de quién manda, que sí se ve: `textos.py:996-1000`
  (`eres_el_titular` / `no_eres_el_titular` → `quien_entra.js:162`).

Lo malo: **el 401 expulsa al agricultor sin explicarle nada, con un texto escrito en JavaScript** (que
por tanto **no pasa por la prueba de jerga**):

```
319:   if (respuesta.status === 401) {
320:     salir(false);
321:     throw new Error("sin permiso");
322:   }
```
(`app.js:319-322`)

Ese `"sin permiso"` acaba en pantalla por `app.js:3781`
(`avisarDelError(error.message, { sinVolver: true })`). Es decir: **literalmente «sin permiso», en
minúscula y sin botón**, cuando lo que pide la guía es «Te hemos desconectado por seguridad. Vuelve a
entrar.» (`docs/GUIA_UI_UX.md:123`). Matiz que hay que decir: solo se llega ahí si **no** hay copia
guardada de la interfaz, porque con copia el error no se propaga (`app.js:3585-3586`).

**Ojo, no confundir tres textos que se llaman parecido:**
- `INTERFAZ.sin_permiso` (`textos.py:2960`) es «el navegador no deja guardar en el móvil», **no** acceso
  restringido — y **está sin usar**: grep de `sin_permiso` en `backend/web/` solo encuentra
  `sigpac.sin_permiso_red`.
- `SIGPAC.sin_permiso_red` (`textos.py:2664`) es «el SIGPAC no contesta» (sí se usa, `app.js:6009`).
- `FINCAS.no_es_tuya` / `solo_el_titular` son los de verdad.

**Lo que falta:** (a) **no hay ninguna frase en `textos.py` para el 401 / sesión caducada**; (b) el 401
no tiene botón; (c) **no existe ningún concepto de permisos por pantalla**: grep de `permiso` en
`backend/web/` → solo el comentario de `nucleo.js:451` y el `"sin permiso"` de `app.js:321`. El
contrato pide permisos por acción y acceso económico (`CONTRATO...md:305-306`), y el panel de mando no
aplica ningún permiso a sus contadores (que el contrato pide expresamente, `CONTRATO...md:117`).

#### 5. Servicio no disponible — **sí, por casos; sin texto propio de 5xx**

| Caso | Texto | Dónde |
|---|---|---|
| El general | «No se ha podido. Prueba otra vez; si sigue igual, avisa a quien te instaló el programa.» | `textos.py:669-671`; elegido en `app.js:375`, `407`, `411`, `441` y ~20 sitios más |
| El de la cabecera, sin cobertura | «No se ha podido mandar. No te preocupes: sigue guardado en el móvil.» | `textos.py:2977-2979`; `app.js:7470`, `7514`, `10903` |
| El mapa | «No se puede cargar el mapa ahora mismo: para el mapa hace falta conexión. Puede ser la cobertura o que el servicio no esté disponible. Apunta la parcela con su referencia y lo miras en el mapa otro día.» | `textos.py:3421-3424` → `app.js:5747`. **Es el único texto del programa que nombra el servicio no disponible** |
| El SIGPAC | «No se ha podido preguntar al SIGPAC. Puede ser la cobertura o que el servicio no esté disponible…» | `textos.py:2664-2666` → `app.js:6009` |
| Subir el cuaderno de la Junta | «Para subir el cuaderno hace falta conexión…» | `textos.py:3546-3548` → `app.js:5399` |
| Leer una factura | «Para leer la factura hace falta conexión…» | `textos.py:3926-3928` → `app.js:8320` |
| **Si no llegan ni los ficheros de React** | «Esta pantalla no se ha podido abrir. Vuelve a abrir la aplicación; si sigue igual, dile a quien te la instaló que falta un fichero del programa.» + botón «VOLVER A ABRIRLA» | `textos.py:855-859` → `app.js:506-509` y `montar.js:74-102` |

**Lo que falta:** (a) no hay texto que distinga el 5xx; (b) **el fallo de arranque se enseña en crudo**:
`avisarDelError(error.message, …)` (`app.js:3781`) vuelca el mensaje interno del navegador (del tipo
«Failed to fetch»), no un texto de `textos.py` — es la única pantalla a la que se le ha quitado el botón
a propósito (`app.js:3779-3780`); (c) **no hay aviso permanente de «sin conexión»** más allá del de
apuntes pendientes: el evento `offline` solo refresca ese aviso (`app.js:11320`).

#### 6. Copia local antigua — **NO existe. No encontrado.**

No hay ninguna clave en `textos.py` para esto, no hay comparación de la versión del cliente con la del
servidor, y no hay botón de actualizar. Lo que hay, y **por qué no lo cubre**:

- La versión se enseña en el pie, **sin decir que puede ser vieja**:
  `const VERSION_DE_LA_APLICACION = "2026-10-01-57";` (`app.js:3762`) →
  `pie.textContent = … \`versión ${VERSION_DE_LA_APLICACION}\`` (`app.js:3769`). Un número que el
  agricultor no puede interpretar como «estás viendo algo viejo».
- **El service worker sirve la copia guardada en silencio**:
  ```
  310:         caches.match(peticion).then((guardada) => {
  311:           if (guardada) return guardada;
  ```
  (`service-worker.js:309-316`). Y cuando no está, **devuelve la portada guardada**: el agricultor ve la
  pantalla de inicio creyendo que ha pedido otra cosa (`service-worker.js:314`).
- **Los textos de la interfaz también se usan de una copia local sin avisar**: `estado.interfaz =
  leer(CLAVE_INTERFAZ, null)` (`app.js:3585` y `app.js:11329`), y ese `catch` existe justo para
  funcionar sin cobertura (`app.js:3582-3586`).
- No hay escucha de `updatefound` ni `controllerchange`: el único uso del service worker es
  `navigator.serviceWorker.register("/service-worker.js").catch(() => {})` (`app.js:11348`).

**Lo que falta: todo.** No hay ninguna forma de que el agricultor sepa que está viendo una versión
antigua, ni de que actualice.

#### 7. Pendiente de enviar — **sí, y bien hecho**

- El hueco, siempre visible arriba: `<div id="aviso-pendientes" class="aviso oculto" role="status"
  aria-live="polite">` (`index.html:17`).
- Lo pinta `pintarAvisoPendientes()` (`app.js:461-482`), con el texto en singular o plural:
  «1 apunte esperando a que haya cobertura. Se manda solo.» (`textos.py:2956-2958`) /
  «{cuantos} cosas apuntadas esperando a que haya cobertura. Se mandan solas.» (`textos.py:2951-2953`).
- Se apunta a la cola cuando no hay red (`app.js:357-360`), cuando el servidor da 5xx (`app.js:378-379`)
  y cuando la petición revienta (`app.js:383-384`).
- Se manda solo al volver la red: `window.addEventListener("online", …)` (`app.js:11315-11318`).
- **Lo rechazado se aparta en vez de borrarse**, y se avisa en rojo:
  ```
  471:   if (rechazados.length > 0) {
  472:     avisoPendientes.className = "aviso aviso-error";
  473:     const ultimo = rechazados[rechazados.length - 1];
  ```
- Y lo apuntado sin cobertura se confirma con su propio texto: «No hay cobertura. No te preocupes: lo
  hemos guardado en el móvil y se manda solo cuando llegues a casa.» (`textos.py:549-551` →
  `hecho.js:96`).
- La cola **no se borra al salir de la cuenta**, con el motivo escrito (`app.js:3795-3796`).

**Lo que falta:** (a) **no se dice QUÉ está pendiente** (ni la tierra, ni la fecha, ni el tipo): solo el
número (`app.js:481`); (b) de los rechazados se enseña **solo el motivo del último** y **sin botón**: no
hay forma de ver la lista, ni de corregir, ni de reintentar a mano, y no hay ninguna clave de texto para
una pantalla de «lo que no se ha podido mandar»; (c) nada anuncia cuántos quedan mientras se mandan
(`aviso.mandando` sin usar).

#### 8. Conflicto — **NO existe. No encontrado.**

No hay número de versión, `ETag`, `If-Match` ni marca de revisión por registro. Comprobado: grep de
`revision|__version|version_id|lock_version|updated_at` en `backend/app/` → **cero coincidencias**; grep
de `If-Match|version_esperada|optimistic` → cero.

**Los 409 del servidor no son esto**: son «esto está en uso y no se puede borrar»
(`maestros.py:128-137`, `parcelas.py:800`, `planes_api.py:301`, `explotacion.py:128`, `339`,
`documentos_api.py:325`, `analiticas_api.py:521`, `facturas_api.py:933`), con el texto genérico de «en
uso» (`textos.py:734-738`, `B5_en_uso_uno` / `B5_en_uso_varios`).

**Lo más cercano a un conflicto de verdad es de la firma, no de la edición:**

```
364:     if datos.huella != huella_actual:
365:         raise HTTPException(
366:             status_code=status.HTTP_409_CONFLICT, detail=textos.FIRMA["huella_no_cuadra"]
```
(`backend/app/routers/firmas_api.py:364-367`, texto en `textos.py:2754-2756`: «Ese fichero de firma no
corresponde a lo que hay ahora en el cuaderno. Vuelve a descargarlo y fírmalo otra vez.»). Y **sí llega
a pantalla** (`app.js:9601-9602` → `estado.errorFirma` → `app.js:9519`). Pero eso es «este fichero no es
de esta versión del cuaderno», no «otro ha editado el registro».

**Lo que falta: todo.** Corregir manda un `PUT` con el cuerpo entero y **sin comprobar** que lo que hay
en el servidor sea lo que el agricultor tenía delante:

```
3812:     if (correccion) return mandarCambio(\`${ruta}/${correccion.id}\`, "PUT", carga);
```
(`app.js:3811-3814`)

Dos móviles editando lo mismo: **gana el último, en silencio**. Y no hay ni una frase en `textos.py`
para decirlo.

#### 9. Guardado — **sí, con una confirmación por tipo**

| Qué se ha guardado | Título | Pista | Dónde |
|---|---|---|---|
| Un apunte (producto, abono, trabajo, cosecha) | «Apuntado. Si te has equivocado, pulsa DESHACER.» | «Por si te has confundido de tierra, producto o dosis.» | `textos.py:2946`, `2950` → `hecho.js:92`, `194` |
| Una corrección **en vez de** un alta | «Corregido» | «Ya está cambiado. Lo que había antes queda guardado en el historial del cuaderno.» | `textos.py:2828-2829` → `hecho.js:92-93` |
| Plan de abono | «Plan guardado» | «Cuando apuntes un abono, podrás decir que va con él.» | `textos.py:2204`, `2171` → `app.js:9894-9895` |
| Venta | «Venta apuntada» | «Ya se puede responder de dónde salió cada partida.» | `textos.py:2377-2378` → `app.js:10149-10150` |
| Análisis | «Análisis apuntado» | «Guárdalo bien: sirve para varios años.» | `textos.py:2228-2229` → `app.js:10864-10865` |
| Medidas preventivas | «Medidas apuntadas» | «Cuando apuntes un producto, ya saldrá marcado lo que hagas aquí.» | `textos.py:2306-2307` → `app.js:10382-10383` |
| Una ficha de un maestro | — | «Apuntado. Ya lo tienes disponible para cuando lo necesites.» | `textos.py:1477` → `app.js:9313` |
| Un año nuevo | — | «Año guardado. Ya puedes apuntar en él.» | `textos.py:3893` → `app.js:9282` |
| Mis datos | — | «Tus datos están guardados. La portada del cuaderno ya los lleva.» | `textos.py:4081` → `mis_datos.js:86` |
| Un papel | — | «Papel guardado.» | `textos.py:3145` → `app.js:7535` |

**Lo que falta:** (a) **no hay confirmación al guardar ajustes que no existen** (filtros, orden,
columnas): no existen esas preferencias; (b) **`mensajes.guardado_ok` está definido y NO lo usa nadie**:
`textos.py:548` (`"guardado_ok": "Apuntado. Si te has equivocado, tienes unos segundos para deshacer."`),
grep en `backend/web/` → **cero coincidencias**. Es un duplicado huérfano de `INTERFAZ.apuntado_ok`;
(c) el texto de haber subido el fichero de un papel entra por la puerta de los errores
(`estado.errorDocumentos`, `app.js:7535`), aunque se vea bien.

#### 10. Dato incompleto — **sí, de dos formas**

**(a) Avisos que no bloquean al guardar.** El servidor contesta con `avisos: [{mensaje, bloquea}]`, la
interfaz solo para si el aviso bloquea (`nucleo.js:432-435`, `primerAvisoBloqueante`) y los que no
bloquean se enseñan en la pantalla de confirmación (`hecho.js:76`). Los textos: `N5_sin_numeros`
(`textos.py:482-484`), `N9_sin_laboratorio` (`textos.py:498`), `C5_sin_comprador` (`textos.py:522`).

**(b) La lista de «lo que falta», con el botón que lo arregla.** Es el patrón bueno del proyecto:

- En «mi cuaderno»: «Te falta 1 cosa por apuntar» / «Te faltan {N} cosas por apuntar» / «No te falta
  nada por apuntar» (`textos.py:938-940`), servido por `GET /api/cuaderno/falta` (`app.js:3644`) y
  pintado en `mi_cuaderno.js:127-166`. Cada pendiente lleva **el botón que lo arregla** si tiene
  pantalla propia (`app.js:1464-1476`).
- En el panel de mando del ordenador: lo mismo con «1 cosa por completar» / «{cuantas} cosas por
  completar» / «No te falta nada: el cuaderno está al día.» (`textos.py:3829-3831`), y **aquí sí con el
  botón** (`panel_de_mando.js:73-81`).
- Las frases de «a este apunte le falta un dato», del servidor (`cuaderno.py:697`, `706`, `720`):
  «Un apunte no dice por qué se echó el producto. Se puede completar cuando quieras.» (`textos.py:606-607`),
  «Un apunte no dice cuánto producto se echó…» (`textos.py:613`), «Un apunte no dice quién echó el
  producto o con qué máquina…» (`textos.py:620-622`).
- **El caso más visible**, la tierra sin cultivo: «Le falta decir qué tiene sembrado este año»
  (`textos.py:1527` → `app.js:6784` → `tarjeta.js:138`, en ámbar **y con palabras**) y su etiqueta corta
  de tabla «Falta decirlo» (`textos.py:3690` → `app.js:6980`).
- Ficheros que faltan: `textos.py:3147` (`documentos.js:56`), `textos.py:4021` (`facturas.js:81`),
  `textos.py:3138` («Hace falta», `nuevo_documento.js:90`).
- Y lo que falta para poder apuntar un dictado: `textos.py:2993` → `borrador.js:103-107`.

**Lo que falta:** (a) **`V19_incompleto` es texto muerto**: `textos.py:425-427` («Falta algo por poner,
pero puedes guardarlo ahora y completarlo cuando quieras. Queda apuntado en la lista de lo que falta.»)
— grep en todo el proyecto: **solo aparece en `textos.py:425`**, no lo lee ninguna pantalla ni ningún
router. La idea general está escrita y no la usa nadie; lo que se ve son las frases concretas A6/A7/A9;
(b) **no hay marca de «incompleto» en la ficha del registro** más allá de la tierra sin cultivo: un
apunte al que le falta la dosis **se enseña igual que uno completo**, y solo se entera quien mire la
lista; (c) **no hay contador de registros sin dato**, que S01 pide expresamente
(`CONTRATO...md:115`: «Mostrar fecha de corte, campaña y número de registros sin dato»).

### 5.2 Cuadro final de los estados

| Estado | Existe | Texto y salida | Lo que falta, en una línea |
|---|---|---|---|
| cargando | Parcial | «Un momento…» en la cabecera | No hay carga por pantalla ni en las listas; 3 textos muertos |
| vacío nuevo | **Sí** | una frase por pantalla, con botón | **Se confunde con el fallo de consulta** |
| sin resultados por filtro | Sí, en 2 sitios | «Con esas letras no encuentro ninguna tierra.» + `VERLAS TODAS` | Filtros removibles y el pie «N de M» en el móvil |
| acceso restringido | Parcial | frases buenas de la finca (del servidor) | El 401 dice «sin permiso» **desde el JavaScript**, sin botón |
| servicio no disponible | Sí, por casos | 7 textos distintos + el aviso de emergencia de React | Falta el 5xx, y el arranque vuelca el error crudo del navegador |
| copia local antigua | **NO** | ninguna | Todo |
| pendiente de enviar | **Sí** | singular/plural + rechazados en rojo | No dice *qué* está pendiente; los rechazados no tienen salida |
| conflicto | **NO** | ninguna | Todo (sin versión ni `If-Match`: gana el último, en silencio) |
| guardado | **Sí** | una confirmación por tipo | `mensajes.guardado_ok` huérfano; nada al guardar preferencias |
| dato incompleto | **Sí** | lista de lo que falta, con el botón | `V19_incompleto` huérfano; no hay marca en la ficha ni contador |

---

## 6. Responsive real

### 6.1 Los tres anchos, y qué regla gobierna cada cosa

**Antes de nada, una advertencia que invalida cualquier medida hecha de memoria: los `@media` usan
`rem`, y el `rem` de un `@media` sale del tamaño de letra del elemento raíz (`html`), no del `body`.**
Aquí `body { font-size: var(--letra) }` (`estilos.css:86`) y `body.letra-grande { --letra: 21px }`
(`estilos.css:69-72`) **no cambian el `rem`**: cambian una variable. El `html` no tiene `font-size`
puesto en ninguna parte, así que **1 rem = 16 px siempre**, incluso con la letra grande puesta. Por
tanto:

| `rem` de las reglas | px reales | Qué significa |
|---|---|---|
| 44 rem | 704 px | el ancho máximo de la columna de móvil |
| 63.99 rem | 1023.84 px | el último píxel «de móvil» |
| **64 rem** | **1024 px** | **el primer píxel «de ordenador»** |
| 71.99 rem | 1151.84 px | por debajo, el panel de detalle pasa debajo de la tabla |
| 72 rem | 1152 px | a partir de aquí caben tabla y panel al lado |

**Solo hay cinco `@media` en todo `estilos.css`** (comprobado con `grep`), y tres de ellos son los
mismos dos puntos de corte:

| Línea | Regla | Qué gobierna |
|---|---|---|
| `estilos.css:1194` | `@media (min-width: 64rem)` | **todo el ordenador**: menú lateral, barra, esconder la cabecera de móvil, el ancho de la pantalla, la tabla, el panel de detalle y el panel de mando |
| `estilos.css:1380` | `@media (min-width: 64rem)` | qué forma de la lista se enseña: `.solo-escritorio` (la tabla) o `.solo-movil` (las tarjetas) |
| `estilos.css:1688` | `@media (max-width: 71.99rem)` (dentro de la anterior) | **el panel de detalle pasa de ir al lado a ir debajo** |
| `estilos.css:1809` | `@media (max-width: 63.99rem)` | esconde `.solo-escritorio` |
| `estilos.css:1817` | `@media (max-width: 63.99rem)` | esconde el armazón entero (`.marco`) |

### 6.2 A 390 px (móvil)

- **Nada del ordenador se aplica**: ningún `min-width: 64rem` casa. Gobierna el CSS de base.
- **El armazón no se ve**: `.marco { display: none }` (`estilos.css:1817-1821`). No hay menú lateral ni
  barra: se entra por la pantalla de inicio, como siempre.
- **La cabecera de móvil manda**: pegajosa arriba (`estilos.css:97-108`, `position: sticky; top: 0;
  z-index: 10`), con el título que vuelve al inicio y los dos botones de letra y salida.
- **La pantalla es una columna de como mucho 44 rem** (704 px), centrada y con 0,8 rem de aire:
  `.pantalla { padding: 0.8rem; max-width: 44rem; margin: 0 auto; }` (`estilos.css:166-170`). A 390 px,
  el ancho útil es **390 − 2×12,8 = 364 px**.
- **Las listas son tarjetas o renglones**: `.solo-escritorio { display: none }` (`estilos.css:1372-1373`
  y `1809-1813`), así que **todas las tablas desaparecen** y se ven `.tarjetas` (`estilos.css:942`) o
  `.lista` (`estilos.css:612-624`).
- **Ningún elemento tocable baja de 64 px** (`--toque: 64px`, `estilos.css:53`) y el botón principal
  mide 104 px (`DESIGN.md:336-337`).
- **El aviso de lo pendiente de mandar** sigue arriba, fuera del armazón (`index.html:17`).
- El pie con la versión: `#pie` (`index.html:40`), centrado (`estilos.css` base).

### 6.3 A 1024 px (portátil pequeño)

**A 1024 px se está exactamente en el primer píxel del modo ordenador**: `min-width: 64rem` casa
(1024 ≥ 1024). Es decir, el ancho que el contrato nombra expresamente
(`CONTRATO...md:395-396`: «a 1024 px no ocultes Acciones; panel lateral pasa debajo») cae **justo en el
límite**, y a 1023 px se vería como un móvil.

Lo que gobierna, todo dentro de `@media (min-width: 64rem)` (`estilos.css:1194-1354`):

| Qué | Regla | Línea |
|---|---|---|
| Menú lateral fijo de 17 rem (272 px) | `.marco .menu { position: fixed; width: var(--ancho-menu) }` | `estilos.css:1197-1210` |
| Barra de arriba fija, a partir del menú | `.marco .barra { position: fixed; left: var(--ancho-menu) }` | `estilos.css:1265-1280` |
| La cabecera de móvil se esconde | `header.cabecera { display: none }` | `estilos.css:1332-1335` |
| La pantalla deja de ser una columna | `main.pantalla { max-width: none; margin: 0 0 0 var(--ancho-menu); padding: calc(var(--alto-barra) + 1.2rem) 2rem 2rem }` | `estilos.css:1337-1342` |
| Se ven las tablas | `.solo-escritorio { display: block }` y `.solo-movil { display: none }` | `estilos.css:1380-1387` |
| **El panel de detalle pasa DEBAJO de la tabla** | `@media (max-width: 71.99rem) { .tabla-y-panel { grid-template-columns: minmax(0, 1fr) } }` | `estilos.css:1688-1691` |

**La cuenta del ancho útil a 1024 px:** 1024 − 272 (menú) − 2×32 (los 2 rem de aire a cada lado) =
**688 px** para la tabla.

**La cuenta del panel, que es la que explica por qué pasa debajo** (y está escrita en el CSS, «medida y
no inventada», `estilos.css:1681-1687`):

```
1684:      (su `min-width`). Total: 17 + 2 + 2 + 20 + 1 + 30 = **72 rem (1152 px)**. Por debajo de eso, con el panel
1685:      al lado, a la tabla le quedan 22 rem y **deja fuera la columna de Acciones**
```

### 6.4 ¿A 1024 px las Acciones de las tablas quedan visibles?

**Sí, y hay tres razones que se pueden citar, con una salvedad que hay que decir.**

1. **El panel de detalle pasa debajo de la tabla**, así que la tabla no compite con él:
   `estilos.css:1688-1691`. Y el `position: sticky` del panel se desactiva
   (`estilos.css:1693-1696`, `.panel-detalle { position: static }`).
2. **Dentro de su contenedor, la tabla conserva un ancho mínimo y, si no cabe, se desplaza en
   horizontal** en vez de apretarse: `.tabla-scroll { overflow-x: auto }` y
   `.tabla-scroll .tabla { min-width: 30rem }` (`estilos.css:1699-1708`). A 1024 px, 30 rem = 480 px,
   y hay 688 px: **no hace falta desplazar nada**.
3. **La columna de Acciones no se parte y no se lleva el ancho de los datos**:
   `.tabla-acciones { width: 1%; white-space: nowrap }` (`estilos.css:1482-1486`), y dentro de ella la
   barra de botones **no se envuelve** (`estilos.css:1488-1496`, con el fallo que eso arregló contado:
   «CORREGIR y BORRAR se ponían uno debajo de otro»).

**La salvedad, y es importante: dos de las seis tablas llevan panel y cuatro no, y el contenedor
`.tabla-scroll` solo existe cuando la tabla lleva panel.** Está escrito en la pieza:

```
230:   if (!tabla.panel) return soloLaTabla;
231:   return html`<div className="tabla-y-panel">
232:     <div className="tabla-scroll">${soloLaTabla}</div>
```
(`tabla.js:230-232`)

Es decir: las tablas **de tierras y de almacén** van dentro de `.tabla-scroll` (tienen panel), y las de
**cuaderno, facturas, años y sembrado** —que son justo las que más columnas tienen: **8** la de facturas,
**7** la de apuntes y la de cultivos— **van sueltas, sin contenedor que las desplace**. Con 688 px y
`table-layout: auto`, esas cuatro tablas no se desplazan: **envuelven el texto** de las celdas (solo
`.tabla-numero` y `.tabla-acciones` llevan `white-space: nowrap`, `estilos.css:1466-1470` y `1483-1486`),
y por eso Acciones queda visible aunque las filas crezcan de alto.

**No comprobado en navegador.** Las tres razones salen del CSS y del JSX, no de haberlo mirado. Lo que sí
se puede afirmar sin reservas es el mecanismo: **el ancho de 1152 px del CSS es el que decide si el panel
va al lado, y a 1024 px no va al lado.**

### 6.5 A 1440 px (monitor normal)

- 1440 px = 90 rem: **por encima de 72 rem**, así que aquí sí caben **la tabla y su panel al lado**:
  `.tabla-y-panel { grid-template-columns: minmax(0, 1fr) 20rem }` (`estilos.css:1674-1679`), y el panel
  vuelve a ser `position: sticky` (`estilos.css:1722-1725`, `top: calc(var(--alto-barra) + 1rem)`).
- **Ancho útil de la tabla:** 1440 − 272 (menú) − 64 (aire) = 1104 px; menos 320 px del panel y 16 de
  hueco = **768 px ≥ 480 px** del `min-width`: cabe sin desplazarse.
- **El panel de mando (S01) se ve aquí**: es `.solo-escritorio` (`inicio.js:147-157`) y solo existe
  dentro de `@media (min-width: 64rem)` (`estilos.css:1511-1515`, comentario: *«Solo existe en el
  ordenador»*). Sus cuatro tarjetas se colocan con `auto-fit` (`estilos.css:1519-1526`), y sus dos
  columnas (lo que falta / los últimos) con `minmax(0, 1.1fr) minmax(0, 1fr)`
  (`estilos.css:1559-1565`).
- La cabecera de la tabla se queda pegada al bajar: `position: sticky; top: var(--alto-barra)`
  (`estilos.css:1408-1419`).

### 6.6 Un hueco real del responsive, deducido del código

**En el ordenador, las seis listas de maestros de «mis cosas» no se ven.** La sección de las tierras
tiene tabla (`app.js:7194` → `mis_cosas.js:69`), pero **las otras seis secciones no** (`app.js:7216-7242`:
solo llevan `lista: estado.productos`, etc., sin `tabla`), y su lista de renglones está marcada
`.solo-movil`:

```
109:           : html`
110:               <ul className="lista solo-movil">
```
(`mis_cosas.js:109-134`)

Y `.solo-movil` es `display: none` a partir de 64 rem (`estilos.css:1385-1387`). Es decir: a 1024 y a
1440 px, las secciones «Productos», «Abonos», «Quién aplica», «Asesores», «Máquinas» y «Naves y
almacenes» de «Mis parcelas, productos y máquinas» **se quedan con su título, su pista, su cuenta y su
botón de añadir, y sin un solo elemento dentro**. La tabla de las tierras sí se ve.

**No comprobado en navegador**, pero el mecanismo es de una sola regla y se puede seguir de punta a
punta: `solo-movil` → `display: none` a ≥64 rem; la `<ul>` no tiene ninguna otra clase que la rescate;
no hay `.lista` dentro del `@media` que la vuelva a mostrar (grep de `^  .lista` en `estilos.css`: cero
coincidencias). **Es el candidato número uno a comprobar en pantalla en cuanto se pueda** — y encaja con
lo que el propio `docs/REACT.md:773-776` deja pendiente («las tablas de las listas que quedan (los seis
maestros, los análisis y las ventas)»).

---

## 7. Huecos frente a S01, S02 y S03

### 7.1 S01 — Inicio de gestión (`/inicio`)

**Lo que pide** (`CONTRATO...md:110-118`): tres zonas (pendientes, resumen de campaña y agenda);
tarjetas de tierras sin cultivo, trabajos previstos, documentos por revisar, cobros y pagos vencidos e
inspecciones próximas; **pulsar cualquier cifra abre su lista filtrada**; fecha de corte, campaña y
número de registros sin dato; «Con los importes registrados» y no beneficio; personalización; permisos
económicos también en los contadores.

**Lo que hay ya:**

| Qué | Dónde |
|---|---|
| El panel de mando, como pantalla propia del ordenador | `react/piezas/panel_de_mando.js:152-224`; lo prepara `datosDelPanelDeMando()`, `app.js:990-1128`; se monta en `inicio.js:145-158` y **solo se ve a ≥64 rem** |
| Cuatro tarjetas de número | `app.js:1016-1044`: apuntes del año, hectáreas tratadas (con el total de la finca como detalle), kilos vendidos, tierras (con «N sin decir qué tienen este año» o «Todas con su cultivo dicho») |
| «Lo que falta por completar», con el botón que lo arregla | `app.js:1046-1058` y `panel_de_mando.js:50-91`; es **la misma lista** que la de «mi cuaderno» (`app.js:983-984`), a propósito |
| Los últimos cinco apuntes, en una tabla corta | `app.js:1060-1068`, `panel_de_mando.js:94-138`; el enlace a la lista entera, `app.js:1102-1108` |
| Apuntar algo de hoy (3 botones) y el cierre (papel, datos, firma) | `app.js:1070-1126` |
| El aviso que desbloquea al agricultor nuevo | `inicio.js:79-97` + `app.js:143` |
| Fecha de corte | **No.** No hay ninguna clave ni ningún dato de «a fecha de» |
| Campaña | **Sí, en el `h1`**: «Hola, David · 2026» (`inicio.js:137-142`) |
| Permisos económicos en los contadores | **No existe ningún permiso por pantalla** (apartado 5.1, estado 4) |

**Lo que falta:**

1. **Las cifras no se pueden pulsar.** El componente de cada tarjeta es un `<li>` con `<p>` dentro, sin
   `data-accion` y sin ser botón: `panel_de_mando.js:35-47`. El contrato pide *«Pulsar cualquier cifra
   abre su lista filtrada»* (`CONTRATO...md:115-116`), y **eso exige exactamente lo que no existe: el
   filtro en la tabla de destino** (apartado 3.2, punto 3).
2. **Faltan cuatro de las cinco tarjetas que nombra el contrato**: tierras sin cultivo (está, dentro de
   la tarjeta de tierras), **trabajos previstos, documentos por revisar, cobros y pagos vencidos,
   inspecciones próximas** — no hay ninguna de las cuatro. Y no es un olvido de diseño: **el número de
   dinero no existe en el programa**, y está escrito por qué al lado de la tarjeta que ocupa su sitio
   (`textos.py:3803-3806`: *«la tarjeta del «gasto en fitosanitarios» en euros, porque ese número no
   existe en el programa»*). Lo mismo en `panel_de_mando.js:25-27`.
3. **No hay agenda.** El contrato pide tres zonas y hay dos: pendientes y resumen. Los «últimos apuntes»
   son historial, no agenda.
4. **No hay personalización**: no se pueden ordenar ni ocultar tarjetas, ni restaurar la vista
   (`panel_de_mando.js:152-224`: las cuatro tarjetas salen siempre, en el mismo orden).
5. **Nada de esto se ve en el móvil**: a <64 rem manda la pantalla de inicio de siempre, con sus seis
   botones (`inicio.js:159-197`). S01 dice «Inicio de gestión» y el contrato habla de despacho
   (`CONTRATO...md:20`), así que puede ser aceptable, pero **conviene decidirlo, no heredarlo**.
6. **No hay contador de registros sin dato** (solo el de tierras sin cultivo).

**Lo que se puede reutilizar:** el patrón de `LoQueFalta` (`panel_de_mando.js:50-91`) —el pendiente, su
frase y **el botón que lo arregla** en el mismo renglón— es exactamente la forma que necesitan las
tarjetas nuevas; y `Numero` (`panel_de_mando.js:35-47`) solo necesita envolverse en un botón con
`data-accion` para cumplir el «pulsar la cifra». Los datos ya están cargados: `datosDelPanelDeMando`
sale de `estado` sin una petición más (`app.js:978-979`).

### 7.2 S02 — Tierras y mapa (`/tierras`)

**Lo que pide** (`CONTRATO...md:120-135`): tabla con nombre, municipio, área gestionada, cultivo actual,
último trabajo, pendientes y estado de geometría; ocho filtros; **vista mapa que sincroniza la selección
con la tabla**; tierras sin geometría en una lista aparte; acciones abrir / planificar / registrar /
comparar campañas / exportar; edición múltiple con vista previa; siete capas con leyenda, fecha, fuente
y calidad; polígonos con huecos y multipolígonos; digitalización con cierre de anillo y
auto-intersecciones; geolocalización con precisión; mapa sin red que avisa.

**Lo que hay ya:**

| Qué | Dónde |
|---|---|
| La pantalla «Mis parcelas, productos y máquinas» | `pantallaMisCosas`, `app.js:7181-7317` → `mis_cosas.js` |
| La tabla de tierras, 5 columnas (Nº, Nombre, Hectáreas, Qué tiene este año, Acciones) | `tablaDeTierras`, `app.js:6942-7019` (las columnas, `app.js:6950-6956`) |
| Ordenar por cualquier columna, con el pie de hectáreas | `app.js:6910-6920`, `6999-7008` |
| El buscador de tierras (nombre y referencia SIGPAC) | `app.js:2213-2229`; filtra con `tierrasQueCasen`, `app.js:6759` |
| El panel de la tierra elegida, al lado | `panelDeLaTierra`, `app.js:7060-7112` |
| El dibujo de la forma de cada tierra, en la tarjeta y en el panel | `formaDeLaTierra`, `app.js:2291-2302`; `tarjeta.js`; `tabla.js:140-143` |
| **El mapa del SIGPAC**, con foto, linderos, el trozo marcado y «estoy aquí» | `pantallaMapa`, `app.js:5616-5682` → `pantallas/mapa.js` |
| La consulta por un punto y el alta de la tierra desde el mapa | `mapa-tocar` (`app.js:11054`), `mapa-preguntar` (`11049`), `mapa-apuntar` (`11056`); el estado, `estadoDelMapa`, `app.js:5485-5507` |
| La geolocalización | `pedirLaUbicacion`, `app.js:5586-5601` (`enableHighAccuracy: true`) |
| El aviso de que el mapa necesita conexión | `textos.py:3419` (`mapa.necesita_conexion`) → `mapa.js:156`, `app.js:5265` |
| Editar/corregir una tierra | `cosa-corregir` (`app.js:11222`) con el asistente, y borrar (`cosa-borrar`, `11225`) |

**Lo que falta:**

1. **No hay vista mapa en «Tierras y mapa».** El mapa **solo existe dentro del alta de una tierra**:
   cuelga de `pantallaTraerOApuntar` (`app.js:5232-5269`) y su único botón de entrada es
   `mapa-abrir` (`app.js:10966`). No hay nada que **sincronice la selección con la tabla**, que es la
   mitad de lo que pide S02 (`CONTRATO...md:124-125`): el mapa no sabe de la tabla y la tabla no sabe del
   mapa.
2. **Cuatro columnas de siete no están.** Faltan **municipio**, **último trabajo**, **pendientes** y
   **estado de geometría** (`app.js:6950-6956`). El municipio y la referencia SIGPAC **existen en los
   datos** (`app.js:6791`) y están a propósito fuera de la tabla, con el motivo escrito
   (`app.js:6946-6949`: *«El pueblo y la referencia del SIGPAC están en el panel de al lado»*). Pero
   **«último trabajo», «pendientes» y «estado de geometría» no están ni en los datos de la ficha**.
3. **Siete de los ocho filtros no existen.** Solo hay el buscador (que hace de «por nombre»). Faltan
   cultivo, municipio, secano/regadío, titularidad, campaña, sin cultivo, trabajo
   realizado/pendiente y sin forma. **Y la titularidad no está ni en el modelo** (no comprobado en
   detalle: se ha mirado el frontend, no `models.py` entero).
4. **Las tierras sin geometría no tienen su lista aparte.** Se mezclan en la misma tabla (y el dibujo,
   correctamente, no se inventa un cuadrado: `formaDeLaTierra`, `app.js:2291-2302`), pero el contrato
   pide que «permanezcan en una lista» propia (`CONTRATO...md:125`).
5. **De las cinco acciones que pide S02 (abrir, planificar trabajo, registrar trabajo, comparar
   campañas, exportar), hoy hay dos**: abrir lo que hay sembrado (`cultivo-decir`) y corregir/borrar.
   **No hay planificar, ni registrar un trabajo desde la tierra, ni comparar campañas, ni exportar.**
6. **No hay edición múltiple** (ni selección múltiple, apartado 3.2 punto 6).
7. **Las siete capas del contrato no existen.** El mapa tiene **dos**: `foto` (ortofoto) y `linderos`
   (`app.js:5547-5559` y `5662-5666`), y `backend/app/routers/mapa.py` las sirve **como imágenes, no
   como capas conmutables**. **No hay** capas de recintos oficiales, tierras gestionadas, cultivo,
   trabajos ni avisos; y **no hay leyenda, ni fecha de la imagen, ni fuente, ni indicador de calidad**
   (`mapa.js:35-54`: solo dos `<img>` y un `<svg>`).
8. **No hay digitalización.** El mapa solo **pregunta por un punto** (`mapa-tocar`, `mapa-preguntar`):
   no se dibuja ni se edita un polígono, así que no hay cierre de anillo, ni detección de
   auto-intersecciones, ni vista previa de área, ni marca de origen manual. Los polígonos con huecos y
   multipolígonos **no se pueden comprobar** porque no hay dibujo propio.
9. **La geolocalización no dice la precisión**: `pedirLaUbicacion` devuelve solo `{lon, lat}`
   (`app.js:5592-5594`) y **descarta `posicion.coords.accuracy`**. Pedir la ubicación sí requiere una
   acción del usuario (`mapa-estoy-aqui`, `mapa.js:149`, `mapa.js:159-163`), que es la otra mitad del
   requisito.
10. **El mapa sin red avisa** («El mapa necesita conexión…», `textos.py:3419`) y **no inventa un
    cuadrado**: cuando no hay centro, dice y ofrece «estoy aquí» (`mapa.js:159-163`, y el motivo escrito
    en `mapa.js:25-26`). Esa parte **sí** cumple. Lo que no hay es la idea de «conserva solo lo
    descargado».

**Lo que se puede reutilizar:** la pieza `Tabla` con su `Panel` (`tabla.js`) ya soporta columnas
ordenables, celda-botón, fila elegida y panel; añadir municipio, último trabajo y pendientes es
**añadir celdas y su dato en `tierrasParaMisCosas`** (`app.js:6750-6809`), no tocar el componente. El
`tabla-scroll` (`estilos.css:1699-1708`) ya resuelve el ancho cuando se añadan columnas. Y para la vista
mapa, el estado y el pintado ya existen: `estadoDelMapa` (`app.js:5485-5507`), `direccionDeLaImagen`
(`app.js:5547-5559`) y `aPixeles` (`app.js:5530-5536`) son exactamente lo que hace falta para pintar
**los polígonos que ya están guardados**.

### 7.3 S03 — Ficha de tierra (`/tierras/:id`)

**Lo que pide** (`CONTRATO...md:137-144`): resumen fijo con mapa, campaña/cultivo, superficie,
referencias y próximo trabajo; secciones **Historia, Cultivos, Productos y abono, Cosecha y cuentas,
Documentos y PAC**; en Historia, fecha, trabajo, superficie, máquina/persona, insumos y revisión;
separar «Última labor», «Cultivo declarado», «Observación de campo» y «Estimación»; comparación anual
con variedad, siembra, cosecha, rendimiento y coste conocido.

**Lo que hay ya: la ficha de tierra es un PANEL de 20 rem, y no tiene secciones.**

| Qué | Dónde |
|---|---|
| El panel (solo ordenador, solo al lado de la tabla) | `panelDeLaTierra`, `app.js:7060-7112`; pintado por `Panel`, `tabla.js:125-181` |
| Identidad: «Tierra n.º N» | `app.js:7074` |
| Referencia SIGPAC y cultivo del año (con su nombre delante) | `app.js:7077-7078` (vienen de `tierrasParaMisCosas`, `app.js:6780-6783`) |
| Superficie | `app.js:7079-7082` (`formateaNumero` + «ha») |
| Municipio | `app.js:7083` |
| El dibujo de la forma (el «mapa» de la ficha) | `app.js:7088` → `tabla.js:139-144` |
| Aviso de lo que le falta (la tierra sin cultivo) | `app.js:7085` |
| «Lo último que le has hecho»: **los 3 últimos apuntes del año**, con fecha | `app.js:7092-7100`; texto, `textos.py:3757` |
| Acción principal: decir/ver lo que hay sembrado | `app.js:7101-7108` |
| Corregir y borrar la tierra | `app.js:7109` |
| **La ficha del móvil distinta**: la tarjeta de «mis cosas» | `tarjeta.js:77-167`, con los datos de `app.js:6775-6807`: nombre, «Tierra n.º N», forma, referencia SIGPAC, cultivo, aviso |
| Ver y cambiar el cultivo de una tierra | `pantallaDecirCultivo`, `app.js:8740-8780` |

**Lo que falta:**

1. **La ficha de tierra no tiene pantalla ni dirección.** Es un panel que **solo existe en el ordenador
   y solo al lado de la tabla** (`.panel-detalle`, `estilos.css:1722-1730`, dentro del
   `@media (min-width: 64rem)`). En el móvil, lo más parecido es la tarjeta de «mis cosas», que enseña
   **menos**: no tiene hectáreas, ni municipio, ni los últimos apuntes, ni el aviso completo.
2. **Cinco de las cinco secciones no existen.** No hay Historia, ni Cultivos, ni Productos y abono, ni
   Cosecha y cuentas, ni Documentos y PAC. Lo único que se acerca a «Historia» son **tres apuntes del
   año en curso**, sin superficie por apunte, sin máquina, sin persona, sin insumos y sin revisión.
3. **No hay «próximo trabajo»** en ninguna forma.
4. **El resumen no lleva la campaña como dato propio**: el cultivo sí (el «actual» de `/api/cultivos`,
   `app.js:6766`), pero **no dice de qué campaña es**.
5. **No se separan «Última labor», «Cultivo declarado», «Observación de campo» y «Estimación».** La
   lista de apuntes ya distingue el tipo (`fichaDeUnApunte`, `app.js:1214-1307`: tratamiento,
   fertilización, cosecha, labor), pero **la ficha de la tierra no lo usa**: solo concatena fecha y
   etiqueta (`app.js:7096-7098`).
6. **No hay comparación anual** de variedad, siembra, cosecha, rendimiento ni coste. Lo más cercano es
   la tabla de «qué hay sembrado», que enseña «Otros años» en texto (`tablaDeLosCultivos`, `app.js:8695`),
   y el plan de abono, que compara previsto/aplicado/queda (`app.js:9627-9643`) — pero eso es del plan,
   no de la tierra.
7. **No hay nada de dinero**: ni coste conocido, ni cuentas. Con el motivo ya escrito en el proyecto:
   ese número no existe (apartado 7.1, punto 2).
8. **El historial depende de lo que esté cargado en memoria.** El comentario lo dice: *«Se sacan de los
   mismos apuntes del año que ya están cargados, sin pedir nada más al servidor»* (`app.js:7089-7091`).
   Es una decisión buena para el rendimiento, pero significa que **la ficha no puede enseñar historia de
   otros años** sin cambiar de dónde salen los datos.

**Lo que se puede reutilizar:** prácticamente todo el contenido ya existe, repartido:

- **Historia** → `losApuntesDelAnio()` (`app.js:1318-1341`) + `fichaDeUnApunte` (`app.js:1214-1307`), que
  ya trae superficie, producto, dosis, plazo de seguridad y cultivo por apunte.
- **Cultivos** → `/api/cultivos` ya devuelve `actual`, `anteriores` y `falta_decirlo` por tierra
  (`app.js:6765-6766`, `8695`), y la pantalla «qué hay sembrado» ya lo pinta.
- **Productos y abono** → el almacén (`/api/productos/cesta/situacion`, `app.js:3641`) y el plan de abono
  (`app.js:9623-9702`) ya están en memoria.
- **Cosecha** → `estado.ventas` (`app.js:1007-1008`) y las cosechas de `estado.labores`
  (`app.js:1322-1325`).
- **Documentos** → `/api/documentos` (`app.js:3640`) ya trae los papeles con su carpeta, aunque **hoy no
  tengan ningún vínculo con una tierra** (apartado 4.3, punto 2): ese vínculo es el trabajo que falta.
- Y el panel vacío ya dice qué hacer en vez de quedarse en blanco (`textos.py:3746`), que es el patrón
  que la ficha nueva tiene que conservar.

### 7.4 Los cinco huecos más importantes, en una tabla

| # | Hueco | Fichero:línea | A qué pantalla afecta |
|---|---|---|---|
| 1 | **No hay selector de campaña, y la campaña activa es siempre la más nueva** (tampoco hay selector de explotación en la cabecera) | `backend/app/routers/explotacion.py:145-151`, `app.js:614`, `marco.js:79-89`, `textos.py:3773-3778` | S01, S02, S03 (y todas) |
| 2 | **El mapa solo sirve para dar de alta una tierra: no hay vista mapa en «Tierras y mapa»**, ni capas, ni sincronía con la tabla | `app.js:5237-5243`, `app.js:10966`, `mapa.js:125-170`, `app.js:5547-5559` | S02 |
| 3 | **La ficha de tierra es un panel de 20 rem del ordenador, sin ninguna de las cinco secciones** (Historia, Cultivos, Productos y abono, Cosecha y cuentas, Documentos y PAC), y sin comparación anual | `app.js:7060-7112`, `tabla.js:125-181`, `estilos.css:1722-1730` | S03 |
| 4 | **A la tabla de tierras le faltan cuatro columnas y siete de los ocho filtros**, y no hay edición múltiple ni exportación | `app.js:6950-6956` (columnas), `app.js:2213-2229` (el único filtro), `CONTRATO...md:122-127` | S02 |
| 5 | **En el inicio de gestión las cifras no se pueden pulsar y falta la agenda, la fecha de corte y cuatro de las cinco tarjetas** | `panel_de_mando.js:35-47` (tarjeta sin `data-accion`), `app.js:990-1128`, `textos.py:3803-3806` | S01 |

**Y el hueco que los cruza a los tres:** **no hay ninguna dirección que abra un registro** (no hay
enrutador: apartado 1.5), así que «cada registro tiene una ficha única accesible desde todos sus
contextos» (`CONTRATO...md:82-83`) **no se cumple hoy en ningún sitio**. Es la pieza que T04 («Armazón
común, contexto, tabla y ficha reutilizables», `CONTRATO...md:361`) necesita antes que ninguna otra.

---

## 8. No comprobado

Lo que sigue **no se ha podido comprobar** y por tanto no se afirma en ninguna parte de este informe.

1. **Nada visual se ha visto en un navegador.** El encargo lo prohibía expresamente (los puertos y las
   bases los está usando el dueño del proyecto). **Todo el apartado 6 está deducido del CSS y del JSX.**
   En particular, **no comprobado**: que las Acciones se vean a 1024 px en la práctica (§6.4), que las
   seis listas de maestros desaparezcan en el ordenador (§6.6), ni el reparto real de anchos.
2. **No se ha ejecutado nada**: ni `pytest`, ni `node --test`, ni `scripts/humo.py`, ni
   `scripts/comprobar_en_un_navegador.py`. **No se ha leído la suite de pruebas**, así que no se sabe qué
   contrato tienen fijado estas pantallas ni si alguna de las afirmaciones de aquí choca con una prueba.
3. **No se han leído enteros `app.js` (11 351 líneas), `textos.py` (4 290 líneas) ni `estilos.css`
   (1 821 líneas).** Se han leído los tramos citados y se ha buscado con `grep`. Un dato que viva fuera
   de esos tramos y no case con ningún patrón buscado **se puede haber pasado**.
4. **No se ha mirado el backend más allá de lo citado.** No se ha auditado `models.py` ni `schemas.py`
   entero, así que **no comprobado**: si la titularidad de una tierra existe en el modelo (§7.2, punto
   3), si una venta guarda importe (§4.3, punto 4) o si hay un vínculo documento↔hecho en la base de
   datos. Lo que se afirma sobre esas cosas es **sobre lo que se pinta**, no sobre lo que se guarda.
5. **No se ha comprobado el uso real de todas las claves de `textos.py`.** Se han buscado las que se
   citan (y se han encontrado tres huérfanas: `V19_incompleto`, `guardado_ok`, `mandando`), pero
   **puede haber más** en bloques que no se han abierto enteros.
6. **No se ha comprobado qué devuelve de verdad un 5xx** del servidor (si trae `detail` o no), así que
   «cae en `no_se_pudo` o en el `detail` del servidor» es una lectura del código, no una medición.
7. **El número de versión citado** (`2026-10-01-57`, `app.js:3762`) es el del repositorio local, no el
   de lo desplegado.
8. **No se ha cruzado el menú del contrato con el real, módulo a módulo.** El contrato pide doce módulos
   de despacho (Inicio, Tierras y mapa, Trabajos, Cultivos y PAC, Almacén, Documentos, Cuentas, Personas,
   Maquinaria, Cuaderno, Normativa, Ajustes —`CONTRATO...md:80-81`) y el menú real tiene **dieciséis**
   entradas distintas (`app.js:529-546`). **No hay módulos de Trabajos, Cuentas, Personas, Maquinaria ni
   Normativa**, y eso **no se ha inventariado aquí** porque el encargo pedía S01, S02 y S03.
9. **No se ha comprobado el estado de la base de datos real** (`backend/cuedigital.db`), ni se ha tocado.
10. **No se ha leído `nucleo.js` entero** (23 KB), ni las piezas `campo.js`, `campos_del_maestro.js`,
    `lista_para_elegir.js`, `resumen_del_apunte.js`, `confirmacion.js`, `ayuda_de_un_campo.js` ni
    `tarjeta.js` enteras: se han leído los tramos que hacían falta para lo que se afirma.
