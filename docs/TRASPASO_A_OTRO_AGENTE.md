# Traspaso a otro agente: qué es CUE Digital y qué falta

**Encargo actual para DeepSeek:** empezar por
[CONTRATO_IMPLEMENTACION_CRM.md](CONTRATO_IMPLEMENTACION_CRM.md) y
[MATRIZ_NORMATIVA_CRM.md](MATRIZ_NORMATIVA_CRM.md). Ejecutar T01–T04 primero;
no rehacer toda la aplicación de una vez ni activar reglas legales sin su revisión.

> Este fichero existe para que otro agente (o una persona) pueda entender el proyecto sin
> haber estado dentro. Si vas a tocar código, lee antes `AGENTS.md`: es el convenio de trabajo
> y manda sobre este fichero. Para el detalle del volcado oficial, `docs/INTEGRACION_IUWS.md`.

> **⚠️ Este documento es del 23/09/2026 y sus números están viejos.** Para el encargo nuevo de
> gestión integral, lee [`PLAN_CRM_AGRARIO_2026.md`](PLAN_CRM_AGRARIO_2026.md) (01/10/2026):
> separa lo comprobado de lo proyectado y ordena el trabajo para otros agentes. Para la historia
> del escritorio y Stitch, consulta [`RESUMEN_PARA_CHATGPT.md`](RESUMEN_PARA_CHATGPT.md), que es una
> fotografía del 30/09/2026 y también tiene estados antiguos. Aquí decía «2465 pruebas de
> Python y 545 de JavaScript»; la última suite completa de esta conversación dio **2892 y 643**. Lo que sigue valiendo de este fichero es el
> contexto del **IUWS**, el mapeo de los 18 bloques y por qué el programa está hecho así.

**Estado a 23/09/2026.** Lo que se descubrió o cambió en estas rondas está marcado así: 🔵.

**Actualización del mapeo:** ya están **los 18 bloques** cotejados en sus campos obligatorios con el cuaderno: **113 campos
obligatorios**, de los que **61** tienen fuente y tipo traducibles (24/09/2026). Los 52 restantes se separan
entre códigos oficiales, datos que aún no se preguntan y conversiones por confirmar. Se han
incorporado los 11 bloques que faltaban. Queda revisar parte de los campos opcionales. Esta cifra
describe el trabajo de correspondencia, no un envío IUWS habilitado. El Anexo V vigente de FEGA
define variables y obligatoriedad, pero no publica los valores de los catálogos; esos siguen
pendientes del Anexo VII o de un canal oficial de descarga.

## Resumen de un vistazo

| | |
|---|---|
| **Qué es** | Un cuaderno de campo y digital para agricultores, en el navegador, para cualquier cultivo y cualquier superficie |
| **Estado** | Se puede usar entero. **2465 pruebas de Python y 545 de JavaScript en verde**, diseño con 0 errores, y el recorrido completo contra un servidor real en «todo correcto» |
| **Lo que falta** | Mandar el cuaderno a la Junta por IUWS. La correspondencia de los 18 bloques ya está revisada; faltan preguntas de la aplicación, conversiones y **valores de los catálogos** de FEGA, además del **certificado, alta y nombre comercial** de David. |
| **El bloqueo gordo** | Los **valores** de los catálogos de SIEX. Su estructura es pública y **ya sabemos qué tabla es la de 15 de los 40 catálogos**; los datos de cada tabla están detrás de un captcha |
| **Lo que más ayuda** | Ver el apartado **6** (qué te pido). Y **no repetir** lo del apartado **5.8**, que ya está comprobado y con tests |

---

## 1. Qué es

**CUE Digital** es un **cuaderno de campo y cuaderno digital para agricultores**,
autohospedado, que corre en un navegador. Lo está haciendo David para su propia explotación,
con la idea de que, si funciona bien, lo pueda usar algún cliente más.

- **Ámbito:** Castilla y León para empezar, pero escrito para **cualquier superficie,
  cualquier cultivo, secano y regadío** de España. Nada está cableado a un cultivo concreto.
- **Régimen:** REAGP.
- **Prioridad declarada por David, por delante de todo lo demás:** que la aplicación **no le
  falte de nada** y que sea **amigable para un usuario que no sabe de informática**. Esta es
  la parte que más se ha cuidado y la que más veces ha cambiado decisiones técnicas.
- **Lo que NO es:** no es una app de facturación ni de contabilidad. Facturas, Verifactu,
  factura electrónica B2B, bancos/PSD2, economía, OCR de compras, NDVI y ganadería están
  **aplazados a propósito**, no olvidados.

### Por qué el programa está hecho así

El registro de tratamientos puede estar **en papel hasta el 31/12/2026** (RD 1311/2012, art. 16.1,
en la redacción que le dio el RD 1039/2025) y desde el **01/01/2027** tiene que ser electrónico; la
fertilización es preceptiva desde el **01/01/2026** y el **plan de abonado desde el 01/09/2026**
(RD 1051/2022, arts. 4.2 y 5); y la factura electrónica B2B llega con el RD 238/2026. O sea: el
agricultor va a tener que llevar esto por ordenador, y las herramientas que hay son, en palabras de
David, para gente que ya sabe. De ahí la obsesión con el lenguaje llano.

**Pero hay que contarlo entero, porque es lo que más se malinterpreta** (y está en la ayuda del
programa, con los artículos delante): tener el registro es obligatorio, **mandarlo a la Junta no**
—artículo 10.2 del RD 1054/2022, «decidirán de forma voluntaria poner a disposición de la
administración […] la información que hayan cumplimentado en el CUE»—, se puede llevar con
**cualquier programa propio** que tenga el contenido mínimo del anexo II (artículo 10.3), y el
cuaderno electrónico obligatorio no empieza hasta el **siguiente periodo de la PAC** (después de
2027), y solo para fincas de más de 30 ha de cultivo, más de 5 ha de regadío o invernaderos de más
de 0,1 ha. Lo comprobado, artículo por artículo y con enlaces al BOE, en
[`LO_QUE_OBLIGA_LA_LEY.md`](LO_QUE_OBLIGA_LA_LEY.md).

---

## 2. Cómo está construido

| Pieza | Qué se usa |
|---|---|
| Servidor | Python 3.12 + FastAPI + SQLAlchemy 2.0 |
| Base de datos | SQLite en local, PostgreSQL + PostGIS en producción |
| Interfaz | HTML, CSS y JavaScript **a pelo**, y la pantalla de inicio ya en **React sin compilar** (los ficheros están en `backend/web/vendor`, con su LEEME y su huella) |
| Pruebas | `pytest` (Python) y `node --test` (JavaScript) |

**No hay `npm install`, ni `vite`, ni TypeScript.** Es una decisión, no un descuido: el servidor donde
vive esto puede servir ficheros estáticos, y punto. Y **React entró sin romper esa regla**: se bajan
una vez los ficheros ya compilados de React y `htm` a `backend/web/vendor/` (con su LEEME, sus
licencias y su SHA-256) y se escriben las pantallas con `htm`, que es como JSX pero sin compilar. Si
se subiera de versión, la guía está en [`REACT.md`](REACT.md) — y ojo: **React 19 ya no publica
ficheros UMD**, que son los que se cargan con una etiqueta `<script>` sin compilar. Hay una prueba que
lo impide a propósito.

### Por dónde está cada cosa

```
backend/app/
├── models.py          22 tablas
├── textos.py          TODO el texto que ve el usuario (~2.300 líneas)
├── legal.py           Los cálculos legales, aislados y puros
├── validaciones.py    Los avisos (V1…V22, F1…F5). Avisan, no bloquean
├── catalogos.py       Listas oficiales y listas nuestras
├── servicios.py       Casos de uso
├── cades.py           Verificador de firmas CAdES, sin librería de criptografía
├── adjuntos.py        Guardar ficheros en disco
├── geo.py             Geometría, distancias y el dibujo de la parcela
├── iuws.py            El volcado oficial: versiones, direcciones, qué falta y por qué
├── iuws_contenido.py  El contenido mínimo CUE, campo por campo
├── iuws_cliente.py    Las llamadas HTTP y la validación contra el esquema oficial
└── routers/           Las puertas de la API
backend/web/           app.js, estilos.css, index.html (lo que ve el agricultor)
backend/web/react/     Las pantallas ya migradas a React (inicio, confirmación, «mis cosas», «los papeles», el almacén, «qué hay sembrado», la ayuda, «mis datos» y las medidas preventivas), los componentes compartidos y montar.js
backend/web/vendor/    React y htm ya compilados, con su LEEME, sus licencias y su huella
backend/tests/         2465 pruebas de Python
backend/tests_js/      545 pruebas de JavaScript
backend/scripts/humo.py  Recorrido completo contra un servidor de verdad, 30 secciones
backend/scripts/bajar_catalogos_fega.py  Baja los catálogos oficiales que se pueden bajar
docs/                  Esta guía, la de UI/UX, la de la Junta, la de IUWS, la de React,
                       la de los catálogos oficiales y la actualización
data/                  Listas oficiales descargadas, fuentes oficiales del IUWS y plantillas
data/fega/             Los catálogos oficiales del FEGA y del MAPA, con su procedencia y su LEEME
backend/tests/datos/   Ficheros de los tests, todos con datos inventados (ver su LEEME)
data/ocr/              El idioma español del lector de fotos, con su LEEME y su huella
```

---

## 2 bis. La migración de la interfaz a React: terminada (ronda 72)

**Está terminada: 27 pantallas, siete piezas y los 65 pasos del asistente, todo en React.** No queda ni un
`innerHTML` de pantallas: `pintar()` y `bloqueError()` se borraron, y **el único sitio que escribe en la
pantalla es `montar()`**. Y no hay que contar nada a mano: la lista de pantallas vive en el código
(`PANTALLAS_EN_REACT`, al principio de `backend/web/app.js`), y hay una prueba
(`backend/tests/test_la_migracion_a_react.py`) que exige que **el código, la guía `docs/REACT.md` y la
caché del service-worker digan lo mismo**. Ese mismo fichero tiene ahora tres pruebas que impiden **volver
atrás** (al final de este apartado).

**Migradas:** inicio · confirmación («Apuntado…») · mis cosas · los papeles · el almacén · qué hay
sembrado · la ayuda · mis datos · las medidas preventivas · lo que he vendido · los grupos de parcelas ·
los análisis · dímelo con la voz · la revisión de lo dictado · guardar un papel · firmar el cuaderno · el plan de abono · entrar · facturas (la lista, el alta y la interpretación) · el mapa del SIGPAC · decir qué hay sembrado · traer las tierras del cuaderno de la Junta · traer la tierra del SIGPAC · mi cuaderno · **el asistente de apuntar**.

**Las tres últimas fueron las difíciles**, y en este orden:

1. **«Mi cuaderno»** (ronda 70): sus **nueve bloques** —los apuntes de producto, lo que falta, lo que se ha
   vendido, las medidas, los análisis, el plan, la firma, el cuaderno de la Junta y el registro
   electrónico— estaban escritos en `app.js` como **siete funciones `bloqueDe…` que devolvían HTML**, y
   ahora los pinta `react/pantallas/mi_cuaderno.js` con los datos que prepara `datosDelCuaderno()`.
2. **Los avisos de error** (ronda 71): lo que sale cuando el servidor falla. De paso se le dio salida a
   siete avisos que **no tenían ningún botón** —el `pintar()` borraba la pantalla y dejaba al agricultor
   con un texto y sin salida— y se les puso prueba, que era imposible antes porque el servidor de mentira
   daba por bueno todo (ahora hay un ayudante `falla()` en `interfaz.test.js`).
3. **El asistente de apuntar** (ronda 72): sus 65 pasos ya estaban en React desde la ronda 68, pero el
   envoltorio (las barras, la pregunta, la pista, el hueco `#formulario` y los botones) se pintaba a mano.
   Ahora es `react/pantallas/asistente.js`, y **el motor no se ha tocado**: `irA`, `normalizaIndice`, el
   `recoger()` de cada paso y **el borrador, que se sigue leyendo del DOM campo a campo**, siguen igual.
   Por eso migrar el motor no cambió nada de cómo se guardan los apuntes.

**Y ocho pantallas pequeñas más** se montan con la **pieza de la confirmación**: las cinco de «guardado»
(venta, análisis, plan de abono, medidas y ficha de un maestro) y las tres que ofrecen un camino (el alta
de una tierra, el listado de papeles y las tierras traídas).

**Lo que mantiene esto terminado** (`TestLoQueQuedaDeLaInterfazVieja`, en `test_la_migracion_a_react.py`):
ningún paso con `pintar:`, los 65 pasos con `montar:`, y ni un `innerHTML` de pantallas en `app.js`. Volver
atrás es fácil y no se nota —se copia un paso viejo de otro sitio y ese paso sale en blanco—, así que se
vigila.

**Lo que queda, y no es migrar nada**: (1) fuera de la interfaz, mandar el cuaderno a la Junta por IUWS
(necesita el alta del dominio que tiene que pedir David) y las dos decisiones de diseño que dependen de él;
(2) nada más dentro del código: la limpieza que quedaba (24 de las 27 pantallas repetían el bloque de
siempre para montarse, que `montar()` ya hace en una línea) se hizo en la ronda 73 —`app.js` se quedó en
221 líneas menos y `montarEn` tiene un solo usuario—. Está contado en [`REACT.md`](REACT.md) §6.1.

**Y una distinción que se añadió con el resumen del asistente:** los componentes que **no son una
pantalla entera** van en `backend/web/react/piezas/`, no en `react/pantallas/`. La lista
`PANTALLAS_EN_REACT` es la lista de pantallas, y meter ahí un trozo sería mentir en la tabla. Hay
**siete piezas** hoy (el resumen del apunte, la lista de botones para elegir, el campo, su ayuda, el
grupo de campos del maestro, la confirmación y **la tarjeta** —`tarjeta.js`, la del rediseño, que sirve para
elegir una tierra, para mirar las tierras de la finca y para leer los apuntes del cuaderno—) y una
prueba que exige que **todo** el JavaScript de `react/` (pantallas y piezas) esté en la caché del
service-worker.

**Y desde la ronda 62 el asistente se comprueba en un navegador de verdad**, que hasta entonces no se
comprobaba: el formulario de cada paso no se pinta en la pantalla entera sino en un **hueco**
(`#formulario`) dentro de la pantalla del asistente. Si el formulario del paso no llega, el agricultor ve
la pregunta y **nada que contestar**, y eso solo se ve en un navegador (en los tests no hay ReactDOM). El
guion lo caza buscando el hueco vacío; los pasos donde eso se comprueba están en `FORMULARIO_CON_PIEZA`
del guion.

**Cómo se hace una**, en corto (el detalle está en [`REACT.md`](REACT.md)): el fichero en
`backend/web/react/pantallas/<nombre>.js` con el componente **puro** (recibe textos y datos por
propiedades), `app.js` prepara esos datos y monta con `montar()`, se apunta el nombre en
`PANTALLAS_EN_REACT`, se añade el fichero a la caché del service-worker (subiendo su número), se
escriben las pruebas del componente en `tests_js/react.test.js`, se mueven las que miraban ese HTML
en `tests_js/interfaz.test.js` (dejando una que compruebe el cableado), y se comprueba **en un
navegador de verdad** con `scripts/comprobar_en_un_navegador.py`.

**Las decisiones que valen para todas las pantallas que quedan** (están explicadas en su sitio, no
las cambies sin leerlas):

- **Los campos de formulario siguen teniendo su `id` y los sigue leyendo `app.js`** (ver
  `mis_datos.js` y `medidas.js`): el manejador de clics es **uno solo** y vive en `app.js`, así que no
  se ha montado un estado compartido entre las dos mitades. Decenas de pruebas escriben en los campos
  por su `id`.
- **Los textos salen del servidor** (`textos.py` por `/api/interfaz`), también en React. En cada
  componente hay una prueba de que **no hay ni una frase escrita a mano**.
- **Nada de `esc()`** dentro de un componente: React escapa solo.
- **Las mismas `data-accion` y los mismos `id`** que la interfaz vieja: el manejador delegado y las
  pruebas dependen de ellos.
- **Nada de `style`**: los colores viven en el `:root` de `estilos.css`.
- **Un comentario dentro de una plantilla `htm` no puede llevar comillas invertidas**: cierra la
  plantilla y la aplicación deja de arrancar. Pasó; está avisado en `mis_datos.js`.
- **Las frases compuestas (dos textos del servidor unidos) se montan en `app.js`**, no en el
  componente: dentro de un componente son «una frase escrita a mano» y la prueba lo caza. Pasó dos
  veces, y las dos veces tenía razón la prueba.
- **El botón que guarda se deshabilita mientras guarda** y lo dice: sin eso, la misma factura o el
  mismo apunte se mandan dos veces.
- **El toque del mapa no se engancha a React**: el manejador delegado necesita saber **dónde** se ha
  tocado, y si se enganchara al componente se perdería la posición.

### Dos fallos que se encontraron mirando la pantalla con datos (ronda 46)

Los dos eran invisibles con la base de datos vacía, y por eso hay que dejar datos antes de mirar la
interfaz (`scripts/comprobar_en_un_navegador.py` los deja, en `siembra_datos`):

- **«Mi cuaderno» contaba cero apuntes de producto.** `estado.tratamientos` no lo rellenaba nadie: la
  pantalla enseñaba «0 apuntes de producto» y una lista vacía con el año lleno de tratamientos. Ahora
  se pide en `cargarDatos()` (`/api/tratamientos`) y se filtra por la campaña que se está llevando.
- **La pantalla de inicio decía «todavía no has apuntado nada» a quien tenía el cuaderno lleno.** Lo
  decidía con `localStorage`, es decir, con lo que recordaba **ese** aparato: al estrenar móvil o al
  entrar desde el ordenador de casa, el agricultor leía que no había apuntado nada y se quedaba sin el
  atajo de repetir. Ahora el atajo se saca también del servidor (`ultimoDeLaFinca` en
  `web/nucleo.js`, con `producto_id`, `aplicador_id` y `equipo_id` en la respuesta) y la frase se
  elige con los números del cuaderno (`/api/cuaderno/resumen`, que ahora cuenta también
  `apuntes_de_trabajo`). Y el atajo avisa de que está repitiendo (`tituloForzado`, que estaba escrito
  y no lo leía nadie).

### Otros dos fallos, estos buscando en el código (ronda 51)

En la ronda 51 se buscaron **uno por uno** los textos que pide el JavaScript y salieron dos huecos que
nadie había visto en pantalla, porque un texto que falta **no revienta nada: deja un hueco**:

- **La ficha de la parcela traída del SIGPAC** pedía `parcela.ref_sigpac`, que **no existe** en el
  vocabulario de la interfaz (las etiquetas de campo viven dentro de `etiquetas`, y además son
  preguntas). El número del recinto salía **sin rótulo**.
- **Diez sitios pedían `mensajes.no_se_pudo`, que tampoco existía**: al fallar una descarga (el
  cuaderno en papel, el fichero de datos), una subida (el boletín, el papel firmado) o la firma, el
  aviso salía **en blanco**. El agricultor pulsaba, no pasaba nada y no había ni una palabra.

Los dos están arreglados y **hay una prueba que impide que vuelvan**:
`backend/tests/test_que_no_falte_ningun_texto.py` extrae todas las claves de
`t("…")`, `mensaje("…")`, `aviso("…")` y `accion("…")` del JavaScript y comprueba que existan en lo
que sirve `/api/interfaz` — con **la misma búsqueda que hace la aplicación** (clave más larga
primero, porque hay etiquetas con puntos dentro del nombre) y comprobando que **existe**, no que no
esté vacía. **Si añades una pantalla, esa prueba es la que te dice si te falta un texto.**

**Lección para lo que queda:** un hueco en pantalla se caza **buscando**, no mirando. Y cuando un
texto se pide con una función auxiliar (`accion`, `aviso`, `mensaje`), la clave tiene que estar en la
tabla que le toca: `acciones`, `aviso` o `mensajes`.

<small>(Y la lección del apartado anterior, que sigue valiendo: una pantalla se comprueba **con datos
dentro**, no vacía. Una lista vacía se ve bien aunque esté rota.)</small>

---

## 3. Las reglas que no se doblan

Si vas a proponer un cambio, ten esto en cuenta o la propuesta no vale:

1. **Todo el texto que ve el usuario vive en `backend/app/textos.py`.** No se escribe una
   frase en una plantilla ni en el JavaScript. Hay una lista de **palabras prohibidas**
   («error», «fitosanitario», «interfaz», «sesión», «uhc», «dgc»…) y una prueba que la
   vigila. Un agricultor no tiene por qué saber qué es un UHC.
2. **Nada inventado.** Si un dato no se sabe, se deja **vacío y marcado como pendiente**,
   nunca se rellena con algo plausible. Esto vale para códigos de catálogo, límites legales y
   listas de municipios. `catalogos.limites_que_faltan()` avisa si falta alguna tabla;
   los anexos III y V de la Orden MAV/398/2022 ya están en `data/nitratos_cyl/`;
   el III avisa sin bloquear solo con zona, cultivo y sistema exactos. Los 387 municipios
   se derivan del Excel oficial de IDECyL en `data/zv_cyl_fuentes/`.
3. **Nada se borra.** Un registro equivocado se **anula con motivo** y queda en `auditoria`.
   Borrar pone en riesgo el cuaderno entero.
4. **El vacío es `None`, nunca `0`.** `0` significa «cero», `None` significa «no lo sé».
5. **Aislamiento por explotación:** todas las tablas de negocio llevan `explotacion_id` y no
   se cruzan datos entre fincas.
6. **`DESIGN.md` y `estilos.css` tienen que decir lo mismo.** Los colores solo viven en el
   `:root` de la hoja de estilos.
7. **Los tests no se borran ni se desactivan para que algo pase.** Si un cambio rompe una
   prueba, o se arregla el cambio, o se actualiza la prueba **explicando por qué** el
   comportamiento nuevo es el bueno.
8. **Nada de secretos en el repositorio.** Ni claves, ni certificados, ni contraseñas.
   Certificado, CIF y nombre comercial van por variables de entorno, a propósito.
9. **Los tests no salen a internet.** Solo la prueba de humo llama a servicios de verdad.
10. **Los recuentos de pruebas de los documentos tienen que estar al día.** Si añades tests,
    actualiza `README.md`, `AGENTS.md` y `docs/LO_QUE_PIDE_LA_JUNTA.md` en el mismo cambio.
11. **Cuidado con PowerShell en Windows:** `Set-Content` y `Out-File` meten BOM y estropean
    los acentos. Hay una prueba (`tests/test_ficheros_de_texto.py`) que lo vigila.

---

## 4. Qué está terminado y verificado

Ejecutado y en verde, no «debería funcionar»:

| Comprobación | Resultado |
|---|---|
| `pytest` | **2465 pruebas, 0 fallos** |
| `node --test` | **545 pruebas, 0 fallos** |
| `designmd lint DESIGN.md` | **0 errores, 0 avisos** |
| `scripts/humo.py` contra un servidor real | **30 secciones, «RESULTADO: todo correcto»** |

Y por dentro:

- **Los 21 apartados** que pide el cuaderno de Castilla y León (veinte apartados más el
  repositorio de documentación), cada uno con su pantalla.
- **Cuaderno de campo y cuaderno digital** completos: tratamientos, abonado, labores,
  cosecha, ventas, análisis, medidas preventivas, plan de abonado, instalaciones.
- **Firma del cuaderno** (CAdES), verificada con **firmas OpenSSL reales** de verdad.
- **Autenticación con certificado digital**.
- **Registro de zonas vulnerables a nitratos** según el Decreto 5/2020.
- **Conexión con el SIGPAC** por sus servicios públicos, para traer la parcela por su
  referencia y dibujar su forma.
- **Ayuda en cada campo**, dictado por voz que **nunca escribe solo** (propone, el agricultor
  confirma), avisos que explican y no bloquean, y **Modo Sencillo** con seis botones.

---

## 5. El volcado oficial a la Junta (IUWS)

### 5.1 🔵 El descriptor apareció: estaba dentro del propio Word oficial

Durante muchas rondas esto se dio por bloqueado esperando que FEGA mandara el fichero
`BdcSix-DS-DiseñoCUE.xlsx`. **Estaba incrustado en el propio Anexo VI**, y se extrajo el
22/09/2026. Está en `data/iuws_fuentes/`, sin tocar, y su procedencia está **comprobada
byte a byte**:

| Fichero | De dónde sale | Comprobación |
|---|---|---|
| `BdcSix-DS-DisenoCUE_3.11.4.xlsx` | Parte `word/embeddings/Microsoft_Excel_Worksheet1.xlsx` del Anexo VI | SHA-256 idéntico |
| `BdcSix-DS-DisenoRegistroREA_3.11.xlsx` | Parte `word/embeddings/Microsoft_Excel_Worksheet.xlsx` | SHA-256 idéntico |
| `BdcSix-DS-DisenoCUE_3.11.4.schema.json` | Paquete OLE (`oleObject1.bin`) del Anexo VI | **Byte a byte** igual a la carga del paquete, cuyo nombre original dentro es `BdcSix-DS-DiseñoCUE_3.11.4.json` |

- El Excel del CUE lleva la hoja **`EstructuraCuadernoWS`** y la marca **«Versión 3.11.4»**.
- El esquema exige un objeto raíz `CUADERNO` (lista). Cada elemento exige `CAExplotacion`,
  `IdTitular`, `CodigoRea` y `UnidadGestora`.
- El descriptor describe **107 bloques y 402 campos**, de los que **175 son obligatorios**, y
  en su columna de observaciones dice **contra qué catálogo** valida cada campo.

> **Lección para el próximo agente:** antes de declarar que algo oficial no existe, **mira
> dentro del documento oficial**, no solo los enlaces de la página.

### 5.2 🔵 Las rutas llevan `/api/`

Lo verificado llamando **sin certificado** (22/09/2026):

| Dirección | Entorno de integración de FEGA | Castilla y León (producción) |
|---|---|---|
| `/IUWS/api/version` | `200` — «Versión del descriptor : 3.11.4» | `200` — `{"version": "3.11.4"}` |
| `/IUWS/version` | `404` | `200` |
| `/IUWS/api/comunicacion/{app}` | `200` con `No Autorizado` | negociación TLS: pide certificado de cliente |
| `/IUWS/api/crear/` | `405` con `GET` (existe: es `POST`) | `401` |
| `/IUWS/api/exportar/`, `/exportarREA/`, `/comprobarEstado/` | `200` con `No Autorizado` | `401` |

Los `404` que había antes eran culpa nuestra, por llamar a la ruta antigua sin `/api/`: **no
eran señal de que faltara el alta**. La ruta de exportación CUE ya **no** lleva `IdCuaderno`.

**Ninguna llamada autenticada se ha probado todavía.** Eso sigue sin verificar.

### 5.3 🔵 Los catálogos: la estructura sí, los valores no

- El portal público de SIEX publica la **estructura de 287 catálogos** (141 visibles) y se
  consulta **sin certificado**: `https://www3.sede.fega.gob.es/bdcsixpor/tablas/configJson`.
  Ahí están los nombres oficiales de los catálogos (por ejemplo `TIPENERGIA`,
  `TRAT_ESTIERCOLES`, `CUACOM`, `ENTIHABI`) y las columnas de cada uno.
- **Los datos de cada tabla no**: el portal es una aplicación de una sola página con
  **reCAPTCHA** en el interceptor de peticiones, y devuelve su propia página en cualquier otra
  ruta. **No se han podido descargar los valores.**

🔵 **Y el descriptor dice qué catálogos hacen falta, con nombre y apellidos.** Su hoja
`EstructuraCuadernoWS` está convertida en datos (`data/iuws_campos_del_cuaderno.json`, derivado,
con script para rehacerla) y se lee desde `backend/app/iuws_descriptor.py`. De ahí sale:
**107 bloques, 402 campos, 175 obligatorios y 40 catálogos** distintos que el descriptor pide por
su nombre. Por ejemplo, `Eficacia` es obligatorio y sale del catálogo **`Eficacia del
tratamiento`**.

🔵 **Y 15 de esos 40 ya tienen tabla localizada.** SIEX publica sin certificado la lista de sus
**287** catálogos con sus nombres y columnas (`data/siex_catalogos.json`, bajado con
`backend/scripts/bajar_catalogos_siex.py`, y se lee desde `backend/app/catalogos_siex.py`).
Cruzando los dos nombres, **15 coinciden exactamente** y **las 15 son públicas**:
`Eficacia del tratamiento` → `EFICACIA_TRATAMIENTO`, `Unidades de Medida` → `UNIDADES_MEDIDA`,
`Justificación de la Actuación` → `JUSTIFICACION_ACTUACION`, `Sistema de Riego` → `SIST_RIEGO`…

> **Lo que NO se hace, y es lo importante:** los otros 25 **no se emparejan por parecido**. El
> descriptor pide «tipos de producto» y en SIEX hay «tipo de producto fitosanitario»
> (`TIPO_PRODFITO`): se parecen y no se puede afirmar que sean lo mismo. Un test recorre las
> correspondencias y exige que los dos nombres sean **exactamente** iguales, para que nadie meta
> un emparejado a ojo.

Lo que sigue faltando son **los valores**: el portal publica la estructura de las tablas y los
datos de cada tabla están detrás de un captcha. El recado para FEGA ya no es «mándame los
catálogos», es **«los valores de estas tablas»**, y 15 van con nombre y apellidos de tabla.

> **Aviso que ahorra media tarde:** el descriptor oficial **omite la llave `{`** en 14 cabeceras
> de bloque (entre ellas `TratamFito`, `SiembraPlantacion` y las listas de plagas y enfermedades).
> Una tabla que se saque del Excel mirando solo la llave **pierde esos bloques** y cuelga sus
> campos del bloque de arriba. **Pasó**: durante una ronda estos documentos dijeron que «el
> descriptor no tiene `TratamFito`», y era falso. La marca fiable es la **columna de ocurrencia**
> (`0..n`, `1..n`). Y como dato: los dos documentos **coinciden** en los 20 bloques de actividades;
> el descriptor trae uno de más, `ActividadAgraria`.

Consecuencia medida, y es la que bloquea de verdad: **el esquema oficial no admite campos
vacíos** — declara 528 tipos y **no hay un solo `null`** en todo el esquema. Un campo
obligatorio de catálogo que no tengamos **no se puede dejar en blanco**: ese bloque no se puede
armar de forma que valide.

### 5.4 Lo que falta, y de quién depende

| # | Clave | Qué es | De quién depende |
|---|---|---|---|
| 1 | ~~`descriptor`~~ | 🔵 **Conseguido**: v3.11.4 en `data/iuws_fuentes/`, con su esquema | — |
| 2 | `catalogos` | Los **valores** de los catálogos oficiales (la estructura ya es pública) | FEGA |
| 3 | `nombre_comercial` | El nombre comercial del software, **registrado** en el interfaz | David |
| 4 | `dominio` | El dominio y el **CN** del certificado de dominio | David |
| 5 | `certificado` | El certificado de dominio (sello de entidad) con autenticación de cliente | David |
| 6 | `empresa_habilitada` | El CIF de la empresa habilitada **y la autorización de cada titular** | David y cada agricultor |
| 7 | `alta_entorno` | El alta en el entorno de integración (formulario firmado) | David |
| 8 | `codigo_siex` | El código SIEX de cada explotación | Cada agricultor, en «Mi finca» |

**Y una novena que no depende de nadie de fuera:** lo que el cuaderno **no pregunta**. El mapeo
del bloque de tratamientos (`backend/app/iuws_mapeo.py`) lo separa con cuatro estados. De sus 11
campos oficiales: **6 se pueden mandar ya**, **3 esperan un catálogo de FEGA**
(`ProblematicaFito`, `Justificaciones`, `Eficacia`), **1 está a medias** (`ProductosFito`: falta
el tipo y la unidad, que son códigos) y **1 no lo recogemos** (`DGCs`, para saber en qué parcela
concreta se trató).

🔵 **En la ronda 23 se cerraron dos de esas lagunas**, que eran nuestras y no de nadie más: el
cuaderno ya pregunta **si se aplicó a mano** (el interfaz exige `AplicacionManual` como
obligatorio) y **cómo de bien funcionó** (exige `Eficacia`). Con eso un campo obligatorio pasó de
bloqueado a enviable y otro pasó de «no lo tenemos» a «falta el código». La lista de respuestas
que se le ofrecen al agricultor es **nuestra** y está marcada como tal: la equivalencia con los
códigos oficiales no se supone.

🔵 **En la ronda 24 se cerraron las dos últimas lagunas que dependían solo de nosotros**, en el
bloque **`PlanAbonado`**: **el cultivo del año anterior** (`CultivoPrecedente`) ya no se pregunta
—se rellena con el cultivo que el agricultor declaró en la campaña anterior— y **`Herramienta`**
(el descriptor oficial de FEGA, `BdcSix-DS-DisenoCUE_3.11.4`, lo define como **booleano**) se
pregunta con un **sí o un no**, no con una lista de programas que nadie ha publicado. Eso sube los
campos obligatorios con fuente directa de **60 a 61** (hay un test que lo comprueba en
`tests/test_mapeo_oficial.py`). Y de paso se cerró un agujero de los tests: la copia de los textos
que usan los tests de JavaScript **no tenía la pregunta nueva**, así que el test la pintaba en
blanco y se daba por bueno; ahora `tests/test_interfaz.py` saca las claves del propio `app.js` y
avisa si falta alguna **o si la copia dice otra pregunta distinta de la que ve el agricultor**.

Tres cosas que estaban mal y ya se sabe por qué: **las fechas van en `dd/mm/aaaa`, no en ISO**
(el patrón oficial empieza por el día); **`IdAjena…` es un número**, así que el `CD-…` de la
aplicación no vale para el interfaz; y **el esquema tiene `oneOf`** — el equipo de aplicación
tiene que llevar uno de los tres entre ROMA, REGANIP o nuestro identificador propio.

Los ocho datos del formulario de Castilla y León están en `iuws.CAMPOS_DEL_FORMULARIO_CYL`.

🔵 **Y en la ronda 25, el cuaderno de la propia Junta.** El agricultor de Castilla y León que lleva
su cuaderno en la aplicación de la Junta (el **Cuecyl**) tiene ahí escritas todas sus parcelas: en
el cuaderno real de 2026 son **54 líneas y 51 tierras distintas** con su referencia del SIGPAC, su
cultivo, su ecorregimen y sus hectáreas. Ahora hay un botón —«TRAER MIS TIERRAS»— que sube ese
fichero y apunta las tierras: primero **enseña lo que trae** (sin escribir nada) y solo después las
apunta, y subirlo dos veces **no duplica ninguna tierra**. Está en `app/cuaderno_cyl.py` (la
lectura) y `app/routers/cuaderno_cyl_api.py` (leer y traer), con 41 pruebas en
`tests/test_cuaderno_cyl.py`, el fichero de ejemplo inventado en `tests/datos/`, y todo contado en
[`CUADERNO_DE_LA_JUNTA.md`](CUADERNO_DE_LA_JUNTA.md) — que es también donde está la dirección
oficial de las instrucciones del Cuecyl y lo que dicen.

🔵 **Y en la ronda 26, las facturas de compra.** El cuaderno de la Junta pide la «empresa
suministradora» y el «nº de factura» (hoja 9.1) y el «nº de albarán» (hoja 6), y dice que hay que
conservar «las facturas u otros documentos que justifiquen la adquisición» tres años. Ahora el
agricultor **hace una foto al papel** (o sube el PDF del proveedor) y el programa **lee lo que pone**
y se lo enseña para que lo confirme: proveedor, NIF, número, fecha, base, IVA, total y cada línea con
su producto, su cantidad y su precio. Para las fotos hace falta un lector de letras (**Tesseract**, un
programa aparte, no una librería de Python); su idioma español se trae con
`scripts/bajar_idioma_ocr.py` a `data/ocr/` y se usa **sin tocar la instalación del ordenador**. Si no
hay lector, **se dice y no se inventa nada**: la factura se guarda como justificante y los datos se
escriben a mano. Lo que hace fiable la lectura **son las cuentas**: cantidad × precio = importe, las
líneas suman la base, base + IVA = total; si no cuadra, se avisa. Está en `app/facturas.py` (la
lectura), `app/ocr.py` (el lector de letras) y `app/routers/facturas_api.py`, con 63 pruebas en
`tests/test_facturas.py`, y contado entero en [`FACTURAS.md`](FACTURAS.md).

🔵 **Y en la ronda 27, el cuaderno relleno.** `GET /api/cuaderno-cyl/exportar` escribe el libro de
**25 hojas** del cuaderno oficial de Castilla y León con los datos del agricultor —parcelas,
tratamientos, abonos con su nº de albarán y su tipo, análisis, ventas, labores, plan de abonado y la
hoja de documentación— y `GET /api/cuaderno-cyl/que-falta` devuelve **la lista de lo que falta**, cada
cosa con **dónde se apunta**. Esa lista no está escrita a mano: sale de comparar el cuaderno oficial
con lo que hay. Lo que no está se queda **en blanco**, nunca con un cero. Está en
`app/cuaderno_cyl_exportar.py`, con 21 pruebas en `tests/test_cuaderno_cyl_exportar.py` — entre ellas
la de **ida y vuelta**: el fichero que se escribe se vuelve a leer con el lector del cuaderno y tiene
que decir lo mismo.

### 5.5 Dónde está el código, si vas a mirarlo

- `backend/app/iuws.py` — versiones, direcciones, **`QUE_FALTA`** (la lista de arriba, en
  código), `configuracion()` y el cargador del descriptor.
- `backend/app/iuws_contenido.py` — el contenido mínimo CUE, campo por campo, con su número.
- `backend/app/iuws_cliente.py` — las llamadas y la **validación contra el esquema oficial**
  (`jsonschema`, borrador 7) antes de mandar. La marca local `formato` nunca viaja.
- `data/iuws_fuentes/LEEME.md` — de dónde sale cada fichero oficial y su huella.
- `docs/ACTUALIZACION_IUWS_2026-09-22.md` — la nota del día que se consiguió el descriptor.

### 5.6 Lo que NO hay que hacer

- **No inventar códigos de catálogo** ni nombres de campo del JSON. Van vacíos y marcados.
- **No copiar los ejemplos del Anexo VI**: el propio anexo avisa, **también en la v3.11.4**,
  de que sus ejemplos «pueden no corresponderse con la v2.6 del descriptor».
- **No editar nada de `data/iuws_fuentes/`**: son fuentes oficiales. Lo derivado va aparte.
- **No meter el certificado ni la clave privada en el repositorio.**
- **No quitar** la comprobación de «está conectado» para que parezca que funciona.
- **No romper** la suite. Si algo no se puede comprobar, la aplicación dice **«no lo he podido
  comprobar»**: eso es una función, no un fallo.

### 5.7 🔵 El mapeo al formato oficial, campo por campo

`backend/app/iuws_mapeo.py` responde, por cada campo oficial, **de dónde sale** y **qué le falta**.
No es sí o no, son cuatro estados, y la diferencia importa porque decide si hay que escribir a
FEGA o escribir una pantalla:

| Estado | Qué significa | De quién depende |
|---|---|---|
| `se_puede` | Está en el cuaderno y el formato lo admite (con su conversión) | De nadie |
| `hace_falta_catalogo` | El dato está, el código no | **De FEGA** |
| `a_medias` | Tenemos parte y falta algo que no preguntamos | De nosotros |
| `no_lo_tenemos` | El cuaderno no recoge ese dato | De nosotros |

El bloque de tratamientos está mapeado entero (**11 campos, 8 obligatorios**): **6 se pueden**
mandar ya, **3 esperan un catálogo** (`ProblematicaFito`, `Justificaciones`, `Eficacia`), **1 está
a medias** (`ProductosFito`) y **1 no lo recogemos** (`DGCs`).

**Cuatro cosas que estaban mal y ya se sabe por qué** (las cuatro se descubrieron cotejando con
el esquema, no leyendo el Excel):

1. **Las fechas van en `dd/mm/aaaa`, no en ISO.** El patrón oficial empieza por el día:
   `2026-05-01` mide 10 caracteres y **no lo cumple**. Hay una conversión con tests.
2. **`IdAjena…` es un número** (`integer`, hasta 10 dígitos). El `CD-70922320A-T-14` de la
   aplicación sirve para rastrear y **no vale** para el interfaz; para el interfaz se manda el
   número de la fila, que no cambia nunca.
3. **El esquema tiene cinco `oneOf`**, no solo tipos. La que importa: el equipo de aplicación
   tiene que llevar **uno** de estos tres —ROMA, REGANIP o nuestro identificador propio—, ni los
   tres ni ninguno.
4. **El descriptor y el esquema coinciden en los bloques.** Los 20 bloques del esquema tienen su
   bloque en el descriptor. Esto **estuvo escrito al revés** durante una ronda («el descriptor no
   tiene `TratamFito`») por un fallo de lectura del Excel, no por una diferencia de los
   documentos. Está corregido y con un test que exige que todos los bloques del esquema aparezcan
   en la tabla del descriptor.

**Lo que ya se puede demostrar con tests:** con los códigos puestos, el cuerpo que armamos
**valida** contra el esquema oficial (o sea, la forma es la correcta); sin ellos, el validador
dice **exactamente qué** falta. El bloqueo son los códigos, no la estructura.

🔵 **Y el mapa del cuaderno ENTERO sale solo, de los dos documentos oficiales.**
`GET /api/iuws/estado`, apartado `mapa_del_cuaderno`: **18 bloques** (3 de datos de la explotación
y 15 de actividades), **113 campos obligatorios**, **19 catálogos** que hacen falta para esos
campos (de los que **7 ya tienen tabla de SIEX localizada**) y **9 bloques que obligan a decir en
qué parcela pasó** — que es el bloqueo que alcanza a más sitios a la vez, porque va en el código
de la DGC. No está escrito a mano: sale del esquema y del descriptor cada vez que se pregunta.

Dos detalles que salieron al construirlo: **un contenedor no pide un catálogo, pide los de
dentro** (`ProblematicaFito` necesita las cuatro listas: plagas, enfermedades, malas hierbas y
reguladores), y **cuando el descriptor no dice el catálogo de un campo pero sí lo dice en otro
bloque, se apunta como información y no como conclusión** (`Riego.SistemaRiego`).

🔵 **Y el mapa dice de qué tabla nuestra sale cada bloque.** Es un dato sobre nuestro programa, y
un test comprueba que las tablas existen:

| Tabla del cuaderno | Bloques oficiales |
|---|---|
| **`Labor`** | **7**: riego, labores culturales, pastoreo, cubierta, siembra y plantación, semilla tratada y cosecha |
| **`TratamientoFitosanitario`** | **3**: tratamientos, postcosecha y tratamiento de instalaciones |
| Las otras siete tablas | 1 cada una |

O sea: **10 de los 18 bloques salen de dos tablas**. El mayor trabajo de mapeo era el de
las labores, y no porque faltaran datos (el cuaderno guarda el agua, la semilla, el marco y la
densidad), sino porque hay que traducir cada tipo de labor a los campos de su bloque. Y **el
único bloque del que no tenemos nada es el de la energía**, a propósito: la app oficial de
Castilla y León tampoco lo pide.

🔵 **Los 18 bloques tienen ya clasificados todos sus campos obligatorios.** De esos **113 campos, 61 tienen
correspondencia directa**. `GET /api/iuws/estado`, apartado `mapeo_de_los_bloques`, da el detalle
de cada campo, su fuente y lo pendiente. Ningún bloque se declara enviable por este recuento.

**Y el hallazgo que cambia la conversación: en esta parte del cuaderno lo que falta no son
catálogos, son preguntas.** Los cuatro bloques que salen de `Labor` necesitan **una sola lista de
códigos** entre todos (la de tipo de labor); el resto de lo que falta son cosas que la aplicación
no pregunta: si se sacó semilla, si se dejó sin cosechar, si los animales eran de terceros o
propios, qué cubre el suelo y sus dos anchuras, si los restos quedaron en el suelo…

Eso **no depende de nadie de fuera**: es la lista de pantallas que hay que escribir, y es la parte
del objetivo que dice «dejar bloqueado **solo** lo que dependa de terceros».

Tres cosas más, que son **diferencias entre los dos documentos oficiales** (declaradas en el
módulo con su motivo, y con tests que exigen que sean **esas** y ninguna más):

- **`Cosecha.GestionInsumos`**: el descriptor la marca **obligatoria** y el esquema **no la
  declara**. Hay que preguntar cuál manda.
- **`LaboresCulturales.TipoLabor`**: hace falta un código y el descriptor **no cita ningún
  catálogo**, así que no se puede saber de dónde salen.
- **`UsoSemillaTratada.IdAjenaSiembraPlant`**: el descriptor permite enlazar la semilla con la
  siembra, pero el esquema omite ese campo opcional. Se guarda la correspondencia como pendiente.

Y una sola convención se ha dado por buena, porque está **escrita**: `SiembraPlantacion` dice «1
Siembra 0 Plantación» y `CosechaSiega` dice «cosecha/recolección (1) o siega». Para poder
comprobarlo se guarda la **descripción** de cada campo del descriptor (columna de la tabla
derivada). Los demás códigos no se suponen: se piden.

Ya no quedan bloques sin correspondencia manual. Sí quedan campos marcados `a_medias`,
`hace_falta_catalogo` o `no_lo_tenemos` en `GET /api/iuws/estado`, apartado
`mapeo_de_los_bloques`.

🔵 **Y buscando esto salió un fallo de la pantalla que no tenía nada que ver con la Junta:**
**catorce campos se pintaban sin pregunta escrita.** El campo estaba en el mapa de `app.js` y se
dibujaba, pero `pintaCamposMaestro` busca el texto en `textos.ETIQUETAS`/`ETIQUETAS_MAESTRO` y no
lo encontraba, así que salía **un hueco en blanco al lado de la casilla**: en la siembra (semilla,
dosis, lote, marco, densidad), en el riego (agua, unidad, sistema, contador, nitratos), en la
compra del producto (cantidad, fecha, unidad) y en el número de informe del análisis.

Se han escrito las catorce, y hay un test que recorre **todas** las claves del mapa de campos y
exige que cada una tenga su pregunta, que no esté vacía y que no lleve jerga. Ese test es el que
las encontró y el que impide que vuelva a pasar.

Las dos preguntas del pastoreo ya están puestas (el pastoreo pasó de 3 a **5 de 6** campos
obligatorios), así que de esa lista de preguntas pendientes ya está hecha una.

### 5.8 Lo que NO hay que volver a averiguar

Ya está comprobado y con tests. No hace falta repetirlo:

- **El descriptor y su esquema son oficiales** (huellas comprobadas contra el Word del FEGA).
- **Las rutas llevan `/api/`** y las de la versión se pueden llamar hoy, sin certificado.
- **El formato de fecha** es `dd/mm/aaaa`.
- **`IdAjena…` es numérico.**
- **El equipo se identifica con uno de los tres** (ROMA, REGANIP o el propio).
- **La tabla de campos del descriptor**: 107 bloques, 402 campos, 175 obligatorios, 40 catálogos.
- **Las 15 correspondencias exactas** entre catálogos del descriptor y tablas de SIEX.
- **El sobre del mensaje ya valida** contra el esquema oficial.

---

## 6. Qué te pido

El bloqueo del descriptor ya no existe y el formato ya está resuelto. Lo que desatasca ahora, por
orden de importancia:

1. **Una vía oficial para los VALORES de los catálogos de SIEX** (no la estructura: los valores).
   El portal público publica la estructura de las 287 tablas, pero **los datos de cada tabla están
   detrás de un reCAPTCHA** y no se han podido bajar. Preguntas concretas:
   - ¿Publica FEGA esas listas en algún fichero descargable (CSV, Excel) fuera del portal?
   - **Comprobado:** el [Anexo V 3.11](https://www.fega.gob.es/sites/default/files/files/document/2025.11.20-ANEXO_V_Definicion_de_variables_3.11_CORRECCION_ERRORES_PUBLICACION.xlsx)
     define variables y obligatoriedad, pero **no trae los valores** de los catálogos.
   - ¿Hay que pedirlos junto con el alta en el entorno de integración?
   - **Ya sabemos 15 tablas por su nombre y su identificador**, así que la petición puede ir con
     nombre y apellidos: `EFICACIA_TRATAMIENTO`, `UNIDADES_MEDIDA`, `JUSTIFICACION_ACTUACION`,
     `ENFERMEDADES`, `MALAS_HIERBAS`, `SIST_RIEGO`, `TIPO_ANALISIS`, `MATERIAL_ANALIZADO`… (los 15
     salen en `GET /api/iuws/estado`, apartado `catalogos_de_siex`).
   - Y para los **campos obligatorios** de los 18 bloques hacen falta **19 catálogos**, de los
     que **7 ya tienen tabla localizada**: el mapa entero, bloque por bloque, está en el mismo
     sitio (`mapa_del_cuaderno`).
2. **La correspondencia de los 25 catálogos que NO coinciden de nombre.** ¿Existe un documento
   oficial que diga qué tabla de SIEX corresponde a cada catálogo del descriptor? Los que hay que
   resolver son, entre otros: `Plagas`, `tipos de producto`, `Medida preventiva/cultural`,
   `Variedad`, `Producto`, `cultivos`, `especies`, `paises`, `unidades`, `coberturas de suelo`.
   > Ojo a un detalle: varios de esos nombres están **en minúscula y en plural** (`cultivos`,
   > `especies`, `paises`, `unidades`, `productos`), que no es como están escritos los nombres
   > oficiales de las tablas de SIEX. Puede que sean nombres internos. Si alguien sabe de dónde
   > salen, eso solo ya desbloquea varios.
3. **La asignación de `CodigoDGCAjena`**. El Anexo VI, apartado «Importación de datos en el cue
   (crear)», ya dice que el CUE comercial genera un identificador único para cada DGC nueva.
   El descriptor lo declara `number(16)`. Queda por definir y persistir una asignación estable,
   confirmar el ámbito de unicidad y vincularla con los códigos que devuelve la administración.
   Véase [`FUENTES_OFICIALES_PENDIENTES.md`](FUENTES_OFICIALES_PENDIENTES.md), punto 2.
4. **`MateriaActiva`**: el esquema lo declara **numérico** y el cuaderno guarda el **nombre** de la
   materia activa («Cipermetrina»). ¿De qué catálogo salen esos números?
5. **Confirmar el procedimiento de alta vigente en 2026**: a qué correos, con qué formulario, y
   si sigue valiendo lo del anexo (`soporte-integracioncue@fega.es` y
   `comercialcuecyl@jcyl.es`, formulario firmado electrónicamente).
6. **Los requisitos del certificado de dominio**: el Anexo VI admite sello de entidad o
   SSL/TLS DV/OV/EV con autenticación de cliente, y recomienda el sello; falta confirmar la
   comparación exacta del CN con el dominio registrado en Castilla y León.
7. **Confirmar la vigencia y delimitación concreta de las zonas vulnerables**. El listado
   oficial con 387 códigos y 24 zonas del Decreto 5/2020 ya se deriva del Excel de IDECyL
   en `data/zv_cyl_fuentes/`. El Anexo III avisa sin bloquear cuando zona, cultivo y sistema
   coinciden exactamente; no sustituye la revisión de excepciones o de una parcela limítrofe.
8. **Confirmar posibles modificaciones posteriores** de la Orden MAV/398/2022; el PDF íntegro
   de 2022 está conservado en `data/nitratos_cyl/`.

### Lo que le pido a David, concretamente

- El **nombre comercial** que quiere que aparezca.
- El **CN del certificado** y el dominio.
- Si va a pedir el **alta** en el entorno de integración.

---

## 7. Cómo comprobar cualquier cosa que toques

```powershell
# Python: 2465 pruebas
cd backend
$env:CUEDIGITAL_ENTORNO="pruebas"; $env:CUEDIGITAL_ITERACIONES_PBKDF2="1000"
$env:PYTHONIOENCODING="utf-8"
..\.venv\Scripts\python.exe -m pytest

# JavaScript: 545 pruebas
node --test "tests_js/nucleo.test.js" "tests_js/interfaz.test.js" "tests_js/react.test.js"

# El contrato de diseño: 0 errores y 0 avisos
cd .. ; npx --yes -p "@google/design.md" designmd lint DESIGN.md

# El recorrido completo contra un servidor de verdad (30 secciones)
# hace falta un servidor recién arrancado y una base de datos limpia
```

Si algo de esto sale en rojo, el trabajo no está terminado. Da igual lo bien que suene la
explicación.
