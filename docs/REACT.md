# React en CueDigital

Este documento cuenta **por qué** la interfaz se está pasando a React, **cómo** está montado
hoy, **qué pantallas están hechas y cuáles no**, y **cómo se hace la siguiente**. Está escrito
para que lo pueda seguir alguien que no haya tocado nunca React.

Última revisión: cuando la pantalla de inicio ya estaba en React y lo demás seguía igual.

---

## 1. Por qué React, y por qué SIN COMPILAR

La decisión la tomó el dueño del proyecto (ver el apartado 5 de [`AGENTS.md`](../AGENTS.md)):
«rehaz toda la ui con react aunque haya que rehacer pruebas». Lo que cambia con React es **cómo
se pinta la pantalla**; lo que NO cambia es nada de lo de siempre:

- **Los textos siguen viviendo en `backend/app/textos.py`** y llegan al navegador por
  `GET /api/interfaz`. Ni un componente escribe una frase para el agricultor.
- **La aplicación tiene que seguir funcionando sin cobertura**, y se sirve como ficheros
  estáticos desde el mismo servidor FastAPI (`backend/app/main.py:142` monta `backend/web/` en
  `/`).
- **Los colores siguen viviendo solo en el `:root` de `backend/web/estilos.css`.** Los
  componentes emiten las mismas `className` que había antes (`.boton`, `.boton-principal`,
  `.texto`, `.icono`, `.pista-boton`, `.aviso`, `.pista`, `.pista-campo`…). No hay ni un
  `style={{…}}`.
- **Los clics los sigue atendiendo un solo manejador** delegado en `document`
  (`backend/web/app.js`, «eventos»), que lee `elemento.dataset.accion`. Por eso los
  `data-accion` y los demás `data-*` tienen que salir iguales que antes.

**Sin compilar** quiere decir tres cosas, y las tres son requisitos, no comodidad:

1. **Donde corre esto no hay Node.** El servidor solo sirve ficheros: no hay un paso de
   compilación que se pueda ejecutar allí.
2. **El agricultor está en el campo, sin cobertura.** Todo lo que haga falta para dibujar una
   pantalla tiene que estar ya en su móvil, guardado por el `service-worker`
   (`backend/web/service-worker.js`). Un `import` de internet en tiempo de ejecución es una
   pantalla en blanco en mitad de una parcela.
3. **No se mete npm.** No hay `package.json` con dependencias, ni bundler, ni TypeScript, ni
   `jsdom`. Lo único que hay es JavaScript que corre tal cual en el navegador.

Cómo se consigue: React 18.3.1 se publica también como ficheros UMD (los que se cargan con una
etiqueta `<script>` y dejan `window.React`), y **`htm` 3.1.1** permite escribir las plantillas
sin JSX y sin compilar:

```js
const html = globalThis.htm.bind(globalThis.React.createElement);

export function Saludo({ nombre }) {
  return html`<h1>${nombre}</h1>`;
}
```

`htm` usa plantillas de JavaScript normales (las de las comillas invertidas) y las traduce a
`React.createElement`. Se escribe igual que JSX pero **es JavaScript válido**, así que el
navegador lo entiende sin ayuda de nadie.

**Ojo con React 19**: la 19 ya no publica ficheros UMD. Por eso la versión está clavada en la 18
y hay una prueba (`backend/tests/test_react_vendor.py`) que avisa si alguien intenta subir sin
cambiar el planteamiento.

---

## 2. Qué ficheros hay y cómo se regeneran

| Ruta | Qué es |
|---|---|
| `backend/web/vendor/react.production.min.js` | React 18.3.1. Deja `window.React`. |
| `backend/web/vendor/react-dom.production.min.js` | ReactDOM 18.3.1. Deja `window.ReactDOM`, con `createRoot`. Es el que monta de verdad en el navegador. |
| `backend/web/vendor/htm.umd.js` | `htm` 3.1.1. Deja `window.htm`. Es lo que permite escribir plantillas sin compilar. |
| `backend/web/vendor/react-dom-server-legacy.browser.production.min.js` | **Solo para las pruebas.** Convierte un componente en HTML sin navegador (`renderToStaticMarkup`). En la aplicación no se carga. |
| `backend/web/vendor/LEEME.md` | De dónde sale cada fichero, con su versión, su huella SHA-256 y su licencia. |
| `backend/web/vendor/LICENSE-React.txt`, `LICENSE-htm.txt` | Las licencias (MIT y Apache 2.0). Viajan con los ficheros, como mandan. |
| `backend/scripts/bajar_react.py` | El guion que los descarga y comprueba. |
| `backend/tests/test_react_vendor.py` | El que impide que alguien edite un fichero de `vendor/` a mano. |

**Estos ficheros no se editan a mano.** Se descargan con:

```bash
cd backend
../.venv/Scripts/python.exe scripts/bajar_react.py
```

El guion clava la versión en la dirección de descarga (`…/react@18.3.1/…`), comprueba la huella
SHA-256 de lo descargado y **se para** si un fichero no coincide con el que se revisó. Si algún
día hay que cambiar de versión: se cambia en `bajar_react.py`, se vuelve a lanzar y se actualizan
las huellas del `LEEME.md` (hay una prueba que exige que cuenten lo mismo). Sin permiso de red,
el guion no hace nada si los ficheros ya están y coinciden.

---

## 3. Qué pantallas están migradas y cuáles no

**La migración está terminada: no queda ni una pantalla en la interfaz vieja.** Están en React la pantalla
de inicio, la de confirmación, «mis cosas», «los papeles», el almacén, «qué hay sembrado», la ayuda, «mis
datos», las medidas preventivas, «lo que he vendido», los grupos de parcelas, los análisis, «dímelo con la
voz», la revisión de lo dictado, «guardar un papel», firmar el cuaderno, el plan de abono, la pantalla de
entrar, las facturas enteras, el mapa del SIGPAC, decir qué hay sembrado, traer las tierras del cuaderno
de la Junta, traer la tierra del SIGPAC, «mi cuaderno» **y el asistente de apuntar entero** (la del SIGPAC
va **dentro** del asistente de dar de alta una tierra: es la pantalla que busca el recinto oficial). La de
inicio fue el paso piloto (sirve para medir lo que cuesta de verdad) y la de confirmación —la de
«Apuntado. Si te has equivocado, pulsa DESHACER.»— es la segunda, elegida **a propósito por ser la más
fácil**: no tiene ni un campo que leer del DOM, así que se pasa a React sin tocar nada de cómo se guardan
los apuntes.

Las tres últimas, por orden:

1. **«Mi cuaderno»** (ronda 70), que no era una pantalla más: son nueve bloques —los apuntes de producto,
   lo que falta, lo que se ha vendido, las medidas, los análisis, el plan, la firma, el cuaderno de la
   Junta y el registro electrónico— que estaban escritos a mano como siete funciones `bloqueDe…`.
2. **Los avisos de error** (ronda 71): lo que sale cuando el servidor falla ya no se pinta con
   `innerHTML` (ver el apartado 4 ter), y de paso se le dio salida a siete avisos que no tenían ningún
   botón.
3. **El asistente de apuntar** (ronda 72), que era **el último `innerHTML` de la aplicación**: sus 65
   pasos ya estaban en React desde la ronda 68, pero el envoltorio (las barras, la pregunta, la pista, el
   hueco del formulario y los botones) se pintaba a mano. Con él, `pintar()` se ha borrado y **no queda ni
   una pantalla que se monte con `innerHTML`**.

| Pantalla | Estado |
|---|---|
| **Inicio** (`backend/web/react/pantallas/inicio.js`) | ✅ En React |
| **Confirmación, «Apuntado…»** (`backend/web/react/pantallas/hecho.js`) | ✅ En React |
| **Mis cosas** (`backend/web/react/pantallas/mis_cosas.js`) | ✅ En React |
| **Los papeles** (`backend/web/react/pantallas/documentos.js`) | ✅ En React |
| **El almacén** (`backend/web/react/pantallas/cesta.js`) | ✅ En React |
| **Qué hay sembrado** (`backend/web/react/pantallas/cultivos.js`) | ✅ En React |
| **La ayuda** (`backend/web/react/pantallas/ayuda.js`) | ✅ En React |
| **Mis datos** (`backend/web/react/pantallas/mis_datos.js`) | ✅ En React |
| **Quién entra en mi finca** (las cuentas que apuntan en la misma finca y en cuál estás) (`backend/web/react/pantallas/quien_entra.js`) | ✅ En React |
| **Las medidas preventivas** (`backend/web/react/pantallas/medidas.js`) | ✅ En React |
| **Lo que he vendido** (`backend/web/react/pantallas/ventas.js`) | ✅ En React |
| **Los grupos de parcelas** (`backend/web/react/pantallas/grupos.js`) | ✅ En React |
| **Los análisis** (`backend/web/react/pantallas/analiticas.js`) | ✅ En React |
| **Dímelo con la voz** (`backend/web/react/pantallas/dictado.js`) | ✅ En React |
| **La revisión de lo dictado** (`backend/web/react/pantallas/borrador.js`) | ✅ En React |
| **Guardar un papel** (`backend/web/react/pantallas/nuevo_documento.js`) | ✅ En React |
| **Firmar el cuaderno** (`backend/web/react/pantallas/firmar.js`) | ✅ En React |
| **El plan de abono del año** (`backend/web/react/pantallas/planes.js`) | ✅ En React |
| **Entrar** (correo y clave, o el certificado) (`backend/web/react/pantallas/entrar.js`) | ✅ En React |
| **Mis facturas** (la lista) (`backend/web/react/pantallas/facturas.js`) | ✅ En React |
| **Añadir una factura** (el alta) (`backend/web/react/pantallas/nueva_factura.js`) | ✅ En React |
| **La interpretación de una factura leída** (`backend/web/react/pantallas/interpretacion_factura.js`) | ✅ En React |
| **El mapa del SIGPAC** (`backend/web/react/pantallas/mapa.js`) | ✅ En React |
| **Decir qué hay sembrado** (`backend/web/react/pantallas/decir_cultivo.js`) | ✅ En React |
| **Traer las tierras del cuaderno de la Junta** (`backend/web/react/pantallas/cuaderno_de_la_junta.js`) | ✅ En React |
| **Traer la tierra del SIGPAC** (`backend/web/react/pantallas/traer_del_sigpac.js`) | ✅ En React |
| **Mi cuaderno** (`backend/web/react/pantallas/mi_cuaderno.js`) | ✅ En React |
| **El asistente de apuntar** (echar producto, abonar, trabajo) (`backend/web/react/pantallas/asistente.js`) | ✅ En React: el envoltorio es la pantalla y **sus 65 pasos son piezas** (`montar`) |
| **Los años de mi cuaderno** (la campaña) (`backend/web/react/pantallas/campanas.js`) | ✅ En React |
| **El libro del almacén** (`backend/web/react/pantallas/libro_del_almacen.js`) | ✅ En React (T09) |
| **La ficha de un albarán** (`backend/web/react/pantallas/recepcion.js`) | ✅ En React (T09) |
| **Apuntar un albarán** (`backend/web/react/pantallas/nuevo_albaran.js`) | ✅ En React (T09) |
| **Una merma, un ajuste o una entrada** (`backend/web/react/pantallas/movimiento_de_almacen.js`) | ✅ En React (T09) |
| **Sacar de un envase desde un apunte** (`backend/web/react/pantallas/sacar_de_un_lote.js`) | ✅ En React (T09) |
| **Decir de qué factura es un albarán** (`backend/web/react/pantallas/enganchar_la_factura.js`) | ✅ En React (T09) |
| **Mis tierras, en el mapa y en la tabla** (`backend/web/react/pantallas/tierras_mapa.js`) | ✅ En React (T06) |
| **Lo que ha sido esta tierra** (`backend/web/react/pantallas/tierra_versiones.js`) | ✅ En React (T06) |
| **Las semillas** (`backend/web/react/pantallas/semillas.js`) | ✅ En React (T10) |
| **Sembrar una semilla y corregir la siembra** (`backend/web/react/pantallas/siembras.js`) | ✅ En React (T10) |
| **Las personas y las empresas** (`backend/web/react/pantallas/contactos.js`) | ✅ En React (T11) |
| **La revisión de los nombres escritos** (`backend/web/react/pantallas/revision_de_contactos.js`) | ✅ En React (T11) |
| **El importe de una entrega** (`backend/web/react/pantallas/venta_importe.js`) | ✅ En React (T12) |
| **Un ajuste de peso, humedad o calidad** (`backend/web/react/pantallas/venta_ajuste.js`) | ✅ En React (T12) |
| **Las facturas que hemos emitido** (`backend/web/react/pantallas/facturas_emitidas.js`) | ✅ En React (T12) |
| **Facturar varias entregas juntas** (`backend/web/react/pantallas/facturar_entregas.js`) | ✅ En React (T12) |
| **La ficha de una factura nuestra** (`backend/web/react/pantallas/factura_emitida.js`) | ✅ En React (T12) |
| **Los cobros** (`backend/web/react/pantallas/cobros.js`) | ✅ En React (T12) |
| **Apuntar un cobro** (`backend/web/react/pantallas/cobro_nuevo.js`) | ✅ En React (T12) |
| **Mi maquinaria, y la ficha de una máquina** (`backend/web/react/pantallas/maquinaria.js`) | ✅ En React (T14) |
| **Mis cuentas, y la ficha de un gasto** (`backend/web/react/pantallas/gastos.js`) | ✅ En React (T13) |
| **Los trabajos, la ficha de un trabajo y la historia de una tierra** (`backend/web/react/pantallas/trabajos.js`) | ✅ En React (T15) |

**Y desde el T06 (03/10/2026) son treinta y siete**: las treinta y cinco de antes más las dos de las
tierras en el mapa y en la tabla (`tierras_mapa`, `#/tierras/mapa`) y lo que ha sido una tierra
(`tierra_versiones`, `#/tierras/<id>/versiones`). Las dos se añadieron a `PANTALLAS_EN_REACT`, a la
caché del `service-worker` (que sube a la versión 64) y a la tabla de arriba en el mismo cambio, que es
lo que exige la prueba que vigila que las tres listas digan lo mismo. Se cuenta aquí porque **una lista
escrita a mano se queda vieja y nadie se entera**, que es la lección que este apartado ya llevaba
escrita desde el T09.

**Y desde el T10 (03/10/2026) son treinta y nueve**: entran las semillas (`semillas`: la lista con lo
que queda de cada una, la ficha de su etiqueta y la lectura de una foto, que **no guarda nada**) y
`siembras` (`#/siembras`: lo que se ha sembrado, y el formulario de «en esta tierra sembré esta
semilla», que es lo que descuenta la semilla del almacén). Se apuntan aquí porque esta tabla y el
`PANTALLAS_EN_REACT` del código **tienen que decir lo mismo** y hay una prueba que lo exige; la caché
del `service-worker` sube con ellas a la versión 65, y la versión del pie (`app.js`) se puso al día en
el mismo cambio. **Ojo con el nombre de `siembras.js`**: es la asignación de una semilla a una siembra
(T10), no la pantalla de los trabajos de siembra por campaña, que es otro ticket (T15) y tendría que
traer su propio nombre y su propia ficha.

**Y desde el T11 (03/10/2026) son cuarenta y uno**: entran las personas y las empresas (`contactos`:
la lista de fichas, la ficha de una persona o una empresa **con los papeles que hace con la finca y
dónde está escrito su nombre**, y la lista de nombres escritos para enlazarlos sin teclear una letra) y
`revision_de_contactos` (`#/contactos/revisar`: la revisión de los nombres que ya están escritos, donde
el programa **propone fichas y no fusiona nada que no pueda asegurar**). Los dos ficheros nuevos van a
la caché del campo, que sube a la versión 66, y la versión del pie se puso al día en el mismo cambio —
que es lo que exige la prueba que vigila que las tres listas digan lo mismo.

**Y desde el T12 (02/10/2026) son cuarenta y ocho**: entran las siete pantallas del dinero de las ventas,
que es lo que el contrato pide en S12 —**separar la entrega, la factura y el cobro**—: `venta_importe`
(`#/ventas/<id>/importe`: el importe del papel o el precio por la cantidad, con su vencimiento y de qué
cosecha salió), `venta_ajuste` (una devolución o un ajuste de peso, humedad o calidad, **con su origen y
su motivo obligatorios**), `facturas_emitidas` (la lista de las facturas nuestras), `facturar_entregas`
(agrupar varias entregas en una factura **sin contar el ingreso dos veces**), `factura_emitida` (su ficha,
con sus líneas, sus pagos y lo que queda pendiente), `cobros` (los cobros, con factura o sin asignar) y
`cobro_nuevo` (apuntar uno, **parcial** si hace falta). Los siete van a la caché del campo, que sube a la
**versión 67**, y la versión del pie se puso al día en el mismo cambio.
**Ninguna de estas pantallas presenta nada como factura fiscal**: la emisión fiscal completa necesita su
propia especificación normativa, y aquí solo se apunta la entrega, la factura nuestra de gestión y los
cobros.

**Y desde el T14 (03/10/2026) son cuarenta y ocho más una**: entra la maquinaria
(`maquinaria.js`: la lista con su tabla —máquina, tipo, matrícula o serie, propiedad, horas, próxima
revisión, papeles y disponibilidad— y **la ficha de una máquina**, que es la que separa las cinco
obligaciones: ITV, ITEAF, mantenimiento, seguro y ROMA). Es **un solo fichero con las dos pantallas** por
el mismo motivo que las semillas: son la misma cosa mirada de dos maneras. Va a la caché del campo, que
sube a la **versión 68**, y la versión del pie se puso al día en el mismo cambio.
**Lo que esta pantalla NO hace, y conviene que quede escrito aquí**: no calcula ningún plazo de
inspección. El contrato lo prohíbe con estas palabras («No calcular plazo solo por "tractor" o
"sulfatadora"; pedir la clasificación técnica necesaria»), y por eso la ficha **pregunta** la
clasificación técnica, guarda la aplicabilidad de cada obligación con tres estados (`sí`, `no` y «no lo
sé») y **enseña la próxima fecha que traiga el papel**, no una calculada. Cuando no hay fecha, dice que
falta el dato y pide lo que hace falta para saberlo.
| Las descargas (el cuaderno en papel, los datos en CSV y el fichero de la firma) | ❌ No son pantallas: las pide `app.js`, que es quien tiene el token, y el botón lo pinta React |

La lista de lo que está en React vive también en el propio código, para que el siguiente que
llegue no tenga que buscarla: `const PANTALLAS_EN_REACT = new Set([...])` con veintinueve nombres: `inicio`,
`hecho`, `mis_cosas`, `documentos`, `cesta`, `cultivos`, `ayuda`, `mis_datos`, `quien_entra`, `medidas`,
`ventas`, `grupos`, `analiticas`, `dictado`, `borrador`, `nuevo_documento`, `firmar`, `planes`, `entrar`,
`facturas`, `nueva_factura`, `interpretacion_factura`, `mapa`, `decir_cultivo`,
`cuaderno_de_la_junta`, `traer_del_sigpac`, `mi_cuaderno`, `asistente` y `campanas` (ronda 93: los años
del cuaderno), al principio de
`backend/web/app.js`. **Y desde el T09 (03/10/2026) son treinta y cinco**: los veintiocho de antes más las
seis del libro del almacén (`libro_del_almacen`, `nuevo_albaran`, `recepcion`, `movimiento_de_almacen`,
`sacar_de_un_lote` y `enganchar_la_factura`) y la ficha de un albarán, que se cuenta aparte porque
`libro_del_almacen` es su lista. **Y desde el T13 (05/10/2026) son treinta y seis**: las cuentas de la
explotación (`gastos.js`, con la lista y la ficha de un gasto en un solo fichero, como la maquinaria).
La cuenta que la prueba de la migración exige («veintiocho») sigue
escrita, con la fecha en la que dejó de ser el número: **una lista escrita a mano se queda vieja y nadie
se entera**, y este párrafo es justo eso.

**Ya no hay dos interfaces: solo React.** Hasta la ronda 72 convivían, porque las pantallas sin migrar se
pintaban con `pintar(html)` (que hacía `innerHTML = …` sobre `#pantalla`). Con el asistente, esa función se
borró y **el único sitio que escribe en la pantalla es `montar()`**. Se sigue creando **una raíz de React
nueva cada vez** que se cambia de pantalla, que es lo que hace que un montaje no herede nada del anterior y
que el contenedor se vacíe solo.

---

## 4. Cómo se añade una pantalla nueva

Se copia el patrón de la de inicio. Los pasos, en orden:

1. **Crea el componente** en `backend/web/react/pantallas/<nombre>.js`:
   - Cabecera de comentario: por qué esa pantalla y qué se conserva a propósito.
   - `const React = globalThis.React;` y la plantilla `html` de `htm` (en `inicio.js` se arma la
     primera vez que hace falta, para que el módulo se pueda importar aunque React no haya
     cargado; ver el apartado 6).
   - Un componente **puro**: todo le llega por propiedades. Ni `fetch`, ni `localStorage`, ni
     tocar el DOM.
   - Las mismas `className` y los mismos `data-accion` / `data-*` que la pantalla vieja.
   - **Nada de `esc()`**: React ya escapa. Llamarlo hace que se vea `&amp;` en pantalla.
   - Exporta también las piezas pequeñas (un botón, un aviso), para poder probarlas sueltas.
2. **Pide los textos al servidor** desde `app.js` con `t("ruta.de.la.clave", "")` y pásalos como
   propiedades. Si falta un texto, **va a `backend/app/textos.py`** y se sirve en
   `backend/app/routers/interfaz.py`. Nunca se escribe en el componente.
3. **Monta la pantalla desde `app.js`**:
   - Conserva la función con el mismo nombre (`pantallaX`) y el mismo comportamiento.
   - Dentro, **una sola línea**: `montar(() => pantallaDeX({ … }))`. `montar()` pide el elemento dentro de
     un `try` (si los ficheros de React de `vendor/` no han llegado, sale el aviso de emergencia en vez de
     una pantalla en blanco) y es **el único sitio que escribe en la pantalla**.
   - Añade el nombre a `PANTALLAS_EN_REACT`.
   - No toques el resto de `app.js`.
4. **Añade los ficheros nuevos al `service-worker`** (`FICHEROS` en
   `backend/web/service-worker.js`) **y sube el nombre de `CACHE`**. Si no, un agricultor que
   abra la aplicación sin cobertura después de un despliegue se queda con los ficheros viejos: el
   `app.js` nuevo pidiendo un componente que su móvil no tiene. Hay una prueba de Python que
   enumera esa lista.
5. **Escribe las pruebas** en `backend/tests_js/react.test.js` (o en un fichero nuevo, el
   apartado 5 lo cuenta), **y rehace las de `interfaz.test.js`** que miraban esa pantalla: en su
   DOM de mentira React no se puede montar. No se borra ninguna sin dejar su equivalente, y en
   `interfaz.test.js` se deja una prueba que compruebe, con `montajes`, que esa pantalla **se le
   pide a React** con los datos de la aplicación.
6. **Actualiza este documento** (la tabla del apartado 3) y la cuenta de pruebas del
   `README.md`, `AGENTS.md` y `docs/LO_QUE_PIDE_LA_JUNTA.md`.

Si la pantalla tiene campos de formulario, lee el apartado 6 antes de empezar: hay trabajo
pendiente ahí.

---

## 5. Cómo se prueban

Se prueban **sin navegador**, con el `node:test` que ya usa el proyecto (no hay Jest, ni Vitest,
ni `jsdom`: no se mete una dependencia nueva para esto).

El arnés está en `backend/tests_js/react.test.js`, y hace tres cosas:

1. **Carga los ficheros de `vendor/` en los globales de Node**, igual que los carga el navegador:
   ```js
   globalThis.self = globalThis;   // los UMD se asignan a `self`
   vm.runInThisContext(codigo, { filename: nombre });
   ```
   (`self` no existe en Node: se le pone, porque es donde los ficheros UMD se asignan cuando no
   hay un sistema de módulos).
2. **Renderiza a HTML con `renderToStaticMarkup`** del `react-dom-server`:
   ```js
   globalThis.ReactDOMServer.renderToStaticMarkup(
     globalThis.React.createElement(PantallaInicio, propiedades),
   );
   ```
   Devuelve el HTML como una cadena, y sobre esa cadena se hacen las comprobaciones.
3. **Importa el componente con marca en la URL** (`import("…/inicio.js?prueba=" + Math.random())`)
   para que cada prueba arranque de cero, como hace `interfaz.test.js` con `app.js`.

**Por qué no hay `jsdom`.** Porque haría falta una dependencia nueva (y con ella un
`package.json` de verdad, con la puerta abierta a un `node_modules`), porque su DOM no es el de
un móvil, y porque **lo que de verdad hay que probar en un navegador no se prueba con
`jsdom`**: se prueba en el móvil. El `jsdom` daría la sensación de que algo está comprobado
cuando no lo está. Lo que sí se comprueba aquí es todo lo que se puede comprobar sin navegador:
qué botones salen, en qué orden, con qué textos, con qué `data-accion` y qué clases.

**Lo que NO se puede probar así, y hay que decir claramente**: que la pantalla se vea bien en un
móvil de verdad, que se pueda tocar con el dedo, y que el agricultor sepa usarla. Eso exige la
prueba con tres agricultores (apartado 5.18 del documento del MVP).

Para correr las pruebas:

```bash
cd backend
node --test tests_js/nucleo.test.js tests_js/interfaz.test.js tests_js/react.test.js
```

### 4 bis. Las piezas: componentes que no son una pantalla

Cuando lo que hay que migrar no es una pantalla entera sino **un trozo**, el fichero va en
`backend/web/react/piezas/` y no en `react/pantallas/`. La diferencia no es de sitio, es de
significado: **la lista `PANTALLAS_EN_REACT` es la lista de pantallas**, y meter ahí un trozo sería
mentir en la tabla. Hay una prueba (`tests/test_la_migracion_a_react.py`) que exige que cada fichero de
`pantallas/` esté en la lista, y **otra nueva que exige que TODO el JavaScript de `react/` (pantallas y
piezas) esté en la caché del service-worker**: un componente que no está en la caché es un hueco en el
campo.

**La primera pieza es el resumen del asistente** (`piezas/resumen_del_apunte.js`), y trae el mecanismo con
el que se migró el asistente entero:

> Un paso del asistente **dice `montar`** en vez de `pintar`, y devuelve un **elemento de React** en vez de
> una cadena de HTML:
>
> ```js
> // Antes: el paso devolvía HTML
> pintar: pintaResumenTratamiento,
> // Ahora: el paso devuelve el elemento, y la pantalla del asistente lo pinta dentro de `#formulario`
> montar: () => montarResumenDelApunte(cargaTratamiento(), { finDeEspera: { … } }),
> ```
>
> Con eso, el asistente se migró **paso a paso sin tocar su motor**: cada paso pasó de devolver HTML a
> devolver un elemento, y **al final se migró el envoltorio** (ronda 72): `pintarAsistente()` le pasa el
> elemento del paso a `PantallaAsistente` como una propiedad (`formulario`) y el motor —`irA`,
> `normalizaIndice`, `pasoSeMuestra` y el `recoger()` de cada paso— **sigue haciendo exactamente lo
> mismo**. Por eso el asistente se pudo apuntar en `PANTALLAS_EN_REACT` sin tocar cómo se guardan los
> apuntes.
>
> **El borrador no se ha movido.** Se sigue leyendo del DOM campo a campo (por el `id` de cada campo),
> que es el patrón de toda la aplicación (apartado 6.2), y por eso migrar el motor no cambió nada de lo
> que se guarda: es la misma decisión que permitió migrar las otras 26 pantallas sin tocar el guardado.

Dos detalles del mecanismo, aprendidos al escribirlo:

1. **`#formulario` sigue existiendo, y ahora lo pinta React.** Es el hueco donde va el formulario del
   paso: en el navegador es un `<div id="formulario">` de verdad, dentro de la pantalla, y las pruebas de
   los pasos y la comprobación en un navegador de verdad lo siguen buscando por su `id` (esa es la parte
   que se conserva a propósito: el `id` es lo que deja comprobar que **el paso tiene su formulario**).
2. **Un paso ya no puede pintar HTML.** El `pintar` de los pasos se borró al migrar el último: un paso que
   traiga `pintar` en vez de `montar` **no pintaría nada**. Está avisado en el código y hay una prueba
   (`test_la_migracion_a_react.py`) que exige que no quede ni un `pintar:` en las definiciones de pasos.

**La segunda pieza es la lista de botones del asistente** (`piezas/lista_para_elegir.js`), y nació de
una cuenta: **la mitad de los pasos del asistente son la misma pantalla** —una lista donde el agricultor
toca la tierra, la nave, el producto o el trabajo que ha hecho— y estaban escritas **siete veces** a
mano en `app.js`, cada copia acordándose de cosas distintas (unas ponían el título, otras la pista,
otras el aviso con su botón). Ahora hay una sola pieza y `app.js` le pasa los botones **ya preparados**:

```js
// En app.js: los datos, no el HTML
function bloqueDeParcelas() {
  return { botones: estado.parcelas.map((parcela) => ({ etiqueta: parcela.alias, pista: …, accion: "elegir", datos: { campo: "parcela_id", … } })) };
}
// Y el paso dice `montar`
montar: montarParcelas,
```

Con eso quedaron migrados **once pasos**: el resumen final (en los tres asistentes: echar producto,
abonar y hacer un trabajo) y las listas de elegir —la tierra (en los cuatro asistentes que la
preguntan), la nave o el almacén, el producto echado, el abono y la práctica de labor—.

Dos cosas que hay que saber de esta pieza:

1. **El aviso viaja con el botón que lo arregla** (`aviso: { texto, boton }`). Cuando no hay ninguna
   tierra dada de alta, un aviso solo deja al agricultor sin salida: dice que añada una y no hay dónde.
   Si viene el aviso, **los bloques no se pintan**: no hay nada que elegir.
2. **Una sola lista de datos, un solo pintor.** Los bloques se preparan **una vez** en `app.js`
   (`bloqueDeParcelas()`, `bloqueDeGrupos()`…) y los pinta la pieza. Mientras quedaban pasos con `pintar`
   había un segundo pintor que convertía esos mismos datos a HTML (`htmlDeBloque()`, `boton()`); los dos
   se borraron al migrar el último paso, y así no hay dos listas que se puedan separar cuando alguien
   cambie una pista.
3. **La lista sabe llevar su ayuda debajo** (`ayuda: { datos, rotulos }`), y **el aviso sabe llevar su
   explicación** (`aviso: { texto, pista, boton }`). La ayuda va **después de los bloques** porque
   explica la pregunta entera y no uno de sus botones; la pista del aviso es para los avisos que dicen
   qué pasa **y qué se puede hacer igualmente** («el trabajo se apunta sin máquina»), que es lo que evita
   que el agricultor crea que no puede seguir.

**La sexta pieza es la confirmación** (`piezas/confirmacion.js`), y con ella se pasaron de una vez **ocho
pantallas pequeñas** que estaban escritas a mano en `app.js`: las **cinco confirmaciones** (venta
guardada, análisis guardado, plan de abono guardado, medidas declaradas y ficha de un maestro guardada) y
las tres que **ofrecen un camino** (traer la tierra del SIGPAC, el listado de papeles en texto y las
tierras traídas). Todas son la misma forma: un título, la explicación de **para qué sirve** lo que se
acaba de guardar, y sus botones.

```js
// En app.js: los textos y los datos; la pintura, en la pieza
montar(() => confirmacion({
  titulo: p("guardado_titulo"),
  pista: p("guardado"),
  ayuda: { titulo: p("se_usa"), texto: p("apunta_abonos") },
  acciones: accionesDeConfirmacion({ etiqueta: p("ver"), accion: "plan-ver", clase: "boton", sencillo: true }),
}));
```

Dos cosas de esta pieza que conviene saber:

1. **La ayuda («Dónde se usa: …») no es un adorno.** Es lo que hace que el agricultor entienda que apuntar
   eso le vale para algo, y son dos textos del servidor: el genérico y el de esa pantalla.
2. **Los botones de estas pantallas son sencillos** (`sencillo: true`: sin icono y sin flecha), como
   estaban. Los de la pantalla que ofrece los caminos para dar de alta una tierra **sí** llevan el icono y
   la flecha del botón de la casa: son caminos que sacan de la pantalla. Antes iban sin flecha, y se
   unificaron con el resto de la aplicación (el botón de casa es el mismo en todas partes).

**La tercera y la cuarta pieza son el campo y su ayuda** (`piezas/campo.js` y
`piezas/ayuda_de_un_campo.js`), y son las que faltaban para migrar los pasos donde el agricultor
**escribe**: la fecha, las hectáreas, la dosis, los kilos por hectárea. Otra vez la misma cuenta: el
mismo bloque estaba montado por **tres funciones** de `app.js` (`pintaFecha`, `pintaNumero` y
`pintaCamposMaestro`) y cada una se acordaba de cosas distintas (una la pista, otra la ayuda, otra el
`inputmode` para que en el móvil salga el teclado de números).

```js
// En app.js, los datos y los textos; la pintura, en la pieza
montar: () => montarNumero("superficie_tratada_ha", t("rotulos.unidad_hectareas", ""),
                           "tratamiento.superficie", "tratamiento.superficie_tratada_ha"),
```

**Tres reglas del campo que no se pueden romper**, y que están escritas en el fichero para que nadie
las «arregle»:

1. **El campo lleva su `id`, y es el de siempre.** `app.js` lee lo escrito **por ese `id`**
   (`recogeCampos`, `recogeCamposMaestro`, `estadoDelMapa`): si cambia, el formulario se rellena y **se
   guarda vacío sin que salte ningún error**. Es el peor fallo posible en esta pantalla, y por eso hay
   pruebas que miran la lista de `id` entera y una que rellena campos en un navegador de verdad.
2. **El valor inicial va en `defaultValue`, no en `value`.** El campo sigue siendo **descontrolado**:
   React lo pinta y `app.js` lo lee. Guardar estado en las dos mitades sería la forma más segura de que
   un día digan cosas distintas.
3. **`inputmode="decimal"` en los números y nada de eso en las fechas.** Es lo que hace salir el teclado
   de números **con coma** en el móvil (aquí se escribe «2,43»), y en una fecha el teclado de números
   tapa el calendario. Se escribe `inputMode` en el componente (que es lo que entiende React) y el
   navegador lo deja en el atributo `inputmode`; **se comprueba en un navegador de verdad**, porque en
   el HTML estático de los tests sale con la mayúscula del nombre de la propiedad.
4. **Sin etiqueta no se pinta el `<label>`.** Hay pasos en los que la pregunta ya es el título de la
   pantalla (las observaciones de un apunte, los detalles de una labor): una etiqueta vacía solo estorba
   —un lector de pantalla lee un campo sin nombre—, y el campo sigue llevando su `id`, que es lo que
   importa.
5. **El campo sabe más de lo que parece, y todo salió de una pantalla.** «Cómo se echó» el producto (la
   última pantalla larga del asistente) necesitaba: un número **sin coma** (`tipo: "entero"`, para las
   horas y los operarios: en una hora la coma no pinta nada), un **ejemplo dentro de la casilla**
   (`placeholder: "07:30"`), **sin el historial del navegador** (`autocompletar: "off"`, que en el móvil
   tapa media pantalla), el alto del área de escribir (`filas`) y la ayuda **encima** del campo
   (`ayudaAntes`), porque en el primer campo de esa pantalla la explicación es la introducción y se lee
   antes de empezar. Un bloque del maestro puede además llevar **su título** (`titulo`), que es lo que
   pinta el `<h2>` de cada sección.

Y de la ayuda, lo que hay que saber: **los cuatro rótulos son del servidor** (`Qué es:`, `Por qué te lo
piden:`, `Ejemplo:`, `Si te falta:`) y estaban escritos a mano dentro de `app.js`, donde no pasan por la
prueba que vigila que no haya jerga. Los datos se preparan **una vez** en `datosDeLaAyuda()` y los pinta la
pieza (mientras quedaban pasos con `pintar` había un segundo camino, `ayudaDeCampo()`, que ya se borró).

**La quinta pieza es el grupo de campos del maestro** (`piezas/campos_del_maestro.js`), y con ella se
migraron **veinte pasos de golpe**: las fichas de dar de alta un producto, una máquina, un asesor y una
nave, los números del plan de abono y los de la venta. Casi todos los pasos del asistente que no son una
lista son **varios datos seguidos**, y cada dato se pinta como un campo… **menos los que se contestan
eligiendo**, que llevan sus botones dentro del mismo bloque (un sí o un no, la unidad de dosis, el tipo
de carné). Esa mezcla es lo que resuelve esta pieza: recibe una lista de bloques, cada uno de escribir o
de elegir, y los pinta en orden.

```js
// En app.js: la lista de datos, no el HTML
montar: () => montarCamposMaestro(["venta.producto", "venta.variedad"]),
```

Dos cosas aprendidas al escribirla, las dos con su prueba:

1. **La pista de cada dato se pinta con la pieza del campo**, y al montarlo la primera vez **se me
   olvidó**: los veinte pasos salieron sin su explicación de debajo. No lo cazó ninguna prueba de las
   que había (las que miraban ese HTML se estaban reescribiendo en ese momento), lo cazó la prueba nueva
   del componente, que mira el bloque entero. Está contado porque es justo el fallo que el proyecto
   persigue: **un texto que falta no revienta, deja un hueco.**
2. **Un bloque con un `tipo` que no se conoce se pinta como texto**, que es lo que hacía la interfaz de
   siempre. Está decidido a propósito: entre un campo de más —que el agricultor puede rellenar y se
   guarda en su sitio— y un campo que desaparece sin decir nada, el de más. Un campo que no se pinta es
   un dato que se pierde **sin que nadie se entere**.

**Y una cosa que se trajo el T06 (03/10/2026): `componentes.js` tiene una pieza más.** La fila de
botones de elegir —un rótulo y una fila de opciones donde **una está elegida**— la necesitan las dos
pantallas nuevas (los filtros y las capas del mapa, y los años que se comparan), así que vive en
`componentes.js` como `OpcionesParaElegir` en vez de estar escrita dos veces. El elegido lleva
`.boton-elegido` **y `data-elegido`**: el color solo no informa (regla de la casa), así que el
agricultor lo ve marcado y una prueba puede comprobar cuál está elegido leyendo el dato.

Las pruebas de los componentes están en `backend/tests_js/react.test.js`, y comprueban entre otras
cosas el resumen, la lista de elegir, el campo y el grupo de campos del maestro: sus botones con sus
`data-*`, el que ya estaba elegido marcado, el aviso con su botón, el `id` de cada campo, su
`inputmode`, los atajos de la fecha con el campo al que se refieren, la ayuda con sus cuatro rótulos y
que **ninguna frase esté escrita a mano** (todas tienen que venir de la copia de los textos del
servidor), además del camino sin ReactDOM y la salida de emergencia.

**Y una cosa que se descubrió al migrar los últimos pasos: hay pantallas que piden dos cosas a la vez.**
El resumen de la venta tenía una lista y unos números; el sitio de la muestra, una lista de tierras, otra
de naves y un campo; el último día de una venta, un lote y una fecha. Para esas **se componen las piezas
con `html`**, que es lo que evita inventar una pieza nueva para cada mezcla:

```js
// En app.js: dos piezas seguidas en el mismo paso
montar: () => html`${camposDelMaestro({ bloques: bloquesDelMaestro(["venta.lote"]) })}${elementoDeFecha("fecha_fin", "venta.fecha_fin")}`,
```

Tres detalles de eso, aprendidos al escribirlo:

1. **Lo que se le pasa a React es una lista de elementos**, no uno. React las pinta todas; no llevan
   `key` porque **nunca cambian de número ni de orden** y estos pasos se vuelven a montar enteros cada
   vez que el agricultor llega a ellos. Lo que sí hizo falta fue que las pruebas supieran mirarlo: la
   primera versión de `textosDeLoPedido()` leía solo el primer elemento y decía que el paso no listaba
   las tierras, con la aplicación perfectamente bien.
2. **El resumen del apunte sirve para los cuatro resúmenes.** El de echar producto, el del plan de abono,
   el de la venta y el del análisis son la misma cosa: una lista de etiqueta y valor para repasar antes
   de apuntar. Al del plan se le añadió una `pista` («los kilos son por hectárea»), porque sin ella los
   tres números se pueden leer al revés.
3. **Los botones que van dentro de un aviso pueden ser sencillos** (`sencillo: true`: sin icono y sin
   flecha), que es como estaban los que solo abren una cosa concreta («APUNTAR UN ANÁLISIS»). El botón de
   casa, con su flecha, es para los caminos que sacan de la pantalla. Los dos viven en `componentes.js`
   (`Boton` y `BotonSencillo`) para que no se copien.
4. **Ojo: la plantilla `html` de este `htm` NO sabe hacer fragmentos.** Escribir `html\`<>…</>\`` no da un
   `React.Fragment`: da un elemento con `type: ""`, y React revienta con el error #65 («el tipo no es
   válido»). Se descubrió al escribir las pantallas de error, que son un aviso **y** un botón sin nada en
   medio. Lo que sí funciona —y es lo que se hace— es **no envolverlos**: poniendo los dos seguidos en la
   misma plantilla sale una lista de elementos, que es lo mismo que ya se usaba para componer piezas.

**La séptima pieza es la tarjeta** (`piezas/tarjeta.js`), y no nació de una
migración sino del **rediseño con Stitch** (ronda 77). En el asistente, la pregunta que más se repite es
«¿en cuál?», y la respuesta era una fila de texto igual que las de al lado: con 51 tierras, eso es elegir
a ciegas, y el tratamiento acaba apuntado en la tierra que no es —y eso no se nota hasta que alguien mira
el cuaderno—. La tarjeta lleva **el dibujo de la forma de la tierra** (que es como el agricultor la
reconoce: la ve así en el SIGPAC), su superficie, su pueblo, sus **avisos dentro** (zona de nitratos, masa
de agua cerca: datos que ya se saben) y **la palabra «ELEGIDA»** en la que acaba de tocar.

Tres cosas que hay que respetar de esta pieza:

1. **Con acción es un `<button>`**, con su `data-accion` y sus `data-campo` / `data-valor` /
   `data-superficie`: el manejador de clics es uno solo y vive en `app.js`. Una tarjeta bonita que no hace
   nada al tocarla es peor que la fila de texto de antes.
2. **Los avisos son datos que ya se saben**, no suposiciones: salen de `zona_vulnerable_nitratos` y de
   `masa_agua_cerca`, que vienen del SIGPAC y del catálogo oficial. Si un dato no está, no se dice nada.
3. **La elegida se dice con una palabra**, además del color y del círculo marcado: el color nunca informa
   solo (regla de la casa).

**La segunda vez que hizo falta la misma tarjeta (ronda 78) fue en «Mis parcelas, productos y máquinas»**,
donde la lista de tierras era el mismo muro de renglones iguales **y además no se podía hacer nada con
ella**. Para eso la pieza tiene hoy tres cosas más, todas opcionales —el **rótulo** de arriba («Tierra
n.º 12»), las **filas con su nombre delante** (`Referencia oficial SIGPAC` y el valor: una referencia del
SIGPAC suelta no dice qué es) y el **pie que dice qué pasa al tocarla**—, y puede ir **sin el círculo de
elegir** (`marca: false`). Ese círculo no es decoración: dice «esto se toca y queda elegido», y en una
lista donde no se elige nada prometería algo que no ocurre. Ahí la tarjeta **abre** lo que hay sembrado en
esa tierra (`cultivo-decir`), que es lo único que se puede hacer con ella desde esa pantalla.

Las otras seis secciones de esa pantalla siguen con su lista de renglones a propósito: son diez o doce
cosas y se leen de un tirón. Una tarjeta para cada abono sería más ruido que ayuda, y el rediseño no pide
eso. Por eso el componente tiene **dos formas de lista** y cuál es cuál lo dice `tarjetas: true`, que
prepara `app.js`: no se adivina por los datos que traiga.

**Y la tercera vez (ronda 79) obligó a cambiarle el nombre al fichero, que es lo que más se aprende de
esto.** En «mi cuaderno» (`docs/stitch/rediseno/mi_cuaderno.png`) cada apunte de producto es también una
tarjeta —su número, su fecha y cada dato con su nombre delante—, pero allí **no se toca nada: se lee**. Un
apunte no tiene pantalla propia, así que la tarjeta no puede ser un botón: un botón que no hace nada
promete una salida y no la da. Así que la pieza **se pinta de las dos maneras según lo que le llegue**:
con `accion` es un `<button>`; sin ella, un `<div>`. Y eso dejó claro que el nombre del fichero
—`tarjeta_de_tierra.js`— ya no decía la verdad: con tres usos (elegir una tierra, mirar las tierras de la
finca y leer los apuntes del cuaderno) la pieza es **`tarjeta.js`**. Renombrarla no es cosmética: con el
nombre viejo, la tarjeta del apunte habría acabado siendo **una copia** de la de tierra, que es exactamente
lo que este proyecto lleva siete rondas evitando.

Y una cosa que trajo el mismo rediseño: **la barra del asistente va pegada abajo**
(`.asistente-acciones`, en `asistente.js`). De pie en el campo y con una mano, el botón de SEGUIR tiene
que estar donde llega el pulgar, no al final de una lista de cincuenta tierras.

### 4 ter. Las pantallas de error: lo último que se pintaba a mano

Cuando el servidor falla (no se puede guardar, no se puede bajar un papel, no se puede anular un apunte),
la aplicación **enseña el aviso en vez de la pantalla**. Hasta la ronda 71 eso era
`pintar(bloqueError(...))` —el último trozo de la aplicación que escribía HTML con `innerHTML`—, y tenía
dos problemas:

1. **Siete de los nueve avisos no llevaban ningún botón**: el `pintar()` borraba la pantalla en la que
   estaba el agricultor y le dejaba un texto sin salida. Ahora **todos menos uno** llevan su `VOLVER`
   (`data-accion="ir-inicio"`), que es el botón que ya llevaban los dos de las descargas del cuaderno.
2. **No tenían ni una prueba.** Se llega a ellos solo cuando el servidor dice que no, y el servidor de
   mentira de `interfaz.test.js` daba por bueno todo lo que estuviera en su lista: no había forma de que
   una petición fallara. Para eso está ahora el ayudante **`falla()`** de ese fichero (una respuesta
   marcada con `FALLA` contesta 422 con un motivo), y de ahí salen las seis pruebas nuevas: el motivo del
   servidor tiene que llegar entero al agricultor y tiene que haber salida.

El único que **no** lleva botón es el del arranque (`arrancarSesion`), y no es un olvido: ahí no ha
llegado ni la interfaz, así que `accion("volver")` devuelve la clave —el botón diría «volver» en idioma
de programador—. Lo que sale es el mensaje del fallo, y para recargar ya está el botón del navegador. Ese
caso se pasa con `avisarDelError(texto, { sinVolver: true })`.

`bloqueError()` sigue existiendo para **un solo** usuario: el aviso de error del asistente
(`pintarAsistente`), que monta su pantalla como una cadena de HTML porque su motor sigue siendo el viejo.
El día que se migre el motor, esa función se borra.

---

## 5 bis. Cómo se comprueba en un navegador de verdad (rondas 42, 62, 63 y 64)

Los tests dibujan los componentes con `renderToStaticMarkup`, **sin navegador**. Eso comprueba qué
HTML sale, pero **no** lo único que solo pasa en un navegador de verdad: que
`ReactDOM.createRoot(…).render(…)` monte y que la aplicación arranque sin errores de JavaScript, que
es el fallo que dejaría al agricultor delante de una pantalla en blanco.

Para eso está `scripts/comprobar_en_un_navegador.py`, que abre **Chrome (o Edge) sin ventana** con un
perfil de usar y tirar, entra con una cuenta de prueba y **recorre las pantallas ya migradas pulsando
de verdad** (el navegador pulsa los botones, como lo haría una persona), comprobando en cada una que
sale lo que tiene que salir y que **no aparece el aviso de emergencia de React**. Además guarda
**capturas** en la carpeta temporal, para poder mirarlas:

```bash
cd backend
../.venv/Scripts/python.exe scripts/comprobar_en_un_navegador.py http://127.0.0.1:8010
```

**Lo que encontró la primera vez que se ejecutó, y conviene saberlo:**

1. **Un módulo de otro origen no carga.** La primera versión servía la página de la comprobación desde
   un fichero local, y el navegador no cargaba `app.js` (un `import` de módulo necesita CORS, que el
   programa no pone porque no lo necesita): la pantalla salía vacía. Por eso la página se escribe
   **dentro de `backend/web/`** y se borra al terminar.
2. **La página de la comprobación necesita el mismo `viewport` que `index.html`.** Sin él, el
   navegador dibuja la página como si fuera ancha y la captura sale recortada: me hizo buscar un fallo
   de anchura en la aplicación que no existía.

Hoy recorre **24 rutas de verdad: diecisiete pantallas y siete paradas del asistente**. Las pantallas son
inicio, mis cosas, los papeles, el almacén, qué hay sembrado, la ayuda, mis datos, **quién entra en mi
finca**, las medidas, **mi cuaderno**, los análisis, dímelo con la voz, la revisión de lo dictado, guardar
un papel, el plan de abono, mis facturas y añadir una factura; del asistente se recorren dónde se ha
echado, el resumen, las hectáreas, la fecha, **una venta entera**, el alta de una tierra y traer la tierra
del SIGPAC. Todas se
dibujan bien y con datos de verdad dentro (la comprobación siembra una finca). La lista está en
`PANTALLAS` del guion, con cómo se llega a cada una pulsando, y lo que **no** se recorre está en
`NO_SE_RECORREN` con su motivo (hoy solo «firmar», que necesita un certificado puesto).

**Y desde la ronda 54 el guion comprueba una cosa más, que hizo falta:** cada paso de la ruta tiene que
**encontrar lo que busca**. Si un selector no existe, el navegador no pulsa nada y la comprobación se
queda en la pantalla anterior; si los textos que busca también están ahí, **pasa sin haber visto la
pantalla que decía comprobar**. Pasó con «el plan de abono», que se quedó en «mi cuaderno». Ahora la
página apunta en su título lo que no encontró y el guion lo lee y falla.

**Y desde la ronda 62 se recorre también el asistente**, que hasta entonces **no se comprobaba en
ningún navegador** (con sus doce pasos y sus campos obligatorios no cabía en el presupuesto de tiempo de
las capturas, y no había piezas que comprobar). Se recorren sus cuatro momentos clave: la pregunta de
dónde se ha echado, **los dos pasos donde se escribe** (la fecha y las hectáreas) y el camino entero
hasta el resumen. Ahí se comprueba algo que **no se puede comprobar de ninguna otra forma**: que el paso
tiene su formulario dentro del hueco `#formulario`. Desde la ronda 72 ese hueco lo pinta React (es un
`<div id="formulario">` de la pantalla del asistente) en vez de la interfaz vieja, pero el fallo que se
persigue es el mismo: si el formulario del paso no llega (un fichero de `web/react/` que no ha llegado, la
caché de un móvil a medias tras un despliegue), el agricultor ve la pregunta y **nada que contestar**. El
guion lo caza buscando el hueco **vacío** (`<div id="formulario"></div>`), y la lista de pasos donde eso se
comprueba está en `FORMULARIO_CON_PIEZA`.

Y en los pasos de escribir se comprueban **las dos cosas que solo se ven en un navegador de verdad**: que
el campo lleva **su `id`** (`id="superficie_tratada_ha"`, `id="fecha" type="date"`) y que el número lleva
**`inputmode="decimal"`**. Esa última es la que hace salir el teclado de números con coma en el móvil, y
en el HTML estático de los tests no se puede comprobar: allí el atributo sale como `inputMode="decimal"`
(con la mayúscula del nombre de la propiedad de React) y es el analizador del navegador el que lo deja en
minúscula. Lo cazó el propio guion: la primera vez que se añadió la ruta, comparaba `inputmode` en
minúscula contra el HTML de un DOM de mentira y no lo encontraba.

**Y desde la ronda 64 se apunta una venta entera de punta a punta**, que es la comprobación más completa
de todas las que hay. El asistente de la venta usa **todas las piezas a la vez**: las clases de venta
(botones), el producto y la variedad (campos que se escriben), la cantidad, la unidad, la fecha, la lista
de tierras… y el resumen. La ruta **teclea** en los campos que pinta React (`escribir:#producto=Lechuga
romana`) y comprueba que lo tecleado **llega al resumen**: si el `id` de un campo cambiara, el apunte se
guardaría vacío sin que saltara ningún error, y esto lo caza. La captura de esa ruta es la que mejor
enseña que lo que se escribe, se lee y se apunta son la misma cosa.

**El resumen del asistente, visto en un navegador de verdad, se ve así** (captura de la comprobación:
las barras de paso, la pregunta, las filas con su etiqueta y su valor, y los dos botones):

```
🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩
Mira si está bien
Si algo no cuadra, pulsa VOLVER y lo cambias
  ¿Dónde?                                    El Prado
  ¿Cuándo?                                 28/09/2026
  Producto                            Glifosato 36 SL
  Hectáreas                                      4,90
  Por qué              Vi la plaga o la hierba en el campo
  [ VOLVER ]                            [ APUNTARLO ]
```

Y hay un test (`tests/test_comprobar_en_un_navegador.py`) que comprueba que el guion está, que **no
deja ningún fichero dentro de la aplicación**, que la dirección se lee dentro de `main()` y no al
importar el módulo (eso también lo cazó un test: al importarlo desde pytest, `sys.argv` es el de
pytest y el guion creía que el servidor estaba en la ruta de un fichero de tests) y que el lector del
hueco del formulario ve lo que dibuja React.

---

## 6. Lo que todavía NO está resuelto

Se apunta aquí a propósito: es lo que queda y lo que hay que saber antes de tocar las pantallas
grandes. **Nada de esto es un misterio: son decisiones y trampas que ya están pagadas.**

### 6.1 Lo que queda por migrar: nada

**La migración está terminada (ronda 72).** Todo lo que el agricultor ve —las **veintiocho** pantallas de
la tabla del apartado 3, los **nueve avisos de error** (apartado 4 ter) y los **65 pasos del asistente**—
está en React. `pintar()` y `bloqueError()` se borraron: **la aplicación no tiene ni un `innerHTML` de
pantallas**, y el único sitio que escribe en la pantalla es `montar()`.

Lo que queda **no es migrar nada**, y está en dos sitios:

1. **Fuera de la interfaz**, en el objetivo del proyecto: mandar el cuaderno a la Junta por IUWS (que
   necesita el alta del dominio que tiene que pedir David) y las dos decisiones de diseño que dependen de
   él. Está contado en [`TRASPASO_A_OTRO_AGENTE.md`](TRASPASO_A_OTRO_AGENTE.md).
2. **Dentro del código, una cosa que ya se hizo** (ronda 73) y que conviene saber por si vuelve a pasar:
   **24 de las 27 pantallas** repetían el bloque de siempre para montarse (el `let elemento = null;`, el
   `try`, el `catch` y la llamada a `montarEn` con los textos de emergencia). Ahora cada una es una línea:
   `montar(() => pantallaDeX({ … }))`, y `montarEn` tiene **un solo usuario** (la propia `montar()`).
   `app.js` se quedó en **221 líneas menos**. Lo único que se dejó de hacer, en una de las pantallas (la
   de entrar), fue el `window.scrollTo(0, 0)` que no tenía: `montar()` siempre lo hace, y una pantalla que
   se repinta debe empezar por arriba.

**Y lo que mantiene esto terminado**: hay tres pruebas en `tests/test_la_migracion_a_react.py`
(`TestLoQueQuedaDeLaInterfazVieja`) que exigen que **no vuelva** lo viejo: ningún paso con `pintar:`, los
65 pasos con `montar:`, y ni un `innerHTML` de pantallas en `app.js`. Volver atrás es fácil y no se nota
—se copia un paso viejo de otro sitio y ese paso sale en blanco—, así que se vigila.

Y lo que **ya no está** en la lista de pendientes, para que nadie lo busque: **«mi cuaderno»** (ronda 70,
con sus nueve bloques), las **confirmaciones** (ronda 69, con su pieza común), las **tres descargas** (el
cuaderno en papel, los datos en CSV y el fichero de la firma —el botón lo pinta React y la descarga la
sigue haciendo `app.js`, que es quien tiene el token—), los **nueve avisos de error** (ronda 71) y **el
asistente entero** (ronda 72).

### 6.2 El patrón de los formularios, ya decidido y probado

**Los campos son descontrolados: React los pinta con su `id` y `app.js` los lee.** No hay estado
compartido entre las dos mitades, y eso es lo que permite migrar una pantalla sin tocar cómo se
guarda. Lo usan ya `mis_datos`, `medidas`, `dictado`, `nuevo_documento`, `firmar`, `facturas`,
`interpretacion_factura`, `decir_cultivo` y el mapa (el nombre de la parcela).

Tres detalles que se aprendieron a golpes, y que hay que respetar:

1. **El `id` no se puede cambiar.** Si cambia, el agricultor rellena el formulario y se guarda vacío
   **sin que salte ningún error**. Hay pruebas que miran la lista de `id` **entera** (`idsDe` en
   `react.test.js`), y una que rellena el formulario en un navegador de verdad y comprueba lo que
   llega al servidor.
2. **El valor inicial va en `defaultValue`, no en `value`.** Con `value` sin estado, cada tecla borra
   lo anterior. Y en el HTML estático de las pruebas eso sale como `value="..."` (React escribe el
   atributo), así que las pruebas tienen que esperarlo así.
3. **El botón que guarda se deshabilita mientras guarda** y lo dice («Leyendo la factura…»): sin eso,
   la misma factura o el mismo apunte se mandan dos veces.
4. **El asistente no es solo para apuntar: también es el formulario de CORREGIR** (ronda 91, y desde la
   92 también para las tierras y los grupos). Corregir algo lo abre con lo que ya estaba puesto
   —`estado.asistente.borrador` con la traducción del registro guardado (`borradorDeTratamiento` en
   `nucleo.js`, `borradorDeUnaTierra` y `borradorDeUnGrupo` en `app.js`)— y guarda con `PUT` a esa misma
   fila en vez de con `POST`, porque el identificador que viaja a la Junta es el `id` de la fila: crear
   otra al corregir la mandaría dos veces. `abrirAsistente()` **limpia `corregir` siempre**, y eso no es
   un detalle: sin eso, el siguiente apunte nuevo cambiaría el que se acababa de corregir. Lo cuentan
   `docs/CORREGIR_Y_BORRAR.md` y las pruebas (`tests_js/interfaz.test.js`, «guardar una corrección manda
   un PUT…» y «un apunte nuevo se sigue apuntando con POST…»).
5. **Lo que se puede corregir y borrar está en un registro, no en un `if` por tipo** (rondas 92 y 93):
   `OTRAS_COSAS` en `app.js` dice, para cada cosa que no es un apunte del cuaderno —las tierras, los
   grupos, las seis fichas de lo que se usa, los análisis, las ventas, el plan de abono, los papeles y las
   facturas—, de dónde sale su lista, por dónde se manda el cambio, cómo se cuenta en una ficha y con qué
   formulario se abre. Con eso, añadir la siguiente cosa son cuatro líneas y **no** una pantalla de borrar
   nueva (que es como acaban habiendo cinco pantallas de borrar y dos que se olvidan de preguntar). Los
   apuntes del cuaderno siguen con sus propias funciones (se pueden anular, se firman, y cada uno tiene su
   asistente) y las funciones comunes preguntan primero en el registro. Los dos botones son los mismos en
   todas las listas (`botonesDeCorregirYBorrar`) y los pinta **una pieza**
   (`react/piezas/acciones_de_una_ficha.js`, ronda 93: estaba escrita a mano en cuatro pantallas y se
   estaba copiando a las demás). El texto de lo que se está haciendo mientras se corrige viaja al
   asistente en la propiedad `modo` («CORRIGIENDO LO APUNTADO», diseño de Stitch de la ronda 92).
   Y hay tres cosas que **no** abren el asistente al corregirse, porque tienen su propia pantalla: un papel
   (`nuevo_documento`, con sus seis campos) y una factura (`interpretacion_factura`, la que confirma lo
   que se lee). Se dice **dentro de la propia cosa** (`OTRAS_COSAS.documento.corregir` y
   `.factura.corregir`), y `corregirAlgo()` le hace caso antes de intentar abrir el asistente: un `pasos`
   que no existe dejaría la pantalla en blanco. Las dos pantallas se abren en modo corregir con una
   propiedad (`corrigiendo`), y en una factura eso cambia **solo tres cosas** (título, pista y adónde
   vuelve el botón); los campos y las líneas se pintan igual, porque corregir una factura es el mismo
   trabajo que confirmar una lectura.
6. **Al corregir, lo que el formulario no pregunta tiene que viajar igual** (rondas 91, 92 y 93). Es la
   trampa de estas rondas y ha mordido cinco veces: la máquina de una cosecha, las observaciones de una
   labor, la **forma de una tierra**, los **números del boletín de un análisis** y las **notas, el lote y el
   número de registro de una factura** (esta última, vista antes de que hiciera daño: la pantalla de una
   factura no pregunta esos tres datos). La regla, escrita en
   `parcelas.py` y aplicada en el resto: **lo que no se acepta al dar de alta y no se devuelve al leer, no
   se toca al corregir**; y en el navegador, el borrador de la corrección lleva **todos** los campos que la
   API acepta (los pregunta el asistente o no). Hay una prueba de Python que compara los dos lados campo a
   campo (`tests/test_el_formulario_manda_todo.py`) y pruebas de JS que comprueban que el `PUT` lleva lo
   que no se ve. Y una que comprueba **en qué pantalla acaba** el botón de volver: el nombre de la
   pantalla de destino tiene que estar en `irAInicio`, o el botón cae en el `default` y lleva al inicio
   sin que ninguna prueba que mire el `data-ir` se entere.

### 6.4 La versión de ordenador: el armazón y las tablas (30/09/2026)

David lo pidió así: *«debe ser responsive para usarse en pc y móvil, no solo móvil… no es una app usable de
gestión»*. Lo que se añadió, y cómo, para que nadie lo deshaga creyendo que sobra:

1. **El armazón vive fuera del contenedor de las pantallas** (`#marco`, en `index.html`), y lo pinta
   `react/piezas/marco.js`: el menú lateral con los módulos y la barra de arriba (campaña, cuenta y
   apuntar). **No se monta con `montar()`** sino con `montarFueraDeLaPantalla()`, y se apunta en **su propia
   lista** (`montajesDelMarco`, en `react/montar.js`) — no en `montajes`. El motivo está escrito allí: las
   pruebas de cableado cuentan **cuántas pantallas** se le piden a React al pulsar un botón (`se han pedido N
   montajes: solo esta`, más de treinta veces), y el armazón se monta cuando cambia el **módulo**. Si se
   apuntara en la misma lista, esas treinta pruebas dejarían de comprobar lo que comprueban.
2. **El módulo activo lo dice la pantalla que está puesta**, con la tabla `MODULO_DE_LA_PANTALLA` de
   `app.js` (componente → módulo). «Mi cuaderno» se abre desde el menú, desde la pantalla de inicio y desde
   el aviso de lo que falta: en los tres sitios tiene que marcar el mismo renglón.
3. **La misma lista, dos formas, en el mismo HTML**: `.solo-escritorio` (la tabla) y `.solo-movil` (las
   tarjetas), y el CSS enseña una u otra según el ancho. **No se elige con JavaScript**: si se eligiera, la
   elección dependería de la ventana en el momento de pintar y habría dos caminos que se podrían separar.
   Los datos, los textos y los `data-accion` son los mismos en las dos.
4. **La tabla es una pieza** (`react/piezas/tabla.js`): columnas (con su `data-campo` si se pueden
   ordenar), filas, acciones por fila y el total del pie. **No calcula nada**: los totales, el orden y lo
   que va en ámbar los prepara `app.js`. La flecha de «por aquí va el orden» **la pone el CSS**
   (`.tabla-ordenada::after`), no una frase dentro del componente.
5. **Ordenar es un `data-accion` más** (`ordenar-tabla`, con `data-tabla` y `data-campo`): pulsar una
   cabecera ordena y volver a pulsarla le da la vuelta. El orden es **de la pantalla**, no del aparato, así
   que las tarjetas del móvil salen en el mismo orden.
6. **Lo que NO cambia**: los textos del servidor, los colores del `:root`, el manejador de clics único y
   los formularios no controlados. Las medidas nuevas viven dentro de los `@media` del ordenador.
7. **Cada tabla ordena la suya y repinta SU pantalla** (`repintarLaPantallaDeLaTabla`, `app.js`). Antes esto
   era un `if` con dos casos —«¿es la del cuaderno?»—, y con cinco tablas hacía lo peor que puede hacer un
   programa de gestión: pulsar una cabecera en la tabla de **facturas** ordenaba **la lista de tierras** y
   llevaba al agricultor a otra pantalla. El orden de entrada de cada tabla está en `ORDEN_DE_ENTRADA`, y la
   que se añada mañana tiene que traer su línea y su entrada (hay una prueba para cada una).
8. **El panel de detalle** (`Panel`, en la misma pieza) va al lado de la tabla, dentro de `.tabla-y-panel`, y
   lo enseña la fila que se ha tocado: se toca el **nombre** (que es un botón, no la fila entera) y su ficha
   sale al lado, con sus datos y sus botones; volver a tocar el mismo nombre lo cierra. La tabla va dentro de
   `.tabla-scroll` para que no se apriete contra el panel. **Y por debajo de 72 rem el panel pasa debajo de la
   tabla**: con el menú (17 rem), los márgenes (4), el panel (20) y su hueco (1), a una tabla de cinco columnas
   le quedan 22 rem cuando necesita 30 —y dejaba fuera la columna de Acciones—; la cuenta está escrita en el
   CSS y en `tests/test_el_armazon_del_ordenador.py`, y salió de mirar la versión de ordenador con las 64
   tierras de verdad (`docs/REVISION_DE_LA_UI.md`).

Y lo que **falta** de esa versión (fases 2 a 5 de `docs/LA_APLICACION_DE_GESTION.md`): las tablas de las
listas que quedan (los seis maestros, los análisis y las ventas), los filtros de verdad, los paneles de las
demás listas y el panel de mando de verdad. Las seis tablas hechas son las de **tierras, cuaderno, años,
facturas, almacén y qué hay sembrado**, y con panel, las de **tierras y almacén**.



1. **Las frases compuestas se montan en `app.js`, no en el componente.** Si un componente une dos
   textos del servidor con un `·` o un `:`, la prueba de «ni una frase escrita a mano» lo caza (pasó
   tres veces: la cabecera del plan de abono, el «Leída de: …» de la factura y **las dos fechas de una
   venta unidas con una raya** —«18/07/2026 — 19/07/2026»—, que eran dos valores preparados que el
   componente juntaba).
2. **Nada de `esc()`** dentro de un componente: React escapa solo. Y **nada de `style`**: los colores
   viven en el `:root` de `estilos.css`.
3. **Un comentario dentro de una plantilla `htm` no puede llevar comillas invertidas**: cierra la
   plantilla y la aplicación no arranca. Pasó.
4. **El toque del mapa no se engancha al componente.** El manejador delegado de `document` necesita
   saber **dónde** se ha tocado; si el toque se enganchara a React, se perdería la posición.
5. **Las acciones que el manejador no conoce no hacen nada.** Hay una prueba
   (`tests/test_los_botones_hacen_algo.py`) que compara lo que se pinta con lo que se atiende.
6. **Cada texto que se pide tiene que existir**, y con la función que le toca (`accion`, `aviso`,
   `mensaje`): `tests/test_que_no_falte_ningun_texto.py`. Un texto que falta no revienta: deja un
   hueco.
7. **Una prueba que lee el sitio equivocado pasa sin comprobar nada, y encima tapa un fallo de
   verdad.** Al reescribir la prueba del grupo de parcelas contra la pieza nueva se descubrió que
   **nunca llegaba al resumen**: contaba los «10,00» del HTML y el «10,00 ha» estaba en la **pista del
   botón del grupo**, así que pasaba sin haber avanzado ni un paso. Y debajo había un fallo real: al
   elegir un grupo se borra la tierra (un apunte es de una o del otro) y el paso seguía exigiendo la
   tierra, así que el agricultor **se quedaba encerrado** con un aviso de que le faltaba justo lo que
   acababa de sustituir. Se arregló en `exigeSitio()`. La misma trampa volvió a aparecer al migrar el
   campo: la prueba de las hectáreas pulsaba un «SEGUIR» de más y leía **el montaje del paso anterior**
   (la justificación no monta nada, así que el último montaje seguía siendo el campo). Moraleja: al
   migrar una prueba, comprobar que **de verdad está en la pantalla** que dice comprobar, y desconfiar
   de las que pasan a la primera. La comprobación en un navegador de verdad lo cazó: la misma ruta, con
   un «SEGUIR» de más, acababa en la pantalla de la justificación y no encontraba el campo.
8. **Cuando un paso se migra, sus etiquetas dejan de estar donde las buscaban las pruebas.** Al pasar
   las fichas del maestro a React, `avanzarHasta(entorno, "¿Qué carné tiene?")` **dejó de encontrar la
   pregunta**: la pregunta del paso es genérica («¿Quieres afinar más?», porque son varios datos
   juntos) y el texto que se buscaba era la **etiqueta de un bloque**, que ya no está en el HTML del
   contenedor. El test se iba al resumen y decía que el paso no existía, con la aplicación
   perfectamente bien. Se arregló haciendo que `avanzarHasta` busque **en los dos sitios**: en la
   pregunta que pinta la interfaz vieja y en lo que se le ha pedido a React. Y las comprobaciones que
   miraban el HTML de esos pasos se han reescrito contra **lo que se le pide a la pieza**
   (`bloquesDelMaestroPedidos()`, `idsDeLosBloques()`, `opcionesDelBloque()`): los `id` de los campos,
   las opciones de cada bloque de elegir y sus textos.
9. **Al mover un bloque a un componente, sus condiciones se mudan con él.** En «mi cuaderno», el botón de
   firmar solo salía **si se podía firmar**, y eso era un `if` dentro del HTML: al pasar los datos al
   componente, la condición se quedó en el camino y la pantalla ofrecía firmar sin certificado —un botón
   que lleva a un error, que es justo lo que no se quiere—. Lo cazó la prueba de cableado («sin
   certificado no sale el botón de firmar»), que es exactamente para lo que está: al migrar, repasa
   **cada `if` y cada bucle** de la función que borras y comprueba que sigue vivo en los datos o en el
   componente.
10. **Cada aviso lleva su texto como lo llevaba.** En «mi cuaderno», unos avisos van con su texto dentro
   de un `<p>` y otros suelto, y **no es un descuido**: el `<p>` añade aire por dentro, y cambiarlo mueve
   la altura de media pantalla. Por eso el aviso lleva un `enParrafo` en vez de decidirlo el componente.
11. **Un ayudante del servidor de mentira, para probar lo que falla.** Los avisos de error no se podían
   probar: el servidor de las pruebas daba por bueno todo lo que estuviera en su lista, y poner
   `undefined` en una ruta solo vale para las que no existen de verdad (una ruta que se pide con GET y se
   manda con POST —`/api/medidas`— seguía dándose por buena al mandarla). Ahora hay un ayudante **`falla()`**
   en `interfaz.test.js`: la respuesta marcada con `FALLA` contesta **422** (y no 500, porque un 5xx se
   guarda en la cola del móvil para reintentarlo: lo que se prueba es el aviso, no la cola) con el motivo
   que le digas, y así se comprueba que **el motivo del servidor llega entero al agricultor**.

### 6.4 Lo que sigue igual que antes

1. **Las pruebas que miran HTML.** `interfaz.test.js` tiene 230 pruebas y **ya casi ninguna lee el HTML
   del contenedor** —porque el contenedor está vacío: lo pinta React—; lo que se lee es **lo que se le
   pide a React**: `pantallaPedida()` (el contenedor y lo pedido, juntos), `textosDeLoPedido()`,
   `piezasPedidas()` (el formulario del paso), `campoPedido()`, `listaPedida()`, `bloquesDelMaestroPedidos()`
   y `resumenPedido()`.
   Las de cada pantalla migrada se han movido a `react.test.js` reescritas contra el componente (302
   pruebas ya allí, 621 entre los tres ficheros); el resto tendrá que hacer lo mismo, pantalla a
   pantalla, y **ninguna se puede tirar
   sin dejar su equivalente**. Hay cinco casos que conviene saber: al migrar «decir qué hay sembrado» se
   descubrió que la copia de la API que usan las pruebas **no tenía la ruta del alta del cultivo**, así
   que la prueba del camino bueno estaba comprobando el aviso de error; al migrar la lista de tierras
   apareció la prueba que **pasaba sin llegar al resumen**; al migrar el campo, la prueba de las
   hectáreas **leía el montaje del paso anterior**; al migrar las fichas del maestro, `avanzarHasta`
   dejó de encontrar los pasos migrados porque **buscaba las etiquetas en el HTML del contenedor**, donde
   ya no están: se arregló haciendo que busque también en lo que se le pide a React (**un paso migrado
   que «desaparece» para una búsqueda es un test que se va al resumen sin darse cuenta**); y al migrar las
   medidas y «cómo se echó», las pruebas contaban los `boton-elegido` del HTML, que ya no existen —ahora
   se mira **qué botones se le piden marcados** (`botonesMarcados()`), que es la misma comprobación—. Lo
   último está contado en el apartado 6.3, punto 7. Al migrar, mira si la ruta existe de verdad y si la
   prueba **está de verdad** donde dice estar.
2. **React está clavado en la 18.** La 19 no publica ficheros UMD, así que hoy no se puede subir sin
   volver a compilar (y sin Node donde corre esto, no se puede compilar). Está comprobado en
   `backend/tests/test_react_vendor.py`.
3. **Cada montaje crea una raíz de React nueva.** Es lo que hace que las dos interfaces puedan convivir
   (ver el apartado 3), pero las raíces viejas se quedan hasta que las recoja el recolector de basura,
   con sus escuchadores enganchados al contenedor. En una sesión normal son unas decenas; el día que se
   migre todo habrá que hacerlo bien (una sola raíz, o desmontar la anterior).
