# Aceptación: el volumen de verdad y las descargas desde la pantalla

> Lo que el encargo pedía en sus puntos 1 y 2 —**datos representativos (64 tierras)** y
> **exportaciones pulsando el botón**— no estaba hecho: la comprobación del navegador miraba una
> finca de **dos tierras y una campaña**, y las tres exportaciones solo estaban probadas **por la
> API**. Esto es lo que se ha hecho, lo que se ha medido y lo que ha salido.

Fecha de la medición: **7 de octubre de 2026, 00:25** (hora local).
Revisión del árbol: `d7a6d36` (con el árbol **sucio**: otro agente estaba editando `app.js`,
`textos.py` y las pruebas de existencias en el mismo checkout — ver la nota del final).

---

## 0. Resumen en cuatro líneas

| | |
|---|---|
| Comprobaciones **antes** (las de siempre) | **559**, 0 fallos |
| Comprobaciones **ahora** | **661** (559 de siempre + **102 nuevas**), **659 en verde**, **2 fallos** |
| Ficheros nuevos | `backend/scripts/datos_representativos.py` (la preparación) y este informe |
| Fichero ampliado | `backend/scripts/comprobar_en_un_navegador.py` (+798 líneas, **0 borradas**: lo que ya comprobaba sigue igual) |

**Los 2 fallos son hallazgos del programa, no del guion** (§3). Se describen para que los arregle
quien es dueño de esos ficheros: yo no los he tocado.

Y una frase que el encargo pide decir con estas palabras: **no existe ningún botón de exportar en las
pantallas de tierras, papeles, contactos, trabajos, almacén, cuentas ni ventas**; los únicos botones
de exportar o descargar del recorrido son los tres de «mi cuaderno» (los datos, el papel y la Junta),
el del extracto del banco y el de descargar el fichero de un papel (§4.7).

---

## 1. Qué escenario crea la preparación

`backend/scripts/datos_representativos.py` crea **dos explotaciones de usar y tirar** contra el
servidor de pruebas (una nueva en cada vuelta, porque el correo lleva una marca con la hora y el
proceso):

### 1.1 La explotación del volumen

| Qué | Cuánto | Cómo |
|---|---|---|
| Tierras | **64** | nombres de 60 a 81 caracteres (`paraje + ", " + cola`), 8 parajes × 8 colas |
| Campañas | **3** (2024, 2025, 2026) | con cultivos sembrados en las tres, para que «otros años» tenga algo |
| Productos | 12 | |
| Contactos | 20 | |
| Artículos de almacén | 8 | con su lote, una entrada y un ajuste cada uno (**16 movimientos**) |
| Máquinas | 8 | |
| Papeles | **30** | uno con fichero (un PNG de verdad) y 29 sin él |
| Gastos | **40** | repartidos entre 7 categorías |
| Trabajos | 12 previstos + 12 hechos | |
| Tratamientos | 24 | |
| Ventas | 10 | |
| Movimientos del banco | **36** | 30 en la cuenta principal y 6 en la secundaria, importados de un extracto CSV generado |

### 1.2 Los datos incompletos, y por qué

Se dejan a medias **a propósito**, porque es lo que hay que comprobar que la pantalla sabe decir:

| Lo que se deja sin decir | Cuántas | Por qué |
|---|---|---|
| **Superficie** | **9** | Tiene que leerse «Sin hectáreas dichas», **nunca 0,00 ha**: un cero es una afirmación que nadie ha hecho (A7 de `docs/T02_VALORES_POR_DEFECTO.md`) |
| **Forma** (geometría) | **58** | La tierra apuntada a mano no trae el dibujo del SIGPAC; tiene que decirse con palabras («SIN FORMA») y no romper la tabla |
| **Cultivo** | **25** | «Sin decir qué tiene» |
| **Pueblo** | **10** | «Sin pueblo dicho» |
| **Referencia del SIGPAC** | **11** | Sin polígono ni parcela; el cuaderno de la Junta tiene que dejar esas casillas en blanco |
| **Sistema** (secano/regadío) | 32 | `None` es «no lo sé», que es distinto de un secano inventado (A10) |

### 1.3 Lo que se puede buscar y contar (y por qué esos números)

* La búsqueda de la prueba es **«dehesa boyal»** y casa con **8 de las 64** (las del primer paraje).
  El número **lo cuenta el propio módulo** (`Escenario.cuantas_casan`), no se escribe a mano.
* Los cultivos están repartidos **13 / 13 / 13** (TRIGO BLANDO, CEBADA, GIRASOL) y 25 tierras no
  tienen ninguno, así que un filtro por cultivo deja 13 de 64.
* El extracto del banco tiene **10 conceptos con «COSECHERA» de 30**, así que un fichero con los 30
  se distingue de uno con los 10 sin ninguna ambigüedad.

### 1.4 La explotación ajena (y por qué hace falta una segunda cuenta)

Todo lo que crea la segunda finca lleva dentro la marca **«OTRA EXPLOTACION NO DEBE SALIR»** (una
tierra, un gasto, un papel, un contacto, un trabajo, un producto, una cuenta y su movimiento). Es la
única forma de comprobar de verdad que una exportación **no se lleva registros de otro agricultor**:
sin una segunda explotación en la misma base, esa comprobación no se puede hacer.

`preparar()` devuelve un `Escenario` con **los identificadores que ha creado** (los de las tierras,
las campañas, las cuentas, los papeles…). **Ninguna comprobación habla de «la primera tierra»**: todo
lo que se abre, se busca, se marca o se exporta va por el identificador que devolvió el servidor.

---

## 2. Qué se ha comprobado con volumen, en qué anchos y con qué resultado

### 2.1 Las pantallas con lista larga, a los tres anchos del contrato

Se abren con el navegador manejado por el protocolo de depuración (`navegador_cdp.py`), **con la
sesión puesta**, y se mide el ancho **de verdad** de la página contra el ancho **de verdad** de la
ventana. Los tres anchos se consiguen cambiando las métricas del dispositivo (`medir`), no abriendo
otra ventana: así se mide el mismo documento a los tres.

| Pantalla | 390 px | 1024 px | 1440 px | Lo que se comprueba dentro |
|---|---|---|---|---|
| `#/tierras` | cabe | cabe | cabe | «Tienes 64 tierras apuntadas» y los dos alias extremos pintados |
| `#/tierras/mapa` | cabe | cabe | cabe | el pie, la tabla, el mapa, la selección y el agrupado |
| `#/papeles` | cabe | cabe | cabe | 30 papeles, «VER EL PAPEL» (el que tiene fichero) y «SUBIR EL PAPEL» |
| `#/cuentas` | cabe | cabe | cabe | «Tienes 40 gastos apuntados.» y la tabla de gastos |
| `#/cuentas/bancos` | cabe | cabe | cabe | «Tienes 30 movimientos», la pista del alcance y los filtros |
| `#/contactos` | cabe | cabe | cabe | «Tienes 20 fichas apuntadas.» |
| `#/trabajos` | cabe | cabe | cabe | las dos listas (pensado y hecho) con sus botones |
| `#/almacen/libro` | cabe | cabe | cabe | el libro de entradas y salidas |
| `#/cuaderno` | cabe | **SE SALE (1367 de 1024)** | cabe | 36 apuntes, la tabla, y los botones que exportan |
| `#/ventas` | cabe | cabe | cabe | «10 ventas apuntadas · 55.000 kg» y su tabla |

**Encontrado:** «Mi cuaderno» **se sale 343 px por la derecha a 1024 px** con los datos de verdad
(§3.1). A 390 y a 1440 px cabe entera. Es la única de las diez que se sale, y no la medía ninguna
comprobación de las de antes (a 1024 px solo se medían el panel de mando y las pantallas de T06/T10).

### 2.2 El buscador, los filtros, la selección y los recuentos (pulsando de verdad)

Todo esto se hace **pulsando** y se cuenta **lo que la lista pinta**, que es la mitad que hace que un
recuento valga:

| Qué se pulsa | Qué tiene que pasar | Resultado |
|---|---|---|
| Nada (al abrir) | el pie dice **«64 tierras»** y la tabla pinta **64** casillas | ✅ |
| **MARCAR LAS QUE SE VEN** | «Has marcado 64 tierras» y **64 casillas marcadas** | ✅ |
| **QUITAR LA SELECCIÓN** | «No has marcado ninguna tierra.» y **0 casillas** | ✅ |
| La casilla de **una** tierra (por su `data-id`) | «Has marcado 1 tierra» (en singular) y 1 casilla | ✅ |
| La misma casilla otra vez | vuelve a «No has marcado ninguna tierra.» | ✅ |
| **BUSCAR** con «dehesa boyal» | el pie dice **«Ves 8 de 64 tierras»**, la tabla pinta **8** filas, la tierra que **no casa no sale** y la que casa sí | ✅ |
| **QUITAR LOS FILTROS** | vuelven las **64** a la vista (64 casillas) | ✅ |
| Filtrar por **TRIGO BLANDO** | «Ves 13 de 64 tierras», la tabla pinta **13**, y una tierra de CEBADA **no sale** | ✅ |

El buscador casa **sin tildes y sin mayúsculas** (el cotejo de la pantalla) y busca por nombre **y por
referencia del SIGPAC**, que es lo que pide el contrato.

### 2.3 Los nombres largos y los datos incompletos

| Qué | Resultado |
|---|---|
| El alias más largo (**81 caracteres**) se lee entero en la tarjeta y en la tabla | ✅ |
| Ese nombre no rompe la tarjeta a **390 px** (la página no se sale) | ✅ |
| Una tierra **sin superficie** se lee «Sin hectáreas dichas» y **no** «0,00 ha» | ✅ |
| Una tierra **sin cultivo** se lee «Sin decir qué tiene» | ✅ |
| Una tierra **sin forma** se dice con palabras: «SIN FORMA» (no solo con un color) | ✅ |

---

## 3. Los dos hallazgos

> Los dos son del programa, no del guion. **No los he arreglado**: los ficheros de la aplicación no
> son míos. Se describen con lo mínimo para reproducirlos.

### 3.1 «Mi cuaderno» se sale 343 px por la derecha a 1024 px

**Qué pasa.** Con la finca de verdad (64 tierras, 36 apuntes en el año), a **1024 px de ancho** la
página mide **1367 px**: el agricultor tiene que desplazar toda la pantalla a los lados para llegar a
los botones de la última columna. A 390 px y a 1440 px cabe entera.

**Cómo reproducirlo** (medido):

```
# con el servidor de pruebas en el 8021 y una finca con tierras y apuntes:
# abrir http://127.0.0.1:8021/index.html#/cuaderno a 1024 px y mirar:
document.documentElement.scrollWidth   # 1367
window.innerWidth                      # 1024
```

**La causa, medida elemento a elemento** (con `getBoundingClientRect` de todo el documento):

```
TABLE.tabla  right=1367  ancho=1063
```

La tabla de los apuntes **no está dentro del contenedor que se desplaza solo** (`.tabla-scroll`).
Todas las demás tablas del programa sí lo están —`bancos.js:732`, `gastos.js:667`,
`maquinaria.js:273`, `ventas.js:207`, `panel_de_mando.js:114`, `tierras_mapa.js:724`, y la propia
pieza `piezas/tabla.js:232` cuando va con panel—; la de «mi cuaderno» se quedó fuera:

```js
// backend/web/react/pantallas/mi_cuaderno.js:94
apuntes.tabla ? html`<div className="solo-escritorio"><${Tabla} tabla=${apuntes.tabla} /></div>` : null
//                                   ^^^^^^^^^^^^^^^^^^^ le falta `tabla-scroll`, que sí tienen las otras cinco
```

Es el **mismo defecto** que ya se corrigió dos veces (la tabla de la maquinaria de T14 y la del panel
de mando, contadas en los comentarios de `pantallas_estrechas`). No lo he tocado.

### 3.2 El botón del fichero de datos no dice qué se lleva

**Qué pasa.** El botón **«GUARDAR LOS DATOS EN UN FICHERO»** (en `#/cuaderno`) descarga el cuaderno
**entero del año que está abierto**, y **no lo dice en ninguna parte**: ni su etiqueta, ni el bloque
de botones donde vive, ni la pantalla. El encargo lo pide con estas palabras: «verifica el alcance
anunciado: seleccionados, filtrados o todos; si solo permite uno, debe decir cuál».

**Cómo reproducirlo.** Abrir `#/cuaderno`, mirar el bloque de los tres botones de abajo: su texto
entero es

```
🖨️ SACAR EN PAPEL
💾 GUARDAR LOS DATOS EN UN FICHERO
VOLVER
```

y nada más (ni una pista de debajo). El texto que lo explicaba **existe en el servidor** y **no lo
pinta ninguna pantalla**:

```
$ grep -r "datos_pista" backend/web/     # (sin resultados)
backend/app/textos.py:1269:  "datos_pista": "Se abre con Excel. Guárdalo: es tu cuaderno, por si te lo piden",
```

Es decir: es texto muerto (`cuaderno.datos_pista`) y el botón se queda sin decir el alcance. Nótese
que **el hermano sí lo dice**: el bloque de la Junta explica «todo lo que tienes apuntado» y el del
banco dice «lo que estás viendo: con el filtro y la cuenta que tengas puestos» (los dos comprobados
en verde). El del fichero de datos es el único de los cuatro que se calla.

**Matiz, para que no se exagere el hallazgo:** el año está a la vista en la barra («CAMPAÑA 2026») y
el fichero lo dice en su primera línea (`Cuaderno de campo - <explotación> - 2026`), así que nadie va
a equivocarse de explotación. Lo que falta es la frase que diga que el fichero lleva **el año
entero** y no lo que se está viendo (la pantalla enseña los apuntes, no las 25 hojas). Arreglarlo es
pintar la pista que ya está escrita.

---

## 4. Cada exportación: el botón, el fichero y el alcance

Las seis descargas de esta aceptación se hacen **pulsando el botón de verdad** en el navegador y
mirando **el fichero que queda en la carpeta de descargas** (con una carpeta distinta por descarga,
para saber de qué botón es cada fichero). Antes de leerlo se espera a que **deje de crecer**, así que
un `.crdownload` a medias no cuenta como descarga.

### 4.1 El fichero de datos del cuaderno

| | |
|---|---|
| Botón | «💾 GUARDAR LOS DATOS EN UN FICHERO» — `data-accion="sacar-datos"` |
| Pantalla | `#/cuaderno` («Mi cuaderno») |
| Fichero | **`cuaderno_2026.csv`** — 17.531 bytes, 147 líneas |
| Formato | CSV con `;`, con marca de orden de bytes al principio |
| Cabecera | `Cuaderno de campo - La Explotación del Volumen de la Prueba … - 2026` |
| Contenido | **las 64 tierras**, cada una en su fila (comprobadas una a una por su alias) + instalaciones, maquinaria, plan, productos aplicados, abonos, labores y ventas |
| Explotación y campaña | las dos en la primera línea; la campaña es la que está abierta |
| Otra explotación | **no aparece ni una marca de la finca ajena** |
| Alcance anunciado | **ninguno** → **hallazgo §3.2** |
| ¿Lo cumple? | el fichero lleva el cuaderno entero del año; la pantalla no lo dice |

### 4.2 El cuaderno en papel

| | |
|---|---|
| Botón | «🖨️ SACAR EN PAPEL» — `data-accion="sacar-papel"` |
| Pantalla | `#/cuaderno` |
| Fichero | **`cuaderno.pdf`** — 16.662 bytes, empieza por `%PDF` |
| Alcance anunciado | ninguno (mismo caso que §3.2, pero el PDF **es** lo que se está viendo: la pantalla es el cuaderno del año de la barra) |
| ¿Contenido comprobado? | **solo el formato**, no el texto de dentro (ver §5) |

### 4.3 El cuaderno de la Junta

| | |
|---|---|
| Botón | «SACAR MI CUADERNO» — `data-accion="cuaderno-sacar"` |
| Pantalla | `#/cuaderno` (el bloque «Sacar mi cuaderno para la Junta») |
| Fichero | **`cuaderno-de-la-junta.xlsx`** — 27.118 bytes, `PK\x03\x04` (un XLSX de verdad) |
| Formato | se abre con `openpyxl`: **25 hojas**, con sus nombres oficiales («1.1. INF. GRAL», «2.1. DATOS PARCELAS», …) |
| Contenido | el nombre de la explotación y el año en la cabecera de la hoja **2.1** (`Explotación/Titular de la explotación: … · AÑO 2026`); y en esa misma hoja las **53 tierras que tienen referencia**, cada una con su **polígono y su parcela** (53 de 53 comprobadas). La hoja 1.1 sale **en blanco**: son los datos de «Mis datos», que esta finca de prueba no ha rellenado — y eso es lo que la pantalla anuncia («lo que falte sale en blanco, nunca con un dato inventado») |
| Otra explotación | no aparece ninguna marca ajena |
| Explotación y campaña | la explotación y «AÑO 2026», en la cabecera de la hoja 2.1 |
| Alcance anunciado | **sí**: «El programa escribe tu cuaderno con las 25 hojas de la Junta y **todo lo que tienes apuntado**: tus tierras, tus tratamientos, tus abonos, tus análisis y lo que has vendido» |
| ¿Lo cumple? | **sí** |

*(Las tierras van por sus números del SIGPAC y no por el alias del agricultor, y está bien: el
programa de la Junta no conoce los nombres que él les pone. Por eso la comprobación busca polígono y
parcela, no «El Alto de la Dehesa Boyal».)*

### 4.4 El extracto del banco, **sin filtro**

| | |
|---|---|
| Botón | «DESCARGAR EL EXTRACTO» — `data-accion="banco-exportar"` |
| Pantalla | `#/cuentas/bancos` |
| Fichero | **`extracto.csv`** — con cabeceras `Día;Cuenta;Concepto;Entra o sale;Importe;Saldo;Referencia;Estado;Lo que no consta` |
| Filas | **30** (los movimientos de la cuenta que la pantalla tiene puesta, que es la principal) |
| Otra explotación | no aparece ninguna marca ajena |
| Alcance anunciado | **sí**: «Se descarga en un fichero **lo que estás viendo**: con el filtro y la cuenta que tengas puestos» |
| ¿Lo cumple? | **sí** |

### 4.5 El extracto del banco, **con un filtro de 10 entre 30** (la comprobación del encargo)

| | |
|---|---|
| Cómo | se escribe «COSECHERA» en el buscador, se pulsa **BUSCAR** y se pulsa **DESCARGAR EL EXTRACTO** |
| Lo que se ve en pantalla | 10 movimientos |
| Fichero | **`extracto.csv`** |
| Filas | **10** (comprobadas una a una por su concepto) |
| Lo que **no** lleva | **ni uno** de los 20 movimientos que el filtro deja fuera (`GASTO CORRIENTE DE LA NAVE`: 0 apariciones) |
| ¿Lo cumple? | **sí**: el fichero es lo que se está viendo, no los 30 |

Esta es, con las palabras del encargo, la comprobación que faltaba: «un filtro de 10 tierras entre 64
no debe exportar silenciosamente las 64». **Aquí no pasa.** (Nota: el servidor ya aceptaba los
filtros y `app.js` ya los manda; lo que faltaba era **pulsar el botón y mirar el fichero**, y eso es
lo que se ha hecho.)

### 4.6 El fichero de un papel

| | |
|---|---|
| Botón | «VER EL PAPEL» — `data-accion="papel-ver"` |
| Pantalla | `#/papeles` |
| Fichero | **`el-contrato-de-arrendamiento-de-la-finca.png`** — el nombre es el que se subió, y el contenido es **el mismo PNG, byte a byte** |

No es una exportación de una lista, es la descarga del fichero de un papel; se comprueba igual porque
es un botón de descargar.

### 4.7 Botones de exportar que **no existen** en ninguna pantalla del recorrido

Con estas palabras, porque es un dato y no un hueco que se tapa:

> **No hay ningún botón de exportar en las pantallas de tierras (`#/tierras`, `#/tierras/mapa`),
> papeles, contactos, trabajos, almacén, cuentas ni ventas.** Los únicos botones de exportar o
> descargar que existen en el recorrido son los **tres de «mi cuaderno»** (datos, papel, Junta), el
> **del banco** y el **de un papel** de la lista de papeles. Es decir: **no se puede exportar la
> lista filtrada de tierras** a ningún fichero — el filtro de 10 de 64 que nombra el encargo se puede
> ver en pantalla, pero no sacar.

Y dos matices que se han comprobado y que conviene dejar dichos:

* La pantalla **`#/junta`** (`Traer mis tierras del cuaderno de la Junta`) **no exporta nada**: es la
  que **lee** el fichero de la Junta. El botón que exporta (`SACAR MI CUADERNO`) vive en `#/cuaderno`,
  dentro del bloque «Sacar mi cuaderno para la Junta», y **solo aparece cuando hay algo que sacar**
  (el servidor manda si hay hojas con datos). Con la finca vacía ese botón **no existe**.
* El botón de **descargar el informe de un análisis** (`analiticas.js`) no se ha podido pulsar: la
  explotación de la prueba no tiene análisis con fichero. Está en §5.

---

## 5. Lo que NO se ha podido comprobar (y por qué)

| Qué | Por qué |
|---|---|
| **El contenido del PDF** (`cuaderno.pdf`) | se comprueba que es un PDF de verdad (cabecera `%PDF`) y que pesa lo que tiene que pesar, pero **no se lee su texto**: haría falta un lector de PDF y el proyecto no compara textos de PDF en ninguna parte. Lo que va dentro lo cubren la exportación CSV y el XLSX, que sí se leen |
| **El botón de descargar el informe de un análisis** | la explotación de la prueba **no tiene ningún análisis con fichero subido**, así que ese botón no se dibuja. Para comprobarlo haría falta subir un boletín; se ha dejado fuera para no meter en la preparación un fichero PDF de mentira |
| **La pantalla de firmar** (`firmar-descargar`) | necesita un certificado configurado que el servidor de pruebas no tiene: ya estaba declarada como no recorrida en el guion (`NO_SE_RECORREN`) y sigue igual |
| **El cuaderno de la Junta con la finca vacía** | con una finca sin datos ese botón no existe (es correcto: no hay nada que sacar), así que el caso «no hay nada» no se comprueba pulsando |
| **El zoom del navegador al 200 % con volumen** | el ancho al que equivale (720 px) se mide en la sección 4 bis del guion con los datos de siempre, y esa parte no se ha tocado |
| **El modo sin conexión (el service worker)** | ninguna de las comprobaciones de aquí apaga la red. Se probó a arrancar **sin** sesión (que el service worker guarde una respuesta sin permiso) y no se reprodujo ningún fallo, pero no es una comprobación del encargo |

---

## 6. Cómo se repite

```powershell
# 1. Un servidor de pruebas con base temporal y los adjuntos fuera del árbol.
cd F:\EspacioCodigo\CueDigital\backend
$env:CUEDIGITAL_DATABASE_URL="sqlite:///$env:TEMP\cd-volumen.db"
$env:CUEDIGITAL_ADJUNTOS="$env:TEMP\cd-volumen-adjuntos"     # opcional: sin esto, los papeles de
                                                             # prueba van a datos\adjuntos\<explotación>
$env:PYTHONIOENCODING="utf-8"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8021

# 2. La comprobación entera (las 661), desde otra ventana:
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe scripts\comprobar_en_un_navegador.py http://127.0.0.1:8021
```

Y la preparación, sola, para mirar lo que crea y con qué identificadores (tarda un par de minutos:
son unas cuatrocientas peticiones):

```powershell
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe scripts\datos_representativos.py http://127.0.0.1:8021
```

**No se toca la base del agricultor ni su servidor (el 8000).** Todo esto va contra la base temporal
del 8021. El puerto 8013 y el 8022 son de otros agentes y no se han usado.

El servidor de la comprobación **tiene que poder crear cuentas** (la comprobación de siempre ya lo
necesitaba: crea una cuenta de prueba y le mete datos). Si no hay Chrome ni Edge instalado, el guion
lo dice y no falla.

---

## 7. El recuento, con números

| | Antes | Ahora |
|---|---|---|
| Comprobaciones | **559** | **661** |
| En verde | 559 | **659** |
| Fallos | 0 | **2** (los dos hallazgos de §3) |

* Las **559 de siempre siguen en verde**: no se ha tocado ninguna línea de lo que ya comprobaban (el
  cambio en ese fichero son **798 líneas añadidas y 0 borradas**).
* Las **102 nuevas** se reparten así: **72** del volumen (3 de la preparación + 50 de las diez
  pantallas a tres anchos + 19 de búsqueda, filtros, selección y datos incompletos) y **30** de las
  descargas.
* La comprobación del volumen tarda unos **4 minutos** en crear el escenario y otros **3** en
  recorrerlo y descargar (medido en esta máquina).

---

## 8. Nota sobre el árbol compartido

Este checkout lo estaban usando **varios agentes a la vez**. Eso tiene dos consecuencias que conviene
saber al leer estas medidas:

1. **`app.js` cambió mientras se medía.** Las medidas de este informe son del estado del árbol a las
   00:25 del 7/10/2026, con `backend/web/app.js` en
   `E7DC2506EEA92562F5690147DEAE99E08F26EEA18CDD9AF7C59ABFCB4BAA3252` y `mi_cuaderno.js` en
   `FE6B146A0C390FBEEA6B24F6F0C902A93A5A025CCEDA789457BC2EA9FD9FD743`. Si alguien cambia esas
   pantallas, **hay que volver a medir**: es exactamente lo que este guion hace.
2. **Mis dos ficheros acabaron dentro de un commit de otro agente** (`d7a6d36`, «T21: las dos vistas
   de existencias dicen el mismo saldo»), porque ese commit hizo `git add` de todo. No es un problema
   —el trabajo está— pero explica por qué `datos_representativos.py` aparece ya en el historial sin
   que yo haya hecho ningún commit.

Los dos hallazgos de §3 **se han arreglado después de este informe**, por el coordinador (commit
`66b9633`):

* `mi_cuaderno.js` **ya lleva `tabla-scroll`**, como las otras cinco tablas largas.
* El botón **ya dice qué se lleva**: `BotonSencillo` aprendió a llevar pista (como `Boton`) y el botón de
  guardar los datos la lleva con la frase que estaba muerta en el servidor.

**Y se ha vuelto a medir con el árbol de después del arreglo: `661 comprobaciones, 0 fallos`** (el 7/10/2026,
sobre `450ab05`). O sea que los dos fallos de la tabla de arriba están cerrados y la comprobación entera
—las 559 de siempre más las 102 nuevas— está en verde en el árbol de ahora mismo.
