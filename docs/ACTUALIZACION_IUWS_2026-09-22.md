# IUWS: fuentes oficiales y estado comprobado el 22/09/2026

Esta nota sustituye las afirmaciones anteriores de que falta el fichero del descriptor y de
que el entorno de integración no publica los métodos. Se comprobó la versión **3.11.4**.

## El descriptor y el esquema ya están aquí

Fuente: [página de documentación técnica agrícola SIEX del FEGA](https://www.fega.gob.es/es/siex/documentacion-tecnica-agricola-siex), que enlaza el
[Anexo VI, Interfaz Único Común v3.11.4](https://www.fega.gob.es/sites/default/files/files/document/2025.11.19-ANEXO%20VI.Interfaz%20%C3%9Anico%20Com%C3%BAn_V3_11_4.docx).
El documento Word lleva incrustados dos libros Excel y un esquema JSON. Se extrajeron los
bytes originales, sin modificar el contenido, a:

| Fichero | Contenido | SHA-256 |
|---|---|---|
| [`BdcSix-DS-DisenoCUE_3.11.4.xlsx`](../data/iuws_fuentes/BdcSix-DS-DisenoCUE_3.11.4.xlsx) | Descriptor CUE, con hoja `EstructuraCuadernoWS` y marca `Versión 3.11.4` | `eec4e809732e17cd845343db1e0b7bb51507b8878c8f6c0f4d57039cac752217` |
| [`BdcSix-DS-DisenoCUE_3.11.4.schema.json`](../data/iuws_fuentes/BdcSix-DS-DisenoCUE_3.11.4.schema.json) | Esquema JSON del CUE, incluido en el mismo Anexo VI | `f7be0ec1b58271936806a27a3eeb592d3e5804e218927f0f9a15d7dac9555e5f` |
| [`BdcSix-DS-DisenoRegistroREA_3.11.xlsx`](../data/iuws_fuentes/BdcSix-DS-DisenoRegistroREA_3.11.xlsx) | Descriptor REA, para cotejar las descargas | `20db35c973159241c3fc06834881286998cc3582a153aecee167cc144c52bb46` |

El esquema exige un objeto raíz `CUADERNO` (lista). Cada elemento exige
`CAExplotacion`, `IdTitular`, `CodigoRea` y `UnidadGestora`. Entre los bloques de
`ActividadesExplotacion` figuran `TratamFito`, `SiembraPlantacion`, `Fertilizacion`,
`ComercializacionVD` y `Riego`. Estos nombres vienen del esquema, no de los ejemplos del
anexo.

**El sobre de la aplicación ya cumple ese contrato** (comprobado el 23/09/2026 contra el
esquema, con tests). Al cotejarlo aparecieron tres cosas que venían de copiar el ejemplo del
anexo en vez del esquema:

| Estaba | Dice el esquema | Qué pasaba |
|---|---|---|
| `IDTitular` | `IdTitular`, obligatorio | El campo obligatorio no estaba: el sobre no podía validar nunca |
| `IdCuaderno` como texto | `integer` | Tampoco validaba |
| — | `CodigoSIEX` y `CodigoRea` de **exactamente 14** caracteres | Un código corto se rechaza |

Lo que sigue sin poder comprobarse es lo de dentro: los bloques de `ActividadesExplotacion`
necesitan códigos de catálogo que no tenemos, y el esquema **no admite ningún campo vacío**
(528 tipos declarados, ningún `null`).

## Direcciones vigentes

La revisión 3.11.0 del Anexo VI añadió `/api/` a todos los métodos y retiró
`IdCuaderno` de la ruta de exportación CUE. El código ya construye esas rutas. Llamadas
de solo lectura hechas el 22/09/2026, sin certificado:

| Servidor | Ruta | Respuesta |
|---|---|---|
| Integración FEGA | `https://sga.entornointegracion.es/IUWS/api/version` | HTTP 200, `Versión del descriptor : 3.11.4` |
| Castilla y León | `https://servicios.ayg.jcyl.es/IUWS/api/version` | HTTP 200, `{"version": "3.11.4"}` |
| Integración FEGA | `/IUWS/version` | HTTP 404: ruta antigua sin `/api/` |

El 404 anterior **no demuestra que falte el alta**. La ruta actual de versión funciona en el
entorno de integración. No se han probado con certificado los métodos de comunicación,
exportación, importación ni consulta de estado de esta versión.

## Autenticación y catálogos

El Anexo VI v3.11.4 describe un certificado de un Prestador Cualificado de Servicios de
Confianza. Admite sello de entidad y certificado de servidor SSL/TLS (DV, OV o EV), siempre
con autenticación de cliente. Recomienda sello de entidad. En el sello, el `CN` contiene el
dominio (máximo 64 caracteres) y el `serialNumber` del **Subject** contiene el NIF de la
empresa propietaria del dominio. El dominio usado debe coincidir con el autorizado. La
llamada de comunicación usa el certificado para obtener un JWT; las llamadas posteriores
llevan el JWT y ya no requieren las cabeceras `certificate-sscc` ni `data-signed`.

La [página oficial de catálogos SIEX](https://www3.sede.fega.gob.es/bdcsixpor/catalogos)
responde sin certificado. Aún no se ha comprobado la descarga completa de sus listas ni si
existen códigos publicables para eficacia del tratamiento y estado fenológico. Por tanto,
los campos sin código verificado siguen vacíos.

La [Orden MAV/398/2022 íntegra en el BOCyL](https://bocyl.jcyl.es/boletines/2022/05/05/pdf/BOCYL-D-05052022-1.pdf)
ya tiene una fuente oficial localizable. Queda por extraer y contrastar de ella las reglas
concretas que se quieran incorporar a cálculos y avisos.

También se ha localizado un [conjunto de datos oficial de zonas vulnerables de Castilla y
León](https://datos.gob.es/es/catalogo/a07002862-prevencion-ambiental-cyl-zonas-vulnerables-2020)
con un recurso cartográfico SHP del Decreto 5/2020. Aún no se ha cotejado su vigencia ni su
geometría con las parcelas de la aplicación, por lo que `data/zv_cyl.csv` permanecía vacío.
**Actualización del 23/09/2026:** se localizó el [Excel oficial de IDECyL](../data/zv_cyl_fuentes/LEEME.md)
con códigos municipales y se derivó el CSV; la situación anterior queda superada.

## Trabajo pendiente

1. Mapear cada dato de `backend/app/iuws_contenido.py` al descriptor 3.11.4, sin asignar
   códigos no publicados, y generar JSON que pase el esquema oficial. La plantilla
   `data/iuws_descriptor_cue.ejemplo.json` sigue siendo incompleta y no se carga sola.
2. Completar y verificar los catálogos necesarios. La aplicación mantiene `conectado=false`
   mientras esta tarea esté pendiente.
3. Probar el flujo autenticado en integración con el certificado, el nombre comercial, la
   entidad habilitada y la autorización de un titular reales. El alta y el certificado
   siguen dependiendo de David y de los organismos competentes. Los correos del formulario
   conservado en el proyecto aún no se han reconfirmado como procedimiento vigente en 2026.
4. Comprobar el listado oficial de zonas vulnerables y los límites y periodos de nitrógeno
   antes de cargar valores en la aplicación.
