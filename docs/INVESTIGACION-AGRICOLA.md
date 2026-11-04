# Investigación agrícola — qué exige la JCYL, qué permiten sus APIs y cómo lo resuelven los demás

> **Para qué es este documento.** David cambió el rumbo el 2026-11-04: el producto pasa a ser **la
> herramienta digital del agricultor de Castilla y León** (cuaderno de campo, PAC y subvenciones,
> parcelas del SIGPAC). Antes de implementar nada hay que saber **qué exige la administración**, **qué
> permiten sus servicios** y **qué hacen los que ya están en el mercado**. Esto es esa investigación.
>
> **Método, y no es un detalle.** Cuatro líneas de trabajo independientes (SIGPAC, PAC/subvenciones,
> cuaderno digital, competencia) y una regla para todas: **cada afirmación lleva URL oficial, fecha de
> consulta y qué está verificado**. Lo que no se ha podido comprobar se marca **PENDIENTE** y **no se
> rellena** con «lo típico». La fecha de consulta de todo lo verificado aquí es **2026-11-04** salvo
> que se diga otra.
>
> **Lo que ya sabía el proyecto.** Este repositorio llevaba meses documentando el SIGPAC, el Cuecyl y
> el IUWS (`docs/SERVICIOS_DEL_SIGPAC.md`, `docs/CUADERNO_DE_LA_JUNTA.md`,
> `docs/INTEGRACION_IUWS.md`). Esa documentación **se ha vuelto a comprobar hoy** contra las fuentes
> oficiales: lo que sigue valiendo se dice, y lo que ha cambiado o estaba mal contado se corrige.
> El apartado 8 lo resume.
>
> **Lo que este documento NO es**: ni código, ni el plan de pantallas (eso está en
> [`ARQUITECTURA-DE-PANTALLAS.md`](ARQUITECTURA-DE-PANTALLAS.md)), ni una promesa de que todo se pueda
> automatizar. Al contrario: la conclusión principal es que **la administración no ofrece una API para
> presentar la PAC**.

---

## 0 · Los seis hallazgos que cambian el plan

1. **El SIGPAC sí se puede traer entero y en bloque**: el FEGA publica **GeoPackage por provincia** de
   la campaña actual y la anterior, **gratis y sin registro**, con licencia **CC BY 4.0** que permite
   **uso comercial**. No hace falta depender del visor ni de la consulta punto a punto para el alta
   masiva. *(Verificado en la página oficial de descargas, 04/11/2026.)*
2. **Castilla y León publica su propio SIGPAC en SHP, pero su metadato prohíbe la explotación
   comercial**, y su WMS/WFS va una campaña por detrás (llega a 2025). La vía segura para un producto
   que se vende es **el GeoPackage del FEGA**, no el FTP de la Junta, hasta que el CIT responda por
   escrito qué licencia aplica.
3. **La PAC no se «sube» como fichero**: se cumplimenta y se firma **en la aplicación de la Junta con
   certificado** (`ayg.jcyl.es`). **No se ha localizado API pública de presentación.** Lo nuestro es
   **preparar el paquete**: superficies por recinto, cultivo, región, lo que falta y documentación, y
   enlazar al trámite. Prometer «presentar la PAC desde aquí» sería mentir.
4. **El cuaderno digital tiene norma, y el mínimo del tratamiento son 11 datos** (anexo III, parte
   I.B, del RD 1311/2012). Para apuntar «en 30 segundos» hay que pedir **8** (los otros 3 se pueden
   completar al cerrar el día sin invalidar el apunte). Y **la fertilización exige más de lo que hoy
   guarda el programa** (N orgánico/ureico/nítrico/amoniacal, P2O5 soluble, agua de riego por
   hectárea).
5. **Los catálogos oficiales están a medias**: SIEX publica la **estructura** de 298 catálogos (144
   visibles) **sin los valores**; REGFIWEB permite consultar productos fitosanitarios pero **no tiene
   API ni descarga masiva localizada**. Dónde no hay catálogo oficial, se usa uno propio y se marca lo
   que no consta; nunca un código inventado.
6. **El hueco de mercado es la PAC**: ninguno de los siete productos comparados declara preparar la
   solicitud; llegan al SIEX (cuaderno) o importan la declaración. Y el alta de parcela de casi todos
   empieza por un fichero o por dibujar, no por «mis parcelas del SIGPAC».

---

## 1 · SIGPAC: qué hay, qué formato y con qué licencia

### 1.1 Qué es una parcela y qué es un recinto

| Afirmación | Fuente oficial | Fecha | Estado |
|---|---|---|---|
| **Parcela SIGPAC** = superficie continua de terreno con una referencia alfanumérica; su delimitación es la catastral salvo modificaciones no registradas | Reglamento Delegado (UE) 2022/1172, art. 2.2, transcrito en el RD 1047/2022 (<https://www.boe.es/eli/es/rd/2022/12/27/1047/con>) | 04/11/2026 | **VERIFICADO** (texto leído) |
| **Recinto SIGPAC** = cada una de las parcelas de referencia que componen la parcela SIGPAC | mismo artículo | 04/11/2026 | **VERIFICADO** |

Para la aplicación: el agricultor reconoce «su parcela» (la referencia), y la aplicación trabaja con
**recintos** (cada trozo). Es la diferencia que hace que un dedo en una linde sea otra parcela.

### 1.2 La descarga masiva (el hallazgo operativo)

| Afirmación | Fuente oficial | Fecha | Estado |
|---|---|---|---|
| Descarga masiva oficial: **GeoPackage (`.gpkg` dentro de ZIP) por provincia**, campaña actual y anterior, gratis y sin registro | <https://sigpac-hubcloud.es/html/sdsigpac/descServicio.html> | 04/11/2026 | **VERIFICADO** (comprobado también por el Lead) |
| Fichero real de Salamanca 2026: **628 MB**, nombre `37_SALAMANCA_rec_2026_20251215_gpkg.zip` | <https://sigpac-hubcloud.es/geopackages/2026/recintos/> | 04/11/2026 | **VERIFICADO** (listado del servidor) |
| Proyección ETRS89 (península y Baleares) y REGCAN95 (Canarias) | misma página | 04/11/2026 | **VERIFICADO** |
| **No hay KML ni WFS nacional en el FEGA**; la descarga oficial es GeoPackage y las consultas devuelven JSON/GeoJSON | misma página; `https://sigpac-hubcloud.es/wfs` da 404 | 04/11/2026 | **VERIFICADO** (ausencia probada) |
| Los ficheros llevan en el nombre la **fecha de vigencia** (`AAAAMMDD`), y se actualizan por campaña | misma página | 04/11/2026 | **VERIFICADO** |

**Consecuencia**: para «mis parcelas» se puede descargar la provincia entera una vez por campaña y
guardarla en el servidor, en vez de hacer una llamada por cada punto. El peso es grande (628 MB en
Salamanca) pero es **un fichero por provincia y campaña**, no por agricultor.

### 1.3 Los atributos del recinto (y los coeficientes)

| Campo (nombre oficial) | Qué es | Estado |
|---|---|---|
| `PROVINCIA`, `MUNICIPIO`, `AGREGADO`, `ZONA`, `POLIGONO`, `PARCELA`, `RECINTO` | La identidad del recinto; los siete códigos que usan las consultas | **VERIFICADO** en el modelo de datos oficial |
| `DN_SURFACE` | Superficie del recinto en m² | **VERIFICADO** |
| `PENDIENTE_MEDIA`, `ALTITUD` | Pendiente media (tanto por mil) y altitud | **VERIFICADO** |
| **`CSP`** | «Coeficiente de subvencionabilidad en pastos», 0–100 o **nulo** | **VERIFICADO** |
| **`COEF_REGADIO`** | Coeficiente de regadío, 0–100 (tierras arables) | **VERIFICADO** |
| `USO_SIGPAC`, `INCIDENCIAS`, `REGION` | Uso del suelo, incidencias y **región de la PAC** | **VERIFICADO** |
| `admisibilidad` (en la consulta REST) | Es el **CSP**: «porcentaje de admisibilidad de aplicación en los recintos de pastos». **Nulo = no aplica/no consta; nunca 0** | **VERIFICADO** (<https://sigpac-hubcloud.es/html/csp/consultas/codigoSigPac.html>) |

> **Corrección al programa**: hoy `Recinto.admisibilidad` está tipado como `object` y sin documentar.
> Debe ser `float | None` con el nombre y el significado oficiales (CSP), y **guardarse** el
> `coef_regadio`, el `region` y el `uso` que la descarga ya trae y hoy no se persisten.

Modelo de datos del recinto en la descarga: <https://sigpac-hubcloud.es/html/sdsigpac/modelos/recintos-SIGPAC.html>.

### 1.4 Los servicios en línea (lo que ya usaba el programa)

| Servicio | Dirección | Estado |
|---|---|---|
| **11 consultas REST** (JSON y GeoJSON, gzip, sin clave): recinto por códigos, por coordenadas, centroide, referencia catastral, recintos de una parcela e intersecciones (nitratos, Red Natura, montanera, fitosanitarios, pastos) | `https://sigpac-hubcloud.es/servicioconsultassigpac/…` (catálogo: <https://sigpac-hubcloud.es/html/csp/descServicio.html>) | **VERIFICADO** (llamada 200 y gzip) |
| El recinto de ejemplo `37/70/0/0/503/51/1` | <https://sigpac-hubcloud.es/servicioconsultassigpac/query/recinfo/37/70/0/0/503/51/1.json> | **VERIFICADO**: 4,9016 ha, uso TA, pendiente 1, altitud 837, `coef_regadio` 0 — **idéntico** a lo guardado el 24/09 |
| **WMS 1.3.0** con capas `recinto`, `cultivo_declarado`, `e_paisaje` (imagen PNG/JPEG) | <https://sigpac-hubcloud.es/wms?service=WMS&version=1.3.0&request=GetMap&layers=recinto&…> | **VERIFICADO** (200, imagen) |
| **OGC API Features**, colección `recintos`, **acepta `bbox`** | <https://sigpac-hubcloud.es/ogcapi/collections/recintos/items?bbox=-5.560,40.905,-5.550,40.910&limit=1&f=json> | **VERIFICADO** (200, 1 feature) |
| Listas de códigos: **34 usos**, **933 productos**, **20 regiones** | `https://sigpac-hubcloud.es/codigossigpac/cod_uso_sigpac.json`, `cod_producto.json`, `cod_region_2023.json` | **VERIFICADO** (contado hoy) |

La ortofoto que hace de fondo es del **IGN (PNOA)** y su licencia para un producto que se vende
**está pendiente de confirmar** (no se ha localizado hoy la página de condiciones).

### 1.5 Licencia: la buena y la que hay que preguntar

| Afirmación | Fuente oficial | Estado |
|---|---|---|
| Los recintos del SIGPAC del FEGA son **CC BY 4.0**: permiten **uso comercial**, copia, redistribución y caché | Página de descargas y <https://www.fega.gob.es/orig/pdfs/Terminos_de_uso_de_informacion_de_alto_valor_del_SIGC.pdf> | **VERIFICADO** (la página de descargas lo dice literalmente; el PDF lo leyó el investigador) |
| Condiciones: citar «**Fuente de los datos: FONDO ESPAÑOL DE GARANTÍA AGRARIA O.A.**», indicar si hay cambios y la fecha de última actualización | mismo PDF | **VERIFICADO** |
| Al distribuir la capa **RECINTO** hay que citar además a la **Dirección General del Catastro** (CCAA de régimen común) | Acuerdo de distribución del SIGC, nota 5 (<https://www.fega.gob.es/orig/pdfs/240801_MESA_SGC_Acuerdo_Distribucion_Datos_SIGC_fdo.pdf>) | **VERIFICADO** |
| Capas **no HVD** (campañas de hace más de 2 años y otras capas): solo se pueden redistribuir/comercializar **si se transforman** en un producto de valor añadido; **cambiar de formato no es transformar** | mismo Acuerdo, punto séptimo | **VERIFICADO** |
| **CyL**: el FTP 2026 publica SHP por provincia y municipio (POLFE/PARFE/RECFE), pero su metadato dice «**queda prohibida su explotación comercial**» | <http://ftp.itacyl.es/cartografia/05_SIGPAC/2026_ETRS89/> y `Metadados26_SHP_SIGPAC.txt` | **VERIFICADO** |
| **CyL**: WMS/WFS propio de IDECyL con capas `spac_recinto_17`…`spac_recinto_25`; la última es **2025**, no hay 2026; la URL WMS publicada (`/geoserver/lc/wms`) da **404**, funcionan `/geoserver/agricultura/wms` y `/geoserver/wms` | <https://cartografia.jcyl.es/web/es/datos-servicios/sigpac.html> y <https://idecyl.jcyl.es/geoserver/agricultura/wfs> | **VERIFICADO** |
| Qué licencia (IGCYL-C comercial o IGCYL-NC) ampara el SHP SIGPAC de CyL | <https://cartografia.jcyl.es/web/es/documentacion-cartografica/condiciones.html> | **PENDIENTE**: hay que preguntar al CIT (`cit@jcyl.es`) **por escrito** |

**Decisión mientras tanto**: se usa **el GeoPackage del FEGA (CC BY 4.0, uso comercial explícito)** y
se cita al FEGA (y al Catastro al distribuir recintos). El SHP de la Junta **no** se usa en el
producto hasta que el CIT conteste, y sus WMS sí se pueden usar solo como **visualización**.

### 1.6 Qué se puede implementar ya (SIGPAC)

1. **Alta de parcela por punto y por códigos**, referencia catastral, recintos de una parcela e
   intersecciones: todo verificado hoy, sin autenticación. El conector actual (`app/sigpac.py`) está
   alineado con el servicio.
2. **Caché provincial offline** con el GeoPackage del FEGA y refresco por campaña.
3. **Guardar** `uso_sigpac`, `coef_regadio`, `region` y `admisibilidad` (CSP, nulo = no consta).
4. **Mostrar** recintos de CyL por el WMS/WFS de IDECyL solo como visualización, mientras no haya
   licencia.
5. **Las listas de códigos** (usos, productos, regiones) ya descargables.

---

## 2 · PAC: qué se puede preparar y qué no se puede presentar

### 2.1 La vía oficial (lo que cambia el diseño)

| Afirmación | Fuente oficial | Fecha | Estado |
|---|---|---|---|
| La solicitud PAC se **cumplimenta en la aplicación de la Junta** (`ayg.jcyl.es` / `particulares.ayg.jcyl.es`) y **se firma con certificado digital**; las entidades colaboradoras tienen su versión | <https://pac.jcyl.es/web/jcyl/PAC/es/Plantilla100/1284156391976/_/_/_?rendermode=previewnoinsite> | 04/11/2026 | **VERIFICADO** |
| Presentación **electrónica preferente**; presencial solo para personas físicas sin medios acreditados; dirigida al Director General de PAC | Sede de Castilla y León | 04/11/2026 | **VERIFICADO** |
| **No se ha localizado API pública de presentación** de la PAC; la única vía documentada es app + certificado (o entidad colaboradora) | Sede y `pac.jcyl.es` | 04/11/2026 | **VERIFICADO que la vía es esa**; «no existe API» → **PENDIENTE** (no localizada) |

**Consecuencia para el producto**: se prepara el paquete y se enlaza al trámite; **no se presenta y no
se firma desde aquí**. El botón que dice «Presentar» sería una mentira y no se pone.

### 2.2 La convocatoria 2026, que ya está cerrada

| Afirmación | Fuente oficial | Fecha | Estado |
|---|---|---|---|
| Convocatoria PAC 2026: **Orden 27/01/2026**, extracto en BOCYL 30/01/2026 (BDNS 880793) | <https://bocyl.jcyl.es/html/2026/01/30/html/BOCYL-D-30012026-20-4.do> | 04/11/2026 | **VERIFICADO** |
| Plazo inicial: **1 de febrero a 30 de abril de 2026**; modificaciones hasta el 31 de mayo | BOCYL 30/01/2026 | 04/11/2026 | **VERIFICADO** |
| **Ampliado hasta el 15 de mayo de 2026** (+15 días) por Orden 17/04/2026, BOCYL 22/04/2026 | <https://bocyl.jcyl.es/boletines/2026/04/22/xml/BOCYL-D-22042026-76-13.xml> | 04/11/2026 | **VERIFICADO** |
| Contenido: ayuda básica a la renta (ABRS), redistributiva, complementaria para jóvenes, **eco-régimenes** y ayudas asociadas (proteínas, arroz, remolacha, tomate, frutos secos, uva pasa, algodón, olivar, vacuno, ovino/caprino, leche) + desarrollo rural | Sede (Pagos directos 2026) | 04/11/2026 | **VERIFICADO** |
| Documentación: **solicitud única** conforme al anexo 1 de la Orden, firmada por el productor o representante; se puede autorizar a una entidad para la firma (habilitación previa, Orden AYG/1447/2010) | Sede | 04/11/2026 | **VERIFICADO** |
| Formularios y anexos: DP-1, DP-2D/S, DP-3, CDSU-1/2, S-0, S-X, GP, AP, GE, G0, OC, PA, RP, VA, AB-1/3/4 y anexos 2 a 28 y ZL | <https://pac.jcyl.es/web/jcyl/PAC/es/Plantilla100/1284156577990/_/_/_?rendermode=previewnoinsite> y <…1284156578308…> | 04/11/2026 | **VERIFICADO** |
| La app permite rellenar formularios/anexos, digitalizarlos, adjuntar documentación y **genera el formulario MP-SIGPAC**; la modificación del SIGPAC es un trámite hermano | <https://pac.jcyl.es/web/jcyl/PAC/es/Plantilla100/1284159549701/_/_/_?rendermode=previewnoinsite> | 04/11/2026 | **VERIFICADO** |
| La ayuda **redistributiva** se concede «diferenciado en función de la región donde esté ubicada la explotación»; el SIGPAC devuelve `region` por recinto | <https://pac.jcyl.es/web/jcyl/PAC/es/Plantilla100/1284705712804/_/_/_?rendermode=previewnoinsite> | 04/11/2026 | **VERIFICADO** (el dato existe; **lista de regiones e importes → PENDIENTE**) |
| Las solicitudes no resueltas antes del **01/07/2027** se consideran denegadas | Sede (Pagos directos 2026) | 04/11/2026 | **VERIFICADO** |
| Marco estatal: **RD 1048/2022** regula los pagos directos y la solicitud única | <https://www.boe.es/buscar/act.php?id=BOE-A-2022-23048> | 04/11/2026 | **VERIFICADO** |
| **PAC 2027**: convocatoria y fechas | — | 04/11/2026 | **PENDIENTE** (no publicada) |

### 2.3 Lo que el programa ya tiene y lo que le falta

**Ya está** (`app/pac.py`, `app/routers/pac_api.py`, `backend/web/app.js`): el paquete PAC, el escenario
del año siguiente con huella, la «foto» de la PAC, el historial y la exportación CSV. Y la regla
correcta, escrita: **preparar no es declarar** (`pac.py:45-94`).

**Y el hueco principal, que es de datos**: la fuente legal está vacía —
`pac_api.py:171-176` llama a `la_que_aplica([])`, así que `la_fuente` sale `null` y el aviso dice «sin
fuente no se puede decir si algo es elegible». Eso es honesto y es lo que hay que arreglar cargando la
Orden de convocatoria como fuente versionada con vigencia.

**Falta, por orden de importancia**:
1. Cargar la convocatoria (2026 y la 2027 cuando salga) con su vigencia.
2. **Regiones de CyL** (asignación por recinto e importes) — el SIGPAC ya devuelve `region` y
   `admisibilidad`, pero **no se guardan** en la parcela (`sigpac.py:536,541,610,615`).
3. Datos que la solicitud pide y no existen: derechos de ayuda básica (nº y ha), pastos permanentes y
   barbecho, eco-régiMenes con **código de práctica** (hoy texto libre), UGM/ganado, condición de
   joven, titularidad (propiedad/arrendamiento), ingresos y CNAE-IAE, régimen de tenencia.
4. Guardar la **solicitud presentada** (transcripción) para comparar años; no hay tabla.
5. Generar el **paquete para presentar** por recinto (referencia, superficie SIGPAC frente a
   cultivada, cultivo, práctica, región, importe estimado y lo que falta) + anexos/documentación.
6. Enlazar al **trámite exacto** de la sede, no a un portal genérico (`textos.py:5789-5791` apunta hoy
   a un portal genérico).

---

## 3 · Subvenciones de Castilla y León

| Afirmación | Fuente oficial | Fecha | Estado |
|---|---|---|---|
| Subvención **agroambiental/climática, ecológica y razas autóctonas 2026**: Orden 20/02/2026, BOCYL 25/02/2026 (BDNS 882952); compromisos de 3 años (2026–2028); 8.000.000 €; plazo = el de la solicitud única 2026 | <https://bocyl.jcyl.es/html/2026/02/25/html/BOCYL-D-25022026-38-15.do> | 04/11/2026 | **VERIFICADO** |
| **Viñedo 2026**: Orden 24/03/2026, BOCYL 27/03/2026 (BDNS 895148); plazo hasta el **27/04/2026 19:00**; bases del RD 905/2022 | <https://bocyl.jcyl.es/boletines/2026/03/27/xml/BOCYL-D-27032026-60-7.xml> | 04/11/2026 | **VERIFICADO** |
| Documentación y justificación específica de cada subvención | — | 04/11/2026 | **PENDIENTE** (no revisada más allá de los extractos) |
| Próximas convocatorias (2027 en adelante) | — | 04/11/2026 | **PENDIENTE** |

**Lo que significa**: a día de hoy **no hay ninguna convocatoria abierta** de las verificadas (las dos
de 2026 están cerradas). El producto no puede prometer «te aviso de las subvenciones» si no hay un
calendario publicado estable; lo que sí puede hacer es **guardar las convocatorias verificadas con su
fuente y su plazo** y avisar cuando haya una nueva en BOCYL.

---

## 4 · Cuaderno digital (CUE / Cuecyl)

### 4.1 La norma, y una corrección al programa

| Afirmación | Fuente oficial | Fecha | Estado |
|---|---|---|---|
| **RD 1054/2022**: el art. 9 obliga a llevar cuaderno cuando lo pida la normativa sectorial; el **art. 10.2 hace voluntario el envío** a la administración; el art. 10.3 permite un **cuaderno comercial** | <https://www.boe.es/buscar/act.php?id=BOE-A-2022-23054> | 04/11/2026 | **VERIFICADO** |
| **Corrección**: el «contenido mínimo» del **anexo II** del RD 1054/2022 son **4 apartados** (datos generales de la DGC; tratamientos según el anexo III del RD 1311/2012; fertilización según la normativa sectorial; otros). **No es una lista de campos.** El detalle campo a campo está en el **anexo III del RD 1311/2012** y en el **descriptor CUE** | mismo BOE (PDF oficial, 21 pp.) | 04/11/2026 | **VERIFICADO** |
| **RD 1311/2012, art. 16.1**: registro de tratamientos con la **parte I del anexo III**; **papel hasta el 31/12/2026**; **plazo de volcado: 1 mes**; art. 16.3: **conservar 3 años** | <https://www.boe.es/buscar/pdf/2012/BOE-A-2012-11605-consolidado.pdf> (últ. mod. 20/11/2025) | 04/11/2026 | **VERIFICADO** |
| **Anexo III, parte I.B** = los **11 datos obligatorios de un tratamiento** (a–k): fecha; parcela; plaga; aplicador (y asesor); cultivo con especie y variedad; superficie tratada; producto con nombre comercial y nº de registro; máquina; kg o litros; eficacia; observaciones | mismo PDF, pp. 36–39 | 04/11/2026 | **VERIFICADO** |
| **Anexo III, parte I.C** = registro de **fertilización** (a–l): tipo (enmienda/fondo/cobertera), material, valor agronómico (N total, orgánico, ureico, nítrico, amoniacal, P2O5 total y soluble, K2O), dosis, empresa suministradora (REGA/NIF/NIMA), REGFER, agua de riego | mismo PDF, p. 39 | 04/11/2026 | **VERIFICADO** |
| **RD 1051/2022, art. 4.2**: **plan de abonado obligatorio desde el 01/09/2026** (regadío sembrado del 1/3 al 30/6/2026: desde el 01/01/2026), con umbrales de exención (p. ej. ≤10 ha de secano) | <https://www.boe.es/buscar/pdf/2022/BOE-A-2022-23052-consolidado.pdf> | 04/11/2026 | **VERIFICADO** |
| **Corrección**: los efectos del RD 1051/2022 los fija la **disposición final novena** (no «final única»), y su **anexo I remite al anexo III del RD 1311/2012** | mismo PDF | 04/11/2026 | **VERIFICADO** |

### 4.2 El Cuecyl (el cuaderno de la Junta) y lo que exige

| Afirmación | Fuente oficial | Fecha | Estado |
|---|---|---|---|
| El Cuecyl es una aplicación de la Junta, con «**seis secciones con veinte apartados**»; «es decisión de los agricultores utilizar este cuaderno **o bien un cuaderno digital comercial**»; acceso con certificado, DNIe o **CPI** | <https://agriculturaganaderia.jcyl.es/web/jcyl/binarios/198/91/Instrucciones_cumplimentaci%C3%B3n_Cuecyl_ene%202025.pdf> (30 pp.) | 04/11/2026 | **VERIFICADO** |
| Acceso: titular o entidad colaboradora en `particulares.ayg.jcyl.es` / `ayg.jcyl.es` | misma página | 04/11/2026 | **VERIFICADO** |
| **REA** en CyL = **Reacyl** (Ley 1/2014, en funcionamiento desde 2015) | <https://agriculturaganaderia.jcyl.es/web/es/registro-explotaciones-agrarias-castilla.html> | 04/11/2026 | **VERIFICADO** |
| Formato de **exportación** del Cuecyl: `.xlsx` `CuadernoExplotacion_<NIF>.xlsx`, 25 hojas (23 en 2024) | — | 04/11/2026 | **PENDIENTE como especificación oficial**: el PDF de la Junta no lo documenta; está comprobado contra 3 cuadernos reales (`docs/CUADERNO_DE_LA_JUNTA.md:31-60`) |

**Lo que ya hace el programa con el Cuecyl**: leerlo y traer sus tierras sin duplicar
(`app/cuaderno_cyl.py`), rellenarlo (10 de 25 hojas, `docs/CUADERNO_DE_LA_JUNTA.md:134-149`) y decir
qué falta (`GET /api/cuaderno-cyl/que-falta`). Lo que **no** se inventa: el sitio exacto de cada
columna que no se conoce.

### 4.3 El IUWS (el volcado oficial) — qué está abierto y qué no

| Afirmación | Fuente oficial | Fecha | Estado |
|---|---|---|---|
| **`/IUWS/api/version` contesta 200 sin certificado**: `{"version":"3.11.4"}` en producción y la misma versión en integración | <https://servicios.ayg.jcyl.es/IUWS/api/version> · <https://sga.entornointegracion.es/IUWS/api/version> | 04/11/2026 (llamado hoy) | **VERIFICADO** |
| El **token exige certificado de cliente en el TLS**: sin él no hay canal («No se puede crear un canal seguro SSL/TLS») | <https://servicios.ayg.jcyl.es/IUWS/api/comunicacion/PRUEBA> | 04/11/2026 (llamado hoy) | **VERIFICADO** |
| **Anexo VI (Interfaz Único Común) v3.11.4**, actualizado el 19/11/2025; describe los métodos de REA y CUE | <https://www.fega.gob.es/es/siex/documentacion-tecnica-agricola-siex/anexo-vi-interfaz-unico-comun-3114> | 04/11/2026 | **VERIFICADO** |
| Anexo X: dirección de CyL `https://servicios.ayg.jcyl.es/IUWS/` y alta en `comercialcuecyl@jcyl.es` | <https://www.fega.gob.es/sites/default/files/files/document/2024.05.17-ANEXO_X-ProcedimientoAutorizacionCUE_PUBLICADO.pdf> | 04/11/2026 | **VERIFICADO** |
| **Descriptor CUE v3.11.4**: 107 bloques, **402 campos, 175 obligatorios** | `data/iuws_campos_del_cuaderno.json` (hoja `EstructuraCuadernoWS`) | 04/11/2026 | **VERIFICADO** (derivado del oficial) |

**Lo que exige alta y certificado**: `crear/`, `exportar/`, `exportarREA/` y `comprobarEstado/` del
IUWS (certificado de cliente + **alta del dominio** + nombre comercial + CIF + autorización del titular
+ **código SIEX de 14 caracteres**). Presentar en el Cuecyl exige certificado/DNIe/**CPI**.

### 4.4 Catálogos oficiales: dónde están y dónde no

| Afirmación | Fuente oficial | Fecha | Estado |
|---|---|---|---|
| SIEX publica la **estructura** de sus catálogos sin certificado: el endpoint devuelve **298 catálogos (144 visibles)** con sus columnas y **ninguna fila de valores** | <https://www3.sede.fega.gob.es/bdcsixpor/tablas/configJson> (497.820 bytes) | 04/11/2026 | **VERIFICADO** |
| Existen catálogos SIEX llamados exactamente «**Tipo de labor**», «Tipo de fertilización», «Eficacia del tratamiento», «Tipo de producto fitosanitario», «Material fertilizante» y «Tratamiento semilla» | mismo endpoint | 04/11/2026 | **VERIFICADO** (el nombre; los valores no) |
| **Valores** de esos catálogos | — | 04/11/2026 | **PENDIENTE** (el repo los da por captcha, `docs/INTEGRACION_IUWS.md:276-278`; hoy no se ha intentado saltarlo) |
| **REGFIWEB** (productos fitosanitarios): consulta pública, base actualizada **30/10/2026**, semanal | <https://servicio.mapa.gob.es/regfiweb/> | 04/11/2026 | **VERIFICADO** |
| REGFIWEB con API o descarga masiva | — | 04/11/2026 | **PENDIENTE** (no encontrada) |
| **Semillas**: registro de variedades y catálogos nacional/comunitario públicos | <https://www.mapa.gob.es/es/agricultura/temas/medios-de-produccion/semillas-y-plantas-de-vivero/registro-de-variedades> · <https://servicio.mapa.gob.es/germenwai> | 04/11/2026 | **VERIFICADO** |
| **Tipos de producto fertilizante**: anexo I del RD 506/2013 o categoría funcional del Reglamento (UE) 2019/1009 | citado en el anexo III I.C.d.1 del RD 1311/2012 | 04/11/2026 | **VERIFICADO** (la remisión) |
| Registro público de fertilizantes con códigos descargables | <https://www.mapa.gob.es/es/agricultura/temas/medios-de-produccion/productos-fertilizantes/> | 04/11/2026 | **PENDIENTE** |

### 4.5 El hueco entre lo que guarda el programa y lo que exige la norma

- **Tratamientos**: está casi todo el anexo III I.B (fecha `models.py:1104`, parcela `1108`, plaga
  `1131`, aplicador `1162`, cultivo/variedad `1128-1129`, superficie `1127`, producto y nº de registro
  `1136-1137`, máquina `1163`, cantidad `1150-1151`, eficacia `1186`, observaciones `1197`). **Hueco
  real: cuatro campos son texto libre o lista propia** (plaga, justificación, eficacia, estado del
  cultivo) en vez de código de catálogo (`iuws_mapeo.py:119-124`). Y falta el **código de la DGC**,
  que afecta a 9 de los 18 bloques del volcado (`iuws_mapeo.py:201`, `docs/INTEGRACION_IUWS.md:450-452`).
- **Fertilización, hueco de verdad**: el anexo III I.C.h pide **N orgánico, ureico, nítrico y
  amoniacal** y **P2O5 soluble**; el modelo solo guarda `riqueza_n/p/k` totales (`models.py:2242-2244`).
  Y del agua de riego pide **N nítrico, P soluble y m³/ha**: hay `nitratos_agua_riego` (`2271`) y
  `Labor.volumen_agua` (`2403`), sin normalizar por hectárea.
- **Suelo** (anexo III A.3: pH, P2O5, K2O, materia orgánica): está en un **JSON** `parametros`
  (`models.py:1364`), contra la regla del proyecto de que un dato con nombre y número va en su columna.
- **Cuaderno de la Junta**: se rellenan solas **10 de 25 hojas** y **15 no** (`docs/CUADERNO_DE_LA_JUNTA.md:134-149`).
- **Volcado oficial**: de 113 campos obligatorios, **61** tienen fuente directa y tipo compatible y
  **52** esperan catálogo (`docs/INTEGRACION_IUWS.md:474-482`; lista viva en `iuws.QUE_FALTA`).

### 4.6 El mínimo de un apunte en el campo («30 segundos»)

Con la norma verificada, de los **11 datos** del tratamiento, los que **no se pueden deducir** son
**8**: fecha, parcela, plaga, aplicador, cultivo, superficie tratada, producto con su nº de registro y
cantidad. **Eficacia y observaciones se pueden completar al cerrar el día** sin invalidar el apunte.

La **fertilización** pide además: tipo (enmienda/fondo/cobertera/fertirrigación), material con su
clasificación, empresa suministradora con REGA/NIF/NIMA cuando es estiércol o purín, forma de
aplicación, valor agronómico, dosis por hectárea, empresa de servicios (REFER) y datos del agua de
riego.

**Siembras, labores, pastoreo y cosecha no están en el RD 1311/2012**: su mínimo sale del
**descriptor CUE v3.11.4** (bloques 5, 6, 3 y 7 del contenido mínimo, `app/iuws_contenido.py:76`).

---

## 5 · Tipos de producto, siembras y trabajos: qué catálogo se usa

| Pieza | Catálogo oficial | Qué se puede hacer hoy | Estado |
|---|---|---|---|
| **Productos fitosanitarios** | REGFIWEB (MAPA), actualizado 30/10/2026 | Consulta pública a mano; el programa ya tiene `ProductoFitosanitario` con nº de registro | **VERIFICADO** (existe); API/descarga **PENDIENTE** |
| **Fertilizantes** | Tipos del RD 506/2013 / Reglamento (UE) 2019/1009; registro público del MAPA | Catálogo propio con los tipos oficiales; códigos descargables **PENDIENTES** | remisión **VERIFICADA**; descarga **PENDIENTE** |
| **Semillas y variedades** | Registro de variedades del MAPA y catálogos nacional/comunitario | Se puede consultar; el programa ya tiene `Semilla` y `Siembra` | **VERIFICADO** (existe) |
| **Tipos de labor y de siembra** | Catálogos SIEX «Tipo de labor», «Tipo de fertilización» etc. (estructura publicada; valores no) | Catálogo propio **con el mismo nombre** y mapeo explícito; nunca un código inventado | **VERIFICADO** el nombre; **PENDIENTE** los valores |

**Regla que se mantiene**: donde no hay catálogo oficial, se usa uno propio, se dice que es propio y se
deja el campo vacío cuando no se sabe. Un código inventado en un volcado oficial da error meses
después, delante de un inspector.

---

## 6 · Cómo lo resuelven los que ya están en el mercado

Comparación hecha el 04/11/2026 con las páginas oficiales de cada producto (no con artículos de
terceros). **Verificado**: lo que la página oficial declara. **Opinión**: lo que se deduce de ello.

| Producto | Alta de parcela | Apunte en campo | PAC / subvenciones | Mapa | Exportar | Precio público |
|---|---|---|---|---|---|---|
| [Agroptima](https://www.agroptima.com/es/cuaderno-de-campo) | Importa Excel/Shapefile y «añade campos del SIGPAC»; importa la declaración PAC | App móvil, «anotar aunque no tengas cobertura»; base de fitosanitarios del MAPA diaria | Importa la declaración PAC; **no declara generar la solicitud** | Visor SIGPAC integrado; parcelas por cultivo | Excel e informes | **No publicado** (según hectáreas y usuarios; prueba 15 días) |
| [ISAGRI–Geofolia](https://www.isagri.es/geofolia) | «Importa tu parcelario desde el **REA**» | 4 pasos declarados: parcelario → marcar parcelas → crear parte → dosis automática | **Envía el cuaderno al SIEX** por lotes, con nº de seguimiento | No detallado | No detallado | No publicado (demo) |
| [Hispatec–Efemis](https://www.hispatec.com/productos/operaciones-en-campo/) | No detallado | Tareo con QR/NFC, «con o sin cobertura», mapas de calor | Integra con SIEX/FEGA; no prepara solicitud | Mapas de calor | No detallado | No publicado (demo) |
| [John Deere Operations Center](https://www.deere.es/es-es/productos-soluciones/soluciones-tecnologicas/tecnologia-de-agricultura-de-precision/operations-center) | «Define los límites» (sin SIGPAC) | Planificar/supervisar; app móvil/tableta/escritorio | No | Rendimiento y prescripciones | No detallado | **Gratis** |
| [Bayer FieldView](https://www.cropscience.bayer.es/productos/herramientas-digitales/fieldview) | «Dibuja o importa» tus campos (5 pasos) | Hardware *Drive* o entrada manual | No | NDVI/biomasa, prescripciones | Informes | **120 €/año** Prime; **499 €/año** Plus |
| [OneSoil](https://help.onesoil.ai/es/articles/14885036-suscripcion-de-monitoreo-movil) | Límites de campo dibujados; **exportarlos es de pago** | Notas con foto y geolocalización | No | NDVI y humedad | Solo con suscripción | Freemium por región/hectáreas |
| [Cuecyl (JCYL)](https://www.cyldigital.es/curso/aplicacion-informatica-del-cuaderno-digital-de-explotacion-de-castilla-y-leon-cuecyl-webinar) | No consta | Tratamientos, fertilizantes y labores; historial | No consta | No consta | No consta | Herramienta oficial; condiciones no verificadas |

**Dato verificado**: **Agroptima pertenece al grupo ISAGRI** (pie de su web: «© 2026 ISAGRI S.L.»), así
que dos filas son el mismo dueño.

### 6.1 Qué les falta (y es nuestro hueco)

1. **Nadie declara preparar la solicitud PAC.** Llegan al SIEX (cuaderno) o importan la declaración;
   ninguno dice calcular superficies ni generar el paquete de solicitud.
2. **El alta empieza por un fichero o por dibujar**, no por «mis parcelas del SIGPAC»: REA (ISAGRI),
   dibujar (FieldView, Deere), Excel (Agroptima). Solo Agroptima importa la PAC y cuadra códigos.
3. **Precio detrás de una llamada** en 4 de 7. El agricultor no llama para saber cuánto le cuesta.
4. **Dependencia de hardware o de empresa**: FieldView necesita el *Drive*; Deere, sus máquinas;
   Hispatec, QR/NFC pensado para cuadrillas.
5. **La app oficial es solo cuaderno**: la descripción oficial del curso de la JCYL lista anotaciones
   e historial; no menciona parcelas SIGPAC ni PAC (no prueba que no existan).
6. **Reseñas**: no se ha podido leer texto de opiniones (Capterra solo ficha; Play Store no devuelve
   texto). Única señal: App Store de Agroptima, 4,1/5 con 88 valoraciones. **No hay base para afirmar
   quejas concretas**: queda **PENDIENTE**.

### 6.2 Patrones que merece la pena copiar (10)

1. **Importar antes que dibujar**: alta desde SIGPAC/PAC, el dibujo solo como arreglo.
2. **El mapa como selector, no como pantalla aparte**: tocar el recinto y abrir su ficha encima.
3. **Un objeto canónico con ficha única**: parcela con cabecera, historial y acciones.
4. **Lista con buscador y 2–3 filtros en chips, con contador** («64 parcelas · 128,4 ha»).
5. **Un solo botón principal por pantalla**, grande y con verbo en primera persona.
6. **Apunte que funciona sin cobertura y lo dice**: «3 apuntes esperando cobertura».
7. **Producto que precarga dosis y avisa** de caducidad o de cultivo no permitido.
8. **Estado con palabra + icono** («Enviado», «Pendiente», «Rechazado»), nunca solo color.
9. **Actividad reciente en la portada** (qué, dónde, cuándo, estado).
10. **Exportar junto al título de cada lista**, no en ajustes.

### 6.3 Errores que no se repiten (7)

1. **Portada de seis botones sin la finca delante** (lo que había y David rechazó).
2. **Filtros que empujan el contenido bajo el pliegue** a 1440 px (defecto documentado en
   `docs/REVISION_PRODUCTO_2026-10-19.md:236`).
3. **Menú largo y vocabulario mezclado** (21 renglones, `docs/ARMAZON.md:92`).
4. **Pintar el fallo como vacío**: `cargarDatos` convertía errores en `[]`
   (`docs/REVISION_PRODUCTO_2026-10-19.md:241`). Son cuatro cosas distintas.
5. **Obligar a importar o dibujar antes de ver nada**.
6. **Pedir una llamada comercial para saber el precio**.
7. **Prometer plazos legales de memoria** (Agroptima seguía diciendo en 2026 que el CUE sería
   obligatorio «en 2023»).

---

## 7 · Qué significa todo esto para el producto, y qué hay que pedir

### 7.1 Se puede implementar ya (sin permiso de nadie)

- **Traer las parcelas del SIGPAC** por provincia (GeoPackage del FEGA) y elegirlas en el mapa; guardar
  sus atributos oficiales (uso, coeficiente de regadío, región, CSP).
- **Leer y exportar el Cuecyl** y **rellenar las 10 hojas** que ya se rellenan.
- **Apuntar los 8 datos mínimos** de un tratamiento y los de una labor/siembra según el descriptor.
- **Preparar el paquete PAC** (superficies, cultivo, región, lo que falta) y enlazar al trámite.
- **Guardar las convocatorias verificadas** con su fuente y su plazo.
- **Exportar** PDF/CSV/Excel de lo que hay.

### 7.2 Necesita alta y certificado (no se puede prometer hoy)

- **Volcar el cuaderno al IUWS** (`crear/`, `exportar/`): certificado de cliente + alta del dominio +
  nombre comercial + CIF + autorización del titular + código SIEX de 14 caracteres.
- **Presentar en el Cuecyl** y **presentar la PAC**: certificado/DNIe/CPI del titular; no hay API.

### 7.3 Lo que hay que preguntar, y a quién

| A quién | Qué |
|---|---|
| **CIT de la Junta** (`cit@jcyl.es`) | Qué licencia (IGCYL-C o NC) ampara el SHP SIGPAC de CyL y si se puede usar comercialmente |
| **FEGA** | Condiciones de campañas históricas (>2) y de las capas no HVD; cupos de las consultas REST (no publicados); licencia de la ortofoto PNOA es del **IGN** |
| **IGN** | Licencia de la ortofoto PNOA para un producto que se vende |
| **Junta / FEGA (CUE)** | ¿Publican la especificación del `.xlsx` del Cuecyl o hay servicio de importación? ¿El «Tipo de labor» del descriptor es el catálogo SIEX del mismo nombre? ¿Los valores de los 40 catálogos que pide el descriptor? ¿El volcado mensual del art. 16.1 aplica a cuadernos comerciales? ¿Quién asigna el identificador de DGC? ¿Hay que inscribirse como entidad habilitada CUE? |
| **Junta (PAC)** | Regiones e importes de CyL (están en la Orden y anexos en PDF); si se puede importar un fichero propio de parcelas en la app |

---

## 8 · Lo que el repositorio ya decía, y lo que hay que corregirle

**Sigue siendo cierto (comprobado hoy)**:

- Las **11 consultas** del SIGPAC y sus direcciones, el orden de los siete códigos, JSON+GeoJSON con
  gzip, las capas WMS, la OGC API con `bbox`, la licencia CC BY 4.0 y los 34 usos/933 productos
  (`docs/SERVICIOS_DEL_SIGPAC.md`).
- El recinto de ejemplo devuelve **exactamente** lo mismo que el 24/09 (4,9016 ha, uso TA, pendiente
  1, altitud 837).
- El Cuecyl: 25 hojas, 10 rellenables, y el SHA-256 del PDF oficial es el mismo que guarda el repo
  (`docs/CUADERNO_DE_LA_JUNTA.md`).
- El IUWS v3.11.4 y las direcciones de CyL; el descriptor de 107 bloques / 402 campos / 175
  obligatorios (`docs/INTEGRACION_IUWS.md`).

**Hay que corregir o completar en los documentos del repo** (tareas del `BACKLOG.md`):

1. `docs/SERVICIOS_DEL_SIGPAC.md` **no documenta la descarga masiva real** (GeoPackage por provincia):
   solo teselas MVT y consulta por caja.
2. La licencia: los documentos operativos hoy son los «Términos de uso de la información de alto valor
   del SIGC» y el «Acuerdo de distribución», que añaden la **cita al Catastro** y la regla de capas no
   HVD. La frase de que la ortofoto PNOA es «del mismo modo de acceso público» **no está verificada**.
3. Falta la **vía CyL** con su restricción comercial y el aviso de que su WMS va una campaña por
   detrás; la URL WMS publicada da 404.
4. `Recinto.admisibilidad` es `object` y sin documentar: debe ser `float | None` (CSP) y por su
   significado.
5. La atribución normativa del «contenido mínimo»: el anexo II del RD 1054/2022 son **4 apartados**,
   no 13 bloques; los bloques salen del descriptor CUE y del anexo III del RD 1311/2012.
6. Los plazos del plan de abonado los fija la **disposición final novena** del RD 1051/2022, y hay
   **exenciones** (≤10 ha de secano, pastos) que el repo no menciona.

---

## 9 · Lo que NO está verificado (y no se ha rellenado)

- **Regiones e importes de la PAC de CyL** y el **coeficiente de admisibilidad de pastos** (están en la
  Orden y anexos en PDF, no abiertos hoy).
- **Formato de importación de ficheros** en la app de la PAC (no verificado en fuente oficial).
- **Inexistencia de API** de presentación de la PAC: solo «no localizada».
- **Valores** de los catálogos SIEX (estructura sí, valores no: captcha).
- **API/descarga masiva** de REGFIWEB (no encontrada) y registro de fertilizantes (pendiente).
- **Especificación oficial** del `.xlsx` del Cuecyl (comprobado contra 3 cuadernos reales, no publicado).
- **Documentación y justificación** específica de las subvenciones, más allá de los extractos del BOCYL.
- **Convocatorias 2027** (PAC y subvenciones): no publicadas.
- **Licencia del SHP SIGPAC de CyL** y **de la ortofoto PNOA**: pendientes de respuesta.
- **Reseñas de usuarios** de las apps de competencia (texto no disponible en las fuentes usadas).
- **Pasos reales** de las apps de competencia (no hay demo pública en varios casos; los pasos citados
  son declaraciones del vendedor).

---

## 10 · Siguientes pasos ejecutables

| # | Tarea | Nivel | Qué desbloquea |
|---|---|---|---|
| 1 | **Sistema de diseño y artboards** (hecho en este paquete: `designs/`) | 2 | Que David apruebe el aspecto |
| 2 | **Armazón nuevo + Hoy + Mis parcelas** con datos reales | 2 | F2 de la arquitectura |
| 3 | **Traer parcelas del SIGPAC en lote** (GeoPackage del FEGA, caché por provincia) | 2 | F3: el producto existe |
| 4 | **Corregir los cuatro documentos** del apartado 8 (SIGPAC, licencia, `admisibilidad`, norma) | 1 | Que la documentación no mienta |
| 5 | **Apuntar en 30 s** con los 8 datos mínimos + cola sin cobertura | 2 | F4: el cuaderno de campo |
| 6 | **Paquete PAC** con superficies, región y lo que falta + enlace al trámite | 2 | F5: el hueco del mercado |
| 7 | **Escribir al CIT, al FEGA, al IGN y a la Junta** las preguntas del apartado 7.3 | 3 (depende de terceros) | Licencias y catálogos |
| 8 | **Exportar** PDF/Excel y verificar el Cuecyl de ida y vuelta | 2 | F6 |

---

*Investigación cerrada el 2026-11-04. Cada afirmación verificada lleva su fuente y su fecha; lo no
comprobado está en el apartado 9 y no se usa como argumento. La propuesta de pantallas está en
[`ARQUITECTURA-DE-PANTALLAS.md`](ARQUITECTURA-DE-PANTALLAS.md); el aspecto, en
`designs/cue-agricola-design-system/` y `designs/cue-agricola/`.*
