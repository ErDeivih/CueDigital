# Correo para enviar: alta en el entorno de integración y cinco consultas técnicas

> **Esto no es documentación: es un correo para copiar y mandar.** El envío sigue pendiente y es
> lo único que bloquea el volcado oficial. Todo lo que se pregunta aquí está comprobado contra los
> documentos oficiales, y las referencias van puestas para que quien conteste pueda ir al párrafo
> exacto. El detalle de cada punto, con lo que ya se ha descartado, está en
> [`FUENTES_OFICIALES_PENDIENTES.md`](FUENTES_OFICIALES_PENDIENTES.md).

## Antes de enviarlo

1. **Rellena lo que va entre `[...]`**: son datos tuyos (empresa, NIF, nombre comercial, CN del
   certificado, contacto y web). Los pide el formulario de acceso.
2. **Si todavía no tienes dominio ni certificado, elige el dominio primero.** El formulario pide
   el **CN del certificado**, y el Anexo VI explica que el CN contiene el nombre del dominio
   (máximo 64 caracteres) y que el `serialNumber` lleva el NIF de la empresa propietaria. Es decir:
   sin decidir el dominio no se puede rellenar la solicitud.
3. **Firma electrónicamente** la solicitud de alta si te lo piden y **adjúntala**. Las consultas
   técnicas van en el cuerpo del mismo correo.
4. **Guarda la copia enviada y la fecha.** Cuando contesten, esa respuesta se convierte en el
   fichero de origen de los catálogos, y habrá que guardarla como se ha hecho con el Excel de
   IDECyL y con el PDF del BOCyL: en `data/`, con su `LEEME`, su huella y su script para rehacerlo.

## El correo

**Para:** `soporte-integracioncue@fega.es`
**Copia:** `comercialcuecyl@jcyl.es`
**Asunto:** Solicitud de alta en el entorno de integración CUE y consultas técnicas del Anexo VI v3.11.4 (CUE Digital)

---

Buenos días.

Somos **[empresa desarrolladora]**, con NIF **[NIF]**, y solicitamos el alta en el entorno de
integración del Interfaz Único de Web Services para nuestro cuaderno de explotación
**«[nombre comercial del software]»**.

Los datos del formulario de acceso son:

- **Empresa desarrolladora:** [razón social]
- **NIF de la empresa:** [NIF]
- **Nombre del software comercial:** [nombre comercial]
- **CN del certificado de dominio con el que nos comunicaremos:** [CN]
- **Persona de contacto:** [nombre]
- **Teléfono:** [teléfono]
- **Correo electrónico:** [correo]
- **Página web:** [URL]

Adjuntamos la solicitud firmada electrónicamente. El certificado de dominio es de tipo
**[sello de entidad / servidor SSL-TLS]**, con autenticación de cliente, tal y como describe el
Anexo VI en su apartado de tipos de certificados.

Hemos trabajado sobre el **Anexo VI v3.11.4** y tenemos ya extraídos el descriptor
`BdcSix-DS-DiseñoCUE` y su esquema JSON. Antes de generar la primera carga nos quedan **cinco
consultas técnicas** que no hemos podido resolver con la documentación publicada. Las numeramos
para facilitar la respuesta.

**1. Valores de los catálogos de SIEX.** El portal público
(`https://www3.sede.fega.gob.es/bdcsixpor/catalogos`) permite consultar la **estructura** de las
tablas —hemos descargado la definición de las 287— pero no hemos podido acceder a sus **filas de
códigos**. ¿El alta habilita un acceso autenticado a esos valores? ¿Hay un procedimiento o
dirección de descarga documentada? Por coincidencia exacta de nombre hemos identificado estas
quince tablas: `EFICACIA_TRATAMIENTO`, `UNIDADES_MEDIDA`, `JUSTIFICACION_ACTUACION`,
`ENFERMEDADES`, `MALAS_HIERBAS`, `SIST_RIEGO`, `TIPO_ANALISIS`, `MATERIAL_ANALIZADO`,
`PROD_VEGETAL`, `DEST_RES_VEG`, `DEST_COSECHA`, `BUENAS_PRACTICAS_AMBITOS`,
`METODO_APLICACION_FERTILIZANTE`, `TIPO_MEDIDA_FITOSANITARIA` y `TRAT_ESTIERCOLES`. Nos faltaría
también la correspondencia de los **otros 25 nombres de catálogo** que usa el descriptor y que no
coinciden literalmente con ninguna tabla.

**2. Identificador de una DGC nueva (`CodigoDGCAjena`).** El apartado «Importación de datos en el
cue (crear)» del Anexo VI dice que se solicita «un identificador único por cada DGC, generado por
el CUE comercial que envía los datos al CUE», y el descriptor declara `CodigoDGCAjena` como
`number(16)`. ¿En qué ámbito debe ser único (explotación, cuaderno, CUE comercial)? ¿Hay rangos
reservados o restricciones de formato? ¿Cómo se recupera después la correspondencia con el código
interno de REA? ¿Debe reutilizarse el mismo valor en todas las actividades posteriores?

**3. Máquinas de aplicación.** En el bloque `Maquinaria` (utilizado por siembra, labores y
postcosecha) el descriptor exige seis datos por elemento y tres de ellos —`TipoMaquinariaUNE`,
`UnidadesMedida` y `TipoEnergia`— se validan contra catálogo. ¿Pueden confirmarnos la tabla
oficial y los códigos vigentes para esos tres campos?

**4. Conversión de fósforo y potasio.** El descriptor pide `NecesidadUFP2O5` y `NecesidadUFK2O` en
kg/ha (hoja `EstructuraCuadernoWS`, filas 446-447). Nuestro origen guarda P y K elementales. La
*Guía práctica de la fertilización racional de los cultivos en España* del MAPA usa factores
redondeados (P × 2,3; K × 1,2) y otras publicaciones usan 2,29 para el fósforo. **¿Qué factor,
precisión y redondeo espera el interfaz?** ¿Debe distinguirse si el dato de origen ya está
expresado en óxidos?

**5. Tres diferencias entre el descriptor y el esquema, en el Anexo VI v3.11.4.** Hemos cotejado
los dos documentos y aparecen tres casos que no sabemos cómo resolver:
`Cosecha.GestionInsumos` figura como obligatorio en la hoja `EstructuraCuadernoWS` pero **no está
en el esquema JSON**; `LaboresCulturales.TipoLabor` exige un código y **no indica la tabla de
origen**; y `UsoSemillaTratada.IdAjenaSiembraPlant` aparece en el descriptor pero **no en el
esquema** de ese bloque. ¿Qué regla prevalece en cada caso para una carga que deba validar? ¿Hay
una versión posterior corregida?

**6. La pregunta que decide si hace falta mandar algo por obligación.** Es la que más nos importa
para no decirle al agricultor ni más ni menos de lo que toca, y **no la damos por sabida**:

- El artículo 10.2 del Real Decreto 1054/2022 dice que los titulares «decidirán de forma voluntaria
  poner a disposición de la administración, a través de los REA correspondientes, la información que
  hayan cumplimentado en el CUE», y el artículo 10.3 permite usar «cualquier otro sistema
  informático de su elección» que cumpla los requisitos técnicos y el contenido mínimo del anexo II.
- Pero el artículo 16.1, apartado 5, del Real Decreto 1311/2012 dice que los datos «se consignarán
  de manera electrónica por los agricultores, sus representantes o sus asesores, de acuerdo con lo
  previsto en el Real Decreto 1054/2022» y que «deberán ser proporcionados, **al menos, con carácter
  mensual**».

**La pregunta:** si un titular lleva el registro de tratamientos en un programa propio, con los
datos íntegros y en formato legible por máquina a disposición de la autoridad cuando los requiera,
**¿cumple con esa obligación de consignación electrónica, o está obligado a volcarlos además a la
aplicación de la Junta (CUECyL) o al CUE con periodicidad mensual?** Y si está obligado: ¿a través
de qué vía —REA de la comunidad autónoma, servicios IUWS del CUE, o la aplicación de la Junta—, con
qué periodicidad exacta y con qué consecuencia si el programa propio no vuelca? Lo preguntamos
porque de la respuesta depende que el agricultor tenga que hacer un trámite más o ninguno, y
preferimos decírselo con su contestación delante.

Quedamos a su disposición para cualquier aclaración y agradecemos de antemano la referencia
normativa o técnica de cada respuesta.

Un saludo,
[nombre]
[empresa desarrolladora]
[teléfono] · [correo]

---

## Qué esperar, y qué hará el proyecto con la respuesta

- **Si contestan con los valores de los catálogos**, se guardan como fichero derivado en `data/`
  con su `LEEME`, su procedencia y su huella —igual que se ha hecho con el Excel de IDECyL y con
  el PDF del BOCyL—, se mapea cada código a los campos que están ya mapeados, y se intenta la
  **primera carga autenticada** contra el entorno de integración. Es lo único que al proyecto le
  queda por probar: nunca se ha hecho una llamada autenticada.
- **Si contestan que los catálogos no se publican**, entonces se cargan a mano los códigos que el
  agricultor necesite y se dice en pantalla qué falta, en vez de inventar códigos.
- **Mientras tanto**, el proyecto sigue funcionando entero sin el volcado oficial, y así lo dice
  en `GET /api/iuws/estado`: `conectado: false`, con la lista de lo que falta y de quién depende.
