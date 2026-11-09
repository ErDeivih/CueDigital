# Verificación del SIGPAC pintado y del cuaderno guiado — 09/11/2026

> **Qué es este documento, y qué no es.** No es el relevo: es una comprobación hecha **contra el
> código y contra las pruebas ejecutadas**, para separar lo que está cerrado de verdad de lo que
> solo está escrito. **Una cosa se da por buena aquí solo si se ha ejecutado**; cuando lo único
> que hay es código o un test que lee la fuente, se dice así, con esas palabras.
>
> **Dónde se ha mirado:** rama `integracion/cloud-estabilizacion-2026-10-21`, HEAD `ed5157b`, más
> los cambios de otros compañeros que estaban sin confirmar en el árbol de trabajo (observabilidad y
> despliegue). Es decir: lo comprobado es **este árbol**, no una versión publicada.
>
> **Lo que NO se ha hecho aquí, y por qué:** no se ha ejecutado la suite completa ni el recorrido
> con Chrome (los está corriendo otro compañero y tardan); no se ha tocado código de la
> aplicación, ni `.env`, ni `backend/tests/fixtures/firma_cades/`, ni `ESTADO-AGENTE.md`; no hay
> commit ni push. **No se ha descargado ningún mapa del SIGPAC**: el GeoPackage que se usa ya estaba
> en la caché. La única petición a internet es la ortofoto del IGN, que la pide el propio endpoint
> de la imagen y es su funcionamiento normal.

---

## 1. El resultado, en una línea por cosa

| Lo que el relevo da por cerrado | Comprobado con | Resultado real |
|---|---|---|
| `POST /api/sigpac/cache/{provincia}/contornos` **aplica** los contornos del GeoPackage | 39 pruebas del geopackage + 27 de la caché + **petición en vivo** | **Sí.** En vivo: `200`, 2 tierras con su WKT escrito en la base |
| `GET /api/mapa/tierra/{id}.png` devuelve la **ortofoto con el contorno dibujado** | 23 pruebas del PNG (miran los píxeles) + **petición en vivo** | **Sí.** En vivo: `200`, `image/png`, 538.951 bytes, 800×600, visto a ojo |
| Esa imagen dice **«no tiene forma»** cuando la tierra no la tiene | 3 pruebas + **petición en vivo** | **Sí**, con matiz de palabras (ver §5) |
| Una tierra dada de alta **solo con `37-70-0-0-503-51`** recibe su contorno si hay **un** recinto | 7 pruebas del alta por referencia + 5 del geopackage + **en vivo** | **Sí.** En vivo: la tierra se actualizó con 18 puntos (WKT de 406 caracteres) |
| Si hay **varios** recintos **pide elegir** (`sin_codigos` con su motivo) | 3 pruebas + **en vivo** | **Sí en el servidor**; **la pantalla no lo cuenta** (ver §6.1) |
| La **ficha** y la **ventana del SIGPAC** lo enseñan | Código + 12 pruebas del anillo/centro + pruebas que leen la fuente | **En el código sí; no ejecutado en Chrome por mí** |
| El **cuaderno guiado** distingue lo que bloquea de lo que puede rellenar y **cuenta los rellenables** | 2 pruebas de servidor + 3 de JS + 33 que leen la fuente + **en vivo con la función real** | **Sí.** En vivo: 34 faltan, 8 bloquean, **17 rellenables** («Puedes rellenar 17 de ellas aquí.») |

**Cifras de las pruebas ejecutadas:** **266 pruebas de Python superadas, 0 fallos** (11 ficheros,
44,93 s) y **88 pruebas de JavaScript superadas, 0 fallos** (1,28 s).

---

## 2. Las pruebas que se han ejecutado, con su cuenta

### 2.1 Python

```powershell
cd F:\Proyectos\CueDigital\backend
$env:PYTHONIOENCODING="utf-8"
..\.venv\Scripts\python.exe -m pytest `
  tests\test_geopackage_sigpac.py tests\test_contorno_de_una_tierra.py `
  tests\test_codigos_desde_la_referencia.py tests\test_sigpac_cache.py `
  tests\test_sigpac.py tests\test_mapa_del_sigpac.py tests\test_mapa_de_una_tierra.py `
  tests\test_darle_la_forma_a_una_tierra.py tests\test_nuevo_api.py `
  tests\test_nuevo_importar.py tests\test_interfaz_nuevo.py
```

Resultado real: **`266 passed, 2 warnings in 44.93s`**. Las dos advertencias son de las librerías
(`starlette.testclient` y un alias de `anyio`), no del proyecto.

| Fichero | Pruebas | Qué cubre de verdad |
|---|---:|---|
| `tests\test_geopackage_sigpac.py` | 39 | Abrir el GeoPackage, leer recintos, la referencia que rellena los códigos, el de un recinto / varios, y las respuestas de la puerta (401, 403, 404, 409, 422, aislamiento entre fincas) |
| `tests\test_contorno_de_una_tierra.py` | 14 | `POST /api/parcelas/{id}/contorno` con un SIGPAC simulado (varios trozos sin decir cuál → 422) |
| `tests\test_codigos_desde_la_referencia.py` | 7 | El alta solo con la referencia (papel, visor y catastral), sin pisar lo informado y sin bloquear si no se entiende |
| `tests\test_sigpac_cache.py` | 27 | La descarga de la provincia, la ficha, el fichero cortado y la descarga por trozos |
| `tests\test_sigpac.py` | 49 | El conector del SIGPAC contra respuestas guardadas y los 933 productos |
| `tests\test_mapa_del_sigpac.py` | 47 | Las consultas del visor (recintos de una parcela, de un punto, referencia catastral) |
| `tests\test_mapa_de_una_tierra.py` | 23 | **El PNG de la tierra: mira los píxeles** (blancos del contorno, relleno dentro y fuera) y el 409 sin forma |
| `tests\test_darle_la_forma_a_una_tierra.py` | 3 | Dar forma a una tierra sin forma y que sin forma no se apunte nada |
| `tests\test_nuevo_api.py` | 12 | El anillo y el centro de la tierra que pinta la ficha (`anillo`/`centro`, o `None`) |
| `tests\test_nuevo_importar.py` | 12 | `GET /api/nuevo/que-falta`: trae `que`, `donde` y `bloquea`, y coincide con el resumen |
| `tests\test_interfaz_nuevo.py` | 33 | **Lee la fuente**: que el cuaderno use `faltasRellenables`, que la ventana tenga sus enganches, que el aviso de bloqueo exista |

> **Honestidad sobre lo que eso prueba:** los 33 tests de `test_interfaz_nuevo.py` **no arrancan la
> pantalla**; leen `backend/web/nuevo/app.js` y `modelo.js` y buscan que existan las funciones y los
> enganches. Lo que se ejecuta de verdad del cuaderno es lo de `tests_js` y lo que se midió en vivo
> (§4). Y todos los tests del GeoPackage usan un **fichero
> sintético** que se fabrica en el propio test (`_un_gpkg`): **el fichero real no lo usa ningún
> test automático** (ver §6.4).

### 2.2 JavaScript

```powershell
cd F:\Proyectos\CueDigital\backend
node --test "tests_js\nuevo.test.js"
```

Resultado real: `tests 88`, `pass 88`, `fail 0`, `duration_ms 1284`. Los tres que cubren esto:

- `el cuaderno cuenta las faltas que se pueden rellenar aquí, con la misma función de destinos`
- `el filtro deja fuera solo las secciones tecnicas y no inventa el total`
- `cada tierra pintada se abre solo si el padre deja abrirla`

---

## 3. Comprobación en el código, con la línea exacta

### (a) `POST /api/sigpac/cache/{provincia}/contornos` aplica las formas

- Ruta: `backend/app/routers/parcelas.py:1256`. Exige permiso de modificar **antes** de abrir nada
  (`PuedeModificar`, docstring en `1264-1283`).
- Busca las tierras **de su finca**: `parcelas.py:1326-1332` (`explotacion_id == explotacion.id`).
- Abre el GeoPackage y calcula: `parcelas.py:1334` →
  `geopackage_sigpac.contornos_de_las_parcelas` (`app/geopackage_sigpac.py:823`).
- **Escribe la geometría**: `parcelas.py:1346-1348` (`parcela.geometria = actualizada["wkt"]`). El
  dibujo **no se guarda**: se calcula del WKT (`Parcela.dibujo`, `models.py:305`), y por eso
  rellenar la geometría lo rellena solo.
- El rastro de auditoría, solo si algo cambió de verdad: `parcelas.py:1349-1362`.

### (b) `GET /api/mapa/tierra/{id}.png` pinta ortofoto + contorno, y dice cuándo no hay forma

- Ruta: `backend/app/routers/mapa.py:315`. La composición: `mapa.py:353` →
  `app/mapa_de_una_tierra.py:248` (`imagen_de_la_tierra`), que dibuja el contorno sobre la
  ortofoto en `mapa_de_una_tierra.py:197-235`.
- Tamaño por defecto **800×600**: `mapa_de_una_tierra.py:47-48`.
- Sin forma: `mapa.py:356-364` contesta **409** con el texto «Esta tierra no tiene su forma
  guardada, así que no se puede dibujar su contorno…», y **no pide la ortofoto**.
- Devuelve `image/png` con caché privada: `mapa.py:374-377`.
- La ficha pinta esa imagen: `backend/web/nuevo/app.js:3098-3102`
  (`<img data-mapa-imagen src=RUTA_MAPA_TIERRA(...)>`); la definición de la ruta está en
  `app.js:155` y `modelo.js:1602`. Si la imagen falla (sin cobertura), cae al mapa dibujado por
  el propio programa (`onError` → `mapaDelCliente`).
- La ficha **dice** que no hay forma sin pedir la imagen: `app.js:3096` con el texto
  `textos.tierra.sinMapa` («Esta tierra no tiene forma en el SIGPAC: se enseñan sus datos, pero no
  se dibuja.») en `modelo.js:463`.

### (c) La referencia de seis números: un recinto se coge; varios, se pide elegir

- Al **guardar**, los códigos salen de la referencia si faltan:
  `backend/app/routers/parcelas.py:777` (`_completar_los_codigos_con_la_referencia`), llamada en
  `parcelas.py:857`. Solo rellena lo que falta y **no bloquea** si la referencia no se entiende
  (`parcelas.py:799-822`).
- Al **leer el mapa**, los códigos se sacan también de la referencia de las tierras ya guardadas:
  `app/geopackage_sigpac.py:758` (`codigos_de_una_parcela`), `787`
  (`_los_numeros_de_la_parcela`).
- El caso de seis números: `geopackage_sigpac.py:860-885`. Si `numero_recinto is None` se buscan los
  trozos de la parcela: **uno** → se coge (`885`); **varios** → a `sin_codigos` con el motivo
  «la referencia no dice el recinto y esa parcela tiene N recintos; elige uno» (`871-881`);
  **ninguno** → a `no_encontradas` (`882-884`).

### (d) La ficha y la ventana del SIGPAC

- La ficha de la tierra pinta el PNG (§3b) y la ventana del SIGPAC tiene el bloque de contornos:
  `app.js:4122-4141` (resultado en palabras + lista de tierras actualizadas con
  `data-sigpac-cache-actualizada`), y la petición en `app.js:3712-3738`.
- Los enganches de la ventana (provincia, aplicar, resultado, atribución) están comprobados por
  `tests/test_interfaz_nuevo.py:502` (`test_la_ventana_tiene_los_contornos_de_toda_la_finca`).
- Las palabras del resultado salen de `modelo.js:2341` (`lineasDeLosContornos`) y las tierras de
  `modelo.js:1968` (`actualizadasDeLosContornos`).

### (e) El cuaderno guiado

- `GET /api/nuevo/que-falta`: `backend/app/routers/nuevo_api.py:93` → `app/nuevo.py:673`
  (`que_falta`).
- **De dónde sale cada cosa y por qué una bloquea y otra no**: `app/nuevo.py:633` (`_las_faltas`).
  Lo que falta del cuaderno (informe del escritor del Cuecyl) va con `bloquea: False`
  (`nuevo.py:654-657`); lo que falta para presentarlo en la Junta (`iuws.QUE_FALTA`) va con su
  `bloquea` de verdad (`nuevo.py:658-661`). La lista oficial de bloqueos es `app/iuws.py:577`
  (8 cosas, **todas** `bloquea=True`, y cada una dice de quién depende: FEGA, David o cada
  agricultor).
- **Cuenta los rellenables** con la misma función de destinos: `backend/web/nuevo/modelo.js:1858`
  (`destinoDeLaSeccion`) la usan `faltasRellenables` (`1876`), `seccionesRellenables` (`1891`) y
  `tecnicasDeLoQueFalta` (`1896`); la pantalla la llama en `app.js:2743`
  (`const rellenables = faltasRellenables(items)`) y la pinta en `app.js:2776`
  (`data-cuaderno-rellenables`).

---

## 4. Prueba en vivo con el GeoPackage **real** de Salamanca

### 4.1 El fichero que hay en la caché (no se ha descargado nada)

Carpeta por defecto de `app/sigpac_cache.py:133-142` (`datos/sigpac_cache`, sin
`CUEDIGITAL_SIGPAC_CACHE` puesta):

| Fichero | Bytes | Tamaño |
|---|---:|---:|
| `37_SALAMANCA_rec_2026_20251215_gpkg.zip` | 628.836.142 | 599,7 MB |
| `37_SALAMANCA_rec_2026_20251215_gpkg__0837_SALAMANCA_rec_2026_20251215.gpkg` | 1.122.332.672 | 1.070,3 MB |
| **Total de una provincia** | **1.751.168.814** | **1,67 GB** |

La ficha `37_2026.json` dice: campaña **2026**, validez **2025-12-15**, `sha256`
`8b9aa742b6c97771bd4d65ad54f36ae1eb71fa1b7567a5de41929b0e20c8f99f`, licencia CC BY 4.0 (FEGA).

Sonda de solo lectura sobre el fichero real (`app.geopackage_sigpac.abrir_recintos`):

- tabla `recinto`, `srs = 4258`, abierto **cacheado** (usa el `.gpkg` de al lado, no descomprime);
- `37-70-0-0-503-51` → **1 recinto** (recinto 1, **4,9016 ha**, 18 puntos, uso `TA`), WKT de 406
  caracteres. Es el caso del papel `37-70-0-0-503-51-1` y el del visor de seis números;
- parcela real con **2 recintos** para probar el caso de «elige uno»: `37-2-0-0-502-1`
  (recinto 1: 1,3271 ha; recinto 2: 0,0769 ha).

### 4.2 Cómo se probó en vivo

Un `uvicorn` temporal, en un **puerto libre elegido al azar**, con **base SQLite temporal** fuera
del proyecto (`CUEDIGITAL_DATABASE_URL` a `%TEMP%`) y la caché real (`CUEDIGITAL_SIGPAC_CACHE` a
`datos/sigpac_cache`). Una cuenta de pruebas creada por `POST /api/cuenta/registro`, y el servidor
apagado al final. **No se ha tocado la base de datos del proyecto.**

### 4.3 Resultado (peticiones reales, 09/11/2026)

```
GET  /api/sigpac/cache                       -> 200  cuantas=1  campañas=2026
                                                 fichero=37_SALAMANCA_rec_2026_20251215_gpkg.zip
POST /api/parcelas (solo ref del visor 37-70-0-0-503-51)  -> 201  codigo_ine=37070 pol=503 par=51 rec=null
POST /api/parcelas (ref del papel    37-70-0-0-503-51-1)  -> 201  rec=1
POST /api/parcelas (ref de 2 recintos 37-2-0-0-502-1)     -> 201  rec=null
POST /api/parcelas (a mano, sin forma)                    -> 201
POST /api/sigpac/cache/37/contornos          -> 200  en 498 ms (servidor recién arrancado)
                                                 n=4 · actualizadas=2 · sin_forma=0
                                                 no_encontradas=0 · sin_codigos=2
  ACTUALIZADA id=1 "La del visor"  18 puntos  uso=TA  WKT 406 caracteres
  ACTUALIZADA id=2 "La del papel"  18 puntos  uso=TA  WKT 406 caracteres (el mismo recinto y la
                                                 misma forma que la del visor)
  SIN_CODIGOS id=3 "La de dos trozos" motivo="la referencia no dice el recinto y esa
                                       parcela tiene 2 recintos; elige uno"
  SIN_CODIGOS id=4 "A mano"           motivo="su municipio no está en el catálogo oficial"
```

Y en una **segunda pasada** (su propio servidor y su propia base temporal, para pedir la imagen con
la cabecera de sesión bien puesta y leer el 409 con su cuerpo):

```
POST /api/sigpac/cache/37/contornos          -> 200  actualizadas=1 (id 1, "La del visor")
GET  /api/mapa/tierra/1.png                 -> 200  image/png  538.951 bytes  800x600
                                                 firma PNG válida (89 50 4E 47 0D 0A 1A 0A)
                                                 VISTA A OJO: ortofoto de una parcela de cultivo
                                                 con relleno amarillo suave, línea blanca con borde
                                                 oscuro y margen alrededor
GET  /api/mapa/tierra/2.png                 -> 409  {"detail":"Esta tierra no tiene su forma
                                                 guardada, así que no se puede dibujar su
                                                 contorno. La forma se le pone en su ficha, con
                                                 el mapa, y entonces ya se puede sacar la imagen."}
```

(Los identificadores no son los mismos entre las dos pasadas porque cada una empieza con su base
vacía: en la primera la tierra sin forma es la 4 y en la segunda la 2; en las dos es la misma tierra
apuntada a mano, sin geometría.)

**Los 498 ms son la petición completa** con el servidor recién arrancado (arranque, sesión, consulta
y escritura); no he vuelto a medir la función suelta, así que no repito aquí la cifra de 18 ms que
trae el relevo.

### 4.4 El cuaderno guiado, en vivo

En la misma finca de pruebas (recién creada, **sin tierras**):

```
GET /api/nuevo/que-falta  -> 200  faltan=34  items=34
GET /api/nuevo/resumen    -> 200  cuaderno.faltan=34   (el mismo número, no dos cuentas)
```

Y los 34 ítems reales pasados por **la función de verdad de la pantalla** (`node` importando
`backend/web/nuevo/modelo.js`, sin copiar la lógica):

```
resumenDeLoQueFalta      faltan=34  bloquean=8
faltasRellenables        17   -> "Puedes rellenar 17 de ellas aquí."
tecnicasDeLoQueFalta     17   -> "17 quedan fuera: dependen de la aplicación o de la Junta."
secciones                31   (17 con pantalla en /nuevo/)
empezarPorLoPrimero      "las máquinas con las que echas el producto…" -> destino "productos"
las 8 que bloquean       todas con destino null (FEGA, David, quien desarrolla, cada agricultor)
```

En la otra pasada (finca con 4 tierras dadas de alta) el mismo endpoint devolvió **37 ítems, 8
bloquean**, y contados con la misma regla de destinos salían **18 rellenables**. La diferencia es
solo que allí había más tierras que rellenar.

### 4.5 Nada queda encendido

Al terminar cada pasada: `PROCESO_VIVO=False` y el puerto comprobado con `connect_ex` (distinto de
0 = nadie escucha). El uvicorn temporal y su base de datos estaban en `%TEMP%`, fuera del
repositorio. No se ha dejado ningún Chrome ni ningún servidor de CueDigital escuchando.

---

## 5. Qué está cerrado de verdad (y con qué palabra)

1. **Los contornos del GeoPackage se aplican.** Cerrado: código, 66 pruebas entre geopackage y
   caché, y una petición real con el mapa de Salamanca que deja 2 tierras con su WKT.
2. **La imagen de la tierra es la ortofoto con el contorno dibujado.** Cerrado: las pruebas miran
   los píxeles (blancos del contorno, relleno dentro y no fuera) y en vivo salió un PNG de 538.951
   bytes que he mirado: se ve el campo y el linde pintado.
3. **Sin forma se dice y no se inventa un cuadro.** Cerrado: 409 con su explicación, y **no se pide
   la ortofoto** (hay prueba de que no se llama al servicio). Matiz de palabras: la respuesta HTTP
   dice «no tiene **su forma guardada**», no literalmente «no tiene forma»; la ficha dice «Esta
   tierra no tiene forma en el SIGPAC: se enseñan sus datos, pero no se dibuja.».
4. **Una tierra dada de alta solo con la referencia del visor recibe su contorno si la parcela
   tiene un solo recinto.** Cerrado: probado en vivo con `37-70-0-0-503-51` (1 recinto) → 200,
   actualizada, 18 puntos.
5. **Si tiene varios recintos, el servidor no adivina y pide elegir.** Cerrado **en el servidor**:
   probado en vivo con `37-2-0-0-502-1` (2 recintos) → `sin_codigos` con el motivo exacto
   «…tiene 2 recintos; elige uno». **La pantalla no lo dice** (ver §6.1).
6. **El cuaderno guiado distingue lo que bloquea de lo que el agricultor puede rellenar y cuenta
   los rellenables.** Cerrado en el servidor y en el modelo: 8 bloqueos técnicos (los de
   `iuws.QUE_FALTA`, todos con su responsable), 17 rellenables contadas por la función real con su
   texto en singular y plural, y el resumen diciendo el mismo número que la lista.

---

## 6. Qué no está cerrado, y lo que he encontrado al comprobarlo

### 6.1 La pantalla no cuenta **por qué** una tierra queda sin códigos (y debería)

El servidor devuelve, por cada tierra que no casa, su `motivo` (por ejemplo «la referencia no dice
el recinto y esa parcela tiene 2 recintos; elige uno»). Pero la ventana solo pinta:

- los **recuentos** por categoría (`lineasDeLosContornos`, `modelo.js:2341-2356`), que dicen
  «1 tierra sin códigos del SIGPAC», y
- la **lista de las que sí se han actualizado** (`actualizadasDeLosContornos`, `modelo.js:1968`),
  pintada en `app.js:4127-4141`.

El motivo y la lista de `sin_codigos` **no se pintan en ningún sitio** (`app.js:3727-3730` guarda
solo `lineas` y `actualizadas`). Consecuencia: en el caso de la referencia de seis números con dos
recintos, **el agricultor lee «1 tierra sin códigos del SIGPAC» y no «elige uno»**, ni tiene un
botón que abra la ventana del SIGPAC en esa tierra. La información existe en la respuesta HTTP y se
tira al pintar. Lo que el relevo dice («se dice… elige uno») es verdad **del servidor**, no de la
pantalla.

> **No lo he arreglado**: es código de aplicación y la regla de esta tarea era avisar antes de
> tocarlo. Va al Lead como hallazgo (con la línea exacta) para que decida.
>
> **Actualización, mismo 09/11: cerrado** en la tarea `task-5`. `modelo.js` gana
> `sinCodigosDeLosContornos` y `lineasDeLosContornos` agrupa por motivo sin perderlo; la ventana
> pinta una fila por tierra con su motivo y un botón «Elegir el recinto en el SIGPAC» que abre
> **esta misma** ventana rellena con esa tierra (el camino de la ficha); los textos están en
> `textos.py` (`CONTORNOS_DEL_SIGPAC`) y en `textos_visibles()`, con guardián de copia. Queda
> **pendiente de ver en Chrome**: lo probado son las pruebas de JS y las que leen la fuente.

### 6.2 La caché: 1,67 GB por provincia y **ninguna política de limpieza**

- No hay código que borre un mapa ya usado: `sigpac_cache.py` solo borra el fichero temporal de la
  descarga (`502`, y ya se movió a su sitio con `os.replace` en el caso bueno) y
  `geopackage_sigpac.py` solo borra la carpeta temporal de extracción (`393`, `416`). El ZIP y el
  `.gpkg` se quedan para siempre.
- **No basta con «borrar el ZIP»**: la ficha del mapa y la apertura lo exigen. `ficha_guardada()`
  da el mapa por no descargado si no está el ZIP (`sigpac_cache.py:549`), la ruta de los contornos
  comprueba que el fichero de la ficha existe (`parcelas.py:1316-1324`), y `abrir_recintos` necesita
  el ZIP para saber qué `.gpkg` le corresponde y cuánto debe medir (`geopackage_sigpac.py:447-472`,
  `_el_guardado_sirve` en `356-375`). Es decir: **la política de limpieza es una decisión y un
  cambio de código con su prueba**, no un `rm`.
- Lo que hay que decidir: (a) ¿se borra el ZIP en cuanto el `.gpkg` está extraído y validado
  (ahorra 599,7 MB de los 1.670 por provincia), aceptando que la ficha cambie a «preparado» sin
  ZIP? (b) ¿se borra todo pasado un tiempo y se vuelve a bajar? (c) ¿cuota y aviso? Hoy: ninguna de
  las tres.

### 6.3 La PAC de años anteriores: no está, y es lo que dice el relevo

`sigpac_cache`/geopackage resuelven **la forma** de las tierras, no la PAC. Las puertas que hay son
`app/routers/pac_api.py`: `/api/pac/paquete` (se calcula), `/api/pac/escenario` (hipótesis que no
se guarda) y `/api/pac/foto…` (fotos de la PAC y su exportación). **No hay importador de la PAC ni
de los registros de años anteriores de la Junta.** `WALL.md` (bloque «Cargar la PAC/registros de
años anteriores», líneas 51-58) lo deja abierto y explica por qué: el canal de recintos por campaña
está verificado 2023–2026, pero no hay fichero oficial de la solicitud PAC, así que la PAC se modela
y no se presenta desde aquí. Coincide con `ESTADO-AGENTE.md` («PAC de años anteriores» en lo que
sigue abierto).

### 6.4 Lo que la suite automática **no** protege: el fichero real

Todos los tests del GeoPackage construyen un `.gpkg` sintético en el propio test (`_un_gpkg`). El
fichero real de Salamanca **solo se ha probado a mano** (el 07/11 por el relevo y hoy por esta
verificación). Es una prueba de verdad, pero **no es automática**: si el FEGA cambia el esquema, la
campaña o el nombre de la columna, la suite seguirá en verde y el fallo se verá al usarlo. Esta
verificación no lo arregla; lo deja escrito.

### 6.5 Dos textos que no coinciden con lo comprobado (no se han tocado)

- **`ESTADO-AGENTE.md` está desfasado** en un punto: en «Lo que sigue abierto» (líneas 82-83) dice
  «Referencia del visor (6 números) sin recinto: … hoy se declara `sin_codigos` con su motivo», pero
  eso ya está implementado y probado (y en vivo) desde el 08/11, como dice `WALL.md`. La regla de
  esta tarea prohíbe tocar `ESTADO-AGENTE.md`: queda para el Lead.
- **Detalle menor de un texto**: una tierra **sin ningún dato** del SIGPAC (ni referencia ni
  códigos) sale en `sin_codigos` con el motivo «su municipio no está en el catálogo oficial»
  (`geopackage_sigpac.py:850-857`), que describe mal el caso: no es que el municipio no esté en el
  catálogo, es que la tierra no tiene ni referencia. No es un fallo de datos (no se adivina nada),
  es una frase que puede despistar. No lo he cambiado.

### 6.6 Lo que no he ejecutado: Chrome

No he abierto Chrome: el recorrido lo está corriendo otro compañero. Los guiones que lo cubren
existen y no los he tocado: `backend/scripts/comprobar_el_armazon_nuevo.py` comprueba el cuaderno
(`data-cuaderno-rellenables`, líneas 1032-1038), el bloque de contornos de la ventana
(`data-sigpac-cache*`, líneas 841-881) y los cuatro contornos reales del cliente
(`comprobar_los_cuatro_contornos_del_cliente`, desde la línea 1637). **Queda pendiente de ejecutar en
este HEAD**: lo que aquí se da por bueno de la ficha y de la ventana es código más tests que leen la
fuente, no una pantalla vista funcionar.

---

## 7. La lista corta para cerrar del todo

1. ~~**Llevar el motivo de `sin_codigos` a la pantalla** y, cuando el motivo sea «varios
   recintos», un botón que abra la ventana del SIGPAC en **esa** tierra para elegir el recinto.~~
   **Hecho el mismo 09/11 en `task-5`** (§6.1): probado con las pruebas de JS y las que leen la
   fuente; **falta verlo en Chrome**.
2. **Decidir y escribir la política de limpieza de la caché** (ZIP tras extraer, caducidad o
   cuota), sabiendo que hay que tocar `ficha_guardada` y `abrir_recintos` para que un `.gpkg` sin
   ZIP siga sirviendo. Decisión de David + código con prueba (§6.2).
3. **PAC de años anteriores**: sigue fuera. Se puede hacer cuando haya fichero oficial (o con el
   canal de recintos por campaña, que ya está verificado 2023–2026). Mientras, que la pantalla lo
   diga, como ya hace el cuaderno con las hojas que no escribe (§6.3).
4. **Reconciliar `ESTADO-AGENTE.md` con `WALL.md`** y **pasar el arnés de Chrome** en este HEAD
   (§6.5 y §6.6). No es código: es dejar el relevo y la evidencia a la misma altura.

---

## 8. Cómo se reproduce

```powershell
# 1 · Las pruebas de Python (266, 0 fallos, ~45 s)
cd F:\Proyectos\CueDigital\backend
$env:PYTHONIOENCODING="utf-8"
..\.venv\Scripts\python.exe -m pytest `
  tests\test_geopackage_sigpac.py tests\test_contorno_de_una_tierra.py `
  tests\test_codigos_desde_la_referencia.py tests\test_sigpac_cache.py `
  tests\test_sigpac.py tests\test_mapa_del_sigpac.py tests\test_mapa_de_una_tierra.py `
  tests\test_darle_la_forma_a_una_tierra.py tests\test_nuevo_api.py `
  tests\test_nuevo_importar.py tests\test_interfaz_nuevo.py

# 2 · Las pruebas de JavaScript (88, 0 fallos)
node --test "tests_js\nuevo.test.js"

# 3 · La prueba en vivo (el GeoPackage ya está en datos\sigpac_cache)
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000   # con base temporal y la caché real
#   POST /api/cuenta/registro
#   POST /api/parcelas  {"alias":"La del visor","superficie_ha":4.9016,"ref_sigpac":"37-70-0-0-503-51"}
#   POST /api/sigpac/cache/37/contornos
#   GET  /api/mapa/tierra/{id}.png
#   GET  /api/nuevo/que-falta   y   GET /api/nuevo/resumen
```

Ficheros leídos para esta verificación: `AGENTS.md`, `WALL.md`, `ESTADO-AGENTE.md`,
`backend/app/routers/parcelas.py`, `backend/app/routers/mapa.py`,
`backend/app/routers/nuevo_api.py`, `backend/app/geopackage_sigpac.py`, `backend/app/sigpac_cache.py`,
`backend/app/nuevo.py`, `backend/app/iuws.py`, `backend/app/mapa_de_una_tierra.py`,
`backend/web/nuevo/app.js`, `backend/web/nuevo/modelo.js` y los ficheros de pruebas citados.

**No se ha modificado ningún fichero de la aplicación.** El único fichero que se ha escrito es este
informe.
