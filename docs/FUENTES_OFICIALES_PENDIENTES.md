# Fuentes oficiales pendientes para el volcado IUWS

Comprobación realizada el **23/09/2026**. La referencia de trabajo es el [Anexo VI, Interfaz Único Común v3.11.4](https://www.fega.gob.es/sites/default/files/files/document/2025.11.19-ANEXO%20VI.Interfaz%20%C3%9Anico%20Com%C3%BAn_V3_11_4.docx), con el descriptor Excel y el esquema JSON que lleva incrustados (copias intactas en [`data/iuws_fuentes`](../data/iuws_fuentes/LEEME.md)). En el Word se indica epígrafe y, para el Excel incrustado, hoja y fila: la paginación de Word cambia con el programa que lo abre. En los PDF se dan página y/o tabla. «No lo he encontrado» significa que no aparece en las fuentes y accesos examinados; no afirma que el organismo no lo tenga. Las respuestas sin certificado no demuestran qué ofrece un usuario dado de alta. No se ha hecho ninguna llamada autenticada ni se ha enviado ninguna consulta.

## 1. Valores de los catálogos SIEX

### Qué falta

Los **valores y códigos** de los 15 catálogos con tabla localizada por coincidencia exacta, y saber si el alta permite obtenerlos de forma documentada. El inventario local identifica tablas, nombres y columnas, no filas de valores.

### Dónde se publica

El [índice técnico SIEX de FEGA](https://www.fega.gob.es/es/siex/documentacion-tecnica-agricola-siex), actualizado el 09/09/2026, enlaza los anexos III a X; el VII lleva al [portal de catálogos SIEX](https://www3.sede.fega.gob.es/bdcsixpor/catalogos), no a un fichero de filas. Su [configuración de tablas](https://www3.sede.fega.gob.es/bdcsixpor/tablas/configJson) expone estructura. El [portal de datos abiertos FEGA](https://www.fega.gob.es/es/datos-abiertos), revisado el 23/09/2026, enumera pagos y ayudas, pero no una distribución de catálogos SIEX; las búsquedas en [datos.gob.es](https://datos.gob.es/es/catalogo/conjuntos-datos) tampoco dieron sus filas. El [registro de productos fitosanitarios del MAPA](https://servicio.mapa.gob.es/regfiweb/Productos/Index) sí permite exportar productos en Excel o JSON: el [FAQ oficial, pregunta 3](https://servicio.mapa.gob.es/es/agricultura/temas/sanidad-vegetal/faq_tcm30-618120.pdf) remite a sus informes descargables. Es un registro de productos, **no** un catálogo de códigos SIEX ni una equivalencia documentada; tampoco lo es [ROPO](https://servicio.mapa.gob.es/ropowebwai/). **URL de descarga pública de las filas SIEX: no lo he encontrado.**

### Qué dice

El índice FEGA llama al Anexo VII «Catálogos SIEX» y lo describe como listas de códigos estandarizadas (entrada *Anexo VII*). El Anexo V, hojas `REA` y `CUE`, define campos y obligatoriedad, pero no incorpora las listas de valores; el Anexo VI aporta el descriptor y el esquema. En el índice de los demás anexos no he localizado otra descarga de esas listas. No he encontrado una frase oficial que diga que el alta de integración dé acceso a ellas.

El 23/09/2026 descargué y abrí también el **contenido interno** de los otros ficheros enlazados por ese índice, en vez de limitarme a sus páginas. El [Anexo V](https://www.fega.gob.es/sites/default/files/files/document/2025.11.20-ANEXO_V_Definicion_de_variables_3.11_CORRECCION_ERRORES_PUBLICACION.xlsx) solo tiene dos hojas visibles (`REA`, 246 filas; `CUE`, 303 filas), sin hojas ocultas, objetos incrustados ni conexiones externas. El [documento técnico v3.11](https://www.fega.gob.es/sites/default/files/files/document/2025.11.14-DT%20AGRICOLA_v3.11_CORRECCION%20ERRORES_LIMPIO.pdf) tiene 60 páginas, sin adjuntos PDF; en la página 59 remite al portal para el Anexo VII. Revisé además el [Anexo III](https://www.fega.gob.es/sites/default/files/files/document/2025.11.20-ANEXO_III_CRONOLOGIA_INCORPORACION_FFII_y_FRECUENCIA.xlsx) (una hoja, 28 filas), el [Anexo IV](https://www.fega.gob.es/sites/default/files/files/document/2024.05.27-ANEXO_IV_Glosario_SIEX.xlsx) (una hoja, 196 filas), los Word de los [Anexos VIII](https://www.fega.gob.es/sites/default/files/files/document/2023.11.10-ANEXO%20VIII.%20Modelo_autorizacion_representaci%C3%B3n_PUBLICADO.docx) y [IX](https://www.fega.gob.es/sites/default/files/files/document/2023.11.10-ANEXO%20IX.Modelo_autorizaci%C3%B3n_acceso_REA_CUE_PUBLICADO.docx), y el [PDF del Anexo X](https://www.fega.gob.es/sites/default/files/files/document/2024.05.17-ANEXO_X-ProcedimientoAutorizacionCUE_PUBLICADO.pdf). Esos archivos tampoco contienen Excel incrustados, hojas ocultas, adjuntos o tablas de filas de catálogos. El VI sí contiene incrustaciones, ya conservadas en `data/iuws_fuentes`, pero son descriptor y esquema. **Valores oficiales de los catálogos: no los he encontrado en estos ficheros ni en las distribuciones públicas localizadas de FEGA y datos.gob.es.**

Las 15 tablas identificadas **solo por nombre exacto** son `EFICACIA_TRATAMIENTO`, `UNIDADES_MEDIDA`, `JUSTIFICACION_ACTUACION`, `ENFERMEDADES`, `MALAS_HIERBAS`, `SIST_RIEGO`, `TIPO_ANALISIS`, `MATERIAL_ANALIZADO`, `PROD_VEGETAL`, `DEST_RES_VEG`, `DEST_COSECHA`, `BUENAS_PRACTICAS_AMBITOS`, `METODO_APLICACION_FERTILIZANTE`, `TIPO_MEDIDA_FITOSANITARIA` y `TRAT_ESTIERCOLES` (cruce reproducible en [`catalogos_siex.py`](../backend/app/catalogos_siex.py)). La coincidencia del nombre no verifica los valores ni su aceptación por IUWS.

### ¿Se puede descargar sin certificado?

**No**, por el acceso público comprobado: la página y `tablas/configJson` responden sin certificado, pero solo se obtuvo la definición de 287 tablas; la consulta de filas pasa por reCAPTCHA. **No lo he podido comprobar** tras el alta, porque no contamos con credenciales ni certificado. Las búsquedas en FEGA y datos.gob.es no dieron un fichero de filas SIEX; esto no prueba su inexistencia.

**Reconfirmado el 27/09/2026, por los dos lados y con el mismo resultado:** en el código del propio portal (`recaptcha/api.js` + `ngx-captcha`, y la descarga del ZIP exige el token que emite el navegador), y en los documentos oficiales (el Anexo VII del Documento Técnico **solo enlaza al portal**; el Anexo V define campos, no valores). Sigue sin existir una URL pública de las filas. **No se ha intentado pasar el captcha** y no se va a intentar: hay una prueba que revienta si alguien mete esa dirección en cualquier constante de descarga (ver [`CATALOGOS_OFICIALES.md`](CATALOGOS_OFICIALES.md)).

**Lo que sí se ha bajado ese día** (y esto es nuevo): los documentos del FEGA y, **del MAPA**, sus 15 tablas de codificación, el listado completo de productos registrados y los ficheros publicados de plagas y jerarquía de especies, todo con su dirección, su fecha y su huella en [`data/fega`](../data/fega/LEEME.md). **Ninguno de esos ficheros es un catálogo de códigos SIEX** ni una equivalencia con ellos: son de otro organismo y para otra cosa (`Unidades` del MAPA **no es** `UNIDADES_MEDIDA` de SIEX). Lo que falta sigue siendo lo mismo que dice este apartado, y lo que hay que hacer con ello es el correo de abajo.

### Si no existe publicado

Añadir esta consulta **al mismo correo de solicitud de alta** dirigido a FEGA en `soporte-integracioncue@fega.es`, con copia a Castilla y León en `comercialcuecyl@jcyl.es` (el segundo contacto figura en [Anexo X, tabla de empresas desarrolladoras, p. 6](https://www.fega.gob.es/sites/default/files/files/document/2024.05.17-ANEXO_X-ProcedimientoAutorizacionCUE_PUBLICADO.pdf); el primero figura en el formulario de integración conservado en `F:/CuadernoCampo/16_CastillaYLeon_formulario_acceso_entorno_integracion.docx`, cuya vigencia no está reconfirmada). No se ha enviado el correo ni solicitado el alta:

> Asunto: Solicitud de alta en integración CUE y acceso a catálogos SIEX
>
> Buenos días. Junto con nuestra solicitud de alta en el entorno de integración CUE, consultamos el acceso oficial a los valores de catálogos SIEX aplicables a IUWS v3.11.4. El portal público nos permite consultar la estructura de las tablas, pero no hemos localizado sus filas de códigos. ¿El alta habilita un acceso autenticado a esas filas? Solicitamos la URL o el procedimiento de descarga, la documentación del método, los permisos y la versión/fecha de actualización. Hemos identificado por nombre exacto estas 15 tablas: `EFICACIA_TRATAMIENTO`, `UNIDADES_MEDIDA`, `JUSTIFICACION_ACTUACION`, `ENFERMEDADES`, `MALAS_HIERBAS`, `SIST_RIEGO`, `TIPO_ANALISIS`, `MATERIAL_ANALIZADO`, `PROD_VEGETAL`, `DEST_RES_VEG`, `DEST_COSECHA`, `BUENAS_PRACTICAS_AMBITOS`, `METODO_APLICACION_FERTILIZANTE`, `TIPO_MEDIDA_FITOSANITARIA` y `TRAT_ESTIERCOLES`. ¿Pueden confirmarnos sus valores oficiales y la equivalencia de los otros 25 nombres del descriptor? Gracias.

La maquinaria también depende de esta respuesta: las filas 206–211, 268–273 y 566–571 del descriptor exigen seis datos por elemento, pero marcan `TipoMaquinariaUNE`, `UnidadesMedida` y `TipoEnergia` como **«Validar contra catálogo»**. La configuración SIEX publica las estructuras `TIPO_MAQUINA_UNE`, `UNIDADES_MEDIDA` y `TIPENERGIA`, sin filas de códigos accesibles públicamente. La primera y la tercera **no se equiparan por semejanza**; incluir en la consulta: «¿Confirman la tabla oficial y los códigos vigentes para esos tres campos de `Maquinaria`?». `PotenciaMaquinaria`, `NumRepeticiones` y `Duracion` son cifras de cada uso, pero una lista `Maquinaria` con cualquiera de los seis campos obligatorios vacío no valida contra el esquema.

## 2. Códigos de DGC y DGC ajena

### Qué falta

Está **resuelto quién genera el identificador de una DGC nueva**: el CUE comercial. Siguen sin documentarse la regla concreta de asignación, el ámbito de unicidad y la recuperación de su correspondencia con el código interno posterior.

### Dónde se publica

[Anexo VI v3.11.4](https://www.fega.gob.es/sites/default/files/files/document/2025.11.19-ANEXO%20VI.Interfaz%20%C3%9Anico%20Com%C3%BAn_V3_11_4.docx), apartado `Importación de datos en el cue (crear)`, y el Excel incrustado, hoja `EstructuraCuadernoWS`, filas 14 y 36–37.

### Qué dice

«un identificador único por cada DGC, generado por el CUE comercial» (Anexo VI, apartado `Importación de datos en el cue (crear)`). Dice además que reenviar una DGC ya enviada da error y que un cambio de cultivo usa una DGC existente en REA o dada de alta antes desde el CUE comercial. El descriptor llama a `CodigoDGCAjena` «Código de la DGC no vinculada a REA» y para los campos alternativos señala «Indicar código de la DGC o DGCAjena, pero nunca ambos» (hoja `EstructuraCuadernoWS`, filas 36–37). Ambos se declaran `number(16)` en esa hoja; el esquema JSON espera enteros. El ejemplo numérico del anexo **no** establece un algoritmo ni reserva rangos. **Inferencia de ambos documentos:** no hay que esperar a que la Junta asigne *ese identificador ajeno* para una DGC nueva, pero tampoco se puede inventar su política de unicidad.

### ¿Se puede descargar sin certificado?

**Sí**: el Anexo VI se descargó del enlace FEGA y se inspeccionaron el texto y la hoja incrustada sin certificado. No se ha probado el alta real de una DGC, que sí exige autorización.

### Si no existe publicado

Pedir a FEGA y Castilla y León por los contactos anteriores:

> Asunto: IUWS v3.11.4: regla de asignación de CodigoDGCAjena
>
> Buenos días. El apartado «Importación de datos en el cue (crear)» del Anexo VI indica que el CUE comercial genera un identificador único para cada DGC nueva y el descriptor declara `CodigoDGCAjena` como `number(16)`. ¿La unicidad se exige por explotación, cuaderno, CUE comercial o en otro ámbito? ¿Hay rangos reservados, restricciones adicionales o un método documentado para recuperar el código interno de REA tras el alta? ¿Debe persistirse y reutilizarse el mismo `CodigoDGCAjena` en todas las actividades posteriores? Agradecemos la referencia normativa o técnica y un ejemplo válido. Gracias.

## 3. Correspondencia de 25 nombres de catálogo sin coincidencia exacta

### Qué falta

La correspondencia oficial entre cada nombre usado por el descriptor CUE y una tabla concreta de SIEX. **Sin documentar** en los 25 casos siguientes; no se ha emparejado por semejanza.

### Dónde se publica

[Descriptor CUE del Anexo VI](https://www.fega.gob.es/sites/default/files/files/document/2025.11.19-ANEXO%20VI.Interfaz%20%C3%9Anico%20Com%C3%BAn_V3_11_4.docx), hoja `EstructuraCuadernoWS`, frente a la [configuración de tablas SIEX](https://www3.sede.fega.gob.es/bdcsixpor/tablas/configJson). **Tabla de equivalencias oficial: no lo he encontrado.**

### Qué dice

El descriptor identifica, por ejemplo, «Tipo de labor» (hoja `EstructuraCuadernoWS`, fila 562), pero no da un identificador de tabla SIEX para ese concepto. El cruce exacto de todo el inventario da estos 25 nombres **sin documentar**:

| Nombre en el descriptor | Correspondencia SIEX |
|---|---|
| sin especificar en el descriptor | Sin documentar |
| tipos de producto | Sin documentar |
| Plagas | Sin documentar |
| Origen del agua de riego | Sin documentar |
| Producto | Sin documentar |
| Reguladores del crecimiento y otros | Sin documentar |
| Variedad | Sin documentar |
| Buenas prácticas de riego | Sin documentar |
| Buenas prácticas fertilizantes | Sin documentar |
| Detalle de material fertilizante | Sin documentar |
| Medida preventiva/cultural | Sin documentar |
| Producto (Cultivo) | Sin documentar |
| Productos | Sin documentar |
| Productos vegetales | Sin documentar |
| Tipo Fertilización | Sin documentar |
| Tipo de sustancias activas | Sin documentar |
| Tipo material fertilizante | Sin documentar |
| actividad de la cubierta | Sin documentar |
| coberturas de suelo | Sin documentar |
| cultivos | Sin documentar |
| especies | Sin documentar |
| paises | Sin documentar |
| productos | Sin documentar |
| tipos de tratamiento de semilla | Sin documentar |
| unidades | Sin documentar |

La tabla es un resultado de comparación literal de nombres, no una cita de FEGA. No he encontrado un documento que resuelva las correspondencias.

### ¿Se puede descargar sin certificado?

**Sí**, el descriptor y la estructura de las tablas; **no lo he podido comprobar** para una equivalencia oficial porque no he encontrado el documento ni probado un acceso autenticado.

### Si no existe publicado

Pedir a FEGA, con copia a Castilla y León, por los contactos del punto 1:

> Asunto: IUWS v3.11.4: equivalencia de 25 nombres de catálogo
>
> Buenos días. Al cruzar literalmente los 40 nombres de catálogo del descriptor CUE con `tablas/configJson`, 15 coinciden y 25 no. Adjuntamos el listado de los 25 nombres de este documento. ¿Pueden facilitarnos la tabla oficial de correspondencias nombre del descriptor → ID de tabla SIEX, incluida la versión aplicable a IUWS v3.11.4? Les rogamos aclarar también si algunos nombres se refieren a catálogos ajenos a SIEX o a valores libres. Gracias.

## 4. Tres discrepancias entre descriptor y esquema

### Qué falta

Una fe de erratas o instrucción oficial que determine el campo admitido y la fuente de `TipoLabor`.

### Dónde se publica

[Anexo VI v3.11.4](https://www.fega.gob.es/sites/default/files/files/document/2025.11.19-ANEXO%20VI.Interfaz%20%C3%9Anico%20Com%C3%BAn_V3_11_4.docx), descriptor incrustado, hoja `EstructuraCuadernoWS`, filas 259, 216 y 562, y esquema JSON incrustado. **Aclaración o fe de erratas: no lo he encontrado.**

### Qué dice

El descriptor marca `Cosecha.GestionInsumos` con `*` y lo describe como «Indica si hay gestión de ínsumos» (fila 259); el esquema no declara esa propiedad dentro de `Cosecha`. Declara `LaboresCulturales.TipoLabor` obligatorio (`*`), `number(2)` y «Tipo de labor» (fila 562), sin nombrar la tabla de códigos. La fila 216 declara `UsoSemillaTratada.IdAjenaSiembraPlant` como «Identificador de la actividad de siembra en origen», pero el esquema no admite esa propiedad en ese bloque. La fila 181 muestra el mismo nombre en otro bloque; no prueba que el de la fila 216 sea válido. **Ningún documento localizado aclara cuál prevalece.** Para validar paquetes se comprueba el esquema, sin presentar eso como una resolución oficial de la contradicción.

### ¿Se puede descargar sin certificado?

**Sí**: se descargó el Anexo VI, se extrajeron sus dos artefactos y se compararon las propiedades, sin certificado. **No** hay respuesta de la administración comprobada.

### Si no existe publicado

Pedir a FEGA, con copia a Castilla y León:

> Asunto: IUWS v3.11.4: tres diferencias entre descriptor y esquema CUE
>
> Buenos días. Hemos localizado tres diferencias en el Anexo VI v3.11.4: (1) `Cosecha.GestionInsumos` es obligatorio en la hoja `EstructuraCuadernoWS` pero no está en el esquema JSON; (2) `LaboresCulturales.TipoLabor` exige un código y no indica la tabla de origen; (3) `UsoSemillaTratada.IdAjenaSiembraPlant` figura en el descriptor pero no en el esquema de ese bloque. ¿Qué regla prevalece en cada caso para una importación que deba validar? ¿Existe corrección o versión posterior? Agradecemos referencia y, para `TipoLabor`, catálogo e ID de tabla. Gracias.

## 5. Conversión de P y K del plan de abonado

### Qué falta

Confirmación de la **precisión y política de conversión que espera IUWS** para pasar los datos elementales P y K guardados por el cuaderno a `NecesidadUFP2O5` y `NecesidadUFK2O`, especialmente antes de convertir valores históricos.

### Dónde se publica

El destino está en el [descriptor CUE del Anexo VI](https://www.fega.gob.es/sites/default/files/files/document/2025.11.19-ANEXO%20VI.Interfaz%20%C3%9Anico%20Com%C3%BAn_V3_11_4.docx), hoja `EstructuraCuadernoWS`, filas 446–447. La [*Guía práctica de la fertilización racional de los cultivos en España* del MAPA](https://www.mapa.gob.es/es/agricultura/publicaciones/02_FERTILIZACI%C3%93N%28BAJA%29_tcm30-57891.pdf) da factores agronómicos redondeados. **Instrucción específica de conversión IUWS: no lo he encontrado** en el Anexo V ni en el documento técnico SIEX examinado.

### Qué dice

El descriptor pide «Necesidad UF P2O5 (kg/ha)» y «Necesidad UF K2O (kg/ha)» (filas 446–447). La guía MAPA dice «P x 2,3= P2O5; K x 1,2= K2O» (capítulo 24, *Abonado de los cítricos*, fórmula del factor F2, p. 198 impresa / p. 78 del PDF). Es una **guía agronómica**, no una especificación IUWS; no establece por sí sola redondeo, tratamiento de datos ya expresados en óxidos ni cómo interpretar los campos históricos del cuaderno. Por ello no se aplica automáticamente ningún factor en el exportador. Otras publicaciones alojadas por MAPA utilizan `2,29` para P; esa diferencia de redondeo refuerza la necesidad de confirmar la regla de IUWS.

### ¿Se puede descargar sin certificado?

**Sí**: descriptor y guía MAPA se obtienen como ficheros públicos. No se ha validado la conversión mediante una importación autenticada.

### Si no existe publicado

Pedir a FEGA, con copia a Castilla y León:

> Asunto: IUWS v3.11.4: conversión de P y K a P2O5 y K2O
>
> Buenos días. El descriptor solicita `NecesidadUFP2O5` y `NecesidadUFK2O` en kg/ha. Nuestro origen conserva P y K elementales. La guía MAPA cita factores redondeados de 2,3 y 1,2; otras publicaciones usan 2,29 para P. ¿Qué factor, precisión y redondeo exige o recomienda IUWS v3.11.4? ¿Debe distinguirse expresamente si un dato de origen ya está en óxidos? Solicitamos una referencia técnica y un ejemplo de entrada aceptado. Gracias.

## 6. Alta en el entorno de integración en 2026

### Qué falta

Confirmar el formulario vigente, sus destinatarios completos y el plazo de respuesta; no se dispone de alta efectiva.

### Dónde se publica

[Anexo X de FEGA, edición de abril de 2024](https://www.fega.gob.es/sites/default/files/files/document/2024.05.17-ANEXO_X-ProcedimientoAutorizacionCUE_PUBLICADO.pdf), pp. 5–6, publica los pasos y el contacto de Castilla y León. El formulario de integración está conservado en `F:/CuadernoCampo/16_CastillaYLeon_formulario_acceso_entorno_integracion.docx`, pero **URL oficial vigente de descarga del formulario: no lo he encontrado**.

### Qué dice

«La empresa desarrolladora debe figurar en el registro [...] en estado INSCRITA» (Anexo X, p. 5). La tabla de la p. 6 da `comercialcuecyl@jcyl.es` y `https://servicios.ayg.jcyl.es/IUWS/`. El formulario local pide empresa, NIF, nombre comercial, CN del certificado, contacto y web; indica firma electrónica y envío a `soporte-integracioncue@fega.es` y `comercialcuecyl@jcyl.es`. **No he encontrado confirmación oficial de que ese formulario concreto y el primer correo sigan vigentes en 2026, ni un plazo de tramitación publicado.** El Anexo X diferencia empresa desarrolladora, entidad habilitada y autorización del titular; son trámites distintos.

### ¿Se puede descargar sin certificado?

**Sí**, el Anexo X se descargó públicamente. **No lo he podido comprobar** para el formulario 2026: solo hay una copia local antigua, que remite al Anexo VI v1.4, sin URL de origen comprobable. `/IUWS/api/version` responde sin certificado; eso no constituye alta.

### Si no existe publicado

Pedir a Castilla y León por el correo publicado en el Anexo X, con copia al correo FEGA del formulario local para que confirmen si sigue operativo:

> Asunto: Alta 2026 de CUE comercial en Castilla y León y entorno de integración
>
> Buenos días. Queremos inscribir un CUE comercial y acceder al entorno de integración IUWS v3.11.4. ¿Sigue vigente el formulario «Solicitud de acceso de empresas desarrolladoras ... al entorno de integración», firmado electrónicamente y remitido a `soporte-integracioncue@fega.es` y `comercialcuecyl@jcyl.es`? En caso contrario, ¿cuál es la URL oficial y el canal actual? Indiquen por favor documentación requerida, relación con la inscripción como desarrolladora y entidad habilitada, y plazo habitual de tramitación. Aún no remitimos datos personales ni certificados. Gracias.

## 7. Certificado de dominio

### Qué falta

El certificado real de la empresa y una confirmación administrativa de cómo comparan el CN con el dominio inscrito; el tipo y los requisitos técnicos básicos **sí están documentados**.

### Dónde se publica

[Anexo VI v3.11.4](https://www.fega.gob.es/sites/default/files/files/document/2025.11.19-ANEXO%20VI.Interfaz%20%C3%9Anico%20Com%C3%BAn_V3_11_4.docx), apartado `Securización y autenticación` y `Anexo 3. Tipos de certificados`; [Anexo X](https://www.fega.gob.es/sites/default/files/files/document/2024.05.17-ANEXO_X-ProcedimientoAutorizacionCUE_PUBLICADO.pdf), p. 5, pide comunicar el dominio en el caso indicado.

### Qué dice

El Anexo VI exige certificado de un «Prestador Cualificado de Servicios de Confianza» (apartado `Securización y autenticación`). El Anexo 3 admite **sello de entidad** o **certificado de servidor SSL/TLS (DV, OV, EV)**; pide CN con el dominio y autenticación de cliente en ambos casos, y dice «recomendamos el uso de Sello de entidad». Para el sello, el `serialNumber` del *Subject* identifica el NIF del titular del dominio. El Anexo X recoge el dominio como dato de autorización; **no he encontrado una regla textual de igualdad byte a byte, tratamiento de subdominios o normalización del CN**. Por eso hay que registrar el dominio efectivo y confirmarlo antes de adquirir el certificado. La frase anterior en [`INTEGRACION_IUWS.md`](INTEGRACION_IUWS.md) que decía que *tenía que* ser sello de entidad era demasiado restrictiva y debe corregirse.

### ¿Se puede descargar sin certificado?

**Sí**, los anexos se descargan sin certificado. **No**, la prueba de autenticación real no puede hacerse sin certificado y alta; no se ha intentado simularlos.

### Si no existe publicado

Pedir a Castilla y León por el contacto del Anexo X, con copia a FEGA:

> Asunto: IUWS Castilla y León: certificado y coincidencia del dominio
>
> Buenos días. El Anexo VI v3.11.4 admite sello de entidad o SSL/TLS DV/OV/EV con autenticación de cliente, y recomienda el sello. Antes de solicitar el certificado, ¿confirman que Castilla y León admite ambos tipos y qué Prestadores Cualificados/cadenas de confianza acepta? ¿Debe el CN coincidir exactamente con el dominio comunicado al alta, incluidos subdominio, mayúsculas y dominio internacionalizado, o se aplica otra regla? ¿Hay requisitos adicionales para `serialNumber`, SAN o uso extendido de clave? Gracias.

## 8. Castilla y León: zonas vulnerables, nitrógeno y orden completa

### Qué falta

El fichero municipal oficial **ya está descargado y derivado de forma reproducible**. Queda contrastar la vigencia jurídica de esa delimitación y resolver dudas de pertenencia de parcelas concretas. Los límites y periodos pedidos **sí están publicados** en la orden íntegra.

### Dónde se publica

[Orden MAV/398/2022 íntegra, BOCyL de 05/05/2022](https://bocyl.jcyl.es/boletines/2022/05/05/pdf/BOCYL-D-05052022-1.pdf): Anexo III, p. 20895 del boletín / p. 23 del PDF; Anexo V, p. 20897 / p. 25 del PDF. La [ficha oficial de IDECyL](https://idecyl.jcyl.es/geonetwork/static/api/records/spagobcylsoscoavulnitz20) enlaza el [Excel de municipios y zonas](https://opendata.jcyl.es/ficheros/carto/medioambiente/sostenibilidad/coad_cyl_vulnerab_nitrat.xlsx), que sí responde. El [enlace SHP antiguo](https://datosabiertos.jcyl.es/web/jcyl/risp/es/medio-ambiente/zonas-vulnerables/1284997397537.shp) siguió dando HTTP 404. La [tabla oficial de provincias del INE](https://www.ine.es/daco/daco42/codmun/cod_provincia.htm) completa el nombre de provincia de cada código municipal.

### Qué dice

«APORTES MÁXIMOS DE NITRÓGENO [...] EN FUNCIÓN DE LOS CULTIVOS» (Orden MAV/398/2022, Anexo III, BOCyL p. 20895): tabla de N kg/ha por cultivo y secano/regadío, con nota de ajuste por cosecha esperada y remisión a la guía MAPA para otros cultivos. «PERIODOS EN LOS QUE NO PUEDEN APLICARSE FERTILIZANTES NITROGENADOS» (Anexo V, p. 20897): tabla por cultivo y tipo de fertilizante. El Excel de IDECyL contiene 24 zonas y 387 códigos de municipio del Decreto 5/2020; su ficha declara revisión de metadatos el 10/02/2026, lo que no confirma por sí solo que no haya modificaciones normativas posteriores. El Anexo III solo genera un aviso no bloqueante con zona, cultivo y sistema coincidentes; el Anexo V conserva periodos relativos como consulta.

### ¿Se puede descargar sin certificado?

**Sí**. El PDF íntegro y el [Excel de IDECyL](https://opendata.jcyl.es/ficheros/carto/medioambiente/sostenibilidad/coad_cyl_vulnerab_nitrat.xlsx) se descargaron sin certificado. [`zv_cyl.csv`](../data/zv_cyl.csv) se derivó de ese Excel y de la tabla INE; [originales, huellas y reproducción](../data/zv_cyl_fuentes/LEEME.md). El enlace SHP antiguo devolvió HTTP 404; no se necesita para el listado municipal.

### Si no existe publicado

Para dudas de vigencia normativa, límites de parcela y cambios posteriores, usar el contacto de la Junta publicado en el Anexo X o el [formulario oficial de datos abiertos](https://datosabiertos.jcyl.es/web/es/participa/solicitud-apertura-datos.html):

> Asunto: Vigencia del listado municipal de zonas vulnerables 2020
>
> Buenos días. Hemos descargado el Excel `coad_cyl_vulnerab_nitrat.xlsx` desde la ficha oficial de IDECyL, con 387 códigos municipales y 24 zonas del Decreto 5/2020. ¿Confirman si esa es la delimitación municipal vigente y si existe una modificación posterior que debamos incorporar? ¿Cómo se comprueba un recinto concreto cuando el límite no coincide exactamente con el municipal? Agradeceríamos también confirmación de cambios posteriores relevantes en los anexos III y V de la Orden MAV/398/2022. Gracias.

## Consecuencia para el proyecto

La regla de la **DGC ajena** deja de ser un vacío total: el Anexo VI autoriza expresamente que el CUE comercial genere un identificador único. Los **valores de catálogos**, las 25 equivalencias y las tres discrepancias siguen sin respuesta oficial. Las preguntas internas que sí podían resolverse ya recogen los cuatro datos de cosecha, la fecha de establecimiento de la cubierta separada de su mantenimiento, el tipo y anchuras de la cubierta, los restos de poda y desbroce, el tipo de producto y la unidad de la cantidad aplicada. Los textos libres aún requieren los códigos y equivalencias oficiales; no se envían como si los fueran. El Anexo III y el Anexo V de la orden castellano-leonesa están extraídos de forma reproducible en [`data/nitratos_cyl`](../data/nitratos_cyl/LEEME.md); el [listado municipal](../data/zv_cyl_fuentes/LEEME.md) ya permite un aviso no bloqueante para cultivo y sistema exactos, pero no resuelve notas, periodos relativos ni toda duda de delimitación o vigencia. Ningún hallazgo equivale a una importación IUWS aceptada: `GET /api/iuws/estado` debe seguir comunicando `conectado: false` mientras no se complete y pruebe el flujo autenticado.
