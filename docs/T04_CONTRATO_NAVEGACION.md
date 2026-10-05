# T04 / E1 — Contrato de navegación y direcciones reproducibles

> **Lo que hace este documento.** Fija **qué direcciones tiene la aplicación**, **por qué son de
> fragmento** (`#/tierras/12`) y no de camino, **qué entrega esta primera parte de T04** (el módulo
> `web/react/rutas.js`, el contexto de la barra en `web/react/piezas/marco.js` y sus pruebas) y **qué
> falta para que la aceptación esté cumplida**, con la lista de lo que hay que tocar y en qué fichero.
>
> **Segunda entrega (03/10/2026): las pantallas que todavía no tenían dirección.** La primera entrega dejó
> dirección a 18 pantallas y **13 sin ella, sin decidir**. En la segunda entrega se decide **una por una**
> (§9.3): **siete estrenan dirección** (el mapa, decir el cultivo de una tierra, el borrador, el dictado,
> quién entra, la revisión de una factura guardada y firmar) y **seis se quedan sin ella a propósito**, con
> el motivo escrito, porque son pasos de un formulario. Y **lo que ya estaba se corrige**: los pasos de un
> formulario **ya no escriben la dirección de su módulo** (antes, abrir el asistente en una tierra dejaba la
> barra en `#/cuaderno`).
>
> **Lo que NO hace.** No toca `service-worker.js` ni `textos.py` ni `estilos.css` (no son de este encargo):
> lo que hace falta de cada uno está escrito aquí, apartado por apartado, con el nombre del fichero y la
> línea que lo demuestra. **No levanta ningún servidor y no abre ningún navegador**: lo que no se ha
> comprobado se dice en el apartado 10, no se da por bueno.
>
> **Cómo se ha hecho.** Leyendo `AGENTS.md`, `DESIGN.md`, `docs/GUIA_UI_UX.md`, `docs/REACT.md` y
> `docs/SEGUIMIENTO_IMPLEMENTACION_CRM.md` (§3, T03 → T04); leyendo el servidor de ficheros de la web
> (`app/main.py`) y el `service-worker.js` para el porqué del `#`; sacando las claves del menú de la tabla
> `MODULOS` de `app.js` y las palabras de `textos.MENU`; y ejecutando las pruebas que ya existían antes de
> escribir nada.
>
> **Fecha:** 02/10/2026 (primera entrega) y 03/10/2026 (segunda entrega).

---

## 1. La aceptación, en una línea

> **«Abrir una ficha por su dirección, recargarla y volver conservando la campaña y los filtros.»**
> (`docs/SEGUIMIENTO_IMPLEMENTACION_CRM.md`, tabla de tickets, T04 / E1)

Lo que hay para eso, hoy:

| Pieza | Estado |
|---|---|
| La **dirección** de una ficha de tierra: `#/tierras/12?campana=2026&finca=3` | **Entregada y probada** (`web/react/rutas.js`) |
| La **traducción** dirección ↔ pantalla, en las 25 pantallas | **Entregada y probada** (45 pruebas en `tests_js/rutas.test.js`) |
| La **memoria de la vista** de un listado (volver del detalle sin perder los filtros) | **Entregada y probada** (ayudantes `recuerda`/`recupera`/`olvida`/`direccionDe`) |
| La **finca y la campaña en la barra**, con sus botones de cambiar | **Entregada y probada** con el prop `contexto` (sin el prop, la barra es de siempre) |
| El **cableado**: que `app.js` escuche la barra de direcciones, la escriba al navegar y monte la pantalla | **Entregado** por el coordinador (ronda 3), y **corregido y ampliado** en la segunda entrega (§9.3) |
| **Las 13 pantallas que faltaban** | **Decididas una por una** (§9.3): 7 con dirección (probadas) y 6 sin ella a propósito |
| **Que un paso de un formulario no escriba dirección** | **Entregado y probado**: antes el asistente dejaba la barra en `#/cuaderno` |
| Las **claves de texto** nuevas en `textos.py` | **Ninguna nueva en la segunda entrega**: no hizo falta ni una frase |
| Las **cuatro claves** de la primera entrega en `textos.py` | **Entregadas**: están en `textos.MARCO` (`textos.py:4211`) |
| **`service-worker.js`**: guardar `rutas.js` para el campo | **Entregado**: está en `FICHEROS` (`service-worker.js:232`) y su prueba de Python pasa |

**Dicho de la forma más clara que sé:** el módulo que traduce direcciones está terminado, probado y
**cableado** (la primera entrega lo dejó pendiente y el coordinador lo enchufó en la ronda 3, con la
aceptación comprobada en un navegador de verdad). Lo que quedaba era **la mitad de las pantallas sin
dirección**, y de eso se ocupa la segunda entrega (§9.3): siete la estrenan y seis se quedan sin ella con el
motivo escrito.

---

## 2. Qué ficheros entran, y qué otros habría que tocar (y quién)

**Los ficheros de la primera entrega:**

| Fichero | Qué es |
|---|---|
| `backend/web/react/rutas.js` | **NUEVO.** El módulo puro: pantallas, `leer`, `escribir`, la memoria de la vista y los enlaces de fila. |
| `backend/web/react/piezas/marco.js` | **MODIFICADO, solo añadiendo.** El prop opcional `contexto` (la finca y los botones de cambiar de campaña y de finca). |
| `backend/tests_js/rutas.test.js` | **NUEVO.** Las pruebas del módulo, sin navegador. |
| `docs/T04_CONTRATO_NAVEGACION.md` | **NUEVO.** Este documento. |

**Los ficheros de la segunda entrega (03/10/2026, las 13 pantallas que faltaban):**

| Fichero | Qué se ha hecho |
|---|---|
| `backend/web/react/rutas.js` | **Siete pantallas nuevas en la tabla** (`decir_cultivo`, `firmar`, `interpretacion_factura`, `quien_entra`, `mapa`, `dictado`, `borrador`) y el porqué de las seis que **no** están. |
| `backend/web/app.js` | `PANTALLAS_SIN_DIRECCION` (los pasos no escriben dirección), `DIRECCION_PROPIA` (la dirección de cada pantalla que no es la de su módulo), el cableado en `apuntarLaDireccion` y en `abrirLaPantalla`, las cinco entradas nuevas de `ABRIR_LA_PANTALLA` y los cuatro renglones que le faltaban a `MODULO_DE_LA_PANTALLA` (el menú se quedaba sin marcar con el mapa, la firma y el dictado delante). |
| `backend/tests_js/rutas.test.js` | **7 pruebas nuevas** (38 → 45). |
| `backend/tests_js/interfaz.test.js` | **12 pruebas nuevas** (266 → 278). |
| `docs/T04_CONTRATO_NAVEGACION.md` | La decisión de las 13 pantallas, una por una (§9.3), y lo comprobado (§10 y §11). |

**Los que no eran de la primera entrega** (los cinco son del coordinador; el detalle y **la comprobación de
que están hechos**, en el apartado 9.1):

| Fichero | Qué hacía falta, y cómo está |
|---|---|
| `backend/web/app.js` | Leer la dirección al arrancar, escuchar el historial, escribir la dirección al navegar, montar la pantalla que toque y atender `cambiar-campana` y `cambiar-finca`. **Hecho** en la ronda 3 (y esta segunda entrega lo ha ampliado: §9.3). |
| `backend/web/service-worker.js` | Añadir `"/react/rutas.js"` a `FICHEROS` (y subir el número de la caché). **Hecho** (`service-worker.js:232`). |
| `backend/app/textos.py` | Las cuatro claves del apartado 7.4. **Hechas**, en `textos.MARCO` (`textos.py:4211`). |
| `README.md`, `AGENTS.md`, `docs/LO_QUE_PIDE_LA_JUNTA.md` | El recuento de pruebas de JavaScript: **hecho**, los tres dicen **712** (apartado 11.3). |
| `backend/web/estilos.css` | **Nada.** Los botones nuevos usan clases que ya existen (`.boton-letra`, `.boton-elegido`, `.barra-dato`, `.barra-rotulo`, `.barra-valor`), así que no hace falta ni una regla nueva. Y la segunda entrega **no añade ninguna pantalla visual**: no hay ni un componente nuevo. |

---

## 3. Las pantallas y sus direcciones

**Veinticinco pantallas** (las 18 de la primera entrega y las 7 de la segunda). La clave es la que devuelve
`leer` y la que acepta `escribir`.

| Clave | Dirección | Qué es | ¿Está en el menú? |
|---|---|---|---|
| `inicio` | `#/` | La pantalla de inicio (el panel) | Sí, como renglón «Panel» (clave de menú `panel`) |
| `tierras` | `#/tierras` | El listado de tierras | Sí (`tierras`) |
| `tierra` | `#/tierras/<id>` | **La ficha de una tierra** (la aceptación) | No: se llega desde el listado |
| `decir_cultivo` | `#/tierras/<id>/cultivo` | **Decir qué hay sembrado en esa tierra** | No: se llega desde «qué hay sembrado» o desde la ficha |
| `cuaderno` | `#/cuaderno` | El cuaderno del año | Sí (`cuaderno`) |
| `firmar` | `#/cuaderno/firmar` | **Firmar el cuaderno** | No: se llega desde «mi cuaderno» |
| `apunte` | `#/cuaderno/<id>` | Un apunte del cuaderno | No: se llega desde el cuaderno |
| `almacen` | `#/almacen` | Lo que tengo en el almacén | Sí (`almacen`) |
| `facturas` | `#/facturas` | Mis facturas | Sí (`facturas`) |
| `interpretacion_factura` | `#/facturas/<id>` | **Revisar o corregir una factura guardada** | No: se llega desde la lista |
| `anos` | `#/anos` | Los años del cuaderno | Sí (`anos`) |
| `grupos` | `#/grupos` | Los grupos de parcelas | Sí (`grupos`) |
| `cultivos` | `#/cultivos` | Qué hay sembrado | Sí (`cultivos`) |
| `analisis` | `#/analisis` | Los análisis | Sí (`analisis`) |
| `plan` | `#/plan` | El plan de abono | Sí (`plan`) |
| `ventas` | `#/ventas` | Lo que he vendido | Sí (`ventas`) |
| `medidas` | `#/medidas` | Lo que hago sin echar producto | Sí (`medidas`) |
| `papeles` | `#/papeles` | Los papeles | Sí (`papeles`) |
| `junta` | `#/junta` | El cuaderno de la Junta | Sí (`junta`) |
| `datos` | `#/datos` | Mis datos | Sí (`datos`) |
| `quien_entra` | `#/datos/quien-entra` | **Quién entra en mi finca** | No: se llega desde «mis datos» |
| `ayuda` | `#/ayuda` | La ayuda | Sí (`ayuda`) |
| `mapa` | `#/mapa` | **El mapa** | No: se llega desde el alta de una tierra |
| `dictado` | `#/dictado` | **Dímelo con la voz** | No: se llega desde la pantalla de inicio |
| `borrador` | `#/borrador` | **La revisión de lo que has dictado** | No: se llega desde el dictado |

**Las direcciones son estables a propósito**: son lo que se puede enlazar, guardar en un marcador o
mandar por mensaje. Cambiar una clave es romper todos los enlaces que alguien tenga guardados, así que
una clave no se cambia por gusto.

**Dos reglas de forma, y las dos tienen prueba:**

1. **Dentro de cada familia, el tramo fijo va antes que el identificador** (`#/cuaderno/firmar` va por
   encima de `#/cuaderno/<id>` en la tabla). Hoy no haría falta —un identificador tiene que ser un número y
   `firmar` no lo es— pero es la regla que evita que `#/tierras/nueva` acabe abriendo la ficha de la tierra
   «nueva» el día que alguien la añada.
2. **Un identificador que no es un número no es la ficha de nada** (`#/facturas/abc` no lleva a ninguna
   parte). Está dicho en §5.2 y probado.

**Y una tercera que es una decisión, no una forma:** las seis pantallas que **no** están en esta tabla (el
asistente, «lo he apuntado», entrar, el alta de un papel, la de una factura y el paso del SIGPAC) **no
tienen dirección a propósito**, y `app.js` no les escribe ninguna. El porqué, uno por uno, en §9.3.

---

## 4. Por qué el `#` (y no `/tierras/12`)

Esta es la decisión que hay que entender antes de tocar nada, porque parece una antigualla y es lo
contrario: **es la única forma de que una ficha tenga dirección sin tocar el servidor**. Los dos motivos
se suman:

1. **El servidor no tiene «fallback» de aplicación de una sola página.** Los ficheros de la web se montan
   en `/` con `StaticFiles(..., html=True)`: eso sirve un fichero por su nombre y punto. `/tierras/12` no
   es ningún fichero, así que el servidor contesta **404** y recargar la ficha de una tierra sería
   encontrarse con una pantalla que no existe.
2. **La aplicación tiene que abrirse sin cobertura.** La abre el *service worker* desde la caché, y lo que
   hay en la caché es el `index.html`. Cualquier dirección que no sea la raíz no está en la caché, así que
   sin cobertura daría igualmente un error. Y esto no se arregla con una regla más en el servidor: el
   segundo motivo seguiría ahí.

La parte que va **después del `#` no llega nunca al servidor**: la corta el navegador antes de pedir nada.
Por eso `#/tierras/12` funciona recargando, abriendo un enlace directo, sin cobertura y con el servidor
caído, y es lo que el ticket de T04 pedía.

**Lo que esto NO arregla, y se dice:** una dirección de fragmento no se puede indexar ni se puede pedir
desde el servidor (no hay `GET /tierras/12` que devuelva nada útil), y el `#` no viaja en la petición, así
que no sirve para compartir un enlace con nadie que no abra la aplicación. Para esta aplicación —un
agricultor, su móvil y su cuaderno— eso no es un problema: lo que hacía falta era poder recargar y volver,
no publicar fichas en internet.

---

## 5. El contrato de `rutas.js`

El módulo es **puro**: no llama a `fetch`, no lee `localStorage`, no toca el DOM, no usa `history` y no
mira `window`. Hay una prueba que lee su código y lo comprueba (`tests_js/rutas.test.js`, «rutas.js no toca
el navegador»), y **no lleva ni una frase para el agricultor**: aquí no hay textos, solo direcciones.

### 5.1 Lo que se puede pedir

| Se exporta | Qué hace |
|---|---|
| `PANTALLAS` | La tabla: `{clave, patron}`. El patrón son los tramos; un tramo que empieza por `:` es un identificador numérico. |
| `LISTADOS` | Las seis listas con buscador y orden: `tierras`, `cuaderno`, `facturas`, `anos`, `almacen`, `cultivos`. |
| `leer(direccion)` | `{pantalla, parametros, desconocida}`. |
| `escribir(pantalla, parametros)` | La dirección. `""` si esa pantalla no tiene dirección posible. |
| `esConocida(pantalla)` · `pantallas()` · `esUnListado(pantalla)` | Consultas de la tabla. |
| `enlaceDeTierra(id, parametros)` · `enlaceDeApunte(id, parametros)` | El enlace de una fila de la lista, con la vista dentro. |
| `direccionDe(vista)` | La dirección de lo que devolvió `leer` (para volver). |
| `recuerda(memoria, clave, vista)` · `recupera(memoria, clave)` · `olvida(memoria, clave)` | La memoria de la vista, **sobre un objeto que se le pasa** (nunca estado del módulo). |

### 5.2 Cómo se lee (y por qué así)

| Caso | Qué hace | Por qué |
|---|---|---|
| `""`, `"#"`, `"#/"`, `"/"` | `inicio` | Las cuatro son la misma cosa. Con dos formas distintas de escribir el inicio, el historial se llena de direcciones que llevan al mismo sitio. |
| `#/tierras/12?campana=2026&finca=3` | `pantalla: "tierra"`, `{id: 12, campana: 2026, finca: 3}` | El `id` sale **número**, no texto: con texto, `12 === "12"` es falso y la ficha que se pide no es la que se muestra. La campaña y la finca, igual (son identificadores). |
| Sin `#` (`/tierras/12`), con barra final (`#/tierras/12/`), con barras de más (`#/tierras//12`) | Lo mismo | Una dirección se copia, se pega y se escribe a mano. |
| En mayúsculas (`#/Tierras/12`, `?Campana=2026`) | Lo mismo | En un teclado de móvil la primera letra sale en mayúscula, y pedirle a nadie que lo escriba en minúscula es pedirle que se equivoque. |
| Parámetro vacío (`?campana=&q=`) | No existe: es como no ponerlo | Un filtro en blanco es no tener filtro. Así una dirección con los huecos puestos vale lo mismo que la limpia. |
| Parámetro repetido (`?campana=2026&campana=2027`) | Gana el **primero** | Es lo que hace `URLSearchParams`, que es con lo que se escriben las direcciones de verdad. Una sola regla, la del navegador. |
| Parámetro que no conocemos (`?lo_que_sea=1`) | Se queda, como texto | Un filtro que no entendemos es justo lo que no hay que borrar en silencio: puede ser de una pantalla que se añade mañana. |
| `#/lo-que-sea` | `desconocida: true`, `pantalla: ""`, `parametros: {}` | El módulo no adivina media dirección. |
| `#/tierras/abc`, `#/tierras/1.5`, `#/tierras/-3` | `desconocida: true` | Un identificador es un número entero escrito con dígitos. Lo que no lo es, no es la ficha de nada. |
| Cualquier cosa rara (`#%%%`, un `%` suelto, `null`, un número) | Una respuesta, **nunca una excepción** | Esto lo llama el arranque de la aplicación: una excepción aquí no es «una dirección que no se entiende», es **la aplicación que no arranca**. |

**Y lo que el módulo NO puede saber, y por eso no lo dice:** si la tierra 12 existe o si es de este
agricultor. Eso lo decide el servidor, que contesta **404** (y no 403, para no contar si el identificador
existe en otra finca). Por eso aquí no hay ningún estado «no existe» ni «no es tuya»: inventarse uno sería
enseñar un aviso equivocado encima de un dato que sí existe. Es la regla de la casa
(`AGENTS.md` §3.3: lo que no se sabe se queda en blanco).

### 5.3 Cómo se escribe

| Caso | Qué hace | Por qué |
|---|---|---|
| Orden de los parámetros | **Alfabético por el nombre**, se pase como se pase | Dos direcciones con los mismos filtros tienen que escribirse **igual**. Si no, el historial se llena de direcciones distintas que llevan al mismo sitio y «atrás» da dos pasos para volver a lo mismo. |
| Valor vacío, `null` o `undefined` | **No se escribe** | Un parámetro que no dice nada es un parámetro de más. |
| El identificador de la ficha | Va en el camino y **no se repite** en la consulta | Una dirección con dos verdades dentro es una dirección que no se sabe leer. |
| Acentos y espacios (`q=Peñaranda de Bracamonte`) | `q=Pe%C3%B1aranda%20de%20Bracamonte`, y vuelve entero | Con `encodeURIComponent`. Un valor con `&`, `=` o `#` dentro también sobrevive: hay prueba. |
| Valores que no son texto (`campana: 2026`) | Se escriben como texto y se leen como número | La forma canónica es una sola, y la usan las dos direcciones (leer y escribir), así que la ida y la vuelta no cambia nada. |
| Pantalla que no está en la tabla, o ficha sin identificador | Devuelve `""` | `""` no es una dirección: quien la reciba **no debe tocar la barra de direcciones**. Devolver `#/` sería decir que esa pantalla existe, que es lo que no es verdad. `esConocida` está para preguntarlo antes. |

---

## 6. La memoria de la vista

Es lo que hace que **volver del detalle no pierda los filtros** (la segunda mitad de la aceptación).

```js
// De la lista a la ficha, y de la ficha a la lista con lo que había.
const listado = leer("#/tierras?campana=2026&finca=3&orden=numero&q=El%20Prado&sentido=1");
let memoria = recuerda({}, "tierras", listado);          // la vista del listado, guardada
const ficha = leer(enlaceDeTierra(12, listado.parametros)); // #/tierras/12?campana=2026&…
const vuelta = leer(direccionDe(recupera(memoria, "tierras"))); // la lista, con sus filtros
```

Tres decisiones, y sus motivos:

1. **La memoria la trae quien llama** (`memoria` es un parámetro), no vive dentro del módulo. Un estado
   dentro del módulo no se puede probar sin ensuciar la prueba de al lado (una deja la campaña 2026 puesta
   y la siguiente la encuentra puesta), y el día que haya dos listas abiertas se pisarían.
2. **Devuelven una copia**: no se toca el objeto que se les pasa, así que `app.js` puede guardarlo en su
   `estado` sin miedo a que otra cosa lo esté usando a la vez.
3. **Lo que no se ha guardado es `null`**, no un objeto vacío: un objeto vacío se leería como «hay una
   vista sin filtros» y llevaría al agricultor a una lista distinta de la que dejó. Y una vista `null` al
   guardar **olvida** la clave: una vista vacía no es una vista.

---

## 7. El armazón: el prop `contexto` (`marco.js`)

### 7.1 Qué se le pasa

```js
marcoDeLaAplicacion({
  textos: { menu: t("menu", {}), acciones: t("acciones", {}) },
  cuenta: "David Pérez Velasco",
  campana: "2026",
  modulos: MODULOS.map(…),
  contexto: {                       // NUEVO, y OPCIONAL
    finca: "El Prado",              // el nombre de la finca en la que se está trabajando
    campana: 2026,                  // el año que se está llevando
    campanas: [2026, 2025, 2024],   // los años que se pueden elegir (o fichas de /api/campanas)
    fincas: [                       // las fincas en las que puede entrar esta cuenta (/api/fincas)
      { id: 3, nombre: "El Prado", activa: true },
      { id: 7, nombre: "La Vega" },
    ],
  },
});
```

Se acepta lo que el servidor manda tal cual: las fincas son `FincaSalida` (`id`, `nombre`, `municipio`,
`papel`, `activa`, `hectareas`) y los años pueden llegar como años a secas o como `CampanaSalida`
(`{id, anio, …}`). Traducirlo es cosa del componente, no de `app.js`.

### 7.2 Qué se ve

- **La finca**, con el rótulo del servidor, a la izquierda del año (lo primero que hay que saber para no
  apuntar en la finca que no es).
- **Un botón por finca** y **un botón por año**, dentro de su dato de la barra: `data-accion="cambiar-finca"`
  y `data-accion="cambiar-campana"`, con `data-valor="<id de la finca>"` y `data-valor="<año>"`. Es el
  convenio de toda la aplicación: un solo manejador de clics lee `data-accion` y decide, así que el armazón
  no tiene ninguna lógica propia de navegación.
- **El que está elegido** lleva la clase `.boton-elegido` **y** `aria-current="true"`: el color solo no
  informa (regla de la casa).
- Si falta la lista de fincas, se enseña **el nombre**; si falta el nombre, la palabra del servidor
  (`Sin finca`), nunca un guion. Y una finca sin nombre o sin identificador **no se pinta como botón** (un
  botón que no dice a qué finca cambia es peor que no tenerlo).

### 7.3 Sin `contexto`, la barra es exactamente la de siempre

No es una promesa: hay dos pruebas que lo miden.

- `tests_js/react.test.js` → «la barra dice el año y la cuenta, y lleva el botón de apuntar» y «sin año y
  sin cuenta no se queda un hueco»: **no se han tocado** y siguen pasando (se corrió el fichero entero: 330
  pruebas, 330 en verde).
- `tests_js/rutas.test.js` → «sin contexto, la barra es exactamente la de siempre»: comprueba que no
  aparece ni el rótulo de la finca ni ningún botón de cambiar, y que el dibujo con `contexto: null` es
  **idéntico** al de sin prop.

### 7.4 Las claves de texto que hay que añadir a `textos.py`

Cuatro, y ninguna más. **Las palabras las pone el servidor**, como todas: el armazón no escribe ni una
frase (hay una prueba que pinta el armazón con contexto y revisa que cada frase que se ve venga del
servidor o sea un dato: un año o el nombre de una finca).

| Clave | Texto propuesto | Para qué es |
|---|---|---|
| `marco.finca` | `Finca` | El rótulo del dato de la finca en la barra (el mismo papel que `menu.campana`, que dice `Campaña`). |
| `marco.sin_finca` | `Sin finca` | Lo que se lee cuando no hay nombre de finca (el mismo papel que `menu.sin_campana`, que dice `Sin año`). **Nunca un guion ni un hueco.** |
| `marco.cambiar_campana` | `Cambiar de campaña` | El nombre del grupo de botones de los años: lo lee un lector de pantalla al llegar a la fila de años. |
| `marco.cambiar_finca` | `Cambiar de finca` | Lo mismo para el grupo de botones de las fincas. |

**Dónde ponerlas, y por qué vale cualquiera de los dos sitios.** El armazón lee estas palabras de
`textos.marco` y, si no están ahí, de `textos.menu` — que es el bloque que `app.js` manda hoy
(`textos: { menu: t("menu", {}) }`). Hay una prueba que comprueba que las dos formas dan **el mismo
dibujo**, así que se pueden añadir a `textos.MENU` (lo más corto: `app.js` no cambia) o a un `textos.MARCO`
nuevo que se sirva en `/api/interfaz` como `"marco": textos.MARCO` y se pase en `textos.marco`. **Si se
elige el bloque nuevo, hay que hacer las dos cosas** (añadirlo a `interfaz()` y pasarlo en `app.js`), o la
barra saldría sin esas cuatro palabras.

**Tres cosas que conviene saber antes de añadirlas:**

1. **Las revisa el test de jerga**: `test_interfaz.py` › «lo que sirve la api no lleva jerga» recorre
   **todo** lo que devuelve `/api/interfaz`, así que en cuanto se sirvan pasan por el filtro. Las cuatro
   propuestas no llevan ninguna palabra prohibida.
2. **No las caza `test_que_no_falte_ningun_texto.py`**, y se dice para que nadie se fíe de ese test aquí:
   busca llamadas `t("clave")` **dentro del JavaScript**, y estas palabras llegan por propiedades (el
   componente no las pide por su nombre). Es la misma situación que tienen hoy las palabras del menú.
3. **`MENU` tiene un comentario que decide lo contrario** y conviene releerlo
   (`textos.py`, líneas 3804-3809 de `MENU`): dice que en la barra **no** hay «Finca» a propósito, porque
   en este programa la finca se identifica por **el nombre del titular** y poner «Finca: David Pérez
   Velasco» sería decir una cosa que no es. Lo que cambia ahora no es ese criterio, es el dato: una cuenta
   puede entrar en **varias fincas** (ronda 89), y ahí la barra tiene que decir en cuál se está trabajando
   —apuntar en la finca que no es mete un dato falso en el cuaderno—. **La decisión que queda en el aire,
   y que es del coordinador y de David:** si el nombre que llega sigue siendo el del titular, el rótulo
   honesto no es «Finca» sino «Tu cuenta» (que ya está en la barra). Con dos fincas de la misma persona, el
   rótulo que hace falta es «Finca» con su nombre propio. Las claves se llaman `marco.finca` y
   `marco.sin_finca` para que cambiarlo sea cambiar el texto, y no el código.

---

## 8. Las claves del menú: qué hay y qué faltaba

**Dónde están de verdad.** En `marco.js` **no hay ninguna clave**: el armazón recibe la lista ya preparada
(`modulos`) desde `app.js`. Las claves del menú están en la tabla `MODULOS` de `app.js` (líneas 529-546), y
las palabras de la barra, en `textos.MENU` (línea 3799).

**Las 16 claves del menú, tal y como están hoy** (las que usa la navegación). Los nombres de la tercera
columna están comprobados contra lo que sirve `/api/interfaz` (el vocabulario de `textos.py`), no copiados
de un comentario:

| Clave | Nombre que se lee | De dónde sale el texto | Acción |
|---|---|---|---|
| `panel` | Panel | `menu.panel` | `ir-inicio` |
| `cuaderno` | Mi cuaderno | `cuaderno.titulo` | `inicio` + `data-ir="mi_cuaderno"` |
| `tierras` | Mis parcelas, productos y máquinas | `maestros.titulo` | `inicio` + `data-ir="mis_cosas"` |
| `cultivos` | Qué hay sembrado | `cultivos.titulo` | `cultivo-ver-todos` |
| `grupos` | Parcelas que se llevan igual | `grupos.titulo` | `inicio` + `data-ir="grupos"` |
| `almacen` | Lo que tengo en el almacén | `cesta.titulo` | `cesta-ver` |
| `analisis` | Los análisis | `analitica.titulo` | `inicio` + `data-ir="analisis"` |
| `plan` | El plan de abono del año | `plan.titulo` | `inicio` + `data-ir="planes"` |
| `ventas` | Lo que he vendido | `venta.titulo` | `inicio` + `data-ir="ventas"` |
| `medidas` | Lo que hago sin echar producto | `medidas.titulo` | `medidas-ver` |
| `papeles` | Los papeles | `documentos.titulo` | `papel-ver-todos` |
| `facturas` | Mis facturas | `facturas.titulo` | `facturas-abrir` |
| `anos` | Los años de mi cuaderno | `campanas.titulo` | `campanas-abrir` |
| `junta` | Traer mis tierras del cuaderno de la Junta | `cuaderno_cyl.titulo` | `cuaderno-de-la-junta-abrir` |
| `datos` | Mis datos | `mis_datos.titulo` | `mis-datos-abrir` |
| `ayuda` | Ayuda | `ayuda.pantalla.titulo` | `inicio` + `data-ir="ayuda"` |

**Las claves de `textos.MENU`** (12): `titulo`, `etiqueta`, `panel`, `cuenta`, `sin_cuenta`, `campana`,
`sin_campana`, `apuntar`, `letra`, `letra_etiqueta`, `salir`, `salir_etiqueta`.

**Qué faltaba, y qué he hecho con ello:**

1. **Ninguna de las 13 claves de módulo que nombra el ticket faltaba.** Están todas: `almacen`,
   `facturas`, `anos`, `grupos`, `cultivos`, `analisis`, `plan`, `ventas`, `medidas`, `papeles`, `junta`,
   `datos`, `ayuda` — y además `tierras`, `cuaderno` y `panel`, que son las tres que el ticket usa para el
   inicio, el listado de tierras y el cuaderno.
2. **`panel` es la clave del renglón «Panel», y la pantalla se llama `inicio`.** El ticket no nombra
   `panel` y sí `inicio` (`#/`); yo he mantenido las dos: la pantalla es `inicio` (`#/`) y la clave del
   menú sigue siendo `panel`, porque «Panel» es el nombre del renglón y no el de la pantalla. La tabla del
   módulo lo dice escrito.
3. **Faltaban dos pantallas, y son nuevas:** `tierra` (`#/tierras/<id>`) y `apunte` (`#/cuaderno/<id>`).
   No están en el menú porque no se llega a ellas desde un módulo, sino desde su lista. Son las dos únicas
   pantallas nuevas de la tabla.
4. **Las claves que el ticket pedía como «los demás módulos» están usadas tal cual**, sin traducir ni
   renombrar, para que un módulo y su dirección se llamen igual.

---

## 9. Lo que queda pendiente de T04

### 9.1 Lo que había que hacer para que esto se viera (el cableado) — **HECHO, y comprobado el 03/10/2026**

Las cuatro cosas de esta lista eran del coordinador (no de los ficheros de la primera entrega), y **las
cuatro están ya hechas**. Se dejan escritas, marcadas, porque son el contrato de lo que había que hacer y
porque **se ha vuelto a comprobar una por una** al empezar la segunda entrega:

| Lo que faltaba | Estado (medido el 03/10/2026) |
|---|---|
| `app.js`: leer la dirección al arrancar, escuchar el historial y escribir la dirección al navegar | **HECHO.** `abrirLaDireccion()` en el arranque y en `popstate`, `apuntarLaDireccion()` dentro de `montar()`. Y **comprobado en un navegador de verdad** (§10, punto 0) |
| `service-worker.js`: guardar `rutas.js` en la caché del campo | **HECHO.** `"/react/rutas.js"` está en `FICHEROS` (`service-worker.js:232`) y la caché va con la versión (`cuedigital-2026-10-02-61`). La prueba que estaba en rojo (`test_la_migracion_a_react.py` › `test_todo_el_javascript_de_react_se_guarda_para_el_campo`) **pasa** |
| `app.js`: las dos acciones del armazón (`cambiar-campana`, `cambiar-finca`) | **HECHO.** Las dos tienen su rama en el manejador de clics (`app.js:11634` y `11642`). La prueba que estaba en rojo (`test_los_botones_hacen_algo.py`) **pasa** |
| Las cuatro claves de texto del apartado 7.4, en `textos.py` | **HECHO.** Viven en `textos.MARCO` (`textos.py:4211`: `finca`, `sin_finca`, `cambiar_campana`, `cambiar_finca`) |
| Los tres documentos con el recuento de pruebas | **HECHO.** `README.md` (línea 1372), `AGENTS.md` (línea 51) y `docs/LO_QUE_PIDE_LA_JUNTA.md` (línea 22) dicen los tres **712** pruebas de JavaScript, y son las que hay (contadas en los ficheros: `test_lista_de_la_junta.py` lo comprueba y pasa) |

**Lo que sigue sin comprobar de esto, y se dice:** el *service worker* **sin cobertura** no se ha probado
(abrir la aplicación con la conexión quitada y recargar una ficha). Que el fichero esté en la caché está
probado por la prueba de Python; que la aplicación funcione desde la caché, no.

#### 9.1.1 Lo que tenía que hacer `app.js` (y hace)

1. **Al arrancar**: `leer(location.hash)` y montar la pantalla que diga `pantalla`; si `desconocida`, la
   pantalla de «esa dirección no lleva a ninguna parte» **sin cambiar la dirección** (para que el agricultor
   vea qué pasó).
2. **Al navegar**: `escribir(pantalla, parametros)` y la campaña, la finca y los filtros desde `parametros`
   **antes** de pedir los datos.
3. **`popstate`** (y no `hashchange`: escribir el fragmento a mano lo dispara, y volvería a abrir la misma
   pantalla en bucle): «atrás», «adelante» y recargar montan la pantalla que diga la dirección.
4. **La memoria de la vista** (`recuerda`/`recupera`): volver de una ficha deja la lista con lo que tenía.
5. **Los dos botones del armazón** (`cambiar-campana`, `cambiar-finca`) y el prop `contexto`.

#### 9.1.2 `service-worker.js`: `rutas.js` en la caché del campo — **HECHO**

Cada fichero de `web/react/` tiene que estar en la caché, porque un fichero que no está es un hueco en el
campo. `"/react/rutas.js"` está en `FICHEROS` y la caché lleva la versión, que es lo que hace que el móvil
del agricultor se entere de que hay algo nuevo.

#### 9.1.3 `app.js`: las dos acciones del armazón — **HECHO**

`cambiar-finca` (con `data-valor` = el id de la finca, que es lo que quiere `POST /api/fincas/cambiar`) y
`cambiar-campana` (que lleva a la pantalla de los años, que es donde de verdad se puede hacer algo con
ellos: el servidor no tiene forma de «trabajar en el año 2023»). Las dos tienen su rama en el manejador, y
la prueba que las reclamaba (`test_los_botones_hacen_algo.py` › `test_cada_accion_que_se_pinta_la_atiende_alguien`)
**pasa**.

#### 9.1.4 Las claves de texto y los tres documentos con el recuento — **HECHO, los dos**

- **Las cuatro claves del apartado 7.4 están en `textos.py`**: viven en `textos.MARCO`
  (`textos.py:4211`). **La segunda entrega no ha necesitado ninguna clave nueva**: no hizo falta ni una
  frase (lo que se decidió es dónde está cada pantalla, no qué dice).
- **Los tres documentos con el recuento**: `README.md` (1372), `AGENTS.md` (51) y
  `docs/LO_QUE_PIDE_LA_JUNTA.md` (22) dicen ya los tres **712** pruebas de JavaScript, y 712 es lo que hay
  (apartado 11.3). Cuando empezó esta entrega los tres decían 645 y había 693.

### 9.2 Lo que T04 todavía no tiene (y no se va a decir que sí)

**Lo que ha cambiado en la segunda entrega:** las 13 pantallas que no tenían dirección **ya están
decididas**, una por una, y las siete que la merecían **la tienen** (apartado 9.3). Lo que sigue sin viajar
en la dirección es lo de la tabla de filtros, aquí debajo.

**Los filtros que aún no viajan en la dirección** (las claves existen en el módulo, y en la segunda entrega
tampoco se han cableado: es un trabajo aparte, y se dice para que nadie lo dé por hecho):

| Lo que se filtra hoy | Dónde vive hoy | Qué le falta |
|---|---|---|
| El buscador de la lista de tierras | `estado.filtroTierrasMisCosas` | **Ya viaja** en `q` (primera entrega). |
| El buscador de tierras del asistente y de otras pantallas | `estado.filtroTierras` | Igual, con su pantalla: **sigue pendiente**. |
| El orden de las seis tablas | `estado.ordenDeLaTabla[clave] = {campo, sentido}` | **Ya viaja** en `orden` y `sentido` (primera entrega). |
| **«Solo las que no tienen el cultivo dicho»** | `estado.soloLasQueFaltan` | **No tiene parámetro todavía.** Propuesta: `faltan=1`. |
| La fila elegida del panel de al lado | `estado` (y el panel) | Propuesta: `elegida=<id>`, para que el panel se pueda enlazar. |
| La campaña y la finca | `estado.campana` / el vale | Va en `campana` y `finca`, que es lo que la barra con `contexto` ya escribe. |
| La página y «por página» | **No existen** (el diseño de Stitch los pide) | Cuando existan: `pagina` y `por_pagina`, y habrá que añadirlos a la lista de parámetros que son números del módulo. |
| **Dónde está mirando el mapa** (el zoom y el punto elegido) | `estado.mapa` | La dirección del mapa (`#/mapa`) reconstruye la pantalla, pero **no el zoom**: propuesta `lado` y `centro`, con el cuidado de no meter coordenadas en la barra de direcciones sin decidirlo antes. |

**El estado «copia local antigua» (y el «conflicto»).** El inventario (T01, §5.1) dice que faltan dos de
los estados obligatorios porque **ninguna tabla tiene versión ni `If-Match`**: gana el último `PUT`, en
silencio. **Esto no lo arregla una dirección, y por eso no se ha tocado aquí.** Lo que sí conviene decir,
porque es una trampa de esta misma tarea: una dirección reproducible puede dar **falsa tranquilidad** —el
agricultor abre «su» ficha por su enlace, ve datos, y no sabe que son de una copia vieja—. Cuando se
construya ese estado, la pantalla tiene que decirlo **en la pantalla**, no en la barra de direcciones: la
dirección identifica una ficha, no la versión del dato.

**Lo demás del diseño de T04 que todavía no está:** la miga de pan de la ficha, los contadores de la tabla
(«Mostrando 10 de 14 · Total: 64 · Seleccionadas: 1»), la franja de filtros con etiquetas que se pueden
quitar y el botón de quitarlos todos, la paginación, la búsqueda global de la cabecera, los contadores por
módulo en el menú, los cinco estados de pantalla dibujados, y **la ficha de tierra entera** (hoy solo tiene
dirección: la pantalla que la pinte es el siguiente trozo de T04).

---

### 9.3 La segunda entrega (03/10/2026): las 13 pantallas que faltaban, decididas una por una

**El encargo, con sus palabras:** *«decidir, una por una, si merece dirección propia o no, y escribirlo. Una
pantalla de paso (el asistente a medias, «lo he apuntado», el dictado) puede no tener dirección: una
dirección que se recarga y deja al agricultor en un formulario a medias no ayuda a nadie. Eso es una decisión
legítima; lo que no vale es dejarla sin decidir.»*

#### 9.3.1 La regla con la que se decide

> **Una pantalla tiene dirección si volver a su dirección la reconstruye entera.** O no depende de nada
> escrito a medias, o depende solo de un dato que **está en la dirección** (el identificador de una tierra,
> de un apunte o de una factura).
>
> **Una pantalla no la tiene si su contenido vive solo en la memoria de la sesión**: un formulario a medias,
> una propuesta que el servidor no guarda, o la confirmación de algo que se acaba de guardar. Y entonces
> **no escribe ninguna**: escribir una dirección que al recargar no lleva a lo mismo es mentir, y robarle la
> dirección a la pantalla de la que se salió deja al agricultor sin poder volver.

#### 9.3.2 La decisión, una por una

| # | Pantalla | Qué es | Decisión | Por qué |
|---|---|---|---|---|
| 1 | `asistente` | Apuntar algo (65 pasos) | **SIN dirección** | El formulario vive en memoria (`estado.asistente.borrador`): una dirección al paso 34 no se puede reproducir, y la que escribía antes (`#/cuaderno`, la de su módulo) le robaba la dirección a la pantalla de la que salió. No se le da una entrada `#/apuntar` porque una sola entrada no puede decir **qué** se va a apuntar (hay 65 formularios: tratamiento, abono, trabajo, venta, plan, análisis, parcela, año, producto…) y adivinar cuál sería inventarse media dirección. |
| 2 | `hecho` | «Lo he apuntado», después de guardar | **SIN dirección** | Muestra lo que se acaba de guardar, y esos datos están en memoria. No escribe ninguna: la barra se queda donde estaba el agricultor. |
| 3 | `entrar` | Entrar en la cuenta | **SIN dirección** | Un estado sin sesión no es una pantalla de la aplicación: la dirección pertenece a lo último que se estaba mirando, y al volver a entrar se sigue ahí. |
| 4 | `quien_entra` | Quién entra en mi finca | **CON dirección: `#/datos/quien-entra`** | Es un destino de «mis datos», no un paso: pide sus dos listas al servidor al abrirse, así que recargar la reconstruye entera. |
| 5 | `dictado` | Dímelo con la voz | **CON dirección: `#/dictado`** | Es una pantalla a la que se va (tiene su botón en la de inicio) y volver a ella no inventa nada: enseña la misma pantalla. Además es donde tiene que llevar un `#/borrador` sin borrador detrás. |
| 6 | `borrador` | La revisión de lo dictado | **CON dirección: `#/borrador`**, y sin nada dictado **lleva al dictado** | Es una pantalla a la que se vuelve (a mirar lo entendido). Pero el borrador vive en memoria y **el servidor no guarda nada** (`POST /api/borradores/desde-texto` devuelve una propuesta: `AGENTS.md` §3.8), así que abrir su dirección en frío **no inventa una revisión vacía**: lleva al paso donde nace, que es el dictado. |
| 7 | `mapa` | El mapa | **CON dirección: `#/mapa`** | `abrirElMapa()` lo abre de cero y lo centra solo (en la primera tierra o en la ubicación del móvil), así que recargar lo reconstruye. Lo que **no** viaja todavía es el zoom y el punto elegido (§9.2). |
| 8 | `decir_cultivo` | Decir qué hay sembrado en una tierra | **CON dirección: `#/tierras/<id>/cultivo`** | Es **de una tierra**: con la dirección de la lista de lo sembrado (`#/cultivos`, que es la que escribía antes), recargar obligaba a buscar otra vez cuál de las 51 tierras era. Es la forma que el contrato proponía (`#/tierras/12/cultivo`). |
| 9 | `traer_del_sigpac` | Traer una parcela del SIGPAC | **SIN dirección** | Es un paso del alta de una parcela (`pasosDeSigpac`), y lo que lleva escrito —el pueblo elegido, los trozos marcados— vive en el borrador del asistente. Nunca se monta sola, así que la cubre la decisión 1. |
| 10 | `nuevo_documento` | Guardar un papel (seis campos) | **SIN dirección** | Formulario a medias: recargar dejaría al agricultor con los campos vacíos **creyendo que ya lo había guardado** (o teniéndolo que reescribir entero). Antes escribía `#/papeles`, la dirección de su lista: no aportaba nada y se la robaba. |
| 11 | `nueva_factura` | Añadir una factura (elegir el fichero) | **SIN dirección** | Es el paso de elegir la foto o el PDF. Nada de lo que se escribe ahí se puede reproducir (un `<input type="file">` no se puede rellenar desde una dirección), así que no escribe ninguna. |
| 12 | `interpretacion_factura` | Revisar lo leído de una foto **y** corregir una factura guardada | **CON dirección solo cuando es una guardada: `#/facturas/<id>`** | La misma pantalla sirve para dos cosas. La guardada se reconstruye entera desde la lista de facturas, así que tiene dirección (y se puede mandar a quien te ayuda: «mira esta factura»). La lectura recién hecha **no está guardada en ningún sitio**, así que no la tiene y no la escribe: la dirección se queda en `#/facturas`, que es de donde se salió. |
| 13 | `firmar` | Firmar el cuaderno | **CON dirección: `#/cuaderno/firmar`** | Su estado lo trae `cargarDatos()` (`/api/firmas/estado`), que corre antes de abrir la dirección, así que recargar la reconstruye. Es de «mi cuaderno» y se vuelve a ella. |

**Resumen: 7 con dirección y 6 sin ella.** Y de las 6 sin dirección, **dos** (el alta de un papel y la de una
factura) **sí podrían tenerla** el día que guarden lo que se está escribiendo (`localStorage` o el servidor):
hoy no lo hacen, y por eso no la tienen. Queda escrito aquí para que nadie crea que es un olvido.

#### 9.3.3 Lo que se ha implementado

1. **`web/react/rutas.js`**: siete pantallas nuevas en `PANTALLAS`, agrupadas por familia y con el tramo fijo
   antes que el identificador. Y el porqué de las seis que **no** están, escrito en el propio módulo.
2. **`app.js` → `PANTALLAS_SIN_DIRECCION`**: los pasos **no escriben ninguna dirección**. Es el arreglo de un
   fallo de verdad de la primera entrega: antes, cualquier pantalla que estuviera en `MODULO_DE_LA_PANTALLA`
   escribía la dirección de su módulo, así que abrir el asistente en una tierra dejaba la barra en
   `#/cuaderno`. Se conserva `MODULO_DE_LA_PANTALLA` para lo que sí es suyo —**marcar el renglón del menú**—
   y se decide aparte **qué escribe la dirección**: son dos preguntas distintas y tenerlas en la misma tabla
   era justo el fallo.
3. **`app.js` → `DIRECCION_PROPIA`**: la dirección de las siete pantallas que no coinciden con su módulo
   (`PantallaMapa` → `mapa`, `PantallaDecirCultivo` → `decir_cultivo`, `PantallaQuienEntra` → `quien_entra`,
   `PantallaFirmar` → `firmar`, `PantallaDictado` → `dictado`, `PantallaBorrador` → `borrador`,
   `PantallaInterpretacionDeLaFactura` → `interpretacion_factura`).
4. **`abrirLaPantalla`**: `decir_cultivo`, `interpretacion_factura` y las cinco nuevas de
   `ABRIR_LA_PANTALLA` (`mapa`, `dictado`, `borrador`, `quien_entra`, `firmar`). Las dos primeras comprueban
   que la ficha existe **antes** de abrirla, con los mismos tres finales que la ficha de una tierra: se abre,
   «esa dirección no lleva a ninguna parte», o «no lo he podido comprobar» sin cobertura.
5. **`MODULO_DE_LA_PANTALLA`**: cuatro renglones que faltaban (el mapa, la firma, el dictado y su revisión).
   Sin ellos el menú se quedaba **sin ningún módulo marcado** al abrirlas, y no saber dónde estás es la mitad
   de para qué sirve un menú.
6. **`abrirElDictado()` y `abrirElBorrador()`**: la dirección del dictado no borra el texto que el agricultor
   ya había contado (volver con «atrás» desde el borrador no puede perder su trabajo; quien empieza un
   dictado nuevo es el botón, que sí lo vacía), y `#/borrador` sin nada dictado lleva al dictado en vez de
   enseñar una revisión de nada.

**Ni un fichero más, y ninguno de los que son del coordinador.** Lo que la primera entrega dejó pendiente
—las cuatro claves de texto en `textos.py`, `rutas.js` en la caché del `service-worker.js`, las dos acciones
del armazón y el recuento de los tres documentos— **está todo hecho** desde entonces (apartado 9.1, con la
comprobación de cada uno).

---

### 9.4 La segunda entrega: lo que se rompe si esto se deshace

Se dice aquí, y no solo en las pruebas, porque son las dos cosas que un cambio posterior puede volver a
romper sin darse cuenta:

1. **Volver a poner el asistente (o el alta de un papel, o la de una factura) en la tabla que escribe la
   dirección** haría que el agricultor recargara en mitad de un apunte y apareciera en el cuaderno, o peor:
   con el formulario en blanco creyendo que ya había guardado. Hay dos pruebas que lo cazan
   (`interfaz.test.js`: «los pasos de un formulario no le roban la dirección a la pantalla anterior» y
   «recargar en mitad de un apunte no inventa una ficha a medias»), y **se comprobó que las dos fallan**
   desactivando el arreglo (medido, no supuesto): con el arreglo quitado, el asistente deja la barra en otro
   sitio.
2. **Añadir una pantalla de paso a `PANTALLAS`** (la tabla del módulo) para «que tenga dirección» rompería el
   contrato de §5.2: una dirección que al recargar no lleva a lo mismo. Hay una prueba que se pone roja si
   alguna de las seis aparece ahí, con el motivo escrito al lado.

---

## 10. Lo que NO he podido comprobar

Se dice con el mismo detalle que lo demás, porque un documento que da por bueno lo que no ha probado no
sirve para integrar nada.

> **Lo que ha cambiado en la segunda entrega.** Los puntos 1 y 2 de esta lista **ya no valen tal y como
> están escritos** (el navegador sí se ha abierto: ver el punto 0, aquí debajo), y los puntos que siguen
> valiendo se quedan como estaban, porque son de la primera entrega y siguen sin comprobarse.

0. **Lo que SÍ se ha comprobado en un navegador de verdad en la segunda entrega** (03/10/2026), y se dice
   con el detalle de cómo, porque es la mitad del valor de esta entrega:
   - `backend/scripts/comprobar_en_un_navegador.py` **entero y en verde** contra un servidor de prueba
     (puerto **8018**, base y adjuntos temporales; **nunca el 8000, que es el del agricultor**): las 33
     pantallas y rutas que recorre se dibujan, ninguna deja el aviso de emergencia de React, y no queda
     ningún fichero de la comprobación dentro de la aplicación. Es la comprobación de que **nada de lo que
     funcionaba se ha roto**.
   - **Las direcciones nuevas, abiertas de verdad** (una comprobación temporal, fuera del repositorio, con
     Chrome sin ventana y una página servida por el propio programa para tener la sesión puesta): `#/mapa`,
     `#/tierras/<id>/cultivo`, `#/datos/quien-entra`, `#/cuaderno/firmar`, `#/facturas/<id>`, `#/dictado`,
     `#/borrador` (sin nada dictado → el dictado) y las dos que no llevan a nada (`#/facturas/999999` y
     `#/lo-que-sea`) **abren la pantalla que dicen** y dejan escrita la dirección canónica. **Resultado:
     todo correcto** (11 casos, 13 comprobaciones).
   - **Y lo que faltaba de la primera entrega**: pulsar de verdad un botón (`cultivo-decir` en la lista de
     lo sembrado) lleva a `#/tierras/<id>/cultivo`; y **un paso de un formulario no le roba la dirección a
     la pantalla de la que salió** (el asistente abierto desde una tierra deja la barra en la tierra, y
     abierto desde el inicio la deja en `#/`, no en `#/cuaderno`). El caso del inicio es el que distingue de
     verdad: antes del arreglo, la barra acababa en `#/cuaderno`.
   - **No se ha medido en el navegador «antes del arreglo»**: lo que se midió así fue en las pruebas de
     JavaScript (las dos que fallan con el arreglo desactivado, §9.4). En el navegador solo se ha medido
     **después**.
   - **No se ha probado sin cobertura**: `rutas.js` **ya está** en la caché del `service worker` (§9.1.2),
     pero nadie ha abierto la aplicación con la conexión quitada y ha recargado una ficha. Y **no se ha
     probado en un móvil de verdad**: el navegador es Chrome sin ventana, en el ordenador de desarrollo.
1. **La aceptación de T04 en un navegador de verdad ya está hecha** (punto 0, y en la ronda 3 el
   coordinador la comprobó a 390, 1024 y 1440 px). Lo que **no** he hecho yo es mirarlo **a ojo**: las
   capturas las guarda la herramienta y no las he abierto para juzgar el aspecto de las pantallas nuevas
   (el mapa, la firma, la revisión de una factura). Lo que se ha comprobado es **que se dibujan y qué
   dicen**, no cómo se ven.
2. **El armazón con `contexto` está comprobado por lo que *dice*, no por lo que *se ve*.** Las pruebas
   miran el HTML (`renderToStaticMarkup`): que estén los rótulos, los botones, sus `data-*` y el elegido.
   **No sé cómo queda de aspecto** en la barra verde (los botones reutilizan `.boton-letra` y
   `.boton-elegido`, y el elegido pinta el fondo del mismo verde que la barra: se distingue por el
   contorno amarillo de 4 px y por `aria-current`, pero eso no lo he visto en una pantalla).
3. **La forma de `contexto` está sacada de los esquemas, no de una respuesta de verdad con varias fincas.**
   `fincas` viene de `GET /api/fincas` (`FincaSalida`, en `schemas.py:1136`: `id`, `nombre`, `municipio`,
   `papel`, `activa`, `hectareas`) y `campanas` de `CampanaSalida` (`schemas.py:89`: `id`, `anio`,
   `fecha_inicio`, `fecha_fin`, `cerrada`). **No he llamado a `/api/fincas`** en la segunda entrega (lo que
   sí ha hecho la comprobación del navegador es abrir `#/datos/quien-entra` con una cuenta de verdad, y esa
   pantalla sí pide `/api/fincas` y `/api/fincas/quien-entra`).
4. **Sin cobertura no está probado**, y es justo el motivo del `#`. Lo que **sí** está probado es que
   `rutas.js` está en la caché del *service worker* (§9.1.2, y hay una prueba de Python que lo exige), y el
   **tercer final**: con el navegador sin conexión (`navigator.onLine` en falso), una dirección de una ficha
   que no está descargada dice **«no lo he podido comprobar»** y ofrece volver a intentarlo, en vez de decir
   que no existe (hay prueba de las tres ramas: la tierra y —nuevas en esta entrega— decir el cultivo y la
   revisión de una factura).
5. **No he comprobado que el servidor sirva `rutas.js` con el tipo correcto** (`text/javascript`). Se
   sirve como todo lo de `web/react/` (y hay una prueba que lo comprueba para las pantallas), pero para
   este fichero concreto no lo he mirado. Lo que sí se ha visto es que el navegador carga `app.js` —que
   importa `rutas.js`— y la aplicación arranca: si el tipo estuviera mal, no arrancaría.
6. **La suite de Python, medida en la segunda entrega** (el día 03/10/2026, con **otro subagente
   trabajando en `backend/app/` a la vez**, así que los números pueden moverse): ver el apartado 11.4, con
   los fallos separados entre «de este cambio» y «ya estaban».
7. **Las pruebas de Python que vigilan `marco.js`** (`test_el_armazon_del_ordenador.py`) pasan, pero **su
   comprobación de «ninguna frase escrita a mano» es débil** por diseño: solo mira que no haya texto suelto
   entre etiquetas. La comprobación de verdad es la de JavaScript (la primera entrega la añadió para el
   armazón con contexto, porque `react.test.js` no se podía tocar).

---

### 10.1 Lo que la segunda entrega NO ha tocado, y por qué

- **`textos.py`**: no ha hecho falta ni una frase nueva. Lo que se ha decidido es **dónde está cada
  pantalla**, y las que se quedan sin dirección reutilizan los avisos que ya existían (`direccion.titulo`,
  `direccion.explica`, `direccion.sin_cobertura_titulo`, `direccion.reintentar`).
- **`service-worker.js`**, **`index.html`**, **`estilos.css`**: son del coordinador y esta entrega no añade
  ni una pantalla nueva (no hay ningún componente nuevo) ni una regla de estilo.
- **`frontend`/compilación/dependencias**: nada. `rutas.js` sigue siendo un módulo puro sin `fetch` ni
  `localStorage` (hay una prueba que lo lee y lo comprueba, y sigue en verde).

---

## 11. Las pruebas

### 11.1 `backend/tests_js/rutas.test.js`

**45 pruebas, 45 en verde** (38 de la primera entrega y **7 nuevas** de la segunda). Cubren, una por una, lo
que el ticket pedía y lo que el contrato necesita:

| Qué se prueba | Qué se rompe si falla |
|---|---|
| La pantalla de inicio desde `""`, `"#"`, `"#/"` y `"/"` | Al recargar, el agricultor vería un aviso en vez de su pantalla |
| La ficha de una tierra con `id`, `campana` y `finca`, y que el `id` sea **número** | La ficha que se pide por la dirección no sería la que se enseña |
| Una dirección desconocida (`#/lo-que-sea`) | Un aviso técnico donde debería estar el inicio |
| Un `id` que no es número (`#/tierras/abc`, `1.5`, `-3`, `12a`, `0x12`) | Se abriría la ficha de ninguna tierra sin decir nada |
| **Ida y vuelta en las 25 pantallas de la tabla** | Esa pantalla no se podría recargar ni enlazar |
| Acentos, espacios, `&`, `=` y `#` en un valor | Buscar «Peñaranda de Bracamonte» daría una lista vacía |
| Los parámetros vacíos no se escriben y el orden es estable | El historial se llenaría de direcciones duplicadas |
| El repetido gana el primero, y `?Campana=` se lee como `campana` | Dos reglas distintas para lo mismo |
| Lo que no conocemos no se tira | Se perdería un filtro en silencio |
| `recuerda`/`recupera`/`olvida`: guarda, devuelve, olvida, y no toca la memoria que se le pasa | Al volver del detalle se perderían los filtros (o dos listas se pisarían) |
| El recorrido de T04: lista → ficha → vuelta con los filtros | La aceptación, entera |
| **`rutas.js` no usa `window`, `document`, `history`, `location`, `fetch`…** | El módulo no se podría probar sin navegador y podría dejar la pantalla en blanco |
| **`#/tierras/<id>/cultivo`**: su identificador es número, aguanta mayúsculas y barra de más, y sin identificador no hay dirección | Volver de la ficha de una tierra llevaría a la lista de lo sembrado, sin decir cuál era |
| **`#/tierras/<id>/cultivo` con tramos de más** (o una palabra que no es «cultivo») es una dirección desconocida | Se abriría la ficha de ninguna tierra sin avisar |
| **`#/facturas/<id>`** es la revisión de esa factura, y `#/facturas` sigue siendo la lista | Recargar la revisión de una factura devolvería a la lista |
| **`#/datos/quien-entra`** y **`#/cuaderno/firmar`** no se confunden con `datos` ni con un apunte | Se abriría el apunte número «firmar» (o al revés) |
| **`#/mapa`, `#/dictado` y `#/borrador`** tienen su dirección y ninguna otra pantalla la toma | El mapa devolvería a la lista de tierras al recargar |
| **Los seis pasos de un formulario no están en la tabla, y no se les puede añadir sin que salte** | Una dirección que al recargar deja al agricultor en un formulario vacío (o a medias) |
| El quitador de comentarios de esa prueba, probado consigo mismo | Una prueba que se cree un comentario, o que se come el fichero |
| El armazón: **sin** `contexto` no cambia nada, y **con** `contexto` salen la finca y sus botones | La barra de siempre, y los botones que el ticket pide |
| El elegido se marca con clase y con `aria-current`; una finca a medias no se pinta; los años llegan de las dos formas; y ninguna frase está escrita en el armazón | Un botón que no dice a dónde va, y una frase fuera de `textos.py` |

### 11.2 La suite entera de JavaScript

`cd F:\EspacioCodigo\CueDigital\backend; node --test "tests_js/*.test.js"`

```
ℹ tests 712
ℹ pass 712
ℹ fail 0
ℹ skipped 0
```

**Leído de la salida de verdad**, el 03/10/2026, después de la segunda entrega: **712 pruebas, 712 en
verde**. Antes de esta entrega eran **693** (§10.4 del seguimiento), así que las **19 nuevas** son de este
encargo (7 en `rutas.test.js` y 12 en `interfaz.test.js`) y **ninguna de las que había se ha tocado ni se
ha borrado**. Los dos ficheros sueltos:

| Fichero | Antes | Ahora | Qué se ha añadido |
|---|---|---|---|
| `node --test "tests_js/rutas.test.js"` | 38 | **45** | La dirección de cada una de las siete pantallas nuevas, sus casos raros (identificador que no es número, tramos de más, parámetros vacíos, acentos, mayúsculas, barra final) y **la decisión** de que los seis pasos no tengan dirección. |
| `node --test "tests_js/interfaz.test.js"` | 266 | **278** | Pulsar el botón de verdad y acabar en la pantalla correcta **con la dirección que toca** (decir el cultivo, el mapa, firmar, quién entra, la revisión de una factura, el dictado y su revisión); recargar cada una; las dos que no llevan a nada; y **que un paso no le robe la dirección a la pantalla anterior**, incluido «recargar en mitad de un apunte no inventa una ficha a medias». |

**Y dos de esas pruebas se midieron con el arreglo desactivado** (poniendo el paso que escribe la dirección
en el sitio de antes): «los pasos de un formulario no le roban la dirección a la pantalla anterior» y
«recargar en mitad de un apunte no inventa una ficha a medias» **fallan las dos** con el arreglo quitado y
**pasan las dos** con él. No es una suposición: es la comprobación de que las pruebas miran lo que dicen
mirar.

### 11.3 El recuento, en los tres documentos — **ya está**

`README.md` (línea 1372), `AGENTS.md` (línea 51) y `docs/LO_QUE_PIDE_LA_JUNTA.md` (línea 22) dicen ya los
tres **712** pruebas de JavaScript, y **712 es lo que hay**, contado en los ficheros de `tests_js/`
(`interfaz.test.js` 278 + `react.test.js` 330 + `nucleo.test.js` 59 + `rutas.test.js` 45). Lo comprueba
`test_lista_de_la_junta.py` › `test_los_numeros_de_test_de_la_documentacion_no_se_quedan_viejos`, que
**pasa**. (Cuando empezó esta segunda entrega los tres decían 645 y había 693: la diferencia era del
recuento atrasado de las rondas anteriores, y la ha cerrado el coordinador.)

### 11.4 La suite de Python, medida (con el aviso de que había otro subagente trabajando a la vez)

`cd F:\EspacioCodigo\CueDigital\backend; ../.venv/Scripts/python.exe -m pytest -q`

```
tests=3198  failures=0  errors=0  skipped=1   (216,7 s)
```

Es el recuento **de verdad**, leído del informe XML de `pytest` (`--junitxml`) porque la línea final del
resumen no llegaba a la consola de este Windows. **Ningún fichero de Python se ha tocado en esta entrega**,
así que ningún fallo de la suite puede venir de aquí: lo que esta entrega cambia es JavaScript (`app.js`,
`rutas.js`), sus pruebas y este documento.

**Y el aviso que hay que dar, porque los números se movieron durante el trabajo:** mientras se hacía esta
entrega, **otro subagente estaba tocando `backend/app/` a la vez** (tablas nuevas: recepciones, movimientos
de existencias, artículos). En las mediciones intermedias la suite llegó a tener **6 y 7 fallos**, todos en
ficheros suyos y todos por lo mismo (`correcciones.tablas_que_apuntan_a`: la cuenta de tablas que apuntan a
una columna, con las tablas nuevas sin clasificar). **En la medición final están todos en verde**, así que
los cerró él. Se dice aquí para que nadie lea un "0 fallos" de esta tabla como si la suite hubiera estado
tranquila todo el rato.

| Qué | Resultado |
|---|---|
| Los ficheros que vigilan **este** cambio (`test_interfaz.py`, `test_la_migracion_a_react.py`, `test_los_botones_hacen_algo.py`, `test_el_armazon_del_ordenador.py`, `test_ficheros_de_texto.py`, `test_lista_de_la_junta.py`) | **920 en verde, 0 en rojo** (medido aparte, con los seis ficheros juntos) |
| La suite entera | **3198 casos, 0 fallos, 1 omitida** |
| Lo que estos números significan para esta entrega | Que las direcciones nuevas no rompen **ninguna** de las comprobaciones que ya existían: las de Python leen `app.js` y `rutas.js` (jerga, acciones que se pintan y no se atienden, la caché del *service worker*, los textos de la interfaz) |
