# Lo que pide la Junta, y qué falta

> **Actualización 22/09/2026:** el descriptor CUE v3.11.4 y su esquema JSON ya están en
> `data/iuws_fuentes/`, extraídos del Anexo VI oficial. El formato del JSON ya no es un
> bloqueo: lo que bloquea ahora son los **valores de los catálogos** (los códigos, que no se
> inventan) y el certificado con su alta. Consulta
> [la actualización IUWS](ACTUALIZACION_IUWS_2026-09-22.md).

Lista verificada sección por sección contra la **app oficial CUECyL** (sus secciones,
sacadas del documento `03_CastillaYLeon_CUECyL_instrucciones.pdf`) y contra lo que
**existe hoy en este repositorio**. Sin adornos: lo que no está, no está.

> **Lo que la ley obliga y lo que no, para leer esta lista con la cabeza en su sitio.** Tener el
> cuaderno es obligatorio cuando lo pide la normativa de tu sector; **mandarlo a la Junta es
> voluntario** (artículo 10.2 del Real Decreto 1054/2022: «decidirán de forma voluntaria poner a
> disposición de la administración […] la información que hayan cumplimentado en el CUE»), y se
> puede llevar con **cualquier programa propio** que tenga el contenido mínimo del anexo II
> (artículo 10.3). O sea: **todo lo que falta en esta lista por el volcado oficial no deja al
> agricultor sin cuaderno**. Lo comprobado artículo por artículo está en
> [`LO_QUE_OBLIGA_LA_LEY.md`](LO_QUE_OBLIGA_LA_LEY.md).

Última revisión: cuando el proyecto tenía 5621 tests de Python y 1172 de JavaScript.

**Cómo leer la columna «Estado»:**

- ✅ **Hecho** — funciona de punta a punta y tiene tests.
- ⚠️ **A medias** — se puede hacer, pero mal: falta un campo, o no está distinguido, o
  solo está la mitad del camino.
- ❌ **Falta** — no existe.
- 🔒 **Depende de David** — no es código: hace falta un dato, un fichero o una firma.

---

## 1. Las secciones de la app oficial, una por una

| # | Sección de CUECyL | Estado | Qué hay / qué falta |
|---|---|---|---|
| 1 | Cuaderno: Datos básicos | ✅ | `Explotacion` + `Campana`, con endpoints y pantalla |
| 2 | Cuaderno: Asesores / Aplicadores | ✅ | **Aplicador** (carné, ROPO, REGANIP) y **asesor** (`Asesor`: su nº de inscripción en el registro ROPO, el ámbito —plagas, producción integrada, ecológico— y la entidad que lo certifica). Son dos figuras distintas: el asesor dice qué hacer y el aplicador lo hace. El asesoramiento se apunta en cada tratamiento (campos 44 a 53), y **sin nº de ROPO no se deja guardar**, porque el interfaz de la Junta lo rechaza |
| 3 | Explotación: DGC | ✅ | `Parcela` completa, y **conector con el SIGPAC**: se le da la referencia del recinto y trae sola la superficie oficial, la pendiente, el uso y el dibujo del trozo en WKT, que es el mismo formato que guardamos. Los servicios son públicos y sin autenticación, y los datos oficiales (933 productos, 34 usos) están descargados en `data/sigpac/`. Sin cobertura se dice y se apunta a mano. **Corregido en la ronda 16:** faltaba lo que la app oficial tiene en las pestañas de una DGC —«Características DGC» (el cultivo) e «Historial Cultivos» (los de las campañas anteriores)—. La tabla `ParcelaCultivo` estaba desde las primeras rondas **y no la usaba ninguna pantalla**: el cuaderno ya le decía al agricultor «a El Prado le falta decir qué cultivo tiene este año» y **no había forma de contestarle**. Ahora se dice, se ve el historial, se avisa si repites el cultivo del año pasado, y el «Cultivo» de cada tratamiento y cada labor **se rellena solo** (el «campo calculado» de la app oficial). **Y corregido en la ronda 20:** la **forma del trozo** que devuelve el SIGPAC se guardaba desde la ronda 10 y **no se veía en ninguna parte**. Ahora se dibuja, con las tres partes de la referencia por separado (polígono, parcela y recinto, como en el papel del SIGPAC) y sin mandar el polígono entero al móvil |
| 4 | Explotación: UHC | ✅ | `GrupoParcelas`, a mano y automático (mismo cultivo, mismo sistema, radio de 8 km). **Corregido en la ronda 17: esto era la tercera vez que pasaba lo mismo.** El modelo tenía tres endpoints —listar, crear a mano y «calcular» automático— y **ninguna pantalla los llamaba**: `grupo_id` no aparecía ni una vez en todo el JavaScript, así que el trabajo que ahorra esto no lo ahorraba nadie. Ahora hay pantalla, y al apuntar un tratamiento, un abono o una labor **salen los grupos** después de la lista de parcelas: un apunte para todas las del grupo, con la superficie sumada. Y se cerró un agujero de verdad que apareció al mirarlo: **la comprobación de que no se trata más superficie de la que hay solo se hacía con una parcela**, así que en un grupo no se comprobaba nada y se podían apuntar 100 hectáreas sobre 5 sin que el programa dijera una palabra |
| 5 | Explotación: Registro de maquinaria | ✅ | `EquipoAplicacion` con ROMA e ITEAF, y avisos antes de que caduque |
| 6 | Explotación: **Instalaciones** | ✅ | `Instalacion`: naves, almacenes, invernaderos y balsas, con su referencia catastral, uso y superficie. Con pantalla propia en *Mis cosas* |
| 7 | Explotación: **Medidas preventivas** | ✅ | `MedidaPreventivaDeclarada`: el registro propio de la explotación, a nivel de finca, con las diez medidas del catálogo, las tuyas propias por escrito y el histórico (desmarcar no borra). Y lo que lo une todo: **lo declarado aquí ya sale marcado al apuntar un tratamiento**, que antes no se preguntaba nunca. Al apuntar sin haberlas declarado, el cuaderno avisa de que falta esa sección |
| 8 | Labores: Siembra / Plantación | ✅ | `Labor` con **semilla, dosis de siembra y número de lote**, más si el material venía tratado, si se compró, cuándo, si fue siembra directa, y para la plantación la densidad y el marco. Son los campos 4 a 15 del bloque 6 del contenido mínimo |
| 9 | Labores: Riego | ✅ | `Labor` de riego con **volumen de agua, de dónde sale** (pozo, canal, balsa, comunidad de regantes…), el sistema de riego, el nº de contador y **los nitratos del agua**. El agua también es un dato de abono: el documento lo sitúa en el subbloque de fertirrigación |
| 10 | Labores: Cosecha | ✅ | `/api/cosecha`, con **bloqueo por plazo de seguridad** y explicación |
| 11 | Labores: Otras prácticas culturales | ✅ | `Labor` con tipo libre. **Corregido en la ronda 14:** el documento oficial, de este mismo apartado, dice «permite buscar y/o anotar otras prácticas culturales en una DGC: **Laboreo, mantenimiento de cubierta, pastoreo**, etc.» — y **faltaban dos de las tres**. Y había un problema mayor: la lista de tipos existía en el catálogo y **ninguna pantalla la ofrecía**, así que pulsar «OTRO TRABAJO» guardaba la palabra `otra` sin decir jamás cuál: la poda, el desbroce, la escarda y el laboreo estaban escritos y no se podían elegir. Ahora el asistente pregunta **cuál de ellos** y se guarda la práctica de verdad. Sigue habiendo «OTRA COSA» para lo que no esté en la lista |
| 12 | Fitosanitarios: Cesta de la compra | ✅ | `ProductoFitosanitario`, y el tratamiento solo puede usar productos que estén. **Corregido en la ronda 15:** la app oficial tiene aquí un botón «Situación Cesta» que enseña «las cantidades adquiridas y gastadas», y en este programa los cuatro campos de la compra (`cantidad_comprada`, `unidad_compra`, `fecha_compra`, `proveedor`) **estaban en la tabla desde el principio y no los leía nadie**: ninguna pantalla los pedía, `ProductoSalida` ni siquiera los devolvía, y no había cuentas. O sea que la Cesta estaba a medias: se apuntaba *qué* producto tienes y no *cuánto*. Ahora se piden, se devuelven y hay una pantalla **«Lo que tengo en el almacén»** con lo comprado, lo echado y lo que queda — que es la pregunta que se hace de verdad: «¿me llega para tratar la parcela?». Y cuando la resta **no se puede** hacer, se dice por qué en vez de dar un número (ver abajo). **Y corregido otra vez en la ronda 19:** faltaba la **autorización** (ver el apartado 2 bis) |
| 13 | Fitosanitarios: Tratamiento | ✅ | El núcleo: producto, dosis, superficie, plaga, justificación, aplicador, máquina, tiempo, franja, medidas. **Corregido en la ronda 18:** faltaba **cómo se echó**, que es lo que se apunta justo después de echarlo. Se encontró mirando qué campos de la tabla no llegaban a ninguna pantalla: había **once** del registro de tratamientos que se guardaban y ahí se quedaban. Dos los pide el contenido mínimo **por su número** —la hora (campo 3), que el volcado declaraba y no había forma de llenar, y el estado de la planta (campo 8), que **ni estaba declarado**—, y el resto son las condiciones del día (temperatura, humedad, viento y de dónde venía), la mezcla por hectárea, cuántos estaban trabajando y si pasó algo raro. Van en **una sola pantalla opcional** que se salta con un toque: el asistente del tratamiento es el que más se usa y no se le pueden añadir tres pantallas. Y de paso se arregló un aviso que **saltaba siempre**: «¿has dejado la orilla sin tratar?» se preguntaba a nadie, porque su etiqueta estaba escrita y nunca se había puesto en ninguna pantalla |
| 14 | Fitosanitarios: Uso de semilla tratada | ✅ | `tipo = semilla_tratada`: queda distinguido de un tratamiento normal, se puede listar aparte, y sigue exigiendo parcela porque la semilla se siembra en algún sitio |
| 15 | Fitosanitarios: Tratamiento postcosecha | ✅ | `tipo = postcosecha`, con el **producto tratado y su partida** (`producto_cosechado`, `lote_cosecha`) y el local donde se hizo |
| 16 | Fitosanitarios: Tratamiento de instalaciones | ✅ | `tipo = instalaciones`, con la nave y el **plazo de reentrada** (los días antes de poder entrar sin protección). **Ya no hay ninguna sección imposible de cumplimentar** |
| 17 | Fertilización: Recomendación de nutrientes | ✅ | El plan de abono del año: necesidades N-P-K por cultivo, producción esperada y aportes del suelo. Y lo que de verdad sirve: **se compara con lo que se lleva echado** y avisa al pasarse. Se puede corregir, porque es una previsión, no un apunte |
| 18 | Fertilización: Fertilización | ✅ | Con **unidades fertilizantes** calculadas y aviso en zona de nitratos |
| 19 | Otras actividades: **Cosecha comercializada** | ✅ | `VentaDeCosecha`, con las **dos clases que separa la norma** (venta a comprador y venta directa), la fecha —que puede ser un intervalo—, el producto, la cantidad en kilos, toneladas o unidades, y para la trazabilidad el lote, el comprador, el nº de albarán y las parcelas de origen. Lo que de verdad sirve: **compara lo vendido con lo cosechado y avisa si no cuadra** |
| 20 | Otras actividades: **Analíticas** | ✅ | `Analitica`, con las cinco clases (suelo, agua de riego, cultivo, producto cosechado y residuos), las dos fechas, la parcela, la nave, el lote, el laboratorio con su NIF y el nº de boletín, los números **con clave** y el boletín subido en PDF o foto. Los nueve parámetros del suelo son los del contenido mínimo del CUE; los demás van marcados como **no oficiales**, porque ninguna norma los fija. El plan de abono se puede apoyar en un análisis, y si se anula, el plan se queda sin apoyo |
| 21 | **Documentación anexa** | ✅ | `DocumentoAnexo`: los papeles que acompañan al cuaderno, **agrupados en carpetas** que pone el agricultor. Contratos, facturas y albaranes de entrega de envases a Sigfito (los tres que nombra el documento oficial) más «otros». Los ficheros van a disco, nunca a la base de datos ni al repositorio, con el nombre decidido por el programa. **Se puede apuntar un papel sin subir el fichero** —«el contrato está en el cajón de arriba»—, y eso importa: obligar a subir el fichero dejaría fuera al agricultor que no sabe hacerle una foto. Nada se borra: se anula con su motivo y el fichero sigue ahí |

**Resumen: 21 apartados hechos, 0 a medias, 0 sin empezar** (los veinte apartados de la app
oficial más su repositorio de documentación). **Están todos**, aunque la 24 —la exportación
IUWS— sigue a medias por un motivo que no es de código.

De lo que la Junta pide para poder entregar el cuaderno (apartado 2, que son 10 cosas):
**3 hechas, 3 a medias, 4 que dependen de David.**

> ⚠️ **Corrección de la ronda 35.** Este resumen decía «1 hecha, 3 a medias, 6 que dependen de
> David» y la tabla tenía **1, 4 y 5**: sumaba 10 igual, así que el test que solo miraba el
> total lo daba por bueno. Lo que estaba mal no era la suma, sino **el reparto**. Ahora el test
> cuenta los iconos de la tabla uno por uno (`test_lista_de_la_junta.py`) y compara los tres
> números con los del resumen, así que no puede volver a pasar. Y el plazo de conservación
> pasó de 🔒 a ✅ en la misma ronda, con el artículo 16.3 del Real Decreto 1311/2012 delante.

> ⚠️ **Corrección de la ronda 13, y esta es de fondo.** Hasta ahora esta tabla tenía 21 filas,
> pero la fila 21 era «Utilidades: Ver listados», y **«Utilidades» no es un apartado del
> cuaderno**: es el menú donde están los informes. El apartado que faltaba de verdad era
> **Documentación**, y no aparecía por ninguna parte. Lo dice el documento oficial, en su propia
> frase de resumen: *«El Cuecyl se estructura en seis secciones con veinte apartados organizados
> por su temática…, además de un repositorio de documentación.»* Es decir: veinte apartados (que
> son exactamente las filas 1 a 20 de esta tabla, una por una) más el repositorio de
> documentación. El total de 21 seguía cuadrando por casualidad, y por eso el test que cuenta las
> filas no lo cazó: **un total correcto con un elemento equivocado dentro pasa cualquier suma**.
> Se encontró releyendo el documento original, no el resumen. Los informes siguen existiendo, y
> están anotados en el apartado 3.
>
> ⚠️ **Corrección anterior (ronda 4):** el resumen decía «13 hechas, 4 a medias, 0 sin empezar», y
> **no sumaba 21**: eran 17. Estaba mal contado a mano, y además decía que no faltaba ninguna
> sección cuando la cosecha comercializada llevaba desde el principio marcada como inexistente.
> Se deja escrito para que nadie vuelva a fiarse de un total sin sumarlo, y hay un test
> (`test_lista_de_la_junta.py`) que lo recuenta cada vez.

---

## 2. Lo que la Junta pide para poder entregar el cuaderno

Esto es aparte de las secciones: es lo que hace que el cuaderno **valga** para la
administración.

| # | Qué | Estado | Detalle |
|---|---|---|---|
| 22 | **Firma del cuaderno** | ⚠️ | **Se comprueba de verdad desde la ronda 12.** Está el mecanismo entero: el fichero canónico del cuaderno, su huella, la orden de AutoFirma (sacada del manual oficial) y el aviso cuando algo cambia después de firmar. Y además, **cuando el agricultor sube el fichero de firma, se abre y se mira** (`app/cades.py`): se comprueba que el resumen que lleva dentro sea el del cuaderno, se comprueba la cuenta de la firma con el certificado, y se comprueba que la firma sea **del mismo agricultor** que ha entrado. Una firma de otro cuaderno o de otro agricultor **se rechaza**. Los tres finales están distinguidos a propósito: comprobada, no comprobada (se guarda y se dice por qué) y tocada (se rechaza). **Falta la cadena de confianza**: comprobar que el certificado lo haya emitido una autoridad de fiar necesita la lista de autoridades raíz, y eso no se puede deducir del fichero, así que `cadena_de_confianza_comprobada` está en `false` y se declara. En la práctica pesa poco: el agricultor entra con su certificado y lo valida el servidor web, así que la cadena ya se comprobó al entrar. Y las firmas de **curva elíptica** se dicen «no comprobadas», no «malas»: no saber leer algo no es lo mismo que saber que está mal |
| 23 | **Autenticación con certificado digital** | ✅ | Se lee el certificado que ha validado el servidor web, se saca el NIF (con validación de DNI/NIE/CIF) y se entra sin teclear nada. **Las cabeceras no se creen por defecto**, para que nadie pueda falsificar el certificado mandando una cabecera |
| 24 | **Exportación IUWS** | ⚠️ | **Hecho todo lo que se puede hacer sin el descriptor**: las seis direcciones con sus ejemplos del anexo, el catálogo de los 19 mensajes traducido, la lectura de respuestas, el **identificador ajeno de cada actividad** (lo que evita duplicar y permite corregir), el sobre `CUADERNO` documentado y **el contenido mínimo del CUE campo por campo** con el número que le da el documento técnico. Y desde la ronda 12, **el cliente que llama al interfaz de verdad**: la cabecera del certificado, el token, seguir una carga, y una prueba de conexión que **ya funciona hoy**, sin tener nada configurado, porque el método de versión es el único que el interfaz deja abierto (comprobado: contesta `3.11.4`). Se comprobaron los siete métodos uno por uno y está apuntado qué contestó cada uno y en qué dirección. **El descriptor ya está** (v3.11.4, en `data/iuws_fuentes/`, con su esquema JSON y su huella
SHA-256). Lo que falta ahora son **los valores de los catálogos**: el esquema oficial **no admite
un campo vacío** (528 tipos, ningún `null`) y los códigos no se inventan, así que **no se fabrica
ese JSON**. Y la firma del parámetro `data-signed` **ya se hace con el certificado de verdad y sin exportar ninguna clave**: se firma **donde la clave vive** (el almacén de Windows, con `scripts/firmar_con_el_certificado.ps1`) y el programa solo recibe la firma. Comprobado el 27/09/2026: la firma sale y se verifica con la clave pública del certificado. Sigue sin haber ninguna librería de criptografía añadida a Python, y sigue sin hacer falta; y si no puede firmar dice que no pudo en vez de devolver una firma inventada. Todo esto está en [`INTEGRACION_IUWS.md`](INTEGRACION_IUWS.md) |
| 25 | **Periodo de conservación** | ✅ | **Confirmado el 27/09/2026** en el texto consolidado del BOE: el artículo 16.3 del Real Decreto 1311/2012 dice que «los registros y documentos se conservarán al menos durante los 3 años siguientes a su fecha de emisión», y nombra uno por uno lo que hay que guardar con el cuaderno (las facturas, los certificados de inspección de las máquinas, la documentación del asesoramiento y los análisis de residuos). **Está dentro de la aplicación** (ayuda → «cuánto tiempo guardar los papeles»), con el número del artículo delante, y en [`LO_QUE_OBLIGA_LA_LEY.md`](LO_QUE_OBLIGA_LA_LEY.md) con la comilla literal. Del mismo artículo 16.1 sale además el **plazo de volcado: un mes** desde la fecha del tratamiento, que es lo que habrá que respetar el día que se presente por el interfaz. **Nada se borra solo**: la ley dice el mínimo que hay que conservar, no que a los 3 años se pueda tirar sin mirar |
| 26 | **Límites de nitrógeno** (Orden MAV/398/2022) | ⚠️ | Se avisa de las reglas con cifra que ya se comprueban (170 kg N/ha al año en estiércoles y pendiente superior al 15 %). El **Anexo III** también genera un aviso no bloqueante si la parcela figura en zona vulnerable y cultivo y sistema coinciden exactamente con una de sus 22 filas; recuerda el ajuste por cosecha esperada. Los 6 grupos del **Anexo V** se consultan sin inventar fechas. Fuente y reproducción en [`data/nitratos_cyl`](../data/nitratos_cyl/LEEME.md) |
| 27 | **Listado oficial de zonas vulnerables** | ✅ | Los **387 municipios y 24 zonas** del Decreto 5/2020 están derivados del [Excel oficial de IDECyL](https://opendata.jcyl.es/ficheros/carto/medioambiente/sostenibilidad/coad_cyl_vulnerab_nitrat.xlsx), con códigos y [procedencia reproducible](../data/zv_cyl_fuentes/LEEME.md). Falta confirmar si hubo modificaciones posteriores y comprobar la delimitación concreta de la parcela cuando haya dudas. Sin código INE ni municipio y provincia de la **parcela** se mantiene «no lo sé»; tanto al importar del SIGPAC como al apuntarla a mano, no se copia el municipio de la explotación. **Cerrado en la ronda 36:** se ha vuelto a pedir el Excel oficial (27/09/2026) y **es byte a byte el mismo** que el que hay bajado (misma huella SHA-256, `last-modified` 19/05/2026), así que la lista de 387 municipios y 24 zonas sigue vigente. Y para que eso no se quede en una comprobación de un día, hay un guion que lo repite cuando se quiera: `scripts/comprobar_fuentes_oficiales.py` pide **todas** las fuentes oficiales otra vez y avisa de las que hayan cambiado (ver [`CATALOGOS_OFICIALES.md`](CATALOGOS_OFICIALES.md)). La delimitación concreta de una parcela se pregunta a la **capa oficial del SIGPAC** al tocar el mapa (`intersection/nitratos`), que devuelve qué parte del recinto cae dentro y **puede contestar «no lo sé»** |
| 28 | **Nombre comercial del software** | 🔒 | Lo exige el formulario de acceso al entorno de integración de CyL (`16_CastillaYLeon_formulario_acceso_entorno_integracion.docx`) |
| 29 | **Dominio y servidor** | 🔒 | Para el **CN del certificado de dominio** que pide el mismo formulario |
| 30 | **Declaración responsable firmada** | 🔒 | El formulario de CyL la pide. Un usuario de acceso por empresa |
| 31 | **Anexo IX** | 🔒 | FEGA lo pide para actuar como entidad habilitada (Caso 1 de `15_FEGA_CUE_comercial_habilitacion_casos_practicos.pdf`). Hay que recabarlo de los agricultores |

---

## 3. Lo que NO falta (para que quede claro)

Para que nadie «arregle» lo que ya está:

- Los **cálculos legales** están hechos y probados: días de espera, unidades
  fertilizantes, dosis, vigencias.
- Las **validaciones que bloquean** están hechas: producto sin número de etiqueta o
  retirado, dosis por encima, más hectáreas que la parcela, carné caducado, ITV
  caducada, falta de justificación, cosecha antes del plazo, producto no permitido en
  ecológico.
- El **aislamiento entre fincas** está probado.
- El **cuaderno en papel** sale, y sale aunque falten datos.
- El **Modo Sencillo** está hecho, con las pantallas de alta para que un agricultor nuevo
  pueda empezar de cero.
- El **dictado** entiende frases reales y no se inventa nada, **sin contratar ningún
  modelo**.
- El **contrato de diseño** (`DESIGN.md`) pasa el validador oficial con 0 errores y 0
  advertencias.
- Los **boletines de laboratorio** se guardan fuera de la base de datos, con el nombre del
  fichero decidido por el programa y no por el navegador, y la carpeta está en el
  `.gitignore`: un papel de un agricultor no puede acabar en un repositorio.
- **Los tests no escriben nada fuera de una carpeta temporal.** Ni base de datos, ni
  boletines. Se descubrió limpiando: cada ejecución de la suite dejaba boletines de verdad
  en `backend/datos/adjuntos`, y no daba ningún fallo.
- **El protocolo del IUWS está entero**: las seis direcciones probadas contra los ejemplos
  del anexo, los 19 mensajes traducidos, la lectura de respuestas y el identificador de cada
  actividad. **Y no se inventa el JSON del descriptor**: el propio FEGA avisa de que sus
  ejemplos pueden no corresponder a la v2.6.
- **La firma se comprueba de verdad**, y sin añadir ninguna librería de criptografía. Se abre el
  fichero de firma, se mira que el resumen que lleva dentro sea el del cuaderno, se rehace la
  cuenta de la firma con el certificado y se saca **de quién es** el certificado, para que una
  firma de otro agricultor no cuele. Lo que no se comprueba —la cadena de confianza, y que el
  programa no sepa leer las firmas de curva elíptica— **se dice en el resultado**, en vez de
  quedarse en un «no» que sería mentira.
- **Los informes que la app oficial tiene en «Utilidades > Ver listados»**: el cuaderno en PDF
  (completo y «de tractor») con el informe de análisis, las medidas preventivas y el informe de
  cosecha comercializada dentro, más la exportación CSV. **Ojo con no confundir esto con un
  apartado del cuaderno**: los informes son un menú de salidas, no una sección que se
  cumplimente, y por eso no ocupan una fila de la tabla del apartado 1. Estuvieron ahí por error
  hasta la ronda 13, y en su sitio faltaba Documentación.
- **El interfaz de la Junta está comprobado, no supuesto.** Se llamó y está apuntado en el
  programa qué contesta cada método y en qué dirección: los siete existen (nadie contesta que
  la dirección no exista), el certificado lo exige el servidor, y **el entorno de integración
  de FEGA —la dirección que viene por defecto— no publica los métodos**, así que la prueba de
  conexión prueba también la de la comunidad y dice cuál contesta. Y una que se encontró con un
  test: **el interfaz contesta `200` aunque el resultado sea un error**, así que hay que leer el
  cuerpo y no el estado.

---

## 2 bis. Lo que el Anexo II pide y este programa no recoge (y por qué)

Esto se revisó **el 14 de la ronda 14, leyendo el Anexo II del documento técnico de SIEX campo
por campo** en vez de fiarse del índice. El programa vuelca el contenido mínimo **por los veinte
apartados de la app de Castilla y León**, que es lo que hay que cumplir aquí. Del Anexo II hay
tres cosas que **no** recogía, y se dicen en voz alta porque callarlas sería lo mismo que el error
de «Utilidades» de la ronda 13:

> **Actualización (ronda 23):** el bloque de la **evaluación del tratamiento** ya no está en esta
> lista. El descriptor oficial dice que el interfaz exige `Eficacia` como campo **obligatorio**,
> así que ahora el cuaderno **pregunta cómo de bien funcionó**, con cuatro respuestas llanas
> («muy bien», «bien», «regular», «mal») que son **nuestras**, no del catálogo oficial. Lo que
> sigue pendiente es el catálogo y la equivalencia entre esas cuatro respuestas y sus códigos:
> eso lo tiene que dar FEGA, y no se supone. Ver [`INTEGRACION_IUWS.md`](INTEGRACION_IUWS.md).

> **Actualización (ronda 24 del proyecto, ronda 6 del cierre del anexo II):** del bloque **`PlanAbonado`** faltaban dos campos obligatorios del
> anexo II y **ya se rellenan**. `CultivoPrecedente` no se pregunta: se saca del cultivo declarado
> en la campaña anterior, que el cuaderno ya guarda. `Herramienta` se pregunta con un **sí o un
> no**, porque en el descriptor oficial (`BdcSix-DS-DisenoCUE_3.11.4`, publicado por el FEGA en
> <https://www.fega.gob.es/es/siex/documentacion-tecnica-agricola-siex>) ese campo es **booleano**:
> poner una lista de programas habría sido inventarse un catálogo que no está publicado.
> Con estos dos, los campos obligatorios con fuente directa pasan de **60 a 61**
> (ver [`LO_QUE_SE_APUNTA_POR_TIERRA.md`](LO_QUE_SE_APUNTA_POR_TIERRA.md)).

| Bloque del Anexo II | Qué pide | Por qué no está |
|---|---|---|
| **2. Energía utilizada** | Fecha de inicio y fin, cultivo, tipo de energía, cantidad y unidades del consumo de energía de la explotación | **La app oficial de Castilla y León no tiene ese apartado.** Sus veinte apartados son los de la tabla de arriba y ninguno es energía. Recogerlo sería hacer un registro que la Junta de aquí no pide y que el agricultor no sabría para qué rellenar |
| **7. Cubierta del suelo** | Fecha de establecimiento, tipo de cobertura, anchura de la cubierta y anchura libre de la copa | En CyL esto se anota dentro de «Otras prácticas culturales», que es el apartado 11, y **ya se puede**: desde la ronda 14 hay un tipo «Mantenimiento de la cubierta». Lo que no se pide son las dos anchuras en metros |
| **«Evaluación del tratamiento»** (eficacia + observaciones) | Cómo de eficaz fue el tratamiento, **según catálogo** | ✅ **Resuelto lo que dependía de nosotros** (ronda 23): el cuaderno ya pregunta la eficacia. Queda **solo** el catálogo oficial y la equivalencia con sus códigos, que es lo que depende de FEGA |

Y una comprobación que salió mal y bien a la vez: el bloque de tratamientos del Anexo II tiene
**55 campos**, y el programa recoge 22. Eso **no es un fallo**: los 55 son el registro completo de
un tratamiento fitosanitario y los 22 son los del **contenido mínimo** (Anexo II), que es lo que
la norma obliga. Los otros 33 son datos de maquinaria, potencia, repeticiones y cataloguillos que
la app de CyL tampoco pide.

---

## 4. Plan por rondas

Ordenado por lo que **desbloquea** a lo demás, no por lo que es más divertido.

| Ronda | Qué | Por qué en este orden |
|---|---|---|
| 1 | ✅ **Autenticación con certificado** | Hecho. Es la puerta: sin ella no se puede ni entrar al entorno de integración |
| 2 | ✅ **Firma del cuaderno** | Hecho, y desde la ronda 12 **comprobada**: se abre el fichero de firma, se mira de quién es y si es de este cuaderno. Una firma de otro agricultor o de otro cuaderno se rechaza. Queda fuera la cadena de confianza (necesita la lista de autoridades raíz) y se declara |
| 3 | ✅ **Instalaciones** + clases de tratamiento | Hecho. Era la única sección imposible de cumplimentar, y de paso quedan distinguidas la semilla tratada y la postcosecha |
| 4 | ✅ **Plan de abono del año** | Hecho, con la comparación con lo que se lleva echado y el aviso al pasarse |
| 5 | ✅ **Analíticas** | Hecho: modelo, endpoints, pantalla, boletín subido y enganche con el plan de abono |
| 6 | ✅ **Medidas preventivas** como registro de la explotación | Hecho: registro a nivel de finca, y **lo declarado alimenta el apunte de cada tratamiento**, que antes no se preguntaba nunca |
| 7 | ✅ **Cosecha comercializada** | Hecho: cierra la trazabilidad. Lo que de verdad sirve es el aviso de que lo vendido no cuadra con lo cosechado |
| 8 | **Semilla, dosis y lote en la siembra; volumen y origen del agua en el riego** | Completar dos secciones que hoy son a medias. El agua de riego engancha con los nitratos del análisis |
| 9 | ✅ **Conector SIGPAC** | Hecho: se le da la referencia del recinto y trae la superficie oficial, la pendiente, el uso y el dibujo. Y de paso se encontró el **catálogo oficial de productos** (933), que rellena el hueco de códigos del volcado |
| 10 | ⚠️ **Exportación IUWS** | Hecho el protocolo entero, el contenido mínimo campo por campo **y ya con los códigos oficiales de producto**. **El descriptor ya está** (v3.11.4, con su esquema JSON, en `data/iuws_fuentes/`). Faltan los
**valores** del resto de catálogos, y **el alta del dominio**: el 27/09/2026 se llamó al interfaz de producción con el certificado de David puesto desde su ordenador y contestó `Dominio del certificado no registrado en el sistema`. O sea: el certificado vale y la conexión va; lo que falta es el alta. Ver [`INTEGRACION_IUWS.md`](INTEGRACION_IUWS.md) |
| 11 | **Asesor GIP** | Sección pequeña, de datos |
| 12 | ✅ **Llamar al interfaz de verdad** | Hecho: el cliente HTTP con la cabecera del certificado, el token, seguir una carga, y una prueba de conexión que **funciona hoy sin tener nada**. De paso quedó comprobado que los siete métodos existen, que el certificado lo exige el servidor, que la dirección por defecto no publica los métodos, y que **el interfaz contesta `200` aunque el resultado sea un error**. Y el 27/09/2026 se dio el paso que faltaba: **se llamó con el certificado de David desde su ordenador** (`scripts/probar_iuws_con_certificado.ps1`, que lo usa donde vive, sin exportar la clave) y el interfaz contestó `Dominio del certificado no registrado en el sistema`. **No se ha presentado nada** y no se dirá que sí |
| 13 | ✅ **Comprobar la firma de verdad** | Hecho: se abre el fichero de firma que sube el agricultor y se comprueba. Se hace **sin añadir ninguna librería de criptografía** (la cuenta de una firma RSA es una potencia modular, y eso Python lo trae). Los ficheros de prueba son firmas **de verdad**, hechas con OpenSSL, no inventadas por mí. Y queda dicho lo que no se comprueba: la cadena de confianza |
| 14 | ✅ **Documentación anexa** | Hecho… **y era el apartado que faltaba sin saberlo**. Se encontró releyendo el documento oficial, que dice: «seis secciones con veinte apartados… además de un repositorio de documentación». La tabla de arriba tenía 21 filas, pero una era «Utilidades», que **no es un apartado**: es el menú de los informes. El que faltaba era Documentación. Ahora está: carpetas, contratos, facturas, albaranes de Sigfito, ficheros fuera de la base de datos, y **se puede apuntar un papel sin subir el fichero** |
| 15 | ✅ **Las prácticas culturales que faltaban** | Hecho. Leyendo el Anexo II del CUE campo por campo se encontraron dos problemas en el apartado de «Otras prácticas culturales»: **faltaban el mantenimiento de cubierta y el pastoreo** (los dos los nombra el documento), y la lista de tipos de labor **no la ofrecía ninguna pantalla** — todo lo que no fuera sembrar, plantar, regar o coger la cosecha acababa en el cajón de «otra». Ahora se pregunta cuál y se guarda la práctica. De paso salió a la luz que hay tres bloques del Anexo II que este programa **no** recoge y la app de CyL tampoco pide (ver el apartado 3) |
| 16 | ✅ **El libro de movimientos del producto** | Hecho. La app oficial lo llama «Situación Cesta» y aquí no existía: los campos de la compra estaban en la base de datos y **no los leía ninguna pantalla**. Ahora hay ficha de compra (cuánto, en qué unidad, cuándo y a quién) y una pantalla con lo comprado, lo echado y lo que queda. Y lo más importante de esta ronda, que es lo que **no** se hace: cuando las unidades no son comparables —comprado en kilos, echado con dosis en litros— **no se resta**, porque haría falta la densidad y decir «te quedan -3 kg» sería inventarse un dato |
| 17 | ✅ **El cultivo de cada parcela** | Hecho, y **era el fallo más raro de todos**. No faltaba un dato: estaba todo y no se podía usar. La tabla `ParcelaCultivo` existía desde las primeras rondas con su endpoint, y **ninguna pantalla la usaba**; mientras tanto el cuaderno ya le decía al agricultor «a El Prado le falta decir qué cultivo tiene este año», sin darle forma de contestar. Eso es justo lo que prohíbe la regla del proyecto. Tres consecuencias, las tres arregladas: (1) ya se puede decir qué hay sembrado y ver el historial de otros años; (2) el «Cultivo» de **todos** los tratamientos y labores salía vacío y ahora se rellena solo con el de la parcela; (3) el aviso **V5** («en esa fecha no había cultivo») **no podía saltar nunca** porque dependía de este dato. Un aviso que no puede saltar es un aviso que no existe |
| 18 | ✅ **Las parcelas que se llevan igual** | Hecho. Tercera vez que aparecía el mismo fallo y por eso se cuenta: el apartado existía en el programa **y no tenía puerta**. `GrupoParcelas` con sus tres endpoints y `grupo_id` sin aparecer ni una vez en el JavaScript. Ahora se pueden juntar a mano y con el botón automático, se ven en su pantalla, y al apuntar un tratamiento un abono o una labor **salen los grupos** para hacerlo en una sola vez (que es lo que dice el documento oficial: «tienen como fin facilitar la cumplimentación del Cuaderno»). Y de paso se cerró el agujero de la superficie: en un grupo **no se comprobaba**, y ahora se comprueba contra la suma de todas sus parcelas |
| 19 | ✅ **Cómo se echó el producto** | Hecho. Se encontró **comparando cada columna de cada tabla con los esquemas de salida y con el JavaScript**, en vez de mirando pantalla por pantalla: once campos del registro de tratamientos **se guardaban y no salían en ninguna respuesta**, así que ninguna pantalla podía enseñarlos ni rellenarlos. Dos los pide el contenido mínimo por su número (la hora y el estado de la planta) y el resto son las condiciones de la aplicación. Ahora hay pantalla —opcional, una sola, se salta con un toque—, los campos vuelven en la respuesta, la hora llega al volcado y el estado de la planta **ya está declarado** en el bloque de tratamientos (antes ni se nombraba). Y se arregló el aviso V11, que **saltaba siempre** porque la pregunta no existía |
| 20 | ✅ **La autorización del producto** | Hecho. Cuarta vez que aparece el mismo fallo, y esta vez eran **tres comprobaciones de golpe que no podían saltar nunca**. El programa ya tenía escrito y probado que un producto retirado no se puede usar, que uno que no vale para ecológico no se puede echar en una finca ecológica, y que **una autorización excepcional caducada bloquea** — y las tres dependían de datos que no se podían meter desde ninguna pantalla, así que decía «adelante» en los tres casos. Ahora se piden (¿está autorizado?, ¿vale para ecológico?, el nº del permiso especial y hasta cuándo), las tres comprobaciones funcionan y **avisan**, que es lo que de verdad hace falta: se avisa con mes y medio de que el permiso se acaba, y si ya acabó se dice que el programa no dejará usarlo. Lo de la autorización excepcional es lo más delicado: es el permiso temporal para un producto que no está autorizado con carácter general, y usarlo después de que caduque es una infracción |
| 21 | ✅ **La forma de la parcela** | Hecho. El SIGPAC devuelve el polígono de cada recinto desde la ronda 10 y hasta la 20 **no se veía en ninguna parte**: se guardaba en la base de datos y ahí se quedaba. Ahora se dibuja en la lista de parcelas, con las tres partes de la referencia por separado (polígono, parcela y recinto, como en el papel del SIGPAC). Se dibuja **en SVG, sin librería de mapas**: un mapa de verdad pesa megas y necesita cobertura, y lo que hace falta aquí es reconocer la tierra de un vistazo. Y se corrige por la latitud, porque un grado de longitud no mide lo mismo que uno de latitud: sin eso la parcela saldría un tercio más ancha de lo que es. Si no hay forma (parcela apuntada a mano), **no se dibuja nada**: un cuadro inventado parecería su parcela |
| 22 | **Prueba con tres agricultores reales** | **No es la última: es la que decide.** Debería ir antes que varias de arriba, pero necesita a David y a gente de verdad |

> **Nota sobre el orden.** Las rondas 1, 2 y 3 desbloqueaban todo lo demás y ya están. Las
> rondas 6 a 8 son secciones independientes entre sí, así que se pueden hacer en cualquier
> orden. La ronda de la prueba con agricultores no es código y **es la más importante**: si un
> agricultor no lo usa, lo demás da igual.
>
> **Rondas sueltas, ya hechas, que no están en esa tabla:** la **23** cerró la evaluación del
> tratamiento (la eficacia), la **24** los dos campos que faltaban del plan de abonado (el cultivo
> del año anterior y si se usó una herramienta), y la **25** que el agricultor pueda **traer sus
> tierras del cuaderno de la propia Junta** en vez de teclearlas — 54 líneas y 51 tierras
> distintas en el cuaderno real de 2026, con su referencia del SIGPAC, su cultivo y sus hectáreas.
> Lo cuenta entero [`CUADERNO_DE_LA_JUNTA.md`](CUADERNO_DE_LA_JUNTA.md).
>
> Y la **26**, las **facturas de compra**: el agricultor le hace una foto al papel (o sube el PDF del
> proveedor), el programa **lee lo que pone** —proveedor, NIF, número, fecha, totales y cada línea con
> su producto, cantidad y precio—, se lo enseña **para que lo confirme o lo corrija**, y lo guarda
> como justificante. Con eso se puede contestar a las casillas del cuaderno que hasta ahora salían
> vacías: la **«empresa suministradora» y el «nº de factura» de la hoja 9.1**, y el **«nº de albarán»
> de la hoja 6**. Y de paso se sabe **cuánto producto se ha comprado**, para cuadrarlo con lo echado.
> Lo cuenta entero [`FACTURAS.md`](FACTURAS.md).

---

## 5. Lo que hay que pedirle a David

Nada de esto lo puede resolver un agente:

1. **El nombre comercial del software.** Lo exige el formulario de CyL.
2. **El dominio y el servidor** donde va a vivir esto, para el certificado de dominio.
3. **El certificado de persona jurídica** (o saber si se va a usar uno de representante).
   Tiene que ser de tipo **sello de entidad**, con el CN = dominio y el `serialNumber` = NIF, y
   con la casilla de **autenticación de cliente** marcada.
4. **El fichero oficial de zonas vulnerables** de Castilla y León.
5. **La Orden MAV/398/2022**, para cargar los límites de nitrógeno.
6. **Los tres agricultores** que hacen la prueba del apartado 5.18.
7. **Confirmar el periodo de conservación** del cuaderno.
8. **El alta en el entorno de integración**: hay que mandar el formulario de solicitud a
   `soporte-integracioncue@fega.es` y `comercialcuecyl@jcyl.es`, firmado electrónicamente.

Y de FEGA o del organismo pagador, que no depende de David pero bloquea lo mismo:

9. ~~**El descriptor `BdcSix-DS-DiseñoCUE.xlsx` v2.6.0.**~~ **Conseguido**: está en
   `data/iuws_fuentes/` (v3.11.4, con su esquema JSON). Era lo que decía los nombres exactos de
   campo del JSON. Ver [`INTEGRACION_IUWS.md`](INTEGRACION_IUWS.md).
10. **Los valores de los catálogos oficiales.** El descriptor dice **40 catálogos** y de qué
    campo sale cada uno, y SIEX publica sin certificado sus **287** tablas. Cruzando los nombres,
    **15 de esos 40 ya tienen tabla localizada** (con su identificador, y las 15 son públicas);
    los otros 25 **no se emparejan por parecido** y hay que preguntarlos. Lo que falta en todo
    caso son **los datos** de cada tabla, que están detrás de un captcha. Los códigos no se
    inventan.

---

## 6. Aviso

⚠️ Documento técnico-informativo, **no asesoramiento jurídico**. Las obligaciones hay que
confirmarlas con la oficina agraria de la zona o con un asesor. Lo que aquí está marcado
como pendiente de confirmar **no se ha metido en el código a base de suposiciones**: se
ha dejado fuera y se dice que falta.


