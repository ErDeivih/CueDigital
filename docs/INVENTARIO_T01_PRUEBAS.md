# Inventario de pruebas (T01): qué se prueba hoy y qué no

Fecha de este documento: **02/10/2026**. Encargo T01 del `CONTRATO_IMPLEMENTACION_CRM.md`
(«Inventario ruta→pantalla→API→modelo→pruebas; estados realmente existentes»).

**Qué es este documento.** Lo que dicen las suites **al ejecutarlas hoy**, no lo que dicen los
informes antiguos ni lo que promete un comentario del código. Cada afirmación de aquí lleva su
`fichero:línea` para que se pueda comprobar sin creerme.

**Qué NO es.** No es una auditoría de la explotación real. La suite entera se ejecuta contra una
cuenta y una finca **de prueba** (una parcela de 2,43 ha en Peñaranda de Bracamonte). Que esté en
verde dice que el programa hace lo que dicen sus pruebas; **no** dice que los datos del agricultor
estén bien ni que el cuaderno cumpla la PAC.

**Cómo se ha hecho.** Solo lectura sobre el código. Se han ejecutado las dos suites con bases y
adjuntos temporales. **No** se han ejecutado `scripts/humo.py` ni
`scripts/comprobar_en_un_navegador.py` (necesitan puertos y bases que estaba usando el titular).
No se ha modificado ningún fichero salvo este.

---

## 1. Cómo se ejecuta cada suite

El intérprete de Windows es `F:\EspacioCodigo\CueDigital\.venv\Scripts\python.exe`
(Python 3.12.10, pytest 9.1.1). Node es v24.19.0.

### 1.1. Python (pytest) — 2.892 casos

```powershell
# 1. Variables de entorno. Se fijan ANTES de lanzar pytest.
$env:PYTHONIOENCODING            = "utf-8"
$env:CUEDIGITAL_ENTORNO           = "pruebas"
$env:CUEDIGITAL_ITERACIONES_PBKDF2 = "1000"
$env:CUEDIGITAL_DATABASE_URL      = "sqlite:///C:/Users/<usuario>/AppData/Local/Temp/cuedigital_verif/verificacion.db"
$env:CUEDIGITAL_ADJUNTOS          = "C:\Users\<usuario>\AppData\Local\Temp\cuedigital_verif\adjuntos"

# 2. Desde la carpeta backend (la raíz la fija pyproject.toml con testpaths = ["tests"]).
Set-Location F:\EspacioCodigo\CueDigital\backend
& F:\EspacioCodigo\CueDigital\.venv\Scripts\python.exe -m pytest `
    --junit-xml="C:\...\cuedigital_verif\pytest.xml"
```

Para qué sirve cada variable:

| Variable | Para qué | Quién la fija |
|---|---|---|
| `CUEDIGITAL_DATABASE_URL` | Apunta a un fichero de `%TEMP%`. **Sin esto se escribiría en `backend/cuedigital.db`, que es la base del agricultor.** El valor por defecto está en `backend/app/database.py:24` (`sqlite:///./cuedigital.db`) | `conftest.py:24` |
| `CUEDIGITAL_ADJUNTOS` | Carpeta **temporal** para boletines, papeles y facturas que suben las pruebas. Sin esto cada ejecución dejaba ficheros de verdad en el proyecto (`conftest.py:8-12`). Hay además una prueba que comprueba que la carpeta **no** está dentro del proyecto: `backend/tests/test_analiticas.py:454-466` | `conftest.py:30` |
| `CUEDIGITAL_ENTORNO=pruebas` | Habilita el atajo de bajar las iteraciones de la clave. Son **dos** condiciones a propósito | `conftest.py:40` |
| `CUEDIGITAL_ITERACIONES_PBKDF2=1000` | Deriva la clave 1.000 veces en vez de 240.000. Sin el atajo la suite tardaría minutos en vez de 3. **No se puede colar en producción**: por debajo de 100.000 iteraciones el programa revienta si no está en entorno de pruebas (`backend/app/security.py:23,30,38,41,56`), y hay una prueba que lo ata (`backend/tests/test_seguridad_de_las_claves.py:35,98-111`) | `conftest.py:41` |
| `PYTHONIOENCODING=utf-8` | Sin esto los `print` con tildes revientan en la consola de Windows (`AGENTS.md` §7) | hay que ponerla a mano |
| `CUEDIGITAL_SECRETO` | Secreto de los vale de sesión | `conftest.py:27` |
| `CUEDIGITAL_ZV_CYL_RUTA` | La suite arranca **sin** el listado de zonas vulnerables y lo carga solo en las pruebas que lo comprueban | `conftest.py:33` |

**Ojo con el orden.** `conftest.py` fija estas variables **antes de importar nada de `app`**
(`conftest.py:3-13`): `app.database` construye el motor al importarse, así que importar antes haría
que las pruebas escribieran en la base de verdad. Como conftest se importa primero, la suite es
segura incluso sin las variables puestas a mano; ponerlas es una red de seguridad y es lo que se ha
hecho aquí.

Al terminar, `conftest.py:51-78` cierra el motor y borra la carpeta temporal (dos veces: al acabar
la sesión y al cerrar el intérprete).

### 1.2. JavaScript (node --test) — 643 casos

```powershell
Set-Location F:\EspacioCodigo\CueDigital\backend
node --test "tests_js/*.test.js"
```

No necesita ninguna variable de entorno ni sale a internet. `backend/package.json` existe **solo**
para declarar `"type": "module"`, que es lo que necesita `node --test` (no hay dependencias ni
compilación). El equivalente por npm es `npm test` en esa carpeta.

### 1.3. Las dos comprobaciones a mano (NO ejecutadas en este encargo)

```powershell
# Recorrido completo contra un servidor de verdad (hay que tenerlo levantado)
& F:\EspacioCodigo\CueDigital\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
& F:\EspacioCodigo\CueDigital\.venv\Scripts\python.exe scripts/humo.py http://127.0.0.1:8000

# Chrome sin ventana (servidor de pruebas en el 8010 por defecto)
& F:\EspacioCodigo\CueDigital\.venv\Scripts\python.exe scripts/comprobar_en_un_navegador.py
```

Ninguna de las dos se ha ejecutado. Sí se ejecutaron las **pruebas de pytest que las inspeccionan
sin lanzarlas** (`test_comprobar_en_un_navegador.py`, `test_firmar_con_el_certificado.py`,
`test_probar_iuws_con_certificado.py`): están escritas para no abrir ningún navegador
(`test_comprobar_en_un_navegador.py:8`) y para no llamar a ningún servicio.

---

## 2. Números reales (ejecutado la noche del 01/10/2026 al 02/10/2026)

### 2.1. Python / pytest

| | |
|---|---|
| Comando | `python -m pytest --junit-xml=.../pytest.xml` (desde `backend`) |
| Cuándo | empezó **01/10/2026 23:55:47** (+02:00), duró **204,4 s** |
| Fuente del número | `testsuite` del **`--junit-xml`**, no la salida por pantalla |
| **Casos recogidos** | **2.892** |
| **Pasan** | **2.891** |
| **Fallan** | **0** (0 `failure`, 0 `error`) |
| **Omitidas** | **1** |

La única omitida, y su motivo:

- `tests.test_facturas.TestLeerUnaFacturaEnFoto::test_si_el_lector_solo_tiene_ingles_se_avisa`
  → *«el lector tiene el idioma español instalado»*.
  No es un fallo: la prueba solo tiene sentido si Tesseract tiene **solo** inglés, y en este PC tiene
  español. **En esta máquina nunca se ejecuta** (ver §7, riesgo 2).

Cobertura por fichero, contada de ese mismo XML (los casos, no las funciones: por eso salen más que
las funciones `test_` del fichero) — los diez mayores:

| Fichero | Casos |
|---|---|
| `test_ficheros_de_texto` | 723 |
| `test_mapeo_oficial` | 144 |
| `test_iuws` | 121 |
| `test_interfaz` | 105 |
| `test_los_maestros_se_pueden_corregir` | 88 |
| `test_registro_obligatorio` | 79 |
| `test_analiticas` | 78 |
| `test_borradores` | 74 |
| `test_iuws_cliente` | 72 |
| `test_analisis_ventas_planes_y_campanas` | 66 |

### 2.2. JavaScript / node --test

| | |
|---|---|
| Comando | `node --test "tests_js/*.test.js"` (desde `backend`) |
| Cuándo | **01/10/2026**, duró **58,9 s** |
| **Casos** | **643** |
| **Pasan** | **643** |
| **Fallan** | **0** |
| **Omitidas (`skipped`)** | **0** |
| `todo` / `cancelled` | 0 / 0 |

Reparto: `react.test.js` 330, `interfaz.test.js` 254, `nucleo.test.js` 59.

### 2.3. Que no se ha tocado nada del agricultor

- `backend\cuedigital.db` sigue con fecha **30/09/2026 18:05:33**, anterior a la ejecución
  (la suite corrió del 01/10 23:55 al 02/10 00:00): **no se ha abierto ni escrito**.
- `backend\datos\adjuntos` **no existe**: ninguna prueba ha dejado papeles en el proyecto.
- La carpeta temporal de esta ejecución solo contiene `pytest.xml` y una carpeta `adjuntos` **vacía**:
  no ha quedado ninguna base ni ningún fichero de prueba.
- (Aparte: en `%TEMP%` quedan **6** carpetas `cuedigital_tests_*` de ejecuciones anteriores
  (26–30/09), una con un `tests.db` de 397 KB dentro. La limpieza de `conftest` funcionó en esta
  ejecución, pero no siempre: es basura vieja, no de ahora.)

---

## 3. Mapa de cobertura por área

Una línea por fichero, con el número de casos del XML. Entre paréntesis, lo que **no** cubre.

### 3.1. Cálculos legales

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_legal.py` | 27 | Plazo de seguridad, unidades fertilizantes, dosis contra la etiqueta, superficie, vigencias y formato en castellano. Funciones puras, sin base ni servidor |
| `tests/test_geo.py` | 10 | Centro de la parcela y distancia entre parcelas |
| `tests/test_nitratos.py` | 35 | Zona de nitratos: tope de 170 kg de estiércol, pendiente del 15 %, y que lo que no se sabe se diga |
| `tests/test_tablas_nitratos_cyl.py` | 4 | El JSON de tablas deriva del PDF oficial, casillas vacías incluidas |
| `tests/test_listado_oficial_zv_cyl.py` | 5 | La fuente municipal de zonas vulnerables se reproduce y no confunde nombres |
| `tests/test_lo_que_obliga_la_ley.py` | 15 | Que lo que el programa dice de la ley sea verdad y esté a la vista (con artículo y BOE) |

### 3.2. Registro obligatorio (el cuaderno)

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_registro_obligatorio.py` | 79 | El registro de punta a punta: alta, tratamiento, cosecha, fertilización, anulación, aislamiento, grupos y cuaderno |
| `tests/test_autorizacion_del_producto.py` | 23 | Las tres comprobaciones que no podían saltar: producto retirado, ecológico y autorización caducada |
| `tests/test_registro_oficial_de_productos.py` | 16 | El registro oficial de fitosanitarios del MAPA: que la comprobación no mienta |
| `tests/test_cesta_del_almacen.py` | 35 | Cuánto entró, cuánto salió y cuánto queda — y cuándo **no** se contesta |
| `tests/test_como_se_echo.py` | 25 | Hora, estado de la planta y del día del tratamiento |
| `tests/test_practicas_culturales.py` | 53 | Las labores que no son sembrar/plantar/regar/cosechar, y que salgan en el papel y el fichero |
| `tests/test_instalaciones.py` | 24 | Naves y las cuatro clases de tratamiento (parcela, semilla, postcosecha, nave) |
| `tests/test_medidas_preventivas.py` | 57 | Las diez medidas de la finca, que lo declarado alimente el apunte y que desmarcar no borre |
| `tests/test_grupos_de_parcelas.py` | 23 | Parcelas que se llevan igual: apuntar una vez lo que se hace en seis |
| `tests/test_lo_que_he_apuntado_se_puede_corregir.py` | 32 | Corregir y borrar lo propio, con rastro en la auditoría y sin tocar lo firmado |
| `tests/test_cultivo_de_la_parcela.py` | 26 | Qué hay sembrado cada año, el historial y el aviso V5 |
| `tests/test_analisis_ventas_planes_y_campanas.py` | 66 | Borrar análisis, ventas, planes, medidas y campañas |
| `tests/test_asesor_semilla_y_agua.py` | 42 | Asesor, semilla y agua de riego dentro de la labor |
| `tests/test_dibujo_de_la_parcela.py` | 18 | La forma del trozo, que estaba en la base y no se veía |

### 3.3. Interfaz (la pantalla)

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_interfaz.py` | 105 | La pantalla se sirve con su tipo MIME, sin jerga, todas las preguntas existen y **los guardianes de las copias de textos** |
| `tests/test_design_md.py` | 22 | `DESIGN.md` y `estilos.css` dicen lo mismo (los colores viven solo en `:root`) |
| `tests_js/interfaz.test.js` | 254 | `app.js` arranca y los botones llevan a algún sitio, con un DOM de mentira |
| `tests_js/react.test.js` | 330 | Las 27 pantallas de React se dibujan y dicen lo que tienen que decir |
| `tests_js/nucleo.test.js` | 59 | Números en castellano, cola sin cobertura, repetir, buscador, validaciones y mensajes |
| `tests/test_la_migracion_a_react.py` | 14 | Que la migración a React **no vuelva atrás** (ni `pintar:` en un paso, ni `innerHTML` de pantallas) |
| `tests/test_react_vendor.py` | 13 | Los ficheros de React están, son los revisados y no se tocan |
| `tests/test_el_armazon_del_ordenador.py` | 13 | El menú lateral y la barra de arriba |
| `tests/test_los_botones_hacen_algo.py` | 4 | Todo botón que se pinta tiene quien lo atienda |
| `tests/test_la_version_visible.py` | 3 | La versión que se ve en el pie es la de verdad (y la misma que la caché) |
| `tests/test_el_formulario_manda_todo.py` | 6 | El formulario manda todo lo que la API acepta |
| `tests/test_ficheros_de_texto.py` | 723 | Ningún fichero de texto del proyecto lleva marca de orden de bytes (por el fallo de los acentos) |

### 3.4. Textos (cero jerga)

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_sin_jerga.py` | 21 | Ningún texto visible lleva jerga, y los avisos dicen qué hacer |
| `tests/test_que_no_falte_ningun_texto.py` | 4 | Todo texto que la interfaz pide existe (si no, la pregunta sale en blanco) |
| `tests/test_design_md.py` | — | Ver §3.3 |

### 3.5. Aislamiento entre explotaciones

Ver §4, con todas las pruebas una por una. Ficheros que las contienen:
`test_registro_obligatorio.py`, `test_analiticas.py`, `test_cosecha_comercializada.py`,
`test_plan_abonado.py`, `test_medidas_preventivas.py`, `test_documentos.py`, `test_facturas.py`,
`test_cesta_del_almacen.py`, `test_instalaciones.py`, `test_grupos_de_parcelas.py`,
`test_cultivo_de_la_parcela.py`, `test_las_tierras_se_pueden_corregir.py`,
`test_los_maestros_se_pueden_corregir.py`, `test_los_papeles_y_las_facturas_se_pueden_corregir.py`,
`test_lo_que_he_apuntado_se_puede_corregir.py`, `test_firma.py`, `test_asesor_semilla_y_agua.py`,
`test_borradores.py`, `test_cuaderno_cyl.py`, `test_cuaderno_cyl_exportar.py`,
`test_varias_cuentas_en_una_finca.py`, `test_analisis_ventas_planes_y_campanas.py`.

### 3.6. Firma y certificado

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_firma.py` | 45 | La huella es estable, cambiar algo cambia la huella, los tres estados (sin firmar / firmado / cambiado) y que la historia de las firmas se guarde entera |
| `tests/test_firma_cades.py` | 54 | Comprobar la firma **de verdad**, contra ficheros que hizo OpenSSL (`tests/fixtures/firma_cades/`), incluida una firma de otro agricultor y una de curva elíptica |
| `tests/test_certificado.py` | 44 | Leer el certificado, sacar el NIF y entrar con él; y que una cabecera `X-SSL-Client-Subject` falseada no sirva |
| `tests/test_firmar_con_el_certificado.py` | 15 | El guion que firma `data-signed` con el almacén de certificados de Windows (inspección del guion, sin abrir el almacén) |
| `tests/test_seguridad_de_las_claves.py` | 14 | Que el atajo de las iteraciones no se pueda colar en producción |

### 3.7. IUWS (volcado oficial a la Junta)

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_iuws.py` | 121 | Las direcciones del anexo, los 19 mensajes, el sobre, lo que falta y de quién, el contenido mínimo campo por campo, y que **lo que no se sabe no se inventa** |
| `tests/test_iuws_cliente.py` | 72 | El cliente que habla con el interfaz: contra respuestas guardadas y con transporte de mentira, incluidos 404, 500, sin red y respuestas que no son JSON |
| `tests/test_mapeo_oficial.py` | 144 | El mapeo campo a campo: 107 bloques y 402 campos, qué cubre cada modelo nuestro y qué falta |
| `tests/test_descriptor_del_cuaderno.py` | 20 | La tabla del descriptor oficial (obligatoriedad y catálogo de cada campo) |
| `tests/test_catalogos_de_siex.py` | 11 | El cruce entre los catálogos que pide el descriptor y los que publica SIEX |
| `tests/test_preguntas_pendientes_iuws.py` | 4 | Los datos que faltaban al agricultor se preguntan, guardan y devuelven |
| `tests/test_probar_iuws_con_certificado.py` | 7 | El guion que llama a la Junta con el certificado de Windows (inspección, sin llamar) |
| `tests/test_bajar_catalogos_fega.py` | 14 | Bajar los catálogos oficiales y **no** tocar el captcha de SIEX |
| `tests/test_comprobar_fuentes_oficiales.py` | 12 | Que comprobar una fuente oficial no engañe (huella para lo quieto, filas para lo que se genera al vuelo) |
| `tests/test_lista_de_la_junta.py` | 9 | Que la lista de lo que falta sume 21 y que los números de la documentación no se queden viejos |

### 3.8. Dictado y OCR

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_borradores.py` | 74 | El dictado entiende y **sobre todo no inventa**: la regla de oro de «dos litros» (dosis o total) y que `POST /api/borradores/desde-texto` devuelve una propuesta y no guarda nada |
| `tests/test_facturas.py` | 57 (1 omitida) | Leer una factura de un PDF y de una foto, que las cuentas cuadren o se avise, los idiomas del lector y la huella para no subirla dos veces |
| `tests/test_documentos.py` | 54 | La bandeja de papeles: catálogo, subir, descargar, carpetas, anular y que el nombre lo ponga el programa |
| `tests/test_los_papeles_y_las_facturas_se_pueden_corregir.py` | 46 | Corregir y borrar papeles y facturas sin romper el cuadre del almacén |

### 3.9. Almacén

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_cesta_del_almacen.py` | 35 | La Cesta: comprado contra gastado, y que con unidades que no se pueden comparar no se reste |
| `tests/test_facturas.py` | — | El cuadre «lo comprado sale de las facturas» (ver §3.8) |

### 3.10. Ventas / lo que se vende

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_cosecha_comercializada.py` | 60 | Lo que se vende: cuadra con lo cosechado, una unidad de lechugas no se suma con kilos, **no hay precio ni importe** y hay aislamiento |

### 3.11. Plan de abono

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_plan_abonado.py` | 32 | El plan, su comparación con lo abonado y **que actualizar la instalación no reviente** (crear columnas que faltan) |
| `tests/test_nitratos.py` | 35 | Las reglas de la zona de nitratos aplicadas al abono (ver §3.1) |

### 3.12. Medidas preventivas

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_medidas_preventivas.py` | 57 | Ver §3.2 |
| `tests/test_practicas_culturales.py` | — | Ver §3.2 |

### 3.13. Análisis de laboratorio

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_analiticas.py` | 78 | El catálogo como puerta, el boletín subido sin salirse de su carpeta, y el enganche con el plan |
| `tests/test_asesor_semilla_y_agua.py` | 42 | Ver §3.2 |

### 3.14. Suelo, SIGPAC y mapa

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_sigpac.py` | 49 | El conector del SIGPAC: el parser contra una respuesta **de verdad** guardada, los 933 productos oficiales y que sin cobertura se diga |
| `tests/test_mapa_del_sigpac.py` | 47 | Elegir la parcela tocándola en el mapa, y lo que el SIGPAC sabe de esa tierra |
| `tests/test_parcelas_por_codigos.py` | 30 | Dar de alta una parcela sin saberse ningún código (por municipio y número del visor) |
| `tests/test_cuaderno_cyl.py` | 41 | Traer las tierras del cuaderno de la Junta: leerlas y que subirlo dos veces no duplique tierras |
| `tests/test_cuaderno_cyl_exportar.py` | 28 | Sacar el cuaderno de la Junta relleno: el fichero de 25 hojas y la lista de lo que falta |

### 3.15. Corregir y borrar (rondas 91–94)

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_las_tierras_se_pueden_corregir.py` | 44 | Corregir y borrar tierras, su cultivo declarado y los grupos |
| `tests/test_los_maestros_se_pueden_corregir.py` | 88 | Corregir y borrar productos, abonos, aplicadores, asesores, máquinas y naves |
| `tests/test_lo_que_he_apuntado_se_puede_corregir.py` | 32 | Ver §3.2 |
| `tests/test_los_papeles_y_las_facturas_se_pueden_corregir.py` | 46 | Ver §3.8 |
| `tests/test_analisis_ventas_planes_y_campanas.py` | 66 | Ver §3.2 |

### 3.16. Cuentas

| Fichero | Casos | Qué prueba |
|---|---|---|
| `tests/test_cambiar_la_clave.py` | 10 | «Cambiar la clave desde este ordenador»: es lo único que hay en `tests/` que hable de claves de cuenta, **no de cuentas contables** |

### 3.17. **Áreas sin ninguna prueba (y sin código detrás)**

Comprobado sobre `backend/app/models.py` (26 clases, 24 de ellas con `explotacion_id`) y sobre las
172 rutas del esquema OpenAPI. **No falta solo la prueba: no hay modelo, ni ruta, ni pantalla.**

| Área del contrato | Qué falta exactamente | Comprobación |
|---|---|---|
| **Cuentas y economía** (S13) | Ingresos y gastos registrados, vencimientos, tesorería, caja, margen por cultivo/tierra, reparto de costes, subvención prevista/concedida/cobrada, ejercicio económico | No aparece `ingreso`, `gasto`, `margen` ni `ejercicio` en `app/`. `app/textos.py:3803-3804` dice a propósito que el «gasto en euros por producto» del diseño **no se ha copiado porque ese número no existe en el programa** |
| **Movimientos y conciliación bancaria** (S14) | Extractos, conciliación, traspasos propios, duplicados | No hay modelo de movimiento ni ruta |
| **Pagos y cobros parciales** (S11, S12) | Un pago, un vencimiento, un cobro, una cuota | No hay modelo de pago. La factura **no tiene** fecha de vencimiento ni estado de cobro |
| **Personas y empresas** (S15) | Cliente, proveedor, arrendador, trabajador, asesor como contacto con roles | No hay modelo `Persona`/`Contacto`. `proveedor` (`models.py:1175`) y `comprador` (`models.py:840`) son texto libre |
| **Maquinaria de la finca** (S16) | Tractor, remolque, aperos; ITV, seguro, mantenimiento, horas, próxima revisión, averías | El único modelo es `EquipoAplicacion` (`models.py:460-499`): máquinas de **echar producto**, con ROMA e ITEAF. Ver §6, puerta 4 |
| **Servicios a terceros** (S17) | Cliente externo, presupuesto, tarifa, superficie no propia, insumos del cliente | Nada |
| **Tiempo y observaciones** (S18) | Lluvia 24 h/7 d/30 d, estación, pluviómetro propio, humedad del suelo, satélite, NDVI, nubes, avisos ITACyL | `grep -i "ndvi|satelite|nubes|lluvia|precipitacion"` sobre `backend/app/` → **0 coincidencias** |
| **PAC** (S07, S21) | Compromisos, ecorregímenes, escenarios, denominadores, rotación, resultados por regla, paquete preparatorio | El ecorregimen solo existe como **texto** en el cultivo declarado (`test_cuaderno_cyl.py:108`). No hay motor de reglas |
| **Recepción y albarán de compra** (S08, S11, A15) | `Recepcion`, `LineaRecepcion`, albarán como hecho con fecha propia | No hay modelo. La factura es la **única** puerta a la existencia: ver §6, puerta 2 |
| **Lotes y libro de movimientos de existencias** (S08) | `Articulo`, `Lote`, `MovimientoExistencias`, reservas, ubicaciones, caducidades por lote | No hay modelo. La «cesta» **calcula** comprado − gastado (`app/servicios.py:720-772`) |
| **Semillas como entidad** (§5 del contrato) | `ArticuloSemilla`, `LoteSemilla`, categoría, certificador, germinación, pureza, reempleo, merma y su prueba de saldo (1.000 → 600 + 100 = 300) | No hay modelo. La semilla son columnas de `Labor` (`lote_semilla`, `cantidad_semilla_kg`…), y hay pruebas de que se apuntan (`test_asesor_semilla_y_agua.py:202`) pero **no de que cuadre un saldo**, porque no hay existencias |
| **Roles y permisos por acción** (S20) | Titular, gestor, trabajador, asesor, consulta; permiso económico separado | Solo hay titular y ayudante (`test_varias_cuentas_en_una_finca.py`). No hay `rol` con cinco valores ni permiso por acción |
| **Versión y conflicto de edición** (§2) | Versión esperada, comparación de cambios en vez de sobreescritura | No hay columna de versión en los apuntes. Corregir cambia la fila y deja rastro en `auditoria`, pero nada detecta que dos personas graben a la vez |
| **Idempotencia de comandos** (§2, A12) | Identificador de petición único que haga que reenviar devuelva el mismo resultado | Ninguna ruta lo tiene. `grep -i "idempot"` sobre `backend/app/` → solo un comentario en `accesos.py:36` sobre otra cosa |
| **Contrapartidas al anular** (§2) | Anular crea contrapartidas de existencias y efectos económicos | Anular marca `anulado` + `motivo_anulacion` y deja rastro; **no** genera contrapartida (no hay existencias que compensar) |
| **Copia de seguridad y restauración** (S20) | Copia con base, adjuntos y manifiesto verificable; restauración probada en entorno separado | Nada |
| **Estados de pantalla obligatorios** (§3) | Cargando, sin resultados, acceso restringido, servicio no disponible, copia local antigua, conflicto… | Hay algo (cola sin cobertura, «no hay nada» en varias listas) pero **no** hay prueba de los nueve estados |
| **Teclado, foco y zoom 200 %** (§3) | Navegación con teclado, foco visible, zoom 200 % | Hay pruebas de tamaño de letra y de zoom con los dedos (`test_interfaz.py:1090-1129`), **no** de teclado ni de foco |

---

## 4. Aislamiento entre explotaciones

La regla del proyecto está en `AGENTS.md` §3.5 y `docs/QUIEN_ENTRA_EN_LA_FINCA.md`: `explotacion_id`
en todas las tablas de negocio, todo pasa por `obtener_de_la_explotacion()`, y **lo de otra finca
contesta 404, nunca 403**, para no filtrar si el identificador existe.

### 4.1. Las pruebas que lo comprueban (68, todas con una segunda cuenta de verdad)

El patrón es siempre el mismo: se crea un dato en la finca A con la fixture `cuenta`, se crea una
cuenta B con `crear_cuenta` (`conftest.py:160-177`) y se intenta ver o tocar desde B.

**Parcelas y tierras**

| Fichero:línea | Qué comprueba |
|---|---|
| `tests/test_registro_obligatorio.py:545` | `TestAislamiento::test_no_se_ve_la_parcela_de_otra_finca` |
| `tests/test_registro_obligatorio.py:550` | No se puede apuntar un tratamiento en una parcela ajena |
| `tests/test_registro_obligatorio.py:570` | Cada finca ve solo sus parcelas |
| `tests/test_las_tierras_se_pueden_corregir.py:370` | Corregir la tierra de otra finca contesta 404 |
| `tests/test_las_tierras_se_pueden_corregir.py:519` | Borrar la tierra de otra finca contesta 404 |
| `tests/test_las_tierras_se_pueden_corregir.py:758` | El cultivo declarado de otra finca no se toca |
| `tests/test_las_tierras_se_pueden_corregir.py:854` | No se puede corregir un grupo metiendo una tierra ajena |
| `tests/test_las_tierras_se_pueden_corregir.py:926` | El grupo de otra finca no se toca |
| `tests/test_grupos_de_parcelas.py:138` | Una finca no ve los grupos de otra |
| `tests/test_cultivo_de_la_parcela.py:112` | Una finca no ve los cultivos de otra |
| `tests/test_cultivo_de_la_parcela.py:117` | No se puede declarar cultivo en una parcela ajena |
| `tests/test_cuaderno_cyl.py:505` | Cada explotación ve solo sus tierras traídas del cuaderno de la Junta |
| `tests/test_cuaderno_cyl_exportar.py:437` | El fichero del cuaderno de la Junta sale solo con lo suyo |

**Apuntes del cuaderno**

| Fichero:línea | Qué comprueba |
|---|---|
| `tests/test_lo_que_he_apuntado_se_puede_corregir.py:219` | El tratamiento de otra finca no se toca |
| `tests/test_lo_que_he_apuntado_se_puede_corregir.py:305` | El apunte de otra finca no se borra |
| `tests/test_lo_que_he_apuntado_se_puede_corregir.py:591` | Una factura de otra finca no se puede enlazar a un abono |
| `tests/test_lo_que_he_apuntado_se_puede_corregir.py:633` | Corregir no cambia de finca |

**Maestros (las seis fichas, parametrizadas)**

| Fichero:línea | Qué comprueba |
|---|---|
| `tests/test_los_maestros_se_pueden_corregir.py:508` | `test_la_ficha_de_otra_finca_no_se_toca` — corre con `MAESTROS` = producto, fertilizante, aplicador, asesor, equipo e instalación (`:193-331`) |
| `tests/test_los_maestros_se_pueden_corregir.py:629` | `test_la_ficha_de_otra_finca_no_se_borra` — las mismas seis |
| `tests/test_asesor_semilla_y_agua.py:166` | Un asesor de otra finca no se puede usar en un tratamiento |
| `tests/test_cesta_del_almacen.py:321` | Una finca no ve los productos de otra |
| `tests/test_instalaciones.py:51` | Cada finca ve solo sus naves |
| `tests/test_instalaciones.py:56` | No se puede ver una nave ajena |
| `tests/test_instalaciones.py:121` | No se puede apuntar un tratamiento en una nave ajena |

**Análisis, planes, medidas, ventas y campañas**

| Fichero:línea | Qué comprueba |
|---|---|
| `tests/test_analiticas.py:434` | El boletín de otra finca no se puede ni leer |
| `tests/test_analiticas.py:486` | Un análisis de otra finca no se ve |
| `tests/test_analiticas.py:491` | No se puede leer el análisis de otra finca |
| `tests/test_analiticas.py:498` | No se puede atar un análisis a la parcela de otro |
| `tests/test_analiticas.py:517` | No se puede apoyar un plan en el análisis de otro |
| `tests/test_analisis_ventas_planes_y_campanas.py:186` | El análisis de otra finca no se borra |
| `tests/test_analisis_ventas_planes_y_campanas.py:343` | La venta de otra finca no se borra |
| `tests/test_analisis_ventas_planes_y_campanas.py:431` | El plan de otra finca no se borra |
| `tests/test_analisis_ventas_planes_y_campanas.py:675` | Una finca no quita la declaración de medidas de la otra |
| `tests/test_analisis_ventas_planes_y_campanas.py:885` | La campaña de otra finca no se toca |
| `tests/test_analisis_ventas_planes_y_campanas.py:961` | La campaña de otra finca no se borra |
| `tests/test_plan_abonado.py:218` | Cada finca ve solo sus planes |
| `tests/test_plan_abonado.py:223` | No se puede ver un plan de otra finca |
| `tests/test_medidas_preventivas.py:326` | Cada finca declara lo suyo |
| `tests/test_medidas_preventivas.py:333` | Lo que declara uno no avisa en los apuntes del otro |
| `tests/test_cosecha_comercializada.py:476` | Cada finca ve sus ventas |
| `tests/test_cosecha_comercializada.py:480` | Una venta de otra finca no se puede leer |
| `tests/test_cosecha_comercializada.py:486` | No se puede vender con la parcela de otro |
| `tests/test_cosecha_comercializada.py:504` | La cosecha de otra finca no cuenta en mi cuadre (**totales**, no solo listados) |

**Papeles, facturas y firmas**

| Fichero:línea | Qué comprueba |
|---|---|
| `tests/test_documentos.py:435` | Una finca no ve los papeles de otra |
| `tests/test_documentos.py:441` | No se puede descargar el papel de otra finca |
| `tests/test_documentos.py:452` | No se puede anular el papel de otra finca |
| `tests/test_documentos.py:464` | No se puede subir un fichero al papel de otra finca |
| `tests/test_facturas.py:583` | No se puede enganchar una factura a un producto de otra finca |
| `tests/test_facturas.py:818` | Las facturas de otra finca no se ven |
| `tests/test_facturas.py:823` | No se puede ver la factura de otra finca |
| `tests/test_facturas.py:833` | No se puede ver su fichero |
| `tests/test_los_papeles_y_las_facturas_se_pueden_corregir.py:218` | El papel de otra finca no se toca |
| `tests/test_los_papeles_y_las_facturas_se_pueden_corregir.py:300` | El papel de otra finca no se borra (ni su fichero) |
| `tests/test_los_papeles_y_las_facturas_se_pueden_corregir.py:560` | Un producto de otra finca se rechaza igual en el alta y en la corrección |
| `tests/test_los_papeles_y_las_facturas_se_pueden_corregir.py:607` | Una corrección rechazada no deja productos sueltos en la cesta |
| `tests/test_los_papeles_y_las_facturas_se_pueden_corregir.py:761` | La factura de otra finca no se toca |
| `tests/test_los_papeles_y_las_facturas_se_pueden_corregir.py:1048` | La factura de otra finca no se borra |
| `tests/test_firma.py:448` | No se puede firmar un apunte de otra finca |
| `tests/test_firma.py:462` | Cada finca ve solo sus firmas |

**El dictado y el acceso (varias cuentas en una finca)**

| Fichero:línea | Qué comprueba |
|---|---|
| `tests/test_borradores.py:467` | El borrador no puede proponer una parcela o un producto de otro agricultor |
| `tests/test_varias_cuentas_en_una_finca.py:59` | El titular da acceso a otra cuenta y **las dos ven lo mismo** (la prueba que justifica todo lo demás) |
| `tests/test_varias_cuentas_en_una_finca.py:111` | Un ayudante usa la finca pero no decide quién entra |
| `tests/test_varias_cuentas_en_una_finca.py:155` | Quitar el acceso lo quita de verdad |
| `tests/test_varias_cuentas_en_una_finca.py:215` | No se puede dar dos veces el mismo acceso |
| `tests/test_varias_cuentas_en_una_finca.py:232` | Una finca que no es tuya no se puede elegir |
| `tests/test_varias_cuentas_en_una_finca.py:245` | Un vale de una finca sin acceso no vale |
| `tests/test_varias_cuentas_en_una_finca.py:256` | Lo de otra finca sigue contestando 404 |
| `tests/test_varias_cuentas_en_una_finca.py:317` | Cada finca dice las suyas y no las de la otra (también en las **hectáreas**) |

### 4.2. Entidades **no** cubiertas por una prueba de aislamiento

De las 24 clases con `explotacion_id` en `models.py`, estas **no** tienen una prueba propia de
aislamiento (nótese que la mayoría sí están cubiertas **de refilón**: la prueba de otra entidad ya
pasa por la misma puerta, pero eso no es una prueba de esa entidad):

| Entidad | Situación |
|---|---|
| `Fertilizante` (abono) | **Cubierta solo por la vía indirecta**: `test_los_maestros_se_pueden_corregir.py:508,629` (corregir/borrar con el id de otra finca) y `test_lo_que_he_apuntado_se_puede_corregir.py:591` (factura ajena). **No hay prueba de que una finca no vea los abonos de otra** ni de que no pueda abonar con el abono de otro |
| `Aplicador` | Igual: solo la corrección/borrado parametrizado. **No** hay prueba de usar un aplicador ajeno en un tratamiento (sí la hay para el asesor: `test_asesor_semilla_y_agua.py:166`) |
| `EquipoAplicacion` (máquina) | `test_practicas_culturales.py:437` dice en su nombre «una máquina de otra finca no vale», pero **manda un identificador que no existe (`99999`, línea 452)** y **no crea una segunda cuenta**. Comprueba que un id inventado da 404, no que el de otra finca lo dé. Es el agujero más claro: ver §7, riesgo 1 |
| `RegistroFertilizacion` (abono apuntado) | No hay prueba de leer/corregir/borrar una fertilización de otra finca. Sí hay, en cambio, para `TratamientoFitosanitario` y `Labor` |
| `Labor` | No hay prueba de aislamiento de una labor. Lo más cerca: `test_practicas_culturales.py:437` (la máquina, y mal: ver arriba) |
| `Auditoria` | No hay ninguna prueba de aislamiento del rastro de auditoría |
| `LineaDeFactura` | Indirecta (la factura ya se prueba); no hay prueba de la línea por separado |
| `Usuario` / `AccesoAFinca` | Cubiertas por `test_varias_cuentas_en_una_finca.py`, pero **no** por una prueba de «ver datos de otra» (son pruebas de quién entra, que es otra cosa) |

Y estas entidades de negocio **no existen**, así que tampoco pueden tener prueba de aislamiento:
pagos, movimientos de cuenta, recepciones, albaranes, lotes de existencias, semillas como entidad,
personas/contactos y maquinaria que no sea de aplicación.

---

## 5. Las pruebas de aceptación del contrato (A01–A16)

Ninguna prueba de la suite cita los identificadores `A01`–`A16` (búsqueda literal en `tests/`:
0 coincidencias). Así que lo de abajo es el juicio caso por caso: dónde está el equivalente, y
dónde el equivalente **comprueba otra cosa**.

### A01 — Compra 5 L, aplicación 2 L y 3 L → saldo 0; reenvío no duplica; anular 2 L devuelve 2

**A medias.** Dos de los tres extremos están; el del medio **no existe**.

- Saldo = comprado − gastado: `tests/test_cesta_del_almacen.py:145` (sin tratamientos queda todo lo
  comprado), `:155` (1,5 L/ha en 10 ha = 15 L, y de 20 quedan 5) y `:164` (dos tratamientos se suman).
  **Pero con 20 − 15, no con 5 − 2 − 3**, y sin factura de por medio.
- Anular devuelve lo gastado: `tests/test_cesta_del_almacen.py:195` (un tratamiento anulado no cuenta).
- **Reenvío no duplica: no existe.** No hay identificador de petición en ninguna ruta; ver A12.

### A02 — 2 L en 4 ha → 0,5 L/ha; si falta área, dosis desconocida

**No existe.** `app/legal.py:68` solo calcula `cantidad_total(dosis, hectáreas)`, **en un sentido**:
de dosis a total, nunca de total a dosis. `tests/test_legal.py:70` prueba justo la dirección contraria
(0,8 × 2,43 = 1,944). Y la segunda mitad tampoco: `superficie_tratada_ha` y `dosis` son opcionales
(`app/schemas.py:481,489`) y `cantidad_total` queda en `None` cuando falta una
(`app/servicios.py:43-45`), pero **ninguna prueba comprueba que sin área la dosis queda
desconocida**: no hay prueba de ese «no lo sé».

### A03 — Abono 600 kg en 3 ha, N 15 % → 200 kg/ha de producto; 30 kg N/ha; P desconocido si falta

**A medias, y la última parte está mal.**

- El cálculo de kg/ha y de N/ha existe y está probado, **con otros números**: `tests/test_legal.py:44`
  (300 kg al 33,5 % = 100,5 kg N), `tests/test_legal.py:51`, y `tests/test_registro_obligatorio.py:425`
  (300 kg/ha al 33,5 % = 100,5 kg N/ha; 729 kg totales; 244,215 kg N). El caso 600/3/15 % no está,
  pero es la misma fórmula.
- **«P desconocido si falta» es falso hoy.** `riqueza_p` y `riqueza_k` son `float` **con valor por
  defecto 0,0** y no admiten vacío: `app/schemas.py:353-355`, `app/models.py:389-391` (abono) y
  `app/models.py:874-876` (apunte). Un abono del que solo se sabe el nitrógeno sale en el papel con
  **«0,00 kg/ha de P»**, o sea «es cero» donde debería decir «no lo sé». Contradice el §2 del
  contrato y el §3.3 de `AGENTS.md`. No hay ninguna prueba que lo cace (búsqueda de `riqueza_p` en
  `tests/`: 6 coincidencias, todas para rellenarlo con `0.0`, ninguna para exigir que quede vacío).

### A04 — Rodillo después de siembra → historial contiene ambos; cultivo permanece; sin inferir nascencia

**Casi.** El historial y la permanencia del cultivo sí; la «nascencia» no está atada por ninguna
prueba.

- La labor (rodillo = `laboreo`) se apunta y sale en el papel y el fichero:
  `tests/test_practicas_culturales.py:161,176,700`.
- El cultivo declarado es otra cosa y el apunte lo hereda sin pisarlo:
  `tests/test_cultivo_de_la_parcela.py:60` (una parcela sin cultivo dice que le falta), `:68`, `:186`
  (el tratamiento coge el cultivo de la parcela), `:204` (la labor también), `:220` (si el apunte trae
  el suyo, manda el suyo), `:243` (sin cultivo declarado se queda vacío y **no se inventa**).
- **Lo que falta:** una prueba que ate «una labor de tipo `laboreo` **después** de una `siembra` no
  cambia el cultivo declarado ni crea ningún estado de nascencia». Hoy no hay ni campo de nascencia
  en el modelo (0 apariciones de «nascencia» en `backend/app/`), así que el daño no puede ocurrir,
  pero **tampoco hay prueba**: la única frase que lo dice es un comentario del guion de Stitch
  (`backend/scripts/disenar_con_stitch.py:1092`, «una labor no es un cultivo»).

### A05 — Plan de siembra confirmado como plan → no consume semillas ni añade labor realizada

**No existe.** No hay plan de siembra: el plan que hay es de **abono** (`PlanAbonado`), y las semillas
no son existencias (no hay `ArticuloSemilla` ni `LoteSemilla`, ver §3.17). Sin existencias de semilla
no hay nada que consumir, y sin plan de siembra no hay nada que confirmar. La prueba de saldo del §5
del contrato (1.000 kg → 600 + 100 → 300) **no se puede escribir hoy**.

Sobre el plan de abono, que es el análogo: hay pruebas de que **lee** lo abonado
(`tests/test_plan_abonado.py:233,285,320,329`) y de que un abono anulado no cuenta (`:269`), pero
**ninguna de que el plan no cree apuntes realizados**. Es un hueco de la misma familia que A05.

### A06 — Factura 121 EUR, pago 40 EUR → pendiente 81; segundo importe conciliado no crea segunda factura

**No existe.** No hay pagos, ni vencimientos, ni conciliación, ni cuotas (ver §3.17). La factura
guarda `base_imponible`, `cuota_iva`, `total` (`app/models.py:1178-1181`) y nada más: **no hay fecha
de vencimiento, ni importe pagado, ni estado de cobro**. Lo más cerca es el cuadre de la **cesta**
(unidades, no euros) en `tests/test_facturas.py:655`.

### A07 — Traspaso propio 500 EUR → dos movimientos vinculados, cero ingreso/gasto operativo

**No existe.** No hay movimientos de cuenta (ver §3.17).

### A08 — Venta con 8.000 kg y sin precio → cantidad conocida, importe pendiente; no ingreso cero

**A medias, y la mitad que falta es una decisión de producto, no un olvido.**

- Cantidad conocida y **no ingreso cero**: `tests/test_cosecha_comercializada.py:126`
  (`test_no_hay_precio_ni_importe`: la respuesta no lleva `precio`, ni `importe`, ni `euros`) y `:132`
  (la pantalla dice «no se apunta el precio aquí»). La decisión está escrita en `app/models.py:808-811`.
- «**Importe pendiente**» **no existe** como concepto: no hay un campo de importe que pueda quedar
  pendiente. Es distinto de «no se apunta el precio»: el contrato pide el estado «pendiente» y aquí
  el dinero simplemente no está en esta sección.
- Lo que sí está: sin cantidad no se guarda (`:165`) y una cantidad de cero no vale (`:169`).

### A09 — Fuente legal de otra comunidad/año → no se aplica a CyL 2026 por semejanza

**No existe.** `ReglaNitratos` (`app/catalogos.py:934-950`) tiene `clave`, `que`, `valor`, `unidad`,
`fuente` y `que_hace_la_app`, pero **no** tiene comunidad ni campaña: la `fuente` es texto libre
(`FUENTE_ORDEN_MAV`, `app/catalogos.py:953-958`). No hay ningún mecanismo, ni código ni prueba, que
impida aplicar una regla de otra comunidad o de otro año. Lo único que hay es
`tests/test_nitratos.py:44` («cada regla dice de dónde sale») y
`tests/test_lo_que_obliga_la_ley.py:160` («las constantes llevan su norma al lado»): comprueban que la
fuente está escrita, **no** que la regla sea la de aquí y de ahora.

### A10 — 2 ha sin cultivo en denominador PAC → resultado incompleto, nunca verde ignorando esas hectáreas

**No existe** como tal: no hay PAC (compromisos, ecorregímenes, denominadores, resultados por regla).
Lo más cerca, en otros dos sitios:

- `tests/test_cultivo_de_la_parcela.py:60` — una parcela sin cultivo **sale en la lista diciendo que
  le falta**, en vez de esconderse.
- `tests/test_registro_obligatorio.py:705,714` — «lo que falta» del cuaderno nombra la parcela y dice
  qué le falta; cuando está todo, lo dice.

Es la misma idea («no dar por bueno lo incompleto»), pero **no es un denominador PAC** y no hay nada
que impida un verde ficticio en un cálculo de superficies.

### A11 — Imagen cubierta por nubes → sin dato útil; no NDVI cero ni alarma de sequía

**No existe.** No hay satélite ni NDVI ni nubes: `grep -i` sobre `backend/app/` da **0 coincidencias**
para `ndvi`, `satelite`, `satélite`, `nubes`, `lluvia` y `precipitacion`. No hay código que pueda dar
un NDVI cero porque no hay imagen que leer.

### A12 — Móvil repite envío al reconectar → un trabajo, sus consumos una vez, respuesta recuperable

**No existe la parte que importa.** Lo que sí hay es la cola del móvil, y está bien probada
(`tests_js/nucleo.test.js:203` sin cobertura se espera, `:209` al volver la cobertura se manda lo
pendiente, `:164` lo mandado se quita de la cola). Pero:

- El cliente manda **solo los datos del apunte**: `backend/web/app.js:426-429` hace
  `POST apunte.ruta` con `body: JSON.stringify(apunte.datos)`. El `id_local` que la cola sí genera
  (`backend/web/nucleo.js:177`) **no viaja al servidor**.
- Ninguna ruta del servidor es idempotente (no hay identificador de petición, ver §3.17). Si la
  respuesta se pierde **después** de que el servidor haya guardado, el reintento creará un segundo
  tratamiento, y el cuaderno dirá que se trató dos veces.
- **Ninguna prueba comprueba el reenvío contra el servidor.** Las dos cosas que se le parecen son de
  otra familia: la huella de un fichero para no subir la misma factura dos veces
  (`tests/test_facturas.py:434`) y que subir el cuaderno de la Junta dos veces no duplique tierras
  (`tests/test_cuaderno_cyl.py:390`).

### A13 — Tierra ajena o enlace a adjunto de otra finca → sin datos ni filtración de existencia

**Sí existe, y es el área mejor cubierta del programa.** Son 68 pruebas, todas con una segunda cuenta
de verdad, y todas comprueban **404 y no 403**. Están listadas una por una en §4.1. Los casos que el
contrato pide expresamente: tierra ajena (`tests/test_registro_obligatorio.py:545,550`,
`tests/test_las_tierras_se_pueden_corregir.py:370,519`) y enlace a un adjunto de otra finca
(`tests/test_documentos.py:441,464`, `tests/test_facturas.py:833`,
`tests/test_los_papeles_y_las_facturas_se_pueden_corregir.py:300`).

### A14 — Editar registro firmado → revisión nueva, firma antigua verificable y bytes idénticos

**A medias.** Tres cosas sí, dos no.

| Lo que pide | Estado |
|---|---|
| Un apunte firmado no se borra y se dice qué hacer | **Sí**: `tests/test_lo_que_he_apuntado_se_puede_corregir.py:318` (409 y el mensaje `B1_firmado_no_se_borra`), y `:336` (sí se puede anular, que es la salida) |
| La firma antigua **se conserva** | **Sí**: `tests/test_firma.py:393` («la historia de las firmas se guarda entera»: si el cuaderno cambia, quedan las dos) |
| Avisar de que el cuaderno cambió después de firmar | **Sí**: `tests/test_firma.py:360` (el test que justifica toda la firma) |
| **Revisión nueva** al editar | **No**. No hay columna de versión ni de revisión en los apuntes: corregir cambia la fila (`app/routers/registros.py:284`) y deja el rastro en `auditoria`. Lo único que se numera es la firma (`app/models.py:1053`, `version_canonica`) |
| **Bytes idénticos** de lo firmado | **No comprobado, y probablemente imposible hoy.** La firma guarda el fichero `.p7s` en base64 (`app/models.py:1061`) y la **huella** del texto canónico (`:1052`), pero **el texto canónico firmado no se guarda**: se recalcula desde los datos. Si los datos cambian, el documento de la versión vieja ya no se puede reproducir, así que no hay bytes que comparar. No hay ninguna prueba que intente reproducirlos |

### A15 — Factura llega después de albarán recibido → una entrada de almacén y vínculo entre ambos

**No existe.** No hay `Recepcion`, ni `LineaRecepcion`, ni albarán de compra como hecho con fecha
propia (ver §3.17). Y el problema de fondo está al revés de como lo describe el contrato: ver §6,
puerta 2.

### A16 — Filtro de 10 tierras de un total de 64 → pie 10 de 64; exportación y mapa respetan la selección

**A medias, y lo que falta es de fondo.**

- **El pie «N de M» existe y está probado**, pero **con 2 tierras y no con 64**:
  `tests_js/interfaz.test.js:8980` (con el buscador, el pie dice «1 de 2 tierras») y
  `tests_js/interfaz.test.js:3308-3324` (el filtro de las que faltan: «1 de 2 tierras»). El código
  está en `backend/web/app.js:8706-8714` (tabla de cultivos) y `:6922-6938` (pie de tabla).
- **El filtro es del navegador, no del servidor.** `GET /api/parcelas` devuelve
  `list[ParcelaSalida]` sin filtros tipados, sin orden, sin paginación y **sin total de contexto**
  (`backend/app/routers/parcelas.py:230-231`). El contrato (§11) pide «items, total filtrado, total de
  contexto y agregados completos»; hoy la pantalla filtra una lista que ya tiene entera en memoria.
  Con 64 tierras da igual; con 6.400 no.
- **La exportación no respeta ninguna selección.** `GET /api/cuaderno/export.csv` solo acepta
  `campana_id` (`backend/app/routers/cuaderno.py:737-740`) y saca **todas** las tierras.
- **El mapa:** no hay ninguna prueba de que la selección de la tabla y la del mapa sean la misma.

### Resumen de A01–A16

| | Casos |
|---|---|
| **Existe** | **A13** |
| **A medias** (una parte comprobada, otra no) | **A01, A03, A04, A08, A14, A16** |
| **No existe** | **A02, A05, A06, A07, A09, A10, A11, A12, A15** |

---

## 6. Puertas de calidad de la sección 9 («qué no declarar terminado»)

### Puerta 1 — «VentaDeCosecha no acredita ingresos» → **VERDAD hoy**

- El modelo **no tiene precio ni importe**: `app/models.py:808-811` lo dice como decisión («no hay
  precio ni importe. No es un olvido»), y los campos que tiene son fecha, fecha_fin, producto,
  variedad, cantidad, unidad, lote, comprador, albarán y parcelas (`app/models.py:820-848`).
- No hay ningún sitio del programa que sume dinero de una venta: `grep -i "ingreso|gasto|margen"` en
  `backend/app/` solo devuelve comentarios que dicen precisamente que ese número **no existe**
  (`app/textos.py:3803-3804`).
- **Cómo se verifica con una prueba:** ya está verificado, y bien:
  `tests/test_cosecha_comercializada.py:126` (la venta no trae `precio`, ni `importe`, ni `euros`),
  `:132` (la pantalla lo dice) y `:126`+`app/models.py:808-811` juntos. Lo que **no** está probado es
  que ningún panel futuro sume las ventas: no hay prueba que recorra las respuestas de la API
  buscando un campo de dinero en una venta.

### Puerta 2 — «Factura no acredita recepción» → **FALSO hoy**

La factura **sí** es lo que hace aparecer la existencia, y no hay otra puerta:

- Confirmar una factura crea (o engancha) el producto **con la cantidad de la línea**:
  `app/routers/facturas_api.py:472-480` (`cantidad_comprada=linea.cantidad`, `unidad_compra`,
  `fecha_compra` y `proveedor` salen de la factura).
- El cuadre del almacén se calcula desde las líneas de factura, y **las facturas mandan sobre la
  ficha del producto**: `app/servicios.py:705-708` («las facturas mandan sobre la ficha») y
  `:720-772` (`comprado_de_un_producto`). Si hay facturas, el número de la ficha se ignora.
- No existe `Recepcion` ni albarán de compra como hecho aparte (ver §3.17), así que **no hay manera
  de apuntar «la mercancía llegó» sin factura**, ni de que llegue el albarán y después la factura
  sin contar dos veces. Esto incumple §4-S08 («Compra y factura son eventos distintos: la mercancía
  recibida una vez no entra otra vez al llegar su factura») y es exactamente A15.
- **Cómo se verificaría:** una prueba que (1) reciba 40 L contra un albarán, (2) confirme después la
  factura de esos mismos 40 L y (3) compruebe que la cesta sigue diciendo **40** y no 80, y que hay
  un vínculo entre los dos documentos. Hoy esa prueba **no se puede escribir**: faltan los modelos.

### Puerta 3 — «foto_etiqueta no acredita flujo de cámara» → **VERDAD hoy, y es peor de lo que dice**

- `foto_etiqueta` existe en **dos sitios y solo dos**: `app/models.py:378` (columna de texto de 400
  caracteres) y `app/schemas.py:318` y `:347` (se acepta al dar de alta y se devuelve al leer).
- **Nadie la escribe nunca**: no la menciona ni un router, ni una plantilla, ni un fichero de
  JavaScript (búsqueda literal en todo `backend/`: 3 coincidencias, las tres de arriba).
- O sea: no es solo que no haya flujo de cámara — es un dato **sin puerta**, el fallo que
  `AGENTS.md` §4 documenta como el que más se repite en este proyecto. Se puede mandar por la API y
  no se puede rellenar desde ninguna pantalla.
- **Cómo se verificaría:** una prueba que compruebe que **todo campo de un esquema de entrada tiene
  quien lo pregunte** en la pantalla (el guardián ya existe para las preguntas:
  `tests/test_interfaz.py` `TestCadaPreguntaTieneSuTexto` y
  `TestLasPreguntasDelAsistenteEstanYSeComprueban`, que sacan las claves del propio `app.js`; lo que
  falta es el guardián en el sentido contrario: de `schemas.py` hacia la pantalla).

### Puerta 4 — «EquipoAplicacion no cubre toda la maquinaria» → **VERDAD hoy**

- El único modelo de máquinas es `EquipoAplicacion` (`app/models.py:460-499`), que es, con sus
  palabras, «una máquina de echar producto: el pulverizador, el atomizador, la mochila». Tiene
  `titularidad` (propia / ajena / sin ROMA), marca, modelo, `numero_roma`, `numero_serie`,
  `fecha_adquisicion`, `fecha_iteaf` y `fecha_proxima_iteaf`. **No hay ITV, ni seguro, ni
  mantenimiento, ni horas, ni disponibilidad.**
- Y las **labores** apuntan ahí: `equipo_id` de `Labor` es una clave ajena a `equipos_aplicacion`
  (`app/models.py:967`), igual que en los tratamientos (`:574`). O sea: para apuntar que se labró con
  el tractor hay que dar de alta un «equipo de aplicación». Es lo que hace el propio test de la
  labor con máquina (`tests/test_practicas_culturales.py:409`).
- **Cómo se verificaría:** una prueba que dé de alta un tractor (sin ROMA y sin ITEAF), lo use en una
  labor de tipo `laboreo` y compruebe que el programa **no** le pide el ROMA ni la ITEAF; más otra
  que compruebe que cada obligación (ITV, ITEAF, seguro, ROMA) tiene su aplicabilidad, su fuente y su
  documento. Hoy no se puede escribir: falta el modelo de maquinaria.

### Puerta 5 — «Revisar defaults permisivos antes de reutilizarlos» → **hay dos defaults permisivos vivos, y uno ya está documentado como fallo**

1. **`autorizado` y `permitido_ecologico` nacen en `True`** (`app/models.py:373-374`). Es un default
   permisivo de verdad: un producto se da por autorizado y por válido para ecológico **sin que nadie
   lo haya comprobado**. Está justificado (`tests/test_autorizacion_del_producto.py:72-76`: «el
   defecto es "sí", que es lo que pasa con lo que se compra en una tienda»), y ese mismo fichero
   documenta en su cabecera que durante tres rondas las comprobaciones **no podían saltar** porque el
   dato no se podía meter por ninguna pantalla — que es el fallo de la puerta 3 otra vez.
   *Cómo se verifica:* ya hay prueba de que se puede decir que no (`:78`) y de que entonces bloquea
   (`:107`). Lo que **no** hay es prueba de que un producto con `autorizado=True` por defecto no
   acabe en un volcado oficial como «autorizado» sin haberse consultado el registro: el registro
   oficial se comprueba por otro camino (`tests/test_registro_oficial_de_productos.py`) y su aviso
   **nunca bloquea** (`:233`).
2. **`riqueza_p` y `riqueza_k` nacen en `0.0` y no admiten vacío**
   (`app/schemas.py:353-355`, `app/models.py:389-391,874-876`). Aquí el default permisivo es al
   revés y es peor: convierte **«no lo sé» en «es cero»**, que es justo lo que prohibe §2
   («Valores vacíos no equivalen a cero, falso, ecológico, autorizado o pagado»). Un abono del que
   solo se conoce el nitrógeno sale con P y K a cero en el cuaderno. Ver A03.
   *Cómo se verificaría:* una prueba que dé de alta un abono con solo `riqueza_n` y compruebe que
   `uf_p_ha` y `uf_k_ha` quedan **vacíos** (y no `0.00`) en la respuesta y en el papel. Hoy esa
   prueba **fallaría**, que es precisamente lo que hay que saber antes de reutilizar el modelo.

### Lo demás de la sección 9, comprobado

| Afirmación de la sección 9 | Estado hoy |
|---|---|
| «Migraciones: copia de base y adjuntos, ensayo de restauración, transformación versionada, conteos antes/después, firma intacta, vuelta atrás probada» | **No existe.** No hay copia, ni restauración, ni migración versionada. Lo que sí hay es el añadido automático de columnas (`app/database.py`, `crear_tablas`) y pruebas buenas de eso (`tests/test_plan_abonado.py:441-502`). La propia sección 9 avisa: «el añadido automático de columnas no sustituye migraciones de datos ni de dinero» |
| «Pruebas de OCR con documentos autorizados reales… inclinación, sombras, varias páginas, coma decimal, IVA incluido, albarán, rectificativa y factura sin producto identificable» | **Parcial.** Coma decimal: sí (`tests/test_facturas.py:130,133`). IVA incluido/excluido y varias líneas: sí (`:187,255`). «Factura sin producto identificable»: sí (`:290,312`). **No hay** inclinación, sombras, varias páginas, albarán ni rectificativa, y **no hay corpus separado de desarrollo y evaluación**. El aviso del fichero (`:15`) dice que las facturas de prueba son **inventadas** y sin datos de nadie |
| «No prometer un porcentaje de exactitud sin medirlo» | **Se cumple**: no hay ningún porcentaje en el código. `tests/test_autorizacion_del_producto.py` y el resto no prometen tasa |
| «Falso positivo crítico: registro de producto, cantidad/unidad e importe» | **Parcial**: hay pruebas de que el registro se reconoce o se rechaza (`tests/test_registro_oficial_de_productos.py:60,80,86`) y de que la aritmética de la línea es la prueba (`tests/test_facturas.py:329,340,348`), pero **no hay medición de falsos positivos** |
| «Cada ticket termina con suites pertinentes, recorrido de servidor aislado si cambia funcionalidad, capturas si cambia UI y lista de pendientes reales» | **No comprobable desde aquí.** El recorrido aislado (`scripts/humo.py`) y la captura (`comprobar_en_un_navegador.py`) existen y están inspeccionados por pruebas, pero **no se han ejecutado en este encargo** |
| «No recontar archivos como si fueran nuevas capacidades» | Aviso vigente: este documento cuenta **pruebas**, no capacidades. Que una prueba exista no quiere decir que la funcionalidad del contrato exista (A02, A05–A07, A09–A12, A15 no existen aunque la suite esté verde) |
| «Nunca afirmar "sin fallos" ni "cumple toda la PAC" por pasar pruebas» | **Este documento no lo afirma.** 2.891 + 643 pruebas en verde; **9 de las 16 pruebas de aceptación del contrato no existen** y el área PAC no tiene una sola línea de código |

---

## 7. Riesgos de la propia verificación

Ordenados de más grave a menos.

### Riesgo 1 — Pruebas de aislamiento que pasan sin comprobar el aislamiento

El caso concreto: **`tests/test_practicas_culturales.py:437`**
(`test_una_maquina_que_no_es_suya_no_vale`) dice en su nombre y en su comentario que comprueba «una
máquina de otra finca», pero **manda `equipo_id: 99999` (línea 452), un identificador que no existe,
y no crea una segunda cuenta**. Comprueba que un id inventado da 404 — que es otra cosa. **Pasaría
igual aunque `obtener_de_la_explotacion()` no filtrara nada por finca.**

Es la familia de fallo documentada en `AGENTS.md` §4 («una comprobación que no puede saltar nunca» y
«un test que se come el fichero es peor que no tenerlo, porque da la sensación de que revisa»). El
patrón peligroso es fácil de repetir: **404 con un id inventado no prueba aislamiento; hace falta el
id de un dato que existe de verdad en otra finca.**

El resto de pruebas de aislamiento de §4.1 sí usan `crear_cuenta` y un id real, así que estas sí
valen. Pero hay **cinco entidades con `explotacion_id` sin prueba propia de aislamiento**
(`Fertilizante`, `Aplicador`, `EquipoAplicacion`, `RegistroFertilizacion`, `Labor` y `Auditoria`:
ver §4.2), y `Fertilizante`, `Aplicador` y `EquipoAplicacion` son justo las que el contrato señala en
las puertas 3 y 4.

**Otras aserciones débiles del mismo tipo** (pasan aunque la lista esté siempre vacía para todos):
`tests/test_cosecha_comercializada.py:478`, `tests/test_analiticas.py:489`,
`tests/test_plan_abonado.py:221`, `tests/test_cesta_del_almacen.py:321`,
`tests/test_instalaciones.py:54`, `tests/test_firma.py:477`,
`tests/test_varias_cuentas_en_una_finca.py:243`. Son `assert … == []` sobre la finca B: **dentro de
esa prueba no se comprueba que la finca A sí vea el dato**, así que la prueba no distingue «está
aislado» de «no se guardó nada». En la mayoría el dato lo crea una fixture que ya asegura el 201, y
otras pruebas del mismo fichero sí comprueban que A lo ve; pero la aserción de aislamiento, aislada,
es vacía.

### Riesgo 2 — Pruebas que dependen del entorno y por eso no se ejecutan (o se ejecutan distinto)

- **Una prueba omitida, y siempre en esta máquina**:
  `tests/test_facturas.py::TestLeerUnaFacturaEnFoto::test_si_el_lector_solo_tiene_ingles_se_avisa`
  se omite porque Tesseract tiene el español instalado. El caso «el lector solo tiene inglés» —que es
  el que **rompió la lectura del número de factura** (`AGENTS.md` §4: «FACTURA Nº» leído como
  «FACTURA N*»)— **no se está probando hoy aquí**. Un 1 omitido de 2.892 parece nada; este en
  concreto deja sin cubrir un fallo que ya pasó de verdad.
- **El reloj.** `tests/conftest.py:92-94` lo dice sin rodeos: `FECHA_TRATAMIENTO = "2026-05-01"` y
  `FECHA_FIN_ESPERA = "2026-05-22"` caen dentro de la campaña **solo «mientras el año siga siendo
  2026»**, porque la campaña la crea el alta de cuenta con el año en curso. `conftest.py:94` y una
  veintena de pruebas más están ancladas a 2026 (plazos de seguridad, autorizaciones excepcionales,
  vigencias de carné, ITEAF, fechas de tratamiento). **A partir del 01/01/2027 buena parte de la
  suite puede ponerse roja sin que haya cambiado una línea de código**, y entonces la tentación será
  tocar las pruebas, que es lo que `AGENTS.md` prohibe. Hoy (02/10/2026) pasan porque el año sigue
  siendo 2026.
- **Pruebas que exigen tener algo instalado**: las de OCR (`tests/test_facturas.py:228,306,314`)
  dependen de Tesseract y de `data/ocr/tessdata`. Aquí pasan; en una máquina sin Tesseract el
  comportamiento es otro camino, y solo hay una prueba para el caso «no hay lector»
  (`:306,314`), que tampoco se ejerce si el lector está.

### Riesgo 3 — Las copias de los textos de la interfaz dentro de las pruebas de JavaScript

Es el agujero que `AGENTS.md` §4 documenta con nombre y apellidos («Una pregunta que el test pinta en
blanco… el test da por bueno cualquier cosa. Pasó con `plan.herramienta`»), y **sigue habiendo
superficie sin guardián**:

- `tests_js/react.test.js` define **29 bloques de textos escritos a mano** (`TEXTOS`,
  `TEXTOS_DE_REACT`, `TEXTOS_DE_HECHO`, `TEXTOS_DE_MIS_COSAS`, `TEXTOS_DEL_MANDO`…) y
  `tests_js/interfaz.test.js` otros parecidos. Las pantallas de React reciben los textos por
  propiedades del servidor: si un texto llega vacío, el componente pinta un hueco y **la prueba de
  JavaScript pasa**, porque el hueco y el texto esperado los pone el propio fichero de pruebas.
- **Solo diez de esas copias se comparan contra lo que sirve el servidor**, todas en
  `tests/test_interfaz.py:769,817,835,852,870,893,943,965,992,1019` (inicio, grupos, ventas, medidas,
  mis datos, fincas, qué hay sembrado, almacén, papeles y confirmación), más las preguntas del
  asistente (`:1328,1359`).
- **Las demás no**: SIGPAC, cuaderno de la Junta, cultivo, mapa, análisis, dictado, borrador,
  formulario, firma, plan de abono, entrar, facturas, interpretación, campañas, mi cuaderno, el
  marco y el panel de mando. En esas, **la prueba y la aplicación pueden decir cosas distintas sin
  que nada avise**.
- **Cómo se arregla:** extender a todas las pantallas el guardián que ya existe para diez
  (`test_la_copia_lleva_los_textos_de_*`), sacando las claves del propio `app.js` en vez de
  escribirlas a mano.

### Riesgo 4 — Pruebas apoyadas en datos concretos y no en la finca real

- Toda la suite corre contra **una finca de prueba**: alias «El Prado», `ref_sigpac` «37-455-12-3»,
  2,43 ha, sistema secano, Peñaranda de Bracamonte (`tests/conftest.py:188-205`), y una cuenta con el
  **nombre y el NIF reales del titular** (`conftest.py:81-86`, `70922320A`). Es un dato personal
  dentro del repositorio, aunque sea el del dueño del proyecto: conviene saberlo.
- Hay pruebas ancladas a **una parcela real concreta**, copiada de una captura del visor:
  `tests/test_parcelas_por_codigos.py:40-50` (provincia 37, municipio 070, parcela 503, recinto 51) y
  `tests/test_mapa_del_sigpac.py` (el WKT del recinto de ejemplo y la referencia catastral). Si esa
  parcela cambia en el SIGPAC, la suite se pone roja por un dato de fuera, no por un fallo del
  programa. Está declarado como decisión (el parser se escribe contra una respuesta de verdad), que
  es lo correcto — pero es una dependencia externa que hay que tener presente.
- Pruebas que **leen ficheros del proyecto** y por eso se rompen cuando cambia la documentación, no
  el programa: `tests/test_lo_obliga_la_ley.py:213,222,228` (README, traspaso y correo),
  `tests/test_cuaderno_cyl_exportar.py:588` («lo que dice la documentación y lo que hace el programa
  tienen que ser el mismo número»), `tests/test_lista_de_la_junta.py` y
  `tests/test_la_migracion_a_react.py`. Son guardianes útiles, pero **un documento editado puede
  poner la suite en rojo sin que nada del programa esté mal**, y entonces hay que decidir con cuidado
  cuál de los dos está equivocado.
- Pruebas cuyo resultado **depende de la fecha del sistema**: además del reloj de la campaña
  (riesgo 2), `tests/test_autorizacion_del_producto.py:208-270` y las de vencimientos falsean
  `legal.hoy` con `monkeypatch`, que es la forma buena de hacerlo; pero `conftest.py` usa fechas
  literales de 2026, que es la forma mala.

### Riesgo 5 — Pruebas que interpretan otros ficheros (los guardianes)

`AGENTS.md` §4 avisa: «si un test lee ficheros y los interpreta, ese test necesita su propia
prueba». Están guardados los tres casos conocidos (`tests/test_interfaz.py:651-699,1046-1079` para
`quita_comentarios_js` y el extractor de plantillas, y `tests/test_los_botones_hacen_algo.py:174`,
`tests/test_que_no_falte_ningun_texto.py:81` con su «si el extractor se rompiera, esta prueba pasaría
sin comprobar nada»). Pero el riesgo estructural sigue: hay al menos **seis** ficheros de pruebas que
leen y parsean `app.js`, `estilos.css`, `DESIGN.md`, el README y los documentos de `docs/`, y cada
uno de ellos puede quedarse mirando a otro sitio. El caso de `tests/test_ficheros_de_texto.py` (723
casos) es el más benigno (mira bytes).

### Riesgo 6 — Higiene: la suite deja basura en el temporal

`tests/conftest.py:51-78` borra su carpeta temporal al terminar, con dos intentos a propósito porque
en Windows los ficheros siguen abiertos un instante. **En esta ejecución funcionó** (no ha quedado
ninguna carpeta nueva), pero en `%TEMP%` hay **6 carpetas `cuedigital_tests_*` de ejecuciones
anteriores** (26–30/09/2026), una de ellas con un `tests.db` de 397 KB. No es un fallo de seguridad
ni afecta a nadie: es la basura que el proyecto deja en el ordenador de quien lo ejecuta, que es el
mismo problema que ya se encontró el 23/09/2026 con 559 carpetas.

### Lo que NO es un riesgo: ninguna prueba toca la base real

Comprobado y merece decirse con la prueba delante, porque sería el fallo más grave de todos:

- **Ninguna prueba menciona `cuedigital.db`** (búsqueda literal en `backend/tests/` y
  `backend/tests_js/`: 0 coincidencias).
- Las únicas pruebas que crean su propio motor lo hacen contra `tmp_path`:
  `tests/test_plan_abonado.py:441` y `:497` (`vieja.db`, `nueva.db`) y
  `tests/test_cambiar_la_clave.py:32` y `:147` (que además lanza un subproceso con su propia
  `CUEDIGITAL_DATABASE_URL`).
- `conftest.py` fija `CUEDIGITAL_DATABASE_URL` y `CUEDIGITAL_ADJUNTOS` **antes de importar `app`**
  (`:3-13,24,30`), y hay una prueba que comprueba que la carpeta de adjuntos de los tests **no** está
  dentro del proyecto (`tests/test_analiticas.py:454-466`).
- Evidencia de disco: `backend\cuedigital.db` conserva la fecha **30/09/2026 18:05:33** (anterior a
  la ejecución) y `backend\datos\adjuntos` **no existe**.
- Lo mismo en JavaScript: las coincidencias de `cuedigital` en `tests_js/` son claves de
  `localStorage` (`cuedigital.token`, `cuedigital.pendientes`…), no la base.

---

## 8. Lo que no se ha podido comprobar en este encargo

1. **`scripts/humo.py` y `scripts/comprobar_en_un_navegador.py` no se han ejecutado** (a petición
   expresa: necesitan puertos y bases que estaba usando el titular). Por tanto **no está comprobado**
   el recorrido completo contra un servidor de verdad, ni que la pantalla la dibuje React en un
   navegador real. Sí se han ejecutado las pruebas de pytest que **inspeccionan** esos dos guiones sin
   lanzarlos (`test_comprobar_en_un_navegador.py`, 10 casos; `test_firmar_con_el_certificado.py`, 15;
   `test_probar_iuws_con_certificado.py`, 7).
2. **Nada contra el interfaz de la Junta (IUWS) de verdad.** Todas las pruebas del cliente usan
   `httpx.MockTransport` con respuestas guardadas; no hay ni una llamada de red en la suite
   (comprobado: todo el tráfico de `tests/` está sustituido). Que el IUWS siga contestando como dice
   el anexo **solo** lo comprueba `scripts/humo.py`, que no se ha ejecutado.
3. **Nada contra el SIGPAC de verdad.** El parser se prueba contra respuestas guardadas en `data/`
   (`tests/test_sigpac.py:95`), que es lo correcto, pero si el servicio ha cambiado no se ha visto.
4. **Nada con un certificado digital de verdad.** `test_firma_cades.py` usa ficheros firmados con
   OpenSSL, que es lo correcto; la firma con el almacén de Windows (`test_firmar_con_el_certificado.py`)
   se inspecciona, no se ejecuta, y el almacén de certificados de este PC no se ha abierto.
5. **Nada con OCR propio**: no se ha comprobado si Tesseract está instalado, qué versión, ni qué
   idiomas tiene, más allá de lo que dice la prueba omitida.
6. **Nada de lo que exige mirar la pantalla**: no hay capturas, ni comprobación visual, ni teclado,
   ni zoom al 200 %, ni móvil. Lo único que hay es lo que las pruebas de JavaScript comprueban sobre
   un DOM de mentira o con `renderToStaticMarkup`.
7. **No se ha medido el tiempo de la suite por separado del resto** ni se ha comparado con los 30
   segundos que `AGENTS.md` §2 dice que debería durar: hoy tarda **204 s** de pytest (3 min 24 s) más
   **59 s** de node. La nota de `AGENTS.md` dice «son 30 segundos»: conviene comprobar si el número
   del documento se quedó viejo o si algo se ha vuelto lento, pero eso exige medir por etapas y no se
   ha hecho.
8. **No se ha comprobado el aislamiento de las seis entidades de §4.2** ejecutando una petición real
   contra ellas: se ha hecho un inventario de qué pruebas existen, que es lo que pedía el encargo.
9. **No se ha auditado la explotación real.** Todo esto son pruebas contra una finca de prueba. Si la
   pregunta es «¿están bien los datos del agricultor?», este documento no la contesta.

---

## 9. Resumen en seis líneas

- **pytest: 2.892 casos, 2.891 pasan, 0 fallan, 1 omitida** (01/10/2026, 204 s, leído del
  `--junit-xml`). **node --test: 643 casos, 643 pasan, 0 fallan, 0 omitidas** (59 s).
- La suite no toca la base real: `backend\cuedigital.db` no se ha abierto y no existe
  `backend\datos\adjuntos`.
- De las 16 pruebas de aceptación del contrato, **solo A13 existe entera**; **A01, A03, A04, A08,
  A14 y A16 están a medias**; **A02, A05, A06, A07, A09, A10, A11, A12 y A15 no existen**.
- De las cuatro puertas de la sección 9, **tres son verdad** (VentaDeCosecha no acredita ingresos,
  `foto_etiqueta` no acredita cámara, `EquipoAplicacion` no cubre la maquinaria) y **una es falsa
  hoy**: la factura **sí** acredita recepción y es la única puerta a la existencia.
- El aislamiento entre fincas está cubierto con 68 pruebas de verdad, pero **seis entidades con
  `explotacion_id` no tienen prueba propia** y una de ellas (`EquipoAplicacion`) tiene una prueba que
  **parece** comprobarlo y no lo comprueba (`test_practicas_culturales.py:437`).
- Los tres riesgos de verificación más graves: **la prueba de aislamiento que pasa sin comprobar
  aislamiento**, **la suite anclada al año 2026 (se romperá sola en 2027) y la prueba de OCR omitida
  hoy**, y **las 19 copias de textos de las pruebas de React que no se comparan con lo que sirve el
  servidor**.
