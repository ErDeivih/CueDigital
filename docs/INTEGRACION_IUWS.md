# Integración con la Junta: el volcado oficial (IUWS)

Guía honesta de en qué punto está el volcado oficial del cuaderno y qué hace falta para
terminarlo. Escrita para quien tenga que hacer la integración, no para lucir.

---

## 1. Qué es el IUWS

El **Interfaz Único de Web Services** es el canal oficial por el que un cuaderno comercial
(esto) entrega los datos al CUE de la comunidad autónoma. Lo define FEGA en el
**Anexo VI. Interfaz Único Común**, y cada comunidad publica su dirección.

| Dato | Valor |
|---|---|
| Documento | Anexo VI. Interfaz Único Común **v3.11.4** (19/11/2025) |
| Versión del descriptor de cuaderno | **v3.11.4** — y está aquí, en `data/iuws_fuentes/` |
| Versión del interfaz que contesta hoy | **3.11.4** (comprobado el 22/09/2026) |
| Dirección en Castilla y León | `https://servicios.ayg.jcyl.es/IUWS/api/` |
| Entorno de integración (pruebas) | `https://sga.entornointegracion.es` |
| Consola de pruebas (Swagger) | `https://sga.entornointegracion.es/IUWS/swagger-ui.html` |
| Catálogos oficiales | `https://www3.sede.fega.gob.es/bdcsixpor/catalogos` (estructura pública; los **valores**, detrás de un captcha) |
| Código de comunidad autónoma | Castilla y León = **13** |
| Correos para pedir acceso | `soporte-integracioncue@fega.es` y `comercialcuecyl@jcyl.es` |

> **Las rutas llevan `/api/`**, y la de exportación CUE ya no lleva `IdCuaderno`. Esto se
> comprobó llamando el 22/09/2026: en el entorno de integración `/IUWS/api/version` contesta
> `200` con `Versión del descriptor : 3.11.4`, y `/IUWS/version` contesta `404`. En Castilla y
> León contestan las dos direcciones (con `200` la de versión y `401` los demás métodos), así
> que **la que hay que usar es la de `/api/`**.

> Las direcciones de Castilla y León y los dos correos salen del **Anexo X. Procedimiento de
> autorización CUE**, que las lista comunidad por comunidad. No están deducidas.

---

## 2. Los métodos, y qué hace cada uno

| Método | Dirección | Para qué |
|---|---|---|
| Establecer comunicación | `GET /IUWS/api/comunicacion/{nombreAppCue}` | Devuelve el token JWT. Es la puerta: sin él no funciona nada más |
| Versión | `GET /IUWS/api/version` | Con qué versión trabaja el interfaz. **No está securizado** |
| Exportar REA | `GET /IUWS/api/exportarREA/{NIF titular}_{CIF gestora}` | Los datos del registro de la explotación |
| Exportar CUE | `GET /IUWS/api/exportar/{Nº explotación}_{CIF gestora}` | El cuaderno entero. Ya **no** lleva `IdCuaderno` |
| Importar (crear) | `POST /IUWS/api/crear/` | Manda las actividades. Devuelve un **id de petición** |
| Comprobar estado | `GET /IUWS/api/comprobarEstado/{Id Petición}` | Si la petición ya se ha procesado, y con qué resultado |

Están implementadas en `backend/app/iuws.py`, con las direcciones sacadas del anexo (hay tests
que comprueban los ejemplos del documento). Lo que se ha comprobado **llamando de verdad**, sin
certificado, es esto:

| Dirección | En el entorno de integración | En Castilla y León (producción) |
|---|---|---|
| `/IUWS/api/version` | `200` — «Versión del descriptor : 3.11.4» | `200` — `{"version": "3.11.4"}` |
| `/IUWS/version` (sin `/api/`) | `404` — ruta antigua | `200` |
| `/IUWS/api/comunicacion/...` | `200` con `codigoResultado: FALLO`, `No Autorizado` | negociación TLS: **pide el certificado de cliente** |
| `/IUWS/api/crear/` | `405` con `GET` (existe; es un `POST`) | `401` |
| `/IUWS/api/exportar/...`, `/IUWS/api/exportarREA/...`, `/IUWS/api/comprobarEstado/...` | `200` con `No Autorizado` | `401` |

> Que el entorno de integración conteste un JSON con `No Autorizado` es **mejor noticia que un
> 404**: significa que la ruta existe, que ha entendido la dirección y que solo falta el
> certificado. Los `404` de antes eran culpa nuestra, por llamar a la ruta antigua.
> **Ninguna llamada autenticada se ha probado todavía.**

### Cómo se autentica, en corto

1. Se llama a `comunicacion/{nombreAppCue}` con el **certificado de cliente**.
2. Todas las llamadas llevan:
   - la cabecera **`certificate-sscc`** con el certificado en Base64, **sin** las líneas
     `-----BEGIN CERTIFICATE-----` / `-----END CERTIFICATE-----` y sin saltos de línea;
   - el parámetro **`data-signed`**: el NIF o CIF firmado con la clave privada del certificado.
     **Esto ya se puede hacer**, y está explicado abajo: se firma con el certificado **donde vive**
     (el almacén de Windows), sin exportar la clave.
3. El Anexo VI admite **sello de entidad** o **certificado de servidor SSL/TLS (DV, OV o EV)**,
   ambos con **autenticación de cliente**; recomienda el sello de entidad. En el sello, el
   **CN contiene el dominio** (máximo 64 caracteres) y el **`serialNumber` del Subject contiene
   el NIF** de la empresa propietaria del dominio. El dominio debe comunicarse para su
   autorización. La regla exacta de comparación del CN con el dominio inscrito no está publicada.
4. El interfaz autoriza por la terna **(dominio del certificado, NIF de la empresa habilitada
   que va en el JSON, cuaderno comercial)**. Si los tres no están en sus tablas de
   autorización, la llamada se rechaza con `ERROR_VALIDAR_CREDENCIALES`.

> **Ojo, aquí hay dos lecturas del anexo, y conviene no confundirlas** (esto se vio al leer la
> revisión de la versión 3.11.4: [`ACTUALIZACION_IUWS_2026-09-22.md`](ACTUALIZACION_IUWS_2026-09-22.md)):
>
> - Lo de arriba (punto 2) es la lectura **antigua**: *todas* las llamadas llevan
>   `certificate-sscc` y `data-signed`.
> - La lectura de la **3.11.4** dice que la llamada de comunicación usa el certificado para obtener
>   el **JWT**, y que **las llamadas posteriores ya no necesitan esas dos cosas**: les basta el token.
>
> **Qué hace hoy el programa:** sigue la lectura de la 3.11.4 —la llamada de comunicación va con el
> certificado de cliente en el TLS y las demás con `Authorization: <jwt>` (`_cabeceras()` en
> `iuws_cliente.py`)—. Las dos piezas de la otra lectura **están escritas y probadas**
> (`cabecera_certificado()` y `datos_firmados()`, con sus tests), pero **no se mandan**: hasta que el
> alta no esté hecha no hay forma de saber cuál de las dos lecturas acepta el interfaz, y mandar de más
> no se puede comprobar. **La primera llamada autenticada lo dirá**: si contesta
> `ERROR_VALIDAR_CREDENCIALES` teniendo el alta, se añaden las dos y se vuelve a probar (es un cambio
> de diez minutos, y las piezas ya están hechas).

---

## 3. Qué está hecho, y funciona

Todo esto está implementado y probado (115 tests en `tests/test_iuws.py` y 68 en
`tests/test_iuws_cliente.py`):

- **Las seis direcciones**, con los parámetros separados por guión bajo tal y como los pide el
  anexo, y sin dejar huecos vacíos (`A__B` no es lo mismo que `A_B`).
- **El catálogo de mensajes**: los 19 códigos del Anexo 1 con su significado, más los cinco
  resultados generales, traducidos al castellano.
- **La lectura de lo que contesta el interfaz**: `OK` / `PARCIAL` / `FALLO`, el detalle por
  actividad, el `idCuaderno`, el estado del proceso y el id de la petición. Se le puede pegar
  una respuesta al sistema y devuelve qué significa cada código, para poder mandarlo a
  soporte sin interpretarlo.
- **El identificador ajeno de cada actividad** (`IdAjena`), que es lo que permite **corregir**
  una actividad ya cargada en vez de duplicarla, y borrarla con el campo `Borrar`.
- **El sobre del mensaje** (`CUADERNO` con `CodigoSIEX`, `CAExplotacion`, `IDTitular`,
  `UnidadGestora`, `CodigoRea`, `IdCuaderno`, `DatosExplotacion`, `ActividadesExplotacion`),
  con los nombres de campo del ejemplo del anexo.
- **El contenido mínimo del CUE, campo por campo**, con el número y el nombre que le da el
  documento técnico SIEX v3.11. Doce bloques, desde los datos de la explotación hasta las
  analíticas, pasando por tratamientos, fertilización, labores, siembra, lo que se vende y las
  medidas preventivas.
- **La prueba de conexión** contra `/IUWS/version`, que se puede hacer **ya**, sin certificado y
  sin estar dado de alta.
- **El cliente del interfaz** (`app/iuws_cliente.py`): las llamadas de verdad, hechas.
- **El estado de la integración**, que se calcula cada vez: qué falta, quién lo tiene que dar
  y a qué correo se pide.

### Lo que se ha comprobado llamando al interfaz de verdad

Esto no sale de ningún documento: se llamó al interfaz y esto es lo que contestó. Está apuntado
en `iuws.COMPROBADO_CONTRA_EL_INTERFAZ` y se puede ver en `GET /api/iuws/comprobar-de-verdad`.

**En la dirección de la comunidad** (`https://servicios.ayg.jcyl.es`, la del Anexo X):

| Llamada | Qué contestó |
|---|---|
| `GET /IUWS/version` | **200** `{"version": "3.11.4"}` |
| `GET /IUWS/` | **401** |
| `GET /IUWS/comunicacion/prueba` | **corta la conexión pidiendo el certificado** |
| `POST /IUWS/crear/` | **401** |
| `GET /IUWS/comprobarEstado/1` | **401** |
| `GET /IUWS/exportar/{...}` | **401** |
| `GET /IUWS/exportarREA/{...}` | **401** |

**En el entorno de integración de FEGA** (`https://sga.entornointegracion.es`, que es la
dirección que trae el programa por defecto): `/IUWS/` contesta **200**, pero **ninguno de los
siete métodos está publicado** en esas direcciones: los seis dan **404**.

Las tres cosas que enseñan esas dos tablas:

1. **Los siete métodos existen** en la dirección de la comunidad. Un 401 quiere decir «existe y
   no me has dicho quién eres»; un 404 querría decir «ahí no hay nada». Ninguno contestó 404.
2. **El certificado lo exige el servidor**, no el programa: la llamada de comunicación ni
   siquiera negocia TLS sin él. Por eso el cliente **no intenta** las llamadas que lo necesitan
   cuando no está configurado.
3. **La dirección por defecto es una trampa.** Quien no sepa que el entorno de integración no
   publica los métodos se pasa la tarde buscando el fallo en su certificado. Por eso la prueba
   de conexión, si la dirección configurada da 404, prueba también la de la comunidad y dice
   cuál contesta.

Y una cuarta, que se encontró con un test: **el interfaz contesta `200` aunque el resultado sea
un error**. El código de verdad va en el cuerpo (`codigoResultado`). Mirar solo el estado HTTP
es lo que hace decir «comunicación establecida» cuando ha contestado
`ERROR_VALIDAR_CREDENCIALES`.

#### Comprobado otra vez el 27/09/2026, con la ruta `/IUWS/api/` y sin certificado

Se volvió a llamar con `scripts/probar_iuws.py` (dos llamadas por dirección, y **ningún dato del
agricultor**). Lo que salió cambia una decisión, así que se apunta:

| Dirección | Llamada | Qué contestó **exactamente** |
|---|---|---|
| `https://sga.entornointegracion.es` | `GET /IUWS/api/version` | **200** · `Versión del descriptor : 3.11.4` |
| `https://sga.entornointegracion.es` | `GET /IUWS/api/comunicacion/PRUEBA` | **200** · `{"resultado":{"codigoResultado":"FALLO","detalleImportacion":[{"codigo":2,"descripcion":"No Autorizado"}]}}` |
| `https://servicios.ayg.jcyl.es` | `GET /IUWS/api/version` | **200** · `{ "version": "3.11.4" }` |
| `https://servicios.ayg.jcyl.es` | `GET /IUWS/api/comunicacion/PRUEBA` | **no hay respuesta**: el saludo TLS se corta (`sslv3 alert handshake failure`) |

**Lo que esto significa, que es lo importante:**

1. **En producción, el certificado se exige para siquiera hablar.** El corte no es un 401: es el
   saludo TLS. Así que presentar de verdad exige un **certificado de cliente de verdad**, y **no vale
   con mandarlo en una cabecera**. Esto descarta cualquier apaño de «mando el certificado y firmo el
   dato» si no hay clave privada utilizable por el programa.
2. **El entorno de integración sí deja llegar hasta el final del flujo.** Allí la llamada entra y la
   respuesta es del **interfaz**, no de la conexión: «No Autorizado». Es decir: **se puede ensayar todo
   el volcado sin certificado**, y eso es lo que se hará antes de tocar producción.
3. **Las dos direcciones están vivas y hablan la misma versión** (3.11.4), así que la ruta `/IUWS/api/`
   es la buena en las dos. La ruta antigua sin `/api/` era la que daba 404 en integración.

**Y de dónde sale la clave privada, que es el nudo de todo:** el certificado que hay en el almacén de
Windows de este ordenador (`CN=PEREZ VELASCO DAVID - 70922320A`, huella
`43E6322F1995F9D4A667274F8FE1A1EA1F70FBBB`, válido hasta el 31/12/2028) tiene la clave privada
marcada como **no exportable**, así que no se puede sacar de ahí. `httpx` va con OpenSSL y **no sabe
usar** una clave que vive en el almacén de Windows.

**Pero eso no quiere decir que no se pueda usar: quiere decir que hay que usarla donde vive.** Y eso
se ha hecho. Ver el apartado siguiente.

#### Comprobado con el certificado de David, desde este ordenador (27/09/2026)

`scripts/probar_iuws_con_certificado.ps1` encuentra el certificado por su NIF (o su huella, que se
pasa por parámetro o en la variable `CUEDIGITAL_CERTIFICADO`), lo pone en el saludo TLS y llama al
interfaz. **No exporta la clave, no la escribe en ningún sitio y no manda ningún dato del
agricultor**: solo hace dos llamadas de lectura.

Lo que contestó, palabra por palabra:

| Dirección | Llamada | Qué contestó **exactamente** |
|---|---|---|
| `https://servicios.ayg.jcyl.es` | `GET /IUWS/api/version` | **200** · `{ "version": "3.11.4" }` |
| `https://servicios.ayg.jcyl.es` | `GET /IUWS/api/comunicacion/PRUEBA` | **200** · `{"resultado":{"codigoResultado":"FALLO","detalleImportacion":[{"codigo":2,"descripcion":"Dominio del certificado no registrado en el sistema"}]}}` |
| `https://sga.entornointegracion.es` | `GET /IUWS/api/comunicacion/PRUEBA` | **200** · `{"resultado":{"codigoResultado":"FALLO","detalleImportacion":[{"codigo":2,"descripcion":"No Autorizado"}]}}` |

**Lo que esto significa, y es lo importante:**

1. **El certificado sirve y se puede usar desde este ordenador.** Antes el saludo TLS se cortaba; con
   el certificado, el servidor de producción **habla** y contesta el interfaz. Lo que hacía falta no
   era exportar la clave (que es lo que no se debe hacer nunca), sino llamar desde Windows, que es
   donde la clave vive.
2. **La explotación de David todavía no está dada de alta.** El interfaz dice, con sus palabras,
   `Dominio del certificado no registrado en el sistema`. Eso no es un fallo del programa ni del
   certificado: es que falta el alta. Está contado en [§6](#6-el-formulario-de-solicitud-de-acceso-castilla-y-león).
3. **En el entorno de integración de FEGA su certificado no vale** (contesta «No Autorizado»), y es
   lo esperable: es un entorno de pruebas y allí no está dado de alta nadie con un certificado de
   producción. Queda apuntado para que nadie pierda una tarde probando allí con el certificado bueno.
4. **No se ha presentado nada.** Estas dos llamadas son de lectura, la segunda es la que el propio
   interfaz pone para comprobar credenciales. Presentar un cuaderno es otra cosa, y no se puede
   hacer mientras el alta no esté hecha. **No se va a decir que se ha presentado.**

#### Vuelto a comprobar el 28/09/2026 (por si el alta había llegado)

Se repitieron las llamadas al día siguiente, con el mismo certificado y **sin mandar ningún dato**: la
idea era descartar que el alta se hubiera concedido entre medias sin que nadie lo dijera. **No ha
cambiado nada**, y esto es lo que contestó, palabra por palabra:

| Dirección | Llamada | Qué contestó **exactamente** |
|---|---|---|
| `https://servicios.ayg.jcyl.es` | `GET /IUWS/api/version` | **200** · `{ "version": "3.11.4" }` |
| `https://servicios.ayg.jcyl.es` | `GET /IUWS/api/comunicacion/PRUEBA` | **200** · `{"resultado":{"codigoResultado":"FALLO","detalleImportacion":[{"codigo":2,"descripcion":"Dominio del certificado no registrado en el sistema"}]}}` |
| `https://sga.entornointegracion.es` | `GET /IUWS/api/version` | **200** · `Versión del descriptor : 3.11.4` |
| `https://sga.entornointegracion.es` | `GET /IUWS/api/comunicacion/PRUEBA` | **200** · `{"resultado":{"codigoResultado":"FALLO","detalleImportacion":[{"codigo":2,"descripcion":"No Autorizado"}]}}` |

Y la otra mitad de la presentación, que tampoco toca la red, se volvió a comprobar el mismo día:
`firmar_con_el_certificado.ps1 -Texto <NIF> -Comprobar` firmó con la clave del almacén y la firma **se
verificó** con la clave pública del certificado (`True`). Es decir: **las dos piezas que se pueden
probar sin el alta están probadas y siguen funcionando**; lo único que falta es el alta.

**Un detalle del guion que costó un rato y conviene saber:** `-Rutas` es una lista, así que se pasa
con **comas entre cadenas**, no dentro de una sola:

```powershell
# Bien: dos rutas
-Rutas "/IUWS/api/version","/IUWS/api/comunicacion/PRUEBA"
# Mal: una ruta que es «/a,/b», y la llamada contesta 401 (parece un problema de permisos y no lo es)
-Rutas "/IUWS/api/version,/IUWS/api/comunicacion/PRUEBA"
```

---

## 4. Qué NO está hecho, y por qué no se ha inventado

**El JSON todavía no se manda.** El **formato ya no es el problema**: el descriptor oficial y su
esquema JSON están en `data/iuws_fuentes/` (v3.11.4), extraídos del Anexo VI del FEGA y
guardados sin tocar, y el paquete se comprueba contra el esquema con `jsonschema` **antes** de
llamar al servidor. Lo que lo impide son **los códigos numéricos de los catálogos**
(`Producto: 1`, `Unidad: 3`, `JustAct: 20`…), y esto está medido, no supuesto:

- El esquema oficial declara **528 tipos y ninguno admite vacío**: no hay un solo `null` en todo
  el esquema. Un campo obligatorio que no se tenga **no se puede dejar en blanco**.
- El descriptor marca **175 campos obligatorios**, y en su columna de observaciones dice
  **contra qué catálogo** valida cada uno. Sin ese catálogo, ese bloque no se puede armar de
  forma que valide.
- El portal público de SIEX publica la **estructura** de sus 287 catálogos (141 visibles) y se
  puede consultar sin certificado en `https://www3.sede.fega.gob.es/bdcsixpor/tablas/configJson`,
  pero **los datos de cada tabla están detrás de un captcha**: ese fichero trae las columnas de
  cada catálogo, no sus filas.

Y el aviso del anexo sigue ahí, en la versión 3.11.4:

> *«Los ejemplos incluidos en los siguientes apartados pueden no corresponderse con la v2.6
> del descriptor, por lo que deben tomarse como tales ejemplos, ya que aún no se pueden
> generar con dicha estructura.»*

Es decir: **el anexo avisa de que sus ejemplos van por detrás del descriptor**. Por eso no se
copian los ejemplos — se usa el descriptor. Copiar los ejemplos sería construir un volcado
sobre un formato que el propio FEGA avisa de que puede no ser el bueno.

**Lo que se hace en su lugar**:

1. Se vuelca el cuaderno **en el orden de campos del contenido mínimo**, con el número y el
   nombre oficial de cada campo. Eso se puede cotejar línea a línea con el documento técnico.
2. Los campos cuyo valor es un **código de catálogo salen vacíos y marcados** (`c6_catalogo:
   true`), no con un número inventado. Un código mal puesto no da error al mandarlo: guarda
   el producto equivocado.
3. El paquete dice **en sí mismo** que no es el fichero que se manda a la Junta
   (`formato`, `aviso`), para que nadie lo mande creyendo que vale.

### 4.1 El sobre ya cumple el contrato (y tres cosas que estaban mal)

El sobre exterior (`CUADERNO`, `CAExplotacion`, `IdTitular`, `UnidadGestora`, `CodigoRea`,
`IdCuaderno`) **sí se puede comprobar contra el esquema oficial**, y se comprueba. Al cotejarlo
aparecieron tres fallos que venían de copiar el **ejemplo** del anexo en vez del **esquema**:

| Lo que estaba | Lo que dice el esquema | Consecuencia |
|---|---|---|
| `IDTitular` | `IdTitular`, **obligatorio** | El campo obligatorio no estaba: el sobre **no podía validar nunca** |
| `IdCuaderno` como texto (`"2026"`) | `integer` | Tampoco validaba |
| — | `CodigoSIEX` y `CodigoRea`: **exactamente 14 caracteres** | Un código corto (`933`) se rechaza |

Los tres están corregidos y fijados con tests. **La lección vale para todo lo que venga:** el
ejemplo del anexo no es el contrato; el contrato es el descriptor y su esquema.

### 4.2 La tabla de campos del descriptor (y qué pide de verdad)

El descriptor trae una hoja, `EstructuraCuadernoWS`, que es **la especificación de mapeo**: por
cada campo dice si es obligatorio, de qué tipo es y **contra qué catálogo** valida. Está
convertida en datos con `scripts/sacar_campos_del_descriptor.py` y se lee desde
`backend/app/iuws_descriptor.py`, para no mapear a ojo. Sale de ahí:

- **107 bloques y 402 campos, de los que 175 son obligatorios.**
- **40 catálogos** distintos que el descriptor pide por su nombre. Los que más campos tocan son
  `Unidades de Medida` (6), `Eficacia del tratamiento` (3), `Justificación de la Actuación` (3),
  `Plagas` (3), `Enfermedades` (3) y `Producto`/`Productos` (3 entre los dos).
- **`Eficacia` es obligatorio** y sale del catálogo `Eficacia del tratamiento`. Era una de las
  lagunas apuntadas («no existe catálogo oficial»): el descriptor **sí lo pide**. Lo que no se
  sabe —y por eso sigue en la lista de lo que falta— es si SIEX publica sus valores.

> **Aviso que ahorra media tarde:** el descriptor oficial **omite la llave `{`** en 14 cabeceras
> de bloque (entre ellas `TratamFito`, `SiembraPlantacion` y las listas de plagas y enfermedades).
> Una tabla que se saque del Excel mirando solo la llave **pierde esos bloques** y cuelga sus
> campos del bloque de arriba. Pasó, y llegó a estar escrito en estos documentos que «el descriptor
> no tiene `TratamFito`», que era falso. La marca fiable es la **columna de ocurrencia** (`0..n`,
> `1..n`), que solo tienen los bloques. Hay un test que exige que cada bloque del esquema aparezca
> en la tabla. Y como dato: los dos documentos **coinciden** en los bloques; el descriptor trae uno
> de más, `ActividadAgraria`.

Y lo que el descriptor **no** hace: no traduce el nombre del catálogo al identificador de la
tabla de SIEX. Se comprobó buscando los 287 identificadores del portal dentro del descriptor y
**solo aparecen cuatro** nombres de registros externos (`ASPAFITOS`, `MDF`, `REGANIP`, `ROPO`).
Así que emparejar «Catálogo de Producto» con la tabla `PRODUCTOS` por parecido de nombre sería
adivinar, y no se hace: esa correspondencia la tiene que dar FEGA o los valores.

### 4.3 El mapeo del bloque de tratamientos, campo por campo

El bloque de los tratamientos fitosanitarios (`TratamFito`) está mapeado entero en
`backend/app/iuws_mapeo.py`: **11 campos oficiales, 8 obligatorios**, y cada uno con su estado.
Los estados no son un adorno: separan **lo que depende de FEGA** de **lo que depende de
nosotros**, que es lo que decide si hay que escribir un correo o una pantalla.

| Estado | Campos | De quién depende |
|---|---|---|
| **Se puede ya** | `IdAjenaTratamFito`, `FechaInicio`, `FechaFin`, `HoraTratamiento`, `Observaciones`, `IdentificadorAplicador` | De nadie |
| **Hace falta catálogo** | `ProblematicaFito` (plagas), `Justificaciones`, `Eficacia` | **De FEGA** |
| **A medias** | `ProductosFito` | De nosotros: falta un dato que no preguntamos |
| **No lo tenemos** | `DGCs` (en qué parcela) | De nosotros: no lo recogemos |

Cuatro catálogos hacen falta para este bloque, y **los cuatro los nombra el descriptor**
(está comprobado con un test, para que nadie se invente un catálogo): `Plagas`,
`Justificación de la Actuación`, `Eficacia del tratamiento`, `tipos de producto`.

**Cerrar lo que dependía de nosotros movió dos campos de sitio** (ronda 23): el cuaderno ahora
pregunta **si se aplicó a mano** (que el interfaz exige como `AplicacionManual`) y **cómo de bien
funcionó** (el campo `Eficacia`, también obligatorio). Con eso `IdentificadorAplicador` pasó a
«se puede ya» —un campo obligatorio menos bloqueado— y `Eficacia` pasó de «no lo tenemos» a
«hace falta catálogo»: el dato ya se recoge, lo que falta es el código. La lista de respuestas
que se le ofrecen al agricultor («muy bien», «bien», «regular», «mal») es **nuestra** y está
marcada como tal; la equivalencia con los códigos oficiales **no se supone**.

**Y tres cosas que estaban mal y ya se sabe por qué:**

1. **Las fechas no van en ISO.** El esquema pide `minLength: 10, maxLength: 10` y un patrón
   donde el primer grupo es el **día**. `2026-05-01` mide 10 caracteres y **no cumple el
   patrón**; `01/05/2026` sí. Se comprobó contra el validador del esquema, no a ojo.
2. **`IdAjena…` es un número.** El `CD-70922320A-T-14` de la aplicación es un buen
   identificador para rastrear y **no vale** para el interfaz: el campo es `integer` de hasta
   10 dígitos. Para el interfaz se manda el número de la fila, que no cambia nunca.
3. **El esquema no solo tiene tipos: tiene `oneOf`.** Hay cinco. La que importa aquí: el equipo
   de aplicación tiene que llevar **uno** de estos tres —número de ROMA, número de REGANIP o
   nuestro propio identificador de equipo—, ni los tres ni ninguno. Se descubrió construyendo
   un ejemplo completo contra el validador, no leyendo el Excel.

**Y lo que no se puede saltar:** hoy un tratamiento **no puede validar**, y no por la
estructura. De los 8 campos obligatorios, **4 se pueden poner** (el identificador, las dos fechas
y el del aplicador) y los otros **4 no**: uno espera un catálogo de FEGA y tres necesitan datos
que el cuaderno todavía no recoge o no sabe traducir a código. El esquema **no admite un campo
vacío**, así que no se manda el bloque a medias. Un test lo demuestra por los dos lados: con los
códigos puestos el cuerpo **valida** (o sea, la forma que armamos es la correcta), y sin ellos el
validador dice exactamente **qué** falta.

### 4.4 Los catálogos: cuáles ya tienen tabla localizada y cuáles hay que preguntar

El descriptor dice **cómo se llama** cada catálogo («Catálogo de Eficacia del tratamiento»), no
**qué tabla** hay que mirar para sacar los códigos. Y sin saber qué tabla es, no se puede ni
pedir los valores.

SIEX publica, **sin certificado**, la lista de sus **287 catálogos** con sus nombres y sus
columnas (se baja con `backend/scripts/bajar_catalogos_siex.py` a `data/siex_catalogos.json`).
Cruzando los dos nombres sale esto, y se ve en `GET /api/iuws/estado`, apartado
`catalogos_de_siex`:

- **15 de los 40** catálogos que pide el descriptor tienen una tabla de SIEX **con el nombre
  exactamente igual** (comparando sin mayúsculas ni acentos), y **las 15 son públicas**. Por
  ejemplo: `Eficacia del tratamiento` → `EFICACIA_TRATAMIENTO`, `Unidades de Medida` →
  `UNIDADES_MEDIDA`, `Justificación de la Actuación` → `JUSTIFICACION_ACTUACION`, `Enfermedades`
  → `ENFERMEDADES`, `Sistema de Riego` → `SIST_RIEGO`.
- **Los otros 25 no coinciden**, y no se emparejan.

> **Aquí está la decisión que importa:** no se empareja **por parecido**. El descriptor pide
> «tipos de producto» y en SIEX hay una tabla llamada «tipo de producto fitosanitario»
> (`TIPO_PRODFITO`); se parecen mucho y **no se puede afirmar que sean la misma**. Afirmarlo sería
> inventar, y en un volcado oficial un catálogo equivocado no da error: guarda el producto
> equivocado. Hay un test que recorre las correspondencias una por una y exige que los dos
> nombres sean iguales, para que nadie meta un emparejado «a ojo».

Lo que sigue faltando son **los valores**: el portal publica la estructura de las tablas y los
datos de cada tabla están detrás de un captcha. Así que el recado para FEGA ya no es «mándame los
catálogos», es: **«los valores de estas tablas»**, y las 15 que se saben van con su nombre y su
identificador.

### 4.5 La lista de la compra completa: el mapa del cuaderno entero

`GET /api/iuws/estado`, apartado `mapa_del_cuaderno`, dice **qué pide la Junta en cada uno de los
18 bloques** y con qué catálogo. Y no está escrito a mano: sale del esquema (qué campos son
obligatorios) y del descriptor (contra qué catálogo valida cada uno) **cada vez que se pregunta**,
así que no se puede quedar viejo ni inventado.

De ahí sale la cuenta que importa:

| | |
|---|---|
| Bloques | **18** (3 de datos de la explotación y 15 de actividades) |
| Campos obligatorios | **113** |
| Catálogos que hacen falta para esos campos | **19** |
| De esos, con tabla de SIEX ya localizada | **7** |
| Bloques que obligan a decir **en qué parcela** pasó | **9** |

Dos detalles que salieron al construirlo y que conviene saber:

- **Un contenedor no pide un catálogo: pide los de dentro.** `ProblematicaFito` no necesita «un»
  catálogo; necesita las **cuatro** listas que el descriptor declara dentro (plagas, enfermedades,
  malas hierbas y reguladores del crecimiento). Un mapa que solo mirara el campo diría que no hace
  falta ninguno, y la lista saldría incompleta justo donde más bloquea.
- **Cuando el descriptor no dice el catálogo de un campo pero sí lo dice en otro bloque**, se
  apunta como información, **no como conclusión**. `Riego.SistemaRiego` no dice de dónde sale; en
  `Fertilizacion.Fertirrigacion.SistemaRiego` sí: «Sistema de Riego». Que sea el mismo catálogo es
  lo más probable y no se puede afirmar, así que se dice para poder ir a preguntar.

Y el bloqueo que alcanza a más sitios a la vez no es un catálogo: son **las parcelas**. Nueve de
los dieciocho bloques obligan a decir en qué parcela pasó cada cosa, y eso va en el código de la
DGC, que es lo único del bloque de tratamientos que el cuaderno todavía no sabe rellenar.

### 4.6 De qué tabla del cuaderno sale cada bloque oficial

El mapa dice también **de dónde sale cada bloque**, y esto no es una interpretación: es un dato
sobre nuestro programa, y un test comprueba que las tablas que se nombran existen de verdad.
Sirve para saber dónde está el trabajo:

| Tabla del cuaderno | Bloques oficiales que cubre |
|---|---|
| **`Labor`** | **7**: riego, labores culturales, pastoreo, cubierta del suelo, siembra y plantación, semilla tratada y cosecha |
| **`TratamientoFitosanitario`** | **3**: tratamientos, postcosecha y tratamiento de instalaciones |
| `RegistroFertilizacion`, `PlanAbonado`, `Analitica`, `VentaDeCosecha`, `MedidaPreventivaDeclarada`, `Parcela`, `ParcelaCultivo` | 1 cada una |

Es decir: **de los 18 bloques, 10 salen de dos tablas**. El bloque de las labores concentró
el mayor trabajo de mapeo, aunque el cuaderno ya guarda el agua, la
semilla, el marco y la densidad— sino porque hay que traducir cada tipo de labor a los campos de
su bloque.

**Y el único bloque del que no tenemos nada es el de la energía** (`EnergiaUtilizada`), que está
así a propósito: la app oficial de Castilla y León tampoco lo pide.

### 4.7 Lo que ya está mapeado a mano, campo por campo

Los **18 bloques** tienen clasificados todos sus campos obligatorios. Eso —saber de qué dato nuestro sale cada campo— no lo
dice ningún documento: hay que hacerlo uno a uno. De sus **113 campos obligatorios, 61 tienen
fuente directa y tipo compatible** (comprobado el 24/09/2026; el número sube cada vez que el
cuaderno recoge un dato más). El detalle de los otros 52 se puede consultar en
`GET /api/iuws/estado`, apartado `mapeo_de_los_bloques`; se distinguen códigos oficiales,
datos que la aplicación aún no pregunta y conversiones por confirmar. El envío completo sigue
pendiente. Parte de los campos opcionales aún requiere correspondencia manual.

**Y aquí está el hallazgo de esta parte del cuaderno: lo que falta no son catálogos, son
preguntas.** Los bloques que salen de `Labor` —cosecha, pastoreo, cubierta y labores culturales—
necesitan **una sola lista de códigos** entre los cuatro (la de tipo de labor); todo lo demás que
falta son **cosas que la aplicación no pregunta**:

- **Cosecha**: si se sacó semilla, si se sacaron plantas, si se dejó sin cosechar por motivos
  ambientales y si los restos se dejaron en el suelo. Cuatro preguntas de sí o no.
- **Pastoreo**: si los animales eran de terceros o de la explotación. Dos preguntas de sí o no.
  ✅ **Ya se preguntan**: el pastoreo pasó de 3 a **5 de sus 6 campos obligatorios**, y lo único
  que le queda es el código de la parcela.
- **Cubierta**: qué cubre el suelo y las dos anchuras (la de la cubierta y la libre de la copa).
- **Labores**: si los restos del desbroce y de la poda se dejaron en el suelo.

Eso **no depende de nadie de fuera**. Es la lista de pantallas que hay que escribir, y es lo que
el apartado siguiente del documento de la Junta llama «lo que depende de nosotros».

Tres cosas más que han salido al mapear, y que son **diferencias entre los dos documentos
oficiales** (están declaradas en el módulo, con su motivo, y hay tests que exigen que sean
**esas** y ninguna más):

- **`Cosecha.GestionInsumos`**: el descriptor la marca como **obligatoria** y el esquema **no la
  declara**. Como el esquema es lo que se valida antes de mandar, no se puede poner en el cuerpo…
  pero el descriptor la pide, así que hay que preguntarlo antes de fiarse de que con el esquema
  basta.
- **`LaboresCulturales.TipoLabor`**: hace falta un código y **el descriptor no cita ningún
  catálogo** para ese campo, así que no se puede ni saber de dónde salen los códigos.
- **`UsoSemillaTratada.IdAjenaSiembraPlant`**: el descriptor permite enlazar la semilla con la
  siembra, pero el esquema omite este campo opcional. El cuaderno tiene el identificador;
  no se envía hasta saber qué documento manda.

Y una sola convención del descriptor se ha dado por buena, y se da porque está **escrita**:
`SiembraPlantacion` dice «1 Siembra 0 Plantación» y `CosechaSiega` dice «cosecha/recolección (1) o
siega». Al guardar la **descripción** de cada campo del descriptor se puede comprobar que están
ahí, en vez de dejarlo en un «me suena que es así». Los demás códigos **no se suponen**.

No quedan bloques sin correspondencia manual en `GET /api/iuws/estado`. Esto no implica que
se pueda generar el paquete oficial: los estados de cada campo muestran lo que falta.

Los once bloques incorporados al mapeo incluyen `MedidaPreventivaCultural`, `Analitica`,
`ComercializacionVD`, `UsoSemillaTratada`, `PlanAbonado`, altas y cambios de DGC,
postcosecha, instalaciones, fertilización y energía. Entre los 18 bloques hay 113 campos
obligatorios; 61 tienen fuente directa en el cuaderno y tipo compatible con el esquema. Esto no
significa que se puedan enviar los
bloques completos: las medidas, el material analizado, el producto vegetal y la unidad de venta
siguen necesitando códigos oficiales. El [Anexo V de FEGA](https://www.fega.gob.es/sites/default/files/files/document/2025.11.20-ANEXO_V_Definicion_de_variables_3.11_CORRECCION_ERRORES_PUBLICACION.xlsx)
(definición de variables 3.11, corrección de errores publicada el 20/11/2025) tiene dos hojas,
REA y CUE, con definiciones y obligatoriedad; no contiene las filas de valores de los catálogos.

**Comprobación pendiente al mapear `PlanAbonado`:** el esquema oficial pide `NecesidadUFP2O5`
y `NecesidadUFK2O` en kg/ha, mientras la pantalla actual pregunta «Fósforo (P)» y «Potasio
(K)». Antes de asociar esas columnas hay que confirmar si lo guardado representa los elementos
o sus óxidos y aplicar, si procede, una conversión documentada. Una copia directa del número
podría cambiar el significado del plan.

---

## 5. Lo que hace falta, y de quién depende

**Los dos bloqueos externos —los valores de los catálogos y el alta con el certificado— están
con su dueño, su estado, su evidencia y su criterio de cierre en
[`FUENTES_OFICIALES_PENDIENTES.md`](FUENTES_OFICIALES_PENDIENTES.md), apartado «Los dos bloqueos
externos: lista canónica». Aquí no se repiten.** De David dependen además el nombre comercial, el
dominio y el servidor, y el código SIEX de cada finca.

#### Y una decisión que solo puede tomar él: de dónde sale la clave privada

**Resuelto el 27/09/2026, y no hizo falta ninguna decisión.** Se comprobó que el certificado del
almacén de Windows —`CN=PEREZ VELASCO DAVID - 70922320A`, que caduca el 31/12/2028— **tiene clave
privada y es utilizable desde este ordenador**, aunque esté marcada como **no exportable**. La
diferencia es importante: no se puede *sacar* de ahí (y no se debe: una clave exportada es una clave
que se puede copiar), pero **sí se puede usar donde vive**. Lo hace
`scripts/probar_iuws_con_certificado.ps1`: Windows firma el saludo TLS por dentro y el programa nunca
ve la clave. La llamada al interfaz de producción **funciona** desde ahí (ver la tabla de arriba).

Lo que queda, entonces, no es una decisión suya sobre la clave: es **el alta de su explotación**, que
es lo que el interfaz está diciendo con sus palabras (`Dominio del certificado no registrado en el
sistema`).

| Salida | Estado |
|---|---|
| **1. El fichero original `.pfx` / `.p12`** | **Ya no hace falta.** Sería útil solo si algún día se quiere presentar desde otro ordenador o desde un servidor; entonces el fichero y su contraseña irían **fuera del repositorio**, en variables de entorno |
| **2. Presentar desde Windows (schannel)** | **Es lo que funciona**, y está hecho y probado hasta donde el alta permite: `scripts/probar_iuws_con_certificado.ps1`. Falta que el programa (Python) llame a esa pieza cuando toque presentar de verdad |
| **3. Presentar desde el navegador** | Sigue siendo la salida de emergencia: se genera el fichero y lo sube él en el Cuecyl con su certificado. Es honesta, pero no es «presentar por el interfaz» desde el programa |

**Mientras el alta no esté hecha no se presenta nada por el interfaz**, y no se dirá que se ha
presentado. Lo que sí se ha hecho, y con su certificado, es **comprobar qué contesta** (ver la tabla de
arriba) y **ensayar todo el flujo en el entorno de integración**, que no exige certificado para llegar
a la aplicación.

### De cada agricultor

| Qué | Para qué |
|---|---|
| **La autorización del titular** a la entidad habilitada (Anexo VIII/IX de SIEX) | El interfaz solo deja cargar cuadernos de explotaciones autorizadas |

---

## 6. El formulario de solicitud de acceso (Castilla y León)

**Esto es el siguiente paso para presentar, y está medido, no supuesto.** El 27/09/2026, con el
certificado de David puesto desde su ordenador, el interfaz de producción contestó
`Dominio del certificado no registrado en el sistema`; **y el 28/09/2026 se volvió a preguntar para
descartar que el alta hubiera llegado sin avisar: contesta lo mismo.** Es decir: la conexión y el
certificado van bien, y lo que falta es que su explotación (su dominio, con ese certificado) esté
**dada de alta**.

Se manda a **los dos correos**, firmado electrónicamente. Los ocho campos son obligatorios:

1. Nombre de la Empresa desarrolladora
2. NIF de la empresa desarrolladora
3. **Nombre del software comercial**
4. **CN del certificado de dominio** con el que se comunicará con el Servicio Web
5. Nombre de la persona de contacto
6. Teléfono de la persona de contacto
7. Email de la persona de contacto
8. URL página Web Empresa Desarrolladora

Firmarlo supone aceptar la declaración responsable que va en la página siguiente del
formulario (uso del entorno solo para integrar la herramienta, sin ingeniería inversa, sin
crear obras derivadas, sin uso fraudulento).

---

## 7. Cómo se configura, cuando llegue el momento

Todo por variables de entorno. **Nada de esto se escribe en el repositorio**: el nombre
comercial y el CIF identifican a la empresa y el certificado es una clave privada.

```bash
CUEDIGITAL_IUWS_BASE=https://servicios.ayg.jcyl.es   # o el entorno de integración
CUEDIGITAL_IUWS_APP=Nombre comercial del software
CUEDIGITAL_IUWS_CIF=B12345678                        # empresa habilitada
CUEDIGITAL_IUWS_DOMINIO=cuedigital.ejemplo.es        # el CN del certificado
CUEDIGITAL_IUWS_CERTIFICADO=/ruta/al/almacen.p12     # el certificado de dominio
CUEDIGITAL_IUWS_ALTA=alta-2026-0001                  # lo que devuelve la Junta
```

Y el descriptor, copiando la plantilla y rellenándola:

```bash
cp data/iuws_descriptor_cue.ejemplo.json data/iuws_descriptor_cue.json
# y rellenar los nombres de campo y los catálogos desde BdcSix-DS-DiseñoCUE.xlsx
```

Mientras falte cualquier pieza, `GET /api/iuws/estado` la lista y **el sistema no llama al
interfaz** para nada que necesite certificado. Hacer una llamada sin el certificado que el
interfaz exige solo sirve para que alguien vea un error que no puede arreglar.

La excepción es la prueba de versión: el método `version` **no está securizado**, así que se
puede llamar hoy, con `?llamar=1`, sin tener nada. Es la que separa dos problemas que se
confunden todo el tiempo: «no hay camino hasta la Junta» y «la Junta no me reconoce». Si esa
llamada contesta 200, el camino está bien y lo que falta son las credenciales.

---

## 8. Cómo se comprueba que funciona

```bash
# El estado de la integración, con lo que falta
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/iuws/estado

# Qué campos se vuelcan, con su número de campo del documento
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/iuws/contenido

# El paquete con los datos de la finca
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/iuws/paquete.json -o iuws.json

# La prueba de conexión con el interfaz. Sin `?llamar=1` no toca la red: informa y espera.
curl -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:8000/api/iuws/version?llamar=1"

# Qué se ha comprobado contra el interfaz de verdad, método por método
curl http://127.0.0.1:8000/api/iuws/comprobar-de-verdad

# Traducir una respuesta del interfaz
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"respuesta": {"resultado": {"codigoResultado": "PARCIAL", "detalleImportacion": [{"codigo": 6}]}}}' \
  http://127.0.0.1:8000/api/iuws/leer-respuesta
```

Y para preguntarle al interfaz **a mano, desde la consola**, sin pasar por la aplicación (que es como
se comprobó la tabla del apartado 3):

```bash
cd backend
../.venv/Scripts/python.exe scripts/probar_iuws.py
```

Hace dos llamadas por dirección —la versión y el token, **sin certificado y sin ningún dato del
agricultor**— y dice, con las palabras del error, si el corte está en la conexión o en la aplicación.
Es lo que se ejecutó el 27/09/2026.

Los tests del cliente (`tests/test_iuws_cliente.py`, 68 tests) **no salen a internet**: inyectan
un transporte de mentira, así que prueban la dirección, las cabeceras, el cuerpo y la lectura de
la respuesta sin red. La única prueba que llama de verdad es la de humo, que es donde toca.

---

## 9. Lo que falta para poder mandar un cuaderno

El cliente HTTP está escrito, y la parte que se puede probar está probada. **El formato también
está resuelto**: el descriptor y el esquema oficiales están en el repositorio y el paquete se
valida contra el esquema antes de salir. Lo que falta no es programa:

1. **Los dos bloqueos externos**: los valores de los catálogos y el alta con el certificado. Su
   dueño, su estado, su evidencia y su criterio de cierre están en
   [`FUENTES_OFICIALES_PENDIENTES.md`](FUENTES_OFICIALES_PENDIENTES.md), apartado «Los dos bloqueos
   externos: lista canónica»; aquí no se repiten.
2. **El código SIEX de cada explotación**, que lo pone cada agricultor en «Mi finca».
3. **La autorización del titular** a la entidad habilitada.

### El trabajo que queda

1. **El traductor de cada bloque**: `cada fila del paquete` → `el JSON del descriptor`. Esto sí
   se puede escribir ya, bloque por bloque, contra el descriptor y el esquema oficiales; lo que
   **no** se puede es inventar los códigos de catálogo que falten.
2. **Cargar los catálogos** en cuanto haya una vía oficial para sus valores. Los que no se
   publiquen se quedan vacíos y marcados, y se dice cuáles son.
3. ~~**Firmar el parámetro `data-signed`**~~ **Hecho el 27/09/2026** (y vuelto a comprobar el
   28/09/2026), y sin exportar ninguna clave: se firma con el certificado **donde vive**. Está abajo,
   en «Firmar sin sacar la clave del almacén». **Lo que queda es decidir si hay que mandarlo**: hay dos
   lecturas del anexo (contadas en «Cómo se autentica, en corto»), la del programa hoy manda el JWT y
   nada más, y las dos piezas de la otra lectura ya están escritas y probadas. Lo dirá la primera
   llamada autenticada, en cuanto el alta esté hecha.
4. **Probar contra el entorno de integración**, bloque por bloque, mirando el `comprobarEstado`.
   Hasta hoy **no se ha hecho ni una llamada autenticada**: eso está sin verificar. (Lo que sí se ha
   hecho con el certificado de David son las dos llamadas de lectura de arriba.)
5. **Pedir el alta del dominio**: es lo que el interfaz contesta que falta. El estado de esa
   petición está en
   [`FUENTES_OFICIALES_PENDIENTES.md`](FUENTES_OFICIALES_PENDIENTES.md), `BLOQUEO-ALTA-DOMINIO`.

### Firmar sin sacar la clave del almacén

Esto resuelve la que parecía la decisión más difícil del proyecto, así que se cuenta entera.

El certificado de David está en el almacén de Windows y su clave privada está marcada como **no
exportable**. Durante varias rondas eso se leyó como un muro: «no se puede usar desde el programa».
Y no es eso: **no se puede *sacar*, pero sí se puede *usar donde vive***. Windows firma por dentro y
el programa solo recibe la firma. Eso es mejor que exportar la clave, no peor: una clave exportada es
una clave que se puede copiar, y aquí no hay ningún fichero con la clave.

- **`backend/scripts/firmar_con_el_certificado.ps1`** firma un texto (el NIF) con RSA, PKCS#1 v1.5 y
  SHA-256, que es lo que espera el interfaz, y saca la firma en base64. **No exporta** la clave ni el
  certificado, **no escribe ficheros** y **no toca la red**. Trae un modo `-Comprobar` que firma y
  verifica la firma con la clave pública.
- **`iuws_cliente.datos_firmados()`** lo usa solo: el firmador que se le pasa → `cryptography` con un
  `.pem` configurado (por si algún día se presenta desde otro ordenador) → **el certificado del
  almacén de Windows**. Si no puede firmar por ninguno de los tres caminos, devuelve «no se pudo» y
  **nunca una firma inventada**.
- **El certificado se identifica por variable de entorno** (`CUEDIGITAL_CERTIFICADO`, con el NIF o la
  huella). En el repositorio no hay ningún dato personal.

Comprobado el 27/09/2026, en local y sin red: se firmó el NIF con el certificado de David y la firma
**se verificó** con su clave pública (`La firma se comprueba con la clave publica del certificado:
True`). Las pruebas del proyecto **no llaman al script de verdad** —firmarían con la clave privada de
David— : comprueban que no puede hacer daño y que el programa lo llama bien, con un script de mentira.

**Una decisión que hay que entender:** no se ha añadido ninguna librería de criptografía a Python, y
sigue sin hacer falta. Lo que hacía falta era dejar de intentar leer la clave y firmar donde está.

Fingir el resto sería peor que no tenerlo: un volcado inventado se rechaza con
`ERROR_VALIDAR_CAMPO` y, mientras tanto, habría quedado en el repositorio un formato que nadie
ha comprobado. El paquete que hoy sí se puede generar dice en sí mismo que **no** es ese
fichero, para que nadie lo mande creyendo que vale.
