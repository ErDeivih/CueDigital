# CUE Digital: resumen completo del proyecto (para ChatGPT o cualquier otro)

> **Qué es este documento.** David lo pidió así el 30/09/2026: *«resumen completo de todo lo que has
> hecho en los últimos días, lo que te he pedido hacer (aplicación de gestión completa de una
> explotación), lo que llevamos hecho, lo que queda por hacer, usar Stitch para ayudar en la UI,
> etc. Nos ayudará ChatGPT»*. Esto es eso: el estado del proyecto contado **entero y sin adornos**,
> para que otra herramienta (o otra persona) pueda seguir sin haber estado dentro.
>
> **Si vas a tocar el código, lee antes `AGENTS.md`**: es el convenio de trabajo y manda sobre este
> fichero. Este documento cuenta **dónde estamos**, no cómo se trabaja.
>
> Fecha del resumen: **30/09/2026**. Todo lo que va con fecha es de esa fecha; lo que no la lleva es
> porque se ha comprobado al escribirlo.

---

## 0. Las reglas que no se negocian (resumen de `AGENTS.md`)

1. **Ante una petición de cambio: no contestar y esperar. Crear un `goal`, implementarlo y terminarlo.**
2. **Los tests que ya existen son el contrato.** Antes de tocar nada, mirarlos. Nunca se borra ni se
   desactiva un test para que pase: o se arregla el cambio, o se actualiza el test **explicando por
   qué** el comportamiento nuevo es el bueno. Si no hay test de lo que se toca, **se escribe**.
3. **Todo el texto que ve el agricultor vive en `backend/app/textos.py`.** Ninguna pantalla se escribe
   una frase. Hay un test que busca, clave por clave, los textos que pide el JavaScript y falla si a
   alguno le falta su frase.
4. **Los colores viven solo en el `:root` de `estilos.css`.** Ningún componente pone un color.
5. **Un solo manejador de clics**, en `document`, que lee `data-accion` y los `data-*`. Las acciones
   que se pintan están inventariadas y hay un test que falla si alguna no la atiende nadie.
6. **Nada de datos inventados.** Lo que no se sabe se deja en blanco o se enseña «—». Nunca un cero
   que parezca un dato, ni un teléfono, ni un número que no se pueda comprobar.
7. **Ningún aviso sin salida**: si algo falta, al lado está el botón que lo arregla.
8. **Ningún secreto en el repositorio** (ni claves de cuenta, ni la clave de Stitch, ni tokens).
9. **Se escribe para un agricultor de 50 a 70 años que no sabe de informática**: nada de jerga
   («interfaz», «validación», «fitosanitario»…), y hay un test que lo comprueba palabra por palabra.
10. **Todo cambio mueve los números documentados** (el conteo de pruebas de `README.md`, `AGENTS.md` y
    `docs/LO_QUE_PIDE_LA_JUNTA.md` está comprobado por un test: si no coinciden, falla).

---

## 1. Qué es CUE Digital

**Un cuaderno de campo y cuaderno digital para agricultores**, autohospedado, que funciona en el
navegador. Lo está haciendo David para su propia explotación (Castilla y León, **64 tierras**), con
la idea de que si funciona bien lo pueda usar algún cliente más.

| | |
|---|---|
| **Para quién** | David, y la persona que le ayuda en la finca (el programa ya tiene varias cuentas en la misma finca) |
| **Ámbito** | Castilla y León para empezar, pero escrito para **cualquier cultivo y cualquier superficie**, secano y regadío. Nada está cableado a un cultivo concreto |
| **Régimen** | REAGP |
| **Prioridad declarada por David, por delante de todo** | que **no le falte de nada** y que sea **amigable para quien no sabe de informática** |
| **Lo que NO es** | no es facturación ni contabilidad. Facturas/Verifactu, factura electrónica B2B, bancos, economía, OCR de compras, NDVI y ganadería están **aplazados a propósito**, no olvidados |

### Por qué el programa está hecho así (las fechas que lo empujan)

| Obligación | Desde | Lo dice |
|---|---|---|
| Registro de **abonos** | 01/01/2026 | RD 1051/2022, art. 5 |
| **Plan de abonado** | 01/09/2026 | RD 1051/2022, art. 4.2 |
| **El registro de tratamientos en papel deja de valer** | 31/12/2026 | RD 1311/2012, art. 16.1 (RD 1039/2025) |
| Registro **electrónico** de productos aplicados | 01/01/2027 | RD 1311/2012 + Reglamento (UE) 2023/564 |

**Y lo que la ley NO obliga, que es lo que más se confunde** (está escrito en la propia pantalla de
ayuda, con las comillas y los enlaces al BOE en `docs/LO_QUE_OBLIGA_LA_LEY.md`):

- **Mandar el cuaderno a la Junta es voluntario** (art. 10.2 del RD 1054/2022).
- **Se puede llevar con un programa propio** (art. 10.3) si cumple el contenido mínimo del anexo II.
- **El cuaderno electrónico obligatorio empieza después de 2027**, con el siguiente periodo de la PAC,
  y solo para fincas grandes (más de 30 ha de cultivo, más de 5 ha de regadío o invernaderos de más de
  0,1 ha).

---

## 2. Lo que ha pedido David, en sus palabras, y en qué se ha traducido

| Lo que dijo (literal) | Cuándo | En qué se ha traducido |
|---|---|---|
| «que sea **amigable para un usuario que no sabe de informática**» | desde el principio | lenguaje llano con test de jerga, una pregunta por pantalla, botones de 64 px, todo lo que se pide explicado al lado |
| «**recuerda también dejar borrar las cosas que introduzca** porque puede que me equivoque, **o modificar** también» | rondas 91-93 | **CORREGIR** y **BORRAR** en todas las fichas (apuntes, tierras, grupos, los seis maestros, análisis, ventas, plan, papeles, facturas, años del cuaderno), con pregunta antes de borrar, «esto lo usa N apuntes» cuando está en uso, y registro de todo en `auditoria`. Un apunte firmado no se borra: **se anula** |
| «no he probado nada todavía, **en mi cuenta no salen las tierras**, además **no está rehecha la ui**, sigue siendo muy parecida, debe ser **responsive** para usarse en pc y móvil, **no solo móvil**. Hacer una **versión para pc que parezca una aplicación de gestión tipo SAP**, porque actualmente no es una app usable de gestión. **Vuelve a usar Stitch**, incluso, como debes **rehacer prácticamente todo, empezar de nuevo con las specs, funcionalidades, planes, páginas, ui**» | 30/09/2026 | es el encargo de esta tanda, y está desarrollado en los apartados 5, 6 y 7: documento nuevo de especificaciones (`docs/LA_APLICACION_DE_GESTION.md`), armazón de escritorio (menú lateral + barra), tablas y paneles de detalle, diseños de escritorio pedidos a Stitch, y marca de versión visible para saber qué se está viendo |
| «**metelo todo en mi cuenta**, davidpeve01@gmail.com» | antes | los datos están en **su** cuenta: 64 tierras y 3 años de cuaderno. La clave es la que él eligió y **no se escribe en ningún fichero del repositorio** (regla 8) |
| «hazle **más caso a Stitch** … **continua mejorando o rehaciendo toda la ui**» | antes | se le pide diseño a Stitch **para cada pantalla y cada pieza**, y la lista viva de lo pedido y lo aplicado es `docs/stitch/LO_QUE_FALTA_POR_DISENAR.md` |
| «usa **mucho más Stitch**, para cualquier diseño, para cualquier mínima cosa, **no pares hasta tener toda la app cubierta** con todas las funcionalidades y ui refactorizadas» | ronda 90 | **32 encargos** de móvil pedidos y aplicados, más **5 de escritorio** (los de la versión de gestión) |

### Y una cosa que conviene saber de «en mi cuenta no salen las tierras»

Se comprobó **con sus credenciales y en un navegador de verdad**: las 64 tierras **sí salen** («Tienes
64 tierras apuntadas», con la lista entera). El problema de verdad era **otro**: no había **menú**
ninguno, y nada en la pantalla de inicio decía que las tierras estuvieran detrás de un botón llamado
«Mis parcelas, productos y máquinas». De ahí sale la decisión del armazón de escritorio (apartado 5.1).

---

## 3. El estado, en números (30/09/2026)

| | |
|---|---|
| Pantallas en React | **29** (todas; no queda ninguna pantalla pintada a mano) |
| Piezas compartidas (`backend/web/react/piezas/`) | **10** |
| Módulos del menú lateral | **16** |
| **Tablas de escritorio** | **5**: tierras, cuaderno (apuntes), años del cuaderno, facturas y almacén |
| **Paneles de detalle** (ficha al lado de la tabla) | **2**: tierra y producto del almacén |
| Pruebas de Python (`pytest`) | **3422**, 0 fallos, 1 omitida |
| Pruebas de JavaScript (`node --test`) | **771**, 0 fallos |
| Prueba de humo (`scripts/humo.py`) contra un servidor de verdad | **33 secciones**, «todo correcto», 415 comprobaciones |
| Comprobación en un navegador de verdad | **todo correcto**: **44 rutas** de móvil y **7 de escritorio** (a 1440×900), con captura de las 7 de escritorio y de 6 de las de móvil |
| Diseños de Stitch | **32 de móvil** (`docs/stitch/rediseno/`) + **5 de escritorio** (`docs/stitch/escritorio/`), todos pedidos; **0 sin pedir** |
| Contrato de diseño (`designmd lint DESIGN.md`) | **0 errores, 0 avisos** |
| Versión que se está viendo | **`2026-09-30-53`**, la misma cadena que el nombre de la caché del *service worker* |

Cómo se usa hoy: el programa corre en `http://127.0.0.1:8000` con SQLite (`backend/cuedigital.db`), sin
levantar nada más. La cuenta de David tiene **64 tierras y tres años de cuaderno** (2026, 2025 y 2024),
comprobado con sus credenciales en un navegador de verdad el 30/09/2026.

---

## 4. Cómo está construido, y las reglas de forma que no se pueden romper

| Pieza | Qué se usa |
|---|---|
| Servidor | Python 3.12 + FastAPI + SQLAlchemy 2.0 |
| Base de datos | SQLite en local, PostgreSQL + PostGIS en producción |
| Interfaz | HTML, CSS y JavaScript **a pelo**, sin compilar. React 18 y `htm` van **ya compilados** en `backend/web/vendor/`, con su LEEME y su huella |
| Pruebas | `pytest` (Python) y `node --test` (JavaScript) |

**No hay `npm install`, ni Vite, ni TypeScript, y es una decisión, no un descuido**: el servidor donde
vive esto sirve ficheros estáticos y punto. React entró sin romper esa regla (ficheros UMD + `htm`,
que es JSX sin compilar). **React 19 no publica UMD**, así que no se puede subir de versión sin cambiar
la decisión; hay un test que lo impide a propósito.

### La forma de la interfaz (lo que se añadió en esta tanda)

1. **Una aplicación, dos formas de usarla**, y la elige **el CSS**, nunca el JavaScript:
   - **En el despacho (PC, desde 64 rem ≈ 1024 px)**: menú lateral fijo de 17 rem, barra de arriba
     (campaña + cuenta + APUNTAR), pantalla a todo el ancho, **tablas** con orden por cabecera y total
     al pie, y **panel de detalle al lado** de la lista.
   - **En el campo (móvil)**: exactamente lo de antes — pantalla de inicio con botones grandes,
     **tarjetas**, una cosa por pantalla, botones de 64 px.
2. **Las dos formas van en el mismo HTML** (`.solo-escritorio` y `.solo-movil`), así que **los datos,
   los textos y los `data-accion` son los mismos** y el manejador de clics sigue siendo **uno solo**.
   Los tests de cableado pulsan botones de verdad: si una acción se perdiera en la versión de
   escritorio, fallarían.
3. **La tabla es una pieza** (`react/piezas/tabla.js`): **no calcula nada**, todo se lo prepara
   `app.js`. Las cabeceras que ordenan son botones (`data-accion="ordenar-tabla"`), la flecha del orden
   la pone el CSS y la columna lleva `aria-sort`.
4. **El panel de detalle** se abre tocando **el nombre** de la fila (que es un botón, no la fila
   entera: un `<tr>` no se puede enfocar con el teclado), y se cierra volviendo a tocarlo.
5. **La ficha del armazón**: los formularios son **no controlados** (React pinta los campos con su
   `id` y `app.js` los lee: por eso decenas de pruebas escriben en ellos como lo haría una persona) y
   **las frases compuestas se montan en `app.js`**, no dentro de un componente.

---

## 5. Lo que está HECHO, módulo por módulo

Los módulos son los del menú lateral del ordenador. «Tabla» quiere decir que en el ordenador esa lista
se ve como tabla ordenable; en el móvil, como tarjetas.

| Módulo | Estado | Detalle |
|---|---|---|
| **Panel** (inicio) | a medias | la pantalla de inicio funciona (seis acciones, lo que falta por completar, el aviso de lo que queda sin mandar). **Falta el panel de mando de escritorio** (cuatro números del año, lo que falta con su botón, últimos apuntes): fase 4, con su diseño ya pedido a Stitch (`docs/stitch/escritorio/panel.png`) |
| **Cuaderno** | **hecho**, con **tabla** | apuntar producto / abono / trabajo / cosecha (el asistente de pasos), la tabla de los apuntes del año con total de hectáreas al pie, la ficha de cada apunte, corregir, borrar y **anular lo firmado**, firmar el año, sacar el cuaderno en papel y guardar los datos en un fichero |
| **Tierras** | **hecho**, con **tabla y panel** | las 64 tierras en tabla (Nº, Nombre, Hectáreas, Qué tiene este año, Acciones) con **orden por cabecera**, buscador, total de hectáreas al pie y **panel al lado** con la ficha de la tierra elegida, sus datos y sus botones. Alta por SIGPAC (buscando el pueblo y los trozos), por mapa o a mano; decir qué hay sembrado cada año; grupos de tierras |
| **Almacén** | **hecho**, con **tabla y panel** | la cesta: lo comprado, lo echado y lo que queda de cada producto, con su etiqueta de estado y el motivo cuando no se puede restar. **Tabla** (Producto, Comprado, Echado, Te queda, Estado, Acciones) con el pie diciendo cuántos hay y **cuántos hay que mirar**, y **panel** con la ficha del producto, **de dónde sale el número de lo comprado** y sus botones |
| **Compras y facturas** | **hecho**, con **tabla** | subir una factura (foto o PDF), que el programa la lea y **enseñar lo leído para confirmarlo o corregirlo**, el papel de cada factura (verlo o subirlo), la tabla de facturas con la columna del papel y el total del año al pie, corregir y borrar |
| **Análisis** | **hecho** (falta tabla) | los análisis de laboratorio (tierra, agua, planta, cosecha, residuos) con su boletín subido, la edad en su etiqueta y los números en su bloque; el **plan de abono** del año con su veredicto («En regla» / «Alerta: exceso») y la comparación con lo aportado |
| **Ventas** | **hecho** (falta tabla) | lo que se ha vendido, cada dato con su nombre, y el aviso cuando no cuadra con lo cosechado |
| **Productos y máquinas** | **hecho** (faltan tablas) | las seis fichas (productos, abonos, quién aplica, quién asesora, máquinas y naves), con alta, corrección y borrado |
| **Años del cuaderno** | **hecho**, con **tabla** | los años del cuaderno, cuál se está llevando, qué tiene cada uno dentro, corregir, borrar (con el BORRAR apagado y explicado si tiene cosas dentro) y empezar un año nuevo |
| **La Junta** | hecha la mitad | **traer las tierras** del cuaderno de la Junta (leyendo el fichero que descarga el agricultor) y **sacar el cuaderno relleno** (más firmarlo con AutoFirma). **Mandar el cuaderno por el canal oficial (IUWS) está pendiente** y bloqueado por cosas de fuera: ver el apartado 6.4 |
| **Ayuda y datos** | **hecho** | mis datos y mi finca, quién entra en la finca (varias cuentas y varias fincas), la ayuda con **lo que obliga la ley y lo que no** (con los artículos), y las medidas preventivas (lo que se hace sin echar producto) |
| **Otros**, que no son módulos del menú | **hecho** | el **mapa** para dibujar la tierra tocándola, el **dictado** (apuntar hablando, revisando antes de guardar), los **papeles** (documentación anexa con carpetas y ficheros), el **SIGPAC**, el **certificado digital** para entrar sin teclas, **funcionar sin cobertura** (cola en el móvil y aviso de lo que queda por mandar) y el **registro de todo** (`auditoria`) |

**Y las cosas que se arreglaron en esta tanda porque se vieron en una captura** (no las caza ninguna
prueba, y por eso están escritas):

1. **Pulsar una cabecera de la tabla de facturas ordenaba la lista de tierras** y te llevaba a otra
   pantalla sin decir nada. Ahora cada tabla ordena la suya y repinta la suya.
2. **Las cinco tablas tenían una celda de más** (la pieza ya pinta la columna de Acciones): los botones
   caían en una columna sin cabecera y la tabla se ensanchaba sola. Hay un test que lo impide.
3. **CORREGIR y BORRAR se apilaban** uno debajo de otro (cada fila, dos renglones) y los chips de
   estado largos («Todavía no has dicho qué hay aquí este año.») ponían la fila altísima: ahora en la
   celda va la etiqueta corta («Falta decirlo», «Cuadra») y la frase entera se queda en la tarjeta del
   móvil y en el panel.
4. **La cabecera de una tabla dentro de su contenedor se pegaba a la ventana** y tapaba la primera
   fila.
5. **«1 tierras» y «1 facturas»** en el pie de las tablas: las claves del singular estaban escritas
   `_una` (que es femenino) y el ayudante busca `_uno`. Ahora las cuatro bases están en el test que
   existe justo para esto.

---

## 6. Lo que QUEDA por hacer

### 6.1 El rediseño de escritorio, por fases (`docs/LA_APLICACION_DE_GESTION.md`)

| Fase | Estado |
|---|---|
| 0. Especificaciones nuevas | **hecha** (el documento existe y los diseños están en `docs/stitch/escritorio/`) |
| 1. El armazón (menú lateral + barra) | **hecha** |
| 2. Las tablas | **empezada**: 5 hechas (tierras, cuaderno, años, facturas, almacén). **Faltan**: los seis maestros (productos, abonos, quién aplica, asesores, máquinas, naves), los análisis y las ventas |
| 3. Los paneles de detalle | **empezada**: 2 hechos (tierra y producto). Faltan los de las otras tablas |
| 4. El panel de mando de escritorio | **pendiente** (es «donde está el salto que David nota»: cuatro números del año, lo que falta con su botón, los últimos apuntes, la franja de acciones documentales). Diseño pedido |
| 5. Los formularios en dos columnas, con el resumen al lado | **pendiente**. Diseño pedido (`docs/stitch/escritorio/formulario.png`) |
| 6. Las pantallas que faltan de cada módulo | **pendiente** (ventas, análisis, almacén y plan con la misma estructura de tabla+panel) |
| 7. Repaso final | **pendiente**: móvil entero otra vez, `DESIGN.md` revisado, los números de la documentación |

### 6.2 Lo que falta dentro de lo ya empezado

- **Filtros de verdad** en las tablas (hoy el único es el buscador de tierras que ya existía). Es lo
  que pidió David con «tablas con filtros y orden»: el orden está hecho, los filtros no.
- **El gasto en euros por producto** en el almacén: el diseño de Stitch lo dibuja, pero **ese número
  no existe** en el programa (las líneas de factura traen importe, pero no hay gasto por producto
  sumado para el año). Se pone el día que exista; inventarlo sería lo único que este programa no hace.

### 6.3 Las dos decisiones que esperan a David

1. **En qué año trabajas**: hoy el programa usa siempre el año más alto. Si se crea el 2027, todo lo
   que se apunte irá al 2027 y no habrá forma de seguir apuntando en 2026. ¿Se pone un **selector de
   año** en la barra de arriba? (Recomendación: sí.)
2. **Menú también en el móvil**: ¿el menú lateral aparece en el móvil (con un botón que lo abre) o no?
   (Recomendación: no, seguir entrando por la pantalla de inicio, que es lo que ya conoce.)

### 6.4 El cuaderno de la Junta por el canal oficial (IUWS): pendiente y bloqueado por fuera

Esto **no es rediseño**, es otra cosa y va por su cuenta. Estado real (documentado en
`docs/INTEGRACION_IUWS.md`, **revisado el 23/09/2026**: los números de ese documento son de esa fecha,
no se han vuelto a comprobar hoy):

- Los **18 bloques** del cuaderno están cotejados campo por campo: **113 campos obligatorios**, de los
  que **61** tienen fuente y tipo traducibles; los otros 52 se reparten entre códigos oficiales, datos
  que aún no se preguntan y conversiones por confirmar.
- **El bloqueo gordo son los valores de los catálogos de SIEX**: su estructura es pública y ya se sabe
  qué tabla es la de 15 de los 40 catálogos, pero **los datos de cada tabla están detrás de un
  captcha**.
- Además hace falta el **certificado, el alta y el nombre comercial** de David para probar el envío
  autenticado.
- Las direcciones, los métodos y los correos para pedir acceso están comprobados y escritos en ese
  documento (los de Castilla y León son `https://servicios.ayg.jcyl.es/IUWS/api/` y el entorno de
  integración `https://sga.entornointegracion.es`).

**Importante para no confundir a nadie:** mandar el cuaderno a la Junta es **voluntario** (art. 10.2),
y este programa ya sirve para lo obligatorio: tener el registro y poder enseñarlo.

### 6.5 Cuatro ideas de diseño que necesitan algo que hoy no existe

Están apuntadas con su motivo, no descartadas: **«ver entradas y salidas de este producto»** (sería una
pantalla nueva), **«te llega para unas N hectáreas»** (esa cuenta la tiene que hacer el **servidor**),
**«apuntar tratamiento a las N»** (un atajo que abra el asistente con el grupo ya elegido) y **el
resumen vivo del papel mientras se escribe** (pide que la pantalla guarde el estado de los campos, que
es justo lo que este proyecto no hace).

---

## 7. Stitch: cómo nos ayuda con la interfaz y cómo se usa desde aquí

### 7.1 Qué es y por qué se usa

[Stitch](https://stitch.withgoogle.com) es la herramienta de diseño con IA de Google: se le describe una
pantalla con palabras y devuelve un diseño (y código). Desde la ronda 76 **se llama desde este
proyecto**, y desde la ronda 90 se le pide diseño **para cada pantalla y cada pieza**.

**La clave de por qué funciona tan bien aquí:** lo que se le sube a Stitch es **nuestro `DESIGN.md`**
(el contrato de diseño del proyecto: colores, tipos, medidas y reglas), así que **diseña dentro de
nuestras reglas**. Comprobado: los colores que más usa son **los del `:root` de `estilos.css`, uno por
uno**. Lo que aporta un diseño, por tanto, no es repintar nada: es **jerarquía y señales**.

### 7.2 Cómo se pide un diseño (comandos, y la clave)

```bash
cd backend
$env:STITCH_API_KEY="<la clave>"     # NUNCA se escribe en un fichero del repositorio

# ver los proyectos que hay
../.venv/Scripts/python.exe scripts/disenar_con_stitch.py --listar

# las pantallas de móvil que todavía no tienen diseño pedido
../.venv/Scripts/python.exe scripts/disenar_con_stitch.py --nuevas <ID_DEL_PROYECTO>

# una pantalla concreta
../.venv/Scripts/python.exe scripts/disenar_con_stitch.py --pantalla cesta --todas <ID_DEL_PROYECTO>

# los diseños de la versión de ESCRITORIO (aplicación de gestión, 1440x900)
../.venv/Scripts/python.exe scripts/disenar_con_stitch.py --escritorio <ID_DEL_PROYECTO>
```

- El **sistema de diseño** (el `DESIGN.md` ya subido) tiene su identificador y **hay que pasarlo en cada
  pantalla**: sin él, Stitch usa un sistema suyo y las pantallas salen con otro estilo.
- Las respuestas crudas se guardan en `docs/stitch/` (móvil, en `docs/stitch/rediseno/`) con su
  captura, y los de escritorio en `docs/stitch/escritorio/`. Así el trabajo de diseño queda
  documentado: **qué se pidió, qué se obtuvo y cuándo**, sin depender de una dirección de Google que
  caduca.

### 7.3 Las dos familias de diseños que hay

| Familia | Cuántos | Dónde | Para qué |
|---|---|---|---|
| **Móvil** | **32** encargos (las 29 pantallas + una lámina de piezas + dos láminas de estados nuevos) | `docs/stitch/rediseno/` | la aplicación de campo: tarjetas, botones grandes, una pregunta por pantalla |
| **Escritorio** | **5** encargos: `estructura`, `panel`, `cuaderno`, `formulario` y `almacen` | `docs/stitch/escritorio/` | la aplicación de gestión a 1440×900: el armazón con menú y barra, el panel de mando, la tabla del cuaderno, los formularios en dos columnas y la tabla del almacén |

Cada diseño viene con su `.png` (y su `_grande.png`), su `.html` y su `_explicacion.md`, que es lo que
de verdad se lee: ahí Stitch cuenta **qué decisiones ha tomado y por qué**.

### 7.4 Cómo se aplica un diseño (y cómo no)

1. **Se mira la lámina y su explicación**, y se coge **la disposición, la jerarquía y los dibujos**.
2. **Los textos NO se copian**: Stitch reescribe las frases («Bichos, hierbas u hongos tratados» donde
   nosotros decimos «bichos, hierbas, hongos»). Los textos los siguen poniendo `textos.py`, y si un
   diseño pide una frase nueva, se escribe allí y pasa el test de jerga.
3. **Los colores no se copian**: se usan los del `:root`.
4. **El diseño no se pega como código**: Stitch devuelve React + Tailwind y aquí no hay compilación. Se
   implementa a mano con las piezas que ya existen.
5. **Se comprueba en un navegador de verdad** (`scripts/comprobar_en_un_navegador.py`) y se mira la
   captura, que es donde salen los fallos que ninguna prueba caza (los cinco del apartado 5 salieron
   así).
6. **Se apunta qué se aplicó y qué no**, con el motivo, en `docs/stitch/LO_QUE_FALTA_POR_DISENAR.md`
   (la lista viva) y en `docs/MEJORAR_LA_INTERFAZ_CON_STITCH.md` (el detalle por rondas).

### 7.5 Lo que un diseño ha pedido y NO se ha aplicado (con el motivo, y es una decisión)

- **La barra de pestañas de abajo** (Cuaderno / Parcelas / Historial / Ajustes): añadiría pantallas que
  hoy no existen y un menú que hay que aprender.
- **Un segundo bloque verde oscuro** para explicar el almacén: el bloque oscuro es **el de la
  inspección** (lo único que se hace con alguien delante), y un segundo le quitaría a aquel lo que lo
  hace útil.
- **Tarjetas para productos, máquinas y naves**: el dato que hace falta para elegir **ya está en el
  botón**, y esas cosas no tienen forma que dibujar (que es lo que hace útil la tarjeta de una tierra).
- **Un teléfono de ayuda en la pantalla de tierras**: no tenemos el número, y escribir uno inventado es
  lo que este proyecto no hace.
- **El resumen vivo del papel mientras se escribe**: pide que la pantalla guarde el estado de los
  campos, que es justo lo que este proyecto no hace (los lee `app.js` por su `id`).
- **«Tu firma sigue siendo válida»** después de corregir algo firmado (ronda 91): **se rechaza de
  plano**, porque es lo contrario de lo que dice este programa.
- El resto, con su motivo, en el apartado «Lo que el diseño pedía y NO se ha aplicado» de
  `docs/MEJORAR_LA_INTERFAZ_CON_STITCH.md`.

### 7.6 Cuatro trampas de la API de Stitch (ya resueltas, escritas para no volver a tropezar)

1. El `projectId` va **sin** el prefijo `projects/`; con el nombre completo contesta «invalid argument».
2. Después de subir el `DESIGN.md` hay que **crear el sistema de diseño** (es un segundo paso que no se
   hace solo).
3. **Cada pantalla se pide con su `designSystem`**.
4. **Tarda minutos y no se reintenta**: si la llamada se corta, se pregunta por la pantalla con
   `get_screen`, no se vuelve a pedir (se duplicaría).

---

## 8. Cómo se comprueba todo (comandos exactos)

```bash
cd backend

# 1) Las pruebas de Python (3422). En Windows, el intérprete del entorno del proyecto
$env:CUEDIGITAL_ENTORNO="pruebas"; $env:CUEDIGITAL_ITERACIONES_PBKDF2="1000"
../.venv/Scripts/python.exe -m pytest -q -p no:randomly

# 2) Las pruebas de JavaScript (643), que pulsan botones de verdad
node --test "tests_js/*.test.js"

# 3) El recorrido completo contra un servidor de verdad (31 secciones)
../.venv/Scripts/python.exe -m uvicorn app.main:app --port 8012      # en otra terminal, con base de datos de usar y tirar
../.venv/Scripts/python.exe scripts/humo.py http://127.0.0.1:8012

# 4) La comprobación en un navegador de verdad (abre Chrome sin ventana y deja capturas)
../.venv/Scripts/python.exe scripts/comprobar_en_un_navegador.py http://127.0.0.1:8010

# 5) El contrato de diseño
cd .. ; npx --yes -p "@google/design.md" designmd lint DESIGN.md      # 0 errores, 0 avisos
```

**Las tres reglas de oro para probar cosas sucias** (el humo y el navegador crean cuentas y datos):
1. Se levanta un **servidor aparte con base de datos de usar y tirar** (`CUEDIGITAL_DATABASE_URL` a un
   fichero temporal), nunca la base de datos de verdad.
2. `CUEDIGITAL_CONFIAR_EN_CABECERAS=1` solo en ese servidor de pruebas (es lo que deja entrar sin
   certificado).
3. **Al terminar, se para ese servidor y se borra lo temporal.** Un servidor de pruebas olvidado en un
   puerto ha dado más de un quebradero de cabeza.

**Y si se toca código de Python (por ejemplo `textos.py`), hay que reiniciar el servidor**: los textos
se sirven desde memoria, así que sin reiniciar se sigue viendo lo viejo aunque el fichero esté
cambiado. La marca de versión del pie (`versión 2026-09-30-53`) está justo para eso: dice qué se está
viendo de verdad.

---

## 9. Trampas del entorno ya conocidas (Windows)

- **`Set-Content -Encoding utf8` en PowerShell añade BOM** y estropea los ficheros de texto del
  proyecto (hay que escribir sin BOM).
- **`pytest -q` no imprime la línea de resumen** bajo PowerShell: los números se leen del
  `--junit-xml` (`$x.testsuites.testsuite`), no de la salida por pantalla.
- **Los números de pruebas documentados están comprobados por un test**: si se añaden pruebas y no se
  actualizan `README.md`, `AGENTS.md` y `docs/LO_QUE_PIDE_LA_JUNTA.md`, la suite falla a propósito.
- **Cuidado con las sustituciones de texto** tipo `.Replace("N tests", …)`: se cuelan en sitios que no
  tocan. Mejor una expresión regular anclada.
- **Los ficheros se escriben en UTF-8** y el programa habla español: hay que forzar
  `PYTHONIOENCODING=utf-8` al ejecutar comillas por consola.

---

## 10. Lo que hay que decirle a David, sin adornos

**Lo que funciona hoy, comprobado:** las 64 tierras con su tabla y su panel, el cuaderno del año con su
tabla, los años del cuaderno, las facturas, el almacén con sus cuentas y su panel, corregir y borrar
todo lo que se introduce, y todo lo demás del apartado 5. En el ordenador, con menú lateral y tablas;
en el móvil, como estaba.

**Lo que todavía no está:** el panel de mando de escritorio (fase 4), los formularios en dos columnas
(fase 5), las tablas de los seis maestros, los análisis y las ventas, los **filtros** de las tablas, y
el **envío del cuaderno a la Junta** por el canal oficial (que está bloqueado por los catálogos de
FEGA y el certificado, no por este programa).

**Dos preguntas esperando respuesta:** el **selector de año** en la barra (recomendación: sí) y si el
**menú** aparece también en el móvil (recomendación: no).

---

## 11. Dónde está cada cosa (mapa de la documentación)

| Documento | Para qué |
|---|---|
| `AGENTS.md` | **Manda sobre todos.** Cómo se trabaja aquí, las reglas y los comandos de prueba |
| `docs/LA_APLICACION_DE_GESTION.md` | **Las especificaciones nuevas**: la aplicación de gestión, los 13 módulos, los tres flujos, el plan por fases y lo que trajo cada fase |
| `DESIGN.md` | El contrato de diseño (colores, tipos, medidas, la parte de móvil y la de escritorio). Es lo que se le sube a Stitch |
| `docs/stitch/LO_QUE_FALTA_POR_DISENAR.md` | **La lista viva de Stitch**: qué está pedido, qué aplicado y qué queda, pantalla por pantalla |
| `docs/MEJORAR_LA_INTERFAZ_CON_STITCH.md` | Qué es Stitch, cómo se llama desde aquí y **qué trajo cada ronda** (76 a 93), con lo que se rechazó y por qué |
| `docs/REACT.md` | La guía de la interfaz: las pantallas, las piezas, los pasos del asistente, la versión de ordenador y los contratos que vigilan los tests |
| `docs/CORREGIR_Y_BORRAR.md` | Corregir y borrar: cómo funciona, qué queda registrado y qué dijo Stitch de esto |
| `docs/LO_QUE_OBLIGA_LA_LEY.md` | Lo que la ley obliga y lo que no, con los artículos y los enlaces al BOE |
| `docs/LO_QUE_PIDE_LA_JUNTA.md` | La lista de lo que pide el cuaderno oficial, punto por punto, con su estado |
| `docs/INTEGRACION_IUWS.md` | El envío oficial (IUWS): direcciones, métodos y qué falta, con lo revisado el 23/09/2026 |
| `docs/CUADERNO_DE_LA_JUNTA.md` | El cuaderno de la Junta: leerlo, traer sus tierras y sacarlo relleno |
| `docs/TRASPASO_A_OTRO_AGENTE.md` | Traspaso anterior (23/09/2026): sigue valiendo para el contexto del IUWS y del mapeo, pero **sus números de pruebas (2465 y 545) son de aquella fecha**: los de hoy están en el apartado 3 de este documento |
| `README.md` | Cómo se arranca, cómo se entra con certificado, cómo se firma y cómo se prueba |
