# Arquitectura de pantallas — CueDigital para el agricultor

> **Para qué es este documento.** David cambió el rumbo el 2026-11-04: la interfaz anterior no le
> gustaba y el producto pasa a ser **la herramienta digital del agricultor de Castilla y León**.
> Esto es la **propuesta de pantallas y flujos** para que la apruebe **antes** de implementar nada.
> El aspecto visual está en dos artefactos aparte: el **sistema de diseño**
> (`designs/cue-agricola-design-system/`) y los **artboards** (`designs/cue-agricola/`), que se
> abren con los enlaces que se pasan al final.
>
> **Fuentes**: [`ALCANCE-AGRICOLA.md`](../ALCANCE-AGRICOLA.md) (manda), la investigación oficial
> [`INVESTIGACION-AGRICOLA.md`](../INVESTIGACION-AGRICOLA.md) (URL y fecha en cada dato), el
> código que ya existe (`backend/app/`) y la comparación de competencia del 2026-11-04.
>
> **Lo que NO es**: código. Ni una pantalla implementada, ni una migración, ni un cambio de la API.
>
> **Estado: APROBADA CON CORRECCIONES (2026-11-05).** David vio el canvas y dio el visto bueno con
> ocho correcciones, más la regla de la doctrina §8 (*la interfaz no habla de cómo está hecha*). Este
> documento ya las incorpora; el detalle de dónde cae cada una está en el apartado 0.

---

## 0 · Las correcciones de David (2026-11-05), y dónde caen

| # | Corrección | Dónde se resuelve |
|---|---|---|
| 1 | **Las parcelas no tienen por qué estar juntas** ni caber en una imagen | S02 y S09: zoom, agrupación y selección; nunca se supone una finca única |
| 2 | **Leer facturas de fotos** (OCR) para sacar los datos | S08 y S12: foto → propuesta leída, revisión campo a campo, original a la vista |
| 3 | **Cuaderno guiado**: decir qué necesita para rellenarlo | S04: campos obligatorios, qué falta, avisos que no bloquean |
| 4 | **Productos y abonos con dosis por hectárea** | S12: lista, proporción por hectárea y total |
| 5 | **Favoritos** de productos, abonos y tratamientos | S12: en los selectores y en apuntar |
| 6 | **PAC y años anteriores**: importar o modificar, evolución de la tierra, producción estimada y variedad | S07-bis (histórico) y S03 (ficha con «otros años») |
| 7 | **Registro de parcelas fácil**: guiado o importando una PAC | S02-bis (alta guiada) y S07-bis |
| 8 | **Panel de tierras con mapa**: seleccionar cada tierra y ver sus datos y otros años | S02: lista ↔ mapa ↔ panel ↔ años |
| 9 | **Doctrina §8**: la interfaz no habla de cómo está hecha | Principio 11 y la regla de textos del apartado 6 |

---

## 1 · Los principios que deciden las pantallas

1. **El campo primero, pero no solo el campo.** La misma aplicación sirve de pie en una parcela
   (móvil, una mano, sol, sin cobertura) y sentado en el despacho (PC, tablas, cuentas, PAC). No es
   una web que se encoge: son dos densidades del mismo producto.
2. **Mis parcelas primero.** Sin las parcelas del SIGPAC no hay cuaderno, ni PAC, ni nada. La
   primera pantalla que el agricultor ve al entrar por primera vez es **traer sus parcelas**.
3. **Un objeto, una ficha.** Cada cosa (parcela, apunte, campaña, documento) tiene **una ficha
   única** a la que se llega desde cualquier sitio. Nada de «dos caminos a las tierras».
4. **Lista + filtros + estado + actividad** (las ideas de CRM que pidió David): toda lista tiene
   buscador, dos o tres filtros en chips con contador, y un estado con **palabra + icono**.
5. **El mapa es un selector, no un destino aparte.** Se toca el recinto y su ficha se abre encima.
6. **Apuntar en 30 segundos**: máximo **3 pantallas** y **8 campos** para un apunte normal; el resto
   se rellena solo (parcela, campaña, fecha, producto de la última vez) o se deja para después.
7. **Sin cobertura no se pierde nada**, y se dice: «guardado en el móvil» solo si de verdad se
   guardó; la cola se ve y se manda sola.
8. **Los cuatro estados** (vacío, cargando, error, sin permiso) están diseñados en cada pantalla;
   nunca un fallo pintado como vacío.
9. **Nada de datos inventados**: lo que no consta se escribe «no consta»; los plazos y formatos
   legales van con su fuente y su fecha o no se enseñan.
10. **La exportación está al lado de la lista**, no escondida en ajustes: el agricultor exporta
    cuando se lo piden, no cuando navega.
11. **La interfaz no habla de cómo está hecha** (doctrina §8, 2026-11-05): nada de detalles técnicos,
    ni de cómo se calcula un número, ni avisos internos, ni textos de relleno. Lo que no le sirve al
    agricultor para decidir o actuar **se borra, no se sustituye por otro texto**.

---

## 2 · Navegación

### Móvil (390 px; también 360)

Barra inferior fija de **5 destinos**, siempre igual:

| Destino | Qué abre |
|---|---|
| **Hoy** | La finca delante: estado, lo último, lo que falta para la PAC, aviso sin cobertura |
| **Parcelas** | Lista con buscador y filtros; el mapa se despliega arriba y al tocar un recinto abre su ficha |
| **Apuntar** (botón redondo central, 64 px) | El asistente de 30 s: tratamiento, labor, siembra o fertilización |
| **Cuaderno** | Todo lo apuntado, por campaña y por fecha, con filtros y exportar |
| **Más** | Campaña, PAC y subvenciones, Documentos, Mis datos, Quién entra, Ajustes, Ayuda |

**Mapa**: se abre a pantalla completa desde Parcelas o desde la ficha (no es un destino de la barra).

### Tableta (768–1024 px)

Barra lateral **colapsable** con los mismos destinos y el contenido en dos columnas cuando aporta:
lista + mapa, lista + ficha. Los formularios se pueden rellenar de pie con el pulgar.

### PC / despacho (1024–1440 px)

Barra lateral **fija** (240 px) + barra superior con: nombre de la finca, **selector de campaña**,
buscador global, estado de conexión/cola y cuenta. Contenido a **1180 px** como máximo.

Estructura de la barra lateral, en orden de valor: **Hoy · Parcelas · Cuaderno · Campaña · PAC y
subvenciones · Documentos**, y abajo, separado: **Mis datos · Quién entra · Ajustes**.

> **Lo que se retira**: la portada de seis botones y el menú de 21 renglones. Eran los dos defectos
> que David señaló como «no me gusta nada» y los que la revisión de producto ya documentó
> (`docs/REVISION_PRODUCTO_2026-10-19.md`).

---

## 3 · Las pantallas

Prioridad **P0** = lo que hay que hacer primero para que el producto exista. **P1** = siguiente
entrega. Cada pantalla lleva: para qué, qué enseña, qué se puede hacer, qué estados tiene y de qué
datos vive.

### P0 · S01 — Hoy (móvil, tableta y PC)

- **Para qué**: que el agricultor sepa en 5 segundos qué tiene delante y pueda apuntar sin buscar.
- **Enseña**: finca y campaña activas; estado de conexión y cola («Sin cobertura · 3 apuntes
  esperando»); **un** botón principal («Apunta lo que has hecho»); lo último apuntado (3–5 filas
  con qué, dónde, cuándo y estado); **«te falta para la PAC»** (1–3 huecos, cada uno con el botón
  que lo arregla); resumen de la campaña (hectáreas, cultivos, tratamientos pendientes de cerrar).
- **Acciones**: apuntar (4 tipos), ir a una parcela, abrir el cuaderno, resolver un hueco de PAC.
- **Estados**: vacío (sin parcelas → «trae tus parcelas del SIGPAC» y su botón); cargando (última
  actividad); error (la tarjeta afectada, con reintento; el resto sigue usable); sin permiso
  (ayudante sin acceso a PAC → se explica quién puede y dónde se pide).
- **Datos**: parcelas, campaña, apuntes recientes, cola local, checklist PAC.

### P0 · S02 — Mis parcelas (lista + mapa + ficha) (las tres densidades)

- **Para qué**: el objeto central del producto.
- **Enseña**: contador con superficie («64 parcelas · 128,4 ha»); buscador; chips de filtro por
  **cultivo**, **municipio**, **uso SIGPAC** y **estado** (con contador en cada chip); lista de
  filas con alias, superficie, cultivo y estado (palabra + icono); **mapa** con ortofoto y lindero
  (se puede plegar; en PC va al lado); al seleccionar, **ficha rápida** con los datos del SIGPAC y
  las acciones.
- **Acciones**: buscar, filtrar, ordenar, seleccionar varias (para exportar o preparar PAC),
  tocar el recinto, abrir ficha, **traer parcelas del SIGPAC**, exportar la vista.
- **Parcelas dispersas (corrección 1 y 8)**: la finca **no se supone junta**. El mapa tiene **zoom**
  (rueda, botones y pellizco), **«ver todas»** para volver al encuadre que abarca todas las tierras, y
  **agrupación** por municipio o cultivo cuando hay muchas. La **selección** va en los dos sentidos:
  tocar una fila centra y resalta su recinto; tocar un recinto selecciona su fila. Si hay tierras en
  municipios distintos, se dice en la cabecera («4 municipios») y el mapa lo asume.
- **Panel de tierras (corrección 8)**: lista a la izquierda, mapa a la derecha y, debajo o al lado, el
  **panel de la tierra seleccionada** con sus datos del SIGPAC, su campaña actual y **sus registros de
  otros años** (con un acceso «ver años»).
- **Estados**: vacío con el botón de importar; cargando (esqueleto de filas, no spinner ciego);
  error de red conservando lo ya cargado + reintento; sin permiso (ver finca ó 404, nunca datos de
  otra finca).
- **Datos**: `Parcela`, `VersionDeRecinto` (identidad y versiones del recinto), catálogos SIGPAC
  (`data/sigpac/`), `Campana`.

### P0 · S02-bis — Alta de parcelas, fácil (corrección 7)

- **Para qué**: que el agricultor tenga sus parcelas sin pelearse con códigos.
- **Dos caminos, el mismo destino**:
  1. **Guiado**: elige municipio → busca por polígono/parcela/recinto o toca en el mapa → se le enseña
     **qué ha encontrado y su superficie antes de aceptar** (un dedo en una linde es otra parcela) →
     confirma y se añade. Si ya la tiene, se avisa y no se duplica.
  2. **Importando lo que sí existe (verificado el 05/11/2026)**: la **exportación de recintos por
     campaña** de la Junta (2023–2026, texto o Excel, sin certificado), el **Cuecyl `.xlsx`** de una
     campaña (el programa ya lo lee) o el **PDF del formulario S-X** cuando trae texto. Se añaden solas
     las tierras que falten, se avisa de lo que no se ha podido leer y **nunca se pisa una tierra
     existente**. Si no hay fichero, se mete a mano con el paquete preparatorio.
- **Estados**: vacío, cargando, error de lectura (con «meterlo a mano»), recinto ya añadido, sin permiso.
- **Límite declarado**: **no existe un fichero oficial de la solicitud PAC declarada**; la app de la
  Junta la cumplimenta y firma con certificado y reimporta el año anterior dentro de ella. Los formatos
  de «Documentos del expediente» y la descarga del Cuecyl de años anteriores están **pendientes de
  verificar**.
- **Los dos vídeos de referencia de David (revisados el 05/11/2026)**: **no son de SIGPAC** —son dos
  tutoriales de ArcGIS Pro y QGIS, en inglés—, así que no se ha inventado un flujo con ellos (ver
  `INVESTIGACION-AGRICOLA.md`, apartado 9 ter). El registro se queda con las dos vías verificadas, y
  **cuando David pase los vídeos correctos** se ajusta con su flujo real.
- **El listón, escrito para que se cumpla**: el registro tiene que ser **al menos tan fácil como
  esto**, y si no, no vale:
  1. **Buscar**: por los siete códigos o tocando el mapa. **Sin teclear códigos si no se quiere**.
  2. **Ver antes de aceptar**: qué ha encontrado, con su superficie, uso, coeficientes y región.
  3. **Añadir** con un toque, con aviso si ya la tiene y con opción de quitar.
  O bien: **traer un fichero** (recintos por campaña, Cuecyl o S-X), ver la lista de lo encontrado y
  aceptar lo que falte. **Nunca más de esos tres pasos para una tierra**, y nunca pedirle que se sepa
  un código de memoria.

### P0 · S03 — Ficha de parcela (las tres densidades)

- **Para qué**: todo lo de una tierra en un sitio.
- **Enseña**:
  - **Cabecera**: alias, superficie, municipio, cultivo de la campaña, estado.
  - **Mapa** con el/los recintos y sus linderos (tocar abre el mapa grande).
  - **Identidad SIGPAC** (tarjetas `label`/valor): provincia, municipio, agregado, zona, polígono,
    parcela, recinto, uso SIGPAC, coeficiente de admisibilidad (si consta), superficie del recinto;
    **«no consta»** cuando falta, nunca 0.
  - **Campaña actual**: cultivo, siembra, superficie sembrada, estado.
  - **Actividad** (línea de tiempo): tratamiento, labor, siembra, fertilización, foto, documento.
  - **PAC**: si está incluida en la solicitud, con qué cultivo/región y qué le falta.
  - **Documentos y fotos** de esa tierra.
  - **Otros años** (corrección 6): una tabla corta por campaña —año, cultivo, superficie, **variedad
    de semilla** y **producción estimada (kg/ha)**—, con las celdas que el agricultor puede rellenar o
    corregir. Lo que no consta se queda vacío («no consta»), no en cero.
- **Acciones**: apuntar en esta parcela, ver histórico completo, abrir el mapa, preparar la PAC,
  exportar la ficha (PDF), editar alias (no los datos del SIGPAC, que son de la administración).
- **Estados**: los cuatro; el vacío de «actividad» dice qué se puede apuntar y ofrece el botón.
- **Datos**: `Parcela`, `ParcelaCultivo`, `Labor`, `TratamientoFitosanitario`,
  `RegistroFertilizacion`, `Siembra`, `DocumentoAnexo`, `FotoDeLaPac`.

### P0 · S04 — Apuntar en 30 segundos (móvil; en PC, formulario ancho)

- **Para qué**: que un tratamiento o una labor se apunte de pie en el campo sin pelearse.
- **Flujo (3 pantallas, 8 campos)**:
  1. **Qué**: cuatro botones grandes: **Echar producto · Abonar · Sembrar · Hacer un trabajo**
     (y «lo mismo que la última vez», que rellena producto y dosis).
  2. **Dónde**: parcelas recientes arriba, buscador, «la que tengo cerca» (GPS) y «tocar en el
     mapa». Se puede elegir más de una.
  3. **Datos y foto**: producto (con la dosis de la última vez o la del registro), dosis y unidad,
     superficie tratada (calculada si se sabe, editable), fecha; **foto del envase o del papel**;
     guardar.
- **Reglas**: el botón de guardar siempre visible; **guardar y apuntar otro**; lo apuntado sin
  cobertura se queda en la cola con su estado; no se bloquea por un campo opcional; si falta algo
  legal se avisa **antes** de guardar y se puede completar luego; nunca se inventa la dosis.
- **Cuaderno guiado (corrección 3)**: antes de guardar, un panel dice **qué necesita el apunte para
  ser válido** (los datos con nombre y número), **qué falta** y qué se puede completar después, con el
  botón que lleva a cada cosa. Ejemplo: «Para que valga, faltan el producto y la dosis» → «Poner el
  producto» / «Poner la dosis» / «Guardar y completar luego». **No bloquea por un dato opcional** y
  nunca inventa la dosis.
- **Estados**: guardando (con progreso real), guardado en el móvil, guardado en el servidor,
  rechazado por el servidor (con el motivo y el botón para arreglarlo), sin permiso.
- **Datos**: `TratamientoFitosanitario`, `Labor`, `RegistroFertilizacion`, `Siembra`; catálogo
  oficial de productos (ver investigación; hoy hay `ProductoFitosanitario` y `Fertilizante`).

### P0 · S12 — Productos, abonos, dosis y favoritos (móvil y PC)

- **Para qué**: elegir bien lo que se echa, sin teclear de más (correcciones 4 y 5).
- **Enseña**: lista de **productos y abonos** con buscador y **favoritos** (tus productos, abonos y
  tratamientos de siempre) y «los que has usado hace poco»; al elegir uno, la **dosis por hectárea**
  de la etiqueta o la última usada, con su unidad, y el **total** para la superficie.
- **Acciones**: marcar/desmarcar favorito, elegir producto, cambiar dosis y unidad, ver el total,
  guardar. La dosis **no se inventa**: si no hay dato, el campo queda vacío y se avisa.
- **Estados**: vacío («aún no tienes productos» + botón), cargando, error, sin permiso.
- **Datos**: `ProductoFitosanitario` (incluye `dosis_maxima` y `unidad_dosis`), `Fertilizante`,
  `Semilla`; los favoritos son nuevos (tabla por finca y cuenta).

### P0 · S05 — Cuaderno (las tres densidades)

- **Para qué**: ver, corregir y exportar lo apuntado.
- **Enseña**: lista agrupada por campaña y fecha; filtros por tipo, parcela, cultivo y estado
  (borrador/confirmado/en cola); cada fila con qué, dónde, cuándo, quién y estado; detalle con la
  foto y el original; anular **con motivo** (nunca borrar).
- **Acciones**: filtrar, abrir, corregir, anular con motivo, exportar (PDF/Excel) y **volcar a la
  Junta** el día que esté disponible (hoy: `docs/INTEGRACION_IUWS.md`).
- **Estados**: vacío («todavía no has apuntado nada» + botón), cargando, error, sin permiso.
- **Datos**: `Labor`, `TratamientoFitosanitario`, `RegistroFertilizacion`, `Siembra`, `Auditoria`.

### P0 · S06 — Campaña (PC y tableta; móvil en «Más»)

- **Para qué**: qué se ha hecho en cada parcela, en orden, y comparar campañas.
- **Enseña**: selector de campaña; resumen (hectáreas, cultivos, tratamientos, siembras, labores);
  vista **por parcela** (una fila por tierra, con su actividad) y vista **por fecha** (línea de
  tiempo de toda la finca); coste/ingreso **solo si el dato existe** (hoy hay gastos y ventas en el
  backend: se podrán enganchar en P1, no se inventan).
- **Acciones**: cambiar campaña, filtrar, abrir ficha, exportar el resumen.
- **Estados**: los cuatro; el vacío de una campaña nueva ofrece «apuntar lo primero».

### P0 · S07 — PAC y subvenciones (PC y tableta; móvil: versión resumida de solo lectura)

- **Para qué**: preparar lo que pide la administración y tenerlo listo para presentar.
- **Enseña**:
  - **Lista de comprobación** con estado por requisito (hecho / pendiente / no puedo saberlo), cada
    uno con el botón que lo arregla y el enlace a la fuente oficial.
  - **Tabla de superficies**: por parcela y recinto, superficie SIGPAC, superficie declarada,
    cultivo, región; la **diferencia** marcada y explicada (no un número rojo sin motivo).
  - **Cultivos y regiones** de la campaña, con lo que consta y lo que falta.
  - **Documentación** adjunta (fotos, facturas, contratos) y qué falta.
  - **Plazos** con fecha y fuente (solo si están verificados; si no, «por confirmar» y el enlace).
    **Comprobado el 04/11/2026**: la convocatoria PAC 2026 (Orden 27/01/2026, BOCYL 30/01/2026) tuvo
    plazo del 1 de febrero al 30 de abril, ampliado hasta el 15 de mayo; a día de hoy está
    **cerrada**, y la de 2027 **no está publicada**.
  - **Lo que de verdad se puede hacer**: preparar el **paquete para presentar** (por recinto:
    referencia SIGPAC, superficie SIGPAC frente a cultivada, cultivo, práctica, región, importe
    estimado y **lo que falta**), exportarlo para el asesor y **enlazar al trámite exacto** de la
    Junta. La solicitud se cumplimenta y se firma **en la aplicación de la Junta con certificado**
    (`ayg.jcyl.es` / `particulares.ayg.jcyl.es`); **no hay API pública de presentación localizada**
    (04/11/2026). El programa **no promete presentar ni firmar**: deja todo listo y dice qué queda.
- **Acciones**: marcar requisito, abrir la parcela, adjuntar documento, exportar el paquete, abrir el
  trámite oficial.
- **Estados**: los cuatro; el vacío («aún no hay campaña preparada» + botón).
- **Datos**: `Subvencion`, `FotoDeLaPac`, `ParcelaCultivo`, `DocumentoAnexo`; lo que publique la
  Junta (ver investigación: **pendiente** de verificar el modelo de solicitud y los ficheros).

### P0 · S07-bis — Histórico de la PAC y evolución de una tierra (PC y tableta)

- **Para qué**: ver cómo ha cambiado una tierra año a año y guardar lo que el agricultor sabe
  (corrección 6).
- **Enseña**: selector de campaña; **importar o corregir** los datos de otros años desde lo que está
  verificado (exportación de **recintos por campaña** de la Junta 2023–2026, **Cuecyl `.xlsx`** de la
  campaña o **S-X en PDF con texto**) o a mano; tabla por tierra con **campaña, cultivo, superficie,
  variedad de semilla y producción estimada (kg/ha)**; las celdas que se pueden escribir se
  distinguen de las que vienen de la administración.
- **Acciones**: importar año, corregir un dato, marcar que una superficie cambió, exportar la
  evolución, abrir la tierra en el mapa.
- **Estados**: vacío («aún no hay años guardados» + importar), cargando, error de lectura del fichero
  (con el motivo y «meterlo a mano»), sin permiso.
- **Motor que ya existe**: `VersionDeRecinto` guarda una versión por **tierra, campaña y fuente**
  (`sigpac`, `cuaderno_de_la_junta`, `agricultor`, `medicion_en_campo`) con tres áreas separadas, y hay
  API de comparación y previsualización repetible y **pantalla `#/tierras/:id/versiones`**. Lo que
  falta es alimentarla desde el Cuecyl importado y desde la exportación de recintos por campaña.
- **Datos**: `Campana`, `VersionDeRecinto`, `ParcelaCultivo` (variedad), `Subvencion`; la producción
  estimada por hectárea: `PlanAbonado.produccion_esperada_kg_ha` ya existe, y para el histórico se
  valora una tabla propia si no encaja.
- **Límite declarado**: el FEGA publica **2025 y 2026** (dos campañas; los cultivos declarados solo de
  la anterior) y la Junta da **recintos de 2023 a 2026**. **Lo anterior a 2023 solo puede venir de los
  datos que aporte el agricultor.** Un año sin dato es «no consta», no «no sembró».

### P0 · S08 — Documentos y fotos (bandeja + visor)

- **Para qué**: los papeles del agricultor, con su original siempre a la vista.
- **Enseña**: bandeja por fecha y tipo (factura, albarán, boletín, foto de campo, documento PAC);
  miniatura, quién lo subió, a qué está vinculado; visor con el original y la propuesta al lado
  (lo que ya existe: revisión original/propuesta).
- **Acciones**: subir (cámara/galería/PDF), clasificar, vincular a parcela/apunte/gasto, buscar.
- **Facturas de fotos (corrección 2)**: una **foto** de la factura se lee y devuelve una **propuesta**
  —proveedor, NIF, número, fecha, base, IVA y total— con **revisión campo a campo** (bien / mal / sin
  leer), el **original siempre a la vista** y el botón de confirmar. Nada se da por bueno solo; la
  aritmética (cantidad × precio, base + IVA = total) se comprueba y, si no cuadra, se dice. Si el
  lector no está instalado, se guarda el justificante y se teclea: **no se inventa lo que pone el
  papel**. La frase «la lectura es una propuesta, no un dato» es la regla de este bloque.
- **Estados**: vacío con «haz una foto», cargando, error de lectura («no se ha podido leer; se
  guarda igual y se teclea»), sin permiso.
- **Datos**: `DocumentoAnexo`, `VinculoDeDocumento`, `Factura`, `Analitica`.

### P0 · S09 — Mapa a pantalla completa

- **Para qué**: elegir la parcela tocándola y ver la finca entera.
- **Enseña**: ortofoto (IGN) y linderos (SIGPAC), cultivo declarado, capas que existan (nitratos,
  Red Natura, pastos… solo las verificadas); GPS; búsqueda por municipio/polígono/parcela/recinto;
  **zoom** y **«ver todas»**; **agrupación** cuando hay muchas parcelas y **parcelas dispersas** en
  municipios distintos (corrección 1): el mapa no supone una finca junta.
- **Acciones**: tocar recinto (muestra qué ha encontrado y su superficie **antes** de darlo por
  bueno), centrar, volver a la lista, apuntar en lo tocado.
- **Estados**: cargando imagen (con la del recinto ya dibujada), error de red (los linderos guardados
  se siguen viendo), fuera de CyL / sin cobertura.
- **Datos**: servicios WMS y de consultas del SIGPAC ya comprobados (`docs/SERVICIOS_DEL_SIGPAC.md`).

### P0 · S10 — Exportar

- **Para qué**: sacar lo que pidan, en el sitio donde se está mirando.
- **Enseña**: un botón «Exportar» junto al título de cada lista y en cada ficha; elección de
  formato según lo que haya (PDF de lectura, CSV/Excel de datos); qué se va a exportar (lo filtrado,
  no todo); fecha de generación y **fuente de cada dato**.
- **Estados**: generando, hecho (con el nombre del fichero), error.
- **Nota**: los formatos oficiales que pida la Junta se añaden **cuando estén verificados**; hoy no
  se promete ninguno.

### P0 · S11 — Mis datos, Quién entra y Ajustes

- **Mis datos**: la finca (nombre, NIF, municipio, provincia), la campaña activa, el tamaño de letra.
- **Quién entra**: titular y ayudantes, con la **matriz de roles escrita**
  (`docs/QUIEN_ENTRA_EN_LA_FINCA.md`); la autorización se comprueba **en el servidor**.
- **Ajustes**: tema día/noche, tamaño de letra (A+/A−), idioma (castellano), avisos, borrar datos
  locales, ayuda y «cómo funciona sin cobertura».
- **Estados**: los cuatro; «sin permiso» explica quién puede y dónde se pide.

### P1 (siguiente entrega, ya especificado pero no en la primera)

- **Subvenciones — detalle de convocatoria**: requisitos, documentación y justificación, con
  calendario oficial. Depende de la investigación (convocatorias y plazos **por verificar**).
- **Cuaderno de la Junta (Cuecyl)**: importar/exportar el fichero oficial (ya existe la lectura,
  `app/cuaderno_cyl.py`); el volcado por IUWS cuando haya alta (hoy bloqueado, ver
  `docs/INTEGRACION_IUWS.md`).
- **Catálogo de productos y dosis** con el registro oficial (REGFIWEB) y aviso de caducidad.
- **Costes y márgenes** por parcela/campaña, enganchando gastos y ventas que ya existen.
- **Trabajos y maquinaria**, contactos y almacén: se integran en la misma ficha de parcela.

---

## 4 · Los flujos clave

### 4.1 Primera vez: traer las parcelas del SIGPAC

1. Bienvenida: «¿Dónde está tu finca?» → municipio/provincia (catálogo del INE ya cargado).
2. El programa **busca los recintos** de ese municipio (SIGPAC) y los enseña en el mapa.
3. El agricultor **toca los suyos** o busca por polígono/parcela/recinto; se enseña qué ha
   encontrado y su superficie **antes** de aceptar (un dedo en una linde es otra parcela).
4. Confirma; se guardan la identidad del recinto y su geometría (la foto del mapa **no** se guarda,
   como ya hace hoy el proyecto).
5. «Ya tienes tus parcelas» → botón «Apuntar lo primero».

*Alternativa*: importar el fichero del SIGPAC o del Cuecyl cuando el formato esté verificado
(ver investigación). Mientras, se puede subir el Cuecyl que la app ya sabe leer.

### 4.2 Apuntar un tratamiento en 30 segundos

1. **Hoy → Apunta lo que has hecho → Echar producto** (o desde la ficha de una parcela).
2. Parcela: la última, la de cerca (GPS), o tocar en el mapa. Se puede elegir más de una.
3. Producto: de la lista de los que usa; al elegirlo, dosis de la última vez (editable) y aviso si
   el producto no puede usarse en ese cultivo (cuando el catálogo verificado esté).
4. Superficie tratada: la del recinto, editable.
5. **Foto** del envase o del papel (opcional pero recomendada); el original se guarda.
6. **Guardar** → «guardado en el móvil» (y se manda solo) o «guardado» si hay red.
7. Se ofrecen «lo mismo que la última vez» y «apuntar otro».

**Regla de oro**: cualquier dato que la norma exija y no se haya pedido, se pide **después** con un
aviso que nombra la pantalla donde se arregla; no se bloquea el apunte.

### 4.3 Campaña

1. La campaña se crea al empezar el año (o al importar) y **una campaña activa**.
2. El cuaderno y la ficha de parcela se filtran por campaña; cambiar de campaña no cambia datos,
   solo la vista.
3. Al cerrar la campaña: resumen exportable por parcela, y lo que falta para la PAC.

### 4.4 PAC

1. **PAC y subvenciones → Campaña** → lista de comprobación.
2. Cada requisito pendiente lleva a la parcela o al documento que lo arregla.
3. La tabla de superficies se recalcula con lo que hay; las diferencias se explican.
4. Se genera el **paquete para presentar** (por recinto, con lo que falta marcado) y se **exporta
   para el asesor** o para teclearlo en la aplicación de la Junta.
5. **La presentación no se hace desde aquí**: la solicitud se cumplimenta y se firma en la
   aplicación de la Junta con certificado (`ayg.jcyl.es`). El programa enlaza al trámite exacto y
   **nunca dice que ha presentado algo**. Tampoco se firma desde aquí en esta fase (la firma del
   cuaderno no se toca).

---

## 5 · Los cuatro estados, por pantalla

| Pantalla | Vacío | Cargando | Error | Sin permiso |
|---|---|---|---|---|
| Hoy | «Trae tus parcelas» + botón | Tarjetas esqueleto | Tarjeta con reintento; el resto sigue | «Estás como ayudante; esto lo ve el titular» |
| Parcelas | «Aún no tienes parcelas» + importar | Esqueleto de filas + mapa guardado | Conserva lo cargado + reintentar | Ver finca, 404 sin filtrar |
| Ficha | «Todavía no hay actividad» + apuntar | Cabecera primero, actividad después | Sección con reintento | Datos que no se pueden ver, explicados |
| Apuntar | «Elige la parcela» con recientes | Guardando con progreso | Guardado en el móvil / rechazo con motivo | «Necesitas acceso a esta finca» |
| Cuaderno | «No has apuntado nada aún» + apuntar | Esqueleto | Reintento, sin perder filtros | Explicado |
| Campaña | «Campaña nueva» + apuntar | Esqueleto | Reintento | Explicado |
| PAC | «Aún no hay campaña preparada» | Esqueleto de checklist | Requisito con error, el resto sigue | «Solo el titular» |
| Documentos | «Haz una foto» | Miniatura esqueleto | «No se ha podido leer; se guarda y se teclea» | Explicado |
| Mapa | Sin recintos en esa zona | Imagen cargando; linderos ya | «Sin cobertura: se ve lo guardado» | — |

**Regla común**: un error nunca se pinta como vacío; un vacío nunca deja sin salida; un estado sin
permiso dice **quién** y **dónde** se pide.

---

## 6 · Responsive y modos

| Ancho | Qué cambia |
|---|---|
| **360–430** (móvil) | Barra inferior de 5; una columna; texto de campo 19 px; objetivos de 48 px; formularios a pantalla completa; mapa plegable |
| **768–1024** (tableta) | Barra lateral colapsable; dos columnas cuando aporta (lista+mapa); mismos controles táctiles |
| **1024–1440** (PC) | Barra lateral fija; tabla densa; ficha y mapa lado a lado; atajos de teclado; foco visible |

- **Modo campo** (móvil): letra un punto más grande (A+), contraste alto, una pregunta por bloque.
- **Modo despacho** (PC/tableta): tablas, filtros, selección múltiple, exportar.
- Sin scroll horizontal en ningún ancho; si una tabla no cabe, se convierte en tarjetas.

---

## 7 · Qué se reutiliza del programa actual y qué falta

**Se conserva** (no se reescribe el backend):

| Pieza | Dónde está | Uso en el producto nuevo |
|---|---|---|
| Parcelas, versiones de recinto, geometría | `models.Parcela`, `models.VersionDeRecinto`, `app/geo.py`, `app/versiones_de_recinto.py` | Mis parcelas, ficha, mapa |
| SIGPAC (consultas y WMS ya comprobados) | `app/sigpac.py`, `data/sigpac/` | Traer y elegir recintos, mapa |
| Cuaderno: labor, tratamiento, fertilización, siembra | `models.Labor`, `TratamientoFitosanitario`, `RegistroFertilizacion`, `Siembra` | Apuntar en 30 s, cuaderno, campaña |
| Plan de abono, análisis, medidas preventivas | `models.PlanAbonado`, `Analitica`, `MedidaPreventivaDeclarada` | Ficha de parcela (P1) |
| PAC y subvenciones | `models.Subvencion`, `models.FotoDeLaPac`, `app/routers/pac_api.py` | S07 (con lo que falte por verificar) |
| Cuecyl: leer y exportar el cuaderno de la Junta | `app/cuaderno_cyl.py`, `app/cuaderno_cyl_exportar.py` | Importar tierras y exportar (P1) |
| Documentos, facturas, OCR con revisión | `models.DocumentoAnexo`, `app/facturas.py`, `app/ocr.py` | Bandeja y visor |
| Firma, cuentas y permisos | `app/firma.py`, `docs/QUIEN_ENTRA_EN_LA_FINCA.md` | S11; autorización en servidor |
| Cola sin cobertura | `web/nucleo.js` (`crearColaPorIntenciones`, buzón de rechazos) | Apuntar sin cobertura |

**Falta construir** (lo que la investigación tiene que confirmar antes de tocar):
1. **Alta de parcelas desde el SIGPAC en lote** (GeoPackage por provincia) y **alta guiada**; el mapa
   con parcelas dispersas (zoom, agrupación, selección).
2. **Favoritos** de productos, abonos y tratamientos (tabla nueva por finca y cuenta) y el flujo de
   **dosis por hectárea** con total calculado (los campos de dosis ya existen en el modelo).
3. **Histórico de la PAC** por años y la **producción estimada por hectárea** (la variedad y la
   producción esperada ya existen en el modelo; falta la vista y, si no encaja, la tabla).
4. **Catálogo verificado de productos** (fitosanitarios y fertilizantes) y tipos de labor/siembra.
5. **Importador de los canales verificados** (recintos por campaña de la Junta 2023–2026, Cuecyl
   `.xlsx` y S-X con texto) y el eslabón que hoy falta: **que la importación del Cuecyl escriba las
   versiones de su campaña**. El formato de «Documentos del expediente» y la descarga del Cuecyl de
   años anteriores siguen **pendientes de verificar** (ver `INVESTIGACION-AGRICOLA.md`).
6. **Convocatorias y plazos de subvenciones** con calendario oficial.
7. **Tareas y maquinaria** dentro de la ficha (P1).

---

## 8 · Fases de entrega propuestas

| Fase | Qué entra | Criterio de aceptación |
|---|---|---|
| **F1** | Sistema de diseño + artboards | **Aprobado con correcciones el 2026-11-05**; el canvas se actualiza con ellas |
| **F2** | Armazón nuevo: navegación móvil/tableta/PC, estados base, **Hoy** y **Mis parcelas** con el **panel de tierras**, el mapa con **zoom, agrupación y selección** y parcelas **dispersas** | Se recorre en navegador a 390/1024/1440; vacío/error/sin permiso; una explotación de prueba con tierras en **2 municipios** |
| **F3** | Ficha de parcela + mapa selector + **alta guiada de parcelas** (SIGPAC) y el **alta importando** (con lo que esté verificado) | Se dan de alta 3 recintos de verdad; no se duplica ninguno; las tierras dispersas se ven y se seleccionan |
| **F4** | **Apuntar en 30 s guiado** (dice qué falta), los cuatro tipos, **productos/abonos con dosis por hectárea y favoritos**, cola sin cobertura y cuaderno | Un apunte hecho sin cobertura llega solo; la dosis y el total cuadran; el panel dice qué falta sin bloquear |
| **F4-bis** | **Facturas de fotos** con lectura y revisión campo a campo | Una foto de factura devuelve propuesta y se corrige campo a campo; nada se guarda sin revisar |
| **F5** | Campaña + **PAC, histórico de años, evolución de una tierra, producción estimada y variedad** | La tabla de evolución se puede rellenar y exportar; la PAC queda preparada salvo lo pendiente de verificar |
| **F6** | Exportar (PDF/Excel) y Cuecyl | Se exporta lo filtrado y se puede leer |

Cada fase conserva las pruebas del flujo y **no deja la aplicación a medias**: la interfaz anterior
sigue sirviendo hasta que la nueva cubra cada recorrido, o se retira pantalla a pantalla.

---

## 9 · Aprobado con correcciones: qué queda cerrado y qué sigue abierto

**Cerrado por David (2026-11-05)**: la navegación, la portada «Hoy», el orden de las fases, la marca
y el color, y el uso de datos de ejemplo en los artboards. Y las ocho correcciones del apartado 0, ya
incorporadas aquí y en el canvas.

**Lo que sigue abierto y depende de terceros o de una comprobación** (no se decide a ciegas):
1. **El formato para importar una PAC de otros años**: está **pendiente de verificación** (ver
   `INVESTIGACION-AGRICOLA.md`). Si no hay fichero, se importa a mano con el paquete preparatorio y se
   dice claro.
2. **Los vídeos de referencia de David** sobre cómo conseguir las parcelas del SIGPAC: se incorporan
   cuando los pase; hasta entonces, el alta guiada es la vía verificada.
3. **Regiones e importes de la PAC de CyL** y el **coeficiente de admisibilidad de pastos**: están en
   la Orden y anexos en PDF, sin verificar todavía; se enseñan como «por confirmar» hasta cargarlos.
4. **Los valores de los catálogos oficiales** de productos, abonos y tipos de labor: estructura sí,
   valores no (captcha); se usa catálogo propio marcando lo que no consta.
5. **La licencia del SHP de CyL y de la ortofoto PNOA**: pendientes de respuesta por escrito; mientras,
   GeoPackage del FEGA y visualización de los WMS de la Junta.

---

## 10 · Riesgos y límites, dichos

- **La PAC no se presenta desde el programa**: la vía oficial verificada (04/11/2026) es la
  aplicación de la Junta con certificado; **no hay API pública de presentación localizada**. Lo que
  se promete es **preparar y dejar listo**, no presentar. Y la convocatoria de 2027 no está
  publicada: no se dan fechas de memoria.
- **Regiones e importes de la PAC de CyL** están en la Orden y sus anexos (PDF) y **no se han
  verificado**: la tabla de regiones se enseña con «por confirmar» hasta que se cargue la fuente
  versionada. Lo mismo con el coeficiente de admisibilidad de pastos.
- **El formato de la solicitud PAC y los ficheros de la Junta no están verificados todavía**: esta
  arquitectura los deja como «por confirmar» y no promete descargar el fichero de solicitud. La
  investigación ([`INVESTIGACION-AGRICOLA.md`](../INVESTIGACION-AGRICOLA.md)) dirá qué se puede hacer.
- **El alta masiva de recintos del SIGPAC** depende de que exista descarga oficial por municipio (la
  consulta por punto ya está comprobada): si no existe, se hace por lotes con la consulta por punto
  y el agricultor confirma, más lento pero verificado.
- **El catálogo de productos** puede no estar descargable en su totalidad (hay captchas y registros):
  si falta, se usa el catálogo propio y se marca lo que no consta, nunca un código inventado.
- **Sin cobertura**: la cola ya existe y está probada; el rediseño **no puede romperla** (es el
  criterio nº 1 del usuario). Cada fase pasa la prueba del apunte sin red.
- **La interfaz anterior sigue viva** hasta que la nueva cubra sus recorridos: no se deja al
  agricultor con una pantalla a medias.
- **La evolución de una tierra tiene un límite**: el SIGPAC publica **2025 y 2026** (dos campañas) y
  la consulta de la Junta da **recintos de 2023 a 2026** (verificado el 05/11/2026). **Lo anterior a
  2023 solo puede venir de los datos que aporte el agricultor**; no se reconstruye de la nada ni se
  inventa. Y **no hay fichero oficial de la solicitud PAC declarada**: si no hay Cuecyl o S-X con
  texto, se mete a mano con el paquete preparatorio.
- **Leer una factura de una foto no es aprobar la lectura**: la propuesta se revisa campo a campo y
  la precisión sobre facturas reales sigue **sin medir** (el corpus de D08 está aparcado). No se
  promete un porcentaje.
- **La doctrina §8 manda en los textos**: si un texto no ayuda al agricultor a decidir o actuar, se
  borra; no se sustituye por otro. Y nada de explicar cómo está hecha la pantalla o cómo se calcula
  un número.

---

*Documento de propuesta. No implementa nada. El aspecto está en `designs/cue-agricola-design-system/`
y `designs/cue-agricola/`; la investigación con fuentes, en `INVESTIGACION-AGRICOLA.md`.*

---

## 11 · Estado de implementación (2026-11-05)

La primera entrega de **F2** ya está construida y **la app vieja sigue viva**:

| Qué | Dónde | Estado |
|---|---|---|
| Armazón nuevo (barra superior, lateral en tableta/PC, inferior de 5 en el móvil) | `/nuevo/` (`backend/web/nuevo/`) | Hecho |
| «Hoy» (finca, contador, lo último, botón de apuntar) | `/nuevo/` | Hecho |
| «Mis parcelas» (contador, buscador, lista por municipio, mapa real, zoom, zona, panel con otros años) | `/nuevo/` | Hecho |
| **Alta de tierras por código y ventana del SIGPAC** (recintos resaltados con color y etiqueta, clic para elegir, alta en bloque) | `/nuevo/` | Hecho |
| **Tierra catalogada y editable** (alias y superficie; lo del SIGPAC se muestra) | `/nuevo/` | Hecho |
| **Importar el cuaderno del cliente** (Cuecyl `.xlsx`: reconoce las parcelas, las crea sin duplicar y rellena la finca) | `/nuevo/` | Hecho |
| **Mapa coloreado por uso/cultivo con leyenda + ficha al clicar** | `/nuevo/` | Hecho |
| **Gastos/ventas y «qué falta» en «Hoy»** | `/nuevo/` | Hecho (detalle en la app vieja) |
| Los cuatro estados (cargando, error, vacío, sin permiso) | `/nuevo/` | Hecho |
| API del armazón (`/api/nuevo/hoy`, `/api/nuevo/tierras`, `/api/nuevo/importar-cuaderno`, `/api/nuevo/resumen`, `/api/nuevo/que-falta`) | `app/routers/nuevo_api.py`, `app/nuevo.py` | Hecho |
| SIGPAC: uso, coeficiente, región y admisibilidad guardados; descarga por provincia con caché; `puntos` en la búsqueda | `app/sigpac_cache.py`, `app/routers/parcelas.py` | Hecho (falta abrir el GeoPackage) |
| Pantallas propias de gastos/ingresos y de facturas; apuntar en 30 s; PAC de años anteriores | — | Pendiente (diseño aprobado) |
| Conexión bancaria PSD2 solo lectura | — | Investigado y parado (nivel 3): `docs/PSD2-AGREGADORES.md` |

**Evidencia**: `scripts/comprobar_el_armazon_nuevo.py` en Chrome a **390, 1024 y 1440 px → 0 fallos**
(navegación que cambia con el ancho, sin scroll horizontal, 64 tierras en 5 municipios, mapa con
imagen, panel con alias y otros años, los cuatro estados, y el recorrido de **alta SIGPAC** y de
**importación del cuaderno**); capturas en `docs/capturas-nuevo/`. Las pruebas de la pantalla nueva
están en `tests/test_interfaz_nuevo.py` y `tests_js/nuevo.test.js`.

**Lo que sigue**: AGR-15 (abrir el GeoPackage e importar), la PAC y los recintos por campaña, las
pantallas propias de gastos/facturas y el cuaderno de 30 s (AGR-16), y PSD2 cuando haya presupuesto
aprobado (AGR-18).
