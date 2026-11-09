# Despliegue de CUE Digital para agricultores reales

**Qué es este documento.** El diagnóstico de lo que falta hoy para poner CUE Digital en un
servidor de verdad, las opciones que existen y lo que cuestan, la arquitectura que se
recomienda y por qué, el plan de puesta en marcha paso a paso, lo que obliga el RGPD y las
decisiones que tiene que tomar David.

**Qué NO es.** No es un despliegue hecho: **no hay servidor ni dominio**, así que no hay URL
pública. Lo que **sí** se ha hecho el 09/11/2026: **la imagen se construye** (`docker build`,
669 MB) y **el stack entero se ha levantado en local contra PostgreSQL 16 de verdad**
(app + base), con el recorrido de `backend/scripts/comprobar_despliegue.py`: alta de cuenta,
dos tierras (referencia de seis números y con recinto), **contorno pintado** (PNG 800×600 con
el GeoPackage real de Salamanca) y la observabilidad (204/200/403), todo en verde. Eso destapó
y cerró **un bloqueo de producción**: una base PostgreSQL nueva **no se podía crear** por dos
columnas booleanas con `DEFAULT 1` (§1.16). Lo que falta para tener URL pública es **una cuenta**
y un dominio: el paso exacto está en [`CUENTAS-Y-ACCESOS.md`](CUENTAS-Y-ACCESOS.md). Todo lo
que se afirma aquí está comprobado **ejecutándolo**, **leyendo el repositorio** (con fichero y
línea) o **consultando una fuente** (con dirección y fecha). Lo que no se ha podido comprobar
se dice: **«no verificado»**.

| Dato | Valor |
|---|---|
| Fecha del documento | 09/11/2026 |
| Rama | `integracion/cloud-estabilizacion-2026-10-21` |
| Último commit | `4ca5107` (2026-11-09) más los cambios de la ronda de despliegue |
| Python del entorno de desarrollo | **3.12.10** (`..\.venv\Scripts\python.exe --version`) |
| Pruebas declaradas por el proyecto | **6042** de Python (0 fallos) y **1319** de JavaScript (0 fallos), medido el 09/11/2026 |
| Tablas de la base | **67** en la base (66 declaradas con `__tablename__` en `backend/app/models.py` + `grupo_parcela`, la tabla de unión de los grupos de parcelas, que no tiene modelo). Comprobado al crear una base PostgreSQL 16 nueva el 09/11/2026 |
| Tamaño de `data/` (datos oficiales que lee el programa) | 12,5 MB |
| Tamaño de `backend/web/` (la pantalla, sin compilar) | 2,7 MB |
| Precios | consultados el **09/11/2026**, cada uno con su URL |

> **Sobre las líneas que se citan.** Los `fichero:línea` corresponden al commit `ed5157b`. Si
> otro cambio mueve un fichero (por ejemplo `backend/app/main.py`), el número baila; la
> referencia buena es el **nombre** de la función o de la constante, que va al lado.

**Artefactos que acompañan a este documento** (todos nuevos, en `deploy/`):

| Fichero | Para qué |
|---|---|
| `deploy/Dockerfile` | La imagen de la aplicación (Python 3.12, sin root, con el lector de letras) |
| `deploy/docker-compose.yml` | Caddy + aplicación + PostgreSQL, con los datos fuera de Docker |
| `deploy/Caddyfile` | HTTPS automático, proxy inverso y la segunda puerta del tamaño de subida |
| `deploy/.env.example` | **Ejemplo** de configuración, con valores de relleno. No hay ningún `.env` real |
| `deploy/copia.sh` | Copia diaria (base + adjuntos) y copia fuera de la máquina |
| `deploy/restaurar.sh` | Ensayo de restauración en un destino **nuevo**, sin tocar los datos buenos |
| `deploy/LEEME.md` | Cómo se levanta y cómo se comprueba, en corto |
| `backend/requirements-produccion.txt` | El driver de PostgreSQL (`psycopg`), que no está en el de desarrollo |

---

## 1. Qué falta hoy, punto por punto

Esto no es una lista de deseos: cada punto está comprobado en el código o en los documentos
del proyecto, y se dice **dónde**.

### 1.1. La base de datos: SQLite por defecto, y el driver de producción no está

- **El motor por defecto es SQLite.** `backend/app/database.py:24`:
  `URL_POR_DEFECTO = "sqlite:///./cuedigital.db"`. El fichero se crea **en el directorio
  desde el que se arranca**, así que la base depende de dónde se lance el programa.
- **La dirección se cambia con `CUEDIGITAL_DATABASE_URL`** (`database.py:27-28`,
  `url_base_datos()`), y se lee **al importar el módulo** (`database.py:52`,
  `engine = crear_engine()`). Por eso todos los guiones del proyecto fijan esa variable
  **antes** de importar `app` (por ejemplo `scripts/sonda_postgresql.py:53-59`).
- **`backend/requirements.txt` NO trae el driver de PostgreSQL.** Tiene 25 líneas y
  ninguna es `psycopg`; lo dice el propio README (`README.md:64-72`: «hay que instalar
  además el driver, que **no viene en `requirements.txt`**») y lo repite la sonda
  (`scripts/sonda_postgresql.py:36-37`). Una instalación hecha solo con ese fichero
  **no arranca** con una dirección de PostgreSQL.
  **Arreglado en este despliegue** con `backend/requirements-produccion.txt`
  (`psycopg[binary]==3.3.8`, versión comprobada en PyPI el 09/11/2026), sin tocar el
  fichero de desarrollo.
- **`requirements.txt` mezcla dependencias de la aplicación y de los tests.** La imagen de
  producción instala el fichero entero porque la aplicación **sí** importa en tiempo de
  ejecución `httpx` (`sigpac.py`, `sigpac_cache.py`, `iuws_cliente.py`,
  `routers/parcelas.py`), `openpyxl` (`cuaderno_cyl.py`, `cuaderno_cyl_exportar.py`,
  `registro_oficial_de_productos.py`) y `pdfplumber` (`facturas.py:636`), aunque en
  `requirements.txt:15-25` están bajo el comentario «Solo para desarrollo y tests». Ese
  comentario es **inexacto** y conviene corregirlo; separar las dos listas es trabajo
  pendiente (apartado 6).
- **Versiones reales comprobadas** (`backend/requirements.txt`, 09/11/2026): `fastapi
  0.141.1`, `uvicorn[standard] 0.53.0`, `SQLAlchemy 2.0.54`, `pydantic 2.13.5`,
  `pydantic-settings 2.15.0`, `python-multipart 0.0.22`, `reportlab 5.0.1`, `jsonschema
  4.25.1`; y, en la parte de desarrollo, `pytest 9.1.1`, `httpx 0.28.1`, `openpyxl 3.1.5`,
  `pdfplumber 0.11.9`, `pyyaml 6.0.3`, `ruff 0.14.0`. **Python del entorno: 3.12.10**, y la
  imagen de producción usa la misma versión (3.12) a propósito.

### 1.2. Las tablas se crean y se «migran» al arrancar, y en PostgreSQL eso tiene un límite

- **`crear_tablas()` se ejecuta al arrancar** (`backend/app/main.py:107-108`, dentro de
  `ciclo_de_vida`; la función está en `backend/app/database.py:1217`). Crea las tablas que
  faltan, **añade columnas** a las que ya existen (`asegurar_columnas`, `database.py:129`)
  y pone al día los índices (`asegurar_indices`, `database.py:816`).
- **No hay herramienta de migraciones** (ni Alembic ni nada equivalente): no aparece en
  `requirements.txt` ni en el árbol.
- **La puesta al día tiene un límite duro en PostgreSQL.** Las reconstrucciones de tabla
  que en SQLite se hacen copiando filas (`reconstruir_para_poder_decir_no_se` y
  `reconstruir_para_que_nazcan_las_claves_ajenas`) **no se pueden hacer en PostgreSQL desde
  el arranque**, y el código **para y lo dice**: `database.py:405-419` y `:348-353`
  lanzan un `RuntimeError` («en PostgreSQL … hace falta una migración de verdad, con su
  copia y su herramienta. No se ha tocado nada»). Y `main.py:100-146` lo cuenta en
  castellano antes de dejar subir el error.
- **Consecuencia práctica:** una base PostgreSQL **nueva** se crea bien (el modelo ya nace
  con las columnas correctas). Lo que no se puede hacer solo es un cambio futuro que
  necesite **cambiar** una columna (nulabilidad, tipo, clave ajena). Ese día hace falta
  adoptar migraciones de verdad y parar el programa para aplicarlas.
- **Añadir una columna nueva sí funciona** en PostgreSQL (`ALTER TABLE … ADD COLUMN`), y
  también crear índices que falten. Lo que no se rehace fuera de SQLite es la
  **definición** de un índice que ya existe (`database.py:898-899`): se acepta como
  limitación conocida.

### 1.3. Los ficheros del agricultor van a disco, no a la base

- **Carpeta configurable con `CUEDIGITAL_ADJUNTOS`** (`backend/app/adjuntos.py:69-74`).
  Por defecto es `datos/adjuntos` **dentro del repositorio**, y está en `.gitignore`
  (porque son papeles con su NIF).
- **Tope de 12 MiB por fichero** (`adjuntos.py:34`, `MAXIMO_BYTES = 12 * 1024 * 1024`) y
  se lee **por trozos**, cortando en cuanto pasa (`leer_el_fichero`, `adjuntos.py:111-144`).
- **El nombre del navegador no se usa como ruta**: la ruta la pone el programa
  (`guardar_en_disco`, `adjuntos.py:147-176`) y al descargar se comprueba que sigue dentro
  de la carpeta (`ruta_segura`, `adjuntos.py:179-190`).
- **Qué falta para producción:** que esa carpeta esté **fuera** del repositorio, en un
  disco con sitio, con permisos del usuario del contenedor y **dentro de la copia de
  seguridad**. Eso es lo que hace `deploy/docker-compose.yml` con `CARPETA_DATOS` y
  `deploy/copia.sh`.

### 1.4. La clave que firma los vales de sesión

- **`CUEDIGITAL_SECRETO`** (`backend/app/security.py:66-76`). Si no está, el programa
  genera una aleatoria **en cada proceso**: es preferible a arrancar con una clave conocida,
  pero significa que **las sesiones se caen al reiniciar** y que con varios procesos unos
  vales no valdrían en otros.
- **Los vales duran 30 días** (`security.py:32`, `DURACION_TOKEN_SEGUNDOS =
  60*60*24*30`), van firmados con HMAC-SHA256 y **no se pueden revocar**: no hay lista de
  revocados ni rotación. El propio fichero lo dice en su cabecera (`security.py:8-10`:
  «Lo que NO se hace aquí y habrá que hacer antes de abrirlo a clientes: rotación de
  claves, revocación de tokens, límite de intentos y doble factor»).

### 1.5. No hay límite de intentos, ni de peticiones, ni bloqueo de cuenta

Comprobado y documentado en `docs/T01_REVISION_RUTAS_SIN_SESION.md:870-895`:

- **No hay limitación por IP, ni por tiempo, ni por número de peticiones, ni por cuenta.**
  No hay contador, ni ventana temporal, ni captcha.
- **El único middleware de la aplicación es CORS** (`main.py:169-175`).
- **`POST /api/cuenta/entrar` deriva la clave aunque la cuenta no exista**
  (`routers/cuenta.py:103-115`), a propósito, para no revelar qué correos están dados de
  alta. Eso está bien, pero sin límite de intentos se pueden probar claves sin freno.
- **Delante del programa no hay nada que limite**, porque no había despliegue. En este
  despliegue, Caddy **no** pone límite de intentos; es una decisión pendiente (apartado 6).

### 1.6. CORS fijado a `localhost:5173`

`main.py:169-175` permite solo `http://localhost:5173` y `http://127.0.0.1:5173` (el
servidor de desarrollo del interfaz). En producción la pantalla se sirve **desde el mismo
dominio**, así que CORS no interviene y **no hay que tocarlo**. Se apunta porque es la señal
de que la aplicación no se ha pensado para varios dominios ni para una pantalla en otro
origen.

### 1.7. `/health` existe, pero es superficial

`main.py:268-273`:

```json
{"estado": "ok", "zonas_vulnerables_cargadas": true}
```

**No consulta la base de datos.** Sirve para saber que el proceso atiende, no que
PostgreSQL esté bien. Por eso el plan de puesta en marcha comprueba la base **aparte**
(contar las 67 tablas; ver el paso 5). Si algún día se usa como sonda de un vigilante externo, conviene
que también mire la base, o que el vigilante compruebe algo que la use.

### 1.8. La pantalla la sirve la propia aplicación, y hay una caché que se queda pegada

- **Los ficheros estáticos los sirve la aplicación** (`main.py:84`, `RUTA_WEB`; y el
  montaje final en `main.py:286-290`). No hay compilación ni Node en el servidor.
- **Los tipos MIME se declaran a mano** (`main.py:69-78`) porque en Windows el registro
  del sistema puede devolver un `.js` como `text/plain` y el navegador rechaza el módulo
  sin decir por qué.
- **El service worker guarda la aplicación en el móvil** (para el campo sin cobertura) y
  su caché lleva un nombre versionado: `backend/web/service-worker.js:277`,
  `const CACHE = "cuedigital-2026-10-22-79"`. **Ese nombre se sube en el mismo cambio que
  toque ficheros de la pantalla**; si no, un móvil que abra la aplicación después de una
  actualización **sin cobertura** se queda con los ficheros viejos (está explicado en el
  propio fichero, líneas 16-21). Es una regla de despliegue, no un detalle.

### 1.9. La caché del SIGPAC: gigas de disco

- **`CUEDIGITAL_SIGPAC_CACHE`** (`backend/app/sigpac_cache.py:133-142`); por defecto
  `datos/sigpac_cache` dentro del repositorio.
- Son los GeoPackage de los recintos que se bajan del FEGA: el estado del proyecto habla de
  **628 MB de ZIP y 1.070 MB de `.gpkg` por provincia y campaña** (`ESTADO-AGENTE.md:78`).
  Eso no cabe en la imagen ni debe ir en la copia de seguridad: se puede volver a bajar.
- **En el servidor hay que darle un sitio fuera del código** (`/datos/sigpac_cache`, como
  hace el compose) y **vigilar el disco**; el plan de capacidad lo cuenta.

### 1.10. El lector de letras (OCR) es un programa aparte

- **`CUEDIGITAL_OCR`** (`backend/app/ocr.py:104`) permite decir dónde está el ejecutable;
  si no, se busca en el PATH y en rutas conocidas (`ocr.py:42-48`).
- **El idioma español vive en el repositorio**: `data/ocr/tessdata/spa.traineddata`
  (2.293.443 bytes, comprobado). Se usa con `TESSDATA_PREFIX` **sin tocar la instalación
  del sistema** (`ocr.py:75-94`).
- **Sin lector, la aplicación funciona**: lo dice en la pantalla y no inventa nada
  (`ocr.py:9-17`). En la imagen se instala `tesseract-ocr` para que el servidor haga lo
  mismo que el ordenador de desarrollo; si se quita, el programa sigue arrancando.

### 1.11. El IUWS: el certificado y el alta

- **`CUEDIGITAL_IUWS_CERTIFICADO` y `CUEDIGITAL_IUWS_CLAVE`**
  (`backend/app/iuws_cliente.py:80-81`), más `CUEDIGITAL_IUWS_BASE`, `_APP`, `_CIF`,
  `_DOMINIO`, `_ALTA` (`iuws.py:716-724`).
- **Lo que no se resuelve con una variable:** el **alta del dominio del certificado** en el
  interfaz de la Junta. El 27/09/2026 la llamada de producción contestó «Dominio del
  certificado no registrado en el sistema» (`README.md:773-887` y
  `docs/LO_QUE_PIDE_LA_JUNTA.md:221`). Es una decisión/gestión de David, no del servidor.
- **El certificado es de cliente (mTLS)**: se monta en el contenedor como fichero y se
  apunta con las variables; **no se copia al repositorio**. `.gitignore` ya excluye
  `*.key`, `*.p12` y `*.pfx` — pero un `.pem` **sí** pasaría, así que se guarda fuera del
  árbol.

### 1.12. Entrar con el certificado digital: preparado, apagado y sin probar

- **La aplicación no valida certificados**: se cree lo que le ponga el servidor de delante,
  y **solo si se enciende a mano** `CUEDIGITAL_CONFIAR_EN_CABECERAS`
  (`backend/app/certificados.py:301-309`). Las cabeceras son `X-SSL-Client-Subject` y
  `X-SSL-Client-Verify`, y la segunda tiene que valer exactamente `SUCCESS`
  (`certificados.py:320-330`).
- **Está apagado por defecto porque encenderlo sin un proxy que valide es un agujero**: el
  propio docstring lo explica (`certificados.py:301-308`).
- **Caddy puede hacerlo** (`client_auth` + `{tls_client_subject}`), y el `Caddyfile`
  trae el bloque **comentado y marcado como no probado**. El problema de fondo es que si se
  exige certificado en todo el sitio se rompe entrar con correo y clave, que tiene que
  seguir funcionando siempre. Hacerlo bien es trabajo aparte (apartado 6).

### 1.13. Copias de seguridad: hay para SQLite, no para PostgreSQL

- **Para SQLite hay mucho y bueno**: copia coherente antes de migrar
  (`database.py:448-519`), comprobación de que la copia tiene las mismas tablas **y las
  mismas filas** (`_copia_tiene_lo_mismo`, `database.py:649`), ensayo de restauración en un
  destino nuevo (`database.py:562-599`), guion de aceptación
  (`backend/scripts/verificar_la_copia_y_la_restauracion.py`) y una revisión independiente
  entera (`docs/ACEPTACION_COPIA_Y_MIGRACION.md`). La regla que sale de ahí y hay que
  respetar: **restaurar en un destino nuevo y usar la copia, no solo mirar que el fichero
  existe**.
- **Para PostgreSQL no hay nada**: el propio código dice que «en PostgreSQL esto se hace
  con su herramienta» (`database.py:405-419`) y no hay `pg_dump` en ningún sitio del árbol.
  **Eso es lo que añade este despliegue** (`deploy/copia.sh` y `deploy/restaurar.sh`).

### 1.14. Lo que no había en el repositorio (y ahora hay, o se ha decidido no hacer)

- **No había ni un fichero de despliegue**: ni `Dockerfile`, ni `docker-compose`, ni
  Caddyfile, ni nginx, ni `systemd`. Está comprobado en
  `docs/T01_REVISION_RUTAS_SIN_SESION.md:892-895` y se ha vuelto a comprobar hoy: en el
  árbol no hay ninguno. Ahora están en `deploy/`.
- **GitHub Actions está PROHIBIDO en este proyecto.** `PROTOCOLO-AUTONOMIA.md:156-161`:
  «David ha agotado la cuota gratuita de GitHub y **todas las ejecuciones de GitHub Actions
  fallan**. **PROHIBIDO usar GitHub Actions**». Existe un workflow antiguo
  (`.github/workflows/ci.yml`, «Pruebas del CRM»), que **no se ha tocado**: es historia del
  repositorio, no una vía de despliegue. Este despliegue **no lo usa**: se actualiza a mano
  con `git pull` y `docker compose up -d --build`. (Ojo: `DESARROLLO_EN_LA_NUBE.md:54`
  todavía dice que Actions ejecuta las suites; es un documento del 19/10/2026, anterior a
  la política del 04/11/2026.)
- **No hay correo saliente.** El programa no manda correos (`README.md:111-128`), así que
  «he olvidado mi clave» **no existe como función**: David cambia la clave desde el propio
  servidor con `backend/scripts/cambiar_la_clave.py`, apuntando
  `CUEDIGITAL_DATABASE_URL` a la base de producción. Es un procedimiento de soporte que hay
  que tener escrito y probado, y hay que decirle al agricultor **cómo pedirlo**.
- **No hay supresión de cuenta ni exportación completa** (derechos de acceso, supresión y
  portabilidad del RGPD): hay exportación del cuaderno en PDF/CSV y corrección/anulación de
  apuntes, pero no un «borrar mi cuenta y mis datos». Es trabajo pendiente para abrir a
  terceros (apartado 5).

### 1.15. Lo que el proyecto avisa de sí mismo y hay que hacer antes de la primera firma

- **La forma canónica del cuaderno firmado tiene que estar congelada antes de la primera
  firma de un agricultor de verdad**: añadir un campo o cambiar cómo se escriben los
  números invalida todas las firmas anteriores (`README.md:197-200`). Hay un número de
  versión (`VERSION_CANONICA`) para eso.
- **La suite se ejecuta sobre SQLite.** El motor de producción es PostgreSQL y el propio
  proyecto arrastra la asignatura de la pasada completa en ese motor. Antes de abrir, hay
  que correr la suite **contra PostgreSQL** una vez en el servidor: `tests/conftest.py`
  acepta `CUEDIGITAL_SUITE_SOBRE` justo para eso (`conftest.py:31-49`), y hay una sonda
  hecha (`scripts/sonda_postgresql.py`).

---

### 1.16. El bloqueo que destapó la prueba del despliegue: booleanos con `DEFAULT 1` (cerrado)

La imagen se construyó y se levantó contra un **PostgreSQL 16 nuevo**, y la aplicación **no
arrancó**:

```
sqlalchemy.exc.ProgrammingError: (psycopg.errors.DatatypeMismatch)
column "puede_modificar" is of type boolean but default expression is of type integer
ERROR: Application startup failed. Exiting.
```

En SQLite una columna booleana es un entero y `DEFAULT 1` vale; en PostgreSQL es un `boolean`
de verdad y el `CREATE TABLE` aborta. Es un **bloqueo duro de producción**: con una base nueva
no se puede arrancar. Se cerró el 09/11/2026 con dos cambios y sus pruebas:

1. `backend/app/models.py:168-169` — las dos únicas columnas booleanas con
   `server_default=text("1")` pasan a `server_default=text("true")`, que vale en los dos motores.
2. `backend/app/database.py:202-206` (**`_valor_por_defecto`**) — al añadir una columna booleana
   a una tabla que ya existe, el `ALTER TABLE ... ADD COLUMN ... DEFAULT` decía `1`/`0` y en
   PostgreSQL fallaba **en silencio**: el error se apuntaba en «imposibles» y la columna no
   existía, así que reventaría después, al consultarla. Ahora dice `TRUE`/`FALSE`.

La prueba que impide que vuelva es `backend/tests/test_booleans_en_postgresql.py`: compila el
DDL con el dialecto de PostgreSQL **sin servidor** y recorre **todas** las tablas del modelo, así
que caza la próxima columna booleana que se añada mal. Con el arreglo, el stack arranca contra
PostgreSQL 16 y crea las **67 tablas** (66 del modelo + `grupo_parcela`).

## 2. Opciones gratuitas o baratas (precios consultados el 09/11/2026)

> **Cómo leer las tablas.** «Sin IVA» es lo que pone la página del proveedor. El IVA
> aplicable depende de quién contrate (empresa con NIF-IVA intracomunitario o particular)
> y se confirma en la factura; para las estimaciones se usa el **21 % general español**.
> Los precios en dólares se dejan en dólares: **no se convierten** porque el cambio no se
> ha comprobado. **Todo lo que no tenga fuente se marca «no verificado»** y no se inventa.
> Las páginas cambian: antes de contratar hay que volver a mirarlas.

### 2.1. Servidor privado virtual (VPS) en Europa

| Opción | Precio | Qué incluye | Fuente (consultada 09/11/2026) |
|---|---|---|---|
| **Hetzner CX23** | **5,99 €/mes sin IVA** (≈ 7,25 € con 21 %) | 2 vCPU, 4 GB RAM, 40 GB NVMe, 20 TB de tráfico | <https://www.hetzner.com/cloud/cost-optimized/> |
| **Hetzner CAX11** (ARM) | **6,49 €/mes sin IVA** (≈ 7,85 € con 21 %) | 2 vCPU Ampere, 4 GB, 40 GB NVMe, 20 TB | <https://www.hetzner.com/cloud/cost-optimized/> |
| **Hetzner CX33** | **8,99 €/mes sin IVA** | 4 vCPU, 8 GB, 80 GB NVMe, 20 TB | <https://www.hetzner.com/cloud/cost-optimized/> |
| **Hetzner, plan «Regular»** | desde **6,49 €/mes sin IVA** (CPX02: 1 vCPU, 1 GB, 20 GB) | CPX12 (1 vCPU/2 GB/40 GB) 11,99 €; CPX22 (2 vCPU/4 GB/80 GB): **precio no leído**, no verificado | <https://www.hetzner.com/cloud/regular-performance/> |
| **Contabo Cloud VPS Plus 4** | **13,50 €/mes** | 4 vCPU, 8 GB, 150 GB, tráfico ilimitado | <https://www.vpsbenchmarks.com/compare/contabo> (actualizado 09/10/2026) |
| Contabo, plan de entrada | **no verificado** | Su página oficial no se pudo leer (se sirve con JavaScript y no devolvió la tabla) | <https://contabo.com/en/vps/> |
| **OVHcloud VPS-4** | **23,48 €/mes** | 8 vCPU, 24 GB, 200 GB, tráfico ilimitado | <https://www.vpsbenchmarks.com/compare/ovhcloud> (actualizado 23/10/2026) |
| OVHcloud, gama barata | **no verificado** | La página oficial no devolvió los precios | <https://www.ovhcloud.com/es-es/vps/> |

**Dos avisos que no se pueden callar:**

1. Al consultar la página de Hetzner, **los planes baratos aparecían como «currently not
   available»**. El precio es el publicado, pero **la disponibilidad hay que comprobarla al
   contratar**; si no hay, la alternativa es CAX11 o CX33.
2. Los precios de Hetzner son **sin IVA** y la empresa es alemana: si se contrata como
   empresa con NIF-IVA intracomunitario, el IVA se autoliquida en España; si se contrata
   como particular, puede aplicar el IVA alemán (19 %). **No verificado**: se confirma en
   la factura.

**Qué pasa si se supera el plan:** no hay «recargo automático»: el servidor tiene un tope de
precio mensual (Hetzner lo dice en su página: «Your server's bill will never exceed its
monthly price cap»). Si se necesita más, se cambia de plan (CX33, 8,99 €) o se pide más
disco. El tráfico incluido son 20 TB: muy por encima de lo que va a gastar un cuaderno.

### 2.2. Plataformas gestionadas (PaaS)

| Opción | Precio | Plan gratuito y límite | Al superarlo | Fuente (09/11/2026) |
|---|---|---|---|---|
| **Render** | Plan gratuito: 0 $ | 0,1 CPU / 512 MB; **se apaga a los 15 min sin tráfico** (tarda ~1 min en despertar); **750 horas/mes**; **el disco es efímero: lo que se escriba se pierde** en cada reinicio o despliegue; sin disco persistente en el plan gratuito. Su PostgreSQL gratuito son **1 GB y caduca a los 30 días** (después, 14 días de gracia y se borra), sin copias | Se factura el exceso de ancho de banda; si no hay método de pago, **suspenden los servicios gratuitos** hasta el mes siguiente | <https://render.com/docs/free> |
| **Fly.io** | **No hay plan gratuito**: prueba de 1 $ durante 7 días. Máquina `shared-cpu-1x` 512 MB: **3,69 $/mes**; 1 GB: 6,70 $/mes; volumen: **0,15 $/GB/mes**; PostgreSQL gestionado desde **38 $/mes** | — | Se paga por uso; no hay tope gratuito que superar | <https://docs.fly.io/about/pricing> |
| **Railway** | Plan «Free» 0 $ con **1 $/mes de crédito**; «Hobby» **5 $/mes** con 5 $ incluidos | Free: 1 vCPU / 0,5 GB, **volumen máximo 500 MB**, **0 dominios propios**; Hobby: volumen hasta 5 GB, 2 dominios propios | Se paga el uso por segundo (memoria 10 $/GB/mes, CPU 20 $/vCPU/mes, volúmenes 0,15 $/GB/mes, salida 0,05 $/GB) | <https://railway.com/pricing.md> |
| **Render (planes de pago)** | **no verificado** | La página de precios no devolvió las tarifas de los planes de pago en la consulta | — | <https://render.com/pricing> |

**Por qué esto importa para CUE Digital, y no es una opinión:** la aplicación **escribe los
ficheros del agricultor en disco** (`backend/app/adjuntos.py`) y **crea y cambia las tablas
al arrancar** (`backend/app/database.py`). En un plan gratuito de PaaS, el disco se pierde al
reiniciar (Render) y el PostgreSQL gratuito caduca a los 30 días (Render). **Un plan
gratuito de PaaS no sirve para guardar los papeles de un agricultor**: sirve para una
demostración.

### 2.3. PostgreSQL gestionado con plan gratuito, o en la misma máquina

| Opción | Precio | Plan gratuito y límite | Al superarlo | Fuente (09/11/2026) |
|---|---|---|---|---|
| **PostgreSQL en la misma máquina** | **0 €** de licencia (PostgreSQL License, tipo BSD/MIT) + el disco del VPS | Todo el que quepa en el servidor | Se cambia de servidor o se separa la base | <https://www.postgresql.org/about/licence/> |
| **Neon** | Gratis: **0 $**; planes de pago por uso | 1 GB de almacenamiento por proyecto (20 GB por cuenta), 100 «CU-hours» por proyecto y mes, **se suspende a los 5 min de inactividad** (no se puede desactivar), 5 GB de salida | Plan «Launch»: 0,106 $/CU-hora, 0,35 $/GB-mes de almacenamiento; sin cuota mínima | <https://neon.com/docs/introduction/plans> |
| **Supabase** | Gratis: **0 $**; Pro desde **25 $/mes** | 500 MB de base de datos, 1 GB de ficheros, 5 GB de salida, **se pausa tras 1 semana de inactividad**, 2 proyectos activos | Pro: 8 GB de disco incluidos y luego 0,125 $/GB; ancho de banda 250 GB y luego 0,09 $/GB; copias diarias de 7 días | <https://supabase.com/pricing> |

**Comparación honesta para este caso:** con **una sola máquina** se tiene PostgreSQL sin
límite de plan gratuito, sin suspensión por inactividad, sin latencia de red y **con los
adjuntos al lado** (que es lo que la aplicación necesita). Un PostgreSQL gestionado gratuito
obliga a **dos sitios** donde guardar cosas (base y ficheros) y a **dos copias de
seguridad** distintas, y añade el riesgo de que la base se suspenda o caduque. Para un
cuaderno que en el campo tiene que responder, eso es peor negocio.

### 2.4. Almacenamiento de las fotos

| Opción | Precio | Límite gratuito | Al superarlo | Fuente (09/11/2026) |
|---|---|---|---|---|
| **Volumen del propio VPS** | incluido en los 40 GB (≈ 30 GB útiles para adjuntos) | — | Se amplía el disco del VPS (precio del proveedor: **no verificado**) o se pasa a almacenamiento externo | <https://www.hetzner.com/cloud/cost-optimized/> |
| **Cloudflare R2** | **0,015 $/GB-mes** (clase estándar); **salida gratis** | **10 GB-mes gratis**, 1 millón de operaciones A y 10 millones B al mes | 0,015 $/GB-mes y 4,50 $/millón de operaciones A | <https://developers.cloudflare.com/r2/pricing/> (página actualizada el 30/10/2026) |
| **Hetzner Object Storage** | **6,49 €/mes sin IVA** | Incluye **1 TB** de almacenamiento y 1 TB de salida | Pago por uso por encima | <https://www.hetzner.com/storage/object-storage/> |
| **Wasabi** | **7,99 $/TB-mes** (pago por uso), sin cobrar salida ni peticiones | No hay plan gratuito publicado (prueba) | Se paga la capacidad; **duración mínima de almacenamiento: no verificada** | <https://wasabi.com/pricing> |
| **Backblaze B2** | **no verificado** | La tabla de precios de la página oficial no se pudo leer en la consulta | — | <https://www.backblaze.com/cloud-storage/pricing> |

**Lo que se recomienda:** para el arranque, **los adjuntos en el volumen del VPS** (es lo
que la aplicación ya sabe hacer, sin cambiar una línea) y **la copia de fuera en R2**, que
con 10 GB gratis cubre de sobra la base y los adjuntos de los primeros agricultores. El
almacenamiento externo para las fotos **no se puede enchufar sin tocar código**: hoy
`adjuntos.py` escribe en un sistema de ficheros. Eso es una decisión de más adelante
(apartado 3).

### 2.5. TLS (el candado del navegador): 0 €

| Opción | Precio | Notas | Fuente (09/11/2026) |
|---|---|---|---|
| **Caddy + Let's Encrypt** | **0 €** | Caddy pide y renueva el certificado solo, y redirige HTTP a HTTPS. Let's Encrypt es una entidad sin ánimo de lucro que da certificados gratis | <https://letsencrypt.org/> y <https://caddyserver.com/docs/automatic-https> |
| Certificado de pago | no se necesita | — | — |

Aviso útil: Let's Encrypt **acorta la vida de los certificados a 64 días desde febrero de
2027** (<https://letsencrypt.org/2026/10/07/64-day-certs>). Con Caddy no hay que hacer nada:
renueva solo. Si algún día se cambia de servidor web, hay que tenerlo en cuenta.

### 2.6. Copias de seguridad

| Pieza | Coste | Qué cubre | Fuente |
|---|---|---|---|
| `pg_dump` + `tar` en el servidor | **0 €** | El día a día; **no protege** de que se rompa el servidor | Herramientas del propio PostgreSQL/ Linux |
| Copia fuera en **Cloudflare R2** | **0 €** hasta 10 GB-mes | La base + los adjuntos de los primeros agricultores | <https://developers.cloudflare.com/r2/pricing/> |
| Copia fuera en **Hetzner Object Storage** | **6,49 €/mes sin IVA** | Hasta 1 TB, con salida incluida | <https://www.hetzner.com/storage/object-storage/> |
| Vigilar que la copia se hace | **0 €** | Un fallo silencioso de la copia es el peor fallo | `deploy/copia.sh` avisa si no hay copia remota |

**Lo que hay que hacer, y no es opcional:** una copia **fuera de la máquina** y **un ensayo de
restauración de verdad**, con fecha apuntada. El proyecto ya tiene esa cultura para SQLite
(`docs/ACEPTACION_COPIA_Y_MIGRACION.md`); aquí se traslada a PostgreSQL con
`deploy/restaurar.sh`.

### 2.7. Observabilidad: la del propio programa (0 €), y fuera hasta cierto punto

**Lo primero que hay que saber: la observabilidad ya está dentro del programa** (09/11/2026).
Mide **errores**, **uso por pantalla** y el **embudo** de uso, y se lee por una puerta propia
protegida con su token; el detalle está en [`docs/OBSERVABILIDAD.md`](OBSERVABILIDAD.md). Cuesta
**0 €** y no necesita ningún proveedor. **Lo de esta tabla es lo que se añade por fuera**, y
ninguna de estas cosas es obligatoria: son comodidades.

| Opción | Precio | Gratis hasta | Al superarlo | Fuente (09/11/2026) |
|---|---|---|---|---|
| **UptimeRobot** | **0 €** el plan Free | **50 monitores**, comprobación cada **5 minutos**, 1 página de estado, retención de datos de 3 meses | Plan Solo desde 10 €/mes (60 s), Team desde 41 €/mes (30 s) | <https://uptimerobot.com/pricing.md> |
| **Grafana Cloud** | **0 €** el plan Free | 10.000 series de métricas al mes, **14 días** de retención | Plan Pro desde **19 $/mes** + uso | <https://grafana.com/pricing/> |
| **Sentry** | **0 €** el plan Developer | El plan gratuito existe, pero **la cuota exacta no está en la documentación consultada: no verificado**. Los planes de pago incluyen 50.000 errores, 5 GB de registros, 5 GB de métricas, 1 GB de adjuntos, 1 monitor de disponibilidad y 1 de cron | Planes Team/Business (precio **no verificado**) | <https://docs.sentry.io/pricing/> y <https://sentry.io/pricing/> |

**Para qué sirve cada uno, sin humo:** UptimeRobot avisa de que el servidor no contesta (es
lo primero que hay que tener, y cuesta 0 €). Grafana Cloud sirve si algún día se quieren
métricas. Sentry solo tiene sentido **cuando la aplicación integre un SDK de errores**; hoy
no lo lleva, así que instalarlo no da nada todavía. Mientras tanto, los registros de `app` y
de `caddy` (que se ven con `docker compose logs`) son la observabilidad real.

### 2.8. Resumen de la combinación recomendada

| Pieza | Elección | Coste mensual |
|---|---|---|
| Servidor | Hetzner CX23 (2 vCPU / 4 GB / 40 GB) | 5,99 € sin IVA |
| Sistema, TLS | Ubuntu + Caddy + Let's Encrypt | 0 € |
| Base de datos | PostgreSQL 16 en la misma máquina | 0 € |
| Fotos | volumen del servidor (los 40 GB) | incluido |
| Copia fuera | Cloudflare R2 (≤ 10 GB) | 0 € |
| Vigilancia | UptimeRobot Free | 0 € |
| **Total** | | **5,99 € sin IVA · ≈ 7,25 € con el 21 % de IVA** |
| Dominio | no incluido | **no verificado** |
| Si CX23 no hay | CAX11 | 6,49 € sin IVA · ≈ 7,85 € con IVA |

**Las tres cifras que resumen la recomendación:**

- **Coste: ≈ 7,25 €/mes con IVA** (sin contar el dominio, que no se ha podido verificar).
- **Capacidad: 150–200 agricultores** de alta con esta configuración (el primer límite es el
  disco de las fotos, no la CPU) y **10 a la vez** como número medido, con la rodilla entre 10 y
  25 (`docs/PRUEBAS_DE_CARGA.md`, medido el 09/11/2026).
- **Esfuerzo: 10–12 horas** (estimación, no medida; el desglose está en el apartado 4).

---

## 3. Arquitectura recomendada

### 3.1. La recomendación, en un dibujo

```
                     internet
                        │  443 (HTTPS) y 80 (redirección)
                        ▼
            ┌───────────────────────┐
            │        Caddy          │  certificado de Let's Encrypt, solo
            │  (el único público)   │  tope de subida de 15 MB
            └───────────┬───────────┘
                        │ red interna de Docker (sin publicar puertos)
                        ▼
            ┌───────────────────────┐
            │   aplicación (uvicorn)│  una sola instancia; crea y pone
            │   FastAPI + pantalla  │  al día las tablas al arrancar
            └───────┬───────┬───────┘
                    │       │
     ┌──────────────▼─┐   ┌─▼──────────────────────────┐
     │  PostgreSQL 16 │   │ /srv/cuedigital/datos/      │
     │  volumen del   │   │   adjuntos/  (fotos, PDFs)  │
     │  servidor      │   │   sigpac_cache/ (se rebaja) │
     └────────────────┘   └─────────────────────────────┘
                    │
                    ▼  una vez al día
        pg_dump + tar → /srv/cuedigital/copias/ → rclone → Cloudflare R2
```

**Una sola máquina pequeña, con los datos fuera de los contenedores**, y una copia que sale
de la máquina. Esa es la recomendación.

### 3.2. Por qué esta y no las otras

| Alternativa | Por qué no, mirando este repositorio |
|---|---|
| **PaaS gratuito (Render, Railway)** | La aplicación **escribe en disco** (`adjuntos.py`) y **hace cambios de esquema al arrancar** (`crear_tablas`). Render gratuito borra el disco al reiniciar y su PostgreSQL gratuito **caduca a los 30 días**; Railway gratuito tiene **500 MB de volumen y ningún dominio propio**. No es un problema de precio: es que **no cumple** lo que la aplicación necesita |
| **Fly.io** | Ya no tiene plan gratuito, y su PostgreSQL gestionado arranca en **38 $/mes**, que es 6 veces el VPS entero. El VPS con PostgreSQL dentro cuesta una fracción |
| **PostgreSQL gestionado (Neon, Supabase) + app en otro sitio** | Dos proveedores, dos copias, dos contratos de encargado y una latencia de red en cada petición. Los planes gratuitos **se suspenden por inactividad** (Neon a los 5 minutos, Supabase a la semana): el agricultor que abre el cuaderno un domingo por la mañana paga la espera. Y los ficheros siguen necesitando otro sitio |
| **Un servidor más grande desde el principio** | Se paga capacidad que hoy no se usa. El camino barato es empezar pequeño y **cambiar de plan** (misma máquina, un `resize`) cuando los umbrales del apartado 3.4 lo pidan |
| **PostGIS/PostgreSQL «de verdad» separado** | La geometría hoy es **texto WKT** a propósito (`database.py:8-11`), no una columna geométrica. No hace falta PostGIS para servir esto. Meterlo ahora sería complicar el despliegue sin usarlo |

### 3.3. Lo que esta arquitectura **no** resuelve

- **Disponibilidad**: una sola máquina. Si se cae, el cuaderno no está. Un cuaderno de campo
  puede vivir con eso (los datos están apuntados; la copia diaria permite volver), pero
  **hay que decirlo** y avisar con un vigilante externo. Alta disponibilidad es otra
  decisión y otro precio.
- **Actualizaciones sin corte**: al actualizar hay unos segundos de parada. Para un
  agricultor que apunta en el campo, es aceptable **si se hace de madrugada**.
- **Varios procesos**: hoy no. El arranque toca el esquema y `crear_tablas` no está pensado
  para ejecutarse dos veces a la vez. Una instancia.
- **Límite de intentos y revocación de vales**: siguen sin existir. Un servidor delante no
  los arregla solo; hay que decidir si se ponen en Caddy, en la aplicación o en los dos
  (apartado 6).

### 3.4. Capacidad: cuántos agricultores aguanta, y con qué supuestos

**La carga ya está medida, y lo de abajo es la estimación aparte.** El guion
[`backend/scripts/prueba_de_carga.py`](../backend/scripts/prueba_de_carga.py) levantó un uvicorn
de verdad con base temporal y midió el recorrido real (entrar, tierras, ficha, apuntar,
cuaderno) a 1, 5, 10, 25, 50 y 100 usuarios a la vez. El resultado está en
[`docs/PRUEBAS_DE_CARGA.md`](PRUEBAS_DE_CARGA.md) y **cambia una cosa de este apartado**: el
primer límite no es solo el disco, es **cuántos agricultores coinciden en el mismo par de
minutos**.

- **10 usuarios concurrentes van con holgura** (p95 del servidor 240–286 ms, 0 errores).
- **La rodilla está entre 10 y 25**: a 25 el p95 se dobla o triplica (630–1.027 ms).
- **A 50 va lento pero no da ni un error; a 100 se atasca** (las entradas agotan los 20 s de
  espera). El servidor no se cae: deja de contestar a tiempo.
- **Con la clave de producción** (PBKDF2 de 240.000 iteraciones, la que va en el servidor de
  verdad) **entrar cuesta 2,9 veces más** (280 ms de CPU por clave): el p95 a 1 usuario pasa de
  130 a 234 ms y a 10 de 286 a 455 ms. La rodilla se mueve hacia 50.
- Esa medición es **con SQLite**, que tiene **un solo escritor** y un único proceso uvicorn; es
  la configuración del día a día, no la de este despliegue. Con PostgreSQL y 2–3 procesos se
  estima ×2–3, pero **eso no se ha medido** (no hay PostgreSQL en la máquina de las pruebas).

El límite de disco de abajo sigue mandando a largo plazo (**~150 agricultores** el primer año):
las dos cuentas son ciertas a la vez, miden cosas distintas — personas que coinciden y disco
ocupado — y la primera que se agote manda.

| Recurso | Cuenta | Resultado |
|---|---|---|
| **Disco** | 40 GB − ~8 GB (sistema, imágenes de Docker, `data/`, PostgreSQL y sus registros) ≈ **30 GB para adjuntos y caché** | |
| Fotos | ~2 MB por foto o PDF (el tope del programa son 12 MiB), ~100 papeles por agricultor y año ≈ **200 MB/año** | **≈ 150 agricultores** el primer año (30 GB ÷ 200 MB). Con la caché del SIGPAC de una provincia (1–2 GB) baja a ~140 |
| Base de datos | Cientos de miles de filas para cientos de explotaciones: menos de 1 GB | no es el límite |
| **CPU y RAM** | 2 vCPU, 4 GB. Cada petición normal es de milisegundos; entrar deriva la clave 240.000 veces (≈0,1–0,2 s de CPU); leer una foto con OCR ocupa una CPU varios segundos | con uso normal (decenas de peticiones al día y pocas fotos), **cientos de agricultores**. El pico es **varios OCR a la vez** |
| **Peticiones** | ~100 peticiones/día por agricultor × 200 agricultores ≈ 20.000 al día (0,25/s de media). Un solo proceso sirve picos de decenas por segundo sin despeinarse | no es el límite |

**Umbral de cuándo hay que cambiar** (esto sí es una regla, para no decidirlo a ojo):

| Síntoma | Qué mirar | Qué hacer |
|---|---|---|
| Los adjuntos pasan de **30 GB** | `du -sh /srv/cuedigital/datos/adjuntos` | Mover los adjuntos a almacenamiento externo (hay que tocar `adjuntos.py`) o ampliar disco |
| El disco pasa del **80 %** | `df -h /srv/cuedigital` | Ampliar disco o limpiar la caché del SIGPAC (`du -sh .../sigpac_cache`) |
| **CPU sostenida > 70 %** o esperas por OCR | `docker stats` | Subir a CX33 (4 vCPU, 8,99 €) o sacar el OCR a un proceso aparte |
| p95 de **entrar** por encima de **1 s** o **20–25 agricultores a la vez** | registros / métricas de la observabilidad | Mirar PostgreSQL (índices, conexiones, `--workers`) antes de subir de plan. Medido: con 240.000 iteraciones, el p95 a 50 usuarios ya es 1.621 ms |
| Base de datos **> 5 GB** o > 1.000 explotaciones | `pg_database_size` | PostgreSQL dedicado o gestionado |
| Se exige un **SLA por contrato**, doble servidor o copias de 30 días | — | Otra arquitectura y otro presupuesto; no se improvisa |

---

## 4. Plan de puesta en marcha, con comprobación después de cada paso

Cada paso termina con **lo que hay que ver** para poder pasar al siguiente. Si la
comprobación falla, se para ahí: no se sigue «a ver si luego funciona».

### Paso 1. Preparar la máquina

- Ubuntu 24.04, **2 vCPU / 4 GB / 40 GB**, en la UE (el RGPD también manda dónde están los
  datos: apartado 5).
- Usuario sin privilegios, **SSH con clave**, contraseña de root desactivada.
- Cortafuegos: solo 22, 80 y 443.
- Docker y el complemento `compose`.

**Comprobación:** `sudo ufw status` (22/80/443), `docker compose version` contesta v2, y se
entra por SSH con la clave.

### Paso 2. DNS

Registro **A** del dominio a la IP del servidor.

**Comprobación:** `dig +short <dominio>` desde otra máquina devuelve la IP. **No se sigue sin
esto**: Caddy no puede pedir el certificado.

### Paso 3. Código y secretos

```bash
sudo mkdir -p /srv/cuedigital && sudo chown "$USER":"$USER" /srv/cuedigital
cd /srv/cuedigital && git clone <repo> CueDigital && cd CueDigital
cp deploy/.env.example deploy/.env && chmod 600 deploy/.env
# editar: DOMINIO, POSTGRES_PASSWORD, CUEDIGITAL_DATABASE_URL, CUEDIGITAL_SECRETO, CARPETA_DATOS
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # para CUEDIGITAL_SECRETO
```

**Comprobación:** `docker compose -f deploy/docker-compose.yml config --quiet` no dice nada.
Y `grep -c . deploy/.env` ≥ 6. **`deploy/.env` no se copia a ningún sitio.**

### Paso 4. Carpetas de datos y permisos

```bash
sudo mkdir -p /srv/cuedigital/datos/{adjuntos,sigpac_cache,postgresql,observabilidad}
sudo chown -R 10001:10001 /srv/cuedigital/datos
sudo chmod 700 /srv/cuedigital/datos
```

**Comprobación:** `ls -ln /srv/cuedigital/datos` enseña `10001 10001` en las tres carpetas.

### Paso 5. Primer arranque (se crean las tablas)

```bash
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs --tail=100 app
```

**Comprobación:**
1. `ps` enseña `db`, `app` y `caddy` en marcha.
2. La base tiene **67 tablas** (66 del modelo + `grupo_parcela`, la tabla de unión de los
   grupos de parcelas, que no tiene modelo):
   `docker compose -f deploy/docker-compose.yml exec -T db psql -U cuedigital -d cuedigital -tAc "select count(*) from information_schema.tables where table_schema='public' and table_type='BASE TABLE';"`
3. En `logs app` no hay ningún error de base de datos.

### Paso 6. HTTPS de verdad

**Comprobación:**
1. `curl -I https://<dominio>` contesta `200` (o `307` hacia `/`, según la ruta) y el
   certificado es de una autoridad de fiar (Let's Encrypt o ZeroSSL).
2. `curl -I http://<dominio>` redirige a `https://`.
3. `curl -fsS https://<dominio>/health` devuelve
   `{"estado":"ok","zonas_vulnerables_cargadas":true}`.
4. `docker compose logs caddy` no repite errores de emisión de certificado.

> Truco para no gastar intentos: el `Caddyfile` trae comentada la línea del **entorno de
> pruebas de Let's Encrypt**. Se usa mientras se monta y se quita al final (con el entorno de
> pruebas, el navegador avisa de que el certificado no es de fiar: es lo normal).

### Paso 7. La pantalla, en un móvil de verdad

**Comprobación:** abrir `https://<dominio>` desde un móvil (no solo desde el ordenador),
entrar con la cuenta de prueba, moverse por dos o tres pantallas y **comprobar que no hay
errores en la consola**. Si la pantalla sale en blanco: `logs caddy`, la consola del
navegador y la caché del service worker (paso 12).

### Paso 8. Alta del primer agricultor

Se da de alta **con su NIF de verdad** (es lo que se compara después con su certificado
digital) desde la pantalla o con la API.

**Comprobación:**
1. `POST /api/cuenta/registro` devuelve `201` con su vale.
2. `GET /api/cuenta/yo` con ese vale devuelve su nombre y su finca.
3. Entra en la pantalla con su correo y su clave.
4. Si tiene el cuaderno de la Junta (Cuecyl), **se importa** y las tierras aparecen (la
   importación se enseña antes de apuntar: dos pasos).

### Paso 9. Subir una foto y comprobar el tope de tamaño

**Comprobación:**
1. Se sube un papel (boletín, factura o albarán) desde la pantalla y **se vuelve a
   descargar**; el fichero coincide.
2. En el servidor aparece en `/srv/cuedigital/datos/adjuntos/<nº de finca>/`, con un nombre
   puesto por el programa (no el del navegador) y con dueño `10001`.
3. Un fichero de **20 MB** se rechaza con `413` y una frase en castellano (el programa corta
   en 12 MiB; Caddy corta en 15 MB). No se queda a medias ni deja el fichero en disco.
4. Un fichero con un tipo que no vale (por ejemplo `.exe`) se rechaza con su explicación.

### Paso 10. Copia de seguridad, y **restauración probada**

```bash
./deploy/copia.sh
./deploy/restaurar.sh /srv/cuedigital/copias/<la-marca>
```

**Comprobación (la parte que casi nadie hace y es la que importa):**
1. `copia.sh` crea `base.dump` y `adjuntos.tar.gz`, y **los comprueba** (`pg_restore --list`
   y `tar -tzf`).
2. `restaurar.sh` crea una **base nueva** (la de producción no se toca), restaura ahí,
   descomprime los adjuntos en otra carpeta y cuenta las filas.
3. Se levanta la segunda instancia en `127.0.0.1:8001` contra la copia, **se entra con una
   cuenta que exista en la copia y se descarga un documento**. Eso es usar la copia.
4. Se apunta en un sitio **la fecha del último ensayo de restauración**. Una copia que no se
   ha restaurado nunca es una esperanza, no una copia.
5. Programar la copia diaria en el cron y **configurar `COPIA_REMOTA`** (R2): sin copia
   fuera, un fallo del servidor es una pérdida definitiva.

### Paso 11. Vigilancia

- UptimeRobot (gratis, 50 monitores cada 5 min) apuntando a `https://<dominio>/health`, con
  aviso al correo de David.
- Opcional: un segundo monitor a `/api/interfaz` (una ruta que sí hace trabajar al programa).

**Comprobación:** se apaga el servidor un minuto (o se simula) y **llega el aviso**. Un
vigilante que no avisa no es un vigilante.

### Paso 12. Cierre de la puesta en marcha

- **Cambiar `CUEDIGITAL_SECRETO` no es un trámite:** si se cambia, todos tienen que volver a
  entrar. Se elige bien **una vez** y se guarda.
- `chmod 600 deploy/.env`; comprobar que el `.env` no está en el repositorio:
  `git status --short` no lo enseña.
- Comprobar que la **caché del service worker** corresponde a la versión desplegada (si el
  código cambió la pantalla, se subió el nombre en el mismo cambio).
- Documentar en un fichero privado: dominio, IP, dónde está la copia, fecha del último
  ensayo de restauración, y quién tiene acceso.

### Paso 13. Ensayo con un agricultor real (y este es el paso que manda)

Con **un** agricultor de confianza, en su finca, con su móvil:

1. Alta con su NIF y su correo.
2. Importar su cuaderno de la Junta, si lo tiene.
3. Apuntar **un tratamiento y un abono** de verdad (o de un día ya pasado, con su permiso).
4. Hacer una foto a un papel y subirla.
5. Abrirlo **sin cobertura** (modo avión) y comprobar que puede seguir apuntando y que los
   datos suben al volver la cobertura.
6. Sacar el cuaderno en PDF y mirarlo con él.

**Comprobación:** el agricultor termina sin ayuda y los datos están donde tienen que estar.
Lo que no le salga se apunta y se arregla antes de abrir a más gente. Un ensayo con un
agricultor real vale más que cien pruebas de escritorio.

### Paso 14. Antes de abrir a más gente

- [ ] Copia fuera de la máquina funcionando y **restauración probada con fecha**.
- [ ] Vigilante externo avisando.
- [ ] Contrato de encargado del tratamiento con el proveedor (y con cada agricultor si se
      ofrece como servicio): apartado 5.
- [ ] Aviso de privacidad publicado y registro de actividades.
- [ ] Suite corrida **contra PostgreSQL** una vez en el servidor
      (`CUEDIGITAL_SUITE_SOBRE`, ver `tests/conftest.py:31-49`).
- [ ] Decidido qué se hace con el límite de intentos y la revocación de vales.
- [ ] La forma canónica del cuaderno firmado, congelada (si se va a firmar).

---

## 5. RGPD: los datos del agricultor

> **Esto no es asesoría jurídica.** Es lo que hay que tener sobre la mesa. Antes de abrir a
> terceros, que lo revise alguien con titulación (abogado o consultoría de protección de
> datos). Lo que sí se puede afirmar es lo que sigue, con el Reglamento en la mano:
> **Reglamento (UE) 2016/679 (RGPD)**, <https://eur-lex.europa.eu/eli/reg/2016/679/oj>
> (consultado el 09/11/2026), y en España la Ley Orgánica 3/2018 (LOPDGDD).

### 5.1. Qué datos personales se tratan (comprobado en el modelo)

| Dato | Dónde está | Por qué importa |
|---|---|---|
| **NIF del titular** | `backend/app/models.py:70` (`explotaciones.nif`, con índice) | Identifica a una persona (o a un autónomo). Es la llave que se compara con el certificado digital |
| Nombre, correo y clave | `models.py:114` (correo único), `usuarios` | La clave se guarda con PBKDF2-SHA256 con sal; nunca en claro |
| Dirección, localidad, código postal, teléfono | `models.py:95-99` (`explotaciones`) | Datos de contacto |
| **Datos de la explotación**: tierras, cultivos, tratamientos, abonos, cosechas, ganado | tablas de negocio, todas con `explotacion_id` | Es la actividad profesional de una persona identificada: **es dato personal** |
| **Papeles subidos**: facturas, contratos, boletines, albaranes | `documentos_anexos` + ficheros en `CUEDIGITAL_ADJUNTOS` | Pueden llevar **el NIF de terceros** (proveedores, laboratorios): también son datos personales |
| NIF del firmante y del proveedor | `models.py:2650` (`firmante_nif`), `models.py:2901`, `:3312`, `:4148`, `:4220` | Firma y facturación |
| Rastro de auditoría (quién hizo qué) | tabla `auditoria` | Necesario para la inspección; también es dato personal |
| **Direcciones IP** (en los registros de Caddy) | `deploy/Caddyfile` (registro de accesos) | Una IP es dato personal. Hay que decidir cuánto se guarda |

**Nunca se guardan** en este programa: certificados privados (el certificado de cliente se
queda en el proxy), ni la clave en claro, ni datos de tarjetas.

### 5.2. Quién es el responsable y quién el encargado: hay dos casos

Esto es lo que más se equivoca y es **obligación legal** (art. 28 RGPD):

| Caso | Quién es responsable | Quién es encargado | Qué contrato hace falta |
|---|---|---|---|
| **David usa CUE Digital para su propia explotación** | David | El proveedor de hosting (Hetzner) y el de copias (Cloudflare/Hetzner) | Contrato de encargado con **cada proveedor** (art. 28.3) |
| **CUE Digital se ofrece como servicio a otros agricultores** | **Cada agricultor** (el cuaderno es suyo y él responde de él ante la inspección) | **David** (y, por debajo, Hetzner y el de copias: **subencargados**, art. 28.4) | Contrato de encargado **con cada agricultor** (art. 28.3) **y** con cada proveedor |

Si se ofrecen servicios de asesoría o se tratan datos para otros fines, cambia el reparto y
hay que revisarlo. **Decisión de David** (apartado 6).

### 5.3. Lo que es obligación legal, y lo que es recomendación

**Obligación legal (RGPD):**

| Obligación | Artículo | Cómo se cumple en este despliegue |
|---|---|---|
| **Alojar en la UE** (o hacer transferencia internacional legítima) | arts. 44 y siguientes | Hetzner en Alemania/Finlandia. **Aviso:** Cloudflare R2 y Sentry son empresas de EE. UU.; si se usan, hay que mirar sus condiciones de transferencia y su contrato (no verificadas aquí) |
| **Contrato de encargado del tratamiento** con cada proveedor que trate datos por cuenta de David | art. 28.3 | Pedir y firmar el de Hetzner (y el de copias) **antes** de subir datos de agricultores. Hetzner publica condiciones de protección de datos; **el documento concreto de encargado no se ha descargado ni revisado en esta consulta: no verificado** |
| **Registro de las actividades de tratamiento** | art. 30 | Un documento con: qué datos, para qué, base jurídica, destinatarios, plazos y medidas de seguridad. No existe hoy: hay que escribirlo |
| **Información a los interesados** (aviso de privacidad) | arts. 13 y 14 | Una página con quién trata, para qué, base jurídica, destinatarios, plazo, derechos y cómo reclamar ante la AEPD. **No existe hoy** |
| **Seguridad del tratamiento** | art. 32 | HTTPS, contraseñas con PBKDF2, aislamiento por explotación, copias, permisos del disco. Lo que falta: límite de intentos, revocación de vales y doble factor (hoy no hay) |
| **Notificación de violaciones de seguridad** | art. 33 (72 horas a la AEPD) y art. 34 (a los afectados) | Hace falta un **procedimiento escrito** y saber quién lo ejecuta. No existe hoy |
| **Limitar el plazo de conservación** | art. 5.1.e | Hay que **decidir y escribir** cuánto se guardan los adjuntos y las copias. Hoy no hay política |
| **Atender derechos**: acceso, rectificación, supresión, portabilidad, limitación, oposición | arts. 15-21 | Hay corrección y anulación de apuntes y exportación del cuaderno (PDF/CSV), pero **no hay supresión de cuenta ni exportación completa**: hay que atenderlo a mano o hacerlo |
| **Evaluación de impacto** solo si el tratamiento es de alto riesgo | art. 35 | Un cuaderno de campo no suele serlo, pero **hay que dejarlo escrito** el porqué (recomendación: hacer un análisis corto y firmarlo) |

**Recomendación (no obligación, pero sensato):**

- **Guardar los datos personales en la UE**, incluso los de las copias. Si la copia va a R2,
  elegir la jurisdicción de la UE cuando se cree el bucket.
- **Minimizar**: no pedir en el alta más de lo que se usa (hoy el alta ya pide lo mínimo).
- **Cifrar el disco del servidor** (Hetzner lo permite) y las copias (rclone con cifrado, o
  el cifrado del proveedor).
- **No meter datos reales de agricultores en el entorno de pruebas** (el proyecto ya lo
  prohíbe: `contexto_agentes/ESTADO.md`), ni en capturas, ni en un chat.
- **Plazo de conservación propuesto** (a decidir y escribir): mientras la cuenta esté viva;
  al cerrarla, borrar lo que no haya que conservar por ley. **Las facturas y documentos que
  justifican la compra, la Junta pide guardarlos tres años** (`README.md:698-703`); el resto
  de plazos legales del cuaderno **no se han verificado aquí**: se confirman con asesoría y
  se escriben en la política.
- **Las copias también contienen datos personales**: la rotación de 14 días de
  `deploy/copia.sh` es una decisión de conservación que tiene que estar en la política.
- **Registro de accesos** (quién entra al servidor, quién descarga una copia): una hoja
  basta, pero tiene que existir.

### 5.4. Qué avisos harían falta (sin escribirlos en `textos.py`)

En este proyecto **todo lo que lee el agricultor vive en `backend/app/textos.py`** y hay
tests que lo comprueban (`AGENTS.md` §3.1). Por eso aquí **no se escribe ni una frase** de
cara al agricultor: se dice **qué avisos hacen falta** y se dejan para cuando se redacten,
con su test de jerga y su revisión.

1. **Aviso de privacidad** (página pública o pantalla de «mis datos»): responsable,
   finalidades, base jurídica, destinatarios (hosting y copias), plazo, derechos y AEPD.
2. **Aviso en el momento del alta**: qué se guarda, para qué y cuánto; enlazado al aviso
   completo. Tiene que leerlo alguien que no sabe de informática (la regla de la casa).
3. **Aviso de subida de documentos**: los papeles que sube se guardan en el servidor de
   David (no en su móvil) y entran en las copias.
4. **Aviso de la firma**: qué significa firmar el cuaderno y qué se guarda de la firma (ya
   existe contenido técnico en `textos.py`; el aviso de privacidad es otra cosa).
5. **Cómo ejercer los derechos**: un sitio donde diga a quién escribir y cómo (hoy no hay
   correo saliente: tiene que ser un teléfono/correo de David, puesto en el aviso).
6. **Nada de estos textos se escribe en routers, HTML ni JavaScript**: van a `textos.py` con
   su `textos_visibles()` y su test.

---

## 6. Riesgos y decisiones para David

| # | Decisión | Coste | Qué pasa si no se decide |
|---|---|---|---|
| 1 | **Dónde se aloja** (VPS propio, ≈ 7 €/mes, frente a PaaS) | ≈ 7,25 €/mes con IVA | No hay servicio. Y si se elige PaaS gratuito, los papeles del agricultor se pierden al reiniciar |
| 2 | **El dominio**: cuál y a nombre de quién | **no verificado** (precio del registrador) | Sin dominio no hay HTTPS ni certificado, y sin certificado no hay cuaderno en el campo |
| 3 | **Quién es el responsable del tratamiento** (David para su finca, o David como encargado de cada agricultor) | 0 €, pero hay que decidirlo y firmarlo | Sin contrato de encargado se incumple el art. 28 RGPD desde el primer agricultor |
| 4 | **Firmar el contrato de encargado con Hetzner y con el proveedor de copias** | 0 € (trámite) | Lo mismo: incumplimiento del art. 28. Y si se usa R2, revisar la transferencia internacional |
| 5 | **Política de conservación de adjuntos y copias** (cuánto tiempo) | 0 € (escribirla) y algo de limpieza | Datos personales guardados sin plazo: incumplimiento del art. 5.1.e; y un disco que se llena |
| 6 | **Límite de intentos / bloqueo de cuenta** | 1–2 días de desarrollo; 0 € de infraestructura | Un ataque de fuerza bruta contra una clave débil no tiene freno (hoy no hay ninguno) |
| 7 | **Revocación de vales y rotación de la clave** (hoy 30 días sin revocar) | 1–2 días de desarrollo | Un vale robado vale 30 días, y no se puede echar a nadie sin cambiar la clave a todos |
| 8 | **Doble factor** para la cuenta | desarrollo + decisiones de UX | Si se abre a terceros, es una recomendación fuerte y puede ser exigencia de un cliente |
| 9 | **Entrar con certificado digital** (mTLS en Caddy) | 1–2 días, y **probarlo** | Hoy se entra con correo y clave; el certificado está preparado pero apagado y sin probar |
| 10 | **Copia fuera de la máquina** (R2 gratis hasta 10 GB) | 0 € | Un fallo del servidor = pérdida definitiva de los cuadernos. Es el riesgo más caro |
| 11 | **Vigilante externo** (UptimeRobot) | 0 € | El servidor puede estar caído un día y nadie se entera |
| 12 | **Separar dependencias** de producción de las de tests | medio día | La imagen instala `pytest`, `ruff`… y el comentario de `requirements.txt` sigue mintiendo |
| 13 | **Migraciones de verdad** (Alembic o similar) antes del primer cambio de esquema | 2–3 días | El día que haga falta cambiar una columna, el programa **no arranca** en PostgreSQL (está dicho en `database.py:405-419`) |
| 14 | **Supresión de cuenta y exportación completa** (derechos RGPD) | 2–3 días | Hay que atenderlo a mano, y con prisa es cuando se borra lo que no se debe |
| 15 | **Aviso de privacidad y registro de actividades** | 1–2 días + revisión externa | Incumplimiento de los arts. 13 y 30 desde el primer agricultor |
| 16 | **Alta del dominio del certificado en el IUWS** | gestión con la Junta; **no es dinero** | Sin el alta, el volcado a la Junta no se puede probar (hoy contesta «dominio no registrado») |
| 17 | **OCR en el servidor** (instalarlo o no) | 0 € (viene en la imagen) pero ocupa CPU | Sin OCR, las facturas se escriben a mano; el programa lo dice y no inventa |
| 18 | **Soporte de «he olvidado mi clave»** (no hay correo saliente) | horas de proceso, no dinero | El agricultor se queda fuera hasta que David lo arregle desde el servidor |
| 19 | **Congelar la forma canónica del cuaderno firmado** antes de la primera firma | decisión, 0 € | Si se cambia después, **todas las firmas anteriores dejan de valer** |
| 20 | **Actualizaciones sin corte**: ¿de madrugada? ¿con ventana? | 0 € (es un acuerdo) | Un reinicio a las 10 de la mañana en plena campaña |

---

## 7. Lo que no se ha podido verificar (y por tanto no se afirma)

**Del repositorio**

- **La imagen se construye y el stack se ha probado en local** contra PostgreSQL 16, pero **no
  hay servidor público, ni dominio, ni Caddy con certificado real**: no hay URL que enseñar. Lo
  que falta es una cuenta y un dominio ([`CUENTAS-Y-ACCESOS.md`](CUENTAS-Y-ACCESOS.md)).
- **La suite completa sí se ha ejecutado** (09/11/2026): **6042** pruebas de Python, 0 fallos, y
  **1319** de JavaScript, 0 fallos.
- **`deploy/copia.sh` y `deploy/restaurar.sh` no se han ejecutado**: sin servidor no hay a dónde
  copiar. El procedimiento está escrito y probado a mano de sintaxis (`bash -n`), nada más.
- **No se ha probado Caddy con un dominio real** ni el bloque de certificado de cliente
  (está comentado a propósito).

**De los precios y proveedores**

- **Backblaze B2**: la tabla de precios de la página oficial no se pudo leer. No se cita
  precio.
- **Contabo (plan de entrada)** y **OVHcloud (gama barata)**: sus páginas oficiales no
  devolvieron precios; solo se citan los planes que aparecen en VPSBenchmarks, con su fecha.
- **Render, planes de pago**: la página de precios no devolvió las tarifas.
- **Sentry, plan gratuito**: existe, pero **la cuota exacta** no está en la documentación
  consultada.
- **Hetzner: disponibilidad** de CX23/CAX11 en el momento de la consulta (aparecían como «no
  disponible») y **el IVA aplicable** según se contrate como empresa o particular.
- **La duración mínima de almacenamiento de Wasabi** no se ha verificado.
- **El precio del dominio** y **el precio de ampliar el disco del VPS** no se han verificado.
- **El contrato de encargado del tratamiento de Hetzner**: no se ha descargado ni revisado.
- **La conversión dólar-euro** no se ha fijado: los precios en dólares se dejan en dólares.

**Legales**

- Los plazos de conservación del cuaderno distintos del de las facturas (tres años, que sí
  está en el README del proyecto) **no se han verificado**; se confirman con asesoría.
- Este documento **no es asesoría jurídica**.

---

## 8. Resumen para David, en cinco líneas

1. **Falta poco para poder desplegar, pero falta lo importante**: el driver de PostgreSQL
   (ya está el fichero), un sitio para los ficheros, una copia fuera de la máquina, y
   decisiones de acceso (límite de intentos, revocación) que hoy no existen.
2. **La opción recomendada es un VPS pequeño en la UE con Caddy + la aplicación +
   PostgreSQL y los datos en disco**, con copia diaria a R2. Cuesta **≈ 7,25 €/mes con IVA**
   y aguanta **150–200 agricultores** de alta; el primer límite son las fotos, no la CPU. **A la
   vez, medido: 10** (la rodilla está entre 10 y 25; ver `docs/PRUEBAS_DE_CARGA.md`).
3. **El esfuerzo es de 10–12 horas** de puesta en marcha y ensayo, más el trabajo de
   desarrollo que salga de las decisiones 6, 7, 13 y 14.
4. **Lo que no puede esperar**: firmar el contrato de encargado, aviso de privacidad y
   registro de actividades **antes** del primer agricultor real; y **probar la restauración**
   con fecha apuntada.
5. **Lo que hay que decidir ya, y no cuesta dinero**: dominio, quién es el responsable del
   tratamiento, política de conservación, y si se pone el vigilante externo.

---

## 9. El despliegue que está EN PIE hoy: el servidor de casa (09/11/2026)

> **Esto ya no es un plan: es lo que hay funcionando.** La aplicación completa (pantalla + API +
> PostgreSQL) corre en el **servidor propio de David**, y sale a internet por un túnel de
> Cloudflare. La pantalla y la API están en el **mismo origen**, así que no hace falta CORS para
> esta forma de servirla.

### 9.1. La dirección pública (y por qué es esta)

| Dato | Valor |
|---|---|
| **URL pública** | **https://attract-leeds-integer-asp.trycloudflare.com** |
| Pantalla nueva | `/nuevo/` (la de siempre sigue en `/`) |
| Cuenta de ejemplo | `demo@cuedigital.local` / `cuaderno-demo-2026` |
| Finca de ejemplo | Las **cinco parcelas del cliente de Salamanca** (El Prado, El Alto, La Vega, Las Eras y El Visor), con su forma traída del **GeoPackage real** |
| Servidor | el de casa (`192.168.1.139`), Docker, contenedores `cuedigital-db`, `cuedigital-app`, `cuedigital-tunnel` |
| Datos | `/srv/cuedigital/datos/{adjuntos,sigpac_cache,postgresql,observabilidad}` |
| Imagen | `cuedigital:servidor` (se construye en el ordenador de David y se carga con `docker load`) |
| Puerto interno | `127.0.0.1:8090` → túnel |

**El túnel es efímero y esto hay que decirlo:** es un *quick tunnel* de Cloudflare, sin cuenta. Da
HTTPS de verdad (Cloudflare termina el TLS) pero **la dirección cambia si se recrea el
contenedor**. Para una dirección estable hacen falta dos cosas que dependen de David: un
**túnel con nombre** en su cuenta de Cloudflare (y un token con permisos, que el del 09/11 no
tiene) o **un dominio** apuntando a la IP pública. Mientras tanto:

```bash
docker restart cuedigital-tunnel          # si se cae
docker logs cuedigital-tunnel | grep trycloudflare   # la dirección nueva
```

### 9.2. Cómo se levanta y cómo se apaga

```bash
# En el servidor. El guion deja la base, la app y comprueba /health.
/tmp/arrancar-cuedigital.sh

# Apagarlo todo (sin borrar los datos, que están en /srv/cuedigital/datos):
docker stop cuedigital-app cuedigital-db cuedigital-tunnel
```

La configuración vive en **`/srv/cuedigital/env`** (permisos 600, fuera del repositorio): base,
secreto de los vales, token de la observabilidad y orígenes del CORS.

### 9.3. Cómo se conecta la pantalla con el backend

Hay **dos formas**, y las dos están probadas:

1. **El propio programa sirve la pantalla** (lo que hay hoy): `https://<url>/nuevo/`. La pantalla
   pide `/api/...` y está en el mismo origen. **No hace falta CORS ni configurar nada.**
2. **La pantalla publicada aparte** (GitHub Pages u otro sitio): entonces la API y la pantalla
   están en orígenes distintos y hacen falta **las dos cosas**:

   - **En la pantalla**, decir dónde está la API. `deploy/paginas_github/preparar.py` genera una
     carpeta con el front y un `config.js` que pone `window.CUEDIGITAL_API = "https://<url>"`.
     La pantalla pasa **todas** las llamadas por `urlDeLaApi()` (`web/nuevo/modelo.js`), que no
     toca nada si esa variable está vacía.
   - **En el servidor**, autorizar ese origen:
     `CUEDIGITAL_CORS_ORIGENES=https://erdeivih.github.io` (separados por comas). Sin esto, el
     navegador manda el `Origin` de Pages y la API lo rechaza: la pantalla se queda vacía. `*`
     se ignora a propósito (es una API con datos de agricultores).

   ```bash
   # Preparar el front para publicarlo aparte:
   python deploy/paginas_github/preparar.py --servidor https://<url> \
       --demo-correo demo@cuedigital.local --demo-clave cuaderno-demo-2026 --salida build/pages
   ```

### 9.4. GitHub Pages: preparado y **bloqueado por el plan**

La rama **`gh-pages` ya está subida** con el front (con su `config.js`, su `.nojekyll` y las rutas
relativas). **No se ha podido activar Pages**:

> `422 · Your current plan does not support GitHub Pages for this repository.`

El repositorio es **privado** y la cuenta está en el **plan gratuito**, que no da Pages para
repositorios privados. Para activarlo, David decide una de estas dos (las dos, un clic después):

- **hacer público el repositorio** (Settings → General → Danger Zone → Change visibility), o
- **pasar la cuenta a Pro** (de pago).

Después: Settings → Pages → *Deploy from a branch* → `gh-pages` / `/`. La URL sería
`https://erdeivih.github.io/CueDigital/`.

**Mientras eso no se decida, la app se ve (y funciona) en la URL del túnel**, que sirve la misma
pantalla con datos: es la que se ha comprobado.

### 9.5. La comprobación que se puede repetir

```bash
python deploy/comprobar_publica.py https://attract-leeds-integer-asp.trycloudflare.com
```

Comprueba, contra la URL de verdad: `/health`, entrada con la cuenta de ejemplo, **las cinco
parcelas visibles** en la pantalla (Chrome de verdad), **el mapa con el contorno cargado**
(`naturalWidth > 0`) y la ficha de una tierra con su ortofoto y su contorno; y guarda las
capturas a **360 y 1024 px** en `docs/capturas-despliegue/`. El alta por referencia de seis
números se prueba en `deploy/paginas_github/sembrar_finca_ejemplo.py` (las cinco se dieron de alta
así, y «El Visor» solo con `37-70-0-0-501-80`, seis números).

