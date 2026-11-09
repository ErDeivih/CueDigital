# Revisión de la interfaz nueva (`/nuevo/`)

> **Qué es.** El inventario de pantallas de la aplicación nueva y **diez problemas de
> interfaz concretos**, cada uno con la captura que lo demuestra, la explicación de por qué
> le duele a un agricultor de 50 a 70 años de pie en el campo, y el arreglo propuesto dentro
> de `DESIGN.md` y `docs/GUIA_UI_UX.md`.
>
> **Cuándo y cómo.** Revisión hecha el **09/11/2026** contra un servidor temporal en
> `http://127.0.0.1:8091`, con base y adjuntos en `%TEMP%`, y la explotación de volumen de
> `backend/scripts/datos_representativos.py`: **64 tierras en 5 municipios**, 12 productos,
> 24 tratamientos, 36 trabajos, 40 gastos, 10 ventas, 36 movimientos de banco y 30 papeles.
> El servidor se ha apagado al terminar (ver §5).
>
> **Y los arreglos, el 10/11/2026.** La revisión decía lo que estaba mal; esta segunda pasada
> **lo arregla**. Las pantallas se han vuelto a mirar y a medir a **360, 390, 768 y 1024 px**
> con `backend/scripts/capturar_la_revision_movil.py`, contra un servidor temporal en
> `http://127.0.0.1:8094` y la misma explotación de 64 tierras. El resultado está en §6, con
> la tabla de los cuatro anchos, las **capturas antes/después** de cada pantalla y el coste
> de cada arreglo. **La tabla del después da 0 desbordes, 0 controles por debajo de 44 px y
> 0 ventanas que no caben en los cuatro anchos.**
>
> **Dónde están las pruebas.** En `docs/capturas-revision/`:
> · 32 PNG de la revisión (`<pantalla>-390.png`, `<pantalla>-1024.png`…) y `mediciones.json`
>   (30 pantallas medidas: desbordes, tamaños de letra, contrastes, controles y textos);
> · 56 PNG del **antes** (`antes-<pantalla>-<ancho>.png`) y 56 del **después**
>   (`despues-<pantalla>-<ancho>.png`) a los cuatro anchos, más los dos estados vacíos;
> · `mediciones-antes.json` y `mediciones-despues.json`, con lo medido en el DOM pantalla por
>   pantalla y su resumen por ancho.
>
> **Lo que no es.** La revisión de §1–§5 no cambió ni una línea. **Los arreglos de §6 sí**, y
> son los que describen los ficheros y las pruebas de §6.5.

---

## 0. Cómo se ha mirado (y cómo se repite)

### 0.1. El servidor

```powershell
cd backend
$env:CUEDIGITAL_DATABASE_URL="sqlite:///$env:TEMP\cd-revision-8091\datos.db"
$env:CUEDIGITAL_ADJUNTOS="$env:TEMP\cd-revision-8091\adjuntos"
$env:CUEDIGITAL_SECRETO="revision"
$env:CUEDIGITAL_ENTORNO="pruebas"
$env:CUEDIGITAL_ITERACIONES_PBKDF2="100000"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8091
```

### 0.2. El guion de capturas y medidas

`backend/scripts/capturar_pantallas_para_la_revision.py` (nuevo, solo lectura de la app):

```powershell
cd backend
..\.venv\Scripts\python.exe scripts\capturar_pantallas_para_la_revision.py http://127.0.0.1:8091
```

Hace, por cada pantalla y por cada ancho (390×844 y 1024×900):

1. **Navega pulsando lo que pulsaría el agricultor** (`data-destino`, botones, pestañas),
   no inyectando estado. Al no haber rutas por pantalla (§1.2), esta es la única forma
   honesta de llegar a cada una.
2. **Espera a que la pantalla tenga sus datos** (no una foto de «cargando»).
3. **Mide en el DOM** (§0.3) y **hace la captura** desde arriba.

Además crea una **cuenta vacía de verdad** (sin tierras) para el estado vacío y repite
cuatro pantallas **en modo claro**, porque la app nueva se pinta en oscuro o claro según el
sistema y el contrato de diseño solo define la paleta clara.

### 0.3. Qué se mide, exactamente

Todo se lee con `getComputedStyle` y `getBoundingClientRect` en el navegador, y el contraste
se calcula en Python con la fórmula de la WCAG (la misma de `medir_el_contraste.py`).

| Medida | Cómo |
|---|---|
| Desborde horizontal | `document.documentElement.scrollWidth - innerWidth` |
| Letra pequeña | Cada nodo de texto visible, con `fontSize` en píxeles |
| Contraste | Color del texto contra el **fondo efectivo** (subiendo por los padres) |
| Tamaño de lo que se toca | Alto y ancho de cada `button`, `a`, `input`, `select` visible; umbral 44 px |
| Texto recortado | `scrollWidth > clientWidth` con `overflow: hidden` o `text-overflow: ellipsis` |
| Enlaces que salen de la app | `href` de cada enlace visible, con su texto y la zona donde está |
| Qué queda bajo el pliegue | Posición de cada control y de cada bloque de la pantalla |

### 0.4. Cómo se ha mirado cada captura

Las 32 capturas se han abierto y mirado una a una con la herramienta de lectura de imágenes
de este entorno (la herramienta `deepseek_vision` está deshabilitada en esta sesión: contesta
que el modelo ya ve las imágenes). La pregunta que se le ha hecho a cada una es la misma, y
está respondida en este documento para cada problema:

> *¿Hay texto cortado, tapado o pisado? ¿Qué botones hay y se entiende qué hacen? ¿Se
> entiende qué tiene que hacer el agricultor? ¿Hay números sin unidad o repetidos? ¿Hay
> letra demasiado pequeña o con poco contraste? ¿Aparece alguna palabra técnica o de
> programador?*

Lo que se afirma como problema está **en una captura que se ha mirado** o **medido en el
DOM**, y cada problema dice cuál de las dos cosas y con qué número.

### 0.5. Un aviso antes de los problemas: hay dos paletas

La app nueva trae **dos paletas**: una clara y otra oscura (`prefers-color-scheme: dark` en
`backend/web/nuevo/estilos.css`). El Windows de esta revisión está en oscuro, así que las
capturas de trabajo son **oscuras**; para que se vea lo que define `DESIGN.md` se repitieron
en claro `Hoy`, `Tierras`, `Apuntar` y `Cuaderno`.

- En **claro**, los contrastes medidos cumplen: texto secundario 7,31:1, cifra ámbar 5,41:1,
  pestaña elegida 6,51:1.
- En **oscuro**, la pestaña y el filtro elegidos se quedan en **2,48:1** y la marca «Hoy» del
  calendario en **3,28:1**. Eso es el problema P4.

`DESIGN.md` no tiene modo oscuro (define blanco `#ffffff` de fondo, `#1f4a2c` de marca y
`#ffd24a` de foco) y dice que todos los colores viven en el `:root` de `estilos.css` y en
ningún otro sitio. La app nueva usa **su propia hoja** con sus propios tokens (fondo crema
`#f3f0e8`, foco azul `#0b63ce`, ámbar `#9a5b12` de las cifras) y **una segunda paleta
oscura**. No es un problema de gusto: es un segundo contrato de color que nadie ha firmado,
y por eso el modo oscuro se saltó el suelo de contraste.

---

## 1. Inventario de pantallas

### 1.1. Las pantallas que hay

Todas se capturaron a **390×844** y **1024×900**. «Cómo se llega» son los pasos reales
desde la pantalla de arranque, porque la app nueva **no tiene rutas por pantalla** (ver 1.2).

| # | Pantalla | Cómo se llega | Capturas | Qué datos enseña |
|---|---|---|---|---|
| 1 | **Hoy** | arranque de `/nuevo/` | `hoy-390.png`, `hoy-1024.png`, `hoy-claro-390.png` | Finca y campaña, conexión, 64 tierras, gastos 2.868,2 € (por pagar), ventas «no consta», cuaderno «faltan 119 cosas», los 5 últimos apuntes con fecha, producto y tierra, y la lista de lo que falta para el cuaderno |
| 2 | **Mis tierras** | destino «Tierras» | `tierras-390.png`, `tierras-1024.png`, `tierras-claro-390.png` | 64 tierras en 5 municipios, buscador, «Colorear por Uso/Cultivo», lista agrupada por municipio con alias, hectáreas y uso/cultivo, mapa del municipio y leyenda |
| 3 | **Ficha de una tierra** | tocar una fila de «Mis tierras» | `tierra-390.png`, `tierra-1024.png` | Alias, municipio y 2,6 ha; mapa (o el aviso de que no tiene forma); «Apuntar un trabajo» y «Elegir en el SIGPAC»; datos del SIGPAC (superficie, uso, coeficiente, región, admisibilidad, cultivo, variedad); otros años; «Hoy en esta tierra»; historial 2026 con abono, cosecha, labores y el tratamiento del año |
| 4 | **Apuntar — labor** | destino «Apuntar» | `apuntar-390.png`, `apuntar-1024.png`, `apuntar-claro-390.png`, `apuntar-lista-de-tierras-390.png` | Lista de tierras con su miniatura, pestañas «Labor / Tratamiento / Abono / Siembra», fecha de hoy, hectáreas de la tierra elegida, aperos (Rodillo, Cultivador, Arado, Grada, Fresadora, Otro), nota y guardar |
| 5 | **Apuntar — tratamiento** | destino «Apuntar» y pestaña «Tratamiento» | `apuntar-tratamiento-390.png`, `apuntar-tratamiento-1024.png` | Lo mismo, con el buscador de producto, la dosis por hectárea, la plaga o hierba y el porqué |
| 6 | **Añadir tierras** | «Mis tierras» → «Añadir tierras» | `alta-390.png`, `alta-1024.png` | Dos caminos: buscar por los códigos del SIGPAC (con la ventana del mapa) o traer un cuaderno de la Junta. En el ordenador el mapa se abre dentro de la propia pantalla |
| 7 | **Ventana del SIGPAC** | «Añadir tierras» → «Buscar en el SIGPAC» | `sigpac-390.png`, `sigpac-1024.png` | Buscar por referencia o por pueblo; agregado, zona, polígono y parcela; resultados; y «Los contornos de toda la finca» con la provincia del mapa y su validez |
| 8 | **Cuaderno** | destino «Cuaderno» (en móvil, «Más» → «Cuaderno») | `cuaderno-390.png`, `cuaderno-1024.png`, `cuaderno-claro-390.png`, `cuaderno-arreglar-390.png` | 119 cosas que faltan, 8 que bloquean el envío, 102 que se pueden rellenar aquí, 17 que no; la lista agrupada por dónde se arregla, con «Arreglar» y «Abrir el cuaderno de la Junta» |
| 9 | **Productos y abonos** | destino «Productos» (en móvil, «Más» → «Productos») | `productos-390.png`, `productos-1024.png` | 12 productos con «Dosis máxima: no consta» y un botón «Apuntar en una tierra» por producto; pestaña de abonos (0); buscador por nombre o materia activa |
| 10 | **Calendario** | destino «Calendario» | `calendario-390.png`, `calendario-1024.png` | Mes en curso, navegación de mes, rejilla de días, marca «Hoy», «0 trabajos» y «No hay trabajo apuntado en este mes» |
| 11 | **Trabajos** | destino «Trabajos» (en móvil, «Más» → «Trabajos») | `trabajos-390.png`, `trabajos-1024.png` | 36 trabajos · 162,99 ha · 325,35 kg/ha; filtros por tipo con contador, por tierra y por fechas; resumen por tipo; «Descargar» |
| 12 | **Facturas** | destino «Facturas» (en móvil, «Más» → «Facturas») | `facturas-390.png`, `facturas-1024.png` | «Hacer una foto», «Elegir una foto o un PDF», «Leer la factura», «Escribirla a mano» y «Últimas facturas» vacío |
| 13 | **Más** | destino «Más» (solo móvil) | `mas-390.png` | Tarjetas a Facturas, Trabajos, Productos y Cuaderno, y «Ajustes» (que sale de la app; ver P1) |
| 14 | **Mis tierras, sin tierras** | cuenta recién creada | `vacio-tierras-390.png` | «0 tierras · 0 ha · 0 municipios», «Todavía no tienes tierras», «Traer tierras» y «Añadir tierras» |

**Lo que se puede decir a favor, medido**: en las treinta y dos capturas **no hay scroll
horizontal** (0 px de desborde; −15 px en el ordenador por la barra de scroll, que es
normal), **ningún `button`, `a`, `input`, `select` ni `textarea` visible mide menos de 44 px**
(medido en toda la página, incluidas las barras; las etiquetas que hacen de botón, como las
de la cámara de Facturas, no entran en esa cuenta), **no hay ningún nodo de texto del
contenido recortado con puntos suspensivos** (0 casos con `overflow: hidden`), y el estado
vacío tiene su botón (los otros tres estados los recorre el arnés del repositorio, no esta
revisión de capturas).

### 1.2. Cómo se llega, y lo que no se puede alcanzar

**La app nueva no tiene direcciones por pantalla.** `App()` arranca siempre en `hoy` y
cambia la vista con estado de React: no lee ni escribe `location.hash`. Consecuencias
medibles en esta revisión:

- No se puede **abrir una pantalla concreta** con una dirección: recargar vuelve a «Hoy».
- No se puede **compartir** un enlace a una tierra, a un apunte o al cuaderno.
- El guion de capturas tiene que **pulsar** para llegar a cada pantalla, y así está hecho.

**Pantallas de la lista del encargo que NO se pueden alcanzar dentro de `/nuevo/`**, con el
motivo comprobado en el DOM:

| Pantalla pedida | Por qué no se alcanza |
|---|---|
| **Entrar** | La app nueva no tiene pantalla de entrar: sin vale pinta el estado «Entra con tu cuenta» con un botón que va a `/`. La pantalla de entrar es de la app vieja |
| **Ayuda** | No existe en `/nuevo/`. En el móvil no hay ningún destino que lleve a ella |
| **Mis datos** | No existe en `/nuevo/`. Solo se nombra como texto («Mis datos → tu finca») en lo que falta |
| **PAC y subvenciones** | El destino de la barra lateral es un enlace a `/` (medido en `tierras-1024.png`) |
| **Documentos** | Igual: enlace a `/` |
| **Ajustes** | Igual: enlace a `/`; en el móvil, tarjeta «Ajustes · Abrir la app de siempre» |
| **Quién entra en mi finca** | No existe en `/nuevo/` |
| **Apuntar — abono y siembra** | Las pestañas existen y su formulario también, pero esta revisión se detiene en «labor» y «tratamiento»; no se capturaron las otras dos |
| **Productos — pestaña abonos** | Existe; la captura se hizo en «Productos». En la explotación de prueba no hay abonos dados de alta |

Todo eso es, en sí, parte del **problema P1**: en el menú, lo que no está hecho se ve igual
que lo que sí, y al pulsarlo te saca de la aplicación sin avisar.

---

## 2. Los diez problemas

Cada uno lleva: **(a)** qué se ve mal y en qué pantalla, **(b)** la captura, **(c)** por qué
le duele al agricultor, **(d)** el arreglo propuesto dentro del contrato.

---

### P1. «Apunta lo que has hecho» y otros botones grandes te sacan de la app sin decirlo

**Gravedad: alta.** Arreglo de **maquetación y texto** (destinos y rótulos).

**Qué pasa.** En «Hoy», el botón verde grande que ocupa todo el ancho dice **«Apunta lo que
has hecho»** y al pulsarlo **abre la app vieja en `/`**: medido, su `href` es `/`. En la
misma pantalla, la barra inferior tiene otro botón verde, **«Apuntar»**, que sí abre la
pantalla nueva. Dos botones con el mismo aspecto y el mismo propósito que llevan a dos
programas distintos. Lo mismo pasa en más sitios:

| Pantalla | Botón o enlace | Destino medido |
|---|---|---|
| Hoy | «Apunta lo que has hecho» (botón principal) | `/` |
| Hoy | «Abrir la app de siempre» | `/` |
| Mis tierras vacío | «Traer tierras» — al lado de «Añadir tierras», que sí es de la app nueva | `/` |
| Cuaderno | «Abrir el cuaderno de la Junta» | `/` |
| Cuaderno | «Arreglar» de las máquinas de echar producto | abre «Productos y abonos» (ver P6) |
| Más | tarjeta «Ajustes · Abrir la app de siempre» | `/` |
| Barra lateral (1024) | «PAC y subvenciones», «Documentos», «Ajustes» | `/` |

**Capturas.** `hoy-390.png` y `hoy-1024.png` (el botón grande), `vacio-tierras-390.png`
(«Traer tierras» junto a «Añadir tierras»), `mas-390.png` (la tarjeta «Ajustes» con la frase
«Abrir la app de siempre») y `tierras-1024.png` (la barra lateral con los tres destinos que
salen). Los `href` están en `mediciones.json`, apartado `enlaces`, que es lo que ha medido
el guion en el DOM.

**Por qué le duele.** El agricultor que abre la app nueva y pulsa el botón más grande de la
pantalla **cambia de programa sin haber hecho nada malo**: otra cabecera, otros botones, otro
aspecto. No sabe si ha hecho algo que no debía. Y en «Mis tierras» vacío tiene dos botones
para lo mismo —traer tierras— que hacen cosas distintas: uno abre la pantalla nueva de alta,
el otro se va a la vieja. Elegir mal no es un problema estético: es tener que empezar otra
vez en un sitio que no conocía. En el ordenador, además, tres entradas del menú parecen
secciones de esta aplicación y son puertas a la otra.

**Arreglo propuesto.**
1. **Un botón, un sitio.** El botón principal de «Hoy» tiene que abrir la pantalla
   «Apuntar» de la propia app nueva (`ir("apuntar")`), no `/`. El atajo a la app vieja, si
   hace falta durante la migración, se queda como un enlace secundario y **con un rótulo que
   lo diga** («Abrir el cuaderno de siempre»), separado del resto.
2. **Los destinos que aún no están en `/nuevo/`** (PAC, Documentos, Ajustes, Quién entra) no
   pueden tener el mismo aspecto que las secciones que sí funcionan: van en un grupo
   separado, al final del menú, con una marca visible («todavía en la app de siempre») y un
   texto propio; y en el móvil, en «Más», igual.
3. **En el estado vacío de tierras**, el botón que arregla el vacío es **uno**: «Añadir
   tierras», que abre la pantalla nueva. «Traer tierras» a `/` se retira.
4. **Los textos nuevos a `textos.py`** (y su copia en `modelo.js` mientras la app nueva tenga
   su copia, como exige `test_interfaz_nuevo.py`). Ni una frase de esta lista escrita a mano
   en `app.js`.
5. **Prueba que lo ate**: en `tests_js/nuevo.test.js`, que el botón principal de «Hoy» pide
   `ir("apuntar")`; y en el arnés de navegador, que **ningún botón visible con clase de acción
   principal tiene `href="/"`** salvo los declarados como «salida a la app de siempre».

---

### P2. Textos de programador en la pantalla: «lo resuelve quien desarrolla la aplicación»

**Gravedad: alta.** Arreglo de **texto**.

**Qué pasa.** En «Cuaderno», dentro del aviso ámbar que ocupa la primera pantalla, se lee:

> «Lo que impide presentarlo no depende de ti: **lo resuelve quien desarrolla la
> aplicación**»

Y en «Más», la tarjeta de Ajustes dice, debajo del título: **«Abrir la app de siempre»**. En
el modelo de textos hay más del mismo tipo, que salen cuando una pantalla no está disponible:
«Apuntar **todavía no está en la pantalla nueva**», «El cuaderno **todavía no está en la
pantalla nueva**», «Los productos y abonos **todavía no están en la pantalla nueva**»,
«Aplicar el contorno a una tierra **todavía no está aquí. Prueba más tarde.**».

La doctrina §8 del proyecto lo prohíbe expresamente («la interfaz no habla de cómo está
hecha»), y el guardián que lo vigila (`PALABRAS_DE_PROGRAMADOR` en
`tests/test_interfaz_nuevo.py`) solo mira `token`, `endpoint`, `json`, `fetch`, `undefined`
y `api/`: **ninguna de estas frases la caza**.

**Capturas.** `cuaderno-390.png` y `cuaderno-1024.png` (la frase del desarrollador, en la
primera pantalla, dentro del aviso ámbar) y `mas-390.png` (la frase «Abrir la app de
siempre»). El resto de las frases están medidas en el bloque de textos de `modelo.js`, que es
el que se sirve en `/nuevo/modelo.js`; se citan aquí como deuda del mismo problema, no como
una captura.

**Por qué le duele.** Al agricultor se le está contando un problema de la aplicación, no de
su cuaderno, y con el sujeto equivocado («quien desarrolla la aplicación»). Eso le quita la
confianza justo en el momento en que le están diciendo que **no puede presentar el cuaderno**.
Y «la app de siempre» / «la pantalla nueva» son categorías de quien programa, no de quien
lleva el cuaderno: él tiene una aplicación y un cuaderno, no dos aplicaciones.

**Arreglo propuesto.**
1. **Borrar la frase del desarrollador.** El aviso dice qué pasa y qué puede hacer él:
   «Hay 8 cosas que impiden mandar el cuaderno a la Junta. Seis las tiene que arreglar el
   programa; tú puedes rellenar estas dos. Empieza por esta.» con el botón de la que sí puede.
   Lo que no depende de él se dice **sin nombrar a nadie**: «Esto no puedes arreglarlo tú:
   está pendiente en el programa.»
2. **Sustituir «app de siempre» y «pantalla nueva»** por el nombre de lo que hay dentro:
   «Abrir el cuaderno en la versión anterior», o mejor, la pantalla concreta a la que va.
3. **Las frases «todavía no está en la pantalla nueva»** no se enseñan nunca al agricultor:
   si una pantalla no está, el enlace no se pinta (y se dice en el menú, como en P1), en vez
   de dejar un aviso.
4. **Añadir estas palabras a `PALABRAS_DE_PROGRAMADOR`** (`pantalla nueva`, `app de siempre`,
   `quien desarrolla`, `desarrollador`, `todavía no está en`) para que el guardián las cace
   la próxima vez, con su prueba de que el guardián **puede fallar**.
5. Los textos, en `textos.py` (y su copia), como manda `AGENTS.md` §3.1.

---

### P3. La mitad del texto visible está por debajo del tamaño mínimo legible

**Gravedad: alta.** Arreglo de **maquetación**.

**Qué pasa.** La app usa **13 px** como tamaño de casi todo lo que no es título ni botón, y
en el calendario llega a **10 px**. Medido en el DOM, contando cada nodo de texto visible:

| Pantalla | Textos < 16 px | % del texto de la pantalla |
|---|---|---|
| Hoy | 136 de 267 | **51 %** (133 a 13 px y 3 a 15 px) |
| Mis tierras | 91 de 157 | **58 %** (85 a 13 px) |
| Apuntar | 89 de 157 | **57 %** (76 a 13 px) |
| Trabajos | 89 de 131 | **68 %** (41 a 13 px y 48 a 15 px) |
| Cuaderno | 125 de 354 | **35 %** (124 a 13 px) |
| Calendario | 11 de 45 | 24 % (**1 a 10 px** y 10 a 13 px) |

Son las fechas de los apuntes, el detalle de cada tierra, el municipio, la cuenta del grupo,
las notas de las tarjetas y la marca «Hoy» del calendario. `DESIGN.md` es explícito: **«Por
debajo de 18 px, a partir de los 50 años no se lee»**, y el único texto por debajo del cuerpo
es la **pista (0,95 rem ≈ 15,2 px)**, que «nunca lleva información imprescindible». Aquí hay
13 px llevando información: la fecha del último apunte, qué producto se echó y en qué tierra.

**Capturas.** `hoy-390.png` (fechas y detalle de «Lo último», notas de las tarjetas),
`tierras-390.png` (el detalle «TRIGO BLANDO · Sin mapa» y la cuenta del grupo),
`trabajos-390.png` (el resumen bajo cada cifra) y `calendario-390.png` (la palabra «Hoy»,
de 10 px, debajo del 9). Las cuentas salen de `mediciones.json`, campo `textos_pequenos`.

**Por qué le duele.** El agricultor de 60 años que se pone de pie en la parcela no lee 13 px
ni con el brillo a tope, y menos con el sol de frente: son las fechas y los detalles los que
se pierden. Un cuaderno en el que no se puede leer **cuándo** se apuntó algo sirve menos que
el de papel. Y el botón «A+» de la cabecera no arregla esto: agranda el texto general, pero
no convierte un detalle de 13 px en información legible en el mismo golpe de vista.

**Arreglo propuesto.**
1. **Escala del contrato, sin inventar:** cuerpo 18 px en el móvil y 16 px en el ordenador
   (la densidad de escritorio que ya define `DESIGN.md`); pista **solo** 15,2 px y **solo**
   para lo que no lleva información; los datos que vienen a consultarse —fechas, hectáreas,
   producto, tierra— en cuerpo.
2. **Nada de 13 px ni de 10 px en información.** Si un dato es importante, sube a cuerpo; si
   no lo es, se quita, no se encoge. La marca «Hoy» del calendario pasa a cuerpo (18 px) y
   se refuerza con un borde de 3 px en la celda, no con letra diminuta.
3. **Los rótulos cortos de los botones** (15 px actuales) también suben al tamaño de botón
   del contrato (1,1 rem = 17,6 px).
4. **Medida de aceptación en el arnés**: en `comprobar_el_armazon_nuevo.py`, ninguna hoja de
   texto visible dentro de `.contenido` por debajo de **15,2 px**, y los datos con nombre
   (fecha, hectáreas, producto) por debajo de **16 px** en escritorio / **18 px** en móvil.
   El mismo tipo de medida que ya se usa en `medir_el_contraste.py`.
5. Todo esto vive en `backend/web/nuevo/estilos.css`, en sus tokens, y se refleja en
   `DESIGN.md` si se decide cambiar la escala (hoy no hay que cambiarla: hay que cumplirla).

---

### P4. La opción elegida es ilegible en modo oscuro: 2,48:1

**Gravedad: alta.** Arreglo de **maquetación** (colores y estado).

**Qué pasa.** La app se pinta en oscuro con el sistema en oscuro (el de esta revisión lo
está). En ese modo, la **pestaña elegida** de «Apuntar» («Labor»), el **filtro elegido** de
«Trabajos» («Todos · 36») y el de «Productos» («Productos · 12») se pintan con
`color: rgb(46,125,79)` sobre `background: rgb(36,56,45)`: **2,48:1** de contraste, por
debajo de 3:1 y muy por debajo del **4,5:1** del contrato. En las capturas se ven casi
apagados, como si estuvieran deshabilitados, mientras los no elegidos se leen perfectamente
(blancos). La marca «Hoy» del calendario, además, está a **3,28:1** y a 10 px.

En claro el mismo elemento mide **6,51:1** y se lee bien: el problema es la segunda paleta.

**Capturas.** `apuntar-390.png` y `apuntar-1024.png` (la pestaña «Labor» y el apero «Rodillo»
elegidos), `trabajos-390.png` (el filtro «Todos · 36»), `productos-390.png` y
`calendario-390.png` («Hoy», 10 px). Los contrastes están calculados en
`mediciones.json` a partir de los colores que el navegador tiene puestos de verdad
(`estilos_clave` y `contrastes`), con la fórmula WCAG.

**Por qué le duele.** El estado «ya está elegido» es justo el que tiene que verse de un
vistazo: si no se ve, el agricultor pulsa otra vez la pestaña que ya estaba, o cree que no
hay nada elegido y no sabe por qué no le sale el formulario. En el campo, al sol, un 2,48:1
no se lee: se ve un hueco. Y el contrato prohíbe que el color informe solo: aquí el único
indicio del estado es el color (el borde del botón no cambia).

**Arreglo propuesto.**
1. **Una sola paleta o dos que cumplan.** Lo más simple y lo que dice `DESIGN.md` es **una**:
   la clara del contrato, blanco de fondo y verde oscuro. Si se quiere conservar el modo
   oscuro, sus tokens tienen que dar **≥ 4,5:1** en todos los textos: el estado elegido se
   pinta con fondo `--brand` y texto blanco (no con tinte), que es lo que ya hace el
   `.boton-elegido` del contrato.
2. **El estado elegido, además del color:** un borde de 3 px en el color de marca y la
   palabra que lo diga cuando el control sea una tarjeta (la pieza `tarjeta.js` ya usa
   «ELEGIDA»; la pestaña puede llevar un `aria-pressed` y una marca visible).
3. **El foco y el elegido no pueden compartir sitio sin distinguirse:** el foco del contrato
   es amarillo `#ffd24a`, no el azul `#0b63ce` de la app nueva.
4. **Prueba de aceptación**: la que ya existe en `medir_el_contraste.py` (ningún texto por
   debajo de 3,0 y aviso por debajo de 4,5) aplicada a `/nuevo/` en **los dos modos**; y un
   caso que mida específicamente `.pastilla--activa` y `.calendario__hoy`.

---

### P5. Apuntar empieza por una lista de 64 tierras en una caja con scroll propio

**Gravedad: alta.** Arreglo de **maquetación**.

**Qué pasa.** La pantalla «Apuntar» arranca con el bloque «Tierra»: **64 tierras** metidas
en una caja con **scroll propio**. Medido a 390 px, en el DOM:

- **64** tierras (`[data-apuntar-tierra]`), con su alias completo, su municipio y su «sin
  mapa» cada una;
- la caja enseña **318 px** de alto pero su contenido mide **9.426 px** de scroll;
- la pregunta «Qué quieres apuntar» y las pestañas empiezan en **y = 710** (la ventana mide
  844, y la barra fija inferior ocupa los últimos 64);
- el botón **«Guardar» está en y = 1.198**, fuera de la primera pantalla.

O sea: para apuntar el trabajo de hoy hay que **recorrer con el dedo una lista de 9.426 px**
dentro de una caja, y el formulario —la razón de la pantalla— empieza al borde del primer
pantallazo. No hay buscador de tierra, ni «las últimas», ni mapa que ayude a reconocerla.

**Capturas.** `apuntar-390.png` (la caja con dos tierras y su barra de scroll; las pestañas
asomando al fondo), `apuntar-1024.png` (la misma caja en el ordenador, 200 px para 64
tierras) y `apuntar-lista-de-tierras-390.png` (el estado medido). Los números se midieron con
un guion temporal de CDP contra el mismo servidor (no se deja en el repositorio, porque solo
mide y no forma parte de la aplicación); la lista de tierras y su texto están además en
`mediciones.json`.

**Por qué le duele.** «Apuntar en 30 segundos» es la promesa central del producto (y la
regla 1 de la guía: no pedir lo que la app ya sabe). Con 64 tierras, elegir a ojo en una
caja es la forma más segura de **apuntar el tratamiento en la tierra equivocada**, que es un
error que no se nota hasta que alguien mira el cuaderno. Y de pie, con una mano, hacer scroll
dentro de una caja que a su vez está dentro de una página es de las cosas más incómodas que
hay en un móvil: el dedo mueve la caja cuando quiere mover la página.

**Arreglo propuesto.**
1. **Tierra primero, pero la de verdad:** arriba, **las 3 últimas** tierras usadas (el
   servidor ya sabe cuáles son: los últimos apuntes), con su miniatura y su nombre corto.
2. **Un buscador** («Nombre o municipio») y **«Ver todas»** para el resto, como ya hace
   `mis_cosas`.
3. **El mapa como selector** cuando haga falta: tocar el recinto (la app ya tiene el mapa y
   la ventana del SIGPAC) en vez de leer 64 renglones.
4. La lista larga, si se abre, **no va en una caja con scroll dentro de la página**: se abre
   como pantalla propia (o se despliega y desplaza la página, una sola cosa que mover).
5. **La barra de acciones fija abajo** (como ya hace el asistente de la app vieja:
   `.asistente-acciones`): la pregunta y el botón de seguir/guardar siempre al alcance del
   pulgar, sin depender del scroll.
6. **Medida de aceptación**: en el arnés, con 64 tierras, la primera pantalla de «Apuntar»
   no tiene ninguna caja con `scrollHeight > clientHeight + 1`; el bloque «Qué quieres
   apuntar» empieza por encima de la barra inferior (`top < innerHeight - 64`); y hay
   buscador y tierras recientes.

---

### P6. El cuaderno dice lo que falta, pero el botón «Arreglar» no lo arregla

**Gravedad: alta.** Arreglo de **texto y maquetación**.

**Qué pasa.** «Cuaderno» anuncia **119 cosas** que faltan (8 bloquean el envío, 102 se
pueden rellenar aquí, 17 no) y las lista en secciones con un botón «Arreglar» por cosa. Dos
problemas medidos:

1. **El primer «Arreglar» no lleva donde dice.** La primera sección es «Mis cosas → máquinas
   de echar producto» y su primera falta es «las máquinas con las que echas el producto…,
   con su nº de **ROMA** y la fecha de su última inspección». Su botón «Arreglar» tiene
   `data-que-falta-seccion-destino="productos"` y, al pulsarlo, la aplicación acaba en
   **«Productos y abonos»**, donde **no hay ninguna máquina**: el botón hace lo que no dice.
   (Comprobado en el navegador: `vista=productos`, `titulo=Productos y abonos`; captura
   `cuaderno-arreglar-390.png`.)
2. **Jerga y frases largas repetidas.** El texto de cada falta usa «SIGPAC», «ROMA»,
   «ecorregimen» y «el “P3” del cuaderno», que la guía manda traducir («La referencia del
   SIGPAC» → «los números del papel», «ROMA» → «el registro de la máquina», «ecorregimen» →
   «la ayuda por hacerlo bien»). Y la misma frase de 200 caracteres se repite **64 veces**,
   una por tierra, con el nombre completo de la tierra dentro.

**Capturas.** `cuaderno-390.png` (el aviso de lo que bloquea, la primera sección y su
«Arreglar»), `cuaderno-1024.png` (la lista de las 64 tierras) y
`cuaderno-arreglar-390.png` (a donde se llega después de pulsar «Arreglar»: Productos y
abonos). El `destino` y el resultado están medidos en el DOM.

**Por qué le duele.** La regla 8 de la guía es literal: *«si le dices que le falta algo, le
das el botón que lo arregla»*. Aquí el agricultor pulsa «Arreglar» para lo de las máquinas y
aterriza en una pantalla de productos donde no puede hacer nada: ha perdido el sitio, no ha
arreglado nada y no sabe si ha tocado algo. Y 119 faltas con frases de 200 caracteres, 64 de
ellas casi idénticas, es un muro que no se lee: no sabe por dónde empezar, que es exactamente
lo contrario de «cuaderno guiado».

**Arreglo propuesto.**
1. **El destino se calcula con la pantalla que de verdad lo arregla**, o no hay botón: si la
   máquina se arregla en «Mis cosas → máquinas» de la app vieja, el botón dice **«Arreglar
   en la app de siempre»** (con su estilo secundario y su explicación), no «Arreglar» a
   secas y a otra pantalla. Y si no hay pantalla, el ítem no tiene botón: tiene la frase
   «Esto se arregla fuera de esta pantalla».
2. **Una frase por tipo, no por tierra.** Las 64 tierras con lo mismo se agrupan:
   «64 tierras sin la referencia del SIGPAC ni lo sembrado. Se arreglan en Mis tierras» con
   **un** botón. El detalle, dentro, plegado.
3. **Traducir la jerga** con la tabla de `GUIA_UI_UX.md` §2.1, y los textos nuevos a
   `textos.py` (y su copia en `modelo.js`). «ROMA» → «el registro de la máquina»;
   «ecorregimen» → «la ayuda por hacerlo bien»; «P3» → se explica o se quita.
4. **Enseñar 3 cosas y un enlace**: «Lo primero que puedes rellenar» + 2 más + «Ver las 119»
   dentro. La primera pantalla no puede ser un aviso de 8 bloqueos y 119 cosas.
5. **Prueba que lo ate**: en el arnés, por cada sección del cuaderno con `destino`, al
   pulsar «Arreglar» la vista resultante **es capaz de nombrar la falta** (por ejemplo, el
   bloque de máquinas solo puede llevar a una pantalla que tenga máquinas); y un test del
   modelo que compruebe que `destinoDeLaSeccion("Mis cosas → máquinas de echar producto")` no
   es `productos` si esa pantalla no tiene máquinas.

---

### P7. En «Mis tierras», «sin mapa» se repite en cada fila y se dibuja un cuadro que el contrato prohíbe

**Gravedad: media.** Arreglo de **maquetación y texto**.

**Qué pasa.** Cada tierra sin forma pinta **dos veces** la misma idea: un recuadro
discontinuo con la palabra «sin mapa» a la izquierda, y en el detalle de la fila
«TRIGO BLANDO · **Sin mapa**» (con mayúscula distinta, además). En la captura de «Mis
tierras» a 390 px la expresión aparece **66 veces** contada en el texto visible; en la de
1024, **68**. Además, la cabecera de cada municipio dice «**11 tierras · no consta**» sin
decir qué es lo que no consta (las hectáreas del grupo), y una fila con la superficie vacía
dice solo «no consta» donde las demás dicen «2,6 ha».

`DESIGN.md`, en el componente «Dibujo de la parcela», dice lo contrario del recuadro:
**«Si la parcela no tiene forma (se apuntó a mano), no se dibuja un cuadro: no se pone
nada. Un cuadrado inventado sería peor que no dibujar, porque parecería la parcela.»**

**Capturas.** `tierras-390.png` (las dos filas primeras, con el recuadro «sin mapa» y el
detalle «TRIGO BLANDO · Sin mapa»; la cabecera «11 tierras · no consta») y
`tierras-1024.png` (lo mismo en tabla/lista ancha). Los conteos salen de `mediciones.json`
(`texto` de la pantalla) y coinciden con lo que se ve.

**Por qué le duele.** Con 64 tierras, 66 apariciones de la misma palabra en una pantalla es
ruido: tapa el dato que sí importa (el nombre, las hectáreas, el cultivo) y hace que la lista
parezca rota. Y «no consta» a secas, sin decir qué falta, obliga a adivinar: ¿no consta la
superficie, el uso o el mapa? El agricultor necesita que le digan **qué** no consta y **dónde**
se arregla, no una palabra repetida.

**Arreglo propuesto.**
1. **Quitar el recuadro** cuando no hay forma, como manda `DESIGN.md`: en su sitio, nada (la
   fila se alinea sin hueco). Si hace falta el aviso, va **una vez** en el detalle de la
   fila: «Sin forma en el SIGPAC» → traducido («Sin el dibujo del mapa»).
2. **Un solo nombre para lo mismo** (regla de la guía: si se llama «parcela» en una pantalla,
   se llama «parcela» en las cuarenta y una restantes): «sin mapa» o «sin dibujo», pero no
   las dos y con la misma mayúscula.
3. **La cuenta del grupo dice qué cuenta**: «11 tierras · superficie sin constar (4)», y en
   la fila, «sin constar» en el mismo sitio donde las demás llevan «2,6 ha».
4. **Medida de aceptación**: en el arnés, con una finca de 64 tierras y 57 sin forma, no hay
   ningún nodo de texto que sea exactamente «sin mapa» dentro de una miniatura, y «sin mapa»
   aparece como mucho una vez por fila; la cabecera de grupo nunca termina en «· no consta»
   sin decir de qué.

---

### P8. En «Añadir tierras» y en el SIGPAC, los códigos van sin ayuda y la fecha del mapa se corta y se contradice

**Gravedad: alta.** Arreglo de **texto y maquetación**.

**Qué pasa.** La pantalla de alta pide, en una rejilla de dos columnas, **Provincia,
Municipio, Agregado, Zona, Polígono, Parcela y Recinto (opcional)**. De todos ellos, la única
ayuda es una línea general («Los números del papel de la parcela. Con eso sale la lista de
recintos»); **«Agregado» y «Zona» no tienen ni una palabra** que diga qué son, y vienen
rellenos con un `0` que el agricultor no ha elegido. La ventana del SIGPAC repite
«Agregado», «Zona», «Polígono» y «Parcela» con el mismo hueco de ayuda. La guía pide
justamente lo contrario: «nunca pedirle que se sepa un código de memoria» y ayuda en cada
campo que pide un dato que no es obvio.

Y en la ventana del SIGPAC, el desplegable de la provincia del mapa dice, en el ordenador,
**«SALAMANCA · 2026 · válido hasta 15/12/2025»**: un mapa de la campaña 2026 con una fecha de
validez **ya pasada**. En el móvil (390 px) ese mismo texto se **corta**: se lee «SALAMANCA ·
2026 · válido hasta 15/…», así que ni siquiera se puede leer la fecha.

**Capturas.** `alta-390.png` (la rejilla de siete campos, con «Agregado» y «Zona» a 0 y sin
ayuda), `alta-1024.png` (el mapa dentro de la pantalla y la rejilla debajo),
`sigpac-390.png` (la fecha cortada en «15/…») y `sigpac-1024.png` (la fecha completa, con la
contradicción 2026 / 15/12/2025). Las dos cosas se ven en la captura; además, el texto del
`<select>` está medido en `mediciones.json`.

**Por qué le duele.** «Agregado» y «Zona» son vocabulario del SIGPAC, no del agricultor: si
no sabe qué son, o deja el 0 (que puede estar mal) o abandona el alta. Y la fecha del mapa es
la que le dice **si el dibujo que va a traer es del año que cree**: ver «2026» y «válido hasta
2025» a la vez, o ver la fecha cortada, es no poder fiarse de lo que va a aceptar. El alta es
la puerta de entrada de todo lo demás: si aquí se pierde, no hay cuaderno.

**Arreglo propuesto.**
1. **Cada campo, con su ayuda de `textos.AYUDA`** (la guía §3.7: qué es, por qué te lo piden,
   un ejemplo y qué pasa si falta). «Agregado» → «El número que va delante del polígono en el
   papel. Casi siempre es 0.» «Zona» → «El número de zona del papel. Casi siempre es 0.»
2. **Los campos que casi nadie necesita, detrás de «Más datos»** (agregado y zona), y los
   que sí: provincia y municipio (eligiendo de la lista, como ya se hace en otros sitios) y
   polígono, parcela y recinto con su ejemplo encima.
3. **La fecha del mapa, en su propia línea y completa**: «Mapa de Salamanca de 2026. Válido
   hasta el 15/12/2025.» Y si la fecha ya pasó, decirlo y dar la salida: «Este mapa está
   caducado. No se puede usar para poner contornos; hay que traer el del año.» Nada de un
   `<select>` que corta la frase: el dato va en una tarjeta o en una línea de texto, y el
   selector solo lleva el nombre de la provincia.
4. **La contradicción se arregla en el servidor, no en la pantalla**: el año que se enseña y
   la validez tienen que ser el mismo hecho. Mientras no se sepa, no se enseña la fecha (dato
   en blanco, nunca inventado).
5. **Medida de aceptación**: en el arnés, a 390 px el texto de la validez del mapa no está
   recortado (se lee entero) y ningún campo del alta está sin su ayuda asociada.

---

### P9. En «Hoy», las tarjetas dicen «no consta» dos veces y lo que falta no tiene botón

**Gravedad: media.** Arreglo de **texto y maquetación**.

**Qué pasa.** La primera pantalla de la app enseña tres tarjetas de cifras. En la de
**Ventas** se lee «no consta» **dos veces** (como cifra y como nota): no se sabe si es que no
hay ventas, si no se han podido leer o si falta algo. En la de **Gastos**, la cifra
«2.868,2 €» y la nota «quedan 2.868,2 € por pagar» repiten el mismo importe. En la de
**Cuaderno**, la cifra «faltan 119 cosas» y la nota «Falta para el cuaderno» dicen lo mismo
dos veces de dos maneras. Y debajo, la tarjeta «Falta para el cuaderno» lista las faltas con
su «dónde se arregla» en gris («Mis datos → tu finca», «Mis cosas → aplicadores», «Mis
parcelas») **sin un botón por falta**: la única salida es un enlace al final que abre la app
vieja.

**Capturas.** `hoy-390.png` y `hoy-1024.png` (las tres tarjetas y el comienzo de «Falta para
el cuaderno», con «el nº de registro de la explotación (el «0837267320»…)» y
«Mis datos → tu finca» debajo). El texto y los enlaces están en `mediciones.json`; la
ausencia de botones, comprobada contando los controles de esa tarjeta en el DOM. La misma
familia aparece en **Productos y abonos**: `productos-390.png` y `productos-1024.png` enseñan
**12 filas** con «Dosis máxima: no consta» y un botón «Apuntar en una tierra» que no sirve
para poner la dosis que falta: el dato que la pantalla promete (la dosis máxima) no tiene
puerta en ninguna parte.

**Por qué le duele.** La pantalla de «Hoy» es la que se mira de pie y con prisa: si una
tarjeta dice «no consta» dos veces, el agricultor no sabe si tiene que hacer algo; si le
dicen «faltan 119 cosas» y no hay un botón al lado, se queda mirando una lista que no puede
resolver. La regla 8 de la guía y `DESIGN.md` lo prohíben: un aviso sin el botón que lo
arregla es un abandono.

**Arreglo propuesto.**
1. **Una frase por tarjeta, con su acción**: «Ventas: este año no has apuntado ninguna
   venta.» + botón «Apuntar una venta» (o «Ver lo que he vendido»). «Gastos: 2.868,2 €
   apuntados, todos por pagar.» + «Ver las cuentas». «Cuaderno: faltan 119 cosas.» + «Ver qué
   falta» (que ya existe).
2. **No repetir el dato**: si la cifra y la nota dicen lo mismo, se quita la nota; si no hay
   dato, se dice **por qué** y **qué hacer**, no «no consta» dos veces.
3. **En «Falta para el cuaderno» de Hoy, 3 cosas como máximo, cada una con su botón** (el
   mismo «Arreglar» del cuaderno, ya corregido en P6) y «Ver las 119» al final. La primera
   pantalla no es el sitio para una lista de 119.
4. Los textos a `textos.py`; nada de «Mis datos → tu finca» en gris sin puerta.

---

### P10. El resumen de «Trabajos» suma dosis por hectárea y las presenta como un total

**Gravedad: media.** Arreglo de **texto (y del cálculo que se enseña)**.

**Qué pasa.** La cabecera de «Trabajos» dice «**36 trabajos · 162,99 ha · 325,35 kg/ha**».
El tercer número es la **suma de las dosis por hectárea** de los trabajos (kg/ha + kg/ha),
que no es una cantidad que exista: nadie ha aplicado 325 kg en cada hectárea. En el resumen
por tipo se repite: «Tratamiento 27 — 27 trabajos · 119,25 ha · **325,35 kg/ha**». El código
lo hace a propósito por unidad (`totalesDeTrabajos` suma por unidad y no mezcla kg con L),
pero **sumar magnitudes «por hectárea» es mezclar peras con manzanas**: la unidad está, pero
el total no significa nada.

Además, el botón «Descargar» no dice **qué** descarga ni en qué formato, y los filtros de
tipo («Tratamiento · 27», «Abonado · 3»…) son «pastillas» cuyo estado elegido tiene el
contraste de P4.

**Capturas.** `trabajos-390.png` y `trabajos-1024.png` (la cabecera con los tres números y
las tarjetas por tipo con «325,35 kg/ha»). El texto está en `mediciones.json`; los totales
los calcula `modelo.js` (`totalesDeTrabajos`).

**Por qué le duele.** Un agricultor que lea «325,35 kg/ha» puede creer que ha echado 325 kg
en cada hectárea, y eso es un dato con consecuencias (dosis, plazos, abono). Un total que no
es un total es peor que no ponerlo: el número está bien formateado, con su unidad, y por eso
mismo se cree. Y «Descargar» sin decir el formato obliga a pulsar a ciegas, que es justo lo
que no se hace con el móvil en una mano y sin cobertura.

**Arreglo propuesto.**
1. **No sumar lo que está «por hectárea»**: los totales de la cabecera solo suman magnitudes
   absolutas (trabajos, hectáreas, kg, L, horas). La dosis se enseña como **media o rango**
   («dosis media 12,05 kg/ha») o no se enseña. Regla: si la unidad lleva «/ha», no se suma.
2. **En el resumen por tipo**, lo mismo: «27 trabajos · 119,25 ha» y, si acaso, «dosis entre
   X y Y kg/ha».
3. **«Descargar CSV»** (o el formato que sea) y la frase «lo que está filtrando, no todo»,
   que es lo que el contrato pide para exportar.
4. **Un test del modelo** que compruebe que ningún total de la pantalla tiene una unidad con
   «/ha»; y otro que compruebe que dos unidades distintas no se suman (ya existe el
   segundo, se amplía con el primero).

---

## 3. Tabla resumen

| # | Problema | Pantalla | Gravedad | Arreglo |
|---|---|---|---|---|
| P1 | Botones grandes y entradas del menú que sacan de la app sin avisar; dos botones iguales con destinos distintos | Hoy, Mis tierras (vacío), Cuaderno, Más, barra lateral | **Alta** | Maquetación + texto |
| P2 | Textos de programador en pantalla («lo resuelve quien desarrolla la aplicación», «app de siempre», «pantalla nueva») | Cuaderno, Más (y estados no disponibles) | **Alta** | Texto |
| P3 | El 35–68 % del texto visible está por debajo de 16 px (13 px dominante; 10 px en el calendario) | Todas | **Alta** | Maquetación |
| P4 | La opción elegida es ilegible en modo oscuro (2,48:1) y «Hoy» en el calendario (3,28:1) | Apuntar, Trabajos, Productos, Calendario | **Alta** | Maquetación |
| P5 | Apuntar empieza por una caja con 64 tierras y 9.426 px de scroll; el formulario y «Guardar» quedan fuera | Apuntar | **Alta** | Maquetación |
| P6 | El cuaderno lista 119 faltas con jerga y el primer «Arreglar» lleva a una pantalla donde no se arregla | Cuaderno | **Alta** | Texto + maquetación |
| P7 | «sin mapa» 66 veces y un recuadro que `DESIGN.md` prohíbe; «11 tierras · no consta» sin decir qué | Mis tierras | Media | Maquetación + texto |
| P8 | Códigos «Agregado» y «Zona» sin ayuda; fecha del mapa cortada y contradictoria (2026 / 15/12/2025) | Añadir tierras, Ventana del SIGPAC | **Alta** | Texto + maquetación |
| P9 | Tarjetas de «Hoy» con «no consta» duplicado y «Falta para el cuaderno» sin botón por falta | Hoy | Media | Texto + maquetación |
| P10 | «Trabajos» suma dosis por hectárea y las presenta como total; «Descargar» sin formato | Trabajos | Media | Texto + cálculo |

**Regla que comparten los diez arreglos:** nada de sombras, degradados, transparencias ni
animaciones; el color nunca informa solo; todos los textos que lee el agricultor van a
`textos.py` (y su copia en `modelo.js` mientras la app nueva tenga copia, con las pruebas que
atan las dos); y cada arreglo se comprueba con una medida en el arnés de navegador, no a ojo.

---

## 4. Lo que está bien (para no leer esto como si todo fuera mal)

- **No hay scroll horizontal** en ninguna de las 32 capturas (0 px en móvil; −15 px en el
  ordenador, que es la barra de scroll).
- **Ningún `button`, `a`, `input`, `select` ni `textarea` visible por debajo de 44 px** en
  toda la página, incluidas la barra inferior y la lateral.
- **Ningún nodo de texto del contenido se recorta con puntos suspensivos** (0 casos con
  `overflow: hidden`). Sí se cortan dos **valores de campo**, que no son nodos de texto: la
  fecha del mapa en el `<select>` de la ventana del SIGPAC (P8) y el nombre completo dentro
  del campo editable «Nombre» de la ficha de una tierra (el campo se desplaza al escribir,
  pero el nombre entero no se puede leer de un vistazo).
- **Los cuatro estados existen** (vacío capturado en `vacio-tierras-390.png`); los estados de
  cargando, error y sin permiso son los mismos que ya recorre el arnés del repositorio, y no se
  han forzado en esta revisión de capturas.
- **La luz y el orden de la lista de tierras** (agrupada por municipio, con el mapa al lado en
  el ordenador) funcionan y son legibles.
- **En modo claro, el contraste cumple** en todo lo medido (7,31:1 el texto secundario,
  5,41:1 las cifras, 6,51:1 la opción elegida).
- El mapa de la finca se carga de verdad y las tierras se pueden elegir en él; la ficha de
  una tierra enseña sus datos y su historial.

---

## 5. Lo que no se ha podido comprobar, y la limpieza

- **No se ha mirado la app vieja (`/`)**: esta revisión es de `/nuevo/`, como pide el
  encargo. Las pantallas que solo existen en `/` están declaradas en §1.2.
- **No se han capturado** las pestañas «Abono» y «Siembra» de «Apuntar», la pestaña «Abonos»
  de «Productos», ni el flujo de leer una factura de verdad (hace falta una foto de una
  factura real; el arnés del repositorio ya lo recorre con una foto sintética).
- **No se ha probado sin cobertura** (el arnés tiene otro recorrido para eso): aquí se mide
  la pantalla con datos y con la sesión puesta.
- **El estado oscuro no se ha impuesto desde la app**: se ha capturado con el sistema en
  oscuro, y en claro a propósito, para comparar. Si el producto va a tener modo oscuro, el
  P4 hay que arreglarlo en sus tokens; si no, se quita y queda la paleta del contrato.
- **Limpieza**: el uvicorn de 8091 se ha apagado al terminar; el puerto queda libre; los
  Chrome del arnés se cierran solos por perfil (no se ha dejado ninguno vivo); la base y los
  adjuntos estaban en `%TEMP%` y no en el repositorio.

---

## 6. Los arreglos de la revisión móvil (10/11/2026)

La revisión de arriba decía lo que estaba mal. Esto es lo que se ha arreglado, con las
mismas medidas antes y después, y lo que sigue pendiente. Se ha hecho **sin compilación**
(React UMD + htm, como manda `docs/REACT.md`), **sin dependencias nuevas** y **sin tocar**
`backend/app/main.py`, `deploy/` ni los documentos de despliegue.

### 6.1. Cómo se ha medido (y cómo se repite)

Servidor temporal en **8094** (base y adjuntos en `%TEMP%`, `CUEDIGITAL_SECRETO` de pruebas,
`CUEDIGITAL_ENTORNO=pruebas`, `CUEDIGITAL_ITERACIONES_PBKDF2=100000`) con la misma explotación
de volumen de `datos_representativos.py` (64 tierras en 5 municipios, 12 productos…), y el
guion **`backend/scripts/capturar_la_revision_movil.py`** (nuevo; solo abre, pulsa, mide y
guarda: no cambia nada de la aplicación):

```powershell
cd backend
..\.venv\Scripts\python.exe scripts\capturar_la_revision_movil.py http://127.0.0.1:8094 --momento antes
..\.venv\Scripts\python.exe scripts\capturar_la_revision_movil.py http://127.0.0.1:8094 --momento despues
```

Por cada pantalla y por cada ancho (**360×640, 390×844, 768×1024 y 1024×900**) hace tres
cosas, y las tres se guardan en `mediciones-antes.json` / `mediciones-despues.json`:

1. **Llega pulsando** (destinos de la barra, pestañas, filtros) y espera a que la pantalla
   tenga sus datos: una foto de «cargando» no vale. En la ventana del SIGPAC **busca de
   verdad** por la referencia `37:70:0:0:503:51`, así que las capturas enseñan el recinto
   dibujado sobre la ortofoto (si no hubiera cobertura, el documento y el JSON lo dirían).
2. **Mide en el DOM**: desborde horizontal de la página; alto y ancho de **cada** control con
   `getBoundingClientRect` (incluidos los que se tocan por su etiqueta: casillas y campos de
   fichero); huecos entre acciones del mismo grupo; la caja de un modal contra la ventana, su
   scroll interno y su «Cerrar»; tablas (¿se desplazan en su caja o estiran la página?);
   `type`/`inputmode`/`enterkeyhint` de cada campo; y el tamaño de letra de cada hoja visible.
3. **Toca el mapa de verdad**: busca un punto del trazo, pregunta al navegador **quién recibe
   el dedo** (`elementFromPoint`), y en «Mis tierras» lanza el clic y comprueba que **abre la
   ficha de esa tierra**; en la ventana del SIGPAC, que el recinto queda elegido.

Las pantallas medidas son 14 (15 en el móvil, con el estado vacío): Hoy, Mis tierras y el
mapa, ficha de una tierra, Apuntar (labor), Apuntar tratamiento **con el formulario abierto**,
Añadir tierras por referencia, **ventana del SIGPAC con el recinto buscado**, Cuaderno
guiado, Productos y abonos, Calendario, Trabajos, **lista de tratamientos** (el filtro de
Trabajos), Facturas, Más y el estado vacío de tierras.

### 6.2. La tabla de los cuatro anchos

**Antes → después.** En los cuatro anchos: **0 desbordes** (el −15 px del ordenador es la
barra de scroll del navegador, que no es desborde: el guion lo cuenta como 0), **0 controles
por debajo de 44 px**, **0 acciones principales por debajo de 48 px**, **0 ventanas que no
caben** y **0 mapas sin zona de toque**.

| ancho | pantallas | desborde (px) | controles < 44 px | acciones < 48 px | huecos < 8 px | ventanas que no caben | mapas sin zona de toque | letra mínima |
|---|---|---|---|---|---|---|---|---|
| **360** | 14 | 0 → 0 | **30 → 0** | 0 → 0 | **5 → 0** | 0 → 0 | **1 → 0** | **10 → 15,2 px** |
| **390** | 14 | 0 → 0 | **30 → 0** | 0 → 0 | **5 → 0** | 0 → 0 | **1 → 0** | **10 → 15,2 px** |
| **768** | 13 | 0 → 0 | 0 → 0 | 0 → 0 | **135 → 0** | 0 → 0 | **1 → 0** | **10 → 15,2 px** |
| **1024** | 13 | 0 → 0 | 0 → 0 | 0 → 0 | **135 → 0** | 0 → 0 | **1 → 0** | **10 → 15,2 px** |

Los 30 controles pequeños de 360/390 eran **las celdas del calendario** (38,6 px de ancho a
360 y 42,9 a 390: menos que un dedo). Los 135 huecos de 768/1024 eran **los renglones del
menú lateral** (4 px) más las celdas del calendario. Y el mapa sin zona de toque es el de
«Mis tierras»: sus anillos tenían 2 px de trazo y no había detrás los 60 px del SIGPAC.

Comprobaciones de la misma medida que sí se pueden citar como «ya estaban bien»: el desborde
horizontal era 0 en las 56 capturas del antes y sigue siendo 0 en las 56 del después; no hay
ninguna acción principal por debajo de 48 px antes ni después; y las dos ventanas del SIGPAC
(alta y ficha) ya cabían con su scroll interno y su «Cerrar» de 48 px.

### 6.3. Los diez problemas, uno por uno

**P3. La mitad del texto, por debajo del mínimo legible — ARREGLADO (maquetación).**
Había **25 reglas a 13 px**, tres a 10 px y trece a 15. Ahora el suelo es la **pista del
contrato (0,95 rem = 15,2 px)** y lo que lleva datos —fechas, hectáreas, producto, tierra,
municipio y la cuenta de cada grupo— **hereda el cuerpo** (19 px en el móvil, 17 en el
ordenador). La marca «Hoy» y la cuenta del día pasan de 10 a 15,2 px, y el título de pantalla
baja de 32 a **24 px (1,5 rem)** en el móvil, que es el tamaño del contrato: con 32, el nombre
largo de una tierra se comía cuatro renglones antes del mapa. Las tablas suben de 14 a 16 px.
*Evidencia*: `antes-hoy-390.png` / `despues-hoy-390.png`, `antes-calendario-360.png` /
`despues-calendario-360.png`, `antes-cuaderno-390.png` / `despues-cuaderno-390.png` y la
columna «letra mínima» de la tabla. **Coste: 3 h.**

**P4. La opción elegida, ilegible en modo oscuro — ARREGLADO (maquetación).**
El estado elegido (pestaña de «Apuntar», filtros de «Trabajos» y «Productos», renglón del
menú) se pinta como el `boton-elegido` del contrato: **fondo verde de marca y texto blanco**
(5,05:1 en oscuro y 8:1 en claro) con **borde de 3 px**, así que el color no va solo. La marca
«Hoy» y la cuenta del día usan el verde claro en oscuro (de 3,29:1 a 8,0:1). No se ha cambiado
ningún token de `DESIGN.md`: se usan los que ya existen (`primary`/`on-primary`, el par del
botón elegido) y un `--brand-bright` que ya estaba en la paleta de la app nueva.
*Evidencia*: `antes-apuntar-360.png` / `despues-apuntar-360.png`,
`antes-trabajos-360.png` / `despues-trabajos-360.png`, `antes-calendario-360.png` /
`despues-calendario-360.png`; el contraste se calcula en `mediciones-*.json`.
**Coste: 1,5 h.**

**P5. «Apuntar» empieza por una caja de 64 tierras con scroll propio — PARCIAL.**
Hecho: **un buscador de tierra** (nombre o municipio, arriba, con la tierra ya elegida siempre
a la vista) y **fuera el scroll anidado**: con 64 tierras se desplaza la página, una sola cosa
que mover, en vez de una caja dentro de otra. Pendiente: las **3 últimas tierras usadas**, el
**mapa como selector** y la **barra de acciones fija abajo** (necesitan datos del servidor y
textos nuevos). *Evidencia*: `antes-apuntar-390.png` / `despues-apuntar-390.png`;
`antes-apuntar-tratamiento-390.png` / `despues-apuntar-tratamiento-390.png`.
**Coste: 2 h (hecho) + 3 h (pendiente).**

**P7. El cuadro «sin mapa» repetido 66 veces — PARCIAL.**
Hecho: **el recuadro discontinuo ya no se pinta** —`DESIGN.md` prohíbe el cuadro inventado— y
la falta se dice **una sola vez**, en el detalle de la fila: la lista de 64 tierras deja de
tener 66 «sin mapa» y la fila se alinea sin el hueco. Pendiente: que la cabecera del grupo
diga **qué** no consta («11 tierras · superficie sin constar») en vez de «· no consta»; es
texto y toca `textos.py`. *Evidencia*: `antes-tierras-360.png` / `despues-tierras-360.png`
(el recuadro discontinuo de la primera fila ya no está).
**Coste: 1 h (hecho) + 1 h (pendiente).**

**P8. Códigos y fecha del mapa — PARCIAL (la parte de teclado y maquetación).**
Hecho: la referencia del SIGPAC se escribe con **teclado de números con separador**
(`type="tel"` + `inputmode="decimal"`: sin el `inputmode`, en un iPhone no se puede escribir
`37.70.0.0.503.51`), los códigos del alta y de la ventana piden **teclado numérico**, y los
buscadores dicen **qué hace la tecla de enviar** (`enterkeyhint`). La ventana del SIGPAC
entra entera a 360 y a 390 (ocupa 360×640 y 390×844 exactos, con scroll dentro y «Cerrar» de
48 px). Pendiente: la **ayuda de «Agregado» y «Zona»** y la **fecha del mapa que se corta y se
contradice** (2026 / válido hasta 15/12/2025): son texto y un dato del servidor, no
maquetación. *Evidencia*: `antes-sigpac-360.png` / `despues-sigpac-360.png` y los `campos`
de `mediciones-despues.json`. **Coste: 1 h (hecho) + 2 h (pendiente).**

**Mapas que dejan interactuar (encargo 5) — ARREGLADO (maquetación).**
El mapa de «Mis tierras» tenía **2 anillos visibles y 0 zonas de toque**: el trazo mide 2 px y
el dedo no acierta. Ahora cada tierra lleva detrás el mismo camino con **60 px de trazo
invisible** (`data-mapa-toque`), y las que solo tienen centro llevan un círculo de 30 px de
radio; el trazo visible y las etiquetas se pintan encima. En la ventana del SIGPAC las zonas
ya estaban; se les ha puesto el mismo enganche para medirlas. **Medido tocando de verdad**: el
punto del trazo recibe el `path`, y el clic **abre la ficha de esa tierra** en 360, 390, 768 y
1024; en la ventana del SIGPAC, el clic deja el recinto elegido. Nada tapa el lienzo
(`tapados: 0`). *Evidencia*: `antes-tierras-390.png` / `despues-tierras-390.png`,
`antes-sigpac-390.png` / `despues-sigpac-390.png` y el bloque `mapa.toque` del JSON.
**Coste: 2 h.**

**Tablas que se rompen (encargo 3) — ARREGLADO (maquetación).**
Las dos tablas de la ficha (otros años y comparativa) se desplazan **dentro de su caja** y la
primera columna se queda fija; ninguna estira la página (`estira_la_pagina: false` en los
cuatro anchos). La de «otros años», que era la única sin caja, ya la tiene.
*Evidencia*: `antes-tierra-360.png` / `despues-tierra-360.png` y `tablas` del JSON.
**Coste: 1 h.**

**P1, P2, P6, P9 y P10 — NO se han arreglado en esta pasada.**
No son de maquetación y tienen su propio frente: P1 (destinos y botones que salen de la app),
P2 (textos de programador), P6 (el «Arreglar» del cuaderno y la jerga), P9 (tarjetas de «Hoy»
con «no consta» duplicado) y P10 (sumar dosis «por hectárea»). En las capturas del después
se ven tal cual: el botón «Empieza por el cuaderno» y el aviso ámbar del Cuaderno
(`despues-cuaderno-390.png`), y el resumen de «Trabajos» con «325,35 kg/ha»
(`despues-trabajos-360.png`). **Coste estimado de lo que queda: 2 h, 2 h, 3 h, 2 h y 2 h.**

### 6.4. Lo que sigue pendiente, en una lista

1. P5: las 3 últimas tierras, el mapa como selector y la barra de acciones fija al pulsar.
2. P7: la cabecera del grupo diciendo qué no consta (texto en `textos.py`).
3. P8: la ayuda de «Agregado» y «Zona» y la fecha del mapa (texto y dato del servidor).
4. P1, P2, P6, P9 y P10, cada uno con su arreglo de texto, destino o cálculo.
5. **La app sigue sin direcciones por pantalla** (§1.2): no se puede compartir un enlace a una
   tierra ni volver a la misma pantalla al recargar. No es de esta pasada, pero sigue ahí.

### 6.5. Ficheros, pruebas y limpieza

**Ficheros tocados en esta pasada**

- `backend/web/nuevo/estilos.css`: suelo de letra (0,95 rem; los datos heredan el cuerpo),
  estado elegido con fondo de marca y texto blanco, huecos de 8 px en el menú y en la rejilla
  del calendario, tarjeta del calendario a sangre en el móvil (44,3 px por celda a 360),
  zonas de toque de 60 px en el mapa, caja que desplaza la tabla de «otros años», lista de
  tierras de «Apuntar» sin scroll anidado, y sin el recuadro «sin mapa».
- `backend/web/nuevo/app.js`: buscador de tierras en «Apuntar»; miniatura que no se pinta
  cuando la tierra no tiene forma; zonas de toque en el mapa de «Mis tierras» (con
  `data-mapa-toque`); tabla de «otros años» dentro de su caja; celdas del calendario con la
  cuenta del día y el nombre completo en `aria-label`; `type="tel"` +
  `inputmode="decimal"`/`"numeric"` y `enterkeyhint` en los campos que lo piden.
- `backend/scripts/capturar_la_revision_movil.py`: **nuevo**. El guion de capturas y medidas
  del antes y del después (14 pantallas × 4 anchos, con la ventana del SIGPAC buscando de
  verdad y el mapa tocado de verdad).
- `backend/tests/test_revision_movil.py`: **nuevo**. 29 pruebas que atan los arreglos a los
  números (no a las intenciones) y que leen `mediciones-despues.json` para exigir 0
  desbordes y 0 controles < 44 px.
- `docs/revision-interfaz.md` y `docs/capturas-revision/*.png` + `mediciones-*.json`.
- `README.md`, `AGENTS.md` y `docs/LO_QUE_PIDE_LA_JUNTA.md`: el recuento de pruebas de Python,
  que pasa de 6060 a 6108 porque esta pasada añade 29 (lo exige
  `test_el_numero_de_pruebas_de_python_es_el_de_verdad`, que cuenta lo que recoge `pytest`).
  **No se ha tocado `DESIGN.md`**: los tamaños y colores que se usan ya estaban en el contrato.

**Pruebas** (todas en local, sin red):

- `node --test "tests_js/*.test.js"` — **1319 pruebas, 1319 en verde**.
- `pytest tests/test_revision_movil.py` — **29 pruebas, 29 en verde**.
- `pytest` completo — **6108 pruebas en verde** (las 6060 que había más las 29 de esta
  revisión, más las de los frentes que se entregan el mismo día).
- `pytest tests/test_design_md.py tests/test_interfaz_nuevo.py tests/test_interfaz.py
  tests/test_la_migracion_a_react.py tests/test_sin_jerga.py` — en verde.

**Limpieza**: el uvicorn de 8094 se ha apagado al terminar y el puerto queda libre (se ha
comprobado); no se ha dejado ningún Chrome vivo (el guion cierra por perfil); la base y los
adjuntos estaban en `%TEMP%` y se han borrado; no se ha tocado ningún puerto de otro proyecto
(8080/5432/5433).

---

### Anexo: ficheros de esta revisión

- `docs/revision-interfaz.md` — este documento.
- `docs/capturas-revision/*.png` — 32 capturas (390 y 1024; cuatro en claro; el vacío; dos de
  las comprobaciones concretas).
- `docs/capturas-revision/mediciones.json` — todo lo medido en el DOM, por pantalla y ancho.
- `backend/scripts/capturar_pantallas_para_la_revision.py` — el guion que las hace (solo
  lectura: navega, pulsa, mide y guarda; no cambia la aplicación).
- `docs/capturas-revision/antes-<pantalla>-<ancho>.png` y `despues-<pantalla>-<ancho>.png` —
  56 capturas de cada momento a 360, 390, 768 y 1024 px (§6).
- `docs/capturas-revision/mediciones-antes.json` y `mediciones-despues.json` — lo medido en el
  DOM en cada momento, pantalla por pantalla y con su resumen por ancho (§6).
- `backend/scripts/capturar_la_revision_movil.py` — el guion del antes y del después (§6.1).
- `backend/tests/test_revision_movil.py` — las pruebas que atan los arreglos a sus números.
