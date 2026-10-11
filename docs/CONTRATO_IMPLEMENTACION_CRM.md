# Contrato de implementación del CRM agrario

Fecha: 01/10/2026. Estado: especificación, no funcionalidad entregada. Destinatario:
DeepSeek y cualquier agente implementador. Complementa el plan E0–E13 y la
especificación detallada; este documento concreta contratos, pantallas y entregas.
No autoriza pruebas sobre la base real ni sustituye una revisión agronómica.

## 0. Estado a 11/10/2026 — la protección del reenvío y la presentación de la compra

No es un plan nuevo: es lo que este contrato ya pide, comprobado desde fuera con servidor aislado, base
temporal y documentos ficticios.

### Lo que hay hoy, medido

| Qué | Con qué se mide | Hoy |
|---|---|---|
| La compra de punta a punta (factura → recepción → lote → gasto → pagos) | `backend/scripts/comprobar_la_compra_de_punta_a_punta.py` | **49 comprobaciones · 0 fallos** |
| La ficha en un navegador de verdad | `backend/scripts/comprobar_la_ficha_de_la_compra_en_el_navegador.py` | **44 comprobaciones · 0 fallos** |
| El reenvío de la factura | `backend/tests/test_la_factura_reenviada_no_se_duplica.py` | **17 pruebas** |
| La migración del reenvío, sobre copia | `backend/tests/test_la_migracion_del_reenvio.py` | **3 pruebas** |
| La ficha, en pruebas | `backend/tests/test_la_ficha_de_la_compra.py` | **11 pruebas** |
| La suite entera | `python -m pytest tests -q` / `node --test "tests_js/*.test.js"` | **4736 · 0** de Python y **1080 · 0** de JavaScript |

### La historia, aparte, para que nadie lea una cifra vieja como el estado

Estas cifras **han subido**, y cada una se dice aquí una vez en vez de dejar el número viejo suelto más
abajo:

  · El guion de la compra fue **30** cuando se escribió, pasó a **49** al añadir el pago agrupado, la
    corrección con rastro y la separación al anular, y sigue en **49**.
  · La comprobación del navegador fue **13**, pasó a **15** cuando se le añadieron «los botones dicen algo» y
    «ningún título sale en blanco» —las dos que habrían cazado los botones vacíos que encontró el revisor—,
    y hoy son **44** con la presentación: la rejilla de los cuatro indicadores, la tabla de líneas, los dos
    bloques, la barra a 1024 y a 1440 y los importes en español.
  · El reenvío de la factura tenía **11 pruebas y tres desenlaces**; hoy tiene **17 y cuatro** (el cuarto es
    el reenvío de un comando cuya factura se anuló, que contesta con su estado y **no crea otra factura**).
  · Las capturas eran **dos** (móvil y escritorio); hoy son **tres**: móvil de 390 px, escritorio de 1440 y
    escritorio de 1024.

**Acreditado:** una compra identificable —proveedor → factura de **663 €** con líneas → recepción en las
**mismas unidades** → lote → gasto **vinculado** por `factura_id` → pagos—. Los pagos se comprueban **por
identificador**, no por el total: el pendiente de **esa** factura va **663 → 463 → 0**, con **sus**
aplicaciones, **su** saldo sin aplicar y **las demás deudas sin moverse** (40 comprobadas); el resumen de la
explotación (**3.531,20 → 2.868,20**) se contrasta **además**, nunca en lugar de. **A15** medido con el saldo
ya conocido (**1000 → 1000**): la factura **no** vuelve a meter mercancía. **Recepción parcial**: 300 kg y
200 kg **sin factura**, que suman **500 → 1000** con tres movimientos. **Factura posterior al albarán**:
enganche por `POST /api/almacen/recepciones/{id}/factura` → **200**.

**Acreditado desde el 09/10/2026 — el reenvío de la factura, resuelto en el servidor.** Era el hueco que este
mismo apartado tenía apuntado: `models.Factura` era **la única entidad del programa sin `clave_de_reenvio`** y
su puerta **siempre insertaba** (medido: `201`, `201`, dos filas). Ya no: la columna existe con **índice único
parcial por explotación, filtrado por `anulada = 0`** —la misma decisión que `Recepcion` y
`MovimientoDeExistencias`, y por el mismo motivo escrito allí: una anulada **no ocupa su clave**, porque anular
existe justo para poder apuntar la buena después—, y la puerta separa **tres desenlaces**: reenvío técnico
(misma clave, mismos datos) → **200 con la que ya estaba**; posible **duplicado comercial** (mismo proveedor,
número, año y total, pero otra petición) → **200 reconociéndolo por `numero_de_factura`**, sin contar dos
veces; y **conflicto claro** (misma clave con otros datos) → **409**, porque una petición no tiene dos cuerpos.
Cuando no hay número o proveedor, se apunta igual **diciendo que no se pudo comprobar** (`AL27…`). Todo eso
está en **11 pruebas obligatorias** (`backend/tests/test_la_factura_reenviada_no_se_duplica.py`), seis de las
cuales se pusieron **rojas antes** del arreglo: se desactivó la comprobación de la puerta y fallaron las seis.El instrumento que lo mide —`scripts/comprobar_si_una_factura_repetida_se_duplica.py`— tenía un **defecto
propio** que se descubrió midiendo: envolvía `datos` dos veces, así que mandaba facturas **vacías** y su
conclusión era cierta por casualidad; ahora exige que la factura llegue entera antes de concluir nada.
*(Aquellas 11 pruebas son hoy **17**: lo que cambió después va en el apartado siguiente.)*

**Acreditado desde el 11/10/2026 — la protección del reenvío, cerrada, y el duplicado comercial sin
depender de la suerte.** Tres cosas cambiaron, a petición expresa, y las tres con prueba:

  1. **La clave no se recicla.** El índice único ya **no excluye las anuladas**: una petición usada es una
     petición usada, y el reenvío de un comando cuya factura se anuló contesta **200 con su estado anulado y
     su motivo** (`AL46…`) y **nunca crea otra factura**. Antes la anulada soltaba su clave —la regla de los
     albaranes—, y eso **confundía un reintento viejo que llega tarde con un alta nueva deliberada**: el
     móvil que reintentaba sin cobertura recibía una factura nueva sin saberlo. Las altas nuevas se hacen con
     **una clave nueva**, y para eso la pantalla del alta genera la suya al abrirse y la suelta al guardar
     (`app.js`), de modo que la segunda factura del día es una petición distinta.
  2. **El comando original tiene huella** (`facturas.huella_de_la_peticion`). La clave decía «esta petición
     ya se atendió» pero no **qué traía**, y por eso, después de corregir una factura, **cualquier** cuerpo
     con aquella clave recibía un 200 «ya estaba» y sus datos se perdían en silencio. Ahora: si lo que llega
     tiene la huella del comando original es **su reenvío** y se contesta con el registro **como está hoy**
     (corregido → `AL45…`; anulado → `AL46…`); y si no la tiene, es **otra petición** y es **409** (`AL26…`),
     haya correcciones o no.
  3. **El posible duplicado comercial ya no se descarta en silencio, y no depende de la suerte.** El mismo
     papel con el mismo detalle se sigue contestando con el que había; pero si **dice otra cosa**, ahora es
     **409** (`AL47…`) diciendo **qué factura es la que está** (número, fecha y total) para que decida el
     agricultor, en vez de un aviso que nadie lee mientras sus datos se tiran. Y la garantía frente a dos
     envíos **simultáneos** ya no es la consulta previa —el revisor lo dijo con estas palabras: «80 intentos
     sin duplicar no constituyen una garantía»— sino el **índice único del papel** (`facturas.clave_del_papel`
     + `uq_factura_papel`): la segunda inserción falla en la base y la puerta contesta lo mismo que si la
     hubiera encontrado la búsqueda. La clave del papel **se recalcula al corregir** (si cambia el número, la
     fecha o el total, el papel es otro) y **una anulada no lo ocupa**, que es la parte de la regla vieja que
     sigue valiendo: habla del papel, no de la petición.
  4. **La migración, ensayada sobre copia** (`database.rellenar_la_huella_del_comando`): resuelve las claves
     repetidas de la regla vieja —se quedan en la factura **más antigua**— y rellena huellas y claves del
     papel **sin borrar ninguna fila**; si encuentra **dos facturas vivas del mismo papel** —un duplicado de
     verdad, de los que la regla vieja dejaba pasar— las deja **las dos a la vista** y lo dice, para que lo
     resuelva el agricultor. Se puede correr dos veces: la segunda no cambia nada. Lo que no se puede
     reconstruir —la huella de una factura corregida antes de que la huella existiera— se resuelve **por lo
     prudente**: se dice el conflicto en vez de aceptar en silencio algo que no se puede comprobar.


**Acreditado desde el 09/10/2026 — el pago agrupado, la corrección con rastro y la separación al anular.**
La compra de punta a punta pasó **de 30 a 49 comprobaciones** (`0 fallos`) —donde sigue: ver el estado de
arriba—, y las tres nuevas son las que
faltaban del punto 3 del encargo: **un solo pago de 350 € salda dos facturas** (100 y 250) repartido por
antigüedad —cada una queda a **0** por su identificador y las **dos aplicaciones suman 350,00 exactos**—;
**corregir** la factura deja su entrada en la auditoría (`corregir_lineas`), **no mueve el almacén**
(1000 → 1000) y **conserva el enganche** del albarán; y **anular el albarán devuelve exactamente lo que
metió** (300 kg: 1000 → 700) mientras **anular la factura no vacía el almacén** (700 → 700), cada una con
su rastro. Y las cifras nuevas son **obligatorias**: la prueba de la compra las exige literalmente
(`backend/tests/test_la_compra_se_anda_entera.py`), con un mínimo de 40 comprobaciones para que quitarle
secciones al guion se note.

**Acreditado desde el 09/10/2026 — la ficha de la compra (punto 5), por la pantalla y con capturas.**
`GET /api/compras/{id}` junta las cuatro cifras —**facturado, recibido, pagado y pendiente**— y la pantalla
`/compras/:id` (`backend/web/react/pantallas/compra.js`) las enseña, con **enlaces** al albarán y al gasto
(`albaran-abrir`, `gasto-abrir`) y con la **dirección permanente** que se lleva el contexto
(`#/compras/3?campana=2026&finca=6`). El recorrido **se anda en un navegador de verdad**
(`scripts/comprobar_la_ficha_de_la_compra_en_el_navegador.py`: fueron **13** comprobaciones cuando se
escribió, luego **15**, y **hoy son 44 con la presentación** —ver el estado de arriba—), incluido el
camino del agricultor —lista de facturas → «VER LA COMPRA» → ficha—, y deja **tres capturas** en
`docs/capturas/` (móvil de 390 px, escritorio de 1440 y escritorio de 1024). Ahí se cazó un defecto real: la
ficha se abría pero **la dirección no
se escribía**, así que el enlace no se podía mandar a nadie; lo que se enseña sale del sitio de siempre
—lo pagado, con `servicios.lo_pagado_de_un_gasto`, que ahora es la **regla única** del dinero— para que la
ficha y la pantalla de gastos no puedan dar dos cifras distintas del mismo dinero. Lo que **no** se puede
saber se declara: una línea sin enganche con el albarán sale como «no se puede saber», nunca como un cero.

**Acreditado desde el 11/10/2026 — la ficha, presentada como una ficha de gestión.** El contenido ya estaba
reunido, pero se leía como una columna de móvil también en el ordenador, y David lo vio en la captura:
*«en escritorio la ficha sigue organizada como una columna móvil»*. Ahora:

  · **Los cuatro indicadores van en una fila** a partir de 64 rem —medido en un navegador a **1440**: los
    cuatro con la misma altura de arriba (173) y **263 px** de ancho cada uno— y en **cuadrícula de dos** por
    debajo, también a 1024. Lo que no vuelve es la columna: cuatro cifras apiladas son cuatro pantallas.
    (Esas clases **no existían en `estilos.css`**: la ficha las usaba desde el primer día y sin estilo
    alguno, que es exactamente por lo que salía en columna.)
  · **Las líneas van en una tabla** de verdad, con sus cuatro columnas —producto, facturado, ha entrado y
    falta—, dentro del `tabla-scroll` que ya usa el resto de la aplicación para que el móvil la desplace en
    horizontal en vez de apilarla.
  · **Los documentos y el dinero van separados** en dos bloques con su raya: lo que ha llegado (albaranes y
    líneas) y lo que se ha pagado (gastos y pagos). No es decoración: son las dos mitades que se confunden.
  · **Los importes van con coma decimal y en euros**, y eso se comprueba: la puerta sirve el mismo importe en
    texto de máquina y **en español** (`importe_texto`, `pagado_texto`, `pendiente_texto`, `aplicado_texto`,
    `importe_texto`), porque el dinero lo formatea quien lo cuenta con `Decimal` y el navegador no formatea
    dinero; el guion del navegador busca en pantalla cualquier cifra con punto y dos decimales (`663.00`) y
    **falla si aparece**.
  · **Y la barra de arriba, medida a 1024 y a 1440.** A 1440 usa la barra del armazón: **64 px** de alto, sus
    **cuatro acciones a la vista** y la campaña y la cuenta **sin recortar** —lo que sí se recorta es el
    **nombre de la explotación**, que es lo que el diseño decidió que cediera primero, y en el fixture lleva a
    propósito un nombre larguísimo—. A 1024 el armazón usa la **cabecera compacta** (el corte de escritorio
    está en 64 rem y el ancho de maquetación se queda en 1009 con la barra de desplazamiento), con sus **dos
    acciones a la vista**. En los dos anchos: **ninguna acción oculta**.

**Pendiente:** **permisos, uso sin cobertura, conflictos de edición y restauración de copia**; y de §S11,
lo que la ficha todavía no enseña (varios tipos de IVA, portes y descuentos globales, moneda).

### Lo que encontraron los revisores independientes, y qué se hizo (09/10/2026)

Dos revisores que **no eran el autor** —uno de negocio y otro de pantallas— intentaron falsar lo de arriba
midiendo, no leyendo. Los dos reprodujeron lo acreditado y **tiraron abajo seis cosas**, todas con
reproducción mínima. Se arreglaron, cada una con su prueba (y las que se pudieron, **rojas antes**):

| Lo que estaba mal | Cómo se arregló |
|---|---|
| **La ficha pedía textos que no le llegaban**: la puerta servía `textos.FACTURAS` y el componente lee ocho frases de `COMPRA` → **dos botones en blanco de 1059 px** y dos títulos vacíos, medido en Chrome | La puerta sirve `textos.COMPRA` y una prueba **cruza** lo que el componente pide con lo que la puerta sirve. El guion del navegador ahora exige que **los botones y los títulos digan algo** (antes solo miraba que existieran) |
| **Corregir o borrar una factura con un albarán enganchado a sus líneas daba 500** (`FOREIGN KEY constraint failed`): el código borraba y rehacía las líneas, y su docstring afirmaba que «nada del programa apunta a una línea», que era falso | Las líneas se **actualizan en su sitio**, así que **el enganche del albarán sobrevive a la corrección** (que es lo que el encargo pide conservar). Quitar una línea apuntada contesta **409** con sus palabras. El guardián del borrado cuenta también el enganche fino |
| **La ficha sumaba los gastos anulados**: el mismo dinero con dos cifras en dos pantallas | Los anulados no son deuda: se cuentan aparte y se dicen |
| **«Pendiente 0,00 €» cuando no se sabe**: un gasto sin importe dejaba el total en cero mientras su propia fila decía «—» | `pendiente` sale «no se sabe» y se declara por qué |
| **`falta` restaba unidades distintas**: 500 kg menos 300 L decían «faltan 200 kg» | Se resta solo con `servicios.se_pueden_sumar`; lo que llegó en otra unidad **se enseña** |
| **Un albarán enganchado solo por línea no contaba** y la ficha decía «no ha entrado nada» de algo que sí sabía | Se reconocen los dos caminos: la cabecera **y** el enganche de línea |

Y tres cosas más, menores pero reales: el **409 solo miraba los importes** (otras notas u otro IVA se
tiraban en silencio, ahora dan 409); **reintentar el mismo comando después de corregir la factura daba un
409 falso** (ahora devuelve la factura como está hoy y lo dice); y **la misma clave de un pago con otro
dinero se tragaba los datos nuevos** (ahora es 409, como en las facturas). El aviso de «ese número y esa
fecha» decía fecha cuando compara el año, y la captura «del móvil» era de 500 px: las dos corregidas
(la captura es **390×1400** de verdad).

**Límites declarados, que no se han cerrado:** todo lo medido es **SQLite** (los índices parciales tienen
su variante `postgresql_where`, pero no se ha ejecutado la sonda de PostgreSQL); el **posible duplicado
comercial** (mismo proveedor, número, año y total) no tiene índice único propio —la carrera la cubre la
consulta previa, y el revisor no consiguió duplicarlo en 80 intentos, pero no está garantizado por la
base—; el reenvío de un **pago** sigue contestando 201 y no 200; y las **capturas** no las ha podido mirar
ningún agente (el modelo no acepta imágenes): se han verificado como PNG reales, con sus dimensiones, y por
el texto que la propia página declara.

---

## 1. Orden de lectura y decisiones de producto

Leer AGENTS.md, PLAN_CRM_AGRARIO_2026.md, ESPECIFICACION_DETALLADA_CRM_2026.md,
este documento y DESIGN.md. Consultar después el código y los tests existentes.
Los informes antiguos describen su fecha, no acreditan la funcionalidad actual.

El producto tiene dos experiencias sobre los mismos registros: despacho, con tablas,
mapas y planificación; campo, con acciones rápidas y trabajo sin cobertura. Las
antiguas prohibiciones generales de menús o pestañas se aplicaban al recorrido móvil.
No impiden un menú lateral o secciones de ficha en escritorio. No cambiar la tecnología
de renderizado ni añadir una compilación por el mero rediseño.

Decisiones propuestas para la primera versión: selector de campaña visible en
despacho, navegación móvil compacta, vistas guardadas por usuario, filtros explícitos
y enlace permanente al contexto. Son reversibles. Nunca renombrar las tierras reales
automáticamente. Un nombre puede contener hectáreas, pero no es la fuente del área.

No se pretende construir contabilidad fiscal certificada, asesoramiento automático,
presentación telemática PAC ni una entidad bancaria. Sí se construyen gestión
operativa, cuentas explicables y preparación documental. IUWS sigue separado.

## 2. Contratos del núcleo: antes de añadir dashboards

### Identidad y contexto

Toda entidad de negocio pertenece a una explotación. Identificadores opacos estables,
autor, fecha de creación, versión y estado de anulación. Campaña agrícola, ejercicio
económico y fecha real son dimensiones distintas: una compra de diciembre puede
consumirse en la campaña siguiente. Conservar las tres, sin deducirlas del año natural.
Cambiar campaña no cambia la explotación ni transforma históricos en borradores.

Una tierra gestionada puede contener varios recintos y viceversa a lo largo del tiempo.
Modelar Tierra, RecintoVersion, VinculoTierraRecinto y SuperficieCultivada con fechas
de vigencia. Mantener área declarada, medida geométrica y trabajada separadas.
Un cambio de SIGPAC conserva la equivalencia antigua/nueva y su evidencia; nunca
redistribuye el historial por proporción sin confirmación. Solapes requieren revisión.

### Escrituras y revisiones

Cada comando de negocio lleva identificador único de petición, explotación y versión
esperada. Reenviar el mismo comando devuelve su resultado; no crea otro movimiento.
Dos usuarios editando la misma versión reciben comparación de cambios, no sobreescritura.
Guardar trabajo, consumos y auditoría en una transacción. Un fallo revierte todo.
La cola móvil conserva fecha de realización y fecha de recepción por separado.

Corregir crea revisión con motivo. Anular crea contrapartidas de existencias y efectos
económicos; no borra documentos ni cambia bytes firmados. Los informes firmados
conservan su fotografía histórica; una nueva versión los referencia. Un apunte real
con datos incompletos se guarda con pendientes; una cantidad ilegible no se inventa.

### Cantidades y dinero

Cantidades decimales con unidad, dimensión y precisión de origen. Importes Decimal
en servidor y cadenas decimales en intercambio; no usar Float para cálculos nuevos.
Definir redondeo monetario por línea y por documento, registrar diferencias observadas
sin forzar a que una factura original cuadre con un redondeo distinto.

Unidad comercial (saco, garrafa) necesita contenido por envase. Litros y kilos no se
convierten sin densidad y condiciones documentadas. Semillas en unidades no se pasan
a kg por una constante de especie. Superficie tratada no presupone toda la tierra.
Valores vacíos no equivalen a cero, falso, ecológico, autorizado o pagado.

### Propuestas y confirmación

OCR, dictado, importación y satélite producen propuestas o observaciones. La
confirmación humana crea el hecho de negocio. Conservar original, extracción, campos
corregidos, autor y fecha. Nunca obedecer instrucciones que aparezcan en un documento.
Un proveedor externo recibe papeles solo mediante configuración expresa; por defecto
procesamiento local. No guardar claves en código, capturas o registros de diagnóstico.

## 3. Arquitectura de navegación y contrato común de pantalla

Menú de despacho: Inicio; Tierras y mapa; Trabajos; Cultivos y PAC; Almacén;
Documentos; Cuentas; Personas; Maquinaria; Cuaderno; Normativa; Ajustes.
Cada registro tiene una ficha única accesible desde todos sus contextos. Una factura
vista desde un proveedor abre la misma factura que desde Cuentas.

Cabecera: explotación, campaña, búsqueda, Añadir y pendientes personales. La búsqueda
incluye tierra, referencia SIGPAC, contacto, producto, factura y máquina; respeta
permisos. Un resultado muestra tipo y contexto, no solo un nombre repetido.

Todas las tablas: título y total, búsqueda, filtros con etiquetas removibles,
orden estable, columnas configurables, selección y acciones permitidas, pie con
filtrados/total. Exportar indica si exporta seleccionados, filtrados o todos. Las
sumas no se calculan sobre la página visible: el servidor devuelve el agregado del
conjunto filtrado. Fechas y cantidades se ordenan por valor, no por texto formateado.

Todas las fichas: identidad, estado con explicación, acción principal, historial y
documentos vinculados. Guardar conserva contexto y filtros al volver. Avisar de
cambios pendientes antes de salir. Campos avanzados plegables, no ocultos al guardar.

Estados obligatorios: cargando, vacío nuevo, sin resultados por filtro, acceso
restringido, servicio no disponible, copia local antigua, pendiente de enviar,
conflicto, guardado y dato incompleto. Cada uno tiene texto y siguiente acción.
No presentar una tabla vacía cuando falló la consulta. Teclado, foco visible, etiquetas
de formularios y lectura sin depender del color son requisitos de aceptación.

## 4. Pantallas concretas y recorridos

Los identificadores S01–S20 son estables para tickets y pruebas. Las rutas propuestas
son lógicas; adaptar al enrutador existente sin duplicar páginas antiguas.

### S01 Inicio de gestión — /inicio

Tres zonas: pendientes que requieren acción, resumen de campaña y agenda. Tarjetas
iniciales: tierras sin cultivo, trabajos previstos, documentos por revisar, cobros y
pagos vencidos, inspecciones próximas. Pulsar cualquier cifra abre su lista filtrada.
Mostrar fecha de corte, campaña y número de registros sin dato. Sin cuentas completas
mostrar «Con los importes registrados», no beneficio total de la explotación.
Personalización permite ordenar/ocultar tarjetas y restaurar vista; permisos económicos
se aplican también a contadores. No mezclar alertas agrarias con publicidad o consejos.

### S02 Tierras y mapa — /tierras

Tabla: nombre, municipio, área gestionada, cultivo actual, último trabajo, pendientes,
estado de geometría. Filtros: cultivo, municipio, secano/regadío, titularidad, campaña,
sin cultivo, trabajo realizado/pendiente y sin forma. Vista mapa sincroniza la selección
con la tabla; filtrar no borra tierras. Tierras sin geometría permanecen en una lista.
Acciones: abrir, planificar trabajo, registrar trabajo, comparar campañas, exportar.
Edición múltiple muestra exactamente tierras/campos afectados y vista previa.

Capas: ortofoto, recintos oficiales, tierras gestionadas, cultivo, trabajos y avisos;
lluvia y satélite son capas opcionales con leyenda, fecha, fuente y calidad. No usar
el color de NDVI como «salud» sin explicación. Polígonos con huecos y multipolígonos
deben funcionar. Una consulta por coordenada no acredita propiedad. Al digitalizar:
cerrar anillo, detectar auto-intersecciones, previsualizar área y marcar origen manual.
Geolocalización muestra precisión y requiere acción del usuario. Mapa sin red conserva
solo lo descargado y avisa; nunca sustituye geometría ausente por un cuadrado.

### S03 Ficha de tierra — /tierras/:id

Resumen fijo: mapa, campaña/cultivo, superficie, referencias y próximo trabajo.
Secciones: Historia, Cultivos, Productos y abono, Cosecha y cuentas, Documentos y PAC.
Historia muestra fecha, trabajo, superficie, máquina/persona, insumos y revisión.
Separar «Última labor», «Cultivo declarado», «Observación de campo» y «Estimación».
Un rodillo no sustituye el estado sembrado; una lluvia no crea una nascencia observada.
Comparación anual conserva variedad, siembra, cosecha, rendimiento y coste conocido.

### S04 Agenda y lista de trabajos — /trabajos

Tabla: fecha prevista/real, tierra o cliente externo, tipo/subtipo, responsable,
máquina, duración, superficie, estado y documentos. Calendario y tabla comparten
filtros. Estados: previsto, en curso, realizado, cancelado; anulado pertenece a hechos
registrados. Reprogramar no cambia fecha de un trabajo ya realizado.
Un trabajo de varias tierras tiene cabecera y líneas por tierra, con cantidades
asignadas explícitas. No repartir automáticamente el total por igual.

### S05 Registrar trabajo — /trabajos/nuevo

Paso 1 qué y cuándo: laboreo + rodillo/cultivador/arado/otro, siembra, tratamiento,
abono, riego, poda, desbroce, cosecha u observación. Conservar tipos históricos.
Paso 2 dónde: tierras, recintos y área realmente trabajada por línea.
Paso 3 medios: trabajador, máquina, horas y productos según tipo.
Paso 4 revisión: consumos, dosis, advertencias y efecto sobre historial.
Confirmar una vez. Mostrar resultado y pendientes de completar.

Tratamiento exige proponer producto por marca y número de registro, lote, cantidad
total o dosis claramente elegida, unidad, superficie, fecha y objetivo. Solicitar
aplicador/equipo y demás datos exigibles por el destino conforme a la matriz legal.
Tratamiento de semilla o nave no debe forzarse a hectáreas. Mezclas tienen una línea
por producto; litros de caldo no son litros de producto. Mostrar ambos por separado.

Siembra recoge especie, variedad si conocida, lote de semilla, procedencia, cantidad,
área, fecha y tratamiento previo documentado. Cosecha recoge cantidad, unidad, humedad
si medida, lote y destino; no crea venta ni cobro automáticamente.

### S06 Cultivos e historia — /cultivos

Filas por unidad cultivada: tierra/recinto, área, cultivos de tres campañas previas,
actual, siguiente propuesto, variedad, fechas y alertas. Cultivos sucesivos e
intercalados se modelan como episodios, no sobreescribiendo una celda anual.
Editar plan y registrar siembra son acciones distintas. Historial desconocido queda
marcado. Importar declaración PAC permite comparar antes de aceptar cambios.

### S07 Planificación PAC — /pac/:campana

Primera pantalla: compromisos elegidos, documentos de solicitud/resolución, estado
solicitado/concedido/renunciado, superficie y periodo. No elegir un ecorrégimen por
el agricultor. Admitir varios por ámbitos compatibles, con control de solapes.
Escenarios privados comparan distribución, rotación, mejorantes, leguminosas,
barbecho y superficie por práctica; categorías se obtienen de catálogo versionado.

Cada resultado abre: regla, artículo, ámbito, numerador, denominador, exclusiones,
parcelas que contribuyen y datos ausentes. Resultados: comprobado, no cuadra,
falta información, no aplicable. Un escenario no cambia cultivos reales.
Exportación preparatoria incluye referencias completas, áreas, historia, propuestas,
evidencias, reglas y asuntos para asesor; nunca «solicitud presentada».

### S08 Almacén — /almacen

Pestañas de escritorio: productos de tratamiento, abonos, semillas y otros insumos.
Tabla: nombre comercial, identificación oficial cuando exista, lote, disponible,
unidad, ubicación, caducidad y pendiente de comprobar. Ficha muestra entradas,
salidas, reservas y ajustes; disponible físico separado de reservado.
Compra y factura son eventos distintos: la mercancía recibida una vez no entra otra
vez al llegar su factura. Ajustes de inventario piden motivo; saldo negativo señala
falta de entrada o revisión, no inventa una compra.

### S09 Producto/lote y etiqueta — /almacen/:id

Foto anverso/reverso, recorte legible y original conservado. Propuesta OCR junto al
campo fuente. Confirmar identidad, presentación, contenido, lote y caducidad.
Coincidencias de marca ofrecen registro/formulación; nunca seleccionar por similitud
sin revisión. Autorización de uso se consulta para fecha, cultivo y finalidad.
Semilla añade categoría certificada y evidencia, condición ecológica separada,
tratada/no tratada/desconocida y origen comprado/reempleado/otro.

### S10 Bandeja documental — /documentos

Entrada por archivo/foto, clasificación propuesta factura de compra/venta, albarán,
etiqueta, análisis, inspección, PAC u otro. Estados: recibido, leyendo, revisar,
confirmado, descartado, fallo recuperable. Duplicado exacto por huella; posible
duplicado por emisor/número/fecha/total. Rectificativas no son duplicados a eliminar.
Pantalla partida original/campos a 1440; alternancia conservando posición en móvil.
OCR nunca contabiliza ni mueve almacén antes de confirmar. Cada campo puede quedar
pendiente; «no legible» es diferente de importe cero.

### S11 Compra y factura recibida — /compras/:id

Proveedor, número/serie, fechas emisión/recepción/vencimiento, moneda, líneas,
cantidad/unidad, precio, descuentos, base, impuestos y total original. Distinguir
IVA incluido/excluido y varios tipos, portes y descuentos globales. Asociación
propuesta con producto y recepción. Resumen antes de confirmar: importe y qué
entra realmente al almacén. Factura sin existencias (servicio) no crea producto.
Pagos parciales, abonos y documentos relacionados visibles en la ficha.

### S12 Cosecha, entregas y ventas — /ventas

Separar lote cosechado, entrega/albarán, factura emitida y cobro. Tabla: cliente,
producto, fecha, cantidad, importe conocido, vencimiento, cobrado y pendiente.
Una entrega puede facturarse después o agruparse; no duplicar ingresos al agrupar.
Registrar devoluciones y ajustes de peso/humedad/calidad con evidencia y origen.
No convertir las ventas históricas sin precio en ingresos cero. La emisión fiscal
completa requiere especificación normativa propia antes de activarse como tal.

### S13 Cuentas — /cuentas

Vistas: ingresos/gastos registrados, vencimientos, tesorería, inversiones y margen
por cultivo/tierra. Compra de activo no equivale automáticamente a gasto completo
del cultivo. Mostrar costes directos, repartidos y sin asignar; método de reparto
confirmado (área, horas, consumo o manual) y suma exacta, con redondeo residual visible.
Subvención prevista, concedida y cobrada son estados distintos. No sumar previsión
al ingreso cobrado. Margen operativo y caja tienen tarjetas distintas.

### S14 Movimientos y conciliación — /cuentas/bancos

Primero importación de extracto con lectura previa: cuenta, fecha, concepto, signo,
importe, saldo y referencia si existe. Perfiles de formato guardables y rechazo de
filas ambiguas. Duplicados y traspasos propios revisables. Conciliación muchos a
muchos para pagos parciales o agrupados; comisiones como línea separada.
Deshacer conciliación no borra el movimiento original. Conexión bancaria posterior
solo lectura, proveedor habilitado y consentimiento; no pedir contraseña bancaria.

### S15 Personas y empresas — /personas

Un contacto puede ser cliente, proveedor, arrendador, trabajador o asesor. Nombre,
identificador fiscal opcional, canales, direcciones, roles y documentos. No fusionar
homónimos automáticamente. Ficha agrupa trabajos, facturas, cobros/pagos y tierras
arrendadas según permisos. Notas con autor. No enviar mensajes desde la aplicación
sin acción expresa del usuario.

### S16 Maquinaria — /maquinaria

Tabla: máquina, tipo, matrícula/serie, propiedad/alquiler, horas, próxima revisión,
documentación y disponibilidad. Ficha separa ITV, ITEAF, mantenimiento, seguro y ROMA.
Cada obligación tiene aplicabilidad, fuente, última inspección, resultado, próxima
fecha y documento. No calcular plazo solo por «tractor» o «sulfatadora»; pedir
clasificación técnica necesaria. Avisos al planificar trabajo y registro de averías.

### S17 Servicios a terceros — /servicios

Cliente, lugar externo, presupuesto, trabajo, máquinas/horas, insumos propios o del
cliente, tarifa, entrega y cobro. Tierra externa no entra en la superficie PAC propia.
Insumos del cliente no descuentan almacén propio. Trabajo aceptado no equivale a
facturado. Conservar revisión de tarifa y alcance; rentabilidad muestra costes conocidos.

### S18 Tiempo y observaciones — /tiempo

Por tierra: lluvia 24h/7d/30d con ventana y zona horaria, estación y distancia,
cobertura de datos, fuente medida/estimada, previsión separada. Pluviómetro propio
permite corrección con motivo. No sumar días ausentes como cero. Estado del suelo
observado se registra con fecha; inferencia de humedad indica supuestos y límites.
Satélite: fecha de adquisición, nubes válidas, resolución, índice y comparación;
sin píxeles útiles mostrar falta de imagen, no tierra seca. Alertas ITACyL son avisos
territoriales, no diagnóstico automático de plaga en una parcela.

### S19 Cuaderno y normativa — /cuaderno y /normativa

Cuaderno se genera de hechos confirmados, sin transcribir trabajos de nuevo.
Panel de pendientes agrupa campos faltantes por registro con botón para completarlos.
Normativa filtra por territorio, campaña y tema; cada aviso abre su ficha legal,
fuente, versión y cálculo. Documentos adjuntos de asesor no se presentan como BOE.
Exportar registra fecha de corte y pendientes; firmar conserva exactamente lo firmado.

### S20 Ajustes — /ajustes

Explotación, usuarios/permisos, campañas, unidades, ubicaciones, vistas guardadas,
fuentes de datos, copias y restauración. Roles mínimos: titular, gestor, trabajador,
asesor y consulta; permisos por acción y acceso económico, no solo por menú.
La personalización cambia presentación, nunca fórmulas legales. Copia incluye base,
adjuntos y manifiesto verificable; restauración se prueba en entorno separado.

## 5. Semillas: modelo que falta concretar antes de E4

Crear ArticuloSemilla y LoteSemilla, enlazados a especie/variedad con versión de catálogo.
Campos: proveedor/origen propio, campaña de producción si conocida, lote del productor,
categoría declarada, certificador, documento/etiqueta, cantidad y unidad, tratamiento,
condición ecológica y evidencia, fecha de recepción y ubicación. Germinación/pureza
son opcionales con análisis y fecha; no inventar valores típicos.

Reempleo conserva vínculo con cosecha de origen y transformación/limpieza. Merma se
registra; no es consumo de siembra. Protección de variedad y permiso de reempleo se
evalúan separadamente de certificación. Estado sin documentación = pendiente de
comprobar, no ilegal por defecto. Requisitos de una ayuda se aplican solo a quien
la solicita y con su versión vigente. Un certificado de producción ecológica no
demuestra por sí solo categoría de semilla certificada.

Prueba: 1.000 kg recibidos, 600 kg sembrados en 3 ha y 100 kg en otra tierra: saldo
300 kg; primeras 3 ha a 200 kg/ha. Anular la segunda siembra devuelve 100 kg.
La corrección no cambia el documento original ni acredita retroactivamente un lote.

## 6. Fórmulas y pruebas de aceptación comunes

| ID | Entrada | Resultado exigido |
|---|---|---|
| A01 | Compra 5 L, aplicación 2 L y 3 L | Saldo 0; reenvío no duplica; anular 2 L devuelve 2 |
| A02 | 2 L en 4 ha | 0,5 L/ha; si falta área, dosis desconocida |
| A03 | Abono 600 kg en 3 ha, N 15 % acreditado | 200 kg/ha de producto; 30 kg N/ha; P desconocido si falta |
| A04 | Rodillo después de siembra | Historial contiene ambos; cultivo permanece; sin inferir nascencia |
| A05 | Plan de siembra confirmado como plan | No consume semillas ni añade labor realizada |
| A06 | Factura 121 EUR, pago 40 EUR | Pendiente 81; segundo importe conciliado no crea segunda factura |
| A07 | Traspaso propio 500 EUR | Dos movimientos vinculados, cero ingreso/gasto operativo |
| A08 | Venta con 8.000 kg y sin precio | Cantidad conocida, importe pendiente; no ingreso cero |
| A09 | Fuente legal de otra comunidad/año | No se aplica a CyL 2026 por semejanza |
| A10 | 2 ha sin cultivo en denominador PAC | Resultado incompleto, nunca verde ignorando esas hectáreas |
| A11 | Imagen cubierta por nubes | Sin dato útil; no NDVI cero ni alarma de sequía |
| A12 | Móvil repite envío al reconectar | Un trabajo, sus consumos una vez, respuesta recuperable |
| A13 | Tierra ajena o enlace a adjunto de otra finca | Sin datos ni filtración de existencia |
| A14 | Editar registro firmado | Revisión nueva, firma antigua verificable y bytes idénticos |
| A15 | Factura llega después de albarán recibido | Una entrada de almacén y vínculo entre ambos documentos |
| A16 | Filtro de 10 tierras de un total de 64 | Pie 10 de 64; exportación y mapa respetan selección declarada |

## 7. Entregas pequeñas para DeepSeek

No ejecutar E0–E13 como una reescritura única. Cada ticket entrega código, migración
si procede, pruebas de contrato, recorrido visible y limitaciones. Rutas y nombres de
modelos nuevos son propuestas: comprobar equivalentes existentes antes de duplicarlos.

| Ticket / fase | Dependencia | Entrega verificable |
|---|---|---|
| T01 / E0 | Ninguna | Inventario ruta→pantalla→API→modelo→pruebas; estados realmente existentes |
| T02 / E0 | T01 | Auditar valores por defecto de autorización, ecológico y nutrientes; plan de migración sin inventar históricos |
| T03 / E1 | T01 | Prototipos Stitch S01/S02/S03 y navegación; aceptación de tres tareas completas |
| T04 / E1 | T03 | Armazón común, contexto, tabla y ficha reutilizables; 390/1024/1440 px |
| T05 / E2 | T02 | Identidad/versiones de recinto e importación repetible sobre copia |
| T06 / E2 | T04,T05 | Mapa de explotación con selección/filtros y lista sin geometría |
| T07 / E3 | T01 | Corpus autorizado de documentos y evaluación por campo, sin autoescritura |
| T08 / E3 | T04,T07 | Bandeja y revisión original/propuesta, duplicados y rectificativas |
| T09 / E4 | T02,T08 | Unidades, recepción, lotes y libro de movimientos; A01/A02/A15 |
| T10 / E4 | T09 | Semillas, fotos de etiqueta y asignación a siembra |
| T11 / E5 | T04 | Contactos reutilizables y enlaces; migración de textos sin fusiones inseguras |
| T12 / E6 | T09,T11 | Entregas/ventas, importes decimales, cobros parciales; A06/A08 |
| T13 / E7 | T12 | Gastos/activos/repartos y límites de métricas; abono A03 |
| T14 / E8 | T04,T11 | Maquinaria e inspecciones separadas con documento/fuente |
| T15 / E9 | T05,T09,T14 | Trabajos por tierra, revisiones y estado derivado; A04/A05/A12/A14 |
| T16 / E9 | T12,T15 | Servicios a terceros y separación de superficie/stock propios |
| T17 / E10 | T06,T15 | Lluvia piloto 3 tierras, cobertura y observaciones |
| T18 / E10 | T17 | Satélite piloto, nubes y coste medido antes de escalar a 64 |
| T19 / E10 | T12,T13,T15 | Dashboards con consultas explicables y cifras contrastadas |
| T20 / E11 | T12 | Extractos y conciliación reversible; A07 y duplicados |
| T21 / E12 | T05,T10,T15 | Historial, compromisos y escenarios; motor con reglas revisadas |
| T22 / E12 | T21 | Piloto BCAM/rotación elegida y paquete preparatorio PAC |
| T23 / E13 | T22 | Ampliar práctica por práctica; cada una con fuente, excepción y límites |
| T24 / E13 | T20 | Banca opcional solo tras seleccionar proveedor y consentimiento |

Prioridad: T01–T04 primero; luego un recorrido completo compra→almacén→trabajo→tierra
antes de multiplicar paneles. Evitar una pantalla bonita sobre cifras aún inexistentes.

## 8. Encargo preciso a Stitch y criterios de UX

Usar DESIGN.md como punto de partida, revisando sus reglas para despacho. No enviar
datos personales ni la base real. Dataset ficticio explícito: 64 tierras, nombres
largos, 10 sin cultivo, 3 sin forma, importes desconocidos, un pago parcial y una
inspección vencida. Generar estados vacío, cargado y conflicto, no solo portada ideal.

Primer encargo: «CRM agrícola español de escritorio; diseña S01/S02/S03 de este
contrato, navegación persistente, jerarquía clara y tablas compactas; a 1024 px no
ocultes Acciones; panel lateral pasa debajo; mapa y tabla comparten selección;
filtros visibles; detalle conserva campaña; móvil simplifica acciones sin perder
datos. No inventes salud, ingresos o cumplimiento. Incluye interacción y estados».

Después S05/S08/S10 juntos (registrar y revisar); S07 con cálculos explicables;
S11–S17 con componentes comunes. Textos finales viven en textos.py. Adaptar diseño,
no pegar HTML externo con dependencias, teléfonos, garantías o métricas inventadas.

Validación de tareas: encontrar tierra y último trabajo; registrar 2 L sin confundir
dosis; revisar factura y recepción sin doble stock; localizar deuda y pago; comparar
plan PAC con historial. Objetivo inicial: cada tarea localizable desde menú/contexto
sin ayuda y sin retrocesos innecesarios; medir tiempo y errores con usuario, no afirmar
usabilidad por una captura. Probar teclado, zoom 200 %, móvil y red interrumpida.

## 9. Puertas de calidad y qué no declarar terminado

Auditar mapeo de modelos existentes: VentaDeCosecha no acredita ingresos; Factura
no acredita recepción; foto_etiqueta no acredita flujo de cámara; EquipoAplicacion
no cubre toda la maquinaria. Revisar defaults permisivos antes de reutilizarlos.

Pruebas de OCR con documentos autorizados reales, anonimizados cuando proceda,
incluyen inclinación, sombras, varias páginas, coma decimal, IVA incluido, albarán,
rectificativa y factura sin producto identificable. Separar corpus de desarrollo y
evaluación. Informar exactitud por campo y tasa de revisión; no prometer un porcentaje
sin medirlo. Falso positivo crítico: registro de producto, cantidad/unidad e importe.

Migraciones: copia de base y adjuntos, ensayo de restauración, transformación
versionada, conteos y relaciones antes/después, firma intacta, vuelta atrás probada.
El añadido automático de columnas no sustituye migraciones de datos ni de dinero.

Cada ticket termina con suites pertinentes, recorrido de servidor aislado si cambia
funcionalidad, capturas si cambia UI y lista de pendientes reales. No recontar archivos
como si fueran nuevas capacidades. No corregir pruebas solo para conservar verde:
documentar el cambio de comportamiento. Si falta fuente legal, dejar regla pendiente;
si falta documento real, declarar OCR no evaluado en ese caso. Nunca afirmar «sin
fallos» ni «cumple toda la PAC» por pasar pruebas.

## 10. Contrato de los cinco paneles

Todos permiten ir del número a sus registros. Mostrar fecha de corte, filtros y
datos pendientes; la respuesta del servidor incluye valor nullable, unidad, ámbito,
numerador/denominador cuando corresponda, cobertura y enlace al detalle. Un permiso
que oculta dinero también lo elimina de la respuesta, no solo del HTML.

| Panel | Métricas y desglose | Exclusiones y aceptación |
|---|---|---|
| Explotación | Superficie gestionada, cultivada y pendiente; tareas próximas; documentos pendientes | No sumar recintos solapados; 64 tierras no implica 64 recintos ni 64 cultivos |
| Campo | Área trabajada por tipo, último trabajo por tierra, lluvia y observaciones | Dos pases de rodillo pueden sumar ha de trabajo, pero no duplican ha únicas; mostrar ambas etiquetas |
| Economía | Facturado registrado, cobrado/pagado, pendiente, vencido, costes asignados y sin asignar | Factura y movimiento conciliado no suman dos ingresos; previsiones fuera de realizados |
| Almacén y maquinaria | Existencia por lote/unidad, reservas, caducidades e inspecciones | No sumar kg con L; stock negativo visible; vencimiento desconocido no es vigente |
| Campaña y PAC | Área por cultivo/práctica, historia completa, reglas comprobadas y pendientes | No porcentaje de cumplimiento global que oculte una regla crítica pendiente |

Margen conocido por tierra = ingresos atribuidos registrados − costes atribuidos
registrados. Mostrar el alcance y los costes/ventas sin asignar; no llamarlo beneficio
contable. Tesorería conocida = movimientos de cuentas seleccionadas, sin sumar los
dos lados de traspasos internos en entradas/salidas operativas. Pendiente de factura
= total exigible corregido − pagos/cobros aplicados; sobrepago se muestra como saldo
a favor, no deuda negativa sin explicación. Vencido se calcula por vencimiento de
cada cuota, no por fecha de factura.

Aceptación: sembrar una tierra actualiza solo los paneles del contexto afectado;
cambiar filtro mantiene igualdad entre tarjeta y detalle; los agregados permanecen
iguales al cambiar tamaño de página. Comparación entre años explicita diferencias de
área, periodo y cobertura de importes. Caché se invalida al confirmar/revisar/anular.

## 11. Persistencia y API: corte vertical de referencia

Antes de crear tablas, T01 entrega equivalencias con modelos actuales. Estructura
objetivo: DocumentoOriginal→Extraccion→PropuestaConfirmada; Recepcion→LineaRecepcion;
Articulo→Lote→MovimientoExistencias; Trabajo→LineaTrabajo→Consumo; Factura→LineaFactura;
Vencimiento→AplicacionPago→MovimientoCuenta; Compromiso→AdhesionAnual→AmbitoSuperficie;
Escenario→AsignacionCultivo→ResultadoRegla. Cada flecha representa un vínculo con
identificador, no copia libre de nombre. Factura y recepción pueden relacionarse
parcialmente por líneas. Un documento puede servir de evidencia a varios hechos.

Lecturas de listas aceptan filtros tipados, orden, paginación y campaña; devuelven
items, total filtrado, total de contexto y agregados completos. Validar campos de
orden admitidos. Exportación reutiliza la misma consulta y permisos. No filtrar en
cliente una única página y presentar su recuento como si fuera toda la explotación.

Comando de registrar trabajo: identificador de petición, fecha/hora y zona, tipo y
subtipo, líneas con tierra/recinto/área, consumos con lote/cantidad/unidad, personas,
máquinas, documentos y versión esperada si corrige. Servidor verifica pertenencia,
dimensiones y coherencia; devuelve identificador, revisión, avisos, pendientes y
efectos en existencias. Advertencia normativa no debe impedir registrar un hecho
real; sí deben impedirse referencias ajenas, cantidades imposibles de interpretar
y pérdida de integridad. Distinguir «registrar que ocurrió» de recomendar su ejecución.

No exponer nuevas rutas hasta que autorización, anulación y exportación estén
probadas. Consultas de dashboards y cuaderno deben consumir los mismos hechos
confirmados. Evitar un segundo almacén o historial exclusivo del panel.

## 12. Planificación de cultivos: flujo de decisión completo

1. Elegir campaña, superficie bajo gestión y compromisos acreditados. Mostrar lo
   desconocido de anteriores campañas antes de proponer cultivos.
2. Crear escenario copiando estructura de tierras, nunca labores o consumos. El
   usuario decide si prellenar cultivos; el plan queda etiquetado como propuesta.
3. Asignar cultivo por unidad y área; incluir barbecho, cubierta, mezcla y cultivo
   secundario con categoría documentada. No equiparar nombre comercial y código PAC.
4. Recalcular por ámbito: condicionalidad, práctica elegida y compromiso regional.
   Para cada uno construir su propio denominador, sin un porcentaje universal.
5. Comparar alternativas por cumplimiento revisado, necesidades de semilla, costes
   previstos y preferencias agronómicas. Precio/rendimiento esperados llevan autor,
   fecha y rango; no se convierten en ingresos reales ni recomendación garantizada.
6. Mostrar acciones explicables: «faltan datos del cultivo anterior en estas tierras»
   o «esta propuesta no alcanza la superficie exigida por esta regla». Si se sugiere
   cambiar cultivo, indicar el efecto exacto y mantener decisión humana.
7. Aprobar el plan interno crea versión congelada; ejecutar después genera trabajos
   reales vinculados. Diferencias plan/real se ven, no se corrigen retrospectivamente.
8. Preparar expediente para asesor: listado por recinto, áreas, historia, práctica,
   documentos y discrepancias. Guardar copia del paquete y fecha; presentar la PAC
   sigue fuera del alcance de este CRM.

Pruebas adicionales: división de un recinto entre dos cultivos; arrendamiento que
empieza a mitad de campaña; historial de tierra incorporada desconocido; práctica
diferente entre tipologías; cambio de cultivo después de cerrar plan; pérdida de
superficie gestionada; excepción documentada con caducidad; geometría nueva que no
permite reconstruir automáticamente el historial. Ninguno debe dar un verde ficticio.
