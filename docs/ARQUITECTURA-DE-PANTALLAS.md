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
- **Estados**: vacío con el botón de importar; cargando (esqueleto de filas, no spinner ciego);
  error de red conservando lo ya cargado + reintento; sin permiso (ver finca ó 404, nunca datos de
  otra finca).
- **Datos**: `Parcela`, `VersionDeRecinto` (identidad y versiones del recinto), catálogos SIGPAC
  (`data/sigpac/`), `Campana`.

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
- **Estados**: guardando (con progreso real), guardado en el móvil, guardado en el servidor,
  rechazado por el servidor (con el motivo y el botón para arreglarlo), sin permiso.
- **Datos**: `TratamientoFitosanitario`, `Labor`, `RegistroFertilizacion`, `Siembra`; catálogo
  oficial de productos (ver investigación; hoy hay `ProductoFitosanitario` y `Fertilizante`).

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

### P0 · S08 — Documentos y fotos (bandeja + visor)

- **Para qué**: los papeles del agricultor, con su original siempre a la vista.
- **Enseña**: bandeja por fecha y tipo (factura, albarán, boletín, foto de campo, documento PAC);
  miniatura, quién lo subió, a qué está vinculado; visor con el original y la propuesta al lado
  (lo que ya existe: revisión original/propuesta).
- **Acciones**: subir (cámara/galería/PDF), clasificar, vincular a parcela/apunte/gasto, buscar.
- **Estados**: vacío con «haz una foto», cargando, error de lectura («no se ha podido leer; se
  guarda igual y se teclea»), sin permiso.
- **Datos**: `DocumentoAnexo`, `VinculoDeDocumento`, `Factura`, `Analitica`.

### P0 · S09 — Mapa a pantalla completa

- **Para qué**: elegir la parcela tocándola y ver la finca entera.
- **Enseña**: ortofoto (IGN) y linderos (SIGPAC), cultivo declarado, capas que existan (nitratos,
  Red Natura, pastos… solo las verificadas); GPS; búsqueda por municipio/polígono/parcela/recinto.
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
1. **Alta de parcelas desde el SIGPAC en lote** (descarga por municipio, no solo consulta por punto).
2. **Catálogo verificado de productos** (fitosanitarios y fertilizantes) y tipos de labor/siembra.
3. **Modelo de la solicitud PAC** y formatos de fichero que acepta la Junta (ver
   `INVESTIGACION-AGRICOLA.md`: pendiente).
4. **Convocatorias y plazos de subvenciones** con calendario oficial.
5. **Tareas y maquinaria** dentro de la ficha (P1).

---

## 8 · Fases de entrega propuestas

| Fase | Qué entra | Criterio de aceptación |
|---|---|---|
| **F1** | Sistema de diseño + artboards (este paquete) | David aprueba aspecto y arquitectura |
| **F2** | Armazón nuevo: navegación móvil/tableta/PC, barra, estados base, Hoy y Mis parcelas con datos reales de la explotación de prueba | Se recorre en navegador a 390/1024/1440; vacío/error/sin permiso |
| **F3** | Ficha de parcela + mapa selector + traer parcelas del SIGPAC | Se dan de alta 3 recintos de verdad con su mapa y se ven en la ficha |
| **F4** | Apuntar en 30 s (los cuatro tipos) + cola sin cobertura + cuaderno | Un apunte de prueba hecho con el móvil sin cobertura llega al servidor solo |
| **F5** | Campaña + PAC (checklist, superficies, documentación) | La solicitud de prueba queda lista salvo lo que esté pendiente de verificar |
| **F6** | Exportar (PDF/Excel) y Cuecyl | Se exporta lo filtrado y se puede leer |

Cada fase conserva las pruebas del flujo y **no deja la aplicación a medias**: la interfaz anterior
sigue sirviendo hasta que la nueva cubra cada recorrido, o se retira pantalla a pantalla.

---

## 9 · Lo que David tiene que aprobar (o corregir)

1. **La navegación**: barra inferior de 5 en el móvil (Hoy, Parcelas, Apuntar, Cuaderno, Más) y
   barra lateral en el PC. ¿Falta o sobra algún destino?
2. **La portada «Hoy»**: finca delante, un solo botón principal y «te falta para la PAC». ¿Es lo que
   quiere ver al abrir?
3. **El orden de las fases**: primero el armazón y las parcelas (F2–F3), luego el apunte (F4),
   luego campaña/PAC (F5) y exportar (F6). ¿Se empieza por PC o por móvil? La propuesta empieza por
   el armazón común y las parcelas, que sirven a los dos.
4. **El alcance de la primera PAC**: la vía oficial **no admite un fichero de solicitud** (se
   cumplimenta en la aplicación de la Junta y se firma con certificado), así que la propuesta es
   **paquete preparatorio + lista de comprobación + superficies + documentación + enlace al trámite**.
   ¿Se queda ahí, o quiere también guardar la solicitud presentada (transcripción) para comparar
   2025/2026/2027 y detectar cambios del SIGPAC? Lo segundo es más trabajo y necesita que él aporte
   la solicitud de años anteriores.
5. **La marca y el color**: verde de la casa + tierra, tipografía del sistema (funciona sin red).
   ¿Mantiene el nombre «CueDigital» y el símbolo? No hay logo nuevo: se usan tipografía y color.
6. **Los datos de ejemplo de los artboards** son ficticios (Finca La Vega, etc.): ¿los usa para
   revisar o prefiere los suyos (sin datos personales en el repositorio)?

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

---

*Documento de propuesta. No implementa nada. El aspecto está en `designs/cue-agricola-design-system/`
y `designs/cue-agricola/`; la investigación con fuentes, en `INVESTIGACION-AGRICOLA.md`.*
