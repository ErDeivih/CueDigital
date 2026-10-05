# Mejorar la interfaz con Stitch (y qué se puede hacer desde aquí)

Diego lo pidió así: *«usa stitch para mejorar la ui en base a lo que nos dé
<https://stitch.withgoogle.com/docs/skills/get-started/>»*. Este documento cuenta **qué es Stitch**,
**qué se puede hacer desde este proyecto** y **qué no**, y deja escritos los textos para pedírselo.

## 1. Qué es Stitch

[Stitch](https://stitch.withgoogle.com) es la herramienta de diseño con IA de Google: se le describe
una pantalla con palabras y devuelve un diseño (y código). Desde enero de 2026 tiene además un
**servidor MCP remoto** y unas *skills* para agentes que convierten un diseño en componentes
([gihyo.jp](https://gihyo.jp/article/2026/01/google-stitch-mcp),
[codelab de Google](https://codelabs.developers.google.com/design-to-code-with-antigravity-stitch)).
Para usarlo hace falta **cuenta de Google y clave de API** de Stitch.

## 2. Qué se puede hacer desde aquí, y qué no

**Ya se puede llamar a Stitch desde aquí** (desde la ronda 76), y se ha hecho: está
`backend/scripts/disenar_con_stitch.py`, que habla con el servidor MCP de Stitch
(`https://stitch.googleapis.com/mcp`) con la cabecera **`X-Goog-Api-Key`**. La clave **no está en el
repositorio**: se pasa por la variable `STITCH_API_KEY` (o por un fichero temporal fuera del proyecto,
para una sesión de agente). Es la misma regla que con la clave del certificado.

Lo que **sí** hay que tener en cuenta:

1. **Stitch devuelve diseños pensados para React y Tailwind.** Este programa es **HTML, CSS y
   JavaScript a pelo, sin compilar** (decisión del proyecto, ver `AGENTS.md`), con los textos en
   `textos.py` y los colores solo en `:root` de `estilos.css`. Un diseño de Stitch **no se puede
   pegar** tal cual: se implementa a mano respetando esas reglas.
2. **Los textos del diseño no son los nuestros.** Stitch reescribe las frases («Bichos, hierbas u hongos
   tratados» donde nosotros decimos «bichos, hierbas, hongos»): lo que se toma es **la disposición, la
   jerarquía y los dibujos**, y los textos los siguen poniendo `textos.py`.

**Y lo que no se puede hacer todavía: nada de esto se comprueba en un navegador con el diseño puesto.**
Lo que hay se comprueba con las pruebas de interfaz y con la captura del navegador de verdad
(`scripts/comprobar_en_un_navegador.py`), que es lo que impide que un botón baje de 64 px o que la letra
baje de 18 px.

> **El límite que no se cruza:** la interfaz tiene que seguir funcionando **sin compilar** y **sin
> cobertura**. Si un diseño de Stitch exige React, una fuente de internet o un icono que se descarga,
> no vale: se coge la idea y se hace con lo que ya hay.

## 3. El encargo, listo para pegar en Stitch

### Contexto (va primero, tal cual)

> Aplicación web para agricultores de Castilla y León (España), **sin compilar** (HTML, CSS y
> JavaScript a pelo) y pensada para **móvil**, usada sobre todo **en el campo, con una mano y con
> sol**. Los usuarios **no saben de informática**: hay que poder usarla sin explicaciones.
>
> Reglas que no se pueden romper:
> - Texto base **de 18 px o más**; botones **de 64 px de alto o más**; nada de menús escondidos.
> - **Nada de jerga**: no se dice «interfaz», «validación», «fitosanitario», «UGC/DGC», «error». Se
>   dice «¿Qué has hecho hoy?», «echar producto», «lo que tengo en el almacén».
> - **Una pregunta por pantalla**, con un botón grande para seguir y otro para dejarlo en blanco.
> - Un solo color de acción y un fondo claro; los estados con aviso **avisan, no bloquean**.
> - **Todo lo que se pide se explica**: al lado de cada campo, una frase con qué es y por qué.

### Pantallas que interesa rediseñar (por orden de uso)

1. **Inicio** («¿Qué has hecho hoy?»): seis botones, el de «echar producto» el más grande, cada uno
   con su icono y su pista de una línea.
2. **Echar producto** (el asistente de 5 pantallas: parcela, producto y dosis, motivo, quién y con
   qué, resumen). Es el que más se usa.
3. **Mis parcelas**, con el dibujo de la tierra y, en cada una, lo que tiene sembrado y si le falta
   algo.
4. **Mi cuaderno**, con lo apuntado, lo que falta por completar y el botón de sacar el cuaderno de la
   Junta.
5. **Lo que tengo en el almacén** (comprado, echado y lo que queda) y **Mis facturas** (hacer una foto
   a la factura y confirmar lo que el programa ha leído).

### El texto exacto de cada pantalla

Está en `backend/app/textos.py` y se sirve por `/api/interfaz`: es la lista de todo lo que lee el
agricultor, y sirve tal cual como contenido para el diseño (no hay que inventarse los textos, y de
hecho **no se pueden cambiar sin tocar ese fichero**).

---

## El rediseño, en una página (rondas 76 a 92)

David pidió **rehacer la interfaz entera** con Stitch: «la aplicación es terrible de usar, es difícil hacer una
app tan mala estéticamente y de usabilidad». Se creó el proyecto en Stitch, se le subió **nuestro `DESIGN.md`**
como sistema de diseño y se le pidieron **cuatro pantallas** (`inicio`, `asistente`, `mi_cuaderno`,
`mis_tierras`), que están en `docs/stitch/rediseno/` con sus capturas y su explicación. A partir de ahí, el
rediseño se ha hecho **por rondas**, cada una con sus pruebas y con la pantalla mirada en un navegador de
verdad.

**Y en la ronda 90 David cambió el alcance**: *«usa mucho más Stitch, para cualquier diseño, para cualquier
mínima cosa, hazle caso en las ideas, no pares hasta tener toda la app cubierta con todas las funcionalidades
y ui refactorizadas y perfectas»*. Hasta entonces, de las 28 pantallas solo cuatro tenían diseño propio. Desde
la ronda 90 **se le pide a Stitch un diseño para cada pantalla y para cada pieza**, y la lista de lo que queda
—que es la que manda— vive en [`docs/stitch/LO_QUE_FALTA_POR_DISENAR.md`](stitch/LO_QUE_FALTA_POR_DISENAR.md).
Esto es todo lo que cambió:

| Ronda | Qué se hizo |
|---|---|
| 76 | **El lenguaje de los botones y los iconos**: el botón normal es una tarjeta blanca con borde grueso y el verde sólido se reserva para la acción principal; los emoji se cambian por **dibujos de línea en SVG** con el cuadro del icono |
| 77 | **La tarjeta de una tierra** (la forma del SIGPAC, la superficie, el pueblo, los avisos dentro y la palabra «ELEGIDA»), la **barra de pasos** con «Paso 1 de 13» y **la barra de botones pegada abajo** en el asistente |
| 78 | **Las tierras de «mis cosas» como tarjetas**, con el rótulo «Tierra n.º 12», los datos con su nombre delante y **lo que le falta a cada tierra con el botón que lo arregla dentro**; y la cuenta «Tienes 51 tierras apuntadas» |
| 79 | **Los apuntes de «mi cuaderno» como fichas**, cada dato con su nombre —incluida **la tierra donde se echó**, que no salía—; `APUNTAR OTRO TRATAMIENTO` en el bloque; y la pieza pasa a llamarse **`tarjeta.js`** porque sirve para tres cosas |
| 80 | **El bloque verde de la inspección** (el único bloque oscuro de la aplicación) y **la frase de un vistazo** («Te falta 1 cosa por apuntar»), que solo se dice si el servidor ha contestado |
| 81 | **El número de cada bloque con su palabra**: «2 ventas apuntadas · 44.000 kg», «1 análisis guardado» |
| 82 | **El buscador de tierras** en el paso donde se elige: por nombre, pueblo o número del SIGPAC, sin tildes y con «VERLAS TODAS» siempre a mano |
| 83 | **La ayuda, cada cosa con su nombre**: los seis puntos de la ley y los diez porqués dejan de ser dos muros y pasan a ser cosas con título |
| 84 | **Los números en singular**: «A 1 parcela le falta decir qué tiene este año», «Tienes 1 producto apuntado» (que además **no lo enseñaba nadie**), «1 apunte esperando a que haya cobertura» |
| 85 | **Los números del plan de abono** (la cabecera nombra las tres columnas y el «Pasado» sustituye a un ⚠️ suelto) y **la flecha solo donde lleva a algún sitio** |
| 86 | **Las ventas, cada dato con su nombre** (`Cuánto`, `A quién`, `Partida`, `Albarán`…): seis datos seguidos y sin rótulo pasan a ser una ficha |
| 87 | **El buscador también en «mis cosas»**, con su propio filtro (para que buscar en un sitio no esconda tierras en el otro) |
| 88 | **La pantalla del SIGPAC sin lo que sobra**: sin barra de progreso ni «Paso 1 de 1» en un asistente de un paso, y la explicación de la referencia una vez y no dos |
| 89 | **Varias cuentas en la misma finca** («Quién entra en mi finca»), que es de lo que va [`QUIEN_ENTRA_EN_LA_FINCA.md`](QUIEN_ENTRA_EN_LA_FINCA.md): no es un diseño de Stitch, pero es interfaz nueva y sigue las mismas reglas |
| 90 | **Stitch para todo, pantalla por pantalla**: se escriben **veintinueve encargos** (las 28 pantallas + una lámina de piezas), se piden **los 29** y se aplican todos: el almacén (la etiqueta de estado de cada producto, «Te queda» destacado, el motivo en su franja), los análisis (la edad del boletín, los números en su bloque, el papel con lo que hay que hacer al lado), la ayuda («Sí es obligatorio» / «Es voluntario»), qué hay sembrado (la etiqueta por tierra), la revisión de lo dictado (lo que has dicho, entero), traer las tierras de la Junta (la barra de las tres fases), los papeles (guardar arriba y el papel en su franja), decir qué hay sembrado (los campos numerados), la confirmación de apuntado (la ficha de lo que se acaba de apuntar, el plazo de espera en su franja y los botones en su orden), mis datos (los campos numerados), las medidas («Hecho en mi finca» con palabras), las facturas (el papel de cada una, con verlo o subirlo, y su cuenta), el plan de abono (el veredicto «En regla» / «Alerta: exceso»), quién entra en mi finca (las hectáreas de cada finca y qué puede hacer quien ayuda), las ventas (la fecha en su renglón y la cuenta), los grupos (las tierras una por línea con sus hectáreas), guardar un papel (las carpetas para tocar y el papel se sube en la misma pantalla), firmar (el estado de la firma), añadir factura (la caja del fichero y el trato claro), la interpretación de una factura (la etiqueta «Revisar números»), el mapa (la confirmación con el recordatorio), traer del SIGPAC (el camino rápido primero) y entrar (revisada, sin cambios). La lista viva de qué se aplicó, pantalla por pantalla, está en [`docs/stitch/LO_QUE_FALTA_POR_DISENAR.md`](stitch/LO_QUE_FALTA_POR_DISENAR.md), y el detalle en [`docs/stitch/rediseno/LEEME.md`](stitch/rediseno/LEEME.md) |
| 91 | **Diseño de los dos estados nuevos de «corregir y borrar»** (David: *«deja borrar las cosas que introduzca porque puede que me equivoque, o modificar también»*): se piden dos láminas —`corregir_un_apunte` y `borrar_un_apunte`— y de ellas se aplica a los apuntes del cuaderno: **la caja de lo que va a desaparecer con su rótulo**, **la etiqueta «CORRIGIENDO LO APUNTADO» en cada paso** del asistente (el título se lee una vez; la barra de progreso se mira siempre), **«VOLVER SIN GUARDAR»** y la explicación de **qué significa anular** un apunte firmado. Lo que el diseño pedía y no se ha aplicado —y por qué— está en [`docs/CORREGIR_Y_BORRAR.md`](CORREGIR_Y_BORRAR.md#lo-que-dijo-stitch-y-lo-que-se-ha-hecho-con-ello), con un caso que se rechaza de plano: **«tu firma sigue siendo válida»** después de corregir, que es lo contrario de lo que dice este programa |
| 92 | **Lo mismo, para las tierras y los grupos**, con los mismos dos botones y la misma pantalla de borrar (cambia lo que enseña, no cómo se pregunta). El diseño ya estaba pedido en la 91 y es el mismo: un estado nuevo no necesita lámina nueva. Lo que sí trajo la ronda es que **«cuál es la forma de una tierra» se protege al corregirla** —está en la entrada de la API pero no en la salida, así que el formulario no puede mandarla de vuelta y se quedaba sin dibujo— y que una tierra **con apuntes no se deja borrar** |
| 93 | **Los dos estados, en todas las listas**: las fichas de lo que se usa (producto, abono, quién aplica, asesor, máquina, nave), los análisis, lo que se vende y el plan de abono. No hay diseño nuevo que aplicar —la ficha, los dos botones y la pregunta de borrar son los mismos— y lo que se hizo es lo que el diseño pide: **una pieza** para los dos botones (`react/piezas/acciones_de_una_ficha.js`) y un **registro** (`OTRAS_COSAS`) para que añadir la siguiente lista sean cuatro líneas. De paso se arreglaron dos fallos que salieron al hacerlo: el botón de volver que llevaba a la pantalla de inicio (el destino no estaba en `irAInicio`) y **corregir un análisis, que le borraba los nueve números del boletín** |
| 93 (segunda parte) | **Los papeles y las facturas**, las dos últimas fichas que faltaban por tener sus dos botones: el papel se corrige en la misma pantalla con la que se guarda y la factura, en la que confirma lo que se lee. **Tampoco hay lámina nueva que pedir, y esto es una decisión, no una dejada**: los dos son la misma pantalla de siempre con los datos de dentro, y **el diseño de corregir ya está pedido** (la 91: los dos botones, la caja de lo que va a desaparecer, «CORRIGIENDO» y el volver sin guardar). Pedir a Stitch una lámina de «corregir una factura» sería pedir el mismo dibujo otra vez. Lo que sí se aplicó de aquel diseño: el **«VOLVER A MIS FACTURAS»** explícito (un botón que dice adónde va) y **el aviso de lo que no se pregunta y viaja igual** (las notas, el lote y el número de registro de cada línea), que es la lección de la ronda 92 aplicada antes de que hiciera daño |
| 93 (tercera parte) | **Los años del cuaderno**, que era lo único que quedaba sin poder tocarse y lo que más pesa (de la campaña cuelga el año entero). Es **una pantalla nueva**, así que sí se le pidió su diseño a Stitch (`campanas`, encargo número 32) y de la lámina se aplicó lo que se ve: el rótulo **«Año del cuaderno»** encima del año, **el año en grande con su etiqueta de estado al lado** («Estás apuntando en este», en ámbar, porque es lo que se viene a mirar; «Año cerrado» en los demás), las dos fechas en su renglón con su nombre delante, **cuánto hay dentro de cada año** («Tiene 42 apuntes dentro», con el número que cuenta el servidor) y —la idea que más vale de la lámina— **el BORRAR apagado, con la frase que lo explica justo al lado** cuando el año tiene cosas dentro. Lo único que no se copió es el marco decorativo de la ficha del año que se está llevando: aquí el año se distingue por su etiqueta, y el color no informa solo (regla de la casa) |

**Lo que el diseño pedía y NO se ha aplicado, con el motivo:**

1. **La barra de pestañas de abajo** (Cuaderno / Parcelas / Historial / Ajustes): el proyecto tiene la regla de
   no meter menús que haya que aprender, y esa barra añadiría pantallas que hoy no existen. Todo lo que hace
   falta está en la pantalla de inicio.
2. **El aviso de la campaña en la cabecera** («Campaña 2026»): el diseño lo dibuja en una cabecera que lleva
   el título de la pantalla debajo; aquí el título vive dentro de cada pantalla y el año ya se ve donde
   importa (el inicio y cada bloque que es de la campaña). La cabecera es lo único que se ve **siempre**, y
   repetir ahí un dato que ya está en pantalla es gastar el sitio más valioso.
3. **Tarjetas para productos, máquinas y naves**: al ir a hacerlas se comprobó que **el dato que hace falta
   para elegir ya está en el botón** —el número de la etiqueta y los días de espera en los productos, los tres
   números del abono en los abonos— y que esas cosas **no tienen forma que dibujar**, que es lo que hace útil
   la tarjeta de una tierra (51 tierras y todas del mismo color).
4. **La ayuda al final de la lista de tierras** («¿no encuentras una tierra o el SIGPAC está mal? Llama al
   técnico»): la frase tiene que decir **a quién se llama y con qué número**, y ese dato no lo tenemos.
   Escribir un teléfono inventado en la pantalla de un agricultor es lo que este proyecto no hace.
5. **Un segundo bloque verde oscuro** para el «¿para qué sirve esto?» del almacén (ronda 90): la ronda 80
   decidió que **el bloque oscuro es el de la inspección**, porque es lo único que se hace con alguien
   delante. Un segundo bloque oscuro para una explicación le quitaría a aquel lo que lo hace útil.
6. **Las explicaciones de la ayuda que se abren al pulsarlas** (ronda 90): el agricultor entra ahí justo a
   leer eso. Esconderlo detrás de un toque añade un paso y una cosa que aprender en la pantalla que se abre
   cuando no se entiende algo. Lo que sí se abre son las cuatro tablas largas del final, como ya estaba.
7. **El resumen vivo del papel mientras se escribe** («LO QUE VA AL ARCHIVADOR», en «guardar un papel», ronda
   90): sería un resumen que se actualiza con lo que se teclea, y eso pide que la pantalla guarde el estado de
   los campos. Aquí los campos los lee `app.js` por su `id` (formularios no controlados), que es la decisión
   que sostiene toda la aplicación y la que hace que decenas de pruebas escriban en ellos como lo haría una
   persona. Se apunta como idea; no se hace a medias.
8. **Un segundo botón de buscar** en «traer la tierra del SIGPAC» (uno en cada camino, ronda 90): los dos
   caminos hacen la misma búsqueda —el programa usa la referencia si está puesta y, si no, el polígono y la
   parcela—, así que un botón para cada uno sería el mismo botón dos veces. Se deja uno, con los dos caminos
   bien separados y con su nombre.

**Y cuatro ideas de diseño que necesitan algo que hoy no existe** (no se descartan: están apuntadas con su
motivo en `LO_QUE_FALTA_POR_DISENAR.md` y en el `LEEME` de `docs/stitch/rediseno/`):

- **«Ver entradas y salidas de este producto»** (el almacén): sería una pantalla nueva, con su acceso, sus
  pruebas y su sitio en la caché del campo.
- **«Te llega para unas N hectáreas»** (el almacén): esa cuenta la tiene que hacer el **servidor** (con el gasto
  medio de los apuntes); hacerla en la pantalla con datos que no tenemos sería inventarse un número.
- **«Apuntar tratamiento a las N»** (los grupos): un atajo que abra el asistente con el grupo ya elegido. Hoy
  se hace por el camino de siempre (al apuntar, después de la lista de parcelas salen los grupos), y el atajo
  es una función nueva, no un cambio de diseño.
- **El resumen vivo del papel mientras se escribe** (guardar un papel): pide que la pantalla guarde el estado
  de los campos, que es justo lo que este proyecto no hace (los lee `app.js` por su `id`).

**Cómo se comprueba todo esto** (y cómo lo puede comprobar cualquiera):

```bash
cd backend
../.venv/Scripts/python.exe -m pytest -q          # las pruebas de Python en verde
node --test "tests_js/*.test.js"                  # las de JavaScript en verde
../.venv/Scripts/python.exe scripts/humo.py http://127.0.0.1:8010            # «todo correcto»
../.venv/Scripts/python.exe scripts/comprobar_en_un_navegador.py http://127.0.0.1:8011
# ↑ recorre las pantallas en un Chrome de verdad, deja una captura de cada una en la carpeta temporal
```

---

## Lo que se ha aplicado (ronda 37)

Los cinco diseños que generó Stitch están en `docs/stitch/`, con **su captura al lado** (los `.png`),
para poder mirarlos sin abrir el navegador ni depender de una dirección de Google que caduca. Se
bajan con `backend/scripts/bajar_capturas_de_stitch.py`.

**Lo primero que se comprobó al mirarlos, y es la noticia buena: la paleta es exactamente la
nuestra.** Stitch diseñó **dentro de nuestras reglas**, porque lo que se le subió fue este mismo
`DESIGN.md` como sistema de diseño. Los colores que más usa (`#1f4a2c`, `#2f6b40`, `#0d2b18`,
`#10190f`, `#f4f6f3`, `#a9b6a8`, `#8a6a00`, `#3d2f00`) son **los del `:root` de `estilos.css`**, uno
por uno. Así que lo que aporta el diseño no es repintar la aplicación: es **jerarquía y señales**.

**Lo aplicado, y por qué:**

| Del diseño | Qué se ha hecho | Por qué |
|---|---|---|
| La **flecha al final de cada botón** | Puesta en **todos** los botones de la aplicación: en el `boton()` de la interfaz vieja y en el componente `Boton` de React | Es lo que hace que se vea de un vistazo que ese botón **lleva a algún sitio**. Sin ella, un botón y una casilla se parecen. Va con `aria-hidden`, porque quien usa un lector de pantalla ya oye que es un botón. Y va en los dos sitios a la vez **a propósito**: si solo estuviera en las pantallas de React, la aplicación se vería distinta según la pantalla |

**Lo que NO se ha aplicado, y por qué:**

| Del diseño | Por qué no |
|---|---|
| **Dos botones grandes** (ECHAR PRODUCTO y ABONAR en verde sólido) | Hoy solo «ECHAR PRODUCTO» es el grande. Cuál lo es viene de `textos.PANTALLA_INICIO` (`principal`), que es un dato: cambiarlo cambia lo que ve el agricultor y **lo decide él**, no el agente. Se deja como está y se le pregunta |
| La **etiqueta pequeña** encima de la pregunta («REGISTRO DE HOY») | Es texto nuevo para el agricultor, así que tiene que venir de `textos.py` y pasar el test de jerga. Se aplica cuando él diga que quiere esa frase |
| El **cartel amarillo de «Modo Campo (Sin conexión)»** | El programa **ya tiene** su aviso de lo que queda por mandar (`#aviso-pendientes`, arriba y siempre visible), con su texto en `textos.py` y sus pruebas. Cambiarle la forma es otra decisión suya |

**El diseño, por tanto, no se ha tirado ni se ha copiado a ciegas**: se ha mirado, se ha comprobado
que respeta el contrato de diseño, y se ha aplicado lo que mejora la pantalla sin cambiar nada de lo
que el agricultor ya tiene decidido.

---

## Lo que se ha aplicado (ronda 76): el rediseño, empezado

David pidió **rehacer la interfaz entera** con Stitch («la aplicación es terrible de usar»). Se creó el
proyecto `CueDigital - cuaderno de campo y digital` en Stitch, se le subió **nuestro `DESIGN.md`** como
sistema de diseño y se le pidieron las pantallas, con el texto real del agricultor y las reglas del campo.
Los diseños y sus capturas están en **`docs/stitch/rediseno/`**, con un `LEEME.md` que cuenta qué se pidió,
qué se aplicó y qué queda.

**Lo aplicado en esta ronda:**

| Del diseño | Qué se ha hecho | Por qué |
|---|---|---|
| **El botón normal es una tarjeta blanca con borde grueso**, y el verde sólido se reserva para **la acción principal** | Cambiado en `estilos.css` (`.boton`, `.boton-principal`, `.boton-claro`) | Antes **todos** los botones eran verdes y sólidos: «HE ECHO PRODUCTO» se veía igual que «NO SÉ QUÉ PULSAR», y eso es lo que hacía que la pantalla pareciera un formulario sin principio ni fin |
| **Iconos dibujados** en vez de emoji | Hecho en `componentes.js` (`Icono`): 14 dibujos, con los trazos del diseño (estilo Feather, licencia MIT) | Los emoji se ven distintos en cada móvil y con un estilo que no es el de la aplicación. La clave del dibujo sigue siendo el emoji del texto, así que **`textos.py` no se toca** |
| **El cuadro del icono** (el dibujo dentro de su cuadrado con borde) | Hecho en `estilos.css` (`.boton .icono`) | Es lo que hace que el icono se lea como un icono y que todos los botones tengan el mismo hueco |
| **La pantalla de inicio no tiene su propia copia del botón** | `inicio.js` usa el botón común (`componentes.js`) | Tenía su copia desde el paso piloto de la migración: dos botones que se podían separar con el tiempo |

**Lo que queda por aplicar** (está contado en `docs/stitch/rediseno/LEEME.md`, con su captura): los pasos
del asistente (barra de progreso por tramos, la tierra con el dibujo de su forma, el círculo de elegida, los
avisos dentro de la tarjeta y **la barra de botones pegada abajo**), las tarjetas de tierras, los bloques
de «mi cuaderno» y la cabecera.

**Y una cosa del diseño que NO se aplica, a propósito:** Stitch puso una **barra de pestañas abajo**
(Cuaderno / Parcelas / Historial / Ajustes). El proyecto tiene la regla de no meter menús que haya que
aprender, y esa barra añadiría pantallas que hoy no existen. Se queda en la carpeta, con este motivo
escrito.

---

## Lo que se ha aplicado (rondas 77 y 78): las listas de tierras

Las dos rondas siguientes atacaron **el problema de usabilidad más gordo que tiene la aplicación**: las
listas de tierras. David tiene **51 tierras dadas de alta**, y en la aplicación eran **filas de texto
iguales** —«El Prado · 4,90 ha · secano»— en dos sitios distintos: en el asistente, al elegir dónde se ha
echado el producto (donde una elección equivocada **apunta el tratamiento en la tierra que no es, y eso no
se nota hasta que alguien mira el cuaderno**) y en «Mis parcelas, productos y máquinas» (donde además **no
se podía hacer nada** con esa lista).

| Del diseño | Qué se ha hecho | Por qué |
|---|---|---|
| **La tarjeta de una tierra** (`mis_tierras.png`, `asistente.png`) | Pieza nueva `react/piezas/tarjeta.js` (entonces `tarjeta_de_tierra.js`): el **dibujo de la forma de la tierra**, su superficie, su pueblo, sus avisos dentro y **la palabra «ELEGIDA»** con el círculo marcado | Es como el agricultor reconoce de verdad una tierra: **la ve así en el visor del SIGPAC** y en el papel. Con 51 tierras, un renglón no se distingue del de al lado |
| **La barra de progreso por tramos** y el paso en palabras | `.pasos` / `.paso` y «Paso 1 de 13» (`rotulos.paso`) | Una barra sola no dice cuánto queda si no se cuentan los tramos |
| **La barra de botones pegada abajo** | `.asistente-acciones` (`position: sticky; bottom: 0`) en el asistente | De pie en el campo y con una mano, SEGUIR tiene que estar **donde llega el pulgar**, no al final de una lista de cincuenta tierras |
| **Las tierras con su tarjeta en «mis cosas»** (`mis_tierras.png`) | La sección de parcelas de `mis_cosas.js` pinta tarjetas: rótulo «Tierra n.º 12», datos **con su nombre delante** (`Referencia oficial SIGPAC`: un código suelto no dice qué es), **lo que hay sembrado este año** y, si le falta decirlo, el aviso en ámbar **con el camino para arreglarlo dentro de la tarjeta** | La lista era un muro de renglones **y no hacía nada**. Ahora cada tarjeta **abre** lo que hay sembrado en esa tierra (`cultivo-decir`): es lo único que se puede hacer con ella desde ahí, y por eso va **sin el círculo de elegir** |
| **Decir cuántas tierras hay** | «Tienes 51 tierras apuntadas» debajo del título de la sección | La lista se corta al final de la pantalla: sin decirlo, no se sabe si están todas |

**Lo que NO se aplicó de estos dos diseños, y por qué** (está entero en `docs/stitch/rediseno/LEEME.md`):

1. **El buscador «Buscar entre tus fincas».** Hoy no hay ningún buscador en la aplicación, y uno que
   filtrara a medias sería peor que no tenerlo. Va con su ronda.
2. **El bloque verde «CULTIVO EN REGLA».** Repetía en tres líneas lo que la tarjeta ya dice en una; el
   ámbar se reserva para lo que de verdad falta.
3. **La ayuda del final** («¿no encuentras una tierra o el SIGPAC está mal? Llama al técnico»). La frase
   tiene que decir **a quién se llama y con qué número**, y ese dato hoy no lo tenemos: escribir un
   teléfono inventado en la pantalla de un agricultor es exactamente lo que este proyecto no hace.
4. **Las otras seis secciones de «mis cosas»** (productos, abonos, quién aplica, quién asesora, máquinas y
   naves) siguen con su lista de renglones: son diez o doce cosas y se leen de un tirón.

---

## Lo que se ha aplicado (ronda 79): los apuntes de «mi cuaderno»

«Mi cuaderno» es **la pantalla que más se mira** —aquí está el año entero del agricultor—, y su primer
bloque eran los apuntes de producto, uno por renglón. El diseño (`docs/stitch/rediseno/mi_cuaderno.png`) los
pide como **fichas cerradas e independientes**, y al hacerlo salió a la luz algo que no era solo estético:

| Del diseño | Qué se ha hecho | Por qué |
|---|---|---|
| **Cada apunte, una ficha con fecha, producto, parcela y hectáreas** | Cada apunte es una tarjeta: `Apunte 1`, la fecha, y sus filas **con el nombre delante** —`Tierra y parcela`, `Hectáreas tratadas`, `Cuánto por hectárea`, `Cultivo` y `Hasta aquí no puedes coger la cosecha:`— | El renglón decía «TRIGO BLANDO · 4,90 ha · 0,80 L/ha»: tres datos seguidos sin decir cuál era cuál, y **la tierra donde se echó el producto no salía en ninguna parte**. Eso no es un problema de aspecto: «¿dónde lo echaste?» es la primera pregunta de una inspección, y el dato estaba guardado desde el primer día |
| **Botón para añadir otro tratamiento, dentro del bloque** | `APUNTAR OTRO TRATAMIENTO` al pie de la lista, con el mismo dibujo que en la pantalla de inicio y su mismo camino | Desde la pantalla que más se usa, apuntar uno nuevo obligaba a volver al inicio y buscarlo: dos pasos de más, y en el campo los pasos de más se pagan |
| **«Fichas cerradas»** | La tarjeta **no es un botón** donde solo se lee: la misma pieza se pinta como `<div>` cuando no lleva acción | Un apunte no tiene pantalla propia: un botón que no hace nada **promete una salida y no la da**. La pieza decidió aprender eso en vez de tener dos tarjetas que se van separando |

**Y con la tercera vez que hizo falta la tarjeta, el fichero cambió de nombre**: de
`react/piezas/tarjeta_de_tierra.js` a **`react/piezas/tarjeta.js`**. Servía ya para tres cosas (elegir una
tierra en el asistente, mirar las tierras de la finca y leer los apuntes del cuaderno). Con el nombre
viejo, la tarjeta del apunte habría acabado siendo una copia; ahora es la misma pieza, y lo que cambia
—botón o no— lo decide el dato que le llega. La caché del móvil sube a la 38 para que nadie se quede con el
aspecto de antes.

---

## Lo que se ha aplicado (ronda 80): de un vistazo, y lo que hay que enseñar

Dos cosas del mismo diseño (`docs/stitch/rediseno/mi_cuaderno.png`), y las dos sobre lo mismo: **que la
pantalla que más se mira conteste sin tener que leerla entera**.

| Del diseño | Qué se ha hecho | Por qué |
|---|---|---|
| **El bloque oscuro «Para la inspección oficial»**, con el botón de sacar el cuaderno dentro | «Sacar mi cuaderno para la Junta» es ahora un bloque con **fondo verde oscuro** —el único bloque oscuro de la aplicación—, con la explicación en blanco y **el botón a lo ancho dentro del bloque**; los otros dos botones debajo. La lista de lo que falta se queda **fuera del verde** | Es lo único de esa pantalla que se hace **con alguien delante**: el inspector, en el campo, esperando. Hay que encontrarlo sin leer nada, y el contraste es lo que lo consigue al sol. Lo que falta se lee con calma, así que va en blanco |
| **«Tienes pendientes 0 tareas de revisión»**, debajo del título | Una frase: «Te falta 1 cosa por apuntar», «Te faltan 3 cosas por apuntar» o «No te falta nada por apuntar» | Es la pregunta con la que se abre el cuaderno: «¿lo tengo al día?». Antes había que bajar hasta el bloque de «lo que falta por completar» para saberlo |

**Y una decisión que es la de siempre, pero escrita aquí porque se ve en el código:** la frase **solo se
dice si el servidor ha contestado** lo que falta. Con la petición fallida, la lista llega vacía, y decir
«no te falta nada por apuntar» sería **afirmar lo que no se sabe**. Hay una prueba para ese caso
(`si el servidor no contesta lo que falta, no se afirma que no falte nada`), y es la que importa de las tres.

**Lo que queda de este diseño:** el **aviso de la campaña** en la cabecera, que no es una pantalla de React
sino el marco de la aplicación (`index.html` + `app.js`), y por eso se hace aparte. Los números de cada
bloque se hicieron en la ronda 81 (aquí abajo).

---

## Lo que se ha aplicado (ronda 81): el número de cada bloque

El diseño pone el número grande en la cabecera de cada bloque —«2 entregas registradas · 42.000 kg de trigo
blando», «1 análisis guardado»—, y al ir a hacerlo resultó que **los dos resúmenes que había no decían lo
que tenían que decir**:

| Lo que había | Lo que hay ahora | Por qué |
|---|---|---|
| `2 · 44.000 Kilos` | **`2 ventas apuntadas · 44.000 kg`** | Ni dice qué se cuenta (¿dos qué: entregas, lotes, compradores?) ni se lee bien: «Kilos» es un rótulo de campo y va en mayúscula en medio de una frase. Se dice «ventas apuntadas» porque es como llama a esto el resto de la aplicación |
| `1 · Dónde se aprovecha esto:` | **`1 análisis guardado`** | Era la explicación de para qué sirve un análisis puesta **justo donde va el número**: la línea decía para qué sirve pero no cuántos hay |

Los dos van en la misma línea destacada que la frase de un vistazo (`.cuantas`), y **en singular cuando son
uno**: «1 ventas apuntadas» es lo primero que hace desconfiar de un programa, y el proyecto ya tiene esa
regla escrita en `test_sin_jerga.py`. Cuando no hay nada (ninguna venta, ningún análisis), **no se dice
ningún número**: la frase de la lista vacía ya lo cuenta, y un «0 ventas apuntadas» encima sería repetir lo
mismo con peor cara.

**Y una cosa que trajo esto:** la comprobación en un navegador de verdad ahora **siembra una venta**. Hasta
hoy no sembraba ninguna, así que ese bloque se comprobaba siempre en su estado vacío —y con el estado vacío
la línea del número ni se dibuja—. Es la misma lección de la ronda 77: **una pantalla que se comprueba vacía
pasa cualquier prueba**.

---

## Lo que se ha aplicado (ronda 82): el buscador de tierras

El diseño lo pide en la lista de tierras («Buscar entre tus fincas»), y se ha puesto **donde de verdad hace
falta**: en el paso del asistente donde se elige la tierra. Ahí es donde David, con **51 tierras** dadas de
alta, tenía que recorrer cincuenta y una tarjetas con el pulgar para apuntar dónde ha echado el producto.

| Del diseño | Qué se ha hecho | Por qué |
|---|---|---|
| **Un buscador encima de la lista** | Un campo con su etiqueta, su pista, su ejemplo y su botón (`BUSCAR`), usando **la pieza del campo** que ya existe, más `VERLAS TODAS` cuando hay una búsqueda puesta | Escribir una pieza nueva para «una casilla con un botón» sería tener dos sitios donde se escribe un `<label>`. Y el campo lleva su `id` (`#buscar_tierra`), que es como `app.js` lee lo que el agricultor escribe: **eso no es decoración** |
| **Buscar por nombre** | Se busca por el nombre, **por el pueblo y por el número del SIGPAC** | Son las tres cosas por las que se llama a una tierra. Y **sin tildes**: quien escribe con una mano y con guantes no pone tildes, y el programa no puede castigarle por eso |
| — | El número del SIGPAC se compara **por trozos en su orden**: «503», «503-51» o «37 70 503» encuentran la misma tierra | En el visor se copia «37-70-0-0-503-51-1» y quien lo escribe de memoria teclea «37 70 503»: los ceros sueltos están en todas las referencias y no distinguen nada |

**Cuatro decisiones que están en el código y conviene no deshacer:**

1. **Lo escrito no se borra al buscar.** La pantalla se vuelve a montar entera, así que el texto vuelve al
   campo. Si no, el agricultor escribe, busca, y se queda sin saber qué buscó.
2. **De un filtro se puede salir siempre** (`VERLAS TODAS`), y si la búsqueda no encuentra nada se dice y el
   aviso lleva el botón. Una lista vacía sin salida es un agricultor creyendo que ha perdido sus tierras.
3. **El buscador se vacía al empezar un apunte nuevo.** Un filtro que sobrevive sin verse es la forma más
   fácil de que alguien crea que le faltan tierras.
4. **Una cifra suelta no da por buena ninguna tierra.** Los números se comparan en trozos de dos cifras o
   más: buscar «5» no puede sacar las cincuenta y una. Lo que sí casa con «51» es un trozo de una referencia
   de verdad, y eso es una búsqueda legítima.

**Y la comprobación en un navegador de verdad recorre el buscador de verdad**: siembra **una segunda tierra**,
escribe «suertes», pulsa BUSCAR y comprueba que **la otra tierra ha desaparecido de la lista**. Es lo único
que no se puede ver en un DOM de mentira —ahí el campo que pinta React no existe—, y es lo que une el campo
con la lista. Esa comprobación ya encontró una cosa: el **ejemplo dentro de la casilla** decía «El Prado,
Calvarrasa, 503» y esa tierra salía siempre en la pantalla, así que el ejemplo pasó a ser «Por ejemplo:
503 51» —un ejemplo que no nombra ninguna tierra de verdad, porque un ejemplo con un nombre real engaña a
quien lea la pantalla y a quien la compruebe—.

---

## Lo que se ha aplicado (ronda 83): la ayuda, cada cosa con su nombre

La pantalla de ayuda es **a donde va el agricultor cuando no entiende algo** —es lo que hay detrás del botón
«NO SÉ QUÉ PULSAR»—, y tenía dos muros: los seis puntos de lo que obliga la ley y los diez porqués salían
como párrafos seguidos **sin nombre**, así que no se sabía dónde acababa uno y empezaba el siguiente, y para
encontrar «lo de mandarlo a la Junta» había que leerlos todos.

| Lo que había | Lo que hay ahora |
|---|---|
| Seis párrafos largos bajo un único rótulo («Qué te obliga la ley, y qué no») | **Cada punto con su título**: «Llevar el cuaderno al día», «Mandar los datos a la Junta», «Con un programa tuyo», «Las fechas que importan», «Cuándo será obligatorio del todo», «Lo que todavía no está aclarado» |
| Diez párrafos seguidos, sin caja ni título | **Cada porqué con su nombre**: «Para qué sirve el cuaderno», «En papel o en el móvil», «Qué pasa si no lo llevo», «Por qué te pido tantos datos», «Por qué hay días de espera», «Por qué te aviso de los nitratos»… |
| Los saltos de línea del texto se perdían | El porqué del cuaderno enumera tres motivos y ahora salen **en tres líneas**, no en un párrafo corrido (`white-space: pre-line` en `.apunte-detalle`) |

**Dos decisiones que están en el código:**

1. **El título va aparte del texto** (`PORQUE` + `PORQUE_TITULOS`, y el texto de cada punto de la ley con su
   `_titulo` al lado). No es capricho: el mismo porqué se enseña en otras pantallas —el de vender, en «lo que
   he vendido»; el de las medidas, en las medidas— donde un título no pinta nada, y los textos de la ley se
   siguen usando donde ya estaban.
2. **Dos pruebas nuevas lo vigilan** (`test_sin_jerga.py`): que ningún porqué ni ningún punto de la ley pueda
   llegar **sin nombre**, que no sobre ningún título, que el título no sea el rótulo del apartado repetido y
   que un título sea un título (no un párrafo de sesenta palabras). Y los títulos pasan por la prueba de jerga,
   como todos los textos (`textos_visibles()`).

**Lo que NO se hizo, y por qué:** los dos bloques largos (los aportes máximos de nitrógeno y los periodos
prohibidos) siguen **abriéndose al pulsarlos** (`<details>`), como estaban. Son tablas y, si se abren todas,
tapan lo demás; y `<details>` es lo que sabe abrir y cerrar un lector de pantalla **sin una línea de
JavaScript**. Cambiarlo por un desplegable propio sería más bonito y funcionaría peor.

---

## Lo que se ha aplicado (ronda 84): los números, en singular cuando son uno

Yendo a mirar «qué hay sembrado» me encontré la primera línea de la pantalla:

> **A 1 parcelas les falta decir qué tienen este año.**

Ese es el fallo que el propio proyecto tiene escrito como regla desde la primera ronda —*«1 apuntes es lo
primero que hace desconfiar de un programa»*— y que solo se cumplía en los mensajes que pasan por
`mensaje_con_cuenta`. Los demás textos con el número delante se habían quedado en plural:

| Lo que decía | Lo que dice ahora | Dónde |
|---|---|---|
| «A 1 parcelas les falta decir qué tienen este año» | «A 1 parcela le falta decir qué tiene este año» | «qué hay sembrado» |
| «Tienes 1 productos apuntados» | **«Tienes 1 producto apuntado»** | «lo que tengo en el almacén» |
| «Tienes 1 papeles guardados» | «Tienes 1 papel guardado» | «los papeles» |
| «1 cosas apuntadas esperando a que haya cobertura» | «1 apunte esperando a que haya cobertura» | **el aviso de la cabecera**, el que sale en el campo sin cobertura |
| «1 hojas de 25 llevan datos tuyos» | «1 hoja de 25 lleva datos tuyos» | el bloque verde de la inspección |

**Y una cosa que salió al hacerlo, que no era de textos sino de pantalla:** la frase del almacén **no la
enseñaba nadie**. El servidor contaba los productos y mandaba «Tienes 1 producto apuntado», y la pantalla del
almacén no la leía: se calculaba para nada. Ahora va en su línea destacada (`.cuantas`), la misma que llevan
las tierras y los apuntes del cuaderno. Es el tercer sitio donde aparece el mismo olvido —un dato que se
calcula y no se enseña—, y el que lo cazó fue mirar la pantalla con los ojos, no una prueba.

**El ayudante, para no repetirlo:** `con_cuenta(diccionario, base, cuantos)` en `textos.py` (y su gemelo
`conCuenta` en `nucleo.js` para los textos que compone la interfaz). El singular se escribe al lado del plural
con la terminación `_uno`, y si falta se usa el de siempre —en pantalla nunca se queda un hueco—; lo que
impide que falte es **`TestSingularYPlural`**, que exige las dos formas y comprueba que el singular no lleve
el número dentro. Dos pruebas más van contra la API de verdad (los papeles), para que la frase salga entera.

**Lo que queda pendiente de esta familia, y por qué:** `grupos.cuantas` («{cuantas} parcelas») **no lleva
singular a propósito**: una agrupación de una sola parcela no tiene sentido y el servidor la rechaza, así que
ese texto nunca puede salir con un uno. Y hay dos textos de cuenta (`mapa.cuantos`, `labores.apuntes`) que
**no los usa nadie**: están escritos y no se enseñan en ninguna pantalla. Se dejan como están y se dice aquí:
quitarlos o usarlos es otra decisión, y no la de esta ronda.

---

## Lo que se ha aplicado (ronda 85): los números del plan, y la flecha donde toca

Seguí mirando pantallas con los ojos —es lo que ha dado los mejores hallazgos de estas rondas— y me paré en
**el plan de abono**, que es la sección que la Junta pide como «Recomendación de nutrientes». Tenía dos
cosas que no se leían:

| Lo que había | Lo que hay ahora | Por qué |
|---|---|---|
| La tabla: `N  100,0 · 0,0 · 100,0` bajo la cabecera **«Tenías previsto · Llevas»** | Cabecera **«Tenías previsto · Llevas · Te queda»**, y las tres cifras debajo | Eran **tres números con dos rótulos**: el tercero había que adivinarlo. Y el texto «Te queda» ya existía en `textos.py` sin que lo usara nadie |
| Cuando alguien se había pasado: `N  100,0 · 130,0 ⚠️` | `N  100,0 · 130,0 · Pasado` | Un ⚠️ suelto en el sitio de un dato no se puede leer; y «Pasado» es otro texto que existía y no se usaba. El aviso de arriba ya lo dice en rojo, pero eso no sustituye al rótulo |
| `Lo hice: Sí` en el detalle del plan | `Lo hice con una herramienta: Sí` | «Lo hice: Sí» no dice el qué. La pregunta del asistente es «¿Has usado un programa o una herramienta para hacerlo?», así que el rótulo dice lo mismo en corto |

**Y una cosa que se veía al mirar «lo que hago sin echar producto»:** los diez botones de las medidas
llevaban **flecha**. En esta aplicación la flecha significa una cosa muy concreta —«esto te lleva a otro
sitio»; está escrito en `componentes.js`, en el comentario de `Flecha`—, y esos botones **marcan y desmarcan
una medida en la misma pantalla**: la flecha ahí mentía. Ahora el botón de casa sabe pintarse sin ella
(`flecha: false`) y lo que dice que se marca es el cuadro del icono (✅ / ⬜). Los tres botones de abajo
—GUARDAR, NINGUNA, VOLVER— siguen llevándola, porque esos sí salen de la pantalla.

**Lo que se miró y NO se tocó, y por qué** (para que se sepa que se miró):
- **«Los papeles»** y **el estado vacío del plan**: están bien resueltos —título, explicación, el aviso en
  ámbar y su botón principal— y no había nada que arreglar.
- **La lista de «las medidas»**: las diez preguntas en su fila, con su cuadro, su explicación arriba y el
  aviso de dónde sale el catálogo. Lo único que estaba mal era la flecha.
- **`mapa.cuantos` y `labores.apuntes`**: dos textos de cuenta que no usa nadie. Se quedan como están y se
  dice aquí; usarlos o quitarlos es otra decisión.

---

## Lo que se ha aplicado (ronda 86): las ventas, cada dato con su nombre

Otra vez mirar la pantalla con los ojos. «Lo que he vendido» enseñaba cada venta así:

> **10/07/2026 — Trigo blando**
> 42.000,00 kg · Venta a comprador · Cooperativa Agrícola de Peñaranda · Partida L-2026-07 · Albarán ALB-2026-118 · El Prado

**Seis datos seguidos y sin decir cuál es cuál.** El comprador se saca por el contexto, pero «L-2026-07» y
«ALB-2026-118» no dicen qué son —y la partida y el albarán son justo lo que se busca cuando alguien pregunta
por una entrega—. Ahora la venta es una ficha: **Cuánto** 42.000,00 kg · **Cómo lo vendiste** Venta a
comprador · **A quién** Cooperativa Agrícola de Peñaranda · **Partida** L-2026-07 · **Albarán** ALB-2026-118 ·
**De dónde** El Prado.

**Y los rótulos no hubo que inventarlos**: `tabla_cuanto`, `tabla_quien`, `tabla_lote`, `tabla_donde` y
`tabla_albaran` están en `textos.py` desde hace rondas —son los de la tabla de la Junta— y **solo se usaban
dos**. Es la cuarta vez en estas rondas que el problema es el mismo: **un texto escrito que no se enseña** (el
singular de las cuentas, el «Te queda» del plan, el «Pasado», el número del almacén…). Cuando el dato ya está
escrito, lo que falta casi nunca es contenido: es que alguien lo mire.

**Dos decisiones que quedan en el código:**

1. **El bloque de «mi cuaderno» sigue con la línea corta**, a propósito: enseña hasta cuatro ventas de un
   tirón y con seis filas cada una no cabría. La ficha con nombre está a un toque, en su pantalla. Las dos
   formas se arman en `app.js` y cada una dice para qué es.
2. **La pantalla entra en la comprobación de un navegador de verdad** (no estaba en la lista): es lo único
   que garantiza que los datos del servidor llegan hasta la ficha que se dibuja, y no solo que el componente
   sepa pintar lo que le pasen.

**Lo que se miró y NO se tocó:** «Los análisis» está bien resuelto —la ficha con sus rótulos, los números del
boletín y el aviso honesto de que falta el papel, con su botón para subirlo— y no había nada que arreglar. Es,
de hecho, el modelo que se ha copiado para las ventas.

---

## Lo que se ha aplicado (ronda 87): el buscador también en «mis cosas»

El diseño pide el buscador **en la pantalla de tierras** («Buscar entre tus fincas»). En la ronda 82 se puso
en el paso del asistente, que es donde se elige una tierra con prisa; ahora está también en «Mis parcelas,
productos y máquinas», que es donde el diseño lo dibuja y donde se miran (con 51 tierras, buscar una concreta
era recorrerlas todas). Es la misma casilla con los mismos textos: no hay nada nuevo que aprender.

**Tres decisiones que quedan en el código:**

1. **El número de la tierra no cambia al buscar.** La que es «Tierra n.º 2» en la lista entera sigue siéndolo
   cuando sale sola entre las que casan. Renumerar al buscar sería mentirle: ese número es como la llama el
   agricultor cuando habla de ella.
2. **Un filtro por pantalla, y a propósito.** El del asistente y el de «mis cosas» son dos estados distintos.
   Con uno solo, buscar «prado» al apuntar un tratamiento dejaría «mis cosas» enseñando una tierra de las 51
   sin que nadie lo hubiera pedido allí —y su cuenta de arriba seguiría diciendo que hay 51—. Hay una prueba
   que lo comprueba: `los dos buscadores de tierras no se pisan`.
3. **Si no casa ninguna se dice, y con salida.** El aviso de «todavía no tienes parcelas» sería mentira (las
   tiene), así que sale el suyo —«Con esas letras no encuentro ninguna tierra»— con el botón de volver a
   verlas todas. Es la misma regla de la ronda 82: un filtro del que no se puede salir es una lista de
   tierras que ha desaparecido.

**Y una cosa del diseño que NO se aplica, ahora con el motivo escrito:** el **aviso de la campaña** en la
cabecera («Campaña 2026»). El diseño lo dibuja en una cabecera que lleva **el título de la pantalla** debajo
de la barra; en esta aplicación el título vive dentro de cada pantalla (y así la cabecera no cambia nunca), y
el año ya se ve donde importa: en la pantalla de inicio («Hola · 2026») y en cada bloque que es de la campaña.
Meterlo en la cabecera —que es lo único que se ve **siempre**— sería gastar el sitio más valioso de la
aplicación repitiendo un dato que ya está en pantalla. Si algún día la aplicación enseña datos de campañas
anteriores, ese aviso tendrá sentido; hoy no.

---

## Lo que se ha aplicado (ronda 88): la pantalla del SIGPAC, sin lo que sobra

Seguí mirando pantallas y me paré en **la de traer una tierra del SIGPAC**, que es la que ahorra más trabajo
de todas (con 54 líneas, teclear cada tierra es la diferencia entre empezar y no empezar). Tenía dos cosas de
más:

| Lo que había | Lo que hay ahora | Por qué |
|---|---|---|
| Una barra de progreso llena y **«Paso 1 de 1»** | Nada | Esta pantalla es un asistente de **un solo paso**: una barra llena y un «Paso 1 de 1» no cuentan nada y empujaban hacia abajo los campos. La barra sigue saliendo donde hay trece pasos que contar |
| La explicación de la referencia **dos veces**: como pista del paso (arriba) y como pista de la casilla (debajo) | Una vez, y cada una en su sitio: arriba lo que explica **la pantalla** («Si tienes la referencia del trozo, el programa trae solo la superficie, la pendiente, el uso y el dibujo…») y debajo de la casilla lo que explica **la casilla** («Pega lo que tengas: la del visor…, los siete números del papel…, la catastral…») | Eran el mismo párrafo, y la pantalla lo decía entero dos veces. El texto de arriba ya existía en `textos.py` (`sigpac.explica`) y no lo usaba nadie |

**Y una regla que queda en el componente:** el asistente **no pinta la barra ni cuenta los pasos cuando solo
hay uno**. Está escrito en `asistente.js` con su motivo, para que la próxima pantalla de un solo paso no
vuelva a nacer con una barra que no mide nada.
