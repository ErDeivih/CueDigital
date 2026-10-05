# T01 — Revisión ruta por ruta de las rutas que no piden vale de sesión

**Qué es este documento.** La revisión, una por una, de **las 24 rutas de la API que hoy se pueden
llamar sin identificarse**. No es un inventario nuevo: es la revisión del que ya existe
(`INVENTARIO_T01_SERVIDOR.md` §2.2 y §2.3), hecha ruta por ruta y **contra el código**, con la
pregunta concreta de qué devuelve cada una, qué cambia, de dónde saca la finca, quién puede gastar
recursos ajenos con ella y qué se rompe si se cierra.

**De dónde salen los datos.** De leer el código. La lista de rutas se ha sacado con el árbol
sintáctico de Python (decoradores `@router.*` y firma de cada función) sobre los 19 ficheros de
`backend/app/routers/`, y los que llama cada una se han buscado en `backend/web/**/*.js`
(sin `vendor/`), en `backend/scripts/humo.py`, en `backend/tests/**` y en `docs/`. Todo lo que dice
aquí lleva fichero y número de línea.

**Lo que NO se ha comprobado, y conviene que se sepa:**

- **No se ha abierto la base de datos real** (`backend/cuedigital.db`). Lo que se dice de lo que se
  escribe es lo que el código *puede* escribir, no lo que hay dentro. No se ha contado ninguna fila.
- **No se ha arrancado ningún servidor** y **no se ha hecho ni una petición a `127.0.0.1:8000`**.
  Los códigos de estado salen de leer el código, no de llamarlo.
- **No se ha salido a internet**: lo que hace cada llamada saliente se ha leído en `sigpac.py`,
  `iuws_cliente.py` y `catalogos.py`, no probado contra el SIGPAC ni contra la Junta.
- **No se ha ejecutado la suite de pruebas** (el encargo lo permitía; se ha preferido no hacerlo
  porque no se toca ni una línea de código y las pruebas que cito se han leído enteras).
- **No se ha mirado qué límites pone el servidor de delante** (nginx u otro): no hay ni un fichero de
  despliegue en el repositorio (ver §5.2), así que de eso **no se puede decir nada**.
- **Cuándo se ha leído.** La lectura del código es del **02/10/2026, entre la 01:00 y la 01:35**. En
  ese mismo rato hay ficheros del repositorio con fecha de modificación de esa madrugada
  (`backend/app/models.py` a las 01:15, `docs/INVENTARIO_T01_SERVIDOR.md` a la 01:01, y `.pyc` de una
  ejecución de `pytest`), así que **puede haber otro proceso escribiendo a la vez**. Si un número de
  línea no cuadra al comprobarlo, míralo antes de dar el desfase por bueno: es el aviso que ya dejó
  escrito `SEGUIMIENTO_IMPLEMENTACION_CRM.md:253-258`.

> **Las 24 no son 24 agujeros.** La mayoría son catálogos oficiales, textos o la puerta de entrada de
> la cuenta, y **cuatro de ellas tienen que seguir siendo públicas por obligación** (una pantalla que
> no puede mandar vale, los textos que hacen falta *antes* de entrar). Este documento las clasifica
> una por una justamente para no tratarlas en bloque. La frase que resume el resultado: **hoy no hay
> ninguna ruta sin sesión que devuelva datos de una explotación**, pero sí hay **cuatro** que deberían
> pedir sesión sin que se rompa nada, **siete** que necesitan un límite y **cuatro** que son
> herramienta de integración, no pantalla de agricultor.

---

## 1. El recuento, y en qué se desvía el inventario

### 1.1. La cuenta

| Qué | Cuántas |
|---|---|
| Rutas declaradas en `backend/app/routers/*.py` | **170** |
| De esas, sin `UsuarioActual` ni `ExplotacionActual` | **24** |
| Rutas sin sesión declaradas en `main.py` (`/health`, `/api`) | **2** |
| **Total de rutas propias sin sesión** | **26** |

El inventario dice exactamente eso (`INVENTARIO_T01_SERVIDOR.md:704-706`: «24 rutas … más `/health`
y `/api` … 26 en total»), y la lista coincide **ruta por ruta** con la que sale de leer el código: las
mismas 24. Lo que sí está desfasado son las líneas de tres de ellas y un matiz de cómo están
agrupadas:

| Ruta | Línea en el inventario | Línea de verdad | Qué pasó |
|---|---|---|---|
| `GET /api/ayuda` | `cuaderno.py:1248` | **`cuaderno.py:1264`** | El fichero creció por encima (el PDF): el inventario se quedó corto |
| `GET /api/ayuda/{campo}` | `cuaderno.py:1294` | **`cuaderno.py:1310`** | Igual |
| `GET /api/iuws/mensajes` | `iuws_api.py:347` | **`iuws_api.py:346`** | Una línea de más |

Y dos matices que conviene corregir al leerlo:

1. El inventario agrupa las 24 en «4 de alta y entrada + 17 de catálogos y textos + 3 de `/validar`».
   La cuenta es correcta, pero **dentro de esas 17 hay tres que no son lo mismo**: `/api/mapa/imagen`
   (la pide un `<img>` y no puede llevar vale) y `/api/mapa/punto` y `/api/sigpac/buscar` (salen a
   internet con parámetros de quien llama). Meterlas en el mismo saco que `/api/ayuda` es lo que hace
   que después no se pueda decidir nada. §3 y §4 las separan.
2. El inventario dice que «las rutas de `/api/iuws/*` … no se ha verificado respuesta a respuesta»
   (`:26-27`). Aquí sí se han leído las cuatro que no piden sesión, línea a línea, y de ahí sale
   §1.2.

### 1.2. La corrección ya está hecha, y así se comprueba

**`GET /api/iuws/comprobar-de-verdad` NO llama a la Junta.** Devuelve resultados históricos
guardados, en constantes:

- `iuws_api.py:280-298` devuelve `iuws.configuracion()["base"]` (una variable de entorno leída,
  `iuws.py:709-736`), `iuws.VERSION_OBSERVADA` y `iuws.FECHA_DE_LA_COMPROBACION` (`iuws.py:102-103`)
  y las dos tablas de lo que se comprobó en su día: `iuws.COMPROBADO_CONTRA_EL_INTERFAZ` e
  `iuws.COMPROBADO_ENTORNO_INTEGRACION` (`iuws.py:179-186`).
- **En toda esa función no hay ni una llamada a `httpx` ni a `iuws_cliente`.** El único uso de
  `iuws_cliente` en el fichero está en `iuws_api.py:248`, y esa línea está dentro de `/api/iuws/version`.

**La llamada de verdad hacia fuera es `GET /api/iuws/version?llamar=1`**: `iuws_api.py:232-245`
devuelve el informe sin tocar la red cuando no se le pide, y `iuws_api.py:248` llama a
`iuws_cliente.comprobar_donde_contesta(config["base"])` cuando `llamar` es verdadero.

El inventario **ya lo dice bien** en §2.4 (`:748`) y en §9 (`:1231-1232`), y el `SEGUIMIENTO` dejó
escrito que fue una corrección del 02/10 (`SEGUIMIENTO_IMPLEMENTACION_CRM.md:278-281`). Lo he
comprobado línea a línea y **no queda nada que corregir**: la atribución de riesgo está bien puesta
en los dos documentos. (En `docs/INTEGRACION_IUWS.md:663` la llamada que sale fuera también es
`version?llamar=1`, con vale.)

### 1.3. Lo que no entra en la cuenta de 24, y también está abierto

No son rutas declaradas, así que no están en las 24 ni en el inventario, pero son superficie pública
y conviene tenerlo escrito:

- **`/openapi.json`, `/docs` y `/redoc`.** `main.py:92-97` crea la aplicación sin desactivarlos, y
  FastAPI los publica por defecto (`fastapi/applications.py:221` para `openapi_url="/openapi.json"` y
  `:398-405` para `docs_url="/docs"`). El propio programa los anuncia: `main.py:147` devuelve
  `"documentacion": "/docs"`. Son la lista completa de la API —las 170— sin identificarse. No llevan
  datos de nadie, pero le ahorran a quien quiera buscar un descuido el trabajo de adivinar caminos.
- **La carpeta de la pantalla**, servida entera sin sesión desde `/` (`main.py:155-156`). Es a
  propósito y no se puede quitar: la pantalla de entrar tiene que abrirse **antes** de que haya vale.
- **`/api/interfaz` antes de entrar** va en el mismo paquete de decisiones (§3.1).

---

## 2. Cómo está clasificada cada ruta

Los cuatro grupos son los del encargo, y aquí se usan así:

- **«Tiene que ser pública»**: si se le pide el vale, o el cliente **no puede** mandarlo, o la
  aplicación no arranca. No hay nada que cambiar.
- **«Pública pero hay que filtrar/limitar»**: **tiene que seguir siendo pública**, pero hoy no tiene
  tope. «Limitar» aquí es de dos clases: **de recursos** (que alguien pueda hacer trabajar al
  servidor o a un tercero sin identificarse) y **de datos** (que la respuesta diga más de lo que
  tiene que decir). La etiqueta **no** quiere decir «cerrarla».
- **«Debería pedir sesión»**: no hay ninguna razón para que sea pública y hoy no aporta nada a nadie
  por serlo. Es el grupo pequeño, y son cuatro.
- **«No es una ruta de la API para personas»**: es herramienta de la integración o del técnico, no
  una pantalla. No está mal que exista; lo que está mal es que la use cualquiera.

| # | Método y camino | Fichero:línea | Grupo |
|---|---|---|---|
| 1 | `POST /api/cuenta/registro` | `cuenta.py:35` | Pública pero hay que limitar |
| 2 | `POST /api/cuenta/entrar` | `cuenta.py:103` | Pública pero hay que limitar |
| 3 | `GET /api/cuenta/certificado/estado` | `cuenta.py:167` | Tiene que ser pública |
| 4 | `POST /api/cuenta/entrar-con-certificado` | `cuenta.py:184` | Tiene que ser pública |
| 5 | `GET /api/municipios` | `parcelas.py:427` | Tiene que ser pública |
| 6 | `POST /api/sigpac/buscar` | `parcelas.py:460` | Pública pero hay que limitar |
| 7 | `GET /api/sigpac/estado` | `parcelas.py:591` | Pública pero hay que filtrar |
| 8 | `POST /api/sigpac/consultar` | `parcelas.py:604` | **Debería pedir sesión** |
| 9 | `GET /api/zonas-vulnerables/estado` | `parcelas.py:1168` | Pública pero hay que limitar |
| 10 | `GET /api/mapa/estado` | `mapa.py:44` | Tiene que ser pública |
| 11 | `GET /api/mapa/imagen` | `mapa.py:79` | Pública pero hay que limitar |
| 12 | `POST /api/mapa/punto` | `mapa.py:133` | Pública pero hay que limitar |
| 13 | `GET /api/interfaz` | `interfaz.py:17` | Tiene que ser pública |
| 14 | `GET /api/ayuda` | `cuaderno.py:1264` | Tiene que ser pública |
| 15 | `GET /api/ayuda/{campo}` | `cuaderno.py:1310` | Tiene que ser pública |
| 16 | `GET /api/cuaderno-cyl/estado` | `cuaderno_cyl_api.py:456` | Tiene que ser pública |
| 17 | `GET /api/cuaderno-cyl/hojas` | `cuaderno_cyl_api.py:470` | Tiene que ser pública |
| 18 | `GET /api/iuws/version` | `iuws_api.py:206` | No es una ruta para personas |
| 19 | `GET /api/iuws/comprobar-de-verdad` | `iuws_api.py:272` | No es una ruta para personas |
| 20 | `POST /api/iuws/leer-respuesta` | `iuws_api.py:318` | No es una ruta para personas |
| 21 | `GET /api/iuws/mensajes` | `iuws_api.py:346` | No es una ruta para personas |
| 22 | `POST /api/planes/validar` | `planes_api.py:159` | **Debería pedir sesión** |
| 23 | `POST /api/analiticas/validar` | `analiticas_api.py:286` | **Debería pedir sesión** |
| 24 | `POST /api/medidas/validar` | `medidas_api.py:98` | **Debería pedir sesión** |
| +1 | `GET /health` | `main.py:134` | Tiene que ser pública |
| +2 | `GET /api` | `main.py:142` | Tiene que ser pública |

**Resumen: 9 + 2 tienen que ser públicas, 7 necesitan límite, 4 deberían pedir sesión y 4 son
herramienta de integración.**

---

## 3. Las 24, una por una

### 3.1. `GET /api/interfaz` — tiene que ser pública

**Dónde está.** `backend/app/routers/interfaz.py:17` (`@router.get("/interfaz")`, línea 17) y
`interfaz.py:18` (`def interfaz() -> dict`). El router se declara con prefijo `/api`
(`interfaz.py:14`), así que el camino completo es `/api/interfaz`.

**Qué devuelve.** El vocabulario entero de la pantalla, `interfaz.py:19-257`: los textos de cada
pantalla, los del mapa, los del cuaderno de la Junta, las medidas preventivas, los plazos legales,
las provincias, los usos del SIGPAC y la ayuda. **Ni un dato de nadie**: todo sale de `textos.py`,
`catalogos.py` y `sigpac.py` (los usos del SIGPAC se leen del fichero local,
`interfaz.py:230-233` → `sigpac.usos_oficiales()`, `sigpac.py:989-990`). No escribe nada, no lee la
base de datos y no sale a internet.

**De dónde saca la explotación.** De ningún sitio: no hay finca en esta ruta y no hay ningún
parámetro que permita pedir datos de una finca. No hay nada que filtrar porque no hay nada de nadie.

**Quién la llama.** `app.js:3590` (`cargarInterfaz()`), y esa función se llama **antes de que haya
vale** en el arranque: `app.js:11338-11350` pinta la pantalla de entrar, y solo después pide la
interfaz «para poder escribir la pantalla de entrada en castellano de verdad» (`app.js:11341-11344`).
También la pide el recorrido de humo antes de dar de alta la cuenta (`humo.py:144`, sin cabeceras).
En las pruebas de Python es lo que más se llama y **siempre sin vale** (`test_interfaz.py:334`, `:380`,
`:397`, `:745`, `:1130`, `:1165`…).

**Clasificación: «tiene que ser pública».** Porque la pantalla de entrada necesita sus palabras
**antes** de que exista un vale, y lo que devuelve no es de nadie.

**Coste.** Arma un JSON grande en cada llamada y, por el camino, **lee y parsea un fichero JSON del
disco cada vez** (`interfaz.py:232` → `sigpac.cargar_codigos`, `sigpac.py:944-966`: no hay caché ni
`lru_cache`). No es un problema, pero está ahí y es barato de arreglar si algún día molesta.

### 3.2. `GET /api/cuenta/certificado/estado` — tiene que ser pública

**Dónde está.** `backend/app/routers/cuenta.py:167` y `:168` (`def estado_del_certificado(request: Request) -> dict`).

**Qué devuelve.** Cuatro cosas y dos textos (`cuenta.py:174-181`): si la instalación está configurada
para creerse las cabeceras del servidor web (`certificados.esta_configurado()`,
`certificados.py:338-340`), si hay certificado, los datos del certificado **del que llama** (NIF,
nombre, organización y si el NIF es válido, `certificados.py:241-248`) y dos frases de ayuda. El
certificado se lee de las cabeceras `X-SSL-Client-Subject` y `X-SSL-Client-Verify`
(`certificados.py:297-335`), y **solo si `CUEDIGITAL_CONFIAR_EN_CABECERAS` está encendido**
(`certificados.py:301-309`). No escribe nada y no lee la base de datos.

**De dónde saca la explotación.** De ningún sitio, y eso es lo correcto. **El único certificado que
puede devolver es el del propio que pregunta**: viene en su petición. No hay parámetro, ni cabecera,
ni variable de entorno que permita pedir el certificado de otro.

**Quién la llama.** `app.js:906` (`mirarCertificado()`), en el arranque **sin vale**
(`app.js:11344`), y `humo.py:466`. En pruebas, `test_interfaz.py:580`.

**Clasificación: «tiene que ser pública».** Porque la pantalla de entrar tiene que saber si esta
instalación sabe leer un certificado **antes** de enseñar el botón, y lo único que devuelve es lo que
quien pregunta ya ha mandado.

### 3.3. `POST /api/cuenta/entrar-con-certificado` — tiene que ser pública

**Dónde está.** `backend/app/routers/cuenta.py:184` y `:185`.

**Qué devuelve y qué cambia.** Devuelve un vale de sesión (`TokenSalida`, `cuenta.py:230-235`) y
**escribe** una fila en `auditoria` con `accion="entrar_con_certificado"` y el NIF y el nombre del
certificado (`cuenta.py:218-228`). Si no hay certificado, o el NIF no tiene forma válida, o la
instalación no está configurada: 401 (`:188-203`). Si el NIF es válido pero no hay ninguna finca dada
de alta con él: 403 con el NIF dentro y diciendo qué hacer (`:206-210`).

**De dónde saca la explotación.** **Del NIF del certificado**, no de la petición:
`_explotacion_por_nif(db, certificado.nif)` (`cuenta.py:205`, función en `:155-164`) busca la finca
cuyo `nif` coincide. **No hay ningún parámetro con el que se pueda pedir la finca de otro**: el cuerpo
de la petición ni se lee (la firma solo recibe `request` y `db`). La única forma de entrar en otra
finca sería presentar su certificado.

**Y aquí está la condición que hay que respetar, escrita:** esto es seguro **mientras el programa no
se exponga directamente**. Si `CUEDIGITAL_CONFIAR_EN_CABECERAS=1` y el programa es alcanzable sin un
servidor web delante, cualquiera puede mandar `X-SSL-Client-Subject: CN=LO QUE SEA,SERIALNUMBER=<NIF
del titular>` y entrar como él. Está previsto y probado en los dos sentidos: por defecto la variable
está apagada y **no se entra** (`certificados.py:301-309`, `test_certificado.py:261-267`), y con la
cabecera puesta por el servidor web sí se entra (`test_certificado.py:269-279`). También hay prueba de
que un certificado que el servidor web no ha validado (`X-SSL-Client-Verify: NONE`) no entra
(`test_certificado.py:319-327`). Lo que **no** hay es ningún límite de intentos (§5.2).

**Quién la llama.** `app.js:917`, desde la pantalla de entrar, **sin vale** (no puede tenerlo: es la
puerta). En pruebas, `test_certificado.py:263` y `:273`, y `humo.py:475`.

**Clasificación: «tiene que ser pública».** Porque **es** la entrada con certificado —pedirle un vale
sería pedir el vale para conseguir el vale— y porque no deja elegir finca: la finca sale del
certificado.

### 3.4. `GET /api/municipios` — tiene que ser pública

**Dónde está.** `backend/app/routers/parcelas.py:427` y `:428`.

**Qué devuelve.** Las nueve provincias y **hasta 25 municipios de los 2.248** de Castilla y León con
su nombre, su provincia, su código INE y sus dos códigos (el de municipio de tres cifras y el de
provincia), más el total (`parcelas.py:439-457`). La lista es **local**: se lee de
`data/municipios_cyl.csv` (`catalogos.py:637-638`, `:676-703`) y se queda en memoria, así que solo se
lee del disco la primera vez (`municipios_de_cyl()`, `catalogos.py:706-709`). No escribe, no toca la
base de datos y no sale a internet.

**De dónde saca la explotación.** De ningún sitio. Los dos parámetros (`buscar`, `provincia`,
`parcelas.py:428`) solo filtran la lista pública: no hay ningún valor que permita pedir datos de una
finca, porque esta ruta no tiene ninguno.

**Quién la llama.** La pantalla **con** vale: `app.js:5943`, dentro del asistente de traer la tierra
del SIGPAC (`apiJson` añade la cabecera si hay vale, `app.js:315-318`). Sin vale la llaman
`humo.py:429` y `test_parcelas_por_codigos.py:300`; en las pruebas de JavaScript está en el servidor
de mentira (`tests_js/interfaz.test.js:5161`, `:5209`).

**Clasificación: «tiene que ser pública».** Porque es la lista oficial del INE —la misma numeración
que el visor del SIGPAC— y no es de nadie; es lo que permite elegir el pueblo en vez de teclearlo
(`parcelas.py:429-437`, que lo dice con estas palabras).

### 3.5. `GET /api/ayuda` — tiene que ser pública

**Dónde está.** `backend/app/routers/cuaderno.py:1264` y `:1265`.

**Qué devuelve.** Los textos de ayuda que ya viven en `textos.py`: los porqués, la explicación de cada
campo, los plazos legales, las medidas preventivas, las reglas de nitratos y lo que falta
(`cuaderno.py:1266-1307`). No escribe, no lee la base de datos y no sale a internet.

**De dónde saca la explotación.** De ningún sitio: no tiene ni un parámetro.

**Quién la llama.** **Ninguna pantalla** (el inventario ya lo dice: `INVENTARIO_T01_SERVIDOR.md:886`;
la pantalla de ayuda se sirve por `/api/interfaz`, `app.js:1986-1988`). La llaman el recorrido de humo
**sin cabeceras** (`humo.py:419` y `:1745`, aunque en esos puntos ya tiene vale y podría mandarlo) y
seis pruebas, también sin vale: `test_interfaz.py:280`, `test_registro_obligatorio.py:834` y `:852`,
`test_medidas_preventivas.py:434`, `test_nitratos.py:352`, `test_cosecha_comercializada.py:594`.

**Clasificación: «tiene que ser pública».** Porque son palabras escritas que además salen por
`/api/interfaz`, y no hay absolutamente nada que filtrar: cerrarla no protegería nada y solo pondría
en rojo a quien la usa para comprobar que los textos están.

### 3.6. `GET /api/ayuda/{campo}` — tiene que ser pública

**Dónde está.** `backend/app/routers/cuaderno.py:1310` y `:1311`.

**Qué devuelve.** La ayuda de **un campo** (`textos.ayuda(campo)`, `cuaderno.py:1312`) o un 404 con
«De eso no tengo explicación todavía.» (`:1313-1314`).

**De dónde saca la explotación.** De ningún sitio. El parámetro `campo` es el nombre de un campo del
cuaderno (`producto.plazo_seguridad_dias`), no un identificador de nada de nadie: no hay forma de
pedir datos de una finca por aquí.

**Quién la llama.** Ninguna pantalla. `test_registro_obligatorio.py:841` y `:846`, **sin vale**.

**Clasificación: «tiene que ser pública»**, por lo mismo que la anterior.

### 3.7. `GET /api/cuaderno-cyl/estado` — tiene que ser pública

**Dónde está.** `backend/app/routers/cuaderno_cyl_api.py:456` y `:457`.

**Qué devuelve.** Los textos del cuaderno de la Junta, `se_puede: True`, **de dónde se descarga** (la
aplicación de la Junta, `particulares.ayg.jcyl.es`) y qué tipos de fichero se aceptan
(`cuaderno_cyl_api.py:459-467`). Son constantes: no escribe, no lee la base y no sale a internet.

**De dónde saca la explotación.** De ningún sitio: no tiene parámetros.

**Quién la llama.** Ninguna pantalla. `humo.py:2565` y `test_cuaderno_cyl.py:524`, **sin vale**.

**Clasificación: «tiene que ser pública».** Porque dice de dónde se descarga un cuaderno oficial —un
sitio público— y qué papeles valen; no lleva nada de nadie.

### 3.8. `GET /api/cuaderno-cyl/hojas` — tiene que ser pública

**Dónde está.** `backend/app/routers/cuaderno_cyl_api.py:470` y `:471`.

**Qué devuelve.** Las **25 hojas** del cuaderno oficial de la Junta, con su nombre y su título
(`cuaderno_cyl_api.py:477-482`), sacadas de `exportar.HOJAS` y `exportar.TITULOS`. Constantes.

**De dónde saca la explotación.** De ningún sitio: no tiene parámetros.

**Quién la llama.** Ninguna pantalla. `humo.py:2793` y `test_cuaderno_cyl_exportar.py:413`, **con**
vale (así que cerrarla no rompería ningún cliente hoy).

**Clasificación: «tiene que ser pública».** Porque es la lista de hojas de un documento público —el
cuaderno oficial de Castilla y León— y no lleva datos de nadie. No hay motivo para cerrarla ni para
cambiar nada.

### 3.9. `GET /api/mapa/estado` — tiene que ser pública

**Dónde está.** `backend/app/routers/mapa.py:44` y `:45`.

**Qué devuelve.** Qué hay detrás del mapa y de dónde sale (`mapa.py:47-76`): las tres capas con su
servicio (la foto del IGN/PNOA y los linderos y el cultivo declarado del SIGPAC/FEGA), que necesita
conexión, el mensaje para cuando no la hay, los límites de la caja y del tamaño de la imagen
(`:65-70`) y la licencia de los datos. La propia función dice por qué no pide sesión: «no lleva datos
de nadie» (`mapa.py:46`).

**De dónde saca la explotación.** De ningún sitio: no tiene parámetros y no toca la base.

**Quién la llama.** **Ninguna pantalla** —la aplicación tiene sus propios topes escritos en
JavaScript, por eso pide la imagen con `MAPA_ANCHO` y `MAPA_ALTO`, `app.js:5559-5567`—.
`humo.py:445` y `test_mapa_del_sigpac.py:403`, **sin vale**.

**Clasificación: «tiene que ser pública».** Porque es la ficha de los servicios oficiales que hay
detrás del mapa y la licencia con la que se publican; no hay nada que filtrar. Publicar los límites
no es un riesgo: son justamente los topes que conviene que respete quien pida una imagen.

### 3.10. `POST /api/cuenta/registro` — pública pero hay que limitar

**Dónde está.** `backend/app/routers/cuenta.py:35` y `:36`.

**Qué devuelve y qué cambia.** Devuelve un vale (201, `cuenta.py:95-100`) y **escribe**: crea la
`explotacion`, el `usuario`, el acceso a la finca con papel de titular, la `campana` del año y una
fila de `auditoria` (`cuenta.py:48-93`). **Es la única ruta sin sesión de toda la API que crea datos
de negocio** (la otra que escribe, `entrar-con-certificado`, solo deja una fila en `auditoria`), y
crea cinco filas por llamada.

**De dónde saca la explotación.** **La crea, no la lee**: sale del cuerpo (`datos.explotacion`,
`cuenta.py:48`). No hay ningún parámetro que apunte a una finca que ya existe; lo único que no se
puede repetir es el correo, que da 409 (`cuenta.py:38-42`). O sea: con esta ruta no se puede leer ni
tocar la finca de otro.

**Coste por llamada.** `security.hash_clave` (`cuenta.py:44`) deriva la clave con
**PBKDF2-SHA256 a 240.000 vueltas** (`security.py:23`, `:79-85`). Es caro **a propósito** (que una
clave robada sea difícil de adivinar) y por eso mismo es el sitio por donde se puede hacer trabajar
al servidor sin identificarse. No hay captcha, ni límite por IP, ni límite por tiempo (§5.2).

**Quién la llama.** La pantalla de alta, **sin vale** (`app.js:3742`). Y **toda la suite se apoya en
ella**: las fixtures `cuenta` (`conftest.py:153`) y `crear_cuenta` (`conftest.py:164`) dan de alta
una cuenta con esta ruta, sin la cual no existiría ninguna prueba de nada de lo demás. El recorrido
de humo también.

**Clasificación: «pública pero hay que limitar».** Porque **tiene que seguir siendo pública** —es la
puerta de alta, y sin ella no hay ni la primera cuenta— pero es la ruta más cara del servidor y hoy
se puede llamar tantas veces como quiera cualquiera: hay que limitar altas por IP y por tiempo.

**¿Rompe algún cliente si se cierra?** Sí, y **no se debe cerrar**: `app.js:3742` y las dos fixtures
de `conftest.py:153` y `:164`.

### 3.11. `POST /api/cuenta/entrar` — pública pero hay que limitar

**Dónde está.** `backend/app/routers/cuenta.py:103` y `:104`.

**Qué devuelve y qué cambia.** Devuelve un vale o un 401 con «El correo o la clave no son los
correctos» (`cuenta.py:110-113`), y 403 si la cuenta está dada de baja (`:114-115`). **No escribe
nada**: no se apunta ni siquiera un intento fallido.

**De dónde saca la explotación.** De la cuenta cuyo correo coincide: `usuario.explotacion_id`
(`cuenta.py:117-122`). **No hay ningún parámetro de finca**: no se puede pedir la finca de otro.

**Lo que hay que decir de esta ruta.** **Se deriva la clave aunque la cuenta no exista**, a propósito,
para no revelar qué correos están dados de alta (`cuenta.py:107-109`). Eso significa que cada intento
—también con un correo inventado— cuesta 240.000 vueltas de PBKDF2. Y **no hay ningún freno**: ni
límite de intentos, ni retardo progresivo, ni bloqueo temporal, ni registro. Está dicho en el propio
código, en la lista de lo que falta antes de abrir esto a clientes: `security.py:8-10` nombra
«límite de intentos» entre la rotación de claves y el doble factor.

**Quién la llama.** La pantalla de entrar, **sin vale** (`app.js:3744`). En pruebas,
`test_registro_obligatorio.py:48` y `:58`.

**Clasificación: «pública pero hay que limitar».** Porque tiene que ser pública (es la puerta), pero
hoy se pueden probar claves sin freno y cada intento cuesta 240.000 vueltas de hash: hay que poner
límite de intentos por cuenta **y** por IP.

### 3.12. `POST /api/sigpac/buscar` — pública pero hay que limitar

**Dónde está.** `backend/app/routers/parcelas.py:460` y `:461`. (Ojo: el camino literal es
`/api/sigpac/buscar`, en el router de parcelas, que tiene prefijo `/api`, `parcelas.py:32`.)

**Qué devuelve.** Los **trozos (recintos) oficiales** que hay en una parcela del SIGPAC, con
recinto, referencia, superficie, uso, pendiente, altitud, coeficiente de regadío y si tiene dibujo
(`parcelas.py:494-516`). Son datos **del FEGA**, los mismos que da el visor público del SIGPAC sin
identificarse. No escribe nada y no toca la base de datos.

**De dónde saca la explotación.** De ningún sitio. El cuerpo trae los números del SIGPAC o una
referencia pegada (`BuscarRecintosEntrada`), y eso **permite preguntar por la parcela de cualquier
otro agricultor**: se obtiene su forma, su superficie y su uso. Pero eso **no es una fuga del
cuaderno**: el SIGPAC es público por diseño y **no dice de quién es una parcela**. Lo que no se puede
hacer por aquí es saber si esa tierra está en el cuaderno de alguien, ni ver ni tocar ningún apunte.

**Gasto de recursos (lo que de verdad importa en esta ruta).** Hasta **26 llamadas salientes por cada
petición**: una para la lista de trozos (`sigpac.pedir_recintos`, `parcelas.py:480`) y una por cada
trozo encontrado, hasta 25 (`MAX_RECINTOS_POR_BUSQUEDA = 25`, `parcelas.py:37`, y el bucle en
`parcelas.py:489-490`, que llama a `sigpac.pedir_recinto`, `sigpac.py:1072-1087`). Cada llamada lleva
**10 segundos** de espera (`sigpac.ESPERA_SEGUNDOS`, `sigpac.py:64`). Quien llame sin vale puede
encargar todo eso y no hay nada que se lo impida (§5.2).

**Quién la llama.** La pantalla **sí manda vale**: `app.js:5977`, dentro del asistente de traer del
SIGPAC, con `apiJson` (que añade la cabecera si hay vale, `app.js:315-318`). Sin vale la llaman
**siete pruebas** de `test_parcelas_por_codigos.py` (`:312`, `:335`, `:344`, `:360`, `:372`, `:378`,
`:385`) con la fixture `cliente`, que **no tiene cuenta** (`conftest.py:146-148`), y la tiene en su
servidor de mentira `tests_js/interfaz.test.js:5222`.

**Clasificación: «pública pero hay que limitar».** Porque no lleva datos de nadie —el SIGPAC es
público y lo mismo se saca del visor del FEGA— pero es un amplificador abierto: cualquiera puede
encargarle 26 peticiones al SIGPAC por cada una suya, y el SIGPAC es de todos.

**Si no se puede limitar todavía**, cerrarla con la finca es una alternativa aceptable y barata para
el cliente (la pantalla ya manda vale), pero entonces hay que arreglar primero las siete pruebas,
poniéndolas con la fixture `cuenta`.

### 3.13. `GET /api/sigpac/estado` — pública pero hay que filtrar

**Dónde está.** `backend/app/routers/parcelas.py:591` y `:592`.

**Qué devuelve.** `sigpac.datos_disponibles()` (`parcelas.py:600`) y los textos. Eso incluye: **la
ruta absoluta de la carpeta de datos del servidor** (`"ruta": str(RUTA_DATOS)`, `sigpac.py:1038`),
si hay datos, cuántos productos oficiales hay (933), cuántos usos, aprovechamientos e incidencias,
cómo actualizarlos (`python scripts/bajar_sigpac.py`) y la licencia (`sigpac.py:1037-1050`). No
escribe, no toca la base y no sale a internet.

**De dónde saca la explotación.** De ningún sitio: no tiene parámetros.

**Coste.** Cuatro lecturas y parseos de fichero JSON del disco por llamada
(`sigpac.py:1036-1043` → `cargar_codigos`, `sigpac.py:944-966`: **no hay caché**).

**Quién la llama.** Ninguna pantalla. `humo.py:1633` y `test_sigpac.py:454`, **sin vale**.
`test_las_tierras_se_pueden_corregir.py:986` solo comprueba que la ruta sigue publicada en el
esquema, no la llama.

**Clasificación: «pública pero hay que filtrar».** Porque no lleva datos de nadie, pero **no tiene por
qué decirle a quien pregunte dónde está la carpeta de datos del servidor**: el arreglo no es cerrarla,
es **quitar `ruta` de la respuesta** (o darla solo con sesión). Es lo único que sobra de esta ruta.

### 3.14. `GET /api/zonas-vulnerables/estado` — pública pero hay que limitar

**Dónde está.** `backend/app/routers/parcelas.py:1168` y `:1169`.

**Qué devuelve.** Si el listado oficial de zonas vulnerables está cargado, cuántos municipios tiene
(387 con el fichero que hay, `data/zv_cyl.csv`) y una explicación
(`parcelas.py:1176-1182`).

**Lo que hace sin que se lo pidan.** Llama a `catalogos.cargar_zonas_vulnerables()` **en cada
petición** (`parcelas.py:1176`), y esa función **vuelve a abrir y a leer el CSV y a rehacer el
conjunto de municipios cada vez**: no hay ninguna comprobación de «ya está cargado»
(`catalogos.py:787-819`), a diferencia de la lista de municipios, que sí se carga una sola vez
(`catalogos.py:706-709`). Es decir: **cualquiera puede hacer que el servidor lea y reconstruya el
catálogo tantas veces como quiera**, sin identificarse.

**De dónde saca la explotación.** De ningún sitio: no tiene parámetros y no lee nada de nadie.

**Quién la llama.** Ninguna pantalla. `test_listado_oficial_zv_cyl.py:90` y
`test_registro_obligatorio.py:970`, **sin vale**. Lo mismo que dice esta ruta ya sale, más barato, en
`/health` (`main.py:136-139` → `catalogos.hay_datos_zonas_vulnerables()`).

**Clasificación: «pública pero hay que limitar».** Porque lo que dice es público (el listado municipal
del Decreto 5/2020 lo publica la Junta) y no revela nada de nadie, pero **cada llamada sin sesión
hace un trabajo de disco que no hace falta**: lo suyo es dejar de recargar el catálogo en cada
petición, o devolverlo desde donde ya está cargado.

### 3.15. `GET /api/mapa/imagen` — pública pero hay que limitar

**Dónde está.** `backend/app/routers/mapa.py:79` y `:80`.

**Qué devuelve.** **Una imagen** (JPEG o PNG) que **trae el programa** del IGN (la foto PNOA) o del
SIGPAC (los linderos y el cultivo declarado) y sirve él (`mapa.py:116-130`). Las direcciones oficiales
están en `sigpac.CAPAS_DEL_MAPA` (`sigpac.py:468-475`). Va con `Cache-Control: public, max-age=600`
(`mapa.py:129`) para que mover el mapa no vuelva a pedir lo mismo.

**De dónde saca la explotación.** De ningún sitio, y aquí no hay ninguna: la petición son **coordenadas
y un tamaño**. No existe ningún parámetro que pida datos de una finca.

**Lo que sí está acotado.** La capa tiene que existir (`mapa.py:96-97`); la caja no puede venir al
revés ni medir menos de 0,0008° ni más de 0,5° por el lado mayor (`mapa.py:99-114`, con los topes en
`mapa.py:40-41`); y el ancho y el alto se recortan a **64-1600 píxeles** (`sigpac.py:489-490`). Con
eso, **una** petición no puede pedir una imagen enorme.

**Lo que no está acotado.** **Cuántas peticiones hace quien llama.** Cualquiera puede usar el programa
como servidor de imágenes del IGN y del SIGPAC para cajas distintas de 90 metros a 55 kilómetros. Y
la caché que protege al agricultor es de **20 imágenes y se vacía entera al llegar a 20**
(`TAMANO_DE_LA_CACHE_DE_IMAGENES = 20`, `sigpac.py:72`; `_CACHE_DE_IMAGENES.clear()`,
`sigpac.py:927-928`): **veinte cajas distintas pedidas por cualquiera dejan al agricultor sin caché**,
que es justo lo que la caché existía para evitar (`sigpac.py:900-905`).

**Quién la llama, y por qué esto es especial.** **La pantalla la pide con un `<img src>`**:
`app.js:5556-5568` (`direccionDeLaImagen`) construye la dirección y el componente la pinta en
`react/pantallas/mapa.js:39-40` (`<img className="mapa-foto" src=... />`). **Por esa vía el navegador
no manda la cabecera del vale, y no puede mandarla.** O sea: **cerrarla obliga a cambiar el cliente
antes** (pedirla con `fetch` y pintarla desde memoria), o a aceptar un vale en la propia dirección.
Sin vale la llaman `humo.py:456` y seis pruebas de `test_mapa_del_sigpac.py` (`:429`, `:452`, `:457`,
`:466`, `:481`, `:499`); en JavaScript, `tests_js/interfaz.test.js:5484` comprueba que la dirección de
la foto es la del programa.

**Clasificación: «pública pero hay que limitar».** Porque no lleva datos de nadie y la pantalla no
puede mandar vale por un `<img>`, pero es un proxy abierto a dos servicios de fuera: hay que ponerle
un tope por IP, arreglar la caché para que no se pueda vaciar desde fuera, y —si se quiere cerrar de
verdad— cambiar antes la pantalla.

### 3.16. `POST /api/mapa/punto` — pública pero hay que limitar

**Dónde está.** `backend/app/routers/mapa.py:133` y `:134`.

**Qué devuelve.** Lo que hay en un punto del mapa (`mapa.py:216-242`): la referencia del recinto, su
superficie, uso y pendiente, la altitud, **los vértices para pintarlo**, el municipio, la
**referencia catastral** y si el punto está en zona de nitratos (que puede quedar en «no lo sé» si el
servicio no contesta, `mapa.py:136-144`). Son datos oficiales del SIGPAC y del Catastro.
No escribe nada y no toca la base de datos.

**De dónde saca la explotación.** De ningún sitio: el cuerpo son **dos coordenadas** (`x`, `y`),
comprobadas a mano y dentro del mundo (`mapa.py:151-164`). Con esto se puede preguntar por **cualquier
punto de España**, incluida la tierra de otro agricultor, y se obtendrá exactamente lo mismo que da
el visor del SIGPAC a cualquiera. **Lo que no se puede saber por aquí es de quién es**: el SIGPAC no
publica la titularidad, y esta ruta no toca ninguna finca. El contrato ya avisa de que «una consulta
por coordenada no acredita propiedad» (`INVENTARIO_T01_SERVIDOR.md:745`), y eso sigue siendo verdad.

**Gasto de recursos.** Hasta **3 llamadas** a servicios de fuera por petición: el recinto del punto
(`sigpac.pedir_recinto_por_punto`, `mapa.py:167`), la referencia catastral (`mapa.py:193`) y la capa
de nitratos (`sigpac.zona_de_nitratos`, `mapa.py:210` → `pedir_interseccion`, `sigpac.py:860-877`).
10 segundos de espera cada una (`sigpac.py:64`).

**Quién la llama.** La pantalla **sí manda vale**: `app.js:5749`, con `apiJson`. Sin vale la llaman
seis pruebas de `test_mapa_del_sigpac.py` (`:508`, `:534`, `:539`, `:543`, `:554`, `:586`). Ninguna
pantalla más: el recorrido de humo no la llama.

**Clasificación: «pública pero hay que limitar».** Porque no lleva datos de nadie, pero cada petición
gasta tres consultas al SIGPAC y al Catastro y hoy no hay tope. Con el matiz de que aquí **cerrarla
sí sería barato para el cliente** (la pantalla ya manda vale y solo hay que actualizar seis pruebas),
así que es la candidata natural si se prefiere exigir sesión antes que poner un límite por IP.

### 3.17. `POST /api/sigpac/consultar` — debería pedir sesión

**Dónde está.** `backend/app/routers/parcelas.py:604` y `:605`.

**Qué devuelve.** La ficha de un recinto del SIGPAC a partir de una referencia pegada
(`parcelas.py:634-644`): superficie, pendiente, uso, altitud y si tiene dibujo; o
`encontrado: False` si esa referencia no existe (`:628-633`). Y devuelve también **la dirección exacta
que ha consultado** (`"consulta": sigpac.url_recinto(referencia)`, `parcelas.py:643`). No escribe y no
toca la base de datos. Existe para comprobar una referencia antes de apuntarla (`parcelas.py:606-609`)
y **no tiene botón en ninguna pantalla** (el inventario ya lo dice: `INVENTARIO_T01_SERVIDOR.md:883`).

**Y es la excepción que hay que señalar.** Es **la única ruta de la API que llama a un servicio de
fuera directamente desde un router**: `httpx.get(...)` en `parcelas.py:617` (el módulo importa `httpx`
en la línea 13). Todo lo demás sale por `sigpac.pedir_*` o por `iuws_cliente.*`, que es la frontera
única que el propio módulo declara («es lo único de todo el programa que necesita internet, y tenerlo
en un solo sitio es lo que permite probarlo», `sigpac.py:1055-1059`). Aquí no se usan la espera ni el
manejo del error de `pedir_recinto`: compárese `parcelas.py:616-625` con `sigpac.py:1072-1087`. **No
es un fallo por sí solo —hay espera y hay 503— pero es la puerta por la que una consulta saliente se
puede disparar sin identificarse y sin pasar por el sitio donde están todas las demás.**

**De dónde saca la explotación.** De ningún sitio, y no hay ninguna que sacar: el cuerpo solo lleva
una referencia pública del SIGPAC (`ReferenciaSigpacEntrada`). Aquí no hay datos de nadie **ni los
habrá**: lo que se pide es catastro público.

**Quién la llama.** **Ninguno de los que la llaman hoy lo hace sin vale**: `test_sigpac.py:425` y
`:446` (con `cuenta["cabeceras"]`) y `humo.py:1653` (con `cabeceras`). Ninguna pantalla.

**Clasificación: «debería pedir sesión».** Porque no tiene pantalla, **todos los que la llaman hoy ya
llevan vale** y es una llamada saliente que cualquiera puede disparar: es la que se puede cerrar
**hoy, sin tocar ni un cliente**, y por eso va la primera en la lista de por dónde empezar.

**Pruebas que hay que escribir:**

1. Sin vale contesta **401** (con la fixture `cliente`, `conftest.py:146`, que no tiene cuenta).
2. Con vale sigue haciendo lo mismo que hoy: la prueba que ya existe vale como contrato
   (`test_sigpac.py:425`), solo hay que asegurarse de que sigue en verde.
3. **Y la que de verdad cierra el asunto**: que sin vale **no se llama a `httpx.get`**. Las pruebas
   del SIGPAC ya saben contar llamadas sustituyendo `httpx.get` por un doble
   (`test_parcelas_por_codigos.py:295`, `test_mapa_del_sigpac.py:423-427`); con ese mismo truco, la
   prueba demuestra que la puerta no gasta red, no solo que contesta 401.
4. De paso, un 404/401 que no filtre si la referencia existe (la regla del proyecto: **404 y no 403**,
   `deps.py:74-85`).

### 3.18. `POST /api/planes/validar` — debería pedir sesión

**Dónde está.** `backend/app/routers/planes_api.py:159` y `:160`.

**Qué devuelve.** `{puede_guardarse, avisos}` calculados por `validaciones.validar_plan(datos=datos)`
(`planes_api.py:161-165`), que es una **función pura**: mira `parcela_id`, `grupo_id`, `cultivo` y
`superficie_ha` del cuerpo y devuelve avisos (`validaciones.py:540-557`). No abre la base de datos, no
escribe y no sale a internet. La firma solo recibe los datos: ni sesión, ni finca
(`planes_api.py:160`).

**De dónde saca la explotación. De ninguna, y ahí está el motivo.** El cuerpo
(`PlanAbonadoEntrada`) lleva `campana_id`, `parcela_id` y `analitica_id`, que son **identificadores de
una finca**. Hoy la función no los usa para consultar nada, así que **no hay fuga** —pero el día que
una comprobación necesite leer la parcela (por ejemplo, avisar de que el plan no cuadra con la
superficie declarada), se leería **la parcela que diga el cuerpo, sin comprobar de quién es**, y por
ahí sí se podría mirar la finca de otro.

**Y el contraste que hay que copiar está en el mismo proyecto**: `POST /api/tratamientos/validar`
(`registros.py:180-185`) hace lo mismo —validar sin guardar— y **sí pide `ExplotacionActual`**, porque
por dentro carga la parcela, el producto, el aplicador y la máquina con `obtener_de_la_explotacion`
(`registros.py:43-46` y `:130-139`). Eso es lo que hay que hacer aquí.

**Quién la llama.** Ninguna pantalla (el inventario la lista entre las que no llama nadie,
`INVENTARIO_T01_SERVIDOR.md:869`). `test_plan_abonado.py:210`, **con vale**;
`test_analisis_ventas_planes_y_campanas.py:1471` solo comprueba que sigue publicada en el esquema.
El recorrido de humo no la llama.

**Clasificación: «debería pedir sesión».** Porque hoy no filtra nada —es pura— pero lleva en el cuerpo
identificadores de una finca y es la excepción que permite que mañana alguien añada una consulta ahí
dentro sin que nada lo pare.

**Pruebas que hay que escribir:**

1. Sin vale, **401**.
2. Con vale, los mismos avisos que hoy (la prueba que ya existe, `test_plan_abonado.py:208-216`).
3. Que el `parcela_id` de **otra finca** en el cuerpo no sirve para nada: o no se consulta, o si algún
   día se consulta, da 404 y no 403 (`deps.py:74-85`).

### 3.19. `POST /api/analiticas/validar` — debería pedir sesión

**Dónde está.** `backend/app/routers/analiticas_api.py:286` y `:287`.

**Qué devuelve.** `{puede_guardarse, avisos}` de `validaciones.validar_analitica` (`:289-293`),
después de pasar los parámetros por `servicios.limpia_parametros` (`:288`), que es la puerta que
descarta un número que no está en el catálogo (`servicios.py:296-335`) y que **es pura** (usa el
catálogo en memoria, no la base). `validar_analitica` (`validaciones.py:681-719`) mira el tipo, las
dos fechas y `parcela_id`/`instalacion_id`. No escribe.

**De dónde saca la explotación.** De ninguna. Y el cuerpo (`AnaliticaEntrada`) lleva `campana_id`,
`parcela_id` e `instalacion_id` —los mismos identificadores que usa `crear_analitica` para comprobar
de quién son (`analiticas_api.py:304-307`)—, así que es exactamente el mismo riesgo de mañana que en
la ruta anterior.

**Quién la llama.** Ninguna pantalla. `test_analiticas.py:229` y `humo.py:912-921`, **con vale** las
dos.

**Clasificación: «debería pedir sesión»**, por el mismo motivo y con las mismas pruebas que §3.18
(401 sin vale; los avisos de siempre con vale; y un `parcela_id` de otra finca que no sirve para
nada).

### 3.20. `POST /api/medidas/validar` — debería pedir sesión

**Dónde está.** `backend/app/routers/medidas_api.py:98` y `:99`.

**Qué devuelve.** `{puede_guardarse, avisos}` de `validaciones.validar_medidas(aplicadas=datos.aplicadas)`
(`medidas_api.py:100-104`), que es pura (`validaciones.py:565-578`): si no hay ninguna medida marcada
devuelve **un aviso que no bloquea**, a propósito (`validaciones.py:568-573`). No escribe.

**De dónde saca la explotación.** De ninguna: **es la única de las tres `/validar` cuyo cuerpo no
lleva ni un identificador de finca** (`MedidasEntrada` son códigos del catálogo y observaciones). O
sea: de las tres, es la menos urgente.

**Quién la llama.** Ninguna pantalla. `test_medidas_preventivas.py:180` y `:190`, **con vale**;
`test_analisis_ventas_planes_y_campanas.py:1471` solo mira el esquema.

**Clasificación: «debería pedir sesión».** Porque hoy no hay ningún dato de nadie en juego, pero se
pone en el mismo grupo para que la regla quede uniforme y no haya excepciones que alguien pueda
copiar: **toda ruta que valide algo de una finca pide la finca, aunque hoy no la mire.** Si se decide
no tocarla, hay que dejarlo escrito aquí para que no parezca un olvido.

### 3.21. `GET /api/iuws/version` — no es una ruta de la API para personas

**Dónde está.** `backend/app/routers/iuws_api.py:206` y `:207`.

**Qué devuelve, y las dos caras.** **Sin `llamar`** devuelve un informe que **no toca la red**
(`iuws_api.py:232-245`): la dirección configurada, que ya se puede probar sin tener nada configurado,
la versión observada (3.11.4), la fecha de la comprobación, lo que falta y las direcciones conocidas
por comunidad. **Con `?llamar=1`** llama de verdad:
`iuws_cliente.comprobar_donde_contesta(config["base"])` (`iuws_api.py:248`), que prueba **primero la
dirección configurada y, si no contesta 200, la de la comunidad** (`iuws_cliente.py:328-348`) —**hasta
dos llamadas**, con **15 segundos** de espera cada una (`iuws.ESPERA_SEGUNDOS`, `iuws.py:104`);
`BASES_CONOCIDAS` tiene hoy una sola entrada, Castilla y León (`iuws.py:71-73` y `:186`).

**Esta es la llamada de verdad hacia fuera, y no `comprobar-de-verdad`** (§1.2). Es la ruta que hay
que limitar o cerrar antes de exponer el servidor, porque sin identificarse se puede hacer que el
programa llame al servidor de la Junta, y a la espera de 30 segundos se le suma un trabajador del
servidor ocupado.

**De dónde saca la explotación.** De ningún sitio: `configuracion()` solo lee variables de entorno
(`iuws.py:709-736`), no hay finca ni base de datos.

**Quién la llama.** Ninguna pantalla. `humo.py:1363` y `:1373`, `test_iuws.py:872` y
`test_iuws_cliente.py:775`, `:815` y `:826`, **todas con vale**; y
`docs/INTEGRACION_IUWS.md:663` la documenta con `Authorization`.

**Clasificación: «no es una ruta de la API para personas».** Porque el propio router lo dice con
estas palabras: «no tiene pantalla de agricultor: quien lo usa es quien hace la integración (una vez,
para dejar el sistema conectado) o el técnico que comprueba si ya está conectado» (`iuws_api.py:3-5`).
Lo suyo es que la use quien tiene el encargo de integrar, con vale, y no el primero que pase.

**Qué falta.** Si se quiere dejar pública la parte informativa (que no toca la red y es útil), la
solución honesta es separar las dos: la información, pública; **`?llamar=1`, con vale o con límite**.

### 3.22. `GET /api/iuws/comprobar-de-verdad` — no es una ruta de la API para personas

**Dónde está.** `backend/app/routers/iuws_api.py:272` y `:273`.

**Qué devuelve.** **Solo constantes** (`iuws_api.py:280-298`): la dirección que se usó, la versión
observada, la fecha, **los siete métodos con lo que contestó cada uno** (`iuws.COMPROBADO_CONTRA_EL_INTERFAZ`,
`iuws.py:102-103` y `:179-186`) y lo mismo del entorno de integración, más tres explicaciones escritas
(de qué significa un 401, de que un 200 también engaña y de por qué no se prueba lo demás,
`:299-314`). **No llama a `httpx` ni a `iuws_cliente`: no sale a internet.** Lo único que lee son
variables de entorno (`iuws.configuracion()`, `:282`).

**De dónde saca la explotación.** De ningún sitio: no tiene parámetros.

**Quién la llama.** `humo.py:1395` y `test_iuws_cliente.py:832`, **con vale**. Y
`docs/INTEGRACION_IUWS.md:666` la documenta con un `curl` **sin** vale: es **la única línea de ese
bloque que no lleva `Authorization`** (las otras cuatro, `:654`, `:657`, `:660`, `:663`, sí lo
llevan). Si algún día se cierra, esa línea del documento hay que cambiarla.

**Clasificación: «no es una ruta de la API para personas».** Porque es la tabla de lo comprobado
contra la Junta, material de la integración.

### 3.23. `POST /api/iuws/leer-respuesta` — no es una ruta de la API para personas

**Dónde está.** `backend/app/routers/iuws_api.py:318` y `:319`.

**Qué devuelve.** La traducción de lo que contesta el interfaz (`iuws_api.py:331-343`): código,
mensaje, si está bien o es parcial o es fallo, identificador de la petición, detalles, actividades
fallidas, la operación y **el texto crudo**. Existe para poder pegar la respuesta en un correo a
soporte sin tener que interpretarla (`:320-324`). 422 si no le llega `respuesta` (`:326-330`). Es una
función pura sobre lo que llega (`iuws.leer_respuesta`): no toca la base, no sale a internet y **no
hay nada que sacar de nadie**: lo que devuelve es lo que le han mandado.

**De dónde saca la explotación.** De ningún sitio: el cuerpo es la respuesta del interfaz pegada a
mano.

**Quién la llama.** `humo.py:1418`, `test_iuws.py:892` y `:913`, **con vale**; y
`docs/INTEGRACION_IUWS.md:669-671`, con `Authorization`.

**Clasificación: «no es una ruta de la API para personas».** Porque es la herramienta para escribir
un correo a soporte, no algo que use un agricultor.

### 3.24. `GET /api/iuws/mensajes` — no es una ruta de la API para personas

**Dónde está.** `backend/app/routers/iuws_api.py:346` y `:347` (el inventario lo pone en `:347`: es
una línea de más, ver §1.1).

**Qué devuelve.** El catálogo de los **19 mensajes** del interfaz, traducidos: código, nombre,
significado y explicación (`iuws_api.py:349-355`, de `iuws.MENSAJES` y `iuws.mensaje_de_codigo`).
Constantes.

**De dónde saca la explotación.** De ningún sitio: no tiene parámetros.

**Quién la llama.** `humo.py:1439` y `test_iuws.py:883`, **con vale**. Ninguna pantalla.

**Clasificación: «no es una ruta de la API para personas».** Porque es la lista de mensajes oficiales
traducida, para tenerla a mano al integrar.

### 3.25. `GET /health` (fuera de los routers) — tiene que ser pública

**Dónde está.** `backend/app/main.py:134` y `:135`.

**Qué devuelve.** `{"estado": "ok", "zonas_vulnerables_cargadas": ...}` (`main.py:136-139`): si el
programa está en pie y si el listado oficial de zonas vulnerables se ha podido cargar
(`catalogos.hay_datos_zonas_vulnerables()`, `catalogos.py:822-823`). Nada de nadie.

**Quién la llama.** La pantalla no (`service-worker.js:298` lo menciona **solo para no guardarlo en
la caché**). `test_interfaz.py:278`. Es la que preguntaría un sistema de vigilancia.

**Clasificación: «tiene que ser pública».** Porque una salud del servicio tiene que poder preguntarse
sin identificarse, y lo único que dice es si está en pie y qué tiene cargado.

### 3.26. `GET /api` (fuera de los routers) — tiene que ser pública

**Dónde está.** `backend/app/main.py:142` y `:143`.

**Qué devuelve.** Cuatro frases fijas (`main.py:144-149`): el nombre, qué es, dónde está la
documentación (`/docs`) y por dónde se empieza (`/api/cuenta/registro`). Nada de nadie.

**Quién la llama.** `test_interfaz.py:279`. La pantalla, no.

**Clasificación: «tiene que ser pública».** Porque es la portada de orientación de la API, y lo que
dice no es de nadie. (Que anuncie `/docs` es la otra cara de §1.3: la documentación de la API también
está abierta.)

---

## 4. De dónde saca la finca cada una (el cuadro del aislamiento)

**Ninguna de las 24 saca una finca, porque ninguna tiene sesión.** Y eso hay que decirlo con
precisión, porque es la pregunta que decide si hay fuga o no:

| Cómo consigue la finca | Rutas | ¿Se puede pedir la finca de otro? |
|---|---|---|
| **La crea** (viene del cuerpo del alta) | `POST /api/cuenta/registro` | **No.** Crea una finca nueva; no hay parámetro que apunte a una existente. Lo único que no se puede repetir es el correo (409). |
| **Sale del certificado** (el NIF de la cabecera que ha validado el servidor web) | `POST /api/cuenta/entrar-con-certificado` | **No**, mientras el programa esté detrás de un servidor web. **Sí**, si se expone directamente con `CUEDIGITAL_CONFIAR_EN_CABECERAS=1`: entonces se entra mandando el NIF del titular en una cabecera (§3.3). |
| **Sale del correo de la cuenta** | `POST /api/cuenta/entrar` | **No.** La finca es la de la cuenta cuya clave se acierta. |
| **De ningún sitio, y no hay ninguna que sacar** (catálogos, textos, estado, servicios oficiales) | las otras 21 | **No.** No hay parámetro con nombre de finca, ni identificador de finca en el cuerpo, en ninguna. |
| **Ojo: llevan identificadores de finca en el cuerpo sin usarlos todavía** | `POST /api/planes/validar` (`campana_id`, `parcela_id`, `analitica_id`), `POST /api/analiticas/validar` (`campana_id`, `parcela_id`, `instalacion_id`) | **Hoy no**, porque las funciones que hay detrás son puras. **El día que se consulte algo con esos identificadores, sí**, y por eso estas dos van al grupo de «debería pedir sesión» (§3.18 y §3.19). |

**Y lo que sí se puede pedir por las rutas del SIGPAC y del mapa** (`sigpac/buscar`, `sigpac/consultar`,
`mapa/punto`, `mapa/imagen`): **datos públicos de una tierra que puede ser de otro** —forma,
superficie, uso, pendiente, referencia catastral, zona de nitratos—, **pero no datos de su cuaderno
ni la titularidad**. El SIGPAC no publica de quién es una parcela y el programa, por estas cuatro
rutas, no toca la base de datos. Es exactamente la misma información que da el visor oficial del FEGA
a cualquiera y sin registrarse. Decirlo así importa: **no es una fuga, es una consulta pública con
nuestro servidor de por medio**, y lo que hay que arreglar es el «por medio» (§5), no el dato.

---

## 5. Gasto de recursos sin sesión

### 5.1. Quién puede hacer que el programa llame a la Junta, al SIGPAC o a internet

| Ruta | A quién llama | Llamadas por petición | Espera por llamada | Límite hoy |
|---|---|---|---|---|
| `POST /api/sigpac/buscar` | SIGPAC (FEGA) | **hasta 26** (1 lista + 25 fichas, `parcelas.py:37` y `:489`) | 10 s (`sigpac.py:64`) | **ninguno** |
| `POST /api/mapa/punto` | SIGPAC (FEGA) y Catastro | **hasta 3** (`mapa.py:167`, `:193`, `:210`) | 10 s | **ninguno** |
| `POST /api/sigpac/consultar` | SIGPAC (FEGA) | **1** (`parcelas.py:617`) | 10 s | **ninguno** |
| `GET /api/mapa/imagen` | IGN (PNOA) y SIGPAC | **1** (0 si esa caja ya está en caché) | 6 s (`sigpac.py:68`) | **ninguno**; caché de 20 que **se vacía entera** al llenarse (`sigpac.py:72` y `:927-928`) |
| `GET /api/iuws/version?llamar=1` | interfaz de la Junta (IUWS) | **hasta 2** (`iuws_cliente.py:328-348`) | 15 s (`iuws.py:104`) | **ninguno** |

Ninguna de estas cinco pide sesión. Con las cinco, **un solo cliente sin identificarse puede encargar
hasta 26 consultas al SIGPAC, 3 más con cada toque de mapa, y 2 al servidor de la Junta**, y el
programa se queda esperando hasta 260 segundos por una sola petición de `sigpac/buscar` en el peor
caso (26 × 10 s, contando que todas las llamadas agoten su espera).

**Y las que parecen lo mismo y no lo son** (para no asustar donde no hay que asustarse):

- `GET /api/iuws/comprobar-de-verdad`: **no sale a internet**, son constantes (§3.22).
- `GET /api/municipios`: lee un CSV local y **solo la primera vez** (`catalogos.py:706-709`).
- `GET /api/sigpac/estado`: lee cuatro JSON locales **en cada llamada**, pero no sale a la red
  (`sigpac.py:944-966`).
- `GET /api/zonas-vulnerables/estado`: lee un CSV local **en cada llamada** (`catalogos.py:787-819`).
- `GET /api/interfaz`, `/api/ayuda`, `/api/ayuda/{campo}`, `/api/mapa/estado`,
  `/api/cuaderno-cyl/estado`, `/api/cuaderno-cyl/hojas`, `/health`, `/api`: nada de fuera.

### 5.2. ¿Hay algún límite? **No hay ninguno**

Comprobado buscando en todo `backend/` (`slowapi`, `ratelimit`, `rate_limit`, `throttle`, `429`,
`max_requests`, `por_minuto`, `middleware`):

- **No hay limitación por IP, ni por tiempo, ni por número de peticiones, ni por cuenta.** No hay
  contador, ni ventana temporal, ni cola, ni captcha.
- **El único middleware que se añade a la aplicación es CORS** (`main.py:101-107`). No hay ningún
  otro: la búsqueda de `middleware` en todo `backend/` solo encuentra esas líneas y el `import` del
  que sale (`main.py:15`, `:101` y `:102`).
- **Está dicho por escrito en el propio código**, en la cabecera de `security.py` (`:8-10`): «Lo que
  NO se hace aquí y habrá que hacer antes de abrirlo a clientes: rotación de claves, revocación de
  tokens, **límite de intentos** y doble factor. Está anotado para que no se olvide.» Es la frase que
  contesta a esta pregunta sin tener que buscarla.
- **Lo que sí existe son topes «hacia dentro», y sirven para otra cosa**: que una petición no se
  desmadre, no que no haya muchas. Son la espera de cada llamada
  (`ESPERA_SEGUNDOS = 10.0`, `sigpac.py:64`; `ESPERA_IMAGEN_SEGUNDOS = 6.0`, `sigpac.py:68`;
  `ESPERA_SEGUNDOS = 15.0`, `iuws.py:104`), el recorte del tamaño de imagen a 64-1600 píxeles
  (`sigpac.py:489-490`), el tope de la caja del mapa a 0,5° (`mapa.py:108` con `:41`), el tope de 25
  recintos por búsqueda (`parcelas.py:37`) y la caché de 20 imágenes (`sigpac.py:72`).
- **Gasto que no es de red, y también sin límite:** `POST /api/cuenta/registro` deriva la clave con
  240.000 vueltas de PBKDF2 **y escribe cinco filas** por llamada (`security.py:23`, `cuenta.py:48-93`);
  `POST /api/cuenta/entrar` deriva la clave **aunque la cuenta no exista**, para no revelar qué
  correos están dados de alta (`cuenta.py:107-109`), así que se pueden probar claves sin freno ni
  retardo; y `/api/zonas-vulnerables/estado`, `/api/sigpac/estado` y `/api/interfaz` releen ficheros
  del disco en cada llamada.
- **Lo que NO se ha podido comprobar:** si el servidor de delante (nginx u otro) pone algún límite.
  **No hay ni un fichero de despliegue en el repositorio** —ni `Dockerfile`, ni `docker-compose`, ni
  `.conf` de nginx ni `systemd`; buscados por todo el árbol— y la única configuración del proyecto es
  `backend/pyproject.toml`, que es de `pytest` y `ruff`. Así que **del despliegue real no se puede
  decir nada desde aquí**: hay que preguntarlo o mirarlo en el servidor.

---

## 6. Tabla de decisión

Convenio de la última columna, que es lo que evita romper algo al cerrar una ruta:

- **«Solo pruebas»**: los que la llaman sin vale son pruebas de `backend/tests/**` o el recorrido de
  `scripts/humo.py`, y arreglarlos es añadir `headers=cuenta["cabeceras"]` o usar la fixture `cuenta`.
  No hay ninguna pantalla ni ningún script de fuera.
- **«Sí, la pantalla»**: un cliente de verdad (el navegador) la llama sin vale y **no puede mandarlo**.
  Cerrar esa ruta **rompe la aplicación** hasta que se cambie el cliente.
- **«Sí, y no se debe cerrar»**: es la puerta de entrada; cerrarla deja al agricultor fuera.

| Ruta | Grupo | Quién debería poder llamarla | Qué falta | ¿Rompe algún cliente si se cierra? |
|---|---|---|---|---|
| `POST /api/cuenta/registro` | Pública, hay que limitar | Cualquiera que se dé de alta (no hay otra forma) | Límite de altas por IP y por tiempo; no hay captcha ni tope | **Sí, y no se debe cerrar**: `app.js:3742`, `conftest.py:153` y `:164` |
| `POST /api/cuenta/entrar` | Pública, hay que limitar | Cualquiera que entre con su clave | Límite de intentos por cuenta **y** por IP, con retardo o bloqueo; y apuntar los intentos fallidos | **Sí, y no se debe cerrar**: `app.js:3744` |
| `GET /api/cuenta/certificado/estado` | Tiene que ser pública | La pantalla de entrar, sin vale | Nada | **Sí, y no se debe cerrar**: `app.js:906` y `:11344` |
| `POST /api/cuenta/entrar-con-certificado` | Tiene que ser pública | Quien trae un certificado validado por el servidor web | Nada en la ruta; **sí** que el programa no se exponga directamente con `CUEDIGITAL_CONFIAR_EN_CABECERAS=1` (y límite de intentos) | **Sí, y no se debe cerrar**: `app.js:917` |
| `GET /api/municipios` | Tiene que ser pública | Cualquiera (lista oficial del INE) | Nada (o caché HTTP, si algún día molesta) | Sí, **solo pruebas**: `test_parcelas_por_codigos.py:300` y `humo.py:429` |
| `POST /api/sigpac/buscar` | Pública, hay que limitar | Quien esté dando de alta sus tierras | Tope por IP y por tiempo (hoy puede encargar 26 llamadas al SIGPAC por petición) | Sí, **solo pruebas**: siete de `test_parcelas_por_codigos.py` (`:312`, `:335`, `:344`, `:360`, `:372`, `:378`, `:385`). La pantalla ya manda vale (`app.js:5977`) |
| `GET /api/sigpac/estado` | Pública, hay que filtrar | Quien administra la instalación | **Quitar `ruta` de la respuesta** (`sigpac.py:1038`): dice dónde está la carpeta de datos del servidor | Sí, **solo pruebas**: `test_sigpac.py:454` y `humo.py:1633` |
| `POST /api/sigpac/consultar` | **Debería pedir sesión** | Quien esté comprobando sus referencias (con vale) | `ExplotacionActual` (o `UsuarioActual`) y **usar `sigpac.pedir_recinto`** en vez de `httpx.get` suelto (`parcelas.py:617`) | **No rompe nada**: `test_sigpac.py:425`, `:446` y `humo.py:1653` ya llevan vale |
| `GET /api/zonas-vulnerables/estado` | Pública, hay que limitar | Quien administra la instalación | **Dejar de recargar el catálogo en cada petición** (`parcelas.py:1176` → `catalogos.py:787-819`), o devolverlo desde `/health` | Sí, **solo pruebas**: `test_listado_oficial_zv_cyl.py:90` y `test_registro_obligatorio.py:970` |
| `GET /api/mapa/estado` | Tiene que ser pública | Cualquiera | Nada | Sí, **solo pruebas**: `test_mapa_del_sigpac.py:403` y `humo.py:445` |
| `GET /api/mapa/imagen` | Pública, hay que limitar | La pantalla del mapa (aunque hoy no pueda mandar vale por un `<img>`) | Tope por IP; caché que no se pueda vaciar desde fuera (`sigpac.py:927-928`); y, si se quiere cerrar, **cambiar antes la pantalla** a `fetch` + memoria | **Sí, la pantalla**: `app.js:5568` con `<img src>` en `react/pantallas/mapa.js:39-40`; y seis pruebas (`test_mapa_del_sigpac.py:429`…) |
| `POST /api/mapa/punto` | Pública, hay que limitar | Quien esté eligiendo su tierra en el mapa | Tope por IP y por tiempo (3 llamadas al SIGPAC por petición), **o** pedirle la finca: aquí cerrarla es barato | Sí, **solo pruebas**: seis de `test_mapa_del_sigpac.py` (`:508`, `:534`, `:539`, `:543`, `:554`, `:586`). La pantalla ya manda vale (`app.js:5749`) |
| `GET /api/interfaz` | Tiene que ser pública | La pantalla, **antes** de entrar | Nada (una caché HTTP sería un lujo, no una necesidad) | **Sí, y no se debe cerrar**: `app.js:3590` llamado desde `:11344` sin vale |
| `GET /api/ayuda` | Tiene que ser pública | Quien quiera los textos de ayuda | Nada | Sí, **solo pruebas**: seis (`test_interfaz.py:280`, `test_registro_obligatorio.py:834` y `:852`, `test_medidas_preventivas.py:434`, `test_nitratos.py:352`, `test_cosecha_comercializada.py:594`) y `humo.py:419` y `:1745` |
| `GET /api/ayuda/{campo}` | Tiene que ser pública | Igual | Nada | Sí, **solo pruebas**: `test_registro_obligatorio.py:841` y `:846` |
| `GET /api/cuaderno-cyl/estado` | Tiene que ser pública | Quien vaya a importar el cuaderno de la Junta | Nada | Sí, **solo pruebas**: `humo.py:2565` y `test_cuaderno_cyl.py:524` |
| `GET /api/cuaderno-cyl/hojas` | Tiene que ser pública | Igual | Nada | **No rompe nada**: `humo.py:2793` y `test_cuaderno_cyl_exportar.py:413` ya llevan vale |
| `GET /api/iuws/version` | No es para personas | Quien hace la integración, con vale | Vale para `?llamar=1` (hoy hasta 2 llamadas de 15 s sin identificarse), y **límite o vale** en la parte que sale fuera | Sí, **solo pruebas** (`humo.py:1363`, `:1373` y las de `test_iuws*.py`, todas con vale) |
| `GET /api/iuws/comprobar-de-verdad` | No es para personas | El técnico de la integración | Nada en la ruta; **cambiar el `curl` de `docs/INTEGRACION_IUWS.md:666`** si se cierra | Sí, **solo pruebas**, más esa línea de la documentación |
| `POST /api/iuws/leer-respuesta` | No es para personas | Quien vaya a escribir a soporte | Nada | Sí, **solo pruebas** (`humo.py:1418`, `test_iuws.py:892` y `:913`) |
| `GET /api/iuws/mensajes` | No es para personas | El técnico de la integración | Nada | Sí, **solo pruebas** (`humo.py:1439`, `test_iuws.py:883`) |
| `POST /api/planes/validar` | **Debería pedir sesión** | El asistente del plan, con vale | `ExplotacionActual`, como en `registros.py:180` | **No rompe nada**: `test_plan_abonado.py:210` ya lleva vale |
| `POST /api/analiticas/validar` | **Debería pedir sesión** | El asistente del análisis, con vale | `ExplotacionActual` | **No rompe nada**: `test_analiticas.py:229` y `humo.py:912` ya llevan vale |
| `POST /api/medidas/validar` | **Debería pedir sesión** | El asistente de las medidas, con vale | `ExplotacionActual` (de las tres es la menos urgente: su cuerpo no lleva ningún identificador de finca) | **No rompe nada**: `test_medidas_preventivas.py:180` y `:190` ya llevan vale |
| `GET /health` | Tiene que ser pública | Un sistema de vigilancia | Nada | Sí, **solo pruebas**: `test_interfaz.py:278` |
| `GET /api` | Tiene que ser pública | Cualquiera que llegue a la API | Nada | Sí, **solo pruebas**: `test_interfaz.py:279` |

---

## 7. Por dónde empezar, en orden

1. **`POST /api/sigpac/consultar`** (`parcelas.py:604`): pedirle la finca y hacer que use
   `sigpac.pedir_recinto` en vez de `httpx.get` suelto. **No rompe ningún cliente** —todos los que la
   llaman ya llevan vale— y quita la única llamada a internet que sale desde un router.
2. **Las tres `/validar`** (`planes_api.py:159`, `analiticas_api.py:286`, `medidas_api.py:98`):
   añadirles `ExplotacionActual` como hace `registros.py:180`. Tampoco rompen a nadie, y cierran la
   excepción que permite que mañana alguien meta una consulta dentro sin que nada avise.
3. **Un límite de verdad, que hoy no existe en ninguna parte** (§5.2): lo mínimo, por IP y por tiempo,
   para `cuenta/registro`, `cuenta/entrar`, `sigpac/buscar`, `mapa/punto`, `mapa/imagen` y
   `iuws/version?llamar=1`. Sin esto, da igual lo demás: son seis puertas abiertas a gastar recursos
   de terceros y del propio servidor.
4. **La caché de las imágenes** (`sigpac.py:927-928`): que se vacíe lo más viejo y no todo, o que
   nadie de fuera pueda dejarla inservible con veinte cajas distintas.
5. **Recortes pequeños y baratos**: quitar `ruta` de `/api/sigpac/estado` (`sigpac.py:1038`) y dejar de
   recargar el catálogo de zonas vulnerables en cada llamada (`parcelas.py:1176`).

Y lo que **no** hay que tocar: `interfaz`, `cuenta/certificado/estado`, `entrar-con-certificado`,
`municipios`, `ayuda`, `ayuda/{campo}`, `cuaderno-cyl/estado`, `cuaderno-cyl/hojas`, `mapa/estado`,
`health` y `/api`. Cerrarlas no protegería nada y rompería pantallas, pruebas y la puerta de entrada.
